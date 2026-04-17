"""
Pull 5 years of daily OHLCV data for all NIFTY 50 constituents.

Uses yf.Ticker().history() for cleaner column structure than yf.download().
"""
from pathlib import Path
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent))
from constituents import NIFTY_50_CONSTITUENTS

load_dotenv()

connection_string = (
    f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
    f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
    f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
)

engine = create_engine(connection_string)

end_date = datetime.now().date()
start_date = end_date - timedelta(days=5 * 365 + 30)

MAX_RETRIES = 3
RETRY_DELAY = 5


def fetch_ticker_data(ticker: str) -> pd.DataFrame | None:
    """Fetch OHLCV via Ticker().history(). Returns None on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            yf_ticker = yf.Ticker(ticker)
            df = yf_ticker.history(
                start=start_date,
                end=end_date,
                auto_adjust=True,  # adjusts prices for splits/dividends
            )

            if df.empty:
                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY * (2 ** (attempt - 1))
                    print(f"Empty response, retry {attempt}/{MAX_RETRIES} in {wait}s...")
                    time.sleep(wait)
                    continue
                return None

            # Ticker().history() returns clean columns: Open, High, Low, Close, Volume, Dividends, Stock Splits
            # Reset index to get Date as a column
            df = df.reset_index()

            # Normalize column names
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]

            # Keep what we need; duplicate close -> adj_close (since auto_adjust=True already adjusted)
            expected = ["date", "open", "high", "low", "close", "volume"]
            missing = [c for c in expected if c not in df.columns]
            if missing:
                print(f"Missing columns {missing}. Got: {list(df.columns)}")
                return None

            df = df[expected].copy()
            df["adj_close"] = df["close"]  # auto-adjusted close serves as both

            # Date: strip timezone, convert to pure date
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.date

            df["ticker"] = ticker

            # Drop any rows where close is null
            df = df.dropna(subset=["close"])

            return df

        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * (2 ** (attempt - 1))
                print(f"Error: {e} — retry {attempt}/{MAX_RETRIES} in {wait}s...")
                time.sleep(wait)
            else:
                print(f"Final failure: {e}")
                return None

    return None


def main():
    print(f"Ingesting {len(NIFTY_50_CONSTITUENTS)} tickers")
    print(f"Date range: {start_date} to {end_date}\n")

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE prices_daily;"))
    print("Cleared prices_daily table.\n")

    success_tickers = []
    failed_tickers = []
    total_rows = 0

    for i, stock in enumerate(NIFTY_50_CONSTITUENTS, 1):
        ticker = stock["ticker"]
        print(f"[{i:02d}/50] {ticker:18s} ", end="", flush=True)

        df = fetch_ticker_data(ticker)

        if df is None or df.empty:
            print("FAILED")
            failed_tickers.append(ticker)
            continue

        df = df[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]]

        try:
            df.to_sql(
                name="prices_daily",
                con=engine,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=500,
            )
            rows = len(df)
            earliest = df["date"].min()
            latest = df["date"].max()
            total_rows += rows
            success_tickers.append(ticker)
            print(f"{rows:4d} rows ({earliest} → {latest})")
        except Exception as e:
            err_msg = str(e).split('\n')[0][:150]
            print(f"DB INSERT FAILED: {type(e).__name__}: {err_msg}")
            failed_tickers.append(ticker)

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Succeeded: {len(success_tickers)}/50 tickers, {total_rows:,} total rows")

    if failed_tickers:
        print(f"Failed:    {len(failed_tickers)} — {failed_tickers}")
        print("\nRe-run the script to retry failed tickers.")
    else:
        print("All 50 tickers ingested successfully.")


if __name__ == "__main__":
    main()