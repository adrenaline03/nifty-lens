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
- [x] Day 5: Predictions integration, dashboard-ready views, refresh pipeline
- [x] Day 6: Streamlit app scaffolded, Market Overview + Stock Deep-Dive pages
- [x] Day 7: Portfolio Analyzer + Volatility Predictions pages — all 4 dashboard pages live
- [ ] Day 8: Power BI dashboard (complement artifact) + Streamlit polish
- [ ] Day 9: Deployment to Streamlit Cloud
- [ ] Day 10-14: README polish, writeup, launch

## Tech Stack

- **Database:** PostgreSQL (Neon)
- **Data ingestion:** Python, yfinance, SQLAlchemy
- **Analytics layer:** SQL views + materialized views + pl/pgsql functions
- **ML feature engineering:** Python, pandas, `ta` library
- **ML model:** XGBoost classifier with time-series cross-validation
- **Orchestration:** Python refresh pipeline (`scripts/refresh_pipeline.py`)
- **Dashboard (coming):** Streamlit + Power BI

## Refresh Pipeline

Running `python scripts/refresh_pipeline.py` re-runs the entire data-to-predictions
pipeline end-to-end: ingests latest prices from yfinance, refreshes all materialized
views, recomputes ML features, and regenerates predictions. Useful flags:

- `--skip-ingest`: skip data ingestion (use existing Postgres data)
- `--skip-ml`: skip feature/prediction rebuild

## Dashboard

Interactive 4-page dashboard built with Streamlit + Plotly, querying the Postgres
analytics layer in real time.

**Pages:**

- **Market Overview** — NIFTY 50 index history, sector YTD heatmap, top gainers/losers (time-period selector: 1M/3M/6M/1Y/3Y)
- **Stock Deep-Dive** — ticker-level price chart with 50/200 DMA, rolling volatility, drawdown underwater plot, key metrics panel
- **Portfolio Analyzer** — interactive portfolio builder with weight sliders and sector exposure breakdown, powered by SQL stored procedures (`sp_portfolio_metrics`, `sp_sector_exposure`)
- **Volatility Predictions** — XGBoost model output with per-stock current predictions, confusion matrix, calibration chart, accuracy-over-time, sector performance breakdown, per-ticker prediction history

Run locally: `streamlit run streamlit_app/app.py`

## Highlights

- **67.80% test accuracy** on 3-class volatility regime classification (33% random baseline)
- **85.95% accuracy** on high-confidence predictions (>70% confidence, 40% of test set)
- **Well-calibrated classifier**: predicted probabilities match real accuracy across confidence tiers
- **Volatility clustering recovered independently**: `vol_5d` carries 52% of feature importance
- **16pp sector-accuracy spread**: model is differentially skilled (Utilities 74% vs Consumer Discretionary 58%)

## Data Scope

- 49 full-history NIFTY 50 constituents (5 years of daily OHLCV + features)
- TMPV.NS: partial history (post-October 2025 demerger)
- ETERNAL.NS: partial history (Zomato IPO July 2021)
- NIFTY 50 index (5 years)

## Assumptions

- 252 trading days per year
- 6.5% annualized risk-free rate (Indian 10-year G-Sec)
- Per-ticker volatility tertiles (low/medium/high regime boundaries are ticker-specific)
- Adjusted close prices for all return calculations
