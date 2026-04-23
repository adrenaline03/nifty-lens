"""
Page 2: Stock Deep-Dive
Single-stock analysis: price, moving averages, volatility, drawdown, key metrics.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.db import run_query
from utils.queries import get_query


st.set_page_config(
    page_title="Stock Deep-Dive | Nifty-Lens",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Stock Deep-Dive")
st.caption("Interactive analysis of any NIFTY 50 constituent — price, volatility, drawdown.")

# Ticker Selector

tickers_df = run_query(get_query("Q_available_tickers"))

# Group tickers by sector for the dropdown display
tickers_df = tickers_df.sort_values(["sector", "company_name"])
display_options = [
  f"{row['ticker']} — {row['company_name']} ({row['sector']})"
  for _, row in tickers_df.iterrows()
]
ticker_map = dict(zip(display_options, tickers_df["ticker"]))

# Default to RELIANCE
default_idx = next(
    (i for i, opt in enumerate(display_options) if opt.startswith("RELIANCE.NS")),
    0,
)

selected_display = st.selectbox(
  "Select a stock",
  options=display_options,
  index=default_idx,
)
selected_ticker = ticker_map[selected_display]

st.markdown("---")

# Key Metrics Panel

metrics_df = run_query(get_query("Q_stock_key_metrics"), {"ticker": selected_ticker})

if metrics_df.empty:
  st.warning(f"No data for {selected_ticker}")
  st.stop()

metrics = metrics_df.iloc[0]

col1, col2, col3, col4 = st.columns(4)
with col1:
  st.metric(
    "Latest Price",
    f"₹{float(metrics['latest_price']):,.2f}",
  )
with col2:
  vol_pct = float(metrics["current_vol_60d"]) * 100
  st.metric(
    "60-Day Volatility",
    f"{vol_pct:.2f}%",
    help="Annualized realized volatility over trailing 60 days",
  )
with col3:
  sharpe = float(metrics["current_sharpe_60d"])
  st.metric(
    "60-Day Sharpe",
    f"{sharpe:.2f}",
    help="Risk-adjusted return — (return − 6.5% risk-free) / volatility",
  )
with col4:
  dd_pct = float(metrics["current_drawdown"]) * 100
  st.metric(
    "Current Drawdown",
    f"{dd_pct:.2f}%",
    help="% below all-time-high price",
  )

st.caption(
  f"**{metrics['company_name']}** · {metrics['sector']} · "
  f"Worst-ever drawdown: {float(metrics['worst_drawdown']) * 100:.2f}%"
)

st.markdown("---")

# Price Chart with Moving Averages

st.subheader("Price History with Moving Averages")

price_df = run_query(get_query("Q_stock_price_history"), {"ticker": selected_ticker})
price_df["date"] = pd.to_datetime(price_df["date"])
price_df["adj_close"] = price_df["adj_close"].astype(float)
price_df = price_df.sort_values("date").reset_index(drop=True)

# Compute MAs client-side (no need for another SQL round-trip)
price_df["ma_50"] = price_df["adj_close"].rolling(50).mean()
price_df["ma_200"] = price_df["adj_close"].rolling(200).mean()

fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
  x=price_df["date"], y=price_df["adj_close"],
  mode="lines", name="Price",
  line=dict(color="#4a90d9", width=1.5),
  hovertemplate="%{x|%Y-%m-%d}<br>₹%{y:,.2f}<extra></extra>",
))
fig_price.add_trace(go.Scatter(
  x=price_df["date"], y=price_df["ma_50"],
  mode="lines", name="50-day MA",
  line=dict(color="#f0d267", width=1.2, dash="dot"),
  hovertemplate="%{x|%Y-%m-%d}<br>MA50: ₹%{y:,.2f}<extra></extra>",
))
fig_price.add_trace(go.Scatter(
  x=price_df["date"], y=price_df["ma_200"],
  mode="lines", name="200-day MA",
  line=dict(color="#d9534f", width=1.2, dash="dot"),
  hovertemplate="%{x|%Y-%m-%d}<br>MA200: ₹%{y:,.2f}<extra></extra>",
))
fig_price.update_layout(
  height=400,
  margin=dict(l=0, r=0, t=10, b=0),
  xaxis_title=None,
  yaxis_title="Price (₹)",
  hovermode="x unified",
  template="plotly_dark",
  paper_bgcolor="rgba(0,0,0,0)",
  plot_bgcolor="rgba(0,0,0,0)",
  xaxis=dict(rangeslider=dict(visible=True), showgrid=True, gridcolor="#2a2f3a"),
  yaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_price, use_container_width=True)

st.markdown("---")

# Rolling Volatility Chart

st.subheader("Rolling Volatility (Annualized)")

vol_df = run_query(get_query("Q_stock_volatility"), {"ticker": selected_ticker})
vol_df["date"] = pd.to_datetime(vol_df["date"])
for col in ["vol_20d", "vol_60d"]:
  vol_df[col] = vol_df[col].astype(float)

fig_vol = go.Figure()
fig_vol.add_trace(go.Scatter(
  x=vol_df["date"], y=vol_df["vol_20d"] * 100,
  mode="lines", name="20-day vol",
  line=dict(color="#8db365", width=1.2),
  hovertemplate="%{x|%Y-%m-%d}<br>20d: %{y:.2f}%<extra></extra>",
))
fig_vol.add_trace(go.Scatter(
  x=vol_df["date"], y=vol_df["vol_60d"] * 100,
  mode="lines", name="60-day vol",
  line=dict(color="#4a90d9", width=1.8),
  hovertemplate="%{x|%Y-%m-%d}<br>60d: %{y:.2f}%<extra></extra>",
))
fig_vol.update_layout(
  height=320,
  margin=dict(l=0, r=0, t=10, b=0),
  xaxis_title=None,
  yaxis_title="Volatility (%)",
  hovermode="x unified",
  template="plotly_dark",
  paper_bgcolor="rgba(0,0,0,0)",
  plot_bgcolor="rgba(0,0,0,0)",
  xaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
  yaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("---")

# Drawdown Chart (Underwater Plot)
 
st.subheader("Drawdown History")

dd_df = run_query(get_query("Q_stock_drawdown"), {"ticker": selected_ticker})
dd_df["date"] = pd.to_datetime(dd_df["date"])
dd_df["drawdown"] = dd_df["drawdown"].astype(float) * 100  # to percentage

fig_dd = go.Figure()
fig_dd.add_trace(go.Scatter(
  x=dd_df["date"], y=dd_df["drawdown"],
  mode="lines", name="Drawdown",
  line=dict(color="#d9534f", width=1.5),
  fill="tozeroy",
  fillcolor="rgba(217, 83, 79, 0.3)",
  hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>",
))
fig_dd.update_layout(
  height=300,
  margin=dict(l=0, r=0, t=10, b=0),
  xaxis_title=None,
  yaxis_title="Drawdown (%)",
  hovermode="x unified",
  template="plotly_dark",
  paper_bgcolor="rgba(0,0,0,0)",
  plot_bgcolor="rgba(0,0,0,0)",
  xaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
  yaxis=dict(showgrid=True, gridcolor="#2a2f3a", range=[None, 2]),
)
st.plotly_chart(fig_dd, use_container_width=True)

st.caption(
  "Drawdown = % below all-time-high price. "
  "Measures peak-to-trough decline. The 'underwater curve' shape is a standard "
  "risk visualization."
)