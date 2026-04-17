-- =====================================================
-- Nifty-Lens: Stored Procedures (Functions)
-- =====================================================
-- Portfolio-level analytics functions used by the dashboard
-- to compute metrics for user-defined portfolios.
-- =====================================================


-- =====================================================
-- FUNCTION: sp_portfolio_metrics
-- Given an array of tickers and their weights, returns
-- summary metrics for the weighted portfolio.
--
-- Inputs:
--   p_tickers  text[]    e.g., ARRAY['RELIANCE.NS', 'TCS.NS']
--   p_weights  numeric[] e.g., ARRAY[0.6, 0.4] (should sum to 1.0)
--   p_start    date      portfolio measurement start date
--   p_end      date      portfolio measurement end date
--
-- Returns: single row with portfolio-level metrics
-- =====================================================
DROP FUNCTION IF EXISTS sp_portfolio_metrics(text[], numeric[], date, date);

CREATE OR REPLACE FUNCTION sp_portfolio_metrics(
  p_tickers text[],
  p_weights numeric[],
  p_start date,
  p_end date
)
RETURNS TABLE (
  total_return numeric, 
  annualized_return numeric,
  annualized_volatility numeric,
  sharpe_ratio numeric,
  max_drawdown numeric,
  n_trading_days integer
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_daily_rf numeric := 0.065 / 252; -- Assuming 6.5% annual risk-free rate
BEGIN
  -- Validate Inputs
  IF array_length(p_tickers, 1) IS DISTINCT FROM array_length(p_weights, 1) THEN
    RAISE EXCEPTION 'tickers and weights arrays must be of the same length';
  END IF;

  RETURN QUERY
  WITH
  -- Unnest the two parallel arrays into (ticker, weight) rows
  portfolio AS (
    SELECT UNNEST(p_tickers) AS ticker, UNNEST(p_weights) AS weight
  ),
  -- Daily weighted returns for each date in range
  daily_portfolio AS (
        SELECT
            rd.date,
            SUM(rd.log_return * p.weight) AS portfolio_log_return
        FROM returns_daily rd
        JOIN portfolio p ON p.ticker = rd.ticker
        WHERE rd.date BETWEEN p_start AND p_end
          AND rd.log_return IS NOT NULL
        GROUP BY rd.date
    ),
  -- Cumulative returns for drawdown calculation
  cumulative AS (
      SELECT
          date,
          portfolio_log_return,
          EXP(SUM(portfolio_log_return) OVER (ORDER BY date)) AS cum_wealth
      FROM daily_portfolio
  ),
  -- Running max and drawdown from cumulative wealth
  drawdowns AS (
      SELECT
          cum_wealth,
          MAX(cum_wealth) OVER (ORDER BY date) AS running_max,
          (cum_wealth - MAX(cum_wealth) OVER (ORDER BY date))
              / MAX(cum_wealth) OVER (ORDER BY date) AS dd
      FROM cumulative
  ),
  -- Final summary stats
  summary AS (
        SELECT
            -- Total return: exp(sum(log_returns)) - 1
            (EXP(SUM(portfolio_log_return)) - 1)::numeric AS total_ret,
            -- Annualized return: mean_daily_log * 252, then exp - 1 for arithmetic
            (EXP(AVG(portfolio_log_return) * 252) - 1)::numeric AS ann_ret,
            -- Annualized vol
            (STDDEV_SAMP(portfolio_log_return) * SQRT(252))::numeric AS ann_vol,
            COUNT(*)::integer AS n_days
        FROM daily_portfolio
    )
    SELECT
        ROUND(s.total_ret, 4),
        ROUND(s.ann_ret, 4),
        ROUND(s.ann_vol, 4),
        -- Sharpe = (annualized excess return) / annualized vol
        CASE
            WHEN s.ann_vol > 0 THEN ROUND(((s.ann_ret - 0.065) / s.ann_vol)::numeric, 4)
            ELSE NULL
        END AS sharpe,
        ROUND((SELECT MIN(dd) FROM drawdowns)::numeric, 4) AS max_dd,
        s.n_days
    FROM summary s;
END;
$$;

-- =====================================================
-- FUNCTION: sp_sector_exposure
-- Given an array of tickers + weights, return sector-level
-- breakdown showing total weight per sector.
--
-- Inputs:
--   p_tickers  text[]    e.g., ARRAY['RELIANCE.NS', 'TCS.NS']
--   p_weights  numeric[] e.g., ARRAY[0.6, 0.4]
-- =====================================================
DROP FUNCTION IF EXISTS sp_sector_exposure(text[], numeric[]);

CREATE OR REPLACE FUNCTION sp_sector_exposure(
    p_tickers  text[],
    p_weights  numeric[]
)
RETURNS TABLE (
    sector        varchar(100),
    n_stocks      bigint,
    total_weight  numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF array_length(p_tickers, 1) IS DISTINCT FROM array_length(p_weights, 1) THEN
        RAISE EXCEPTION 'tickers and weights arrays must be same length';
    END IF;

    RETURN QUERY
    WITH portfolio AS (
        SELECT UNNEST(p_tickers) AS ticker,
               UNNEST(p_weights) AS weight
    )
    SELECT
        s.sector,
        COUNT(*)::bigint AS n_stocks,
        ROUND(SUM(p.weight)::numeric, 4) AS total_weight
    FROM portfolio p
    JOIN stocks s ON s.ticker = p.ticker
    GROUP BY s.sector
    ORDER BY total_weight DESC;
END;
$$;