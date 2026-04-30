import time
import json
import warnings
import numpy as np
import pandas as pd
import joblib
import optuna

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_squared_error, r2_score, mean_absolute_error,
    accuracy_score, f1_score, roc_auc_score,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier,
    ExtraTreesRegressor, ExtraTreesClassifier,
)
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier

try:
    from xgboost import XGBRegressor, XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    from lightgbm import LGBMRegressor, LGBMClassifier
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False

from app.automl.core.config import settings
from app.automl.core.logging import get_logger
from app.automl.service.preprocessing_service import build_preprocessor, encode_target, infer_task

log = get_logger("training_service")
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")


# ─── Model quality labels ─────────────────────────────────────────────────────

def regression_quality(r2: float) -> str:
    if r2 < 0: return "poor"
    if r2 < 0.5: return "weak"
    if r2 < 0.8: return "good"
    return "excellent"


def classification_quality(f1: float) -> str:
    if f1 < 0.5: return "poor"
    if f1 < 0.7: return "weak"
    if f1 < 0.85: return "good"
    return "excellent"


# ─── Base candidates (no tuning) ─────────────────────────────────────────────

def get_base_candidates(task: str, random_state: int) -> dict:
    if task == "regression":
        candidates = {
            "LinearRegression": LinearRegression(),
            "DecisionTreeRegressor": DecisionTreeRegressor(random_state=random_state),
            "RandomForestRegressor": RandomForestRegressor(
                n_estimators=200, random_state=random_state, n_jobs=-1
            ),
            "GradientBoostingRegressor": GradientBoostingRegressor(
                n_estimators=100, learning_rate=0.1, random_state=random_state
            ),
            "ExtraTreesRegressor": ExtraTreesRegressor(
                n_estimators=200, random_state=random_state, n_jobs=-1
            ),
        }
        if HAS_XGB:
            candidates["XGBRegressor"] = XGBRegressor(
                n_estimators=200, learning_rate=0.05,
                random_state=random_state, verbosity=0, n_jobs=-1,
            )
        if HAS_LGBM:
            candidates["LGBMRegressor"] = LGBMRegressor(
                n_estimators=200, learning_rate=0.05,
                random_state=random_state, verbose=-1, n_jobs=-1,
            )
    else:
        candidates = {
            "LogisticRegression": LogisticRegression(
                max_iter=3000, class_weight="balanced"
            ),
            "DecisionTreeClassifier": DecisionTreeClassifier(
                random_state=random_state, class_weight="balanced"
            ),
            "RandomForestClassifier": RandomForestClassifier(
                n_estimators=200, random_state=random_state,
                class_weight="balanced", n_jobs=-1,
            ),
            "GradientBoostingClassifier": GradientBoostingClassifier(
                n_estimators=100, learning_rate=0.1, random_state=random_state
            ),
            "ExtraTreesClassifier": ExtraTreesClassifier(
                n_estimators=200, random_state=random_state,
                class_weight="balanced", n_jobs=-1,
            ),
        }
        if HAS_XGB:
            candidates["XGBClassifier"] = XGBClassifier(
                n_estimators=200, learning_rate=0.05,
                random_state=random_state, verbosity=0, n_jobs=-1,
                eval_metric="logloss", use_label_encoder=False,
            )
        if HAS_LGBM:
            candidates["LGBMClassifier"] = LGBMClassifier(
                n_estimators=200, learning_rate=0.05,
                random_state=random_state, verbose=-1, n_jobs=-1,
            )
    return candidates


# ─── Optuna tuning ────────────────────────────────────────────────────────────

def _optuna_objective(trial, preprocessor, X_train, y_train, task, random_state, cv_folds):
    model_name = trial.suggest_categorical(
        "model",
        (["XGBClassifier", "LGBMClassifier", "RandomForestClassifier", "GradientBoostingClassifier"]
         if task == "classification" else
         ["XGBRegressor", "LGBMRegressor", "RandomForestRegressor", "GradientBoostingRegressor"]),
    )

    if "XGB" in model_name:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 400),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "random_state": random_state,
            "verbosity": 0,
            "n_jobs": -1,
        }
        if task == "classification":
            params["eval_metric"] = "logloss"
            params["use_label_encoder"] = False
            model = XGBClassifier(**params) if HAS_XGB else None
        else:
            model = XGBRegressor(**params) if HAS_XGB else None

    elif "LGBM" in model_name:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 400),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 20, 150),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "random_state": random_state,
            "verbose": -1,
            "n_jobs": -1,
        }
        model = (LGBMClassifier(**params) if task == "classification"
                 else LGBMRegressor(**params)) if HAS_LGBM else None

    elif "RandomForest" in model_name:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 400),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
            "random_state": random_state,
            "n_jobs": -1,
        }
        if task == "classification":
            params["class_weight"] = "balanced"
            model = RandomForestClassifier(**params)
        else:
            model = RandomForestRegressor(**params)

    else:  # GradientBoosting
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "random_state": random_state,
        }
        model = (GradientBoostingClassifier(**params) if task == "classification"
                 else GradientBoostingRegressor(**params))

    if model is None:
        raise optuna.exceptions.TrialPruned()

    pipe = Pipeline([("preprocess", preprocessor), ("model", model)])
    scoring = "f1_weighted" if task == "classification" else "neg_root_mean_squared_error"

    try:
        scores = cross_val_score(pipe, X_train, y_train, cv=cv_folds, scoring=scoring, n_jobs=None)
        return float(np.mean(scores))
    except Exception:
        raise optuna.exceptions.TrialPruned()


