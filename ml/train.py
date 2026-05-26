"""
train.py
========
BhoomiSense training pipeline. Trains THREE models, each on its own feature set:

  flood_model      -> calibrated ensemble classifier on FLOOD_FEATURES
  landslide_model  -> calibrated ensemble classifier on LANDSLIDE_FEATURES
  severity_model   -> ensemble regressor on SEVERITY_FEATURES

Each classifier: median imputation -> RandomizedSearchCV-tuned XGBoost & LightGBM
-> soft-voting ensemble with RandomForest -> isotonic probability calibration
-> evaluation (ROC-AUC / F1 / confusion matrix) -> SHAP importances -> joblib.

Run:
    python generate_synthetic_data.py     # or: python build_real_dataset.py ...
    python train.py
"""

from __future__ import annotations
import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor,
                              VotingClassifier, VotingRegressor)
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             mean_absolute_error, r2_score, roc_auc_score)
from sklearn.model_selection import (RandomizedSearchCV, StratifiedKFold,
                                     train_test_split)
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier, XGBRegressor
from lightgbm import LGBMClassifier, LGBMRegressor

from feature_engineering import (FLOOD_FEATURES, LANDSLIDE_FEATURES,
                                 SEVERITY_FEATURES, get_flood_matrix,
                                 get_landslide_matrix, get_severity_matrix)

warnings.filterwarnings("ignore")
MODELS_DIR, DATA_PATH, RANDOM_STATE = "models", "data/training_data.csv", 42

XGB_SPACE = {"n_estimators": [200, 350, 500], "max_depth": [3, 4, 5, 6],
             "learning_rate": [0.02, 0.05, 0.1], "subsample": [0.7, 0.85, 1.0],
             "colsample_bytree": [0.7, 0.85, 1.0]}
LGBM_SPACE = {"n_estimators": [200, 350, 500], "num_leaves": [15, 31, 63],
              "learning_rate": [0.02, 0.05, 0.1], "subsample": [0.7, 0.85, 1.0]}


def _tune(estimator, space, X, y, n_iter=12):
    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
    search = RandomizedSearchCV(estimator, space, n_iter=n_iter,
                                scoring="roc_auc", cv=cv, n_jobs=-1,
                                random_state=RANDOM_STATE)
    search.fit(X, y)
    return search.best_estimator_, search.best_params_


def train_hazard_model(df, target, feature_cols, matrix_fn) -> dict:
    """Train one calibrated ensemble classifier for a hazard."""
    print(f"\n{'='*60}\nTraining: {target}  ({len(feature_cols)} features)\n{'='*60}")
    X = matrix_fn(df)
    y = df[target].astype(int)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)

    imp = SimpleImputer(strategy="median")
    X_tr_i = pd.DataFrame(imp.fit_transform(X_tr), columns=feature_cols)

    print("  Tuning XGBoost ...")
    xgb, xgb_p = _tune(XGBClassifier(eval_metric="logloss",
                                     random_state=RANDOM_STATE),
                       XGB_SPACE, X_tr_i, y_tr)
    print("  Tuning LightGBM ...")
    lgbm, lgbm_p = _tune(LGBMClassifier(random_state=RANDOM_STATE, verbose=-1),
                         LGBM_SPACE, X_tr_i, y_tr)

    rf = RandomForestClassifier(n_estimators=90, max_depth=9, n_jobs=-1,
                                random_state=RANDOM_STATE)
    ensemble = VotingClassifier(
        estimators=[("xgb", xgb), ("lgbm", lgbm), ("rf", rf)],
        voting="soft", weights=[2, 2, 1], n_jobs=-1)

    print("  Calibrating ensemble ...")
    model = Pipeline([("imputer", SimpleImputer(strategy="median")),
                      ("clf", CalibratedClassifierCV(ensemble,
                                                     method="isotonic", cv=3))])
    model.fit(X_tr, y_tr)

    proba = model.predict_proba(X_te)[:, 1]
    preds = (proba >= 0.5).astype(int)
    cm = confusion_matrix(y_te, preds)
    metrics = {"roc_auc": round(float(roc_auc_score(y_te, proba)), 4),
               "f1": round(float(f1_score(y_te, preds)), 4),
               "accuracy": round(float(accuracy_score(y_te, preds)), 4),
               "confusion_matrix": cm.tolist()}
    print(f"  ROC-AUC={metrics['roc_auc']}  F1={metrics['f1']}  "
          f"Acc={metrics['accuracy']}")

    importances = _shap_importances(xgb, X_tr_i, feature_cols)
    name = target.replace("_label", "")
    joblib.dump(model, os.path.join(MODELS_DIR, f"{name}_model.joblib"),
                compress=3)
    return {"metrics": metrics, "feature_importance": importances,
            "features": feature_cols, "xgb_params": xgb_p, "lgbm_params": lgbm_p}


