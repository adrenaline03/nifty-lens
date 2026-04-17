-- -----------------------------------------------------
-- 1. Latest closing price for each stock
-- -----------------------------------------------------
SELECT s.ticker, s.company_name, s.sector, p.date, p.close
FROM stocks s
JOIN LATERAL (
    SELECT date, close
    FROM prices_daily
    WHERE ticker = s.ticker
    ORDER BY date DESC
    LIMIT 1
) p ON TRUE
ORDER BY s.sector, s.ticker;


-- -----------------------------------------------------
-- 2. Top 10 best performers over the past year
-- -----------------------------------------------------
WITH year_ago_prices AS (
    SELECT DISTINCT ON (ticker) ticker, close AS price_1y_ago
    FROM prices_daily
    WHERE date <= CURRENT_DATE - INTERVAL '1 year'
    ORDER BY ticker, date DESC
),
latest_prices AS (
    SELECT DISTINCT ON (ticker) ticker, close AS price_now
    FROM prices_daily
    ORDER BY ticker, date DESC
)
SELECT
    s.ticker,
    s.company_name,
    s.sector,
    y.price_1y_ago,
    l.price_now,
    ROUND(((l.price_now - y.price_1y_ago) / y.price_1y_ago * 100)::numeric, 2) AS return_pct
FROM stocks s
JOIN year_ago_prices y ON y.ticker = s.ticker
JOIN latest_prices l ON l.ticker = s.ticker
ORDER BY return_pct DESC
LIMIT 10;


-- -----------------------------------------------------
-- 3. Sector-level average performance (past 1 year)
-- -----------------------------------------------------
WITH year_ago AS (
    SELECT DISTINCT ON (ticker) ticker, close AS price_then
    FROM prices_daily
    WHERE date <= CURRENT_DATE - INTERVAL '1 year'
    ORDER BY ticker, date DESC
),
latest AS (
    SELECT DISTINCT ON (ticker) ticker, close AS price_now
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
-- 4. Highest daily trading volume events (past year)
-- -----------------------------------------------------
SELECT p.ticker, s.company_name, p.date, p.volume, p.close
FROM prices_daily p
JOIN stocks s ON s.ticker = p.ticker
WHERE p.date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY p.volume DESC
LIMIT 20;


-- -----------------------------------------------------
-- 5. Biggest single-day losses (past year)
-- -----------------------------------------------------
WITH daily_returns AS (
    SELECT
        p.ticker,
        p.date,
        p.close,
        LAG(p.close) OVER (PARTITION BY p.ticker ORDER BY p.date) AS prev_close
    FROM prices_daily p
    WHERE p.date >= CURRENT_DATE - INTERVAL '1 year'
)
SELECT
    dr.ticker,
    s.company_name,
    s.sector,
    dr.date,
    dr.prev_close,
    dr.close,
    ROUND(((dr.close - dr.prev_close) / dr.prev_close * 100)::numeric, 2) AS daily_return_pct
FROM daily_returns dr
JOIN stocks s ON s.ticker = dr.ticker
WHERE dr.prev_close IS NOT NULL
ORDER BY daily_return_pct ASC
LIMIT 20;


-- -----------------------------------------------------
-- 6. NIFTY 50 index: YTD performance
-- -----------------------------------------------------
WITH ytd AS (
    SELECT
        (SELECT close FROM nifty_index
         WHERE date = (SELECT MIN(date) FROM nifty_index
                       WHERE date >= DATE_TRUNC('year', CURRENT_DATE))) AS year_open,
        (SELECT close FROM nifty_index ORDER BY date DESC LIMIT 1) AS latest
)
SELECT
    year_open,
    latest,
    ROUND(((latest - year_open) / year_open * 100)::numeric, 2) AS ytd_return_pct
FROM ytd;