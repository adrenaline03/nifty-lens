"""
Page 5: Methodology
Project narrative — design decisions, ML approach, key findings.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from utils.styling import inject_css, render_sidebar_header


st.set_page_config(
    page_title="Methodology | Nifty-Lens",
    page_icon="📚",
    layout="wide",
)
inject_css()
render_sidebar_header()

st.title("📚 Methodology")
st.caption("Design decisions, ML approach, and key findings from this project.")

st.markdown("---")

# =====================================================
# Section 1: Project goal
# =====================================================
st.subheader("🎯 What this project does")
st.markdown("""
Nifty-Lens predicts the **next-5-day volatility regime** for each NIFTY 50 stock —
classifying it as low, medium, or high volatility based on technical indicators
computed from 5 years of daily price data.

Volatility prediction is genuinely useful: risk managers, options traders, and
portfolio managers all care about *how choppy* a stock will be over the coming days,
distinct from *which direction* it will move.
""")

st.markdown("---")

# =====================================================
# Section 2: Data
# =====================================================
st.subheader("📊 Data layer")
st.markdown("""
- **Source:** yfinance (Yahoo Finance API), 5 years of daily OHLCV for all NIFTY 50 stocks
- **Coverage:** 49 stocks with full 5-year history; ETERNAL.NS (Zomato) has partial
  history from its July 2021 IPO; TMPV.NS has partial history from October 2025 demerger
- **Storage:** PostgreSQL hosted on Neon — chosen for serverless availability and
  generous free tier
- **Adjustments:** All return calculations use split/dividend-adjusted close prices
- **Standard assumptions:** 252 trading days/year, 6.5% annualized risk-free rate
  (Indian 10-year G-Sec yield)
""")

st.markdown("---")

# =====================================================
# Section 3: SQL analytics layer
# =====================================================
st.subheader("🗄️ SQL analytics")
st.markdown("""
Server-side analytics avoid duplicating logic across the dashboard and ML pipeline.
The database itself computes:

- **Returns:** daily and monthly, both simple and log
- **Rolling volatility:** 20-day and 60-day annualized
- **Rolling Sharpe:** 60-day window, ex-risk-free
- **Drawdowns:** running maximum and current drawdown
- **Correlation matrix:** pairwise Pearson correlation over trailing 252 days
- **Stored procedures:** `sp_portfolio_metrics()` and `sp_sector_exposure()` accept
  array parameters for dynamic portfolio analysis
""")

st.markdown("---")

# =====================================================
# Section 4: ML approach
# =====================================================
st.subheader("🤖 Machine learning")

st.markdown("**Features (12 total):**")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
- *Returns:* `ret_1d`, `ret_5d`, `ret_20d`
- *Volatility:* `vol_5d`, `vol_20d`
- *Range-based:* `bb_width`, `atr_14`
""")
with col_b:
    st.markdown("""
- *Momentum:* `rsi_14`, `macd`, `macd_signal`, `macd_diff`
- *Volume:* `volume_ratio` (today / 20-day avg)
""")

st.markdown("**Target:**")
st.markdown("""
The next-5-day average absolute log-return, bucketed into per-ticker tertiles
(low/medium/high). Per-ticker tertiles ensure HDFC Bank's "high vol day" and
Adani Enterprises' "high vol day" are scaled to each stock's own history.
""")

st.markdown("**Train/test split:**")
st.markdown("""
Strictly time-based — earliest 4 years for training, latest 1 year for testing.
**No random shuffling.** Within training, 3-fold walk-forward cross-validation
using `TimeSeriesSplit`. This mirrors how a real trading system would operate
and prevents leakage of future information into model evaluation.
""")

st.markdown("**Models:**")
st.markdown("""
- **Logistic Regression** (linear baseline) — 65.8% accuracy
- **XGBoost** (final model) — 67.8% accuracy

The 2pp gap is small because our engineered features already capture most of the
signal monotonically. XGBoost adds value through feature interactions
(e.g., "high `vol_5d` AND high `volume_ratio` is more predictive than either alone").
""")

st.markdown("---")

# =====================================================
# Section 5: The key finding
# =====================================================
st.subheader("💡 The most important finding")

st.warning("""
**Initial model targeted next-day volatility and achieved only 39% accuracy** —
just 6pp above the 33% random baseline. Single-day volatility is dominated by
idiosyncratic noise: news, overnight global moves, earnings surprises.

**Reframing to next-5-day average volatility moved accuracy to 67.8%** —
a 29-percentage-point jump from a single-line code change.

This aligns with well-documented *volatility clustering* in finance literature:
volatility is much more autocorrelated over 3-10 day windows than over single days.

**The lesson: target horizon mattered more than model complexity.**
""")

st.markdown("---")

# =====================================================
# Section 6: Calibration matters
# =====================================================
st.subheader("⚖️ Calibration > raw accuracy")

st.markdown("""
The headline 67.8% accuracy understates the model's usefulness. The classifier is
**well-calibrated**: when it reports >70% confidence, it is right 86% of the time
across 4,874 test examples (40% of the test set).

In production, this means a confidence threshold can be applied — users get
high-quality predictions when the model is confident, and honest uncertainty
when it isn't. This tiered behavior is arguably more valuable than the
raw accuracy number.
""")

st.markdown("---")

# =====================================================
# Section 7: Honest limitations
# =====================================================
st.subheader("⚠️ Known limitations")

st.markdown("""
1. **Tertile boundaries** were computed on the full dataset, meaning some
   information from the test period influenced the target definition. A
   production system would compute tertiles on training data only. Effect
   in practice is small but worth noting.

2. **Medium class is structurally hardest** (58% recall vs 70% for low and 76%
   for high). The middle tertile is closest in distribution to both extremes,
   making it inherently noisier.

3. **One-year test window** covers a specific market regime (April 2025 -
   April 2026). Robustness across regime changes (rate-cut cycles, geopolitical
   shocks, etc.) is untested.

4. **No transaction costs or slippage** are modeled in portfolio metrics —
   results are "gross" returns only.

5. **No news, sentiment, or macro features** — model relies purely on
   price/volume technicals. Adding macro factors would likely add a few points
   of accuracy at the cost of pipeline complexity.
""")

st.markdown("---")

# =====================================================
# Section 8: Stack and architecture
# =====================================================
st.subheader("🛠️ Tech stack")

st.markdown("""
- **Database:** PostgreSQL on Neon
- **Ingestion:** Python, yfinance, SQLAlchemy
- **Analytics:** SQL views, materialized views, pl/pgsql stored functions
- **Feature engineering:** Python, pandas, `ta` (Technical Analysis) library
- **ML:** XGBoost, scikit-learn
- **Dashboard:** Streamlit + Plotly, deployed to Streamlit Cloud
- **Orchestration:** Custom Python pipeline (`scripts/refresh_pipeline.py`)
""")

st.markdown("---")

st.caption(
    "Source code on GitHub: [github.com/adrenaline03/nifty-lens]"
    "(https://github.com/adrenaline03/nifty-lens)"
)