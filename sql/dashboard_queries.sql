-- =====================================================
-- Nifty-Lens: Dashboard Query Library
-- =====================================================
-- Pre-built queries organized by dashboard page.
-- Streamlit loads these by reading the file and executing
-- specific blocks (named by the Q_<name> comments).
--
-- Each query is commented with:
-- - Q_<name>: unique identifier
-- - PAGE: which dashboard page uses it
-- - PARAMS: bind parameters expected (if any)
-- =====================================================


-- =====================================================
-- PAGE 1: MARKET OVERVIEW
-- =====================================================

-- Q_nifty_history
-- Returns NIFTY 50 index close prices for the last N years.
-- PARAMS: :years_back (int, default 5)
SELECT date, close
FROM nifty_index
WHERE date >= CURRENT_DATE - (:years_back * INTERVAL '1 year')
ORDER BY date;

-- Q_sector_performance_ytd
-- Year-to-date average return per sector.
WITH ytd_start AS (
  SELECT DISTINCT ON (ticker) ticker, adj_close AS price_then
  FROM prices_daily
  WHERE date >= DATE_TRUNC('year', CURRENT_DATE)
  ORDER BY ticker, date ASC
), 
latest AS (
  SELECT DISTINCT ON (ticker) ticker, adj_close AS price_now
  FROM prices_daily
  ORDER BY ticker, date DESC
)
SELECT 
  s.sector, 
  COUNT(*) AS n_stocks,
  ROUND(AVG((l.price_now - y.price_then) / y.price_then * 100)::numeric, 2) AS avg_ytd_return_pct
FROM stocks s
JOIN ytd_start y ON y.ticker = s.ticker
JOIN latest l ON l.ticker = s.ticker
GROUP BY s.sector
ORDER BY avg_ytd_return_pct DESC;

-- Q_top_gainers
-- Top N gainers over a given period.
-- PARAMS: :days_back (int), :limit_n (int)
WITH start_prices AS (
    SELECT DISTINCT ON (ticker) ticker, adj_close AS price_then
    FROM prices_daily
    WHERE date <= CURRENT_DATE - (:days_back * INTERVAL '1 day')
    ORDER BY ticker, date DESC
),
latest AS (
    SELECT DISTINCT ON (ticker) ticker, adj_close AS price_now
    FROM prices_daily
    ORDER BY ticker, date DESC
)
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    ROUND(((l.price_now - sp.price_then) / sp.price_then * 100)::numeric, 2) AS return_pct
FROM stocks s
JOIN start_prices sp ON sp.ticker = s.ticker
JOIN latest l ON l.ticker = s.ticker
ORDER BY return_pct DESC
LIMIT :limit_n;

-- Q_top_losers
-- Top N losers over a given period.
-- PARAMS: :days_back (int), :limit_n (int)
WITH start_prices AS (
    SELECT DISTINCT ON (ticker) ticker, adj_close AS price_then
    FROM prices_daily
    WHERE date <= CURRENT_DATE - (:days_back * INTERVAL '1 day')
    ORDER BY ticker, date DESC
),
latest AS (
    SELECT DISTINCT ON (ticker) ticker, adj_close AS price_now
    FROM prices_daily
    ORDER BY ticker, date DESC
)
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    ROUND(((l.price_now - sp.price_then) / sp.price_then * 100)::numeric, 2) AS return_pct
FROM stocks s
JOIN start_prices sp ON sp.ticker = s.ticker
JOIN latest l ON l.ticker = s.ticker
ORDER BY return_pct ASC
LIMIT :limit_n;

-- =====================================================
-- PAGE 2: STOCK DEEP-DIVE
-- =====================================================

-- Q_stock_price_history
-- Full OHLCV history for a single ticker.
-- PARAMS: :ticker (text)
SELECT date, open, high, low, close, adj_close, volume
FROM prices_daily
WHERE ticker = :ticker
ORDER BY date;


-- Q_stock_volatility
-- Rolling volatility time series for one ticker.
-- PARAMS: :ticker (text)
SELECT date, adj_close, vol_20d, vol_60d
FROM rolling_volatility
WHERE ticker = :ticker
  AND vol_20d IS NOT NULL
ORDER BY date;


-- Q_stock_drawdown
-- Drawdown time series for one ticker.
-- PARAMS: :ticker (text)
SELECT date, adj_close, running_max, drawdown
FROM drawdown_daily
WHERE ticker = :ticker
ORDER BY date;


