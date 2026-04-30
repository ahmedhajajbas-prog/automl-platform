import json
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse

# ✅ CORRECTION IMPORT
from app.automl.models.schemas import (
    FeatureAnalysisRequest, TrainRequest, PredictRequest,
    LLMReportRequest, LLMTargetSuggestRequest, LLMFeatureSuggestRequest,
    RunStatus,
)

# ✅ CORRECTION IMPORT SERVICES
from app.automl.service import data_service, training_service, evaluation_service, llm_service
from app.automl.service.preprocessing_service import infer_task

# ✅ CORE
from app.automl.core.config import settings
from app.automl.core.logging import get_logger

log = get_logger("automl_router")

# ⚠️ IMPORTANT : ne mets pas de prefix ici
router = APIRouter()


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"module": "AutoML", "status": "ok", "version": "2.0.0"}


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    return await data_service.handle_upload(file)


# ─── EDA ──────────────────────────────────────────────────────────────────────

@router.get("/eda/{run_id}")
def get_eda(run_id: str):
    return data_service.get_eda(run_id)


# ─── Analyze Features ─────────────────────────────────────────────────────────

@router.post("/analyze-features")
def analyze_features(req: FeatureAnalysisRequest):
    run_path = data_service.get_run_path(req.run_id)
    df = data_service.load_dataset(req.run_id)

    if req.target not in df.columns:
        raise HTTPException(400, f"Target '{req.target}' not found")
    missing = [c for c in req.features if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Features not found: {missing}")
    if req.target in req.features:
        raise HTTPException(400, "Target must not be in features list")

    feature_analysis = data_service.analyze_feature_relevance(df, req.target, req.features)
    target_dist = data_service.get_target_distribution(df, req.target)

    # Imbalance detection
    y = df[req.target].dropna()
    task = infer_task(y)
    imbalance = None
    if task == "classification":
        imbalance = data_service._detect_class_imbalance(y)

    data_service.update_run_status(req.run_id, RunStatus.FEATURES_ANALYZED)

    return {
        "run_id": req.run_id,
        "target": req.target,
        "features": req.features,
        "task_detected": task,
        "feature_analysis": feature_analysis,
        "target_distribution": target_dist,
        "imbalance_info": imbalance.model_dump() if imbalance else None,
        "status": RunStatus.FEATURES_ANALYZED,
    }


# ─── Train ────────────────────────────────────────────────────────────────────

@router.post("/train")
def train_model(req: TrainRequest):
    run_path = data_service.get_run_path(req.run_id)
    df = data_service.load_dataset(req.run_id)

    # Validations
    if req.target not in df.columns:
        raise HTTPException(400, f"Target '{req.target}' not found")
    if not req.features:
        raise HTTPException(400, "Provide at least one feature")
    missing = [c for c in req.features if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Features not found: {missing}")
    if req.target in req.features:
        raise HTTPException(400, "Target must not be in features list")

    df = df.dropna(subset=[req.target])
    if len(df) < settings.min_rows_required:
        raise HTTPException(400, f"Not enough rows (min {settings.min_rows_required})")

    y = df[req.target]
    task = infer_task(y) if req.task.value == "auto" else req.task.value

    data_service.update_run_status(req.run_id, RunStatus.TRAINING)

    try:
        meta = training_service.train(
            run_id=req.run_id,
            df=df,
            target=req.target,
            features=req.features,
            task=task,
            test_size=req.test_size,
            random_state=req.random_state,
            cv_folds=req.cv_folds,
            use_optuna=req.use_optuna,
            optuna_trials=req.optuna_trials,
        )
    except Exception as e:
        data_service.update_run_status(req.run_id, RunStatus.FAILED, {"error": str(e)})
        raise HTTPException(500, f"Training failed: {e}")

    # Compute SHAP on test sample
    X_sample = df[req.features].dropna().sample(min(100, len(df)), random_state=42)
    shap_summary = evaluation_service.compute_shap(req.run_id, X_sample)
    meta["shap_summary"] = shap_summary

    # Save updated meta with SHAP
    meta_path = run_path / "train_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    feature_analysis = data_service.analyze_feature_relevance(df, req.target, req.features)

    data_service.update_run_status(req.run_id, RunStatus.COMPLETED)

    return {
        **meta,
        "feature_analysis": feature_analysis,
        "status": RunStatus.COMPLETED,
    }


# ─── Predict ──────────────────────────────────────────────────────────────────

@router.post("/predict")
def predict(req: PredictRequest):
    try:
        return evaluation_service.predict(req.run_id, req.data)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── LLM: Suggest Target ──────────────────────────────────────────────────────

@router.post("/llm/suggest-target")
def llm_suggest_target(req: LLMTargetSuggestRequest):
    eda_data = data_service.get_eda(req.run_id)
    result = llm_service.suggest_target(eda_data)
    return {"run_id": req.run_id, "type": "target_suggestion", "content": result}


# ─── LLM: Suggest Features ────────────────────────────────────────────────────

@router.post("/llm/suggest-features")
def llm_suggest_features(req: LLMFeatureSuggestRequest):
    df = data_service.load_dataset(req.run_id)
    eda = data_service.get_eda(req.run_id)
    result = llm_service.suggest_features(
        target=req.target,
        all_columns=df.columns.tolist(),
        feature_analysis=req.feature_analysis,
        dtypes=eda["dtypes"],
    )
    return {"run_id": req.run_id, "type": "feature_suggestion", "content": result}


# ─── LLM: Explain Results ─────────────────────────────────────────────────────

@router.get("/llm/explain/{run_id}")
def llm_explain_results(run_id: str):
    run_path = data_service.get_run_path(run_id)
    meta_path = run_path / "train_meta.json"
    if not meta_path.exists():
        raise HTTPException(404, "Train the model first")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    explanation = llm_service.explain_results(meta)
    return {"run_id": run_id, "type": "results_explanation", "content": explanation}


# ─── LLM: Generate Full Report ────────────────────────────────────────────────

@router.post("/llm/report")
def llm_generate_report(req: LLMReportRequest):
    run_path = data_service.get_run_path(req.run_id)
    meta_path = run_path / "train_meta.json"
    if not meta_path.exists():
        raise HTTPException(404, "Train the model first")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    eda_data = data_service.get_eda(req.run_id)

    report_md = llm_service.generate_report(meta, eda_data)

    report_path = run_path / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    return {"run_id": req.run_id, "type": "full_report", "content": report_md}


# ─── Get Report (raw markdown) ────────────────────────────────────────────────

@router.get("/report/{run_id}", response_class=PlainTextResponse)
def get_report(run_id: str):
    run_path = data_service.get_run_path(run_id)
    report_path = run_path / "report.md"
    if not report_path.exists():
        raise HTTPException(404, "Report not generated yet. Call /llm/report first.")
    return report_path.read_text(encoding="utf-8")


# ─── Run Status ───────────────────────────────────────────────────────────────

@router.get("/status/{run_id}")
def get_run_status(run_id: str):
    run_path = data_service.get_run_path(run_id)
    status_path = run_path / "status.json"
    if not status_path.exists():
        return {"run_id": run_id, "status": "unknown"}
    return json.loads(status_path.read_text(encoding="utf-8"))


# ─── List Runs ────────────────────────────────────────────────────────────────

@router.get("/runs")
def list_runs():
    runs = []
    for run_dir in sorted(settings.runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        status_path = run_dir / "status.json"
        meta_path = run_dir / "train_meta.json"
        entry = {"run_id": run_dir.name, "status": "unknown"}
        if status_path.exists():
            entry.update(json.loads(status_path.read_text()))
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            entry["task"] = meta.get("task")
            entry["target"] = meta.get("target")
            entry["best_model"] = meta.get("best_model", {}).get("name")
        runs.append(entry)
    return {"runs": runs, "total": len(runs)}