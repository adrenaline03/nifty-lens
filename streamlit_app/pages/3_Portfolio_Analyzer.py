"""
Page 3: Portfolio Analyzer
Build a custom portfolio of NIFTY 50 stocks with user-defined weights.
Computes portfolio-level metrics via SQL stored procedures.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.db import run_query
from utils.queries import get_query

st.set_page_config(
  page_title="Portfolio Analyzer | Nifty-Lens",
  page_icon="💼",
  layout="wide",
)

st.title("💼 Portfolio Analyzer")
st.caption(
  "Build a custom NIFTY 50 portfolio. We compute return, volatility, Sharpe, "
  "and drawdown — plus sector exposure — using SQL stored procedures."
)

# Initialize state

if "portfolio" not in st.session_state:
  # Default: simple 3-stock balanced portfolio to demonstrate the page
  st.session_state.portfolio = [
    {"ticker": "RELIANCE.NS", "weight": 0.40},
    {"ticker": "HDFCBANK.NS", "weight": 0.30},
    {"ticker": "TCS.NS", "weight": 0.30},
  ]

# Load available tickers

tickers_df = run_query(get_query("Q_available_tickers"))
tickers_df = tickers_df.sort_values(["sector", "company_name"]).reset_index(drop=True)

# Map for display formatting
ticker_display = {
  row["ticker"]: f"{row['ticker']} — {row['company_name']}"
  for _, row in tickers_df.iterrows()
}

# Portfolio construction UI

st.subheader("Build Your Portfolio")

if st.session_state.portfolio:
  st.markdown("**Current holdings:**")

  for i, holding in enumerate(st.session_state.portfolio):
    cols = st.columns([3, 1, 1])
    with cols[0]:
      st.write(ticker_display.get(holding["ticker"], holding["ticker"]))
    with cols[1]:
      new_weight = st.slider(
        f"Weight %",
        min_value=0.0,
        max_value=100.0,
        value=float(holding["weight"] * 100),
        step=1.0,
        key=f"weight_{i}",
        label_visibility="collapsed",
      )
      st.session_state.portfolio[i]["weight"] = new_weight / 100
    with cols[2]:
      if st.button("✕", key=f"remove_{i}", help="Remove from portfolio"):
        st.session_state.portfolio.pop(i)
        st.rerun()

  total_weight = sum(h["weight"] for h in st.session_state.portfolio)
  if abs(total_weight - 1.0) < 0.001:
    st.success(f"✅ Weights sum to 100.00%")
  elif total_weight < 1.0:
    st.warning(f"⚠️ Weights sum to {total_weight * 100:.2f}% — under-allocated by {(1 - total_weight) * 100:.2f}%")
  else:
    st.warning(f"⚠️ Weights sum to {total_weight * 100:.2f}% — over-allocated by {(total_weight - 1) * 100:.2f}%")
else:
  st.info("No stocks added yet. Use the dropdown below to add.")

st.markdown("---")

# Add / Normalize / Clear controls

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
  existing_tickers = {h["ticker"] for h in st.session_state.portfolio}
  available = [t for t in tickers_df["ticker"] if t not in existing_tickers]

  if available: 
    display_options = [ticker_display[t] for t in available]
    to_add_display = st.selectbox(
      "Add a stock to your portfolio",
      options=display_options,
      index=None, 
      placeholder="Select a ticker to add...",
    )
  else: 
    to_add_display = None
    st.info("All NIFTY 50 stocks are in your portfolio.")

with col2:
  st.write("")
  st.write("")
  if st.button("➕ Add", disabled=(to_add_display is None), use_container_width=True):
    ticker_to_add = next(
      t for t, d in ticker_display.items() if d == to_add_display
    )

    n = len(st.session_state.portfolio) + 1
    new_weight = 1.0 / n
    existing_total = sum(h["weight"] for h in st.session_state.portfolio)
    if existing_total > 0:
      scale = (1.0 - new_weight) / existing_total
      for h in st.session_state.portfolio:
        h["weight"] *= scale
    st.session_state.portfolio.append({"ticker": ticker_to_add, "weight": new_weight})
    st.rerun()

with col3:
  st.write("")
  st.write("")
  c1, c2 = st.columns(2)
  with c1:
    if st.button("⚖️", help="Normalize weights to 100%", use_container_width=True):
      total = sum(h["weight"] for h in st.session_state.portfolio)
      if total > 0:
        for h in st.session_state.portfolio:
          h["weight"] /= total
        st.rerun()
  with c2:
    if st.button("🗑️", help="Clear all", use_container_width=True):
      st.session_state.portfolio = []
      st.rerun()

st.markdown("---")

# Analysis controls

st.subheader("Analysis")

date_col1, date_col2, _ = st.columns([1, 1, 2])
default_end = date.today()
default_start = default_end - timedelta(days=365)

with date_col1:
  start_date = st.date_input(
    "Start date",
    value=default_start,
    max_value=default_end - timedelta(days=30),
  )

with date_col2:
  end_date = st.date_input(
    "End date",
    value=default_end,
    max_value=default_end,
  )

can_analyze = (
  len(st.session_state.portfolio) > 0 
  and abs(sum(h["weight"] for h in st.session_state.portfolio) - 1.0) < 0.001
  and start_date < end_date 
)

analyze = st.button(
  "🔍 Analyze Portfolio",
  type="primary",
  disabled=not can_analyze,
  use_container_width=False,
)

if not can_analyze:
  st.caption(
    "Tip: Add at least one stock and ensure weights sum to 100% (use ⚖️ to normalize)."
  )

# Results

if analyze:
    tickers = [h["ticker"] for h in st.session_state.portfolio]
    weights = [h["weight"] for h in st.session_state.portfolio]

    with st.spinner("Computing portfolio metrics..."):
        # Portfolio metrics via stored procedure
        metrics_df = run_query(
            get_query("Q_portfolio_metrics"),
            {
                "tickers": tickers,
                "weights": weights,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        # Sector exposure via stored procedure
        sector_df = run_query(
            get_query("Q_portfolio_sector_exposure"),
            {
                "tickers": tickers,
                "weights": weights,
            },
        )

    if metrics_df.empty or metrics_df.iloc[0]["n_trading_days"] == 0:
        st.error(
            "No trading days found in the selected date range for these tickers. "
            "Try widening the date range."
        )
    else:
        metrics = metrics_df.iloc[0]

        st.markdown("---")
        st.subheader("📊 Portfolio Metrics")

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric(
                "Total Return",
                f"{float(metrics['total_return']) * 100:+.2f}%",
            )
        with m_col2:
            st.metric(
                "Annualized Return",
                f"{float(metrics['annualized_return']) * 100:+.2f}%",
            )
        with m_col3:
            st.metric(
                "Annualized Volatility",
                f"{float(metrics['annualized_volatility']) * 100:.2f}%",
            )
        with m_col4:
            sharpe = float(metrics["sharpe_ratio"]) if metrics["sharpe_ratio"] is not None else 0.0
            st.metric(
                "Sharpe Ratio",
                f"{sharpe:.2f}",
                help="(annual return − 6.5% risk-free) / annual volatility",
            )

        m_col5, m_col6 = st.columns(2)
        with m_col5:
            st.metric(
                "Max Drawdown",
                f"{float(metrics['max_drawdown']) * 100:.2f}%",
            )
        with m_col6:
            st.metric(
                "Trading Days",
                f"{int(metrics['n_trading_days']):,}",
            )

        st.markdown("---")

        # Sector exposure visualization
        st.subheader("🏭 Sector Exposure")

        sector_df["total_weight"] = sector_df["total_weight"].astype(float)
        sector_df = sector_df.sort_values("total_weight", ascending=False)

        pie_col, table_col = st.columns([2, 1])
        with pie_col:
            fig_pie = go.Figure(data=[go.Pie(
                labels=sector_df["sector"],
                values=sector_df["total_weight"],
                hole=0.45,
                textinfo="label+percent",
                textfont=dict(size=11),
                marker=dict(
                    line=dict(color="#0e1117", width=2),
                ),
                hovertemplate="<b>%{label}</b><br>%{value:.1%}<extra></extra>",
            )])
            fig_pie.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with table_col:
            st.markdown("**Breakdown:**")
            display_df = sector_df.copy()
            display_df["weight_pct"] = (display_df["total_weight"] * 100).round(2)
            st.dataframe(
                display_df[["sector", "n_stocks", "weight_pct"]].rename(
                    columns={
                        "sector": "Sector",
                        "n_stocks": "# Stocks",
                        "weight_pct": "Weight %",
                    }
                ),
                hide_index=True,
                column_config={
                    "Weight %": st.column_config.NumberColumn(
                        "Weight %",
                        format="%.2f%%",
                    ),
                },
                use_container_width=True,
            )