-- Q_stock_key_metrics
-- Summary metrics for one ticker (latest row of each metric).
-- PARAMS: :ticker (text)
WITH metrics AS (
    SELECT
        :ticker AS ticker,
        (SELECT adj_close FROM prices_daily
         WHERE ticker = :ticker ORDER BY date DESC LIMIT 1) AS latest_price,
        (SELECT vol_60d FROM rolling_volatility
         WHERE ticker = :ticker AND vol_60d IS NOT NULL
         ORDER BY date DESC LIMIT 1) AS current_vol_60d,
        (SELECT sharpe_60d FROM rolling_sharpe
         WHERE ticker = :ticker AND sharpe_60d IS NOT NULL
         ORDER BY date DESC LIMIT 1) AS current_sharpe_60d,
        (SELECT MIN(drawdown) FROM drawdown_daily
         WHERE ticker = :ticker) AS worst_drawdown,
        (SELECT drawdown FROM drawdown_daily
         WHERE ticker = :ticker ORDER BY date DESC LIMIT 1) AS current_drawdown
)
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    m.latest_price,
    ROUND(m.current_vol_60d::numeric, 4) AS current_vol_60d,
    ROUND(m.current_sharpe_60d::numeric, 3) AS current_sharpe_60d,
    ROUND(m.worst_drawdown::numeric, 4) AS worst_drawdown,
    ROUND(m.current_drawdown::numeric, 4) AS current_drawdown
FROM metrics m
JOIN stocks s ON s.ticker = m.ticker;


-- =====================================================
-- PAGE 3: PORTFOLIO ANALYZER
-- =====================================================

-- Q_portfolio_metrics
-- Uses the stored function we built on Day 2.
-- PARAMS: :tickers (text[]), :weights (numeric[]),
--         :start_date (date), :end_date (date)
SELECT * FROM sp_portfolio_metrics(
    :tickers,
    :weights,
    :start_date,
    :end_date
);


-- Q_portfolio_sector_exposure
-- Uses the stored function we built on Day 2.
-- PARAMS: :tickers (text[]), :weights (numeric[])
SELECT * FROM sp_sector_exposure(
    :tickers,
    :weights
);


-- Q_available_tickers
-- For populating ticker dropdowns.
SELECT ticker, company_name, sector
FROM stocks
ORDER BY sector, company_name;


-- =====================================================
-- PAGE 4: VOLATILITY ML PREDICTIONS
-- =====================================================

-- Q_latest_prediction_for_ticker
-- The model's current regime prediction for one ticker.
-- PARAMS: :ticker (text)
SELECT
    ticker,
    company_name,
    sector,
    date,
    predicted_label,
    confidence_tier,
    ROUND(confidence::numeric, 3) AS confidence,
    ROUND(prob_low::numeric, 3) AS prob_low,
    ROUND(prob_medium::numeric, 3) AS prob_medium,
    ROUND(prob_high::numeric, 3) AS prob_high
FROM latest_predictions
WHERE ticker = :ticker;


-- Q_predictions_heatmap_all_tickers
-- All tickers' latest predictions — feeds the "market heat map" visual.
SELECT
    ticker,
    sector,
    predicted_label,
    confidence,
    prob_low,
    prob_medium,
    prob_high
FROM latest_predictions
ORDER BY sector, ticker;


-- Q_model_accuracy_over_time
-- Full daily accuracy series — for the accuracy line chart.
SELECT date, accuracy, n_predictions
FROM accuracy_by_date
ORDER BY date;


-- Q_model_confusion_matrix
-- 3x3 confusion matrix for visualization.
SELECT actual_label, predicted_label, n
FROM confusion_matrix
ORDER BY actual_regime, predicted_regime;


-- Q_model_calibration
-- Accuracy by confidence tier.
SELECT confidence_bucket, n_predictions, n_correct, accuracy, avg_confidence
FROM accuracy_by_confidence_tier
ORDER BY confidence_bucket;


-- Q_model_accuracy_by_sector
-- Sector-level accuracy breakdown.
SELECT sector, n_predictions, accuracy
FROM accuracy_by_sector
ORDER BY accuracy DESC;


-- Q_ticker_prediction_history
-- All past predictions for one ticker — shows model's track record.
-- PARAMS: :ticker (text)
SELECT
    date,
    actual_label,
    predicted_label,
    ROUND(confidence::numeric, 3) AS confidence,
    correct
FROM predictions_enriched
WHERE ticker = :ticker
ORDER BY date DESC
LIMIT 60;