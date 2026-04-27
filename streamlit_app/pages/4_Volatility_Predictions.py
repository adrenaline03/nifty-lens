"""
Page 4: Volatility Predictions
Visualizes the XGBoost volatility regime classifier's output.
All 50 stocks' latest predictions, model performance metrics, calibration,
accuracy over time, and per-ticker prediction history.
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
from utils.styling import inject_css, render_sidebar_header

st.set_page_config(
    page_title="Volatility Predictions | Nifty-Lens",
    page_icon="🔮",
    layout="wide",
)
inject_css()
render_sidebar_header()

st.title("🔮 Volatility Regime Predictions")
st.caption(
    "XGBoost classifier predicts next-5-day volatility regime (low/medium/high) "
    "per stock. Model achieves 67.80% accuracy overall, 85.95% on high-confidence predictions."
)

# Section 1: Market-wide prediction snapshot

st.subheader("📍 Current Market Snapshot")

snapshot_df = run_query(get_query("Q_predictions_heatmap_all_tickers"))
snapshot_df["confidence"] = snapshot_df["confidence"].astype(float)
snapshot_df["prob_low"] = snapshot_df["prob_low"].astype(float)
snapshot_df["prob_medium"] = snapshot_df["prob_medium"].astype(float)
snapshot_df["prob_high"] = snapshot_df["prob_high"].astype(float)

# Regime counts
regime_counts = snapshot_df["predicted_label"].value_counts().reindex(
  ["Low", "Medium", "High"], fill_value=0
)

snap_col1, snap_col2, snap_col3, snap_col4 = st.columns(4)
with snap_col1:
  st.metric("🟢 Low Volatility", int(regime_counts.get("Low", 0)))  
with snap_col2:
  st.metric("🟡 Medium Volatility", int(regime_counts.get("Medium", 0)))
with snap_col3:
  st.metric("🔴 High Volatility", int(regime_counts.get("High", 0)))
with snap_col4:
  avg_conf = snapshot_df["confidence"].mean()
  st.metric("Avg Confidence", f"{avg_conf * 100:.1f}%")

st.markdown("**Latest predictions for all 50 stocks** (sortable):")

display_snapshot = snapshot_df.copy()
display_snapshot["confidence_pct"] = (display_snapshot["confidence"] * 100).round(2)
st.dataframe(
  display_snapshot[[
    "ticker", "sector", "predicted_label", "confidence_pct",
    "prob_low", "prob_medium", "prob_high",
  ]].rename(columns={
    "ticker": "Ticker",
    "sector": "Sector",
    "predicted_label": "Predicted",
    "confidence_pct": "Confidence %",
    "prob_low": "P(Low)",
    "prob_medium": "P(Medium)",
    "prob_high": "P(High)",
  }),
  hide_index=True,
  column_config={
    "Confidence %": st.column_config.ProgressColumn(
      "Confidence %",
      format="%.2f%%",
      min_value=0.0,
      max_value=100.0,
    ),
    "P(Low)": st.column_config.NumberColumn(format="%.3f"),
    "P(Medium)": st.column_config.NumberColumn(format="%.3f"),
    "P(High)": st.column_config.NumberColumn(format="%.3f"),
  },
  use_container_width=True,
  height=420,
)

st.markdown("---")

# Section 2: Model Performance Summary

st.subheader("🎯 Model Performance")

perf_col1, perf_col2 = st.columns([1, 1])

with perf_col1:
  st.markdown("**Confusion Matrix**")
  cm_df = run_query(get_query("Q_model_confusion_matrix"))

  cm_matrix = cm_df.pivot(
    index="actual_label",
    columns="predicted_label",
    values="n",
  ).reindex(
    index=["Low", "Medium", "High"],
    columns=["Low", "Medium", "High"],
    fill_value=0,
  )

  cm_matrix_pct = cm_matrix.div(cm_matrix.sum(axis=1), axis=0) * 100

  annotations = [
    [f"{cm_matrix.iloc[i, j]}<br>({cm_matrix_pct.iloc[i, j]:.1f}%)"
    for j in range(3)] for i in range(3)
  ]

  fig_cm = go.Figure(data=go.Heatmap(
    z=cm_matrix_pct.values,
    x=["Low", "Medium", "High"],
    y=["Low", "Medium", "High"],
    colorscale="Blues",
    text=annotations,
    texttemplate="%{text}",
    textfont=dict(size=13),
    hovertemplate="Actual: %{y}<br>Predicted: %{x}<br>%{text}<extra></extra>",
    showscale=False,
  ))
  fig_cm.update_layout(
    height=360,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="Predicted",
    yaxis_title="Actual",
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(autorange="reversed"),  # Low on top, High on bottom (standard)
  )
  st.plotly_chart(fig_cm, use_container_width=True)

with perf_col2:
  st.markdown("**Confidence Calibration**")
  calib_df = run_query(get_query("Q_model_calibration"))
  calib_df["accuracy"] = calib_df["accuracy"].astype(float)
  calib_df["avg_confidence"] = calib_df["avg_confidence"].astype(float)

  fig_calib = go.Figure()

  fig_calib.add_trace(go.Bar(
    x=calib_df["confidence_bucket"],
    y=calib_df["accuracy"] * 100,
    name="Actual Accuracy",
    marker=dict(color="#4a90d9"),
    text=[f"{a * 100:.1f}%" for a in calib_df["accuracy"]],
    textposition="outside",
  ))

  fig_calib.add_trace(go.Scatter(
    x=calib_df["confidence_bucket"],
    y=calib_df["avg_confidence"] * 100,
    mode="lines+markers",
    name="Perfect Calibration",
    line=dict(color="#d9534f", width=2, dash="dash"),
    marker=dict(size=8),
  ))
  fig_calib.update_layout(
    height=360,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Confidence Bucket",
    yaxis_title="Accuracy (%)",
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#2a2f3a"),
    xaxis=dict(showgrid=False),
  )
  st.plotly_chart(fig_calib, use_container_width=True)

st.caption(
    "**Reading the calibration chart:** Each bar is the actual accuracy of predictions "
    "in that confidence bucket. The dashed line is the average confidence — if bars sit at "
    "or above the line, the model is well-calibrated (not overconfident)."
)

st.markdown("---")

# Section 3: Accuracy Over Time

st.subheader("📈 Accuracy Over Time")

time_df = run_query(get_query("Q_model_accuracy_over_time"))
time_df["date"] = pd.to_datetime(time_df["date"])
time_df["accuracy"] = time_df["accuracy"].astype(float)
time_df["rolling_20d"] = time_df["accuracy"].rolling(20).mean()

fig_time = go.Figure()
fig_time.add_trace(go.Scatter(
  x=time_df["date"],
  y=time_df["accuracy"] * 100,
  mode="lines",
  name="Daily accuracy",
  line=dict(color="#4a90d9", width=1),
  opacity=0.4,
))
fig_time.add_trace(go.Scatter(
  x=time_df["date"],
  y=time_df["rolling_20d"] * 100,
  mode="lines",
  name="20-day rolling",
  line=dict(color="#f0d267", width=2.5),
))

fig_time.add_hline(
  y=67.80,
  line=dict(color="#d9534f", dash="dash"),
  annotation_text="Overall (67.8%)",
  annotation_position="right",
)
# Random baseline
fig_time.add_hline(
  y=33.33,
  line=dict(color="gray", dash="dot"),
  annotation_text="Random (33.3%)",
  annotation_position="right",
)
fig_time.update_layout(
  height=350,
  margin=dict(l=10, r=80, t=10, b=10),
  xaxis_title=None,
  yaxis_title="Accuracy (%)",
  hovermode="x unified",
  template="plotly_dark",
  paper_bgcolor="rgba(0,0,0,0)",
  plot_bgcolor="rgba(0,0,0,0)",
  xaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
  yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#2a2f3a"),
  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_time, use_container_width=True)

st.markdown("---")

# Section 4: Accuracy by Sector

st.subheader("🏭 Accuracy by Sector")

sector_acc_df = run_query(get_query("Q_model_accuracy_by_sector"))
sector_acc_df["accuracy"] = sector_acc_df["accuracy"].astype(float) * 100
sector_acc_df = sector_acc_df.sort_values("accuracy")

fig_sector = go.Figure()
fig_sector.add_trace(go.Bar(
  x=sector_acc_df["accuracy"],
  y=sector_acc_df["sector"],
  orientation="h",
  marker=dict(
    color=sector_acc_df["accuracy"],
    colorscale=[[0, "#d9534f"], [0.5, "#f0d267"], [1, "#5cb85c"]],
    cmin=50, cmax=80,
  ),
  text=sector_acc_df["accuracy"].apply(lambda x: f"{x:.2f}%"),
  textposition="outside",
  hovertemplate="<b>%{y}</b><br>Accuracy: %{x:.2f}%<br>Predictions: %{customdata:,}<extra></extra>",
  customdata=sector_acc_df["n_predictions"],
))
fig_sector.add_vline(
  x=67.80,
  line=dict(color="#4a90d9", dash="dash"),
  annotation_text="Overall",
  annotation_position="top",
)
fig_sector.update_layout(
  height=420,
  margin=dict(l=10, r=60, t=30, b=10),
  xaxis_title="Accuracy (%)",
  yaxis_title=None,
  template="plotly_dark",
  paper_bgcolor="rgba(0,0,0,0)",
  plot_bgcolor="rgba(0,0,0,0)",
  xaxis=dict(range=[45, 85], showgrid=True, gridcolor="#2a2f3a"),
  showlegend=False,
)
st.plotly_chart(fig_sector, use_container_width=True)

st.caption(
  "The 16pp spread between best (Utilities, 74%) and worst (Consumer Discretionary, 58%) "
  "sector reflects genuine differences in how predictable each sector's volatility is."
)

st.markdown("---")

# Section 5: Per-Ticker Prediction History

st.subheader("🎯 Prediction History per Stock")

tickers_df = run_query(get_query("Q_available_tickers"))
display_options = [f"{r['ticker']} — {r['company_name']}" for _, r in tickers_df.iterrows()]
ticker_map = dict(zip(display_options, tickers_df["ticker"]))

default_idx = next(
  (i for i, opt in enumerate(display_options) if opt.startswith("RELIANCE.NS")),
  0,
)
selected_display = st.selectbox(
  "Pick a stock to see recent prediction history",
  options=display_options,
  index=default_idx,
)
selected_ticker = ticker_map[selected_display]

history_df = run_query(
  get_query("Q_ticker_prediction_history"),
  {"ticker": selected_ticker},
)

if history_df.empty:
  st.warning(f"No prediction history available for {selected_ticker}")
else:
  history_df["date"] = pd.to_datetime(history_df["date"])
  history_df["confidence"] = history_df["confidence"].astype(float)
  history_df = history_df.sort_values("date")

  # Compute ticker-level stats
  n_total = len(history_df)
  n_correct = history_df["correct"].sum()
  ticker_acc = n_correct / n_total * 100 if n_total > 0 else 0

  h_col1, h_col2, h_col3 = st.columns(3)
  with h_col1:
    st.metric("Predictions Shown", n_total)
  with h_col2:
    st.metric("Correct", int(n_correct))
  with h_col3:
    st.metric("Accuracy", f"{ticker_acc:.2f}%")

  # Map labels to integers for plotting
  label_to_int = {"Low": 0, "Medium": 1, "High": 2}
  history_df["actual_int"] = history_df["actual_label"].map(label_to_int)
  history_df["predicted_int"] = history_df["predicted_label"].map(label_to_int)

  fig_hist = go.Figure()
  fig_hist.add_trace(go.Scatter(
    x=history_df["date"],
    y=history_df["actual_int"],
    mode="lines+markers",
    name="Actual regime",
    line=dict(color="#4a90d9", width=2),
    marker=dict(size=8),
  ))
  fig_hist.add_trace(go.Scatter(
    x=history_df["date"],
    y=history_df["predicted_int"],
    mode="lines+markers",
    name="Predicted regime",
    line=dict(color="#f0d267", width=2, dash="dot"),
    marker=dict(size=8, symbol="diamond"),
  ))
  fig_hist.update_layout(
    height=320,
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis=dict(
      tickmode="array",
      tickvals=[0, 1, 2],
      ticktext=["Low", "Medium", "High"],
      range=[-0.3, 2.3],
      showgrid=True,
      gridcolor="#2a2f3a",
    ),
    xaxis=dict(showgrid=True, gridcolor="#2a2f3a"),
    hovermode="x unified",
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
  )
  st.plotly_chart(fig_hist, use_container_width=True)

  st.caption(
    "Blue = actual regime. Gold dots = model prediction. Where lines overlap, "
    "the model was correct. Gaps between them show where the model disagreed."
  )