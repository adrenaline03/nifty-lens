-- =====================================================
-- Nifty-Lens: Core schema
-- =====================================================

DROP TABLE IF EXISTS prices_daily CASCADE;
DROP TABLE IF EXISTS nifty_index CASCADE;
DROP TABLE IF EXISTS stocks CASCADE;

CREATE TABLE stocks (
    ticker          VARCHAR(20) PRIMARY KEY,
    company_name    VARCHAR(200) NOT NULL,
    sector          VARCHAR(100),
    industry        VARCHAR(100),
    added_to_nifty  DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prices_daily (
    ticker          VARCHAR(20) NOT NULL,
    date            DATE NOT NULL,
    open            NUMERIC(12, 4),
    high            NUMERIC(12, 4),
    low             NUMERIC(12, 4),
    close           NUMERIC(12, 4) NOT NULL,
    adj_close       NUMERIC(12, 4),
    volume          BIGINT,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE
);

CREATE INDEX idx_prices_daily_date ON prices_daily(date);
CREATE INDEX idx_prices_daily_ticker_date ON prices_daily(ticker, date DESC);

CREATE TABLE nifty_index (
    date            DATE PRIMARY KEY,
    open            NUMERIC(12, 4),
    high            NUMERIC(12, 4),
    low             NUMERIC(12, 4),
    close           NUMERIC(12, 4) NOT NULL,
    volume          BIGINT
);

CREATE INDEX idx_nifty_index_date ON nifty_index(date DESC);