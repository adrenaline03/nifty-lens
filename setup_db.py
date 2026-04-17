"""
One-time schema setup for Nifty-Lens.
Run to recreate database schema.
"""

from pathlib import Path
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

schema_path = Path("sql/schema.sql")
if not schema_path.exists():
    raise FileNotFoundError(f"Schema file not found at {schema_path}")

schema_sql = schema_path.read_text(encoding="utf-8")

with engine.begin() as connection:
    for stmt in schema_sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            connection.execute(text(stmt))

print("Schema created successfully.")

with engine.connect() as connection:
    result = connection.execute(text("""
      SELECT table_name 
      FROM information_schema.tables
      WHERE table_schema = 'public'
      ORDER BY table_name;                               
"""))
    tables = [row[0] for row in result]
    print(f"\nTables in database: {tables}")