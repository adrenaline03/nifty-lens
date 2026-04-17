# Nifty-Lens

**Volatility intelligence and portfolio analytics for NIFTY 50 equities.**

End-to-end analytics platform tracking 5 years of NIFTY 50 data — built with PostgreSQL, Streamlit, Power BI, and XGBoost.

🚧 **Under active development — launching in 14 days.**

## Status

- [x] Day 0: Infrastructure setup
- [x] Day 1: Data ingestion (50 NIFTY 50 constituents, ~61,400 rows of OHLCV data)
- [x] Day 2: SQL analytical layer (2 views, 3 materialized views, 2 stored functions)
- [ ] Day 3: ML feature engineering
- [ ] Day 4: Model training (XGBoost volatility classifier)
- [ ] Day 5: Predictions and integration
- [ ] Day 6-8: Streamlit app + Power BI dashboard
- [ ] Day 9: Deployment
- [ ] Day 10-14: Polish, writeup, launch

## Tech Stack

- **Database:** PostgreSQL (Neon)
- **Data ingestion:** Python, yfinance, SQLAlchemy
- **Analytics layer:** SQL views + materialized views + pl/pgsql functions
- **ML (coming):** XGBoost volatility regime classifier
- **Dashboard (coming):** Streamlit + Power BI

## Analytics Layer (Day 2)

The SQL analytics layer computes returns, risk metrics, and portfolio analytics
server-side, so the dashboard and ML layer can query pre-computed results.

**Views:**

- `returns_daily` — daily log and simple returns per ticker
- `returns_monthly` — month-end returns per ticker

**Materialized views:**

- `rolling_volatility` — 20-day and 60-day annualized volatility
- `rolling_sharpe` — 60-day rolling annualized Sharpe ratio
- `drawdown_daily` — running max price and current drawdown
- `correlation_matrix` — pairwise correlations over trailing 252 days

**Functions (stored procedures):**

- `sp_portfolio_metrics(tickers[], weights[], start, end)` — portfolio return, vol, Sharpe, max drawdown
- `sp_sector_exposure(tickers[], weights[])` — sector breakdown of a portfolio

Standard assumptions: 252 trading days/year, 6.5% annualized risk-free rate (Indian 10yr G-Sec).

## Data Scope

- 49 full-history NIFTY 50 constituents (5 years of daily OHLCV)
- 1 partial-history stock: **TMPV.NS** (post-October 2025 demerger)
- 1 partial-history stock: **ETERNAL.NS** (formerly Zomato, IPO July 2021)
- NIFTY 50 index (5 years)
