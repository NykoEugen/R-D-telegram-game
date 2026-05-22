"""
Core configuration module for the Telegram RPG game bot.

This module provides a clean, single source of truth for all configuration settings.
"""

from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration class for the Telegram RPG game bot using Pydantic BaseSettings."""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    # Bot configuration
    bot_token: str = Field(..., env="BOT_TOKEN", description="Telegram bot token")

    # Webhook base URL (triggers webhook mode when set; use ngrok locally, Koyeb/DuckDNS in prod)
    webhook_base_url: Optional[str] = Field(default="", env="WEBHOOK_BASE_URL", description="Base URL for webhook")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL", description="Logging level")
    
    # Webhook configuration
    webhook_path: str = Field(default="/webhook", description="Webhook path")
    webhook_secret: Optional[str] = Field(default=None, env="WEBHOOK_SECRET", description="Webhook secret for security")
    port: int = Field(default=8000, env="PORT", description="Port for webhook server")
    
    # Database configuration
    database_url: str = Field(..., env="DATABASE_URL", description="Database connection URL")

    @validator("database_url")
    def normalize_database_url(cls, v):
        # Neon and some providers give postgres:// or postgresql:// — asyncpg needs +asyncpg scheme
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                v = v.replace(prefix, "postgresql+asyncpg://", 1)
                break
        # asyncpg doesn't understand sslmode/channel_binding — replace with ssl=true
        parsed = urlparse(v)
        params = parse_qs(parsed.query, keep_blank_values=True)
        needs_ssl = params.pop("sslmode", None) is not None
        params.pop("channel_binding", None)
        if needs_ssl:
            params["ssl"] = ["true"]
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))

    
    # Redis configuration
    redis_url: str = Field(..., env="REDIS_URL", description="Redis connection URL")

    @validator("redis_url")
    def normalize_redis_url(cls, v):
        # Upstash sometimes omits scheme — ensure redis:// or rediss:// prefix
        if not v.startswith(("redis://", "rediss://", "unix://")):
            return f"redis://{v}"
        return v
    
    # Game configuration
    game_name: str = Field(default="Fantasy RPG Adventure", description="Name of the game")
    game_description: str = Field(default="Embark on epic quests in a medieval fantasy world!", description="Game description")
    
    # Scene graph configuration
    scenes_file: str = Field(default="app/game/scenes.yaml", description="Path to scenes YAML file")
    default_energy: int = Field(default=100, description="Default player energy")
    max_energy: int = Field(default=100, description="Maximum player energy")
    energy_regeneration_rate: int = Field(default=10, description="Energy regeneration per hour")
    default_risk_threshold: int = Field(default=10, description="Default risk threshold for ending adventures")
    default_step_budget: int = Field(default=4, description="Default step budget for adventures")
    scene_seed: Optional[int] = Field(default=None, env="SCENE_SEED", description="Random seed for scene generation")
    
    @property
    def webhook_url(self) -> str:
        if self.webhook_base_url:
            return f"{self.webhook_base_url}{self.webhook_path}"
        return ""
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is one of the standard levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @validator("port")
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError("port must be between 1 and 65535")
        return v


# Create a global settings instance
settings = Settings()

# Backward compatibility - keep the old Config class for existing imports
class Config:
    """Legacy configuration class for backward compatibility."""
    
    # Bot configuration
    BOT_TOKEN = settings.bot_token

    WEBHOOK_BASE_URL = settings.webhook_base_url
    
    # Logging configuration
    LOG_LEVEL = settings.log_level
    
    # Webhook configuration
    WEBHOOK_PATH = settings.webhook_path
    WEBHOOK_URL = settings.webhook_url
    WEBHOOK_SECRET = settings.webhook_secret
    PORT = settings.port
    
    # Database configuration
    DATABASE_URL = settings.database_url
    
    # Redis configuration
    REDIS_URL = settings.redis_url
    
    # Game configuration
    GAME_NAME = settings.game_name
    GAME_DESCRIPTION = settings.game_description
    
    # Scene graph configuration
    SCENES_FILE = settings.scenes_file
    DEFAULT_ENERGY = settings.default_energy
    MAX_ENERGY = settings.max_energy
    ENERGY_REGENERATION_RATE = settings.energy_regeneration_rate
    DEFAULT_RISK_THRESHOLD = settings.default_risk_threshold
    DEFAULT_STEP_BUDGET = settings.default_step_budget
    SCENE_SEED = settings.scene_seed
