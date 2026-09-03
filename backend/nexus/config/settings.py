from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXUS_", env_file=".env", extra="ignore")

    # --- simulation clock -------------------------------------------------
    tick_seconds: float = 15.0        # simulated seconds per tick
    wall_seconds: float = 0.6         # real seconds per tick (demo speed 25x)
    warmup_ticks: int = 6240          # ~26h of clean history for model fitting
    buffer_ticks: int = 720           # ~3h retained in memory for the UI

    # --- detector ---------------------------------------------------------
    harmonics: int = 3
    detect_quantile: float = 0.995    # threshold from warm-up score distribution
    persist_k: int = 3                # k-of-n persistence gate
    persist_n: int = 5

    # --- llm --------------------------------------------------------------
    llm_provider: str = "auto"        # auto|openai|anthropic|ollama|deterministic
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    llm_timeout: float = 45.0
    max_tool_turns: int = 8

    # --- eval -------------------------------------------------------------
    eval_seeds_per_scenario: int = 12
    eval_clean_episodes: int = 24
    cv_folds: int = 4

    data_dir: Path = DATA
    db_path: Path = DATA / "nexus.db"
    model_path: Path = DATA / "rca_model.joblib"
    eval_path: Path = DATA / "eval_latest.json"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
