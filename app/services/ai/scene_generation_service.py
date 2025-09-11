"""
AI Scene Generation Service for the Telegram RPG game bot.

This module handles AI-powered scene generation with controlled choice mapping.
"""

import asyncio
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from app.core.config import Config
from app.services.logging_service import get_logger
from app.services.ai.generation_service import AIGenerationService
from app.prompts import get_prompts, get_prompt_config
from app.game.actions import Action

logger = get_logger(__name__)


@dataclass
class AIScene:
    """Represents an AI-generated scene with description and choices."""
    description: str
    choices: List[Tuple[str, Action]]  # (choice_text, mapped_action)
    scene_type: str = "ai_generated"


class AISceneGenerationService:
    """Service for generating AI scenes with controlled choice mapping."""
    
    # Mapping keywords to actions
    CHOICE_MAPPING = {
        # Scout-related keywords
        "scout": Action.SCOUT,
        "investigate": Action.SCOUT,
        "examine": Action.SCOUT,
        "search": Action.SCOUT,
        "explore": Action.SCOUT,
        "look": Action.SCOUT,
        "check": Action.SCOUT,
        "observe": Action.SCOUT,
        "survey": Action.SCOUT,
        "recon": Action.SCOUT,
        
        # Fight-related keywords
        "fight": Action.FIGHT,
        "attack": Action.FIGHT,
        "battle": Action.FIGHT,
        "strike": Action.FIGHT,
        "combat": Action.FIGHT,
        "engage": Action.FIGHT,
        "confront": Action.FIGHT,
        "challenge": Action.FIGHT,
        "assault": Action.FIGHT,
        "charge": Action.FIGHT,
        
        # Retreat-related keywords
        "retreat": Action.RETREAT,
        "flee": Action.RETREAT,
        "escape": Action.RETREAT,
        "withdraw": Action.RETREAT,
        "back": Action.RETREAT,
        "leave": Action.RETREAT,
        "run": Action.RETREAT,
        "avoid": Action.RETREAT,
        "evade": Action.RETREAT,
        "hide": Action.RETREAT,
        
        # Talk-related keywords
        "talk": Action.TALK,
        "speak": Action.TALK,
        "negotiate": Action.TALK,
        "persuade": Action.TALK,
        "convince": Action.TALK,
        "bargain": Action.TALK,
        "diplomacy": Action.TALK,
        "discuss": Action.TALK,
        "chat": Action.TALK,
        "reason": Action.TALK,
        
        # Picklock-related keywords
        "picklock": Action.PICKLOCK,
        "unlock": Action.PICKLOCK,
        "open": Action.PICKLOCK,
        "break": Action.PICKLOCK,
        "force": Action.PICKLOCK,
        "crack": Action.PICKLOCK,
        "bypass": Action.PICKLOCK,
        "disable": Action.PICKLOCK,
        "tamper": Action.PICKLOCK,
        "manipulate": Action.PICKLOCK,
    }
    
    @classmethod
    async def generate_scene(cls, language: str = "en") -> Optional[AIScene]:
        """Generate a complete AI scene with description and mapped choices."""
        try:
            # Generate scene description
            description = await cls._generate_scene_description(language)
            if not description:
                logger.error("Failed to generate scene description")
                return None
            
            # Generate choices
            choices = await cls._generate_choices(description, language)
            if not choices:
                logger.error("Failed to generate choices")
                return None
            
            # Map choices to actions
            mapped_choices = cls._map_choices_to_actions(choices)
            if not mapped_choices:
                logger.error("Failed to map choices to actions")
                return None
            
            return AIScene(
                description=description,
                choices=mapped_choices,
                scene_type="ai_generated"
            )
            
        except Exception as e:
            logger.error(f"Error generating AI scene: {e}", exc_info=True)
            return None
    
    @classmethod
    async def _generate_scene_description(cls, language: str) -> Optional[str]:
        """Generate scene description using AI."""
        try:
            client = await AIGenerationService._ensure_client()
            prompts = get_prompts(language, "scene")
            config = get_prompt_config("scene")

            async def _call():
                resp = await client.chat.completions.create(
                    model=AIGenerationService.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": prompts["system"]},
                        {"role": "user", "content": prompts["user"]},
                    ],
                    max_tokens=config["max_tokens"],
                    temperature=config["temperature"],
                )
                return resp

            response = await AIGenerationService._with_retries(_call)
            content = (response.choices[0].message.content or "").strip() if response.choices else ""
            
            if not content:
                logger.warning("Empty scene description from OpenAI")
                return None

            logger.info(
                "Generated scene description",
                extra={
                    "model": AIGenerationService.DEFAULT_MODEL,
                    "language": language,
                    "max_tokens": config["max_tokens"],
                    "temperature": config["temperature"],
                },
            )
            return content

        except Exception as e:
            logger.error(
                "Failed to generate scene description",
                exc_info=True,
                extra={"model": AIGenerationService.DEFAULT_MODEL, "language": language, "error_type": type(e).__name__},
            )
            return None
    
    @classmethod
    async def _generate_choices(cls, scene_description: str, language: str) -> Optional[List[str]]:
        """Generate choice options using AI."""
        try:
            client = await AIGenerationService._ensure_client()
            prompts = get_prompts(language, "choices")
            config = get_prompt_config("choices")

            # Format the user prompt with scene description
            user_prompt = prompts["user"].format(scene_description=scene_description)

            async def _call():
                resp = await client.chat.completions.create(
                    model=AIGenerationService.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": prompts["system"]},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=config["max_tokens"],
                    temperature=config["temperature"],
                )
                return resp

            response = await AIGenerationService._with_retries(_call)
            content = (response.choices[0].message.content or "").strip() if response.choices else ""
            
            if not content:
                logger.warning("Empty choices from OpenAI")
                return None

            # Parse choices from the response
            choices = cls._parse_choices(content)
            if len(choices) != 3:
                logger.warning(f"Expected 3 choices, got {len(choices)}: {choices}")
                # Generate fallback choices if parsing fails
                choices = cls._generate_fallback_choices()

            logger.info(
                "Generated choices",
                extra={
                    "model": AIGenerationService.DEFAULT_MODEL,
                    "language": language,
                    "choices_count": len(choices),
                    "choices": choices,
                },
            )
            return choices

        except Exception as e:
            logger.error(
                "Failed to generate choices",
                exc_info=True,
                extra={"model": AIGenerationService.DEFAULT_MODEL, "language": language, "error_type": type(e).__name__},
            )
            return None
    
    @classmethod
    def _parse_choices(cls, content: str) -> List[str]:
        """Parse choices from AI response."""
        choices = []
        
        # Try different parsing patterns
        patterns = [
            r'(\d+[\.\)]\s*)([^\n]+)',  # "1. Choice text"
            r'([A-C][\.\)]\s*)([^\n]+)',  # "A. Choice text"
            r'^([^\n]+)$',  # One choice per line
            r'•\s*([^\n]+)',  # "• Choice text"
            r'-\s*([^\n]+)',  # "- Choice text"
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    choice_text = match.group(-1).strip()  # Get the last group (the actual choice)
                    if choice_text and len(choice_text) <= 20:  # Reasonable length
                        choices.append(choice_text)
                        break
        
        # If no patterns matched, try splitting by common separators
        if not choices:
            for separator in ['\n', '|', ';', ',']:
                parts = content.split(separator)
                if len(parts) >= 3:
                    choices = [part.strip() for part in parts[:3] if part.strip()]
                    break
        
        return choices[:3]  # Ensure we only return up to 3 choices
    
    @classmethod
    def _generate_fallback_choices(cls) -> List[str]:
        """Generate fallback choices if AI generation fails."""
        return [
            "Scout Area",
            "Fight",
            "Retreat"
        ]
    
    @classmethod
    def _map_choices_to_actions(cls, choices: List[str]) -> List[Tuple[str, Action]]:
        """Map choice texts to predefined actions."""
        mapped_choices = []
        
        for choice in choices:
            choice_lower = choice.lower()
            mapped_action = None
            
            # Find the best matching action based on keywords
            best_match_score = 0
            for keyword, action in cls.CHOICE_MAPPING.items():
                if keyword in choice_lower:
                    # Calculate match score (longer keywords get higher priority)
                    score = len(keyword)
                    if score > best_match_score:
                        best_match_score = score
                        mapped_action = action
            
            # If no keyword match found, use a default mapping based on position
            if not mapped_action:
                if len(mapped_choices) == 0:
                    mapped_action = Action.SCOUT
                elif len(mapped_choices) == 1:
                    mapped_action = Action.FIGHT
                else:
                    mapped_action = Action.RETREAT
            
            mapped_choices.append((choice, mapped_action))
        
        return mapped_choices
    
    @classmethod
    def get_available_actions(cls) -> List[Action]:
        """Get list of available actions for AI scenes."""
        return [Action.SCOUT, Action.FIGHT, Action.RETREAT, Action.TALK, Action.PICKLOCK]
