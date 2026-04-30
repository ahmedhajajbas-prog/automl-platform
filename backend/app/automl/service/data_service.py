import io
import json
import uuid
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from scipy import stats
from fastapi import HTTPException, UploadFile

from app.automl.core.config import settings
from app.automl.core.logging import get_logger
from app.automl.models.schemas import RunStatus, OutlierInfo, ImbalanceInfo

log = get_logger("data_service")


# ─── Run helpers ──────────────────────────────────────────────────────────────

def get_run_path(run_id: str) -> Path:
    run_path = settings.runs_dir / run_id
    if not run_path.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run_path


def update_run_status(run_id: str, status: RunStatus, extra: dict = {}):
    run_path = settings.runs_dir / run_id
    status_file = run_path / "status.json"
    data = {
        "run_id": run_id,
        "status": status.value,
        "updated_at": datetime.utcnow().isoformat(),
        **extra,
    }
    status_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info(f"run_status_updated run_id={run_id} status={status.value}")


def load_dataset(run_id: str) -> pd.DataFrame:
    run_path = get_run_path(run_id)
    csv_path = run_path / "dataset.csv"
    xlsx_path = run_path / "dataset.xlsx"

    if csv_path.exists():
        return pd.read_csv(csv_path)
    if xlsx_path.exists():
        return pd.read_excel(xlsx_path)
    raise HTTPException(status_code=404, detail="Dataset not found for this run")


# ─── Upload ───────────────────────────────────────────────────────────────────

async def handle_upload(file: UploadFile) -> dict:
    filename = file.filename.lower()
    if not (filename.endswith(".csv") or filename.endswith((".xlsx", ".xls"))):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    run_id = uuid.uuid4().hex[:12]
    run_path = settings.runs_dir / run_id
    run_path.mkdir(parents=True, exist_ok=True)

    content = await file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
            dataset_path = run_path / "dataset.csv"
            df.to_csv(dataset_path, index=False)
        else:
            df = pd.read_excel(io.BytesIO(content))
            dataset_path = run_path / "dataset.xlsx"
            df.to_excel(dataset_path, index=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {e}")

    update_run_status(run_id, RunStatus.CREATED)
    log.info(f"dataset_uploaded run_id={run_id} rows={df.shape[0]} cols={df.shape[1]}")

    return {
        "run_id": run_id,
        "filename": file.filename,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": df.columns.tolist(),
        "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "status": RunStatus.CREATED,
    }


# ─── EDA ──────────────────────────────────────────────────────────────────────

def _detect_outliers(df: pd.DataFrame, numeric_cols: list[str]) -> list[OutlierInfo]:
    outliers = []
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 10:
            continue
        Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
        IQR = Q3 - Q1
        iqr_count = int(((series < Q1 - 1.5 * IQR) | (series > Q3 + 1.5 * IQR)).sum())
        try:
            z_count = int((np.abs(stats.zscore(series)) > 3).sum())
        except Exception:
            z_count = 0
        pct = round(max(iqr_count, z_count) / len(series) * 100, 2)
        if iqr_count > 0 or z_count > 0:
            outliers.append(OutlierInfo(
                column=col,
                iqr_outliers=iqr_count,
                zscore_outliers=z_count,
                pct=pct,
            ))
    return outliers


def _detect_class_imbalance(y: pd.Series) -> ImbalanceInfo | None:
    if pd.api.types.is_numeric_dtype(y) and y.nunique() > 20:
        return None
    counts = y.astype(str).value_counts()
    if counts.min() == 0:
        return None
    ratio = round(float(counts.max() / counts.min()), 2)
    return ImbalanceInfo(
        imbalanced=ratio > 3,
        ratio=ratio,
        recommendation=(
            "Use SMOTE (imbalanced-learn) or class_weight='balanced'"
            if ratio > 3 else "Classes are balanced"
        ),
        class_counts={str(k): int(v) for k, v in counts.items()},
    )


def get_eda(run_id: str) -> dict:
    df = load_dataset(run_id)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    missing_by_col = {col: int(v) for col, v in df.isnull().sum().items()}
    missing_pct = {col: round(v / len(df) * 100, 2) for col, v in missing_by_col.items()}

    # Constant columns (no variance)
    constant_cols = [col for col in df.columns if df[col].nunique(dropna=True) <= 1]

    # High cardinality categoricals (> 50 unique)
    high_card = [
        col for col in categorical_cols
        if df[col].nunique(dropna=True) > 50
    ]

    # Numeric stats
    numeric_stats = {}
    if numeric_cols:
        numeric_stats = df[numeric_cols].describe().replace({np.nan: None}).to_dict()

    # Target candidates: exclude constants and IDs
    target_candidates = []
    for col in df.columns:
        n = df[col].nunique(dropna=True)
        if 1 < n <= len(df):
            target_candidates.append({
                "column": col,
                "dtype": str(df[col].dtype),
                "unique_values": int(n),
                "missing_pct": missing_pct.get(col, 0),
            })

    outliers = _detect_outliers(df, numeric_cols)

    update_run_status(run_id, RunStatus.EDA_DONE)
    log.info(f"eda_completed run_id={run_id} outlier_cols={len(outliers)}")

    return {
        "run_id": run_id,
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "missing_total": int(df.isnull().sum().sum()),
        "missing_by_column": missing_by_col,
        "missing_pct_by_column": missing_pct,
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "numeric_stats": numeric_stats,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "unique_values": {col: int(df[col].nunique(dropna=True)) for col in df.columns},
        "sample_rows": df.head(5).replace({np.nan: None}).to_dict(orient="records"),
        "target_candidates": target_candidates,
        "outliers": [o.model_dump() for o in outliers],
        "constant_columns": constant_cols,
        "high_cardinality_columns": high_card,
        "status": RunStatus.EDA_DONE,
    }


# ─── Target distribution ──────────────────────────────────────────────────────

def get_target_distribution(df: pd.DataFrame, target: str) -> dict | None:
    if target not in df.columns:
        return None
    series = df[target].dropna()
    if series.empty:
        return None
    if pd.api.types.is_numeric_dtype(series):
        return {
            "type": "numeric",
            "summary": {
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std()),
                "skewness": round(float(series.skew()), 4),
            },
        }
    counts = series.astype(str).value_counts().head(20)
    return {
        "type": "categorical",
        "counts": [{"label": str(k), "count": int(v)} for k, v in counts.items()],
    }


