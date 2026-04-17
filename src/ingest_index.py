"""
Pull 5 years of NIFTY 50 index OHLCV data into nifty_index table.
"""
from dotenv import load_dotenv
import os
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

load_dotenv()

connection_string = (
    f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
    f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
    f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
)

engine = create_engine(connection_string)

# Date range: last 5 years ending today
end_date = datetime.now().date()
start_date = end_date - timedelta(days=5 * 365 + 30)  # ~5 years + buffer

print(f"Pulling NIFTY 50 index data from {start_date} to {end_date}...")

# ^NSEI is the NIFTY 50 index ticker on Yahoo Finance
index_data = yf.download(
    "^NSEI",
    start=start_date,
    end=end_date,
    progress=False,
    auto_adjust=False,
)

if index_data.empty:
    raise RuntimeError("yfinance returned empty data for ^NSEI. Try again in a minute.")

# yfinance returns MultiIndex columns when auto_adjust=False; flatten them
if isinstance(index_data.columns, pd.MultiIndex):
    index_data.columns = index_data.columns.get_level_values(0)

# Reset index so Date becomes a regular column
index_data = index_data.reset_index()
index_data.columns = [c.lower() for c in index_data.columns]

# Keep only required columns
index_data = index_data[["date", "open", "high", "low", "close", "volume"]]

# Ensure date is a date (not timestamp)
index_data["date"] = pd.to_datetime(index_data["date"]).dt.date

print(f"Fetched {len(index_data)} rows for NIFTY 50 index.")
print(f"Date range: {index_data['date'].min()} to {index_data['date'].max()}")
print(f"Sample row:\n{index_data.head(2)}\n")

# Insert into PostgresSQL
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE nifty_index;"))

# Write to DB
index_data.to_sql(
    name="nifty_index",
    con=engine,
    if_exists="append",
    index=False,
    method="multi",
    chunksize=500,
)

# Verify
with engine.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM nifty_index;")).scalar()
    earliest = conn.execute(text("SELECT MIN(date) FROM nifty_index;")).scalar()
    latest = conn.execute(text("SELECT MAX(date) FROM nifty_index;")).scalar()

print(f"nifty_index table now has {count} rows")
print(f"   from {earliest} to {latest}")