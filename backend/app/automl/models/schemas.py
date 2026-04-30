from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class TaskType(str, Enum):
    AUTO = "auto"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class RunStatus(str, Enum):
    CREATED = "created"
    EDA_DONE = "eda_done"
    FEATURES_ANALYZED = "features_analyzed"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    WEAK = "weak"
    POOR = "poor"


# ─── Requests ─────────────────────────────────────────────────────────────────

class FeatureAnalysisRequest(BaseModel):
    run_id: str
    target: str
    features: list[str]


class TrainRequest(BaseModel):
    run_id: str
    target: str
    features: list[str]
    task: TaskType = TaskType.AUTO
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    random_state: int = 42
    cv_folds: int = Field(default=5, ge=3, le=10)
    use_optuna: bool = True
    optuna_trials: int = Field(default=40, ge=10, le=200)


class PredictRequest(BaseModel):
    run_id: str
    data: dict[str, Any]


class LLMReportRequest(BaseModel):
    run_id: str


class LLMTargetSuggestRequest(BaseModel):
    run_id: str


class LLMFeatureSuggestRequest(BaseModel):
    run_id: str
    target: str
    feature_analysis: dict


# ─── Responses ────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    run_id: str
    filename: str
    rows: int
    columns: int
    column_names: list[str]
    column_types: dict[str, str]
    status: RunStatus = RunStatus.CREATED


class OutlierInfo(BaseModel):
    column: str
    iqr_outliers: int
    zscore_outliers: int
    pct: float


class ImbalanceInfo(BaseModel):
    imbalanced: bool
    ratio: float
    recommendation: str
    class_counts: dict[str, int]


class EDAResponse(BaseModel):
    run_id: str
    shape: dict
    missing_total: int
    missing_by_column: dict[str, int]
    missing_pct_by_column: dict[str, float]
    duplicate_rows: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    numeric_stats: dict
    dtypes: dict[str, str]
    unique_values: dict[str, int]
    sample_rows: list[dict]
    target_candidates: list[dict]
    outliers: list[OutlierInfo]
    constant_columns: list[str]
    high_cardinality_columns: list[str]
    status: RunStatus


class FeatureAnalysisResponse(BaseModel):
    run_id: str
    target: str
    features: list[str]
    feature_analysis: dict
    target_distribution: dict | None
    imbalance_info: ImbalanceInfo | None
    status: RunStatus


class ModelResult(BaseModel):
    model: str
    training_time_sec: float
    model_quality: str
    error: str | None = None
    # regression
    rmse: float | None = None
    r2: float | None = None
    cv_rmse: float | None = None
    mae: float | None = None
    # classification
    accuracy: float | None = None
    f1_weighted: float | None = None
    cv_f1_weighted: float | None = None
    roc_auc: float | None = None


class TrainResponse(BaseModel):
    run_id: str
    task: str
    target: str
    features_used: list[str]
    metric_used: str
    best_model: dict
    leaderboard: list[ModelResult]
    feature_importance: dict
    shap_summary: dict | None
    leaderboard_chart: list[dict]
    target_distribution: dict | None
    feature_analysis: dict
    recommendation: str
    optuna_used: bool
    best_params: dict | None
    status: RunStatus


class PredictResponse(BaseModel):
    run_id: str
    task: str
    prediction: Any
    confidence: float | None = None


class LLMResponse(BaseModel):
    run_id: str
    content: str
    type: str