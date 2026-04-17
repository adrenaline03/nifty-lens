-- =====================================================
-- Nifty-Lens: Analytical Views
-- =====================================================
-- Standard assumptions:
--   - Trading days per year: 252
--   - Risk-free rate (annualized): 6.5% (Indian 10-yr G-Sec)
--   - Volatility annualisation: daily_vol * sqrt(252)
-- =====================================================


-- =====================================================
-- VIEW: returns_daily
-- Daily log and simple returns per ticker.
-- Uses adj_close so splits/dividends are already adjusted.
-- =====================================================
DROP VIEW IF EXISTS returns_daily CASCADE;

CREATE VIEW returns_daily AS
WITH price_lag AS (
  SELECT 
    ticker, 
    date, 
    adj_close,
    LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
  FROM prices_daily
)
SELECT 
  ticker, 
  date, 
  adj_close,
  prev_close,
  -- Simple return: (P_t - P_{t-1}) / P_{t-1}
  CASE
    WHEN prev_close IS NULL OR prev_close = 0 THEN NULL
    ELSE (adj_close - prev_close) / prev_close
  END AS simple_return,
  -- Log return: ln(P_t / P_{t-1})
  CASE
    WHEN prev_close IS NULL OR prev_close <= 0 OR adj_close <= 0 THEN NULL
    ELSE LN(adj_close / prev_close)
  END AS log_return
FROM price_lag;

-- =====================================================
-- VIEW: returns_monthly
-- Month-end returns per ticker.
-- Computed from the last trading day of each month.
-- =====================================================
DROP VIEW IF EXISTS returns_monthly CASCADE;

CREATE VIEW returns_monthly AS
WITH monthly_last_day AS (
  -- Find the last trading day of each month for each ticker
  SELECT
    ticker, 
    DATE_TRUNC('month', date)::date AS month,
    MAX(date) AS month_end_date
  FROM prices_daily
  GROUP BY ticker, DATE_TRUNC('month', date)
),
monthly_prices AS (
  SELECT 
    m.ticker, 
    m.month, 
    m.month_end_date,
    p.adj_close AS month_end_price
  FROM monthly_last_day m
  JOIN prices_daily p 
    ON p.ticker = m.ticker AND p.date = m.month_end_date
),
with_prev AS (
  SELECT 
    ticker,
    month, 
    month_end_date,
    month_end_price,
    LAG(month_end_price) OVER (PARTITION BY ticker ORDER BY month) AS prev_month_price
  FROM monthly_prices
)
SELECT
  ticker, 
  month, 
  month_end_date,
  month_end_price,
  prev_month_price,
  CASE 
    WHEN prev_month_price IS NULL OR prev_month_price = 0 THEN NULL
    ELSE (month_end_price - prev_month_price) / prev_month_price
  END AS simple_return,
  CASE 
    WHEN prev_month_price IS NULL OR prev_month_price <= 0 OR month_end_price <= 0 THEN NULL
    ELSE LN(month_end_price / prev_month_price)
  END AS log_return
FROM with_prev;

-- =====================================================
-- MATERIALIZED VIEW: rolling_volatility
-- 20-day and 60-day annualized realized volatility.
-- Annualization: daily_std * sqrt(252)
-- =====================================================
DROP MATERIALIZED VIEW IF EXISTS rolling_volatility CASCADE;

