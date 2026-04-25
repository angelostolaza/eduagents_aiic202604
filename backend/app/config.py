from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = "dev-secret-change-in-production"
    app_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5500"]

    @field_validator("app_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://historylive:historylive@localhost:5432/historylive"
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Object Storage ────────────────────────────────────────────────────────
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "historylive"
    storage_region: str = "us-east-1"
    storage_url_expiry_seconds: int = 900

    # ── AI Providers ──────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    elevenlabs_api_key: str = ""
    higgsfield_api_key: str = ""

    # ── Ollama (local open-source LLMs) ─────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"

    # ── Model defaults ────────────────────────────────────────────────────────
    default_research_model: str = "llama3.2"
    default_scripting_model: str = "llama3.2"
    default_seed_image_model: str = "elevenlabs-image"
    default_video_model: str = "elevenlabs-video"
    default_voice_model: str = "eleven_v3"

    # ── Rate limits ───────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 200

    # ── Cost caps (cents) ─────────────────────────────────────────────────────
    max_cost_cents_per_request: int = 2000
    max_cost_cents_per_user_day: int = 5000
    max_cost_cents_global_day: int = 50000

    # ── Access tiers ──────────────────────────────────────────────────────────
    public_tier_enabled: bool = True
    whitelisted_auto_generate: bool = True
    whitelisted_daily_cap: int = 2
    whitelisted_weekly_cap: int = 10

    # ── Feature flags ─────────────────────────────────────────────────────────
    scripting_review_gate_enabled: bool = True

    # ── 3D Bust pipeline ──────────────────────────────────────────────────
    # "triposr" (fast, ~5 s, 3.6 GB VRAM) | "hunyuan3d" (high quality, slow)
    bust_method: Literal["triposr", "hunyuan3d"] = "triposr"
    triposr_dir: str = "TripoSR"
    hunyuan3d_dir: str = "Hunyuan3D-2GP"

    # ── Observability ─────────────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "historylive-backend"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def jwt_algorithm(self) -> str:
        return "HS256"

    @property
    def access_token_expire_minutes(self) -> int:
        return 60 * 24  # 24 hours


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
