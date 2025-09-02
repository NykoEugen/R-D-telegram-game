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
    openai_api_key: str = Field(..., env="OPENAI_API_KEY", description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-3.5-turbo", 
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
    
    # Game configuration
    game_name: str = Field(default="Fantasy RPG Adventure", description="Name of the game")
    game_description: str = Field(default="Embark on epic quests in a medieval fantasy world!", description="Game description")
    
    @property
    def webhook_url(self) -> str:
        """Generate webhook URL from ngrok URL and webhook path."""
        if self.ngrok_url:
            return f"{self.ngrok_url}{self.webhook_path}"
        return ""
    
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
    
    # Game configuration
    GAME_NAME = settings.game_name
    GAME_DESCRIPTION = settings.game_description
