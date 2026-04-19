# Nifty-Lens

**Volatility intelligence and portfolio analytics for NIFTY 50 equities.**

End-to-end analytics platform tracking 5 years of NIFTY 50 data — built with PostgreSQL, Streamlit, Power BI, and XGBoost.

🚧 **Under active development — launching in 14 days.**

## Status

- [x] Day 0: Infrastructure setup
- [x] Day 1: Data ingestion (50 NIFTY 50 constituents, ~61,400 rows of OHLCV data)
- [x] Day 2: SQL analytical layer (2 views, 4 materialized views, 2 stored functions)
- [x] Day 3: ML feature engineering (12 features, 59,763 rows, volatility regime target)
- [x] Day 4: XGBoost classifier — 67.80% accuracy, 85.95% at high-confidence tier
- [ ] Day 5: Predictions integration + model-drift SQL views
- [ ] Day 6-8: Streamlit app + Power BI dashboard
- [ ] Day 9: Deployment
- [ ] Day 10-14: Polish, writeup, launch

## Tech Stack

- **Database:** PostgreSQL (Neon)
- **Data ingestion:** Python, yfinance, SQLAlchemy
- **Analytics layer:** SQL views + materialized views + pl/pgsql functions
- **ML feature engineering:** Python, pandas, `ta` library
- **ML model:** XGBoost classifier with time-series cross-validation
- **Dashboard (coming):** Streamlit + Power BI

## ML Model (Day 4)

Volatility regime classifier trained on 12 engineered features across 50 tickers and 5
years of daily data.

**Target:** Next-5-day average realized volatility bucket (low / medium / high) via
per-ticker tertile split.

**Key design decisions:**

- **Target choice matters more than model.** Initial next-day target yielded 39%
  accuracy (barely above random). Reframing to next-5-day average — aligned with
  well-documented volatility clustering — moved accuracy to 68%. A single-line change.
- **Time-based train/test split** (no shuffling). Walk-forward CV using
  `TimeSeriesSplit`. Final split: 4 years train → 1 year test.
- **Two-model comparison.** XGBoost (67.8%) slightly beats Logistic Regression (65.8%)
  — a healthy margin given our features are already well-engineered for monotonic
  relationships.

**Results (test set, 12,092 predictions):**

- Overall accuracy: **67.80%**
- High-confidence tier (>70% confidence): **85.95%** across 4,874 predictions
- Per-class recall: 70% low, 58% medium, 76% high
- Top feature: `vol_5d` at 52% of total importance — model independently learned
  volatility clustering
- Hyperparameter sanity check: 7 configurations tested, all within 0.5pp of default

See `notebooks/02_model_training.ipynb` for full analysis including calibration plots,
feature importance, and accuracy-over-time stability.

## Data Scope

- 49 full-history NIFTY 50 constituents (5 years of daily OHLCV + features)
- TMPV.NS: partial history (post-October 2025 demerger)
- ETERNAL.NS: partial history (Zomato IPO July 2021)
- NIFTY 50 index (5 years)
