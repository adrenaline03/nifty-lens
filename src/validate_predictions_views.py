"""
Day 5 Phase 2: Validate predictions-related views.
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


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


with engine.connect() as conn:
    section("latest_predictions: top 10 by confidence")
    df = pd.read_sql(text("""
        SELECT ticker, sector, date, predicted_label, confidence_tier,
               ROUND(confidence::numeric, 3) AS confidence
        FROM latest_predictions
        ORDER BY confidence DESC
        LIMIT 10;
    """), conn)
    print(df.to_string(index=False))

    section("accuracy_by_sector")
    df = pd.read_sql(text("SELECT * FROM accuracy_by_sector;"), conn)
    print(df.to_string(index=False))

    section("accuracy_by_confidence_tier (calibration check)")
    df = pd.read_sql(text("SELECT * FROM accuracy_by_confidence_tier;"), conn)
    print(df.to_string(index=False))
    print("\n  Expected: accuracy should increase monotonically with confidence bucket")

    section("accuracy_by_ticker: best 5 and worst 5")
    df = pd.read_sql(text("""
        (SELECT ticker, sector, accuracy FROM accuracy_by_ticker
         ORDER BY accuracy DESC LIMIT 5)
        UNION ALL
        (SELECT ticker, sector, accuracy FROM accuracy_by_ticker
         ORDER BY accuracy ASC LIMIT 5);
    """), conn)
    print(df.to_string(index=False))

    section("confusion_matrix")
    df = pd.read_sql(text("""
        SELECT actual_label, predicted_label, n
        FROM confusion_matrix
        ORDER BY actual_regime, predicted_regime;
    """), conn)
    print(df.to_string(index=False))

    section("accuracy_by_date: last 10 days")
    df = pd.read_sql(text("""
        SELECT * FROM accuracy_by_date
        ORDER BY date DESC LIMIT 10;
    """), conn)
    print(df.to_string(index=False))

print("\n✅ Predictions views validation complete.")