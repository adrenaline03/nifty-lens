"""
Refresh all materialized views. Run after ingesting new data.
"""
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

load_dotenv()
connection_string = (
    f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
    f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
    f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
)
engine = create_engine(connection_string)

materialized_views = [
    "rolling_volatility",
    "rolling_sharpe",
    "drawdown_daily",
    "correlation_matrix",
]

with engine.begin() as conn:
    for mv in materialized_views:
        print(f"  Refreshing {mv}...")
        conn.execute(text(f"REFRESH MATERIALIZED VIEW {mv};"))

print("\n✅ All materialized views refreshed.")