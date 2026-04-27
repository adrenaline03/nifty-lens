"""
Page 1: Market Overview
Top-down view of NIFTY 50 market health — index, sectors, top movers.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.db import run_query
from utils.queries import get_query
from utils.styling import inject_css, render_sidebar_header, render_footer

st.set_page_config(page_title="Market Overview | Nifty-Lens", page_icon="📊", layout="wide")
inject_css()
render_sidebar_header()

st.title("📊 Market Overview")
st.caption("Daily snapshot of NIFTY 50 index performance, sector returns, and top movers.")

# KPI ROW

# Fetch NIFTY index history and compute current level + YTD return inline
nifty_df = run_query(get_query("Q_nifty_history"), {"years_back": 5})
nifty_df["date"] = pd.to_datetime(nifty_df["date"])
nifty_df = nifty_df.sort_values("date")

latest_close = float(nifty_df["close"].iloc[-1])
latest_date = nifty_df["date"].iloc[-1].date()

# YTD return: compare to first trading day of current year
current_year = latest_date.year
ytd_mask = nifty_df["date"].dt.year == current_year
ytd_start = float(nifty_df[ytd_mask]["close"].iloc[0])
ytd_return = (latest_close - ytd_start) / ytd_start * 100

# 1-year return
one_year_ago = nifty_df["date"].iloc[-1] - pd.Timedelta(days=365)
past_row = nifty_df[nifty_df["date"] <= one_year_ago].iloc[-1]
one_year_return = (latest_close - float(past_row["close"])) / float(past_row["close"]) * 100

# Sector performance for best/worst
sector_df = run_query(get_query("Q_sector_performance_ytd"))
sector_df["avg_ytd_return_pct"] = sector_df["avg_ytd_return_pct"].astype(float)
best_sector = sector_df.iloc[0]
worst_sector = sector_df.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
with col1:
  st.metric(
    "NIFTY 50",
    f"₹{latest_close:,.2f}",
    f"{ytd_return:+.2f}% YTD",
  )
with col2:
  st.metric(
    "1-Year Return",
    f"{one_year_return:+.2f}%",
    delta_color="normal",
  )
with col3:
  st.metric(
    "Best Sector (YTD)",
    best_sector["sector"],
    f"{best_sector['avg_ytd_return_pct']:+.2f}%",
  )
with col4:
  st.metric(
    "Worst Sector (YTD)",
    worst_sector["sector"],
    f"{worst_sector['avg_ytd_return_pct']:+.2f}%",
    delta_color="inverse",
  )

st.caption(f"As of {latest_date}")

st.markdown("---")

# NIFTY 50 Index History Chart

st.subheader("NIFTY 50 Index — 5 Year History")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=nifty_df["date"],
    y=nifty_df["close"].astype(float),
    mode="lines",
    line=dict(color="#4a90d9", width=2),
    name="NIFTY 50",
    hovertemplate="<b>%{x|%Y-%m-%d}</b><br>₹%{y:,.2f}<extra></extra>",
))

fig.update_layout(
    height=400,
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis_title=None,
    yaxis_title="Index Level (₹)",
    hovermode="x unified",
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(rangeslider=dict(visible=True), showgrid=True, gridcolor="#2a2f3a"),
    yaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Sector Performance Heatmap

st.subheader("Sector Performance — Year to Date")

fig_sector = px.bar(
    sector_df.sort_values("avg_ytd_return_pct"),
    x="avg_ytd_return_pct",
    y="sector",
    orientation="h",
    color="avg_ytd_return_pct",
    color_continuous_scale=["#d9534f", "#444444", "#5cb85c"],
    color_continuous_midpoint=0,
    labels={"avg_ytd_return_pct": "YTD Return (%)", "sector": ""},
    text="avg_ytd_return_pct",
)
fig_sector.update_traces(
    texttemplate="%{text:+.2f}%",
    textposition="outside",
    cliponaxis=False,
)
fig_sector.update_layout(
    height=450,
    margin=dict(l=0, r=60, t=10, b=0),
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    coloraxis_showscale=False,
    xaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
)
st.plotly_chart(fig_sector, use_container_width=True)

st.markdown("---")

# Top Gainers & Losers

st.subheader("Top Movers")

# Period selector
period_options = {
  "1 Month": 30,
  "3 Months": 90,
  "6 Months": 180,
  "1 Year": 365,
  "3 Years": 1095,
}
selected_period = st.radio(
  "Time period",
  options=list(period_options.keys()),
  horizontal=True,
  index=3,  # Default: 1 Year
)
days_back = period_options[selected_period]

gainers_col, losers_col = st.columns(2)

with gainers_col:
  st.markdown(f"**🟢 Top 10 Gainers ({selected_period})**")
  gainers = run_query(
    get_query("Q_top_gainers"),
    {"days_back": days_back, "limit_n": 10},
  )
  gainers["return_pct"] = gainers["return_pct"].astype(float)
  st.dataframe(
    gainers[["ticker", "company_name", "sector", "return_pct"]].rename(
        columns={
            "ticker": "Ticker",
            "company_name": "Company",
            "sector": "Sector",
            "return_pct": "Return %",
        }
    ),
    hide_index=True,
    column_config={
        "Return %": st.column_config.NumberColumn(
            "Return %",
            format="%+.2f%%",
        ),
    },
    use_container_width=True,
  )

with losers_col:
  st.markdown(f"**🔴 Top 10 Losers ({selected_period})**")
  losers = run_query(
    get_query("Q_top_losers"),
    {"days_back": days_back, "limit_n": 10},
  )
  losers["return_pct"] = losers["return_pct"].astype(float)
  st.dataframe(
      losers[["ticker", "company_name", "sector", "return_pct"]].rename(
          columns={
              "ticker": "Ticker",
              "company_name": "Company",
              "sector": "Sector",
              "return_pct": "Return %",
          }
      ),
      hide_index=True,
      column_config={
          "Return %": st.column_config.NumberColumn(
              "Return %",
              format="%+.2f%%",
          ),
      },
      use_container_width=True,
  )

render_footer()