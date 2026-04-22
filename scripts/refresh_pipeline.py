"""
Nightly refresh pipeline for Nifty-Lens.

Runs the full data-to-predictions pipeline in order:
1. Ingest latest NIFTY 50 price data from yfinance
2. Ingest latest NIFTY 50 index data
3. Refresh materialized views (vol, sharpe, drawdown, correlation)
4. Recompute ML features
5. Regenerate predictions using the persisted model

Each step is idempotent — safe to re-run.

Usage:
    python scripts/refresh_pipeline.py           # full refresh
    python scripts/refresh_pipeline.py --skip-ingest   # skip data ingestion
    python scripts/refresh_pipeline.py --skip-ml       # skip feature/prediction rebuild
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def run_step(label: str, cmd: list[str]) -> bool:
  """Run a subcommand, return True on success."""
  print(f"  {label}")
  start = time.time()
  result = subprocess.run(cmd, cwd=PROJECT_ROOT, shell=False)
  elapsed = time.time() - start
  if result.returncode == 0:
    print(f"\n✅ {label} completed in {elapsed:.1f}s")
    return True
  else:
    print(f"\n❌ {label} failed (exit code {result.returncode}) after {elapsed:.1f}s")
    return False
  
def main():
  parser = argparse.ArgumentParser(description="Refresh the full Nifty-Lens pipeline.")
  parser.add_argument("--skip-ingest", action="store_true", help="Skip yfinance data ingestion (use existing data).")
  parser.add_argument("--skip-ml", action="store_true", help="Skip feature recomputation and predictions.")
  args = parser.parse_args()

  python = sys.executable
  total_start = time.time()

  steps = []
  # Step 1: Data ingestion (prices + index)
  if not args.skip_ingest:
    steps.append(("1. Ingest NIFTY 50 stock prices", [python, "src/ingest_prices.py"]))
    steps.append(("2. Ingest NIFTY 50 index", [python, "src/ingest_index.py"]))
  else:
    print("⏭  Skipping data ingestion (--skip-ingest)")

  # Step 2: Refresh materialized views (returns/vol/sharpe/drawdown/correlation)
  steps.append(("3. Refresh materialized views", [python, "apply_views.py", "sql/refresh_views.sql"]))

  # Step 3: ML feature recomputation and predictions
  if not args.skip_ml:
    steps.append(("4. Recompute ML features", [python, "src/features.py"]))
    steps.append(("5. Regenerate predictions", [python, "src/evaluate_model.py"]))
    # Also refresh the prediction views (they depend on ml_predictions)
    steps.append(("6. Refresh prediction views", [python, "apply_views.py", "sql/predictions_views.sql"]))
  else:
    print("⏭  Skipping ML recomputation (--skip-ml)")

  # Execute
  failed = []
  for label, cmd in steps:
    ok = run_step(label, cmd)
    if not ok:
      failed.append(label)
      print(f"\n⚠️  Aborting pipeline due to failure in: {label}")
      break

  # Summary
  total_elapsed = time.time() - total_start
  print(f"\n{'=' * 60}")
  print(f"  PIPELINE SUMMARY")
  print(f"{'=' * 60}")
  print(f"  Total time: {total_elapsed:.1f}s")
  print(f"  Steps completed: {len(steps) - len(failed)}/{len(steps)}")
  if failed:
    print(f"  Failed: {failed}")
    sys.exit(1)
  else:
    print(f"  ✅ All steps succeeded.")


if __name__ == "__main__":
  main()