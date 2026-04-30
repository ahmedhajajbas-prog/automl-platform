from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 1500

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    runs_dir: Path = base_dir / "data" / "runs"

    # Training
    optuna_n_trials: int = 40
    default_cv_folds: int = 5
    default_test_size: float = 0.2
    default_random_state: int = 42
    min_rows_required: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
settings.runs_dir.mkdir(parents=True, exist_ok=True)