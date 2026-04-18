# Nifty-Lens

**Volatility intelligence and portfolio analytics for NIFTY 50 equities.**

End-to-end analytics platform tracking 5 years of NIFTY 50 data — built with PostgreSQL, Streamlit, Power BI, and XGBoost.

🚧 **Under active development — launching in 14 days.**

## Status

- [x] Day 0: Infrastructure setup
- [x] Day 1: Data ingestion (50 NIFTY 50 constituents, ~61,400 rows of OHLCV data)
- [x] Day 2: SQL analytical layer (2 views, 4 materialized views, 2 stored functions)
- [x] Day 3: ML feature engineering (12 features, 59,763 rows, volatility regime target)
- [ ] Day 4: Model training (XGBoost volatility classifier)
- [ ] Day 5: Predictions and integration
- [ ] Day 6-8: Streamlit app + Power BI dashboard
- [ ] Day 9: Deployment
- [ ] Day 10-14: Polish, writeup, launch

## Tech Stack

- **Database:** PostgreSQL (Neon)
- **Data ingestion:** Python, yfinance, SQLAlchemy
- **Analytics layer:** SQL views + materialized views + pl/pgsql functions
- **ML feature engineering:** Python, pandas, `ta` library (technical indicators)
- **ML model (coming):** XGBoost volatility regime classifier
- **Dashboard (coming):** Streamlit + Power BI

## ML Feature Layer (Day 3)

Built on top of `prices_daily`, the `ml_features` table contains 12 engineered
features per (ticker, date) pair plus a target variable:

**Price-based features:**

- Lagged returns: `ret_1d`, `ret_5d`, `ret_20d` (momentum signals)
- Bollinger Band width: `bb_width` (normalized to price)

**Volatility features:**

- Realized vol: `vol_5d`, `vol_20d` (annualized)
- ATR-14: `atr_14` (normalized to price)

**Momentum features:**

- RSI-14: `rsi_14`
- MACD & signal: `macd`, `macd_signal`, `macd_diff`

**Volume:**

- `volume_ratio` (today / 20-day avg)

**Target:** `regime` — next-day volatility bucket (low / medium / high) via
per-ticker historical tertile split. Near-perfect class balance (~33% each).

See `notebooks/01_eda.ipynb` for feature distributions, class balance, and regime
separation analysis.

## Data Scope

- 49 full-history NIFTY 50 constituents (5 years of daily OHLCV + features)
- TMPV.NS: partial history (post-October 2025 demerger)
- ETERNAL.NS: partial history (Zomato IPO July 2021)
- NIFTY 50 index (5 years)
