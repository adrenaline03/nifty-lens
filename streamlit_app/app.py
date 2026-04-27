"""
Nifty-Lens: Streamlit dashboard entry point.

This is the "home" page. Streamlit auto-detects pages/ folder and
creates sidebar navigation.
"""
import streamlit as st
from utils.styling import inject_css, render_sidebar_header

st.set_page_config(
  page_title="Nifty-Lens",
  page_icon="📈",
  layout="wide",
  initial_sidebar_state="expanded",
)
inject_css()
render_sidebar_header()

# Hero
st.title("Nifty-Lens")
st.markdown(
  "**Volatility intelligence and portfolio analytics for NIFTY 50 equities.**"
)

st.markdown("""
An end-to-end analytics platform tracking 5 years of NIFTY 50 data —
built with PostgreSQL, XGBoost, and Streamlit.

Use the sidebar to navigate through:
- **Market Overview** — index performance, sector returns, top movers
- **Stock Deep-Dive** — price, volatility, drawdown, and risk metrics per stock
- **Portfolio Analyzer** 
- **Volatility Predictions**
""")

# Key stats from the project
col1, col2, col3, col4 = st.columns(4)
with col1:
  st.metric("NIFTY 50 stocks", "50")  
with col2:
  st.metric("Days of data", "1,250+")
with col3:
  st.metric("Model accuracy", "67.8%")
with col4:
  st.metric("High-confidence accuracy", "85.9%")

st.markdown("---")

st.caption(
  "Data via yfinance, split/dividend adjusted. "
  "Volatility regime predictions from an XGBoost classifier trained on 12 engineered features. "
)
st.caption(
  "**This is a portfolio project, not investment advice.**"
)
st.caption(
  "[GitHub](https://github.com/adrenaline03/nifty-lens) · "
  "[LinkedIn](https://www.linkedin.com/in/nalin-singhal-553b6a24a/)"
)