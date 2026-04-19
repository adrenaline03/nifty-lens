"""
Day 4: Train XGBoost volatility regime classifier.

Uses time-based train/test split (no random shuffling).
Evaluates with accuracy, per-class precision/recall, and confusion matrix.
Also compares against Logistic Regression baseline.

Outputs:
- models/xgboost_volatility.pkl: trained XGBoost model
- models/scaler.pkl: fitted StandardScaler (for LR baseline reproducibility)
- Printed evaluation report
"""
from pathlib import Path
import pickle
from dotenv import load_dotenv
import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, ConfusionMatrixDisplay
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
  "rsi_14", "macd", "macd_signal", "macd_diff", "volume_ratio"
]

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

def load_features() -> pd.DataFrame:
  """Load ml_features, cast types, sort by date."""
  df = pd.read_sql(
    "SELECT * FROM ml_features WHERE regime IS NOT NULL ORDER BY date, ticker",
    engine
  )

  for col in FEATURE_COLS + ["abs_return_next"]:
    df[col] = df[col].astype(float)

  df["regime"] = df["regime"].astype(int)
  df["date"] = pd.to_datetime(df["date"])
  return df

def time_based_split(df: pd.DataFrame, test_months: int = 12):
  """
  Split data chronologically: everything before (latest_date - test_months) is train; after is test.
  """
  latest = df["date"].max()
  cutoff = latest - pd.Timedelta(days=30 * test_months)
  train = df[df["date"] < cutoff].copy()
  test = df[df["date"] > cutoff].copy()
  return train, test

def baseline_logistic_regression(X_train, y_train, X_test, y_test):
  """Fit a vanilla LR and report accuracy."""
  scaler = StandardScaler()
  X_train_scaled = scaler.fit_transform(X_train)
  X_test_scaled = scaler.transform(X_test)

  lr = LogisticRegression(
    max_iter=1000,
    solver='lbfgs',
    random_state=42
  )
  lr.fit(X_train_scaled, y_train)
  y_pred = lr.predict(X_test_scaled)
  acc = accuracy_score(y_test, y_pred)

  print(f"  Logistic Regression accuracy: {acc:.4f}")

  return lr, scaler, acc

def train_xgboost(X_train, y_train, X_test, y_test):
  """Train XGBoost with reasonable defaults."""
  model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='multi:softprob',
    num_class=3,
    random_state=42,
    n_jobs=-1,
    eval_metric='mlogloss',
  )
  model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False,
  )
  y_pred = model.predict(X_test)
  acc = accuracy_score(y_test, y_pred)
  print(f"  XGBoost accuracy: {acc:.4f}")

  return model, acc

def evaluate(model, X_test, y_test, model_name: str):
  """Print full classification report + confusion matrix."""
  y_pred = model.predict(X_test)
  print(f"\n{model_name} Classification Report:")
  print(classification_report(
    y_test, y_pred, 
    target_names=["low", "medium", "high"],
    digits=4
  ))
  cm = confusion_matrix(y_test, y_pred)
  print("Confusion matrix (rows = actual, cols = predicted):")
  print(f"            pred_low  pred_med  pred_high")
  print(f"  actual_low  {cm[0][0]:6d}   {cm[0][1]:6d}    {cm[0][2]:6d}")
  print(f"  actual_med  {cm[1][0]:6d}   {cm[1][1]:6d}    {cm[1][2]:6d}")
  print(f"  actual_high {cm[2][0]:6d}   {cm[2][1]:6d}    {cm[2][2]:6d}")  

  return cm

def feature_importance(xgb_model):
  """Print XGBoost feature importance ranking."""
  importances = xgb_model.feature_importances_
  ranked = sorted(
    zip(FEATURE_COLS, importances),
    key=lambda x: x[1],
    reverse=True,
  )
  print("\nXGBoost Feature Importances:")
  for feature, importance in ranked:
    bar = "█" * int(importance * 200)
    print(f"  {feature:15s} {importance:.4f}  {bar}")

def time_series_cv_check(X, y, n_splits=3):
  """Quick sanity check that our features are stably predictive across folds."""
  tscv = TimeSeriesSplit(n_splits=n_splits)
  fold_accs = []
  for fold, (tr_idx, te_idx) in enumerate(tscv.split(X), 1):
    X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
    y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]
    m = xgb.XGBClassifier(
      n_estimators=200, 
      max_depth=5,
      learning_rate=0.05,
      objective='multi:softprob',
      num_class=3,
      random_state=42,
      n_jobs=-1,
      eval_metric='mlogloss',
    )
    m.fit(X_tr, y_tr, verbose=False)
    acc = accuracy_score(y_te, m.predict(X_te))
    fold_accs.append(acc)
    print(f"  Fold {fold}: train size={len(tr_idx):,}, test size={len(te_idx):,}, accuracy={acc:.4f}")
  print(f"  Mean CV accuracy: {np.mean(fold_accs):.4f} (±{np.std(fold_accs):.4f})")

  return fold_accs

def main():
  print("NIFTY-LENS: VOLATILITY REGIME CLASSIFIER")

  print("\nLoading features...")
  df = load_features()
  print(f"  {len(df):,} rows, {df['ticker'].nunique()} tickers")
  print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")

  print("\nSplitting train/test (time-based, 12-month test set)...")
  train, test = time_based_split(df, test_months=12)
  print(f"  Train: {len(train):,} rows ({train['date'].min().date()} → {train['date'].max().date()})")
  print(f"  Test:  {len(test):,} rows ({test['date'].min().date()} → {test['date'].max().date()})")

  X_train = train[FEATURE_COLS]
  y_train = train["regime"]
  X_test = test[FEATURE_COLS]
  y_test = test["regime"]

  print("WALK-FORWARD CV ON TRAINING SET (3 folds)")
  time_series_cv_check(X_train, y_train, n_splits=3)

  print("BASELINE: LOGISTIC REGRESSION")
  lr, scaler, lr_acc = baseline_logistic_regression(X_train, y_train, X_test, y_test)

  print("MODEL: XGBOOST")
  xgb_model, xgb_acc = train_xgboost(X_train, y_train, X_test, y_test)

  print("EVALUATION")
  evaluate(lr, scaler.transform(X_test), y_test, "Logistic Regression")
  evaluate(xgb_model, X_test, y_test, "XGBoost")

  feature_importance(xgb_model)

  print("SUMMARY")
  print(f"  Random baseline:       33.33%")
  print(f"  Logistic Regression:   {lr_acc * 100:.2f}%")
  print(f"  XGBoost:               {xgb_acc * 100:.2f}%")
  print(f"  XGBoost improvement:   +{(xgb_acc - lr_acc) * 100:.2f} pp over LR")

  with open(MODELS_DIR / "xgboost_volatility.pkl", "wb") as f:
    pickle.dump(xgb_model, f)
  with open(MODELS_DIR / "scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)
  print(f"\n✅ Model saved to {MODELS_DIR / 'xgboost_volatility.pkl'}")


if __name__ == "__main__":
  main()