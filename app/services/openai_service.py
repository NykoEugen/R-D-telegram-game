import openai
from typing import Optional
from app.config import Config
from app.services.logging_service import get_logger

# Configure OpenAI client
openai.api_key = Config.OPENAI_API_KEY

logger = get_logger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI API to generate game content."""
    
    @staticmethod
    async def generate_quest_description() -> Optional[str]:
        """
        Generate a fantasy quest description using OpenAI API.
        
        Returns:
            str: Generated quest description or None if failed
        """
        try:
            response = await openai.ChatCompletion.acreate(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a master storyteller creating epic fantasy quests in a medieval D&D style world. Keep descriptions concise (2-3 sentences) and engaging."
                    },
                    {
                        "role": "user",
                        "content": "Generate a short, exciting fantasy quest description for a medieval RPG game. Include a quest objective and a hint of danger or reward."
                    }
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            quest_description = response.choices[0].message.content.strip()
            logger.info("Successfully generated quest description via OpenAI API",
                       model=Config.OPENAI_MODEL,
                       max_tokens=150,
                       temperature=0.8)
            return quest_description
            
        except Exception as e:
            logger.error("Failed to generate quest description",
                        model=Config.OPENAI_MODEL,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return None
    
    @staticmethod
    async def generate_world_description() -> Optional[str]:
        """
        Generate a fantasy world description using OpenAI API.
        
        Returns:
            str: Generated world description or None if failed
        """
        try:
            response = await openai.ChatCompletion.acreate(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are describing a rich medieval fantasy world similar to Dungeons & Dragons. Keep descriptions vivid but concise (2-3 sentences)."
                    },
                    {
                        "role": "user",
                        "content": "Describe a medieval fantasy world with magic, dragons, and epic adventures. Make it sound exciting and immersive."
                    }
                ],
                max_tokens=120,
                temperature=0.7
            )
            
            world_description = response.choices[0].message.content.strip()
            logger.info("Successfully generated world description via OpenAI API",
                       model=Config.OPENAI_MODEL,
                       max_tokens=120,
                       temperature=0.7)
            return world_description
            
        except Exception as e:
            logger.error("Failed to generate world description",
                        model=Config.OPENAI_MODEL,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return None