def run_optuna(preprocessor, X_train, y_train, task, random_state, cv_folds, n_trials) -> dict:
    log.info(f"[optuna_start] task={task} n_trials={n_trials}")
    direction = "maximize"  # neg_rmse → maximize

    study = optuna.create_study(
        direction=direction,
        sampler=optuna.samplers.TPESampler(seed=random_state),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=3),
    )
    study.optimize(
        lambda trial: _optuna_objective(
            trial, preprocessor, X_train, y_train, task, random_state, cv_folds
        ),
        n_trials=n_trials,
        show_progress_bar=False,
    )

    best = study.best_trial
    log.info(f"[optuna_done] best_value={best.value} best_params={best.params}")
    return best.params


# ─── Metrics helpers ──────────────────────────────────────────────────────────

def _safe_roc_auc(y_true, y_prob, n_classes):
    try:
        if n_classes == 2:
            return float(roc_auc_score(y_true, y_prob[:, 1]))
        return float(roc_auc_score(y_true, y_prob, multi_class="ovr", average="weighted"))
    except Exception:
        return None


# ─── Feature importance ───────────────────────────────────────────────────────

def get_feature_importance(pipe: Pipeline, original_features: list[str]) -> dict:
    try:
        model = pipe.named_steps["model"]
        preprocessor = pipe.named_steps["preprocess"]

        if not hasattr(model, "feature_importances_"):
            if hasattr(model, "coef_"):
                coefs = np.abs(model.coef_).flatten()
                n = min(len(original_features), len(coefs))
                items = [
                    {"feature": original_features[i], "importance": round(float(coefs[i]), 6)}
                    for i in range(n)
                ]
                return {
                    "available": True,
                    "message": "Coefficients used (linear model)",
                    "items": sorted(items, key=lambda x: x["importance"], reverse=True),
                }
            return {"available": False, "message": "Feature importance not available for this model.", "items": []}

        transformed_names = preprocessor.get_feature_names_out()
        importances = model.feature_importances_
        grouped = {f: 0.0 for f in original_features}

        for name, imp in zip(transformed_names, importances):
            for feat in original_features:
                safe = feat.replace(" ", "_")
                if feat in name or safe in name or f"__{feat}" in name or f"__{safe}" in name:
                    grouped[feat] += float(imp)
                    break

        items = sorted(
            [{"feature": f, "importance": round(v, 6)} for f, v in grouped.items()],
            key=lambda x: x["importance"],
            reverse=True,
        )
        return {"available": True, "message": "Feature importance computed.", "items": items}
    except Exception as e:
        return {"available": False, "message": str(e), "items": []}


# ─── Recommendation ───────────────────────────────────────────────────────────

def build_recommendation(task: str, score: float) -> str:
    if task == "regression":
        if score < 0:
            return "Features are not informative. Add more relevant variables."
        if score < 0.5:
            return "Weak R². Try more features or better feature engineering."
        if score < 0.8:
            return "Good performance. Consider adding interaction features."
        return "Excellent R². Double-check for data leakage."
    else:
        if score < 0.5:
            return "Poor F1. Check class imbalance and feature quality."
        if score < 0.7:
            return "Weak F1. Add more discriminative features."
        if score < 0.85:
            return "Good F1. Fine-tune with Optuna for better results."
        return "Excellent classification performance."


# ─── Main train function ──────────────────────────────────────────────────────

