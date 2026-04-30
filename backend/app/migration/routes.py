"""
routes.py — Endpoints FastAPI du module de migration Java
"""

from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.migration.service import migrate_java_file

router = APIRouter()

UPLOAD_DIR  = Path("data/uploads/java")
MIGRATED_DIR = Path("data/migrated")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MIGRATED_DIR.mkdir(parents=True, exist_ok=True)

VALID_VERSIONS = {"8", "11", "17", "21"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /upload
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload", summary="Upload d'un fichier Java")
async def upload_java_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".java"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .java sont acceptés.")

    content = await file.read()
    if len(content) > 1 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux. Max : 1 MB.")

    save_path = UPLOAD_DIR / file.filename
    save_path.write_bytes(content)

    return {
        "message":    "Fichier uploadé avec succès.",
        "filename":   file.filename,
        "size_bytes": len(content),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /migrate
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/migrate", summary="Migrer un fichier Java via LLM")
async def migrate_file(filename: str, target_version: str = "17"):
    """
    Lance la migration complète d'un fichier Java.

    Paramètres :
    - filename       : nom du fichier uploadé (ex: MyService.java)
    - target_version : version Java cible — 8 | 11 | 17 | 21 (défaut: 17)

    Retourne :
    - original_code, migrated_code
    - analysis_before, analysis_after (analyse statique)
    - score_before, score_after (scoring qualité)
    - improvement (delta de score)
    - modifications (liste avant/après)
    - summary, saved_file
    """
    if target_version not in VALID_VERSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Version invalide : '{target_version}'. Valeurs acceptées : {sorted(VALID_VERSIONS)}"
        )

    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fichier '{filename}' introuvable. Uploadez-le d'abord."
        )

    result = await migrate_java_file(
        file_path         = str(file_path),
        original_filename = filename,
        target_version    = target_version,
    )

    return {
        "status":          "success",
        "filename":        filename,
        "target_version":  f"Java {target_version}",
        "original_code":   result["original_code"],
        "migrated_code":   result["migrated_code"],
        "summary":         result["summary"],
        "modifications":   result["modifications"],
        "analysis_before": result["analysis_before"],
        "analysis_after":  result["analysis_after"],
        "score_before":    result["score_before"],
        "score_after":     result["score_after"],
        "improvement":     result["improvement"],
        "saved_file":      result["saved_file"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /download/{filename}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/download/{filename}", summary="Télécharger le fichier Java migré")
async def download_migrated_file(filename: str):
    if not filename.endswith("_migrated.java"):
        filename = f"{Path(filename).stem}_migrated.java"

    file_path = MIGRATED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier '{filename}' introuvable.")

    return FileResponse(
        path       = str(file_path),
        media_type = "text/x-java-source",
        filename   = filename,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /history
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/history", summary="Liste des fichiers Java migrés")
async def list_migrated_files():
    files = sorted(MIGRATED_DIR.glob("*_migrated.java"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return {"count": 0, "files": []}
    return {
        "count": len(files),
        "files": [
            {
                "filename":     f.name,
                "size_bytes":   f.stat().st_size,
                "download_url": f"/api/migration/download/{f.name}",
            }
            for f in files
        ],
    }
