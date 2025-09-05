"""
Core configuration module for the Telegram RPG game bot.

This module provides a clean, single source of truth for all configuration settings.
"""

import os
from typing import Optional, Literal
from pydantic import Field, validator
from pydantic_settings import BaseSettings

# Available OpenAI models for chat completion
AVAILABLE_OPENAI_MODELS = [
    # GPT-4 Models
    "gpt-4o",
    "gpt-4o-mini", 
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4",
    "gpt-4-32k",
    
    # GPT-3.5 Models
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-instruct",
    
    # Legacy Models
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k-0613",
    "gpt-4-0613",
    "gpt-4-32k-0613",
]


class Settings(BaseSettings):
    """Configuration class for the Telegram RPG game bot using Pydantic BaseSettings."""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    # Bot configuration
    bot_token: str = Field(..., env="BOT_TOKEN", description="Telegram bot token")
    
    # OpenAI configuration
    openai_enabled: bool = Field(default=True, env="OPENAI_ENABLED", description="Whether OpenAI is enabled")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY", description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-4o-mini", 
        env="OPENAI_MODEL", 
        description="OpenAI model to use for chat completion"
    )
    
    # Ngrok configuration for local testing
    ngrok_url: Optional[str] = Field(default="", env="NGROK_URL", description="Ngrok URL for local testing")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL", description="Logging level")
    
    # Webhook configuration
    webhook_path: str = Field(default="/webhook", description="Webhook path")
    webhook_secret: Optional[str] = Field(default=None, env="WEBHOOK_SECRET", description="Webhook secret for security")
    port: int = Field(default=8000, env="PORT", description="Port for webhook server")
    
    # Database configuration
    database_url: str = Field(..., env="DATABASE_URL", description="Database connection URL")
    
    # Redis configuration
    redis_url: str = Field(..., env="REDIS_URL", description="Redis connection URL")
    
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
        """Generate webhook URL from ngrok URL and webhook path."""
        if self.ngrok_url:
            return f"{self.ngrok_url}{self.webhook_path}"
        return ""
    
    @validator("openai_enabled", pre=True)
    def validate_openai_enabled(cls, v):
        """Convert string environment variable to boolean."""
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "on")
        return bool(v)
    
    @validator("openai_model")
    def validate_openai_model(cls, v):
        """Validate OpenAI model is one of the available models."""
        if v not in AVAILABLE_OPENAI_MODELS:
            raise ValueError(f"openai_model must be one of {AVAILABLE_OPENAI_MODELS}")
        return v
    
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
    
    # OpenAI configuration
    OPENAI_ENABLED = settings.openai_enabled
    OPENAI_API_KEY = settings.openai_api_key
    OPENAI_MODEL = settings.openai_model
    
    # Ngrok configuration for local testing
    NGROK_URL = settings.ngrok_url
    
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
