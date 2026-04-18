"""
Day 3 Phase 2: Sanity-check the ml_features table.

Checks:
- Row counts and coverage per ticker
- Feature value ranges (RSI should be 0-100, vol_20d should be 0-3, etc.)
- Class balance of the target variable
- No unexpected NaN patterns
"""
from dotenv import load_dotenv
import os
import pandas as pd
from sqlalchemy import create_engine, text

load_dotenv()
connection_string = (
    f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
    f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
    f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
)
engine = create_engine(connection_string)


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


with engine.connect() as conn:
    # ----------------------------------------------------
    section("Row counts and ticker coverage")
    # ----------------------------------------------------
    total = conn.execute(text("SELECT COUNT(*) FROM ml_features")).scalar()
    n_tickers = conn.execute(text("SELECT COUNT(DISTINCT ticker) FROM ml_features")).scalar()
    print(f"  Total rows: {total:,}")
    print(f"  Unique tickers: {n_tickers}")

    # ----------------------------------------------------
    section("Feature value ranges (sanity check)")
    # ----------------------------------------------------
    # Each feature should be in a reasonable range.
    # If any are way out, there's a bug.
    stats = pd.read_sql(text("""
        SELECT
            ROUND(AVG(rsi_14)::numeric, 2)       AS avg_rsi,
            ROUND(MIN(rsi_14)::numeric, 2)       AS min_rsi,
            ROUND(MAX(rsi_14)::numeric, 2)       AS max_rsi,
            ROUND(AVG(vol_20d)::numeric, 4)      AS avg_vol_20d,
            ROUND(MAX(vol_20d)::numeric, 4)      AS max_vol_20d,
            ROUND(AVG(atr_14)::numeric, 4)       AS avg_atr,
            ROUND(AVG(bb_width)::numeric, 4)     AS avg_bb_width,
            ROUND(AVG(volume_ratio)::numeric, 2) AS avg_volume_ratio,
            ROUND(MAX(volume_ratio)::numeric, 2) AS max_volume_ratio
        FROM ml_features;
    """), conn)
    print(stats.T.to_string(header=False))
    print()
    print("  Sanity expectations:")
    print("    RSI:          0-100 range, avg near 50")
    print("    vol_20d:      avg 0.20-0.35, max could be 2+ for extreme days")
    print("    atr_14:       avg 0.015-0.025 (normalized ATR ~1.5-2.5% of price)")
    print("    bb_width:     avg 0.05-0.15 (normalized BB width ~5-15%)")
    print("    volume_ratio: avg ~1.0 (by construction), can spike 5-20x")

    # ----------------------------------------------------
    section("Return features (should be small decimals)")
    # ----------------------------------------------------
    ret_stats = pd.read_sql(text("""
        SELECT
            ROUND(AVG(ret_1d)::numeric, 6)  AS avg_ret_1d,
            ROUND(STDDEV(ret_1d)::numeric, 4)  AS std_ret_1d,
            ROUND(MIN(ret_1d)::numeric, 3)  AS min_ret_1d,
            ROUND(MAX(ret_1d)::numeric, 3)  AS max_ret_1d,
            ROUND(AVG(ret_5d)::numeric, 6)  AS avg_ret_5d,
            ROUND(AVG(ret_20d)::numeric, 6) AS avg_ret_20d
        FROM ml_features;
    """), conn)
    print(ret_stats.T.to_string(header=False))
    print("\n  Sanity: log returns should be small decimals (-0.3 to +0.3 typical range)")

    # ----------------------------------------------------
    section("Target variable: class balance")
    # ----------------------------------------------------
    balance = pd.read_sql(text("""
        SELECT regime, COUNT(*) AS n, 
               ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ml_features WHERE regime IS NOT NULL))::numeric, 2) AS pct
        FROM ml_features
        WHERE regime IS NOT NULL
        GROUP BY regime
        ORDER BY regime;
    """), conn)
    print(balance.to_string(index=False))
    print("\n  Expected: ~33% per class (since regime = tertile split per ticker)")

    # NULL regime count (partial history tickers)
    null_regime = conn.execute(text("""
        SELECT COUNT(*) FROM ml_features WHERE regime IS NULL;
    """)).scalar()
    print(f"\n  Rows with NULL regime: {null_regime}")
    print("    (Expected: rows where we couldn't compute tertiles, mostly end-of-series)")

    # ----------------------------------------------------
    section("Class balance per ticker (spot-check 5 stocks)")
    # ----------------------------------------------------
    df = pd.read_sql(text("""
        SELECT ticker,
               COUNT(*) FILTER (WHERE regime = 0) AS low_n,
               COUNT(*) FILTER (WHERE regime = 1) AS med_n,
               COUNT(*) FILTER (WHERE regime = 2) AS high_n
        FROM ml_features
        WHERE ticker IN ('RELIANCE.NS', 'HDFCBANK.NS', 'ADANIENT.NS', 'TCS.NS', 'TMPV.NS')
        GROUP BY ticker
        ORDER BY ticker;
    """), conn)
    print(df.to_string(index=False))
    print("\n  Expected: roughly balanced per ticker (per-ticker tertile split)")

    # ----------------------------------------------------
    section("Sample feature row (latest RELIANCE data)")
    # ----------------------------------------------------
    sample = pd.read_sql(text("""
        SELECT ticker, date, ret_1d, vol_20d, bb_width, atr_14,
               rsi_14, macd_diff, volume_ratio, regime
        FROM ml_features
        WHERE ticker = 'RELIANCE.NS'
        ORDER BY date DESC
        LIMIT 5;
    """), conn)
    print(sample.to_string(index=False))

    # ----------------------------------------------------
    section("NULL feature audit")
    # ----------------------------------------------------
    # Count NULLs in each feature column
    null_counts = pd.read_sql(text("""
        SELECT
            SUM(CASE WHEN ret_1d IS NULL THEN 1 ELSE 0 END)       AS ret_1d,
            SUM(CASE WHEN vol_20d IS NULL THEN 1 ELSE 0 END)      AS vol_20d,
            SUM(CASE WHEN bb_width IS NULL THEN 1 ELSE 0 END)     AS bb_width,
            SUM(CASE WHEN atr_14 IS NULL THEN 1 ELSE 0 END)       AS atr_14,
            SUM(CASE WHEN rsi_14 IS NULL THEN 1 ELSE 0 END)       AS rsi_14,
            SUM(CASE WHEN macd IS NULL THEN 1 ELSE 0 END)         AS macd,
            SUM(CASE WHEN volume_ratio IS NULL THEN 1 ELSE 0 END) AS volume_ratio
        FROM ml_features;
    """), conn)
    print("  NULLs per feature column:")
    print(null_counts.T.to_string(header=False))
    print("\n  (Expected: all zeros — we dropped NaN rows during feature computation)")

print("\n✅ Feature validation complete.")