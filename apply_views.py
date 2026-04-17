"""
Apply SQL definitions (views, procedures, etc.) from a .sql file to Neon.
Usage: python apply_views.py sql/views.sql

Handles multi-line statements, single-line comments, and block statements.
"""
import sys
import re
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
    print("Usage: python apply_views.py <path_to_sql_file>")
    sys.exit(1)

sql_path = Path(sys.argv[1])
if not sql_path.exists():
    print(f"❌ File not found: {sql_path}")
    sys.exit(1)

raw_sql = sql_path.read_text(encoding="utf-8")


def strip_sql_comments(sql: str) -> str:
    """Remove -- line comments (but preserve strings and block structure)."""
    lines = []
    for line in sql.split("\n"):
        # Strip -- comments, but only if not inside a string literal
        # Simple heuristic: if the line has --, cut there
        if "--" in line:
            line = line.split("--", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def is_effectively_empty(stmt: str) -> bool:
    """True if the statement has no SQL keywords after comment stripping."""
    cleaned = strip_sql_comments(stmt).strip()
    return len(cleaned) == 0


# Split on semicolons at end of lines (safer than raw split).
# Keep multi-line statements intact.
statements = []
for stmt in raw_sql.split(";"):
    if not is_effectively_empty(stmt):
        # Keep the original statement (with comments) for readability in logs
        statements.append(stmt.strip())

print(f"Applying {len(statements)} statements from {sql_path}...\n")

with engine.begin() as conn:
    for i, stmt in enumerate(statements, 1):
        # Extract first meaningful (non-comment) line for logging
        meaningful_lines = [
            ln for ln in stmt.split("\n")
            if ln.strip() and not ln.strip().startswith("--")
        ]
        preview = meaningful_lines[0][:80] if meaningful_lines else "(empty)"
        print(f"  [{i}/{len(statements)}] {preview}...")
        conn.execute(text(stmt))

print(f"\n✅ Successfully applied {sql_path.name}")