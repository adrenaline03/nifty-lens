-- =====================================================
-- Nifty-Lens: Example Analytical Queries
-- Uses views and materialized views from views.sql
-- =====================================================


-- -----------------------------------------------------
-- 1. Latest closing price + last-day return per stock
-- -----------------------------------------------------
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    rd.date,
    rd.adj_close,
    ROUND((rd.simple_return * 100)::numeric, 2) AS last_day_return_pct
FROM stocks s
JOIN LATERAL (
    SELECT date, adj_close, simple_return
    FROM returns_daily
    WHERE ticker = s.ticker
    ORDER BY date DESC
    LIMIT 1
) rd ON TRUE
ORDER BY last_day_return_pct DESC NULLS LAST;


-- -----------------------------------------------------
-- 2. Top 10 best performers over the past year
-- -----------------------------------------------------
WITH year_ago AS (
    SELECT DISTINCT ON (ticker) ticker, adj_close AS price_then
    FROM prices_daily
    WHERE date <= CURRENT_DATE - INTERVAL '1 year'
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
    ROUND(((l.price_now - y.price_then) / y.price_then * 100)::numeric, 2) AS return_1yr_pct
FROM stocks s
JOIN year_ago y ON y.ticker = s.ticker
JOIN latest l ON l.ticker = s.ticker
ORDER BY return_1yr_pct DESC
LIMIT 10;


-- -----------------------------------------------------
-- 3. Sector-level average 1-year return
-- -----------------------------------------------------
WITH year_ago AS (
    SELECT DISTINCT ON (ticker) ticker, adj_close AS price_then
    FROM prices_daily
    WHERE date <= CURRENT_DATE - INTERVAL '1 year'
    ORDER BY ticker, date DESC
),
latest AS (
    SELECT DISTINCT ON (ticker) ticker, adj_close AS price_now
    FROM prices_daily
    ORDER BY ticker, date DESC
)
SELECT
    s.sector,
    COUNT(*) AS n_stocks,
    ROUND(AVG((l.price_now - y.price_then) / y.price_then * 100)::numeric, 2) AS avg_return_pct
FROM stocks s
JOIN year_ago y ON y.ticker = s.ticker
JOIN latest l ON l.ticker = s.ticker
GROUP BY s.sector
ORDER BY avg_return_pct DESC;


-- -----------------------------------------------------
-- 4. Stocks currently near their all-time highs (< 5% drawdown)
-- -----------------------------------------------------
WITH latest_dd AS (
    SELECT DISTINCT ON (ticker) ticker, date, drawdown
    FROM drawdown_daily
    ORDER BY ticker, date DESC
)
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    ROUND((ld.drawdown * 100)::numeric, 2) AS drawdown_pct
FROM stocks s
JOIN latest_dd ld ON ld.ticker = s.ticker
WHERE ld.drawdown > -0.05
ORDER BY ld.drawdown DESC;


-- -----------------------------------------------------
-- 5. Highest-volatility stocks (latest 20-day vol)
-- -----------------------------------------------------
WITH latest_vol AS (
    SELECT DISTINCT ON (ticker) ticker, date, vol_20d, vol_60d
    FROM rolling_volatility
    WHERE vol_20d IS NOT NULL
    ORDER BY ticker, date DESC
)
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    ROUND((lv.vol_20d * 100)::numeric, 2) AS vol_20d_pct,
    ROUND((lv.vol_60d * 100)::numeric, 2) AS vol_60d_pct
FROM stocks s
JOIN latest_vol lv ON lv.ticker = s.ticker
ORDER BY lv.vol_20d DESC
LIMIT 10;


-- -----------------------------------------------------
-- 6. Best risk-adjusted performers (latest 60-day Sharpe)
-- -----------------------------------------------------
WITH latest_sharpe AS (
    SELECT DISTINCT ON (ticker) ticker, date, sharpe_60d
    FROM rolling_sharpe
    WHERE sharpe_60d IS NOT NULL
    ORDER BY ticker, date DESC
)
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    ROUND(ls.sharpe_60d::numeric, 3) AS sharpe_60d
FROM stocks s
JOIN latest_sharpe ls ON ls.ticker = s.ticker
ORDER BY ls.sharpe_60d DESC
LIMIT 10;


-- -----------------------------------------------------
-- 7. Biggest single-day moves across all stocks (past year)
-- -----------------------------------------------------
SELECT
    rd.ticker,
    s.company_name,
    s.sector,
    rd.date,
    ROUND((rd.simple_return * 100)::numeric, 2) AS daily_return_pct
FROM returns_daily rd
JOIN stocks s ON s.ticker = rd.ticker
WHERE rd.date >= CURRENT_DATE - INTERVAL '1 year'
  AND rd.simple_return IS NOT NULL
ORDER BY ABS(rd.simple_return) DESC
LIMIT 20;


-- -----------------------------------------------------
-- 8. Most-correlated pairs overall (trailing 1yr)
-- -----------------------------------------------------
SELECT
    c.ticker_a,
    sa.sector AS sector_a,
    c.ticker_b,
    sb.sector AS sector_b,
    ROUND(c.correlation::numeric, 3) AS correlation
FROM correlation_matrix c
JOIN stocks sa ON sa.ticker = c.ticker_a
JOIN stocks sb ON sb.ticker = c.ticker_b
WHERE c.ticker_a < c.ticker_b
ORDER BY c.correlation DESC
LIMIT 15;


-- -----------------------------------------------------
-- 9. Sample portfolio metrics call
-- 60/40 RELIANCE/HDFC BANK over past year
-- -----------------------------------------------------
SELECT * FROM sp_portfolio_metrics(
    ARRAY['RELIANCE.NS', 'HDFCBANK.NS'],
    ARRAY[0.6, 0.4]::numeric[],
    (CURRENT_DATE - INTERVAL '1 year')::date,
    CURRENT_DATE
);


-- -----------------------------------------------------
-- 10. Sample sector exposure call
-- Bluechip diversified portfolio
-- -----------------------------------------------------
SELECT * FROM sp_sector_exposure(
    ARRAY['RELIANCE.NS', 'HDFCBANK.NS', 'TCS.NS', 'INFY.NS',
          'HINDUNILVR.NS', 'ITC.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
          'NTPC.NS', 'BHARTIARTL.NS'],
    ARRAY[0.15, 0.15, 0.12, 0.10, 0.10, 0.08, 0.08, 0.07, 0.08, 0.07]::numeric[]
);


-- -----------------------------------------------------
-- 11. NIFTY 50 index cumulative performance (past 3 years)
-- -----------------------------------------------------
WITH three_yr_start AS (
    SELECT close AS start_close
    FROM nifty_index
    WHERE date >= CURRENT_DATE - INTERVAL '3 years'
    ORDER BY date ASC
    LIMIT 1
)
SELECT
    n.date,
    n.close,
    ROUND(((n.close - s.start_close) / s.start_close * 100)::numeric, 2) AS return_from_3yr_start_pct
FROM nifty_index n
CROSS JOIN three_yr_start s
WHERE n.date >= CURRENT_DATE - INTERVAL '3 years'
ORDER BY n.date;