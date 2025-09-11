"""
AI content generation service for the Telegram RPG game bot.

This module handles AI-powered content generation using OpenAI API.
"""

import asyncio
from typing import Optional, Callable, Awaitable, TypeVar, Dict, List, Any
from datetime import datetime
import httpx
from openai import AsyncOpenAI

from app.core.config import Config
from app.services.logging_service import get_logger
from app.prompts import get_prompts, get_prompt_config

logger = get_logger(__name__)
T = TypeVar("T")


class AIGenerationService:
    """Async service for interacting with OpenAI API to generate game content."""
    _http_client: Optional[httpx.AsyncClient] = None
    _client: Optional[AsyncOpenAI] = None

    # ---- Config defaults
    DEFAULT_MODEL = getattr(Config, "OPENAI_MODEL", "gpt-4o-mini")
    TIMEOUT = 30.0

    @classmethod
    async def _ensure_client(cls) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized and return it."""
        if cls._client is not None:
            return cls._client
        
        # Check if API key is available
        if not Config.OPENAI_API_KEY:
            error_msg = "OpenAI API key is not configured. Please set OPENAI_API_KEY environment variable."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Single async HTTP client per process
            cls._http_client = httpx.AsyncClient(
                verify=True,
                timeout=httpx.Timeout(cls.TIMEOUT),
            )
            cls._client = AsyncOpenAI(
                api_key=Config.OPENAI_API_KEY,
                http_client=cls._http_client,
            )
            logger.info("OpenAI client initialized successfully")
            return cls._client
        except Exception as e:
            logger.error(f"Failed to create Async OpenAI client: {e}", exc_info=True)
            raise

    @classmethod
    async def aclose(cls) -> None:
        """Close clients (call on bot shutdown)."""
        try:
            if cls._client is not None:
                # AsyncOpenAI doesn't have a separate close method - close the transport
                cls._client = None
            if cls._http_client is not None:
                await cls._http_client.aclose()
                cls._http_client = None
        except Exception:
            logger.warning("Failed to close HTTP client", exc_info=True)

    @classmethod
    def is_configured(cls) -> bool:
        """Check if the service is properly configured."""
        return bool(Config.OPENAI_API_KEY and Config.OPENAI_API_KEY.strip())

    @classmethod
    def get_config_status(cls) -> dict:
        """Get the current configuration status of the service."""
        quest_config = get_prompt_config("quest")
        world_config = get_prompt_config("world")
        
        return {
            "api_key_configured": bool(Config.OPENAI_API_KEY and Config.OPENAI_API_KEY.strip()),
            "model": cls.DEFAULT_MODEL,
            "timeout": cls.TIMEOUT,
            "max_tokens_quest": quest_config["max_tokens"],
            "max_tokens_world": world_config["max_tokens"],
            "temperature_quest": quest_config["temperature"],
            "temperature_world": world_config["temperature"],
        }

    # ---- Retry helper
    @staticmethod
    async def _with_retries(
        fn: Callable[[], Awaitable[T]],
        attempts: int = 3,
        base_delay: float = 0.5,
    ) -> T:
        """Execute function with exponential backoff retry logic."""
        last_err: Optional[Exception] = None
        for i in range(attempts):
            try:
                return await fn()
            except Exception as e:
                last_err = e
                # Exponential backoff with jitter
                delay = base_delay * (2 ** i)
                await asyncio.sleep(delay)
        assert last_err is not None
        raise last_err

    # ---- Public API
    @classmethod
    async def generate_quest_description(cls, language: str = "en") -> Optional[str]:
        """Generate a fantasy quest description using OpenAI."""
        try:
            client = await cls._ensure_client()
            prompts = get_prompts(language, "quest")
            config = get_prompt_config("quest")

            async def _call():
                resp = await client.chat.completions.create(
                    model=cls.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": prompts["system"]},
                        {"role": "user", "content": prompts["user"]},
                    ],
                    max_tokens=config["max_tokens"],
                    temperature=config["temperature"],
                )
                return resp

            response = await cls._with_retries(_call)
            content = (response.choices[0].message.content or "").strip() if response.choices else ""
            if not content:
                logger.warning("Empty quest description from OpenAI")
                return None

            logger.info(
                "Generated quest description",
                extra={
                    "model": cls.DEFAULT_MODEL,
                    "language": language,
                    "max_tokens": config["max_tokens"],
                    "temperature": config["temperature"],
                },
            )
            return content

        except Exception as e:
            logger.error(
                "Failed to generate quest description",
                exc_info=True,
                extra={"model": cls.DEFAULT_MODEL, "language": language, "error_type": type(e).__name__},
            )
            return None

    @classmethod
    async def generate_world_description(cls, language: str = "en") -> Optional[str]:
        """Generate a fantasy world description using OpenAI."""
        try:
            client = await cls._ensure_client()
            prompts = get_prompts(language, "world")
            config = get_prompt_config("world")

            async def _call():
                resp = await client.chat.completions.create(
                    model=cls.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": prompts["system"]},
                        {"role": "user", "content": prompts["user"]},
                    ],
                    max_tokens=config["max_tokens"],
                    temperature=config["temperature"],
                )
                return resp

            response = await cls._with_retries(_call)
            content = (response.choices[0].message.content or "").strip() if response.choices else ""
            if not content:
                logger.warning("Empty world description from OpenAI")
                return None

            logger.info(
                "Generated world description",
                extra={
                    "model": cls.DEFAULT_MODEL,
                    "language": language,
                    "max_tokens": config["max_tokens"],
                    "temperature": config["temperature"],
                },
            )
            return content

        except Exception as e:
            logger.error(
                "Failed to generate world description",
                exc_info=True,
                extra={"model": cls.DEFAULT_MODEL, "language": language, "error_type": type(e).__name__},
            )
            return None

    # ---- Quest System Functions (Mock Data Implementation)
    
    @classmethod
    async def generate_offer(cls, language: str = "en") -> Dict[str, Any]:
        """
        Generate a quest offer with mock data.
        
        Returns a dictionary containing quest offer information including
        title, hook, questgiver, and basic quest metadata.
        """
        logger.info(f"Generating quest offer (mock data) for language: {language}")
        
        # Mock quest offers with different themes
        mock_offers = [
            {
                "title": "The Lost Merchant's Cargo",
                "hook": "A desperate merchant approaches you in the tavern, his eyes filled with worry. 'Please, brave adventurer, my cargo wagon was ambushed by bandits three days ago. I need someone to recover my goods before they're sold on the black market!'",
                "questgiver_name": "Marcus the Merchant",
                "quest_type": "recovery",
                "risk_level": 2,
                "reward_gold": 150,
                "reward_xp": 100,
                "faction": "merchants_guild"
            },
            {
                "title": "The Haunted Crypt",
                "hook": "The village elder's voice trembles as he speaks: 'Strange lights have been seen in the old crypt at night, and our livestock have been disappearing. We fear the restless dead have awakened. Will you investigate?'",
                "questgiver_name": "Elder Thorne",
                "quest_type": "investigation",
                "risk_level": 3,
                "reward_gold": 200,
                "reward_xp": 150,
                "faction": "village_council"
            },
            {
                "title": "The Bandit King's Challenge",
                "hook": "A mysterious figure in a dark cloak slides a note across your table: 'The Bandit King seeks worthy opponents. Meet at the crossroads at midnight if you dare face his challenge. Bring gold or bring steel.'",
                "questgiver_name": "The Shadow",
                "quest_type": "combat",
                "risk_level": 4,
                "reward_gold": 300,
                "reward_xp": 200,
                "faction": None
            },
            {
                "title": "The Missing Apprentice",
                "hook": "Master Alchemist Zephyr wrings his hands nervously: 'My apprentice went to gather rare herbs in the Whispering Woods three days ago and hasn't returned. The woods are dangerous, but I fear something worse has befallen him.'",
                "questgiver_name": "Master Zephyr",
                "quest_type": "rescue",
                "risk_level": 2,
                "reward_gold": 180,
                "reward_xp": 120,
                "faction": "alchemists_guild"
            },
            {
                "title": "The Dragon's Riddle",
                "hook": "An ancient dragon's voice echoes through the valley: 'I have grown weary of this world, but before I depart, I seek one worthy of my treasure. Answer my riddle correctly, and my hoard is yours. Answer incorrectly, and face my wrath.'",
                "questgiver_name": "Vaelthar the Ancient",
                "quest_type": "puzzle",
                "risk_level": 5,
                "reward_gold": 500,
                "reward_xp": 300,
                "faction": None
            }
        ]
        
        # Select a random offer (in a real implementation, this would be more sophisticated)
        import random
        selected_offer = random.choice(mock_offers)
        
        # Add quest ID and timestamp
        quest_id = f"quest_{random.randint(1000, 9999)}"
        selected_offer["quest_id"] = quest_id
        selected_offer["created_at"] = datetime.now().isoformat()
        
        logger.info(f"Generated quest offer: {selected_offer['title']} (ID: {quest_id})")
        return selected_offer

    @classmethod
    async def generate_details(cls, title: str, language: str = "en") -> Dict[str, Any]:
        """
        Generate detailed quest information based on the quest title.
        
        Args:
            title: The quest title to generate details for
            language: Language for the generated content
            
        Returns a dictionary containing detailed quest information.
        """
        logger.info(f"Generating quest details for: {title} (mock data)")
        
        # Mock detailed quest information based on common quest types
        details_templates = {
            "lost": {
                "description": "The merchant's cargo wagon was ambushed on the Old Trade Road, just north of the Whispering Woods. The bandits took everything of value, including rare spices, silk, and a mysterious locked chest that the merchant refuses to discuss.",
                "objectives": [
                    "Investigate the ambush site for clues",
                    "Track the bandits to their hideout",
                    "Recover the stolen cargo",
                    "Return the goods to Marcus"
                ],
                "locations": ["Old Trade Road", "Whispering Woods", "Bandit Hideout"],
                "npcs": ["Marcus the Merchant", "Bandit Leader", "Local Trader"],
                "items": ["Stolen Cargo", "Bandit Map", "Mysterious Chest"]
            },
            "haunted": {
                "description": "The ancient crypt has been sealed for over a century, but recent earthquakes have cracked its foundation. Strange blue lights dance within its depths at night, and the villagers report hearing otherworldly wails. The crypt was built to house the remains of a powerful necromancer who was defeated long ago.",
                "objectives": [
                    "Enter the crypt and investigate the source of the lights",
                    "Discover what has disturbed the ancient burial site",
                    "Put the restless spirits to rest",
                    "Seal the crypt to prevent future disturbances"
                ],
                "locations": ["Ancient Crypt", "Village Cemetery", "Necromancer's Chamber"],
                "npcs": ["Elder Thorne", "Restless Spirits", "Crypt Guardian"],
                "items": ["Necromancer's Staff", "Ancient Tome", "Sealing Rune"]
            },
            "bandit": {
                "description": "The Bandit King has been terrorizing the region for months, but now he seeks to legitimize his rule through combat. He has challenged all who would oppose him to a duel at the crossroads. The winner takes all - his gold, his territory, and his life.",
                "objectives": [
                    "Meet the Bandit King at the crossroads at midnight",
                    "Accept his challenge to single combat",
                    "Defeat him in honorable combat",
                    "Claim his territory and treasure"
                ],
                "locations": ["Crossroads", "Bandit Camp", "Hidden Treasure Vault"],
                "npcs": ["The Bandit King", "His Lieutenants", "Local Informant"],
                "items": ["Bandit King's Sword", "Territory Map", "Treasure Key"]
            },
            "missing": {
                "description": "The Whispering Woods are known for their dangerous creatures and magical properties. The apprentice was sent to gather rare moonbloom flowers that only bloom during the new moon. The woods have a reputation for making people lose their way, and some never return.",
                "objectives": [
                    "Enter the Whispering Woods safely",
                    "Search for signs of the missing apprentice",
                    "Gather the required moonbloom flowers",
                    "Rescue the apprentice and return to Master Zephyr"
                ],
                "locations": ["Whispering Woods", "Moonbloom Grove", "Ancient Tree"],
                "npcs": ["Master Zephyr", "Missing Apprentice", "Woodland Spirits"],
                "items": ["Moonbloom Flowers", "Apprentice's Journal", "Spirit Blessing"]
            },
            "dragon": {
                "description": "Vaelthar the Ancient is one of the last great dragons, having lived for over a thousand years. He has grown weary of the world and seeks to pass on his vast treasure to someone worthy. His riddle is said to test not just knowledge, but wisdom and character.",
                "objectives": [
                    "Journey to the Dragon's Lair in the mountains",
                    "Listen to Vaelthar's ancient riddle",
                    "Answer the riddle correctly",
                    "Claim the dragon's treasure hoard"
                ],
                "locations": ["Dragon's Lair", "Mountain Pass", "Treasure Chamber"],
                "npcs": ["Vaelthar the Ancient", "Dragon Guardians", "Ancient Sage"],
                "items": ["Dragon's Treasure", "Ancient Wisdom", "Dragon Scale"]
            }
        }
        
        # Determine quest type from title and select appropriate details
        title_lower = title.lower()
        quest_type = "lost"  # default
        
        if "haunted" in title_lower or "crypt" in title_lower:
            quest_type = "haunted"
        elif "bandit" in title_lower or "challenge" in title_lower:
            quest_type = "bandit"
        elif "missing" in title_lower or "apprentice" in title_lower:
            quest_type = "missing"
        elif "dragon" in title_lower or "riddle" in title_lower:
            quest_type = "dragon"
        
        details = details_templates.get(quest_type, details_templates["lost"])
        
        # Add quest metadata
        details["quest_title"] = title
        details["estimated_duration"] = "2-4 hours"
        details["difficulty"] = "Medium"
        details["recommended_level"] = 3
        
        logger.info(f"Generated quest details for: {title} (type: {quest_type})")
        return details

    @classmethod
    async def generate_scenes(cls, title: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Generate a sequence of scenes for the quest based on the title.
        
        Args:
            title: The quest title to generate scenes for
            language: Language for the generated content
            
        Returns a list of scene dictionaries.
        """
        logger.info(f"Generating scenes for quest: {title} (mock data)")
        
        # Mock scene templates based on quest types
        scene_templates = {
            "lost": [
                {
                    "scene_id": "investigation",
                    "title": "The Ambush Site",
                    "description": "You arrive at the scene of the ambush. The merchant's wagon lies overturned, its contents scattered across the muddy road. Deep wagon tracks lead away from the scene, and you notice several sets of boot prints in the mud.",
                    "actions": [
                        {"id": "examine_wagon", "label": "Examine the overturned wagon", "type": "investigate"},
                        {"id": "follow_tracks", "label": "Follow the wagon tracks", "type": "track"},
                        {"id": "search_area", "label": "Search the surrounding area", "type": "search"}
                    ],
                    "outcomes": {
                        "examine_wagon": "You find a torn piece of cloth caught on a splinter - it appears to be from a bandit's cloak.",
                        "follow_tracks": "The tracks lead north toward the Whispering Woods. The wagon was heavily loaded.",
                        "search_area": "You discover a dropped coin purse containing a few silver pieces and a crude map."
                    }
                },
                {
                    "scene_id": "tracking",
                    "title": "Following the Trail",
                    "description": "Following the wagon tracks through the forest, you come across a small clearing where the bandits appear to have stopped. There are signs of a campfire and several empty wine bottles.",
                    "actions": [
                        {"id": "examine_camp", "label": "Examine the campsite", "type": "investigate"},
                        {"id": "continue_tracking", "label": "Continue following the trail", "type": "track"},
                        {"id": "rest_here", "label": "Rest here before continuing", "type": "rest"}
                    ],
                    "outcomes": {
                        "examine_camp": "You find a discarded bandit mask and overhear distant voices arguing about dividing the loot.",
                        "continue_tracking": "The trail becomes clearer as you approach what must be their hideout.",
                        "rest_here": "You regain some energy but hear the bandits moving further away."
                    }
                },
                {
                    "scene_id": "confrontation",
                    "title": "The Bandit Hideout",
                    "description": "You've found the bandits' hideout - a cave entrance hidden behind a waterfall. You can see the stolen wagon parked outside, and hear the bandits celebrating their successful raid inside.",
                    "actions": [
                        {"id": "sneak_in", "label": "Sneak into the hideout", "type": "stealth"},
                        {"id": "confront_bandits", "label": "Confront the bandits directly", "type": "combat"},
                        {"id": "negotiate", "label": "Try to negotiate for the cargo", "type": "diplomacy"}
                    ],
                    "outcomes": {
                        "sneak_in": "You successfully sneak in and can see the cargo being divided among the bandits.",
                        "confront_bandits": "The bandits are caught off guard but quickly draw their weapons.",
                        "negotiate": "The bandit leader laughs and demands twice the cargo's value in gold."
                    }
                }
            ],
            "haunted": [
                {
                    "scene_id": "approach",
                    "title": "The Ancient Crypt",
                    "description": "You stand before the ancient crypt, its stone entrance cracked and weathered. Strange blue lights flicker within the darkness, and you can hear otherworldly whispers carried on the wind.",
                    "actions": [
                        {"id": "enter_crypt", "label": "Enter the crypt", "type": "explore"},
                        {"id": "examine_exterior", "label": "Examine the crypt's exterior", "type": "investigate"},
                        {"id": "cast_protection", "label": "Cast a protection spell", "type": "magic"}
                    ],
                    "outcomes": {
                        "enter_crypt": "You step into the darkness, your torch casting dancing shadows on the walls.",
                        "examine_exterior": "You notice ancient runes carved into the stone that seem to glow faintly.",
                        "cast_protection": "A warm light surrounds you, and the whispers seem to grow quieter."
                    }
                },
                {
                    "scene_id": "chamber",
                    "title": "The Burial Chamber",
                    "description": "You enter a large chamber filled with stone sarcophagi. The blue lights you saw earlier are actually will-o'-wisps dancing between the tombs. The air is thick with ancient magic.",
                    "actions": [
                        {"id": "examine_sarcophagi", "label": "Examine the sarcophagi", "type": "investigate"},
                        {"id": "follow_wisps", "label": "Follow the will-o'-wisps", "type": "explore"},
                        {"id": "read_inscriptions", "label": "Read the tomb inscriptions", "type": "study"}
                    ],
                    "outcomes": {
                        "examine_sarcophagi": "One of the sarcophagi has been disturbed, its lid partially open.",
                        "follow_wisps": "The wisps lead you deeper into the crypt, toward a hidden chamber.",
                        "read_inscriptions": "The inscriptions tell of a powerful necromancer who was sealed here long ago."
                    }
                },
                {
                    "scene_id": "confrontation",
                    "title": "The Necromancer's Rest",
                    "description": "You've found the source of the disturbance - the necromancer's tomb has been opened, and his restless spirit has been awakened. He floats before you, his eyes burning with otherworldly fire.",
                    "actions": [
                        {"id": "banish_spirit", "label": "Attempt to banish the spirit", "type": "magic"},
                        {"id": "seal_tomb", "label": "Try to seal the tomb", "type": "ritual"},
                        {"id": "reason_with_spirit", "label": "Try to reason with the spirit", "type": "diplomacy"}
                    ],
                    "outcomes": {
                        "banish_spirit": "The spirit shrieks as your magic begins to weaken its hold on this world.",
                        "seal_tomb": "You begin the ancient sealing ritual, but the spirit resists your efforts.",
                        "reason_with_spirit": "The spirit pauses, its burning eyes studying you with ancient wisdom."
                    }
                }
            ]
        }
        
        # Determine quest type and select appropriate scenes
        title_lower = title.lower()
        quest_type = "lost"  # default
        
        if "haunted" in title_lower or "crypt" in title_lower:
            quest_type = "haunted"
        elif "bandit" in title_lower or "challenge" in title_lower:
            quest_type = "lost"  # Use similar structure
        elif "missing" in title_lower or "apprentice" in title_lower:
            quest_type = "lost"  # Use similar structure
        elif "dragon" in title_lower or "riddle" in title_lower:
            quest_type = "lost"  # Use similar structure
        
        scenes = scene_templates.get(quest_type, scene_templates["lost"])
        
        # Add scene metadata
        for i, scene in enumerate(scenes):
            scene["scene_number"] = i + 1
            scene["is_combat_scene"] = "combat" in scene.get("actions", [{}])[0].get("type", "")
            scene["energy_cost"] = 10 if scene["is_combat_scene"] else 5
        
        logger.info(f"Generated {len(scenes)} scenes for quest: {title}")
        return scenes

    @classmethod
    async def resolve_combat_turn(cls, state: Dict[str, Any], action: str, language: str = "en") -> Dict[str, Any]:
        """
        Resolve a combat turn based on the current state and player action.
        
        Args:
            state: Current combat state dictionary
            action: Player's chosen action
            language: Language for the generated content
            
        Returns updated combat state with turn resolution.
        """
        logger.info(f"Resolving combat turn for action: {action} (mock data)")
        
        # Extract combat state information
        player_hp = state.get("player_hp", 100)
        player_max_hp = state.get("player_max_hp", 100)
        player_attack = state.get("player_attack", 15)
        player_defense = state.get("player_defense", 10)
        
        enemy_hp = state.get("enemy_hp", 80)
        enemy_max_hp = state.get("enemy_max_hp", 80)
        enemy_attack = state.get("enemy_attack", 12)
        enemy_defense = state.get("enemy_defense", 8)
        enemy_name = state.get("enemy_name", "Bandit")
        
        turn_count = state.get("turn_count", 0)
        combat_log = state.get("combat_log", [])
        
        # Mock combat resolution
        import random
        
        # Player's turn
        if turn_count % 2 == 0:
            if action == "attack":
                # Calculate damage
                base_damage = player_attack - enemy_defense
                damage = max(1, base_damage + random.randint(-2, 3))
                enemy_hp = max(0, enemy_hp - damage)
                
                combat_log.append(f"You attack {enemy_name} for {damage} damage!")
                if enemy_hp <= 0:
                    combat_log.append(f"{enemy_name} has been defeated!")
            elif action == "defend":
                # Increase defense for next turn
                player_defense += 5
                combat_log.append("You take a defensive stance, increasing your defense!")
            elif action == "use_item":
                # Heal player
                heal_amount = random.randint(15, 25)
                player_hp = min(player_max_hp, player_hp + heal_amount)
                combat_log.append(f"You use a healing potion and recover {heal_amount} HP!")
            else:
                combat_log.append("You hesitate, unsure of what to do...")
        
        # Enemy's turn (if still alive)
        if enemy_hp > 0 and turn_count % 2 == 1:
            enemy_actions = ["attack", "defend", "special_attack"]
            enemy_action = random.choice(enemy_actions)
            
            if enemy_action == "attack":
                base_damage = enemy_attack - player_defense
                damage = max(1, base_damage + random.randint(-1, 2))
                player_hp = max(0, player_hp - damage)
                combat_log.append(f"{enemy_name} attacks you for {damage} damage!")
            elif enemy_action == "defend":
                enemy_defense += 3
                combat_log.append(f"{enemy_name} takes a defensive stance!")
            elif enemy_action == "special_attack":
                # Special attack does more damage but is less accurate
                if random.random() < 0.7:  # 70% chance to hit
                    damage = enemy_attack + random.randint(3, 6)
                    player_hp = max(0, player_hp - damage)
                    combat_log.append(f"{enemy_name} uses a special attack for {damage} damage!")
                else:
                    combat_log.append(f"{enemy_name}'s special attack misses!")
        
        # Update turn count
        turn_count += 1
        
        # Determine combat outcome
        combat_over = player_hp <= 0 or enemy_hp <= 0
        winner = None
        if combat_over:
            if player_hp <= 0:
                winner = "enemy"
                combat_log.append("You have been defeated!")
            else:
                winner = "player"
                combat_log.append("Victory! You have won the combat!")
        
        # Return updated state
        updated_state = {
            "player_hp": player_hp,
            "player_max_hp": player_max_hp,
            "player_attack": player_attack,
            "player_defense": player_defense,
            "enemy_hp": enemy_hp,
            "enemy_max_hp": enemy_max_hp,
            "enemy_attack": enemy_attack,
            "enemy_defense": enemy_defense,
            "enemy_name": enemy_name,
            "turn_count": turn_count,
            "combat_log": combat_log,
            "combat_over": combat_over,
            "winner": winner
        }
        
        logger.info(f"Combat turn resolved. Player HP: {player_hp}, Enemy HP: {enemy_hp}, Turn: {turn_count}")
        return updated_state
