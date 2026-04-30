import json
from openai import OpenAI
from app.automl.core.config import settings
from app.automl.core.logging import get_logger

log = get_logger("llm_service")

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in .env")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def _call(prompt: str, max_tokens: int = 1000, as_json: bool = False) -> str:
    client = get_client()
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert data scientist and ML engineer. "
                "Be concise, specific, and actionable. "
                + ("Respond ONLY with valid JSON. No markdown, no preamble." if as_json else "")
            ),
        },
        {"role": "user", "content": prompt},
    ]
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    result = response.choices[0].message.content.strip()
    # ✅ CORRIGÉ : f-string au lieu de kwargs
    log.info(f"[llm_called] tokens_used={response.usage.total_tokens}")
    return result


def _parse_json(raw: str) -> dict:
    """Strip markdown fences if present, then parse JSON."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())


# ─── 1. Suggest target ────────────────────────────────────────────────────────

def suggest_target(eda_data: dict) -> dict:
    """Called after /eda. Returns suggested target column + task type."""
    prompt = f"""Given this dataset EDA, suggest the best target column for a Machine Learning task.

Dataset shape: {eda_data.get('shape')}
Column types: {json.dumps(eda_data.get('dtypes', {}))}
Unique values per column: {json.dumps(eda_data.get('unique_values', {}))}
Missing % per column: {json.dumps(eda_data.get('missing_pct_by_column', {}))}
Sample rows (first 3): {json.dumps(eda_data.get('sample_rows', [])[:3])}
Constant columns (exclude these): {eda_data.get('constant_columns', [])}

Respond ONLY with this JSON:
{{
  "suggested_target": "column_name",
  "task_type": "classification or regression",
  "confidence": "high or medium or low",
  "reasoning": "one sentence why this column is the best target",
  "alternative_targets": ["col1", "col2"]
}}"""

    try:
        raw = _call(prompt, max_tokens=300, as_json=True)
        return _parse_json(raw)
    except Exception as e:
        # ✅ CORRIGÉ : f-string au lieu de kwargs
        log.warning(f"[suggest_target_failed] error={e}")
        return {"error": str(e), "suggested_target": None}


# ─── 2. Suggest features ──────────────────────────────────────────────────────

def suggest_features(target: str, all_columns: list[str], feature_analysis: dict, dtypes: dict) -> dict:
    """Called after /analyze-features. Returns recommended feature subset."""
    prompt = f"""You are reviewing a dataset for ML training.

Target column: '{target}'
All columns: {all_columns}
Column types: {json.dumps(dtypes)}
Recommended features (correlation >= 0.3): {feature_analysis.get('recommended_features', [])}
Weak features (correlation < 0.1): {feature_analysis.get('weak_features', [])}
Possible data leakage features: {feature_analysis.get('possible_leakage_features', [])}
Warnings: {feature_analysis.get('warnings', [])}

Select the optimal feature subset. Exclude: the target itself, ID-like columns, data leakage columns, constant columns.

Respond ONLY with this JSON:
{{
  "selected_features": ["col1", "col2"],
  "excluded_features": ["col3"],
  "exclusion_reasons": {{"col3": "reason in plain English"}},
  "engineering_suggestions": ["create ratio col1/col2", "log-transform col3"],
  "advice": "one actionable sentence for the user"
}}"""

    try:
        raw = _call(prompt, max_tokens=500, as_json=True)
        return _parse_json(raw)
    except Exception as e:
        # ✅ CORRIGÉ : f-string au lieu de kwargs
        log.warning(f"[suggest_features_failed] error={e}")
        return {"error": str(e), "selected_features": []}


# ─── 3. Explain results ───────────────────────────────────────────────────────

def explain_results(train_meta: dict) -> str:
    """Called after /train. Returns plain-language explanation of results."""
    top3 = train_meta.get("leaderboard", [])[:3]
    top5_fi = train_meta.get("feature_importance", {}).get("items", [])[:5]

    prompt = f"""Explain these AutoML results to a non-technical business stakeholder.

Task: {train_meta.get('task')} on target '{train_meta.get('target')}'
Best model: {train_meta.get('best_model', {}).get('name')} (quality: {train_meta.get('best_model', {}).get('quality')})
Top 3 models: {json.dumps(top3)}
Top 5 most important features: {json.dumps(top5_fi)}
Optuna tuning used: {train_meta.get('optuna_used')}
SHAP available: {train_meta.get('shap_summary', {}) is not None}

Write a 3-paragraph response:
1. What the best model achieved and what this means in practical terms
2. Which features drive the predictions and why that makes intuitive sense
3. Three specific, concrete actions to improve the model further

Use plain language. No jargon. Be specific, not generic."""

    return _call(prompt, max_tokens=700)


# ─── 4. Analyze errors ────────────────────────────────────────────────────────

def analyze_errors(task: str, error_stats: dict, features: list[str]) -> str:
    """Analyzes model error patterns and suggests fixes."""
    prompt = f"""Analyze these ML model error patterns and suggest concrete fixes.

Task type: {task}
Features used: {features}
Error statistics: {json.dumps(error_stats)}

Give exactly 3 concrete, actionable suggestions to reduce prediction errors.
For each suggestion, explain WHY it will help for this specific case.
Be specific, not generic."""

    return _call(prompt, max_tokens=500)


# ─── 5. Generate full report ──────────────────────────────────────────────────

def generate_report(train_meta: dict, eda_data: dict) -> str:
    """Generates a complete Markdown analysis report."""
    top5 = train_meta.get("leaderboard", [])[:5]
    top5_fi = train_meta.get("feature_importance", {}).get("items", [])[:5]
    shap = train_meta.get("shap_summary", {})
    warnings = train_meta.get("feature_analysis", {}).get("warnings", [])

    prompt = f"""Generate a professional AutoML Analysis Report in Markdown format.

## Input Data
- Dataset: {eda_data.get('shape', {}).get('rows')} rows × {eda_data.get('shape', {}).get('columns')} columns
- Missing values: {eda_data.get('missing_total')} total
- Duplicate rows: {eda_data.get('duplicate_rows')}
- Outlier columns: {[o['column'] for o in eda_data.get('outliers', [])]}

## ML Configuration  
- Task: {train_meta.get('task')} on target '{train_meta.get('target')}'
- Features used: {train_meta.get('features')}
- Models tested: {len(train_meta.get('leaderboard', []))}
- Optuna hyperparameter tuning: {train_meta.get('optuna_used')}
- Best Optuna params: {json.dumps(train_meta.get('best_params'))}

## Results
- Best model: {train_meta.get('best_model', {}).get('name')}
- Quality: {train_meta.get('best_model', {}).get('quality')}
- Top 5 models: {json.dumps(top5)}
- Top 5 features by importance: {json.dumps(top5_fi)}
- SHAP summary: {json.dumps(shap) if shap else 'Not computed'}
- Warnings: {warnings}
- Recommendation: {train_meta.get('recommendation')}

## Required Report Sections (use these exact headers):
# AutoML Analysis Report

## 1. Executive Summary
## 2. Dataset Overview
## 3. Model Performance Analysis
## 4. Feature Analysis & Insights
## 5. Recommendations
## 6. Next Steps

Write a professional report suitable for a technical team. Be specific. Use the actual numbers provided."""

    return _call(prompt, max_tokens=settings.openai_max_tokens)