"""
Shared database connection for all Streamlit pages.
Uses @st.cache_resource so the engine is created once and reused.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

@st.cache_resource
def get_engine() -> Engine:
  """Create and cache a SQLAlchemy engine. Called once per session."""
  conn_str = (
    f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
    f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
    f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
  )
  return create_engine(conn_str, pool_pre_ping=True)

@st.cache_data(ttl=3600, show_spinner=False)
def run_query(query: str, params: dict | None = None):
  """
  Execute a query and return results as a pandas DataFrame.
  Results are cached for 1 hour.

  Note: params dict must be hashable for cache to work. Lists/arrays
  should be passed as tuples.
  """
  import pandas as pd
  engine = get_engine()
  return pd.read_sql(text(query), engine, params=params or {})