CREATE MATERIALIZED VIEW rolling_volatility AS
SELECT
    ticker,
    date,
    adj_close,
    simple_return,
    log_return,

    -- 20-day rolling volatility (annualized)
    STDDEV_SAMP(log_return) OVER (
        PARTITION BY ticker ORDER BY date
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) * SQRT(252) AS vol_20d,

    -- 60-day rolling volatility (annualized)
    STDDEV_SAMP(log_return) OVER (
        PARTITION BY ticker ORDER BY date
        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
    ) * SQRT(252) AS vol_60d,

    -- Count of observations in the 20-day window
    -- (null if insufficient data)
    COUNT(log_return) OVER (
        PARTITION BY ticker ORDER BY date
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS n_obs_20d

FROM returns_daily;

-- Index for fast ticker-date lookups (e.g., dashboards)
CREATE INDEX idx_rolling_vol_ticker_date
    ON rolling_volatility(ticker, date DESC);


-- =====================================================
-- MATERIALIZED VIEW: rolling_sharpe
-- 60-day rolling annualized Sharpe ratio.
-- Assumption: 6.5% annualized risk-free rate (Indian 10yr G-Sec).
-- Daily risk-free ≈ 6.5% / 252 = 0.0258%
-- Annualization: (mean_excess * 252) / (std * sqrt(252))
-- =====================================================
DROP MATERIALIZED VIEW IF EXISTS rolling_sharpe CASCADE;

CREATE MATERIALIZED VIEW rolling_sharpe AS
WITH params AS (
    SELECT 0.065 / 252.0 AS daily_rf  -- daily risk-free rate
)
SELECT
    rd.ticker,
    rd.date,
    rd.log_return,

    -- 60-day rolling mean of excess returns
    AVG(rd.log_return - p.daily_rf) OVER (
        PARTITION BY rd.ticker ORDER BY rd.date
        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
    ) AS mean_excess_60d,

    -- 60-day rolling std of log returns
    STDDEV_SAMP(rd.log_return) OVER (
        PARTITION BY rd.ticker ORDER BY rd.date
        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
    ) AS std_60d,

    -- Annualized Sharpe: (mean_excess * 252) / (std * sqrt(252))
    CASE
        WHEN STDDEV_SAMP(rd.log_return) OVER (
                PARTITION BY rd.ticker ORDER BY rd.date
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) > 0
        THEN
            (AVG(rd.log_return - p.daily_rf) OVER (
                PARTITION BY rd.ticker ORDER BY rd.date
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) * 252)
            /
            (STDDEV_SAMP(rd.log_return) OVER (
                PARTITION BY rd.ticker ORDER BY rd.date
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) * SQRT(252))
        ELSE NULL
    END AS sharpe_60d,

    -- Observation count for the window
    COUNT(rd.log_return) OVER (
        PARTITION BY rd.ticker ORDER BY rd.date
        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
    ) AS n_obs_60d

FROM returns_daily rd
CROSS JOIN params p;

CREATE INDEX idx_rolling_sharpe_ticker_date
    ON rolling_sharpe(ticker, date DESC);


-- =====================================================
-- MATERIALIZED VIEW: drawdown_daily
-- Running max and current drawdown per ticker.
-- Drawdown is expressed as a decimal (e.g., -0.15 = -15%).
-- =====================================================
DROP MATERIALIZED VIEW IF EXISTS drawdown_daily CASCADE;

CREATE MATERIALIZED VIEW drawdown_daily AS
SELECT
    ticker,
    date,
    adj_close,

    -- Running maximum of adj_close from start of data
    MAX(adj_close) OVER (
        PARTITION BY ticker ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_max,

    -- Drawdown: (current - peak) / peak, always <= 0
    (adj_close - MAX(adj_close) OVER (
        PARTITION BY ticker ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )) / MAX(adj_close) OVER (
        PARTITION BY ticker ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS drawdown

FROM prices_daily;

CREATE INDEX idx_drawdown_ticker_date
    ON drawdown_daily(ticker, date DESC);

-- =====================================================
-- MATERIALIZED VIEW: correlation_matrix
-- Pairwise Pearson correlation of daily log returns
-- over the trailing 252 trading days (1 year).
--
-- Stored bidirectionally: (A,B) and (B,A) both present
-- for easier lookup. 50 tickers × 50 tickers = 2,500 rows
-- max (self-correlations included).
--
-- Requires minimum 180 overlapping observations to be
-- considered meaningful. Low-overlap pairs (e.g., TMPV
-- with pre-2025 stocks) will be excluded.
-- =====================================================
DROP MATERIALIZED VIEW IF EXISTS correlation_matrix CASCADE;

CREATE MATERIALIZED VIEW correlation_matrix AS
WITH recent_returns AS (
    SELECT ticker, date, log_return
    FROM returns_daily
    WHERE date >= CURRENT_DATE - INTERVAL '365 days'
      AND log_return IS NOT NULL
),
ticker_pairs AS (
    -- Every pair, including self-pairs
    SELECT DISTINCT a.ticker AS ticker_a, b.ticker AS ticker_b
    FROM (SELECT DISTINCT ticker FROM recent_returns) a
    CROSS JOIN (SELECT DISTINCT ticker FROM recent_returns) b
),
joined_returns AS (
    SELECT
        tp.ticker_a,
        tp.ticker_b,
        ra.log_return AS return_a,
        rb.log_return AS return_b
    FROM ticker_pairs tp
    JOIN recent_returns ra ON ra.ticker = tp.ticker_a
    JOIN recent_returns rb ON rb.ticker = tp.ticker_b AND rb.date = ra.date
)
SELECT
    ticker_a,
    ticker_b,
    CORR(return_a, return_b) AS correlation,
    COUNT(*) AS n_overlap_days
FROM joined_returns
GROUP BY ticker_a, ticker_b
HAVING COUNT(*) >= 180;

CREATE INDEX idx_corr_matrix_ticker_a ON correlation_matrix(ticker_a);
CREATE INDEX idx_corr_matrix_both ON correlation_matrix(ticker_a, ticker_b);