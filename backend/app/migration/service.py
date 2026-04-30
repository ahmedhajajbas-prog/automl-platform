"""
service.py — Logique principale du module de migration Java
Pipeline : lecture → analyse → score_before → LLM → analyse → score_after → résultat
"""

import os
import re
import json
from pathlib import Path
from openai import AsyncOpenAI
from fastapi import HTTPException
from dotenv import load_dotenv

from app.migration.analyzer import analyze_java_code
from app.migration.scorer   import compute_score, compute_improvement

# ─── Charger le fichier .env ──────────────────────────────────────────────────
load_dotenv()

# Dossier de sauvegarde des fichiers migrés
MIGRATED_DIR = Path("data/migrated")
MIGRATED_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT OPENAI (lazy — évite l'erreur au démarrage si .env absent)
# ─────────────────────────────────────────────────────────────────────────────

def get_client() -> AsyncOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY manquante. Créez backend/.env avec OPENAI_API_KEY=sk-..."
        )
    return AsyncOpenAI(api_key=api_key)


# ─────────────────────────────────────────────────────────────────────────────
# 1. LECTURE DU FICHIER
# ─────────────────────────────────────────────────────────────────────────────

def read_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {file_path}")
    if path.suffix.lower() != ".java":
        raise HTTPException(status_code=400, detail="Seuls les fichiers .java sont acceptés.")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de lecture : {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. CONSTRUCTION DU PROMPT ENRICHI
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(java_code: str, analysis: dict, target_version: str = "17") -> str:
    """
    Prompt enrichi par l'analyse statique.
    Le LLM reçoit la liste des problèmes détectés pour les corriger en priorité.
    """
    version_features = {
        "8":  "lambdas, Stream API, Optional, java.time, default methods",
        "11": "var, String methods (strip/isBlank/lines), HTTP Client",
        "17": "records, sealed classes, pattern matching instanceof, switch expressions, text blocks, var",
        "21": "virtual threads, sequenced collections, record patterns, switch pattern matching",
    }
    features = version_features.get(target_version, "fonctionnalités modernes Java")

    # Construire la liste des problèmes détectés pour le prompt
    issues = analysis.get("issues", [])
    if issues:
        issues_text = "\n".join([
            f"  - [{i['code']}] {i['title']} (ligne {i['line']}) → {i['suggestion']}"
            for i in issues
        ])
    else:
        issues_text = "  Aucun problème majeur détecté par l'analyse statique."

    return f"""Tu es un expert Java senior. Migre ce code vers Java {target_version}.

PROBLÈMES DÉTECTÉS (à corriger obligatoirement) :
{issues_text}

FEATURES Java {target_version} à utiliser : {features}

CODE SOURCE :
```java
{java_code}
```

INSTRUCTIONS STRICTES :
1. Corrige TOUS les problèmes listés ci-dessus
2. Utilise les features Java {target_version} listées
3. Préserve 100% de la logique métier
4. Retourne UNIQUEMENT un objet JSON valide, sans texte avant ou après
5. N'ajoute pas de balises markdown autour du JSON

FORMAT DE RÉPONSE (JSON strict) :
{{
  "summary": "Résumé court de la migration en 2-3 phrases",
  "migrated_code": "// code Java {target_version} complet ici",
  "modifications": [
    {{
      "title": "Titre court du changement",
      "before": "ancien code",
      "after": "nouveau code",
      "explanation": "Pourquoi ce changement"
    }}
  ]
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# 3. APPEL AU LLM
# ─────────────────────────────────────────────────────────────────────────────

async def call_llm(prompt: str) -> str:
    try:
        response = await get_client().chat.completions.create(
            model       = os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages    = [
                {
                    "role":    "system",
                    "content": (
                        "Tu es un expert Java spécialisé en migration de code legacy. "
                        "Tu retournes TOUJOURS un JSON valide et rien d'autre. "
                        "Pas de texte avant, pas de texte après, pas de balises markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature = 0.1,   # Très faible pour des réponses déterministes
            max_tokens  = 4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur LLM : {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. TRAITEMENT DE LA RÉPONSE
# ─────────────────────────────────────────────────────────────────────────────

def process_response(raw: str, original_filename: str) -> dict:
    """
    Parse la réponse JSON du LLM.
    Gère les cas où le LLM ajoute quand même des balises markdown.
    """
    # Nettoyer les balises markdown si présentes
    cleaned = raw.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*",     "", cleaned)
    cleaned = re.sub(r"\s*```$",     "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback : extraire le JSON avec regex
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    summary       = data.get("summary", "")
    migrated_code = data.get("migrated_code", "")
    modifications = data.get("modifications", [])

    # Sauvegarder le code migré
    saved_file = None
    if migrated_code:
        stem       = Path(original_filename).stem
        out_path   = MIGRATED_DIR / f"{stem}_migrated.java"
        try:
            out_path.write_text(migrated_code, encoding="utf-8")
            saved_file = str(out_path)
        except Exception:
            pass

    return {
        "summary":       summary,
        "migrated_code": migrated_code,
        "modifications": modifications,
        "saved_file":    saved_file,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. ORCHESTRATEUR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

async def migrate_java_file(
    file_path:        str,
    original_filename: str,
    target_version:   str = "17",
) -> dict:
    """
    Pipeline complet :
      1. Lecture du fichier
      2. Analyse statique du code original
      3. Score avant migration
      4. Construction du prompt enrichi
      5. Appel LLM
      6. Traitement de la réponse
      7. Analyse statique du code migré
      8. Score après migration
      9. Calcul de l'amélioration
    """

    # ── Étape 1 : Lire ──────────────────────────────────────────────────────
    original_code = read_file(file_path)

    # ── Étape 2 : Analyser le code original ─────────────────────────────────
    analysis_before = analyze_java_code(original_code)

    # ── Étape 3 : Score avant ────────────────────────────────────────────────
    score_before = compute_score(analysis_before)

    # ── Étape 4 : Prompt enrichi ─────────────────────────────────────────────
    prompt = build_prompt(original_code, analysis_before, target_version)

    # ── Étape 5 : LLM ────────────────────────────────────────────────────────
    raw_response = await call_llm(prompt)

    # ── Étape 6 : Traitement ─────────────────────────────────────────────────
    result = process_response(raw_response, original_filename)

    # ── Étape 7 : Analyser le code migré ────────────────────────────────────
    analysis_after = analyze_java_code(result["migrated_code"]) if result["migrated_code"] else {}

    # ── Étape 8 : Score après ────────────────────────────────────────────────
    score_after = compute_score(analysis_after) if analysis_after else {"score": 0, "grade": "N/A", "risk_level": "N/A", "issues_count": 0}

    # ── Étape 9 : Amélioration ───────────────────────────────────────────────
    improvement = compute_improvement(score_before, score_after)

    return {
        "original_code":   original_code,
        "migrated_code":   result["migrated_code"],
        "summary":         result["summary"],
        "modifications":   result["modifications"],
        "analysis_before": analysis_before,
        "analysis_after":  analysis_after,
        "score_before":    score_before,
        "score_after":     score_after,
        "improvement":     improvement,
        "saved_file":      result["saved_file"],
    }
