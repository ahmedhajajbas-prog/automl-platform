"""
scorer.py — Système de scoring de qualité du code Java
Score de 0 à 100 basé sur les problèmes détectés par l'analyseur statique.
"""


# ─────────────────────────────────────────────────────────────────────────────
# POIDS PAR SÉVÉRITÉ
# ─────────────────────────────────────────────────────────────────────────────

SEVERITY_WEIGHTS = {
    "critical": 15,   # -15 pts par problème critique
    "high":     8,    # -8  pts par problème majeur
    "medium":   4,    # -4  pts par problème moyen
    "low":      2,    # -2  pts par problème mineur
}

# Bonus : bonnes pratiques modernes détectées dans les métriques
BONUS_METRICS = {
    "has_lambda":   +5,
    "has_streams":  +5,
    "has_optional": +3,
    "has_generics": +3,
    "has_records":  +5,
}


# ─────────────────────────────────────────────────────────────────────────────
# FONCTION PRINCIPALE DE SCORING
# ─────────────────────────────────────────────────────────────────────────────

def compute_score(analysis: dict) -> dict:
    """
    Calcule le score de qualité à partir du résultat de analyze_java_code().
    Retourne un dict complet avec score, grade, risk_level et breakdown.
    """
    issues_by_severity = analysis.get("issues_by_severity", {})
    metrics            = analysis.get("metrics", {})
    issues             = analysis.get("issues", [])

    # ── Calcul des pénalités ──
    penalty = 0
    breakdown_penalties = {}
    for severity, count in issues_by_severity.items():
        weight = SEVERITY_WEIGHTS.get(severity, 0)
        pts    = count * weight
        penalty += pts
        if pts > 0:
            breakdown_penalties[severity] = {
                "count":   count,
                "weight":  weight,
                "points_lost": pts,
            }

    # ── Calcul des bonus ──
    bonus = 0
    breakdown_bonuses = {}
    for metric, pts in BONUS_METRICS.items():
        if metrics.get(metric):
            bonus += pts
            breakdown_bonuses[metric] = pts

    # ── Score final (borné entre 0 et 100) ──
    raw_score = 100 - penalty + bonus
    score     = max(0, min(100, raw_score))

    return {
        "score":        score,
        "grade":        _score_to_grade(score),
        "risk_level":   _score_to_risk(score),
        "issues_count": analysis.get("issues_count", 0),
        "penalty":      penalty,
        "bonus":        bonus,
        "breakdown": {
            "penalties": breakdown_penalties,
            "bonuses":   breakdown_bonuses,
            "top_issues": [
                {"title": i["title"], "severity": i["severity"], "line": i["line"]}
                for i in sorted(issues, key=lambda x: SEVERITY_WEIGHTS.get(x["severity"], 0), reverse=True)[:5]
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# CALCUL DE L'AMÉLIORATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_improvement(score_before: dict, score_after: dict) -> dict:
    """
    Compare les deux scores et retourne les métriques d'amélioration.
    """
    delta       = score_after["score"] - score_before["score"]
    delta_issues = score_before["issues_count"] - score_after["issues_count"]

    return {
        "score_delta":   delta,
        "label":         f"+{delta} points" if delta >= 0 else f"{delta} points",
        "issues_fixed":  max(0, delta_issues),
        "issues_added":  max(0, -delta_issues),
        "grade_before":  score_before["grade"],
        "grade_after":   score_after["grade"],
        "risk_before":   score_before["risk_level"],
        "risk_after":    score_after["risk_level"],
        "improved":      delta > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _score_to_grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    if score >= 40: return "D"
    return "F"

def _score_to_risk(score: int) -> str:
    if score >= 80: return "low"
    if score >= 60: return "medium"
    if score >= 40: return "high"
    return "critical"
