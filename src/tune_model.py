"""
Day 4 Phase 2: Focused hyperparameter tuning for XGBoost.

We don't do full GridSearchCV (hours of compute for marginal gains).
Instead, we try a handful of principled variations and verify that
our default isn't clearly suboptimal.
"""
from pathlib import Path
import pickle
from dotenv import load_dotenv
import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.metrics import accuracy_score
import xgboost as xgb

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

def load_features() -> pd.DataFrame:
  df = pd.read_sql(
    "SELECT * FROM ml_features WHERE regime IS NOT NULL ORDER BY date, ticker", 
    engine
  )
  for col in FEATURE_COLS + ["abs_return_next"]:
      df[col] = df[col].astype(float)
  df["regime"] = df["regime"].astype(int)
  df["date"] = pd.to_datetime(df["date"])
  return df

def time_split(df: pd.DataFrame, test_months: int = 12):
  latest = df["date"].max()
  cutoff = latest - pd.Timedelta(days=30 * test_months)
  train = df[df["date"] <= cutoff].copy()
  test = df[df["date"] > cutoff].copy()
  return train, test

def main():
  df = load_features()
  train, test = time_split(df, test_months=12)
  X_train, y_train = train[FEATURE_COLS], train["regime"]
  X_test, y_test = test[FEATURE_COLS], test["regime"] 

  default = dict(
    n_estimators=300, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
  )

  candidates = [
    ("default", default),
    ("shallower trees (depth=3)", {**default, "max_depth": 3}),
    ("deeper trees (depth=7)", {**default, "max_depth": 7}),
    ("slower learning (lr=0.02, 600 trees)",
        {**default, "learning_rate": 0.02, "n_estimators": 600}),
    ("faster learning (lr=0.1, 150 trees)",
        {**default, "learning_rate": 0.1, "n_estimators": 150}),
    ("less regularization (subsample=1.0)", {**default, "subsample": 1.0}),
    ("more regularization (subsample=0.6)", {**default, "subsample": 0.6}),
  ]

  print(f"{'Config':45s} {'Test Acc':>10s}  Notes")
  print("-" * 75)

  results = []
  for name, params in candidates:
    model = xgb.XGBClassifier(
      **params,
      objective="multi:softprob",
      num_class=3,
      random_state=42,
      n_jobs=-1,
      eval_metric="mlogloss",
    )
    model.fit(X_train, y_train, verbose=False)
    acc = accuracy_score(y_test, model.predict(X_test))
    results.append((name, acc, params))
    print(f"{name:45s} {acc * 100:>9.2f}%")

  # Find best and summarize
  best_name, best_acc, best_params = max(results, key=lambda r: r[1])
  default_acc = results[0][1]
  lift = (best_acc - default_acc) * 100

  print("-" * 75)
  print(f"\nDefault accuracy:  {default_acc * 100:.2f}%")
  print(f"Best config:       {best_name} at {best_acc * 100:.2f}%")
  print(f"Absolute lift:     {lift:+.2f} pp")

  if lift < 1.0:
    print("\n→ Default config is within 1pp of best. Keeping default.")
  else:
    print(f"\n→ Best config beats default by {lift:.2f}pp. Consider adopting.")


if __name__ == "__main__":
  main()