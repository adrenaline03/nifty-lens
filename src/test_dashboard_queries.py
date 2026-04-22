"""
Day 5 Phase 3: Smoke-test dashboard queries to catch SQL errors early.
"""
from dotenv import load_dotenv
import os
import pandas as pd
from sqlalchemy import create_engine, text

load_dotenv()
connection_string = (
    f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
    f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
    f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
)
engine = create_engine(connection_string)


def run_test(label: str, query: str, params: dict | None = None):
    print(f"\n[{label}]")
    try:
        df = pd.read_sql(text(query), engine, params=params)
        print(f"  ✅ {len(df)} rows returned")
        if len(df) > 0:
            print(df.head(3).to_string(index=False))
    except Exception as e:
        print(f"  ❌ FAILED: {type(e).__name__}: {str(e)[:200]}")


# Q_nifty_history
run_test("Q_nifty_history (5-year NIFTY index)", """
    SELECT date, close
    FROM nifty_index
    WHERE date >= CURRENT_DATE - (:years_back * INTERVAL '1 year')
    ORDER BY date;
""", {"years_back": 5})

# Q_sector_performance_ytd
run_test("Q_sector_performance_ytd", """
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
        ROUND(AVG((l.price_now - y.price_then) / y.price_then * 100)::numeric, 2) AS avg_ytd_return_pct
    FROM stocks s
    JOIN ytd_start y ON y.ticker = s.ticker
    JOIN latest l ON l.ticker = s.ticker
    GROUP BY s.sector
    ORDER BY avg_ytd_return_pct DESC;
""")

# Q_top_gainers (1-year)
run_test("Q_top_gainers (1-year, top 5)", """
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
        ROUND(((l.price_now - sp.price_then) / sp.price_then * 100)::numeric, 2) AS return_pct
    FROM stocks s
    JOIN start_prices sp ON sp.ticker = s.ticker
    JOIN latest l ON l.ticker = s.ticker
    ORDER BY return_pct DESC
    LIMIT :limit_n;
""", {"days_back": 365, "limit_n": 5})

# Q_stock_price_history
run_test("Q_stock_price_history (RELIANCE.NS)", """
    SELECT date, open, high, low, close, adj_close, volume
    FROM prices_daily
    WHERE ticker = :ticker
    ORDER BY date;
""", {"ticker": "RELIANCE.NS"})

# Q_stock_key_metrics
run_test("Q_stock_key_metrics (RELIANCE.NS)", """
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
        m.latest_price,
        m.current_vol_60d,
        m.current_sharpe_60d,
        m.worst_drawdown,
        m.current_drawdown
    FROM metrics m
    JOIN stocks s ON s.ticker = m.ticker;
""", {"ticker": "RELIANCE.NS"})

# Q_portfolio_metrics via stored function
run_test("Q_portfolio_metrics (50/50 RELIANCE/TCS, 1yr)", """
    SELECT * FROM sp_portfolio_metrics(
        :tickers,
        :weights,
        :start_date,
        :end_date
    );
""", {
    "tickers": ["RELIANCE.NS", "TCS.NS"],
    "weights": [0.5, 0.5],
    "start_date": "2025-04-17",
    "end_date": "2026-04-15",
})

# Q_latest_prediction_for_ticker
run_test("Q_latest_prediction_for_ticker (RELIANCE.NS)", """
    SELECT
        ticker, company_name, sector, date,
        predicted_label, confidence_tier,
        ROUND(confidence::numeric, 3) AS confidence
    FROM latest_predictions
    WHERE ticker = :ticker;
""", {"ticker": "RELIANCE.NS"})

# Q_predictions_heatmap_all_tickers
run_test("Q_predictions_heatmap_all_tickers", """
    SELECT ticker, sector, predicted_label, confidence
    FROM latest_predictions
    ORDER BY sector, ticker;
""")

# Q_model_accuracy_over_time
run_test("Q_model_accuracy_over_time", """
    SELECT date, accuracy, n_predictions
    FROM accuracy_by_date
    ORDER BY date;
""")

# Q_ticker_prediction_history
run_test("Q_ticker_prediction_history (RELIANCE.NS, last 60)", """
    SELECT
        date, actual_label, predicted_label,
        ROUND(confidence::numeric, 3) AS confidence, correct
    FROM predictions_enriched
    WHERE ticker = :ticker
    ORDER BY date DESC
    LIMIT 60;
""", {"ticker": "RELIANCE.NS"})

print("\n✅ Dashboard query smoke tests complete.")