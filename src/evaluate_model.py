"""
Day 4 Phase 3: Final model evaluation and artifact generation.

Produces:
- ml_predictions table in Postgres (test set predictions + probabilities)
- notebooks/plots/confusion_matrix.png
- notebooks/plots/feature_importance.png
- notebooks/plots/prediction_accuracy_by_date.png
"""
from pathlib import Path
import pickle
from dotenv import load_dotenv
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
from sklearn.metrics import confusion_matrix, accuracy_score

load_dotenv()
connection_string = (
    f"postgresql://{os.getenv('NEON_USER')}:{os.getenv('NEON_PASSWORD')}"
    f"@{os.getenv('NEON_HOST')}:{os.getenv('NEON_PORT')}"
    f"/{os.getenv('NEON_DATABASE')}?sslmode=require"
)
engine = create_engine(connection_string)

FEATURE_COLS = [
    "ret_1d", "ret_5d", "ret_20d",
    "vol_5d", "vol_20d", "bb_width", "atr_14",
    "rsi_14", "macd", "macd_signal", "macd_diff",
    "volume_ratio",
]

MODELS_DIR = Path("models")
PLOTS_DIR = Path("notebooks/plots")
PLOTS_DIR.mkdir(exist_ok=True, parents=True)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120


def load_test_set():
    df = pd.read_sql(
        "SELECT * FROM ml_features WHERE regime IS NOT NULL ORDER BY date, ticker",
        engine,
    )
    for col in FEATURE_COLS + ["abs_return_next"]:
        df[col] = df[col].astype(float)
    df["regime"] = df["regime"].astype(int)
    df["date"] = pd.to_datetime(df["date"])

    latest = df["date"].max()
    cutoff = latest - pd.Timedelta(days=30 * 12)
    test = df[df["date"] > cutoff].copy()
    return test


def generate_predictions(test: pd.DataFrame, model):
    """Run model on test set and build predictions DataFrame."""
    X_test = test[FEATURE_COLS]
    predictions = model.predict(X_test)
    probas = model.predict_proba(X_test)

    df_pred = pd.DataFrame({
        "ticker": test["ticker"].values,
        "date": test["date"].dt.date.values,
        "actual_regime": test["regime"].values,
        "predicted_regime": predictions,
        "prob_low": probas[:, 0],
        "prob_medium": probas[:, 1],
        "prob_high": probas[:, 2],
        "correct": predictions == test["regime"].values,
    })
    # Confidence = max probability
    df_pred["confidence"] = probas.max(axis=1)
    return df_pred


def persist_predictions(df: pd.DataFrame):
    """Write predictions to ml_predictions table."""
    create_sql = """
    DROP TABLE IF EXISTS ml_predictions CASCADE;

    CREATE TABLE ml_predictions (
        ticker            VARCHAR(20) NOT NULL,
        date              DATE NOT NULL,
        actual_regime     SMALLINT,
        predicted_regime  SMALLINT NOT NULL,
        prob_low          NUMERIC(6, 4),
        prob_medium       NUMERIC(6, 4),
        prob_high         NUMERIC(6, 4),
        confidence        NUMERIC(6, 4),
        correct           BOOLEAN,
        PRIMARY KEY (ticker, date)
    );

    CREATE INDEX idx_ml_predictions_date ON ml_predictions(date);
    CREATE INDEX idx_ml_predictions_ticker_date ON ml_predictions(ticker, date DESC);
    """

    with engine.begin() as conn:
        for stmt in create_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))

    # Only write the columns that exist in the table — drop conf_bucket
    table_cols = [
        "ticker", "date", "actual_regime", "predicted_regime",
        "prob_low", "prob_medium", "prob_high", "confidence", "correct",
    ]
    df_to_write = df[table_cols].copy()

    df_to_write.to_sql(
        name="ml_predictions",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM ml_predictions")).scalar()
    print(f"  ✅ ml_predictions now has {count:,} rows.")
    
def plot_confusion_matrix(df_pred: pd.DataFrame):
    cm = confusion_matrix(df_pred["actual_regime"], df_pred["predicted_regime"])
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    labels = ["Low", "Medium", "High"]

    # Absolute counts
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues", ax=axes[0],
        xticklabels=labels, yticklabels=labels, cbar=False,
    )
    axes[0].set_xlabel("Predicted")
    axes[0].set_ylabel("Actual")
    axes[0].set_title("Confusion matrix (counts)")

    # Normalized (recall per class)
    sns.heatmap(
        cm_norm, annot=True, fmt=".2%", cmap="Blues", ax=axes[1],
        xticklabels=labels, yticklabels=labels, cbar=False,
        vmin=0, vmax=1,
    )
    axes[1].set_xlabel("Predicted")
    axes[1].set_ylabel("Actual")
    axes[1].set_title("Confusion matrix (row-normalized = recall)")

    plt.suptitle(f"XGBoost Volatility Classifier — 67.80% accuracy",
                 y=1.02, fontsize=13)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "confusion_matrix.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved {PLOTS_DIR / 'confusion_matrix.png'}")


