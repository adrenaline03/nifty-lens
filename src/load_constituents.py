"""
Load NIFTY 50 constituents into the stocks table.
Idempotent: running it multiple times won't create duplicates.
"""
from pathlib import Path
import sys
from dotenv import load_dotenv
import os
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

# Idempotent upsert: INSERT ... ON CONFLICT DO UPDATE
upsert_sql = text("""
    INSERT INTO stocks (ticker, company_name, sector, industry)
    VALUES (:ticker, :company_name, :sector, :industry)
    ON CONFLICT (ticker) DO UPDATE SET
        company_name = EXCLUDED.company_name,
        sector = EXCLUDED.sector,
        industry = EXCLUDED.industry;
""")

with engine.begin() as conn:
    for stock in NIFTY_50_CONSTITUENTS:
        conn.execute(upsert_sql, stock)

print(f"Loaded {len(NIFTY_50_CONSTITUENTS)} constituents into stocks table.")

# Verification
with engine.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM stocks;")).scalar()
    print(f"Total rows in stocks table: {count}")

    print("\nSector distribution:")
    result = conn.execute(text("""
        SELECT sector, COUNT(*) as count
        FROM stocks
        GROUP BY sector
        ORDER BY count DESC, sector;
    """))
    for sector, count in result:
        print(f"  {sector:30s} {count}")