def train_severity_model(df) -> dict:
    print(f"\n{'='*60}\nTraining: severity regressor\n{'='*60}")
    X = get_severity_matrix(df)
    y = df["severity_score"].astype(float)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                              random_state=RANDOM_STATE)
    ensemble = VotingRegressor([
        ("xgb", XGBRegressor(n_estimators=350, max_depth=5, learning_rate=0.05,
                             subsample=0.85, random_state=RANDOM_STATE)),
        ("lgbm", LGBMRegressor(n_estimators=350, learning_rate=0.05,
                               random_state=RANDOM_STATE, verbose=-1)),
        ("rf", RandomForestRegressor(n_estimators=90, max_depth=9, n_jobs=-1,
                                     random_state=RANDOM_STATE))])
    model = Pipeline([("imputer", SimpleImputer(strategy="median")),
                      ("reg", ensemble)])
    model.fit(X_tr, y_tr)
    preds = model.predict(X_te)
    metrics = {"mae": round(float(mean_absolute_error(y_te, preds)), 3),
               "r2": round(float(r2_score(y_te, preds)), 4)}
    print(f"  MAE={metrics['mae']}  R2={metrics['r2']}")
    joblib.dump(model, os.path.join(MODELS_DIR, "severity_model.joblib"),
                compress=3)
    return {"metrics": metrics, "features": SEVERITY_FEATURES}


def _shap_importances(tree_model, X, cols) -> dict:
    """Normalized mean |SHAP| per feature; falls back to gain importances."""
    try:
        import shap
        sv = shap.TreeExplainer(tree_model).shap_values(
            X.sample(min(1000, len(X)), random_state=RANDOM_STATE))
        if isinstance(sv, list):
            sv = sv[-1]
        mean_abs = np.abs(sv).mean(axis=0)
    except Exception as e:
        print(f"  [warn] SHAP fallback: {e}")
        mean_abs = getattr(tree_model, "feature_importances_", np.ones(len(cols)))
    total = mean_abs.sum() or 1.0
    return {f: round(float(v / total), 4)
            for f, v in sorted(zip(cols, mean_abs), key=lambda kv: -kv[1])}


def main() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(DATA_PATH):
        raise SystemExit(f"{DATA_PATH} missing. Run generate_synthetic_data.py "
                         "or build_real_dataset.py first.")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df):,} rows")

    flood = train_hazard_model(df, "flood_label", FLOOD_FEATURES,
                               get_flood_matrix)
    landslide = train_hazard_model(df, "landslide_label", LANDSLIDE_FEATURES,
                                   get_landslide_matrix)
    severity = train_severity_model(df)

    with open(os.path.join(MODELS_DIR, "metadata.json"), "w") as fh:
        json.dump({"models": {"flood": flood, "landslide": landslide,
                              "severity": severity},
                   "note": "Metrics reflect the training data used; with "
                           "synthetic data they are NOT real-world accuracy."},
                  fh, indent=2)
    print(f"\nSaved models + metadata.json to ./{MODELS_DIR}/")


if __name__ == "__main__":
    main()
