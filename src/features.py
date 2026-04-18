"""
Day 3: Compute ML features per (ticker, date) and persist to Postgres.

Features computed:
- Price-based: lagged returns (1d, 5d, 20d), Bollinger Band width
- Volatility: 5-day and 20-day realized volatility, ATR (14d)
- Momentum: RSI-14, MACD, MACD signal
- Volume: volume ratio (today / 20-day avg)

Target: next-day volatility regime (low/medium/high) via per-ticker tertiles.

Output: ml_features table with columns:
  ticker, date, <features>, realized_vol_next, regime (0/1/2)
"""
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands, AverageTrueRange

load_dotenv()
connection_string = (
  f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
  f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
  f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
)
engine = create_engine(connection_string)

def fetch_ticker_prices(ticker: str) -> pd.DataFrame:
  """Pull all price history for one ticker, sorted by date."""
  query = text("""
    SELECT date, open, high, low, close, adj_close, volume
    FROM prices_daily
    WHERE ticker = :ticker
    ORDER BY date
  """)
  with engine.connect() as conn:
    df = pd.read_sql(query, conn, params={"ticker": ticker})

  # Cast to the type ta library expects
  for col in ["open", "high", "low", "close", "adj_close"]:
    df[col] = df[col].astype(float)
  df["volume"] = df["volume"].astype(float)

  return df

def compute_features(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
  """
  Given a per-ticker DataFrame with OHLCV columns sorted by date, 
  return a DataFrame of features + target variable.
  """
  df = df.copy()
  df["ticker"] = ticker

  # Use adj_close for return-based features (corporate actions adjusted)
  price = df["adj_close"]

  # RETURNS 
  df["log_return"] = np.log(price / price.shift(1))

  # Lagged returns: These encode recent momentum
  df["ret_1d"] = df["log_return"]
  df["ret_5d"] = np.log(price / price.shift(5))
  df["ret_20d"] = np.log(price / price.shift(20))

  # REALIZED VOLATILITY (PAST WINDOW, ANNUALIZED)
  df["vol_5d"] = df["log_return"].rolling(5).std() * np.sqrt(252)
  df["vol_20d"] = df["log_return"].rolling(20).std() * np.sqrt(252)

  # BOLLINGER BAND WIDTH
  # Wide bands = high vol regime; narrow bands = low vol regime
  bb = BollingerBands(close=price, window=20, window_dev=2)
  bb_high = bb.bollinger_hband()
  bb_low = bb.bollinger_lband()
  bb_mid = bb.bollinger_mavg()
  # Normalized width (as pct of price) to make cross-ticker comparable
  df["bb_width"] = (bb_high - bb_low) / bb_mid

  # ATR (AVERAGE TRUE RANGE)
  # Uses high/low/close; captures intraday range vol
  atr = AverageTrueRange(
      high=df["high"], low=df["low"], close=df["close"], window=14
  )
  df["atr_14"] = atr.average_true_range() / df["close"]  # normalize to pct

  # RSI
  rsi = RSIIndicator(close=price, window=14)
  df["rsi_14"] = rsi.rsi()

  # MACD
  macd = MACD(close=price, window_slow=26, window_fast=12, window_sign=9)
  df["macd"] = macd.macd()
  df["macd_signal"] = macd.macd_signal()
  df["macd_diff"] = df["macd"] - df["macd_signal"]

  # VOLUME RATIO
  # Today's volume relative to 20-day avg; unusual days have high ratios
  df["vol_avg_20d"] = df["volume"].rolling(20).mean()
  df["volume_ratio"] = df["volume"] / df["vol_avg_20d"]

  # Target: next-day realized volatility proxy
  # Using |log return| as proxy for volatility magnitude
  df["abs_return_next"] = df["log_return"].shift(-1).abs()

  # Regime label: tertile within this ticker's history
  # Drop NaN before computing quantiles
  abs_rets = df["abs_return_next"].dropna()
  if len(abs_rets) < 60:
      # Not enough history (e.g., TMPV.NS with 122 rows); skip regime computation
      df["regime"] = np.nan
  else:
      q33 = abs_rets.quantile(1 / 3)
      q67 = abs_rets.quantile(2 / 3)
      df["regime"] = pd.cut(
          df["abs_return_next"],
          bins=[-np.inf, q33, q67, np.inf],
          labels=[0, 1, 2],
      ).astype("Int64")  # nullable int

  return df

def build_all_features() -> pd.DataFrame:
  """Compute features for every ticker and combine into one DataFrame."""
  # Get list of tickers
  with engine.connect() as conn:
    tickers = [
       row[0] for row in conn.execute(text("SELECT ticker FROM stocks ORDER BY ticker"))
    ]

  all_features = []
  for i, ticker in enumerate(tickers):
    print(f"  [{i:02d}/{len(tickers)}] {ticker:18s}", end=" ")
    prices = fetch_ticker_prices(ticker)
    if prices.empty:
        print("⚠️  no prices")
        continue
    feats = compute_features(prices, ticker)
    # Keep only rows with complete features
    feats = feats.dropna(subset=[
        "ret_1d", "ret_5d", "ret_20d",
        "vol_5d", "vol_20d", "bb_width", "atr_14",
        "rsi_14", "macd", "macd_signal", "volume_ratio",
    ])
    print(f"✅ {len(feats):,} feature rows")
    all_features.append(feats)

  combined = pd.concat(all_features, ignore_index=True)
  return combined

def persist_to_postgres(df: pd.DataFrame):
    """Write the features DataFrame to ml_features table."""
    # Select only the columns we want to store
    columns = [
        "ticker", "date",
        # features
        "ret_1d", "ret_5d", "ret_20d",
        "vol_5d", "vol_20d", "bb_width", "atr_14",
        "rsi_14", "macd", "macd_signal", "macd_diff",
        "volume_ratio",
        # target
        "abs_return_next", "regime",
    ]
    df_out = df[columns].copy()

    # Create table schema
    create_sql = """
    DROP TABLE IF EXISTS ml_features CASCADE;

    CREATE TABLE ml_features (
        ticker          VARCHAR(20) NOT NULL,
        date            DATE NOT NULL,
        ret_1d          NUMERIC(12, 8),
        ret_5d          NUMERIC(12, 8),
        ret_20d         NUMERIC(12, 8),
        vol_5d          NUMERIC(12, 8),
        vol_20d         NUMERIC(12, 8),
        bb_width        NUMERIC(12, 8),
        atr_14          NUMERIC(12, 8),
        rsi_14          NUMERIC(12, 8),
        macd            NUMERIC(14, 8),
        macd_signal     NUMERIC(14, 8),
        macd_diff       NUMERIC(14, 8),
        volume_ratio    NUMERIC(12, 8),
        abs_return_next NUMERIC(12, 8),
        regime          SMALLINT,
        PRIMARY KEY (ticker, date)
    );

    CREATE INDEX idx_ml_features_date ON ml_features(date);
    CREATE INDEX idx_ml_features_ticker_date ON ml_features(ticker, date DESC);
    """

    print("\nCreating ml_features table...")
    with engine.begin() as conn:
        for stmt in create_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))

    print(f"Writing {len(df_out):,} rows to ml_features...")
    df_out.to_sql(
        name="ml_features",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM ml_features")).scalar()
    print(f"✅ ml_features now has {count:,} rows.")


def main():
    print("=" * 60)
    print("BUILDING FEATURES FOR ALL TICKERS")
    print("=" * 60)
    df = build_all_features()
    print(f"\nTotal feature rows across all tickers: {len(df):,}")
    persist_to_postgres(df)


if __name__ == "__main__":
    main()