"""
App-wide custom styling. Imported by every page via inject_css().
"""
import streamlit as st

CUSTOM_CSS = """
<style>
/* Tighter spacing throughout */
.block-container {
  padding-top: 2rem;
  padding-bottom: 2rem;
  max-width: 1400px;
}

/* Polished metric cards: subtle border + hover effect */
[data-testid="stMetric"] {
  background-color: rgba(74, 144, 217, 0.05);
  border: 1px solid rgba(74, 144, 217, 0.2);
  border-radius: 8px;
  padding: 16px 20px;
  transition: border-color 0.2s ease;
}
[data-testid="stMetric"]:hover {
  border-color: rgba(74, 144, 217, 0.5);
}

/* Metric label: smaller, muted */
[data-testid="stMetricLabel"] {
  font-size: 0.85rem;
  color: #9ca3af;
}

/* Metric value: bigger, more prominent */
[data-testid="stMetricValue"] {
  font-size: 1.65rem;
  font-weight: 600;
}

/* Cleaner section headers */
h2, h3 {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
}

/* Subheader caption styling */
.stCaption, [data-testid="stCaptionContainer"] {
  color: #8b95a8;
  font-size: 0.85rem;
}

/* Sidebar header */
.sidebar-header {
  padding: 0.5rem 0 1.5rem 0;
  border-bottom: 1px solid #2a2f3a;
  margin-bottom: 1rem;
}
.sidebar-header h1 {
  font-size: 1.4rem;
  margin: 0 0 0.3rem 0;
}
.sidebar-header p {
  font-size: 0.8rem;
  color: #8b95a8;
  margin: 0;
}

/* Tighter dataframe row spacing */
[data-testid="stDataFrame"] {
  border-radius: 6px;
}

/* Buttons: slightly more polished */
.stButton > button {
  border-radius: 6px;
  font-weight: 500;
}
</style>
"""

SIDEBAR_HTML = """
<div class="sidebar-header">
  <h1>📈 Nifty-Lens</h1>
  <p>NIFTY 50 analytics & volatility intelligence</p>
</div>
"""

def inject_css():
  """Call at the top of every page (after st.set_page_config)."""
  st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def render_sidebar_header():
  """Call at the top of every page (after inject_css) to brand the sidebar."""
  with st.sidebar:
    st.markdown(SIDEBAR_HTML, unsafe_allow_html=True)

def render_footer():
  """Compact footer shown at the bottom of every page."""
  st.markdown("---")
  st.caption(
    "[GitHub](https://github.com/adrenaline03/nifty-lens) · "
    "[LinkedIn](https://www.linkedin.com/in/nalin-singhal-553b6a24a/) · "
    "Portfolio project — not investment advice."
  )