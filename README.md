# Nifty-Lens

**Volatility intelligence and portfolio analytics for NIFTY 50 equities.**

End-to-end analytics platform tracking 5 years of NIFTY 50 data — built with PostgreSQL, Streamlit, Power BI, and XGBoost.

🚧 **Under active development — launching in 14 days.**

## Status

- [x] Day 0: Infrastructure setup
- [x] Day 1: Data ingestion (50 NIFTY 50 constituents, ~61,400 rows of OHLCV data)
- [ ] Day 2: SQL analytical layer (views, stored procedures)
- [ ] Day 3: ML feature engineering
- [ ] Day 4: Model training (XGBoost volatility classifier)
- [ ] Day 5: Predictions and integration
- [ ] Day 6-8: Streamlit app + Power BI dashboard
- [ ] Day 9: Deployment
- [ ] Day 10-14: Polish, writeup, launch

## Tech Stack

- **Database:** PostgreSQL (Neon)
- **Data ingestion:** Python, yfinance, SQLAlchemy
- **Analytics:** SQL views, XGBoost (coming Day 3-4)
- **Dashboard:** Streamlit + Power BI (coming Days 6-8)

## Data Scope

- 49 full-history NIFTY 50 constituents (5 years of daily OHLCV)
- 1 partial-history stock: **TMPV.NS** (post-October 2025 demerger)
- 1 partial-history stock: **ETERNAL.NS** (formerly Zomato, IPO July 2021)
- NIFTY 50 index (5 years)

More details coming as the project progresses.
