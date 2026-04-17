"""
Day 2: Validate analytical views return sensible results.
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
    # =========================================================
    # PHASE 1: returns_daily, returns_monthly
    # =========================================================
    section("returns_daily: row count and sample")
    count = conn.execute(text("SELECT COUNT(*) FROM returns_daily;")).scalar()
    print(f"  Total rows: {count:,}")

    df = pd.read_sql(text("""
        SELECT ticker, date, adj_close, simple_return, log_return
        FROM returns_daily
        WHERE ticker = 'RELIANCE.NS'
        ORDER BY date DESC
        LIMIT 5;
    """), conn)
    print("\n  RELIANCE.NS latest 5 days:")
    print(df.to_string(index=False))

    section("returns_daily: sanity checks")
    out_of_range = conn.execute(text("""
        SELECT COUNT(*) FROM returns_daily
        WHERE simple_return < -0.5 OR simple_return > 0.5;
    """)).scalar()
    print(f"  Rows with |simple_return| > 50%: {out_of_range}")

    df = pd.read_sql(text("""
        SELECT ticker, date, simple_return, log_return
        FROM returns_daily
        WHERE simple_return IS NOT NULL
        ORDER BY ABS(simple_return) DESC
        LIMIT 10;
    """), conn)
    print("\n  Top 10 most extreme single-day returns:")
    print(df.to_string(index=False))

    section("returns_daily: NULL first-row per ticker (expected)")
    nulls = conn.execute(text("""
        SELECT COUNT(*) FROM returns_daily WHERE simple_return IS NULL;
    """)).scalar()
    print(f"  NULL returns: {nulls}  (expected: 50)")

    section("returns_monthly: row count and sample")
    count = conn.execute(text("SELECT COUNT(*) FROM returns_monthly;")).scalar()
    print(f"  Total rows: {count:,}")

    df = pd.read_sql(text("""
        SELECT ticker, month, month_end_price, simple_return
        FROM returns_monthly
        WHERE ticker = 'RELIANCE.NS'
        ORDER BY month DESC
        LIMIT 6;
    """), conn)
    print("\n  RELIANCE.NS last 6 months:")
    print(df.to_string(index=False))

    # =========================================================
    # PHASE 2: rolling_volatility, rolling_sharpe, drawdown_daily
    # =========================================================
    section("rolling_volatility: sample (RELIANCE.NS)")
    df = pd.read_sql(text("""
        SELECT date, adj_close, vol_20d, vol_60d, n_obs_20d
        FROM rolling_volatility
        WHERE ticker = 'RELIANCE.NS' AND vol_60d IS NOT NULL
        ORDER BY date DESC LIMIT 5;
    """), conn)
    print(df.to_string(index=False))

    section("rolling_volatility: sanity checks")
    stats = conn.execute(text("""
        SELECT
            ROUND(AVG(vol_20d)::numeric, 4) AS avg_vol_20d,
            ROUND(AVG(vol_60d)::numeric, 4) AS avg_vol_60d,
            ROUND(MIN(vol_20d)::numeric, 4) AS min_vol_20d,
            ROUND(MAX(vol_20d)::numeric, 4) AS max_vol_20d
        FROM rolling_volatility
        WHERE vol_20d IS NOT NULL AND n_obs_20d = 20;
    """)).fetchone()
    print(f"  Avg 20-day vol: {stats.avg_vol_20d}")
    print(f"  Avg 60-day vol: {stats.avg_vol_60d}")
    print(f"  Min / Max 20-day vol: {stats.min_vol_20d} / {stats.max_vol_20d}")

    section("rolling_sharpe: sample (RELIANCE.NS)")
    df = pd.read_sql(text("""
        SELECT date, ROUND(sharpe_60d::numeric, 3) AS sharpe_60d,
               ROUND(mean_excess_60d::numeric, 6) AS mean_excess_60d,
               ROUND(std_60d::numeric, 6) AS std_60d
        FROM rolling_sharpe
        WHERE ticker = 'RELIANCE.NS' AND sharpe_60d IS NOT NULL
        ORDER BY date DESC LIMIT 5;
    """), conn)
    print(df.to_string(index=False))

    section("rolling_sharpe: top 10 all-time Sharpe ratios")
    df = pd.read_sql(text("""
        SELECT ticker, date, ROUND(sharpe_60d::numeric, 3) AS sharpe_60d
        FROM rolling_sharpe
        WHERE sharpe_60d IS NOT NULL AND n_obs_60d = 60
        ORDER BY sharpe_60d DESC LIMIT 10;
    """), conn)
    print(df.to_string(index=False))

    section("drawdown_daily: current drawdowns (most recent date)")
    df = pd.read_sql(text("""
        WITH latest AS (SELECT MAX(date) AS date FROM drawdown_daily)
        SELECT d.ticker, d.adj_close,
               ROUND(d.running_max::numeric, 2) AS running_max,
               ROUND((d.drawdown * 100)::numeric, 2) AS drawdown_pct
        FROM drawdown_daily d JOIN latest l ON d.date = l.date
        ORDER BY d.drawdown ASC LIMIT 10;
    """), conn)
    print("  Worst 10 current drawdowns:")
    print(df.to_string(index=False))

    section("drawdown_daily: worst-ever drawdowns per ticker")
    df = pd.read_sql(text("""
        SELECT ticker,
               MIN(drawdown) AS worst_drawdown,
               ROUND((MIN(drawdown) * 100)::numeric, 2) AS worst_drawdown_pct
        FROM drawdown_daily
        GROUP BY ticker
        ORDER BY worst_drawdown ASC LIMIT 10;
    """), conn)
    print(df.to_string(index=False))

    # =========================================================
    # PHASE 3: correlation_matrix
    # =========================================================
    section("correlation_matrix: row count and diagonal check")
    count = conn.execute(text("SELECT COUNT(*) FROM correlation_matrix;")).scalar()
    print(f"  Total rows: {count:,}")

    diag = conn.execute(text("""
        SELECT COUNT(*), MIN(correlation), MAX(correlation)
        FROM correlation_matrix WHERE ticker_a = ticker_b;
    """)).fetchone()
    print(f"  Self-correlations: {diag[0]} rows, range [{diag[1]:.4f}, {diag[2]:.4f}]")
    print("    (Expected: all ≈ 1.0)")

    section("correlation_matrix: top 10 most-correlated pairs (excluding self)")
    df = pd.read_sql(text("""
        SELECT ticker_a, ticker_b,
               ROUND(correlation::numeric, 3) AS corr, n_overlap_days
        FROM correlation_matrix
        WHERE ticker_a < ticker_b
        ORDER BY correlation DESC LIMIT 10;
    """), conn)
    print(df.to_string(index=False))

    section("correlation_matrix: 10 least-correlated pairs")
    df = pd.read_sql(text("""
        SELECT ticker_a, ticker_b,
               ROUND(correlation::numeric, 3) AS corr, n_overlap_days
        FROM correlation_matrix
        WHERE ticker_a < ticker_b
        ORDER BY correlation ASC LIMIT 10;
    """), conn)
    print(df.to_string(index=False))

    section("correlation_matrix: RELIANCE's 5 most-correlated peers")
    df = pd.read_sql(text("""
        SELECT ticker_b, ROUND(correlation::numeric, 3) AS corr
        FROM correlation_matrix
        WHERE ticker_a = 'RELIANCE.NS' AND ticker_b != 'RELIANCE.NS'
        ORDER BY correlation DESC LIMIT 5;
    """), conn)
    print(df.to_string(index=False))

    section("correlation_matrix: average pairwise correlation")
    avg_corr = conn.execute(text("""
        SELECT ROUND(AVG(correlation)::numeric, 3) AS avg_corr
        FROM correlation_matrix
        WHERE ticker_a < ticker_b;
    """)).scalar()
    print(f"  Average pairwise correlation: {avg_corr}")
    print("    (Expected: 0.35-0.55 for NIFTY 50 over trailing year)")

print("\n✅ All view validation complete.")