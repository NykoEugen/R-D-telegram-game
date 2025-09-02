import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Telegram RPG game bot."""
    
    # Bot configuration
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Ngrok configuration for local testing
    NGROK_URL = os.getenv("NGROK_URL", "")
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Webhook configuration
    WEBHOOK_PATH = "/webhook"
    WEBHOOK_URL = f"{NGROK_URL}{WEBHOOK_PATH}" if NGROK_URL else ""
    
    # Game configuration
    GAME_NAME = "Fantasy RPG Adventure"
    GAME_DESCRIPTION = "Embark on epic quests in a medieval fantasy world!"
