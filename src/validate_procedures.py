"""
Day 2 Phase 4: Validate stored procedures (functions) work correctly.
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
    # -----------------------------------------------------
    section("sp_portfolio_metrics: 50/50 RELIANCE/TCS portfolio (1yr)")
    # -----------------------------------------------------
    df = pd.read_sql(text("""
        SELECT * FROM sp_portfolio_metrics(
            ARRAY['RELIANCE.NS', 'TCS.NS'],
            ARRAY[0.5, 0.5]::numeric[],
            (CURRENT_DATE - INTERVAL '1 year')::date,
            CURRENT_DATE
        );
    """), conn)
    print(df.to_string(index=False))

    # -----------------------------------------------------
    section("sp_portfolio_metrics: equal-weight banking basket (1yr)")
    # -----------------------------------------------------
    df = pd.read_sql(text("""
        SELECT * FROM sp_portfolio_metrics(
            ARRAY['HDFCBANK.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS', 'AXISBANK.NS', 'SBIN.NS'],
            ARRAY[0.2, 0.2, 0.2, 0.2, 0.2]::numeric[],
            (CURRENT_DATE - INTERVAL '1 year')::date,
            CURRENT_DATE
        );
    """), conn)
    print(df.to_string(index=False))

    # -----------------------------------------------------
    section("sp_portfolio_metrics: 5-stock concentrated IT basket (3yr)")
    # -----------------------------------------------------
    df = pd.read_sql(text("""
        SELECT * FROM sp_portfolio_metrics(
            ARRAY['TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS', 'TECHM.NS'],
            ARRAY[0.3, 0.3, 0.2, 0.1, 0.1]::numeric[],
            (CURRENT_DATE - INTERVAL '3 years')::date,
            CURRENT_DATE
        );
    """), conn)
    print(df.to_string(index=False))

    # -----------------------------------------------------
    section("sp_sector_exposure: diversified 10-stock portfolio")
    # -----------------------------------------------------
    df = pd.read_sql(text("""
        SELECT * FROM sp_sector_exposure(
            ARRAY['RELIANCE.NS', 'HDFCBANK.NS', 'TCS.NS', 'INFY.NS',
                  'HINDUNILVR.NS', 'ITC.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
                  'NTPC.NS', 'BHARTIARTL.NS'],
            ARRAY[0.15, 0.15, 0.12, 0.10, 0.10, 0.08, 0.08, 0.07, 0.08, 0.07]::numeric[]
        );
    """), conn)
    print(df.to_string(index=False))

    # -----------------------------------------------------
    section("sp_sector_exposure: IT-heavy portfolio")
    # -----------------------------------------------------
    df = pd.read_sql(text("""
        SELECT * FROM sp_sector_exposure(
            ARRAY['TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'RELIANCE.NS'],
            ARRAY[0.3, 0.3, 0.2, 0.2]::numeric[]
        );
    """), conn)
    print(df.to_string(index=False))

print("\n✅ Procedure validation complete.")