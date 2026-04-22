-- =====================================================
-- Nifty-Lens: Predictions Dashboard Views
-- =====================================================
-- Views that enrich ml_predictions with context useful for
-- dashboard rendering (company name, sector, price, etc.).
-- =====================================================


-- =====================================================
-- VIEW: predictions_enriched
-- One row per prediction with all context dashboards need.
-- =====================================================
DROP VIEW IF EXISTS predictions_enriched CASCADE;

CREATE VIEW predictions_enriched AS 
SELECT 
  p.ticker,
  s.company_name,
  s.sector, 
  s.industry,
  p.date,
  p.actual_regime, 
  p.predicted_regime,
  p.prob_low,
  p.prob_medium,
  p.prob_high,
  p.confidence,
  p.correct,
  -- Human-readable regime labels
  CASE p.predicted_regime
    WHEN 0 THEN 'Low'
    WHEN 1 THEN 'Medium'
    WHEN 2 THEN 'High'
  END AS predicted_label,
  CASE p.actual_regime
    WHEN 0 THEN 'Low'
    WHEN 1 THEN 'Medium'
    WHEN 2 THEN 'High'
  END AS actual_label,
  -- Confidence tier for filtering
  CASE 
    WHEN p.confidence >= 0.70 THEN 'High'
    WHEN p.confidence >= 0.50 THEN 'Medium'
    ELSE 'Low'
  END AS confidence_tier
FROM ml_predictions p
JOIN stocks s ON s.ticker = p.ticker;

-- =====================================================
-- VIEW: latest_predictions
-- Most recent prediction per ticker — what "today" looks like
-- for the dashboard's "current state" view.
-- =====================================================
DROP VIEW IF EXISTS latest_predictions CASCADE;

CREATE VIEW latest_predictions AS
SELECT DISTINCT ON (pe.ticker)
  pe.ticker, 
  pe.company_name,
  pe.sector,
  pe.date,
  pe.predicted_regime,
  pe.predicted_label,
  pe.confidence,
  pe.confidence_tier,
  pe.prob_low,
  pe.prob_medium,
  pe.prob_high
FROM predictions_enriched pe
ORDER BY pe.ticker, pe.date DESC;

-- =====================================================
-- VIEW: accuracy_by_date
-- Daily accuracy across all tickers — for the "model
-- accuracy over time" line chart on the dashboard.
-- =====================================================
DROP VIEW IF EXISTS accuracy_by_date CASCADE;

CREATE VIEW accuracy_by_date AS
SELECT
    date,
    COUNT(*) AS n_predictions,
    COUNT(*) FILTER (WHERE correct = TRUE) AS n_correct,
    ROUND(
        (COUNT(*) FILTER (WHERE correct = TRUE))::numeric / COUNT(*),
        4
    ) AS accuracy
FROM ml_predictions
GROUP BY date
ORDER BY date;


-- =====================================================
-- VIEW: accuracy_by_sector
-- Sector-level accuracy breakdown — shows whether the
-- model performs better on some sectors than others.
-- =====================================================
DROP VIEW IF EXISTS accuracy_by_sector CASCADE;

CREATE VIEW accuracy_by_sector AS
SELECT
    s.sector,
    COUNT(*) AS n_predictions,
    COUNT(*) FILTER (WHERE p.correct = TRUE) AS n_correct,
    ROUND(
        (COUNT(*) FILTER (WHERE p.correct = TRUE))::numeric / COUNT(*),
        4
    ) AS accuracy
FROM ml_predictions p
JOIN stocks s ON s.ticker = p.ticker
GROUP BY s.sector
ORDER BY accuracy DESC;

-- =====================================================
-- VIEW: accuracy_by_confidence_tier
-- Calibration check — are high-confidence predictions
-- actually more accurate?
-- =====================================================
DROP VIEW IF EXISTS accuracy_by_confidence_tier CASCADE;

CREATE VIEW accuracy_by_confidence_tier AS
SELECT
    CASE
        WHEN confidence < 0.40 THEN '1. <40%'
        WHEN confidence < 0.50 THEN '2. 40-50%'
        WHEN confidence < 0.60 THEN '3. 50-60%'
        WHEN confidence < 0.70 THEN '4. 60-70%'
        ELSE                        '5. >=70%'
    END AS confidence_bucket,
    COUNT(*) AS n_predictions,
    COUNT(*) FILTER (WHERE correct = TRUE) AS n_correct,
    ROUND(
        (COUNT(*) FILTER (WHERE correct = TRUE))::numeric / COUNT(*),
        4
    ) AS accuracy,
    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
FROM ml_predictions
GROUP BY 1
ORDER BY 1;

-- =====================================================
-- VIEW: accuracy_by_ticker
-- Per-stock accuracy — which tickers are easiest/hardest?
-- =====================================================
DROP VIEW IF EXISTS accuracy_by_ticker CASCADE;

CREATE VIEW accuracy_by_ticker AS
SELECT
    p.ticker,
    s.company_name,
    s.sector,
    COUNT(*) AS n_predictions,
    COUNT(*) FILTER (WHERE p.correct = TRUE) AS n_correct,
    ROUND(
        (COUNT(*) FILTER (WHERE p.correct = TRUE))::numeric / COUNT(*),
        4
    ) AS accuracy
FROM ml_predictions p
JOIN stocks s ON s.ticker = p.ticker
GROUP BY p.ticker, s.company_name, s.sector
ORDER BY accuracy DESC;

-- =====================================================
-- VIEW: confusion_matrix
-- Long-format confusion matrix for dashboard rendering.
-- =====================================================
DROP VIEW IF EXISTS confusion_matrix CASCADE;

CREATE VIEW confusion_matrix AS
SELECT
    actual_regime,
    predicted_regime,
    COUNT(*) AS n,
    CASE actual_regime
        WHEN 0 THEN 'Low'
        WHEN 1 THEN 'Medium'
        WHEN 2 THEN 'High'
    END AS actual_label,
    CASE predicted_regime
        WHEN 0 THEN 'Low'
        WHEN 1 THEN 'Medium'
        WHEN 2 THEN 'High'
    END AS predicted_label
FROM ml_predictions
GROUP BY actual_regime, predicted_regime
ORDER BY actual_regime, predicted_regime;