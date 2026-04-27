"""
Shared database connection for all Streamlit pages.

Supports two environments seamlessly:
- Local development: reads from .env file at project root
- Streamlit Cloud deployment: reads from st.secrets

Detection is automatic — st.secrets is checked first; if empty, falls back to .env.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _get_db_config() -> dict:
  """
  Resolve database credentials, preferring st.secrets if available
  (Streamlit Cloud), else .env (local development).

  Returns dict with: user, password, host, port, database
  """
  # Try Streamlit secrets first
  try:
    if "neon" in st.secrets:
      return {
        "user": st.secrets["neon"]["user"],
        "password": st.secrets["neon"]["password"],
        "host": st.secrets["neon"]["host"],
        "port": st.secrets["neon"]["port"],
        "database": st.secrets["neon"]["database"],
      }
  except (FileNotFoundError, KeyError, st.errors.StreamlitSecretNotFoundError):
    pass

  # Fall back to .env (local development)
  PROJECT_ROOT = Path(__file__).parent.parent.parent
  load_dotenv(PROJECT_ROOT / ".env")
  return {
    "user": os.getenv("NEON_USER"),
    "password": os.getenv("NEON_PASSWORD"),
    "host": os.getenv("NEON_HOST"),
    "port": os.getenv("NEON_PORT"),
    "database": os.getenv("NEON_DATABASE"),
  }

@st.cache_resource
def get_engine() -> Engine:
  """Create and cache a SQLAlchemy engine. Called once per session."""
  cfg = _get_db_config()
  if not all(cfg.values()):
    raise RuntimeError(
      "Database credentials not found. Set NEON_* env variables in .env "
      "(local) or st.secrets['neon'] (cloud)."
    )
  conn_str = (
    f"postgresql://{cfg['user']}:{cfg['password']}"
    f"@{cfg['host']}:{cfg['port']}"
    f"/{cfg['database']}?sslmode=require"
  )
  return create_engine(conn_str, pool_pre_ping=True)


@st.cache_data(ttl=3600, show_spinner=False)
def run_query(query: str, params: dict | None = None):
  """
  Execute a query and return results as a pandas DataFrame.
  Results are cached for 1 hour.
  """
  import pandas as pd
  engine = get_engine()
  return pd.read_sql(text(query), engine, params=params or {})