# ─── Feature Analysis ─────────────────────────────────────────────────────────

def analyze_feature_relevance(df: pd.DataFrame, target: str, features: list[str]) -> dict:
    analysis = {
        "recommended_features": [],
        "weak_features": [],
        "high_correlation_features": [],
        "possible_leakage_features": [],
        "warnings": [],
        "insight": {},
    }

    working_df = df[[target] + features].copy().dropna(subset=[target])
    if working_df.empty:
        analysis["warnings"].append("Empty dataset after dropping missing target.")
        return analysis

    target_is_numeric = pd.api.types.is_numeric_dtype(working_df[target])

    if target_is_numeric:
        numeric_features = [
            c for c in features
            if c in working_df.columns and pd.api.types.is_numeric_dtype(working_df[c])
        ]
        if numeric_features:
            corr = working_df[[target] + numeric_features].corr(numeric_only=True)
            for col in numeric_features:
                val = corr.loc[target, col]
                if pd.isna(val):
                    val = 0.0
                abs_val = abs(float(val))
                entry = {"feature": col, "correlation": round(float(val), 4)}
                if abs_val >= 0.3:
                    analysis["recommended_features"].append(entry)
                if abs_val < 0.1:
                    analysis["weak_features"].append(entry)
                if abs_val >= 0.7:
                    analysis["high_correlation_features"].append(entry)
                if abs_val >= 0.95:
                    analysis["possible_leakage_features"].append(entry)

        if analysis["possible_leakage_features"]:
            analysis["warnings"].append("Possible data leakage: features with correlation >= 0.95 to target.")
        if not analysis["recommended_features"]:
            analysis["warnings"].append("No strongly correlated numeric features found.")

        analysis["insight"] = {
            "problem": "Low correlation may indicate weak feature-target relationship.",
            "solution": "Add more domain-relevant features or engineer new ones.",
        }
    else:
        analysis["warnings"].append(
            "Categorical target: correlation analysis not applicable. "
            "Rely on model performance and domain knowledge."
        )
        analysis["insight"] = {
            "problem": "Classification: feature quality depends on discriminative power.",
            "solution": "Check class balance and avoid ID-like columns.",
        }

    return analysis