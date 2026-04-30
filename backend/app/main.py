from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.automl import router as automl_router
from app.routers.migration import router as migration_router
from app.automl.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="AI Platform - AutoML & Code Migration",
    version="2.0.0",
    description="Plateforme intelligente avec deux modules : AutoML avancé et Migration de code",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    automl_router,
    prefix="/api/automl",
    tags=["AutoML"],
)

app.include_router(
    migration_router,
    prefix="/api/migration",
    tags=["Migration Java"],
)


@app.get("/")
def root():
    return {
        "message": "AI Platform API is running",
        "version": "2.0.0",
        "modules": {
            "automl": {
                "prefix": "/api/automl",
                "docs": "/docs#/AutoML",
                "endpoints": [
                    "POST /api/automl/upload",
                    "GET /api/automl/eda/{run_id}",
                    "POST /api/automl/analyze-features",
                    "POST /api/automl/train",
                    "POST /api/automl/predict",
                    "POST /api/automl/llm/suggest-target",
                    "POST /api/automl/llm/suggest-features",
                    "GET /api/automl/llm/explain/{run_id}",
                    "POST /api/automl/llm/report",
                    "GET /api/automl/report/{run_id}",
                    "GET /api/automl/status/{run_id}",
                    "GET /api/automl/runs",
                ],
            },
            "migration": {
                "prefix": "/api/migration",
                "docs": "/docs#/Migration Java",
            },
        },
    }