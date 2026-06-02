"""CortexBrain configuration — extends Cognee's BaseConfig.

All Cognee env vars (LLM_API_KEY, GRAPH_DATABASE_PROVIDER, etc.) are inherited.
CortexBrain-specific settings are added here.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class CortexBrainSettings(BaseSettings):
    """CortexBrain-specific configuration layered on top of Cognee's env-based config."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Data Stores (CortexBrain-managed) ---
    redis_url: str = "redis://localhost:6379/0"
    postgres_url: str = (
        "postgresql+asyncpg://cortexbrain:cortexbrain_dev@localhost:5432/cortexbrain"
    )
    qdrant_url: str = "http://localhost:6333"

    # --- Activation Engine ---
    activation_threshold: int = 20
    dampening_factor: float = 0.55
    max_context_tokens: int = 8000

    # --- Decay Engine ---
    decay_rate: int = 10
    decay_interval_seconds: int = 30

    # --- Confidence Thresholds (Metacognition) ---
    confidence_high: float = 0.8
    confidence_medium: float = 0.5

    # --- Salience Weights ---
    salience_weight_access_freq: float = 0.4
    salience_weight_recency: float = 0.3
    salience_weight_correction_count: float = 0.2
    salience_weight_edge_count: float = 0.1

    # --- API ---
    api_rate_limit_per_minute: int = 100

    # --- Celery ---
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Continuous Learning ---
    continuous_learning_enabled: bool = True
    continuous_learning_confidence: float = 0.6  # Lower than document-sourced (0.7)
    continuous_learning_dataset: str = "auto_learned"

    # --- Consolidation Engine ---
    consolidation_enabled: bool = True
    consolidation_schedule_seconds: int = 604800  # Weekly (7 days)
    consolidation_promotion_min_access: int = 3
    consolidation_promotion_target_confidence: float = 0.75
    consolidation_archive_stale_days: int = 90
    consolidation_archive_salience_percentile: float = 0.10  # Bottom 10%
    consolidation_merge_name_similarity: float = 0.85
    consolidation_compress_max_versions: int = 5

    # --- Image Generation ---
    image_gen_enabled: bool = True
    image_gen_model: str = "gemini-2.5-flash-image"

    # --- Auth ---
    api_key_hash_rounds: int = 12
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"


@lru_cache
def get_settings() -> CortexBrainSettings:
    return CortexBrainSettings()
