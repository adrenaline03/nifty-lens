"""
Apply SQL procedures (CREATE FUNCTION statements) from a .sql file to Neon.
Handles $$-delimited function bodies that contain semicolons.
Usage: python apply_procedures.py sql/procedures.sql
"""
import sys
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

if len(sys.argv) != 2:
    print("Usage: python apply_procedures.py <path_to_sql_file>")
    sys.exit(1)

sql_path = Path(sys.argv[1])
raw_sql = sql_path.read_text(encoding="utf-8")


def split_sql_preserving_dollar_quoted(sql: str) -> list[str]:
    """
    Split on ; but preserve $$...$$ blocks.
    Tracks whether we're inside a $$ block and ignores semicolons there.
    """
    statements = []
    current = []
    in_dollar = False
    i = 0
    while i < len(sql):
        # Detect $$ delimiter
        if sql[i:i+2] == "$$":
            in_dollar = not in_dollar
            current.append("$$")
            i += 2
            continue
        if sql[i] == ";" and not in_dollar:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue
        current.append(sql[i])
        i += 1
    # Last statement (if no trailing semicolon)
    last = "".join(current).strip()
    if last:
        statements.append(last)
    return statements


def is_effectively_empty(stmt: str) -> bool:
    """True if statement is only whitespace or line comments."""
    lines = [ln.strip() for ln in stmt.split("\n")]
    meaningful = [ln for ln in lines if ln and not ln.startswith("--")]
    return len(meaningful) == 0


statements = [s for s in split_sql_preserving_dollar_quoted(raw_sql)
              if not is_effectively_empty(s)]

print(f"Applying {len(statements)} statements from {sql_path}...\n")

with engine.begin() as conn:
    for i, stmt in enumerate(statements, 1):
        meaningful_lines = [
            ln for ln in stmt.split("\n")
            if ln.strip() and not ln.strip().startswith("--")
        ]
        preview = meaningful_lines[0][:80] if meaningful_lines else "(empty)"
        print(f"  [{i}/{len(statements)}] {preview}...")
        conn.execute(text(stmt))

print(f"\n✅ Successfully applied {sql_path.name}")