def plot_feature_importance(model):
    importances = model.feature_importances_
    ranked = sorted(zip(FEATURE_COLS, importances), key=lambda x: x[1], reverse=True)
    feats, imps = zip(*ranked)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(feats[::-1], imps[::-1], color="steelblue")
    # Highlight top feature
    bars[-1].set_color("#d9534f")
    ax.set_xlabel("Importance")
    ax.set_title("XGBoost Feature Importance")
    for bar, val in zip(bars, imps[::-1]):
        ax.text(val + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "feature_importance.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved {PLOTS_DIR / 'feature_importance.png'}")


def plot_accuracy_by_date(df_pred: pd.DataFrame):
    """Daily accuracy over the test period — does the model degrade over time?"""
    df = df_pred.copy()
    df["date"] = pd.to_datetime(df["date"])
    daily = df.groupby("date").agg(
        accuracy=("correct", "mean"),
        n=("correct", "count"),
    ).reset_index()

    # Rolling 20-day avg accuracy for smoother line
    daily["rolling_acc"] = daily["accuracy"].rolling(20).mean()

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(daily["date"], daily["accuracy"], alpha=0.25, color="gray",
            label="Daily accuracy")
    ax.plot(daily["date"], daily["rolling_acc"], linewidth=2, color="steelblue",
            label="20-day rolling avg")
    ax.axhline(y=0.678, linestyle="--", color="#d9534f",
               label="Overall test accuracy (67.8%)")
    ax.axhline(y=0.333, linestyle=":", color="black", alpha=0.5,
               label="Random baseline (33.3%)")

    ax.set_ylabel("Accuracy")
    ax.set_xlabel("Date")
    ax.set_title("Model accuracy over time (test period)")
    ax.legend(loc="lower right")
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "accuracy_over_time.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved {PLOTS_DIR / 'accuracy_over_time.png'}")


def main():
    print("=" * 60)
    print("FINAL MODEL EVALUATION")
    print("=" * 60)

    # Load model
    with open(MODELS_DIR / "xgboost_volatility.pkl", "rb") as f:
        model = pickle.load(f)
    print(f"\nLoaded model from {MODELS_DIR / 'xgboost_volatility.pkl'}")

    # Load test set
    test = load_test_set()
    print(f"Test set: {len(test):,} rows ({test['date'].min().date()} → {test['date'].max().date()})")

    # Generate predictions
    print("\nGenerating predictions...")
    df_pred = generate_predictions(test, model)
    acc = df_pred["correct"].mean()
    print(f"  Overall accuracy: {acc * 100:.2f}%")

    # Per-class breakdown
    print("\nPer-class recall:")
    for regime_val, label in [(0, "Low"), (1, "Medium"), (2, "High")]:
        mask = df_pred["actual_regime"] == regime_val
        class_acc = df_pred.loc[mask, "correct"].mean()
        n = mask.sum()
        print(f"  {label:8s}: {class_acc * 100:.2f}% ({n:,} test examples)")

    # Confidence analysis
    print("\nAccuracy by confidence tier:")
    df_pred["conf_bucket"] = pd.cut(
        df_pred["confidence"],
        bins=[0, 0.4, 0.5, 0.6, 0.7, 1.0],
        labels=["<40%", "40-50%", "50-60%", "60-70%", ">70%"],
    )
    conf_acc = df_pred.groupby("conf_bucket", observed=True).agg(
        accuracy=("correct", "mean"),
        n=("correct", "count"),
    )
    for idx, row in conf_acc.iterrows():
        print(f"  Confidence {idx:8s}: {row['accuracy'] * 100:.2f}% ({row['n']:,} predictions)")

    # Persist to Postgres
    print("\nPersisting predictions to Postgres...")
    persist_predictions(df_pred)

    # Generate plots
    print("\nGenerating plots...")
    plot_confusion_matrix(df_pred)
    plot_feature_importance(model)
    plot_accuracy_by_date(df_pred)

    print("\n✅ Final evaluation complete.")


if __name__ == "__main__":
    main()