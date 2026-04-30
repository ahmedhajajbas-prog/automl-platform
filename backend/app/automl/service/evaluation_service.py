import numpy as np
import pandas as pd
import joblib
import json

from pathlib import Path
from sklearn.pipeline import Pipeline

from app.automl.core.config import settings
from app.automl.core.logging import get_logger

log = get_logger("evaluation_service")


def compute_shap(run_id: str, X_sample: pd.DataFrame) -> dict:
    """
    Compute SHAP values for the best model of a run.
    Returns a summary dict with mean absolute SHAP per feature.
    """
    try:
        import shap
    except ImportError:
        return {"available": False, "message": "shap not installed", "values": []}

    run_path = settings.runs_dir / run_id
    model_path = run_path / "best_model.joblib"

    if not model_path.exists():
        return {"available": False, "message": "Model not found", "values": []}

    pipe: Pipeline = joblib.load(model_path)
    meta = json.loads((run_path / "train_meta.json").read_text(encoding="utf-8"))
    features = meta["features"]

    try:
        preprocessor = pipe.named_steps["preprocess"]
        model = pipe.named_steps["model"]

        # Transform the sample
        X_transformed = preprocessor.transform(X_sample[features])

        # Use TreeExplainer if tree-based, else LinearExplainer / KernelExplainer
        model_type = type(model).__name__

        if any(k in model_type for k in ["Forest", "Boosting", "Tree", "XGB", "LGBM", "Extra"]):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_transformed)
        elif "Logistic" in model_type or "Linear" in model_type:
            explainer = shap.LinearExplainer(model, X_transformed)
            shap_values = explainer.shap_values(X_transformed)
        else:
            # KernelExplainer — slow, use small sample
            background = shap.sample(X_transformed, min(50, len(X_transformed)))
            explainer = shap.KernelExplainer(model.predict, background)
            shap_values = explainer.shap_values(X_transformed[:20])

        # Handle multi-class (shap_values is a list)
        if isinstance(shap_values, list):
            shap_arr = np.abs(np.array(shap_values)).mean(axis=0)
        else:
            shap_arr = np.abs(shap_values)

        # Mean absolute SHAP per transformed feature
        mean_shap = shap_arr.mean(axis=0)

        # Try to map back to original features
        try:
            transformed_names = preprocessor.get_feature_names_out()
        except Exception:
            transformed_names = [f"f{i}" for i in range(len(mean_shap))]

        grouped = {f: 0.0 for f in features}
        for name, val in zip(transformed_names, mean_shap):
            for feat in features:
                safe = feat.replace(" ", "_")
                if feat in name or safe in name:
                    grouped[feat] += float(val)
                    break

        items = sorted(
            [{"feature": f, "shap_importance": round(v, 6)} for f, v in grouped.items()],
            key=lambda x: x["shap_importance"],
            reverse=True,
        )

        # ✅ CORRIGÉ
        log.info(f"[shap_computed] run_id={run_id} n_features={len(items)}")
        return {"available": True, "message": "SHAP computed successfully.", "values": items}

    except Exception as e:
        # ✅ CORRIGÉ
        log.warning(f"[shap_failed] run_id={run_id} error={e}")
        return {"available": False, "message": f"SHAP failed: {str(e)}", "values": []}


def predict(run_id: str, data: dict) -> dict:
    run_path = settings.runs_dir / run_id
    model_path = run_path / "best_model.joblib"
    meta_path = run_path / "train_meta.json"
    le_path = run_path / "label_encoder.joblib"

    if not model_path.exists():
        raise FileNotFoundError("Model not found. Train first.")
    if not meta_path.exists():
        raise FileNotFoundError("Training metadata not found.")

    pipe = joblib.load(model_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    task = meta["task"]
    features = meta["features"]

    missing = [f for f in features if f not in data]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    df_input = pd.DataFrame([data])[features]
    prediction = pipe.predict(df_input)[0]

    confidence = None
    if task == "classification" and hasattr(pipe, "predict_proba"):
        try:
            proba = pipe.predict_proba(df_input)[0]
            confidence = round(float(np.max(proba)), 4)
        except Exception:
            pass

    if task == "regression":
        pred_value = float(prediction)
    else:
        if le_path.exists():
            le = joblib.load(le_path)
            pred_value = str(le.inverse_transform([int(prediction)])[0])
        else:
            pred_value = str(prediction)

    return {"run_id": run_id, "task": task, "prediction": pred_value, "confidence": confidence}