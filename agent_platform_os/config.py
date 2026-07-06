"""Validated root configuration for Agent Platform OS."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    """Environment contract shared across all platform services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    POSTGRES_PRIME_URL: str = Field(
        default="postgresql://agent_platform:agent_platform@127.0.0.1:5432/agent_platform_os"
    )
    REDIS_STREAM_URL: str = Field(default="redis://127.0.0.1:6379/0")
    GATEWAY_PORT: int = Field(default=8080, ge=1, le=65535)
    HYDRA_PORT: int = Field(default=8081, ge=1, le=65535)
    SYNAPSE_PORT: int = Field(default=8082, ge=1, le=65535)
    SWARMBUS_PORT: int = Field(default=8085, ge=1, le=65535)
    SPATIAL_FLUX_PORT: int = Field(default=8084, ge=1, le=65535)
    MAX_TOKENS_PER_MIN: int = Field(default=120000, ge=1)
    COMPLIANCE_MODE: str = Field(default="standard")
    HYDRA_STATE_SCHEMA: str = Field(default="hydra_state")
    EVENT_REPLAY_RETRY_LIMIT: int = Field(default=5, ge=0)
    OPENAI_API_URL: str = Field(default="https://api.openai.com/v1")
    ANTHROPIC_API_URL: str = Field(default="https://api.anthropic.com")
    CRITERIA_FALLBACK_MODE: str = Field(default="cost_weighted")
    SWARMBUS_LOOP_DEPTH_LIMIT: int = Field(default=32, ge=1)
    LOCK_LEASE_TTL_MS: int = Field(default=30000, ge=100)
    EDGE_DRIFT_THRESHOLD: float = Field(default=0.15, ge=0.0, le=1.0)
    IMCODEC_QUALITY_RATIO: int = Field(default=80, ge=1, le=100)
    HEALTH_TIMEOUT_SECONDS: float = Field(default=2.5, gt=0.0, le=60.0)

    @field_validator("COMPLIANCE_MODE")
    @classmethod
    def validate_compliance_mode(cls, value: str) -> str:
        """Validate the gateway compliance profile."""
        allowed = {"permissive", "standard", "locked_down"}
        if value not in allowed:
            raise ValueError(f"COMPLIANCE_MODE must be one of {sorted(allowed)}")
        return value

    @field_validator("CRITERIA_FALLBACK_MODE")
    @classmethod
    def validate_fallback_mode(cls, value: str) -> str:
        """Validate the model selection fallback policy."""
        allowed = {"cost_weighted", "latency_weighted", "quality_weighted", "deny"}
        if value not in allowed:
            raise ValueError(f"CRITERIA_FALLBACK_MODE must be one of {sorted(allowed)}")
        return value


settings = PlatformSettings()
