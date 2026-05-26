"""
evaluate.py
===========
Loads the serialized models and produces a human-readable evaluation report
plus diagnostic plots (ROC curve, confusion matrix, calibration curve).
Run AFTER train.py.

    python evaluate.py

Outputs go to ./reports/.
"""

from __future__ import annotations
import json
import os

import joblib
import matplotlib
matplotlib.use("Agg")            # headless: no display needed
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import RocCurveDisplay, classification_report
from sklearn.model_selection import train_test_split

from feature_engineering import get_flood_matrix, get_landslide_matrix

REPORTS = "reports"
DATA_PATH = "data/training_data.csv"


def evaluate_hazard(name: str, target: str, df: pd.DataFrame) -> None:
    model = joblib.load(f"models/{name}_model.joblib")
    X = get_flood_matrix(df) if target == "flood_label" else get_landslide_matrix(df)
    y = df[target].astype(int)
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)

    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)

    print(f"\n=== {name.upper()} ===")
    print(classification_report(y_test, preds, digits=3))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    # ROC curve
    RocCurveDisplay.from_predictions(y_test, proba, ax=axes[0])
    axes[0].set_title(f"{name} — ROC curve")
    axes[0].plot([0, 1], [0, 1], "k--", lw=0.8)

    # Calibration curve — are the probabilities trustworthy?
    frac_pos, mean_pred = calibration_curve(y_test, proba, n_bins=10)
    axes[1].plot(mean_pred, frac_pos, "o-", label=name)
    axes[1].plot([0, 1], [0, 1], "k--", lw=0.8, label="perfectly calibrated")
    axes[1].set_xlabel("Predicted probability")
    axes[1].set_ylabel("Observed frequency")
    axes[1].set_title(f"{name} — calibration")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(f"{REPORTS}/{name}_evaluation.png", dpi=120)
    plt.close(fig)
    print(f"  plot -> {REPORTS}/{name}_evaluation.png")


def main() -> None:
    os.makedirs(REPORTS, exist_ok=True)
    df = pd.read_csv(DATA_PATH)

    evaluate_hazard("flood", "flood_label", df)
    evaluate_hazard("landslide", "landslide_label", df)

    # Feature-importance bar chart from training metadata
    meta = json.load(open("models/metadata.json"))
    for hazard in ("flood", "landslide"):
        imp = meta["models"][hazard]["feature_importance"]
        if not imp:
            continue
        items = list(imp.items())[:12]
        names, vals = zip(*items)
        plt.figure(figsize=(8, 5))
        plt.barh(list(reversed(names)), list(reversed(vals)), color="#38bdf8")
        plt.title(f"{hazard.title()} — SHAP feature importance")
        plt.xlabel("normalized mean |SHAP|")
        plt.tight_layout()
        plt.savefig(f"{REPORTS}/{hazard}_feature_importance.png", dpi=120)
        plt.close()
        print(f"  plot -> {REPORTS}/{hazard}_feature_importance.png")

    print("\nDone. See ./reports/")


if __name__ == "__main__":
    main()
