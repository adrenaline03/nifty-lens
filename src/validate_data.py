"""
Day 1 validation: sanity-checks the ingested data.
Run anytime to verify database state.
"""
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
import pandas as pd

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
    # -----------------------------------------------------------
    section("TABLE ROW COUNTS")
    # -----------------------------------------------------------
    for table in ["stocks", "prices_daily", "nifty_index"]:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"  {table:20s} {count:,} rows")

    # -----------------------------------------------------------
    section("DATE COVERAGE")
    # -----------------------------------------------------------
    result = conn.execute(text("""
        SELECT MIN(date) AS earliest, MAX(date) AS latest
        FROM prices_daily;
    """)).fetchone()
    print(f"  prices_daily: {result.earliest} → {result.latest}")

    result = conn.execute(text("""
        SELECT MIN(date) AS earliest, MAX(date) AS latest
        FROM nifty_index;
    """)).fetchone()
    print(f"  nifty_index:  {result.earliest} → {result.latest}")

    # -----------------------------------------------------------
    section("ROW COUNT PER TICKER")
    # -----------------------------------------------------------
    df = pd.read_sql(text("""
        SELECT ticker, COUNT(*) AS n_rows,
               MIN(date) AS first_date, MAX(date) AS last_date
        FROM prices_daily
        GROUP BY ticker
        ORDER BY n_rows DESC, ticker;
    """), conn)
    print(df.to_string(index=False))

    # -----------------------------------------------------------
    section("SECTOR DISTRIBUTION")
    # -----------------------------------------------------------
    df = pd.read_sql(text("""
        SELECT sector, COUNT(*) AS n_stocks
        FROM stocks
        GROUP BY sector
        ORDER BY n_stocks DESC, sector;
    """), conn)
    print(df.to_string(index=False))

    # -----------------------------------------------------------
    section("DATA QUALITY CHECKS")
    # -----------------------------------------------------------
    # Null checks
    nulls = conn.execute(text("""
        SELECT
          COUNT(*) FILTER (WHERE close IS NULL)    AS null_close,
          COUNT(*) FILTER (WHERE volume IS NULL)   AS null_volume,
          COUNT(*) FILTER (WHERE open IS NULL)     AS null_open
        FROM prices_daily;
    """)).fetchone()
    print(f"  NULLs in prices_daily: close={nulls.null_close}, "
          f"volume={nulls.null_volume}, open={nulls.null_open}")

    # Negative or zero prices (invalid)
    bad = conn.execute(text("""
        SELECT COUNT(*) FROM prices_daily
        WHERE close <= 0 OR open <= 0 OR high <= 0 OR low <= 0;
    """)).scalar()
    print(f"  Rows with non-positive prices: {bad}")

    # High < Low (impossible)
    impossible = conn.execute(text("""
        SELECT COUNT(*) FROM prices_daily WHERE high < low;
    """)).scalar()
    print(f"  Rows where high < low (impossible): {impossible}")

    # Orphan prices (tickers not in stocks table)
    orphans = conn.execute(text("""
        SELECT COUNT(DISTINCT p.ticker)
        FROM prices_daily p
        LEFT JOIN stocks s ON p.ticker = s.ticker
        WHERE s.ticker IS NULL;
    """)).scalar()
    print(f"  Tickers in prices_daily but not in stocks: {orphans}")

    # -----------------------------------------------------------
    section("SAMPLE DATA — 5 RECENT ROWS FOR RELIANCE")
    # -----------------------------------------------------------
    df = pd.read_sql(text("""
        SELECT date, open, high, low, close, volume
        FROM prices_daily
        WHERE ticker = 'RELIANCE.NS'
        ORDER BY date DESC
        LIMIT 5;
    """), conn)
    print(df.to_string(index=False))

    # -----------------------------------------------------------
    section("SAMPLE DATA — NIFTY 50 INDEX (5 RECENT)")
    # -----------------------------------------------------------
    df = pd.read_sql(text("""
        SELECT date, open, high, low, close, volume
        FROM nifty_index
        ORDER BY date DESC
        LIMIT 5;
    """), conn)
    print(df.to_string(index=False))

print("\n" + "=" * 60)
print("Validation complete.")
print("=" * 60)