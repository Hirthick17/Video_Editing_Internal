"""Application configuration and filesystem paths."""

from pathlib import Path
from pydantic_settings import BaseSettings

# Philosophy core — imported here so every module that imports config
# automatically has access to the editing guardrails.
from app.philosophy import EditingPhilosophy, PhilosophyGuard, PhilosophyViolationError, philosophy  # noqa: F401


class Settings(BaseSettings):
    app_name: str = "HirthicksVisionStudio"
    app_version: str = "0.1.0"
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    sqlite_db_path: Path = base_dir / "data" / "studio_persistence.db"
    log_level: str = "INFO"
    default_fps: int = 30
    default_width: int = 1080
    default_height: int = 1920
    max_node_retries: int = 3
    max_critique_rounds: int = 2

    class Config:
        env_prefix = "HVS_"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)

