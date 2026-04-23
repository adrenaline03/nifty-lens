"""
Load named queries from sql/dashboard_queries.sql.

Queries in the SQL file are delimited by "-- Q_<name>" comment lines.
Everything between one Q_ marker and the next is treated as the query body.
"""
import re
from pathlib import Path
from functools import lru_cache

PROJECT_ROOT = Path(__file__).parent.parent.parent
QUERIES_FILE = PROJECT_ROOT / "sql" / "dashboard_queries.sql"


@lru_cache(maxsize=1)
def _load_all_queries() -> dict[str, str]:
    """Parse the SQL file once and return {name: sql_text}."""
    content = QUERIES_FILE.read_text(encoding="utf-8")
    lines = content.split("\n")

    queries = {}
    current_name = None
    current_body: list[str] = []

    # Pattern matches lines like "-- Q_foo" or "-- Q_foo_bar"
    q_pattern = re.compile(r"^--\s+(Q_\w+)\s*$")

    def flush():
        """Save the accumulated lines under the current query name."""
        if current_name is None:
            return
        body = "\n".join(current_body).strip()
        # Drop any leading comment/blank lines (query description text)
        body_lines = body.split("\n")
        while body_lines and (body_lines[0].strip().startswith("--")
                              or body_lines[0].strip() == ""):
            body_lines.pop(0)
        # Drop trailing separator lines (block dividers)
        while body_lines and body_lines[-1].strip().startswith("-- ="):
            body_lines.pop()
        cleaned = "\n".join(body_lines).strip().rstrip(";")
        if cleaned:
            queries[current_name] = cleaned

    for line in lines:
        match = q_pattern.match(line)
        if match:
            # Hit a new query header — save previous, start new
            flush()
            current_name = match.group(1)
            current_body = []
        elif current_name is not None:
            current_body.append(line)

    # Don't forget the last query
    flush()

    return queries


def get_query(name: str) -> str:
    """Retrieve a named query by name. Raises KeyError if not found."""
    queries = _load_all_queries()
    if name not in queries:
        raise KeyError(
            f"Query '{name}' not found. Available: {sorted(queries.keys())}"
        )
    return queries[name]


def list_queries() -> list[str]:
    """Return sorted list of all available query names."""
    return sorted(_load_all_queries().keys()) 