def train(
    run_id: str,
    df: pd.DataFrame,
    target: str,
    features: list[str],
    task: str,
    test_size: float,
    random_state: int,
    cv_folds: int,
    use_optuna: bool,
    optuna_trials: int,
) -> dict:
    run_path = settings.runs_dir / run_id

    y = df[target]
    X = df[features]

    # Encode target if classification with strings
    y_encoded, label_encoder = encode_target(y) if task == "classification" else (y, None)

    stratify = y_encoded if task == "classification" and y_encoded.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=test_size, random_state=random_state, stratify=stratify
    )

    preprocessor = build_preprocessor(X_train)

    # ── Optuna phase ──
    best_params = None
    if use_optuna:
        try:
            best_params = run_optuna(
                preprocessor, X_train, y_train, task, random_state, cv_folds, optuna_trials
            )
        except Exception as e:
            log.warning(f"[optuna_failed] error={e}")
            best_params = None

    # ── Train all candidates ──
    candidates = get_base_candidates(task, random_state)
    scoring = "f1_weighted" if task == "classification" else "neg_root_mean_squared_error"

    results = []
    best = None

    for name, model in candidates.items():
        t0 = time.time()
        pipe = Pipeline([("preprocess", preprocessor), ("model", model)])

        try:
            cv_scores = cross_val_score(
                pipe, X_train, y_train, cv=cv_folds, scoring=scoring, n_jobs=None
            )
            pipe.fit(X_train, y_train)
            preds = pipe.predict(X_test)
            elapsed = round(time.time() - t0, 3)

            if task == "regression":
                rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
                r2 = float(r2_score(y_test, preds))
                mae = float(mean_absolute_error(y_test, preds))
                cv_mean = float(np.mean(cv_scores))  # neg_rmse
                score = cv_mean
                res = {
                    "model": name,
                    "rmse": round(rmse, 6),
                    "r2": round(r2, 6),
                    "mae": round(mae, 6),
                    "cv_rmse": round(abs(cv_mean), 6),
                    "training_time_sec": elapsed,
                    "model_quality": regression_quality(r2),
                    "error": None,
                }
            else:
                acc = float(accuracy_score(y_test, preds))
                f1 = float(f1_score(y_test, preds, average="weighted"))
                cv_mean = float(np.mean(cv_scores))
                score = cv_mean
                roc = None
                if hasattr(pipe, "predict_proba"):
                    try:
                        proba = pipe.predict_proba(X_test)
                        roc = _safe_roc_auc(y_test, proba, y_encoded.nunique())
                    except Exception:
                        pass
                res = {
                    "model": name,
                    "accuracy": round(acc, 6),
                    "f1_weighted": round(f1, 6),
                    "cv_f1_weighted": round(cv_mean, 6),
                    "roc_auc": round(roc, 6) if roc else None,
                    "training_time_sec": elapsed,
                    "model_quality": classification_quality(f1),
                    "error": None,
                }

            results.append(res)

            if best is None or score > best["score"]:
                best = {"model": name, "score": score, "pipeline": pipe}

            log.info(f"[model_trained] model={name} score={round(score, 4)} time={elapsed}")

        except Exception as e:
            log.warning(f"[model_failed] model={name} error={e}")
            results.append({"model": name, "error": str(e)})

    if best is None:
        raise Exception("All models failed during training")

    # ── Save best model ──
    model_path = run_path / "best_model.joblib"
    joblib.dump(best["pipeline"], model_path)

    le_path = None
    if label_encoder is not None:
        le_path = run_path / "label_encoder.joblib"
        joblib.dump(label_encoder, le_path)

    # ── Sort leaderboard ──
    sort_key = "f1_weighted" if task == "classification" else "rmse"
    reverse = task == "classification"
    results = sorted(
        [r for r in results if "error" not in r or r.get("error") is None],
        key=lambda x: x.get(sort_key, float("inf") if not reverse else -1),
        reverse=reverse,
    )

    # ── Feature importance ──
    fi = get_feature_importance(best["pipeline"], features)

    # ── Leaderboard chart data ──
    chart_metric = "f1_weighted" if task == "classification" else "r2"
    leaderboard_chart = [
        {"model": r["model"], "score": r.get(chart_metric), "metric": chart_metric}
        for r in results if r.get(chart_metric) is not None
    ]

    best_display_score = (
        results[0].get("f1_weighted") if task == "classification" else results[0].get("r2")
    )
    recommendation = build_recommendation(task, best_display_score or 0)

    meta = {
        "run_id": run_id,
        "target": target,
        "task": task,
        "features": features,
        "cv_folds": cv_folds,
        "test_size": test_size,
        "metric_used": "f1_weighted" if task == "classification" else "neg_rmse",
        "leaderboard": results,
        "best_model": {
            "name": best["model"],
            "score": round(float(best["score"]), 6),
            "quality": results[0].get("model_quality", "unknown") if results else "unknown",
        },
        "feature_importance": fi,
        "leaderboard_chart": leaderboard_chart,
        "recommendation": recommendation,
        "label_encoder_path": str(le_path) if le_path else None,
        "optuna_used": use_optuna and best_params is not None,
        "best_params": best_params,
        "shape": {"rows": len(df), "columns": len(df.columns)},
    }

    (run_path / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info(f"[training_complete] run_id={run_id} best_model={best['model']}")

    return meta