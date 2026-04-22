-- =====================================================
-- Nifty-Lens: Materialized View Refresh
-- Run this after any changes to prices_daily.
--
-- Views (returns_daily, returns_monthly) auto-update
-- since they're plain views. Only materialized views
-- need manual refresh.
-- =====================================================

REFRESH MATERIALIZED VIEW rolling_volatility;
REFRESH MATERIALIZED VIEW rolling_sharpe;
REFRESH MATERIALIZED VIEW drawdown_daily;
REFRESH MATERIALIZED VIEW correlation_matrix;