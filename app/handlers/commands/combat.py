"""
Combat command handlers for the Telegram RPG game bot.

This module handles combat-related commands and integrates combat
with the existing game systems.
"""

from typing import Dict, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.models.combat import EnemyGenerator
from app.models.player import Player
from app.handlers.combat import CombatHandler
from app.services.i18n_service import I18nService
from app.services.fsm_service import FSMStateService


class CombatCommandHandler:
    """Handles combat-related commands."""
    
    def __init__(self, i18n_service: I18nService, fsm_service: FSMStateService):
        self.i18n_service = i18n_service
        self.fsm_service = fsm_service
        self.combat_handler = CombatHandler(i18n_service, fsm_service)
        self.router = Router()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup combat command handlers."""
        self.router.message.register(
            self.handle_combat_command,
            F.text.startswith("/combat")
        )
        self.router.message.register(
            self.handle_fight_command,
            F.text.startswith("/fight")
        )
        self.router.message.register(
            self.handle_battle_command,
            F.text.startswith("/battle")
        )
    
    async def handle_combat_command(self, message: Message, context: FSMContext) -> None:
        """Handle /combat command."""
        language = self.i18n_service.get_user_language(message.from_user.id)
        
        # Get player data
        player_data = await self._get_player_data(message.from_user.id)
        if not player_data:
            await message.answer(
                await self.i18n_service.get_text("character.stats.no_character", language)
            )
            return
        
        # Check if player is already in combat
        current_state = await context.get_state()
        if current_state and "combat" in str(current_state).lower():
            await message.answer("You are already in combat!")
            return
        
        # Start combat with random enemy
        enemy_types = ["goblin", "orc", "skeleton"]
        import random
        enemy_type = random.choice(enemy_types)
        
        await self.combat_handler.start_combat(
            message, context, player_data, enemy_type
        )
    
    async def handle_fight_command(self, message: Message, context: FSMContext) -> None:
        """Handle /fight command (alias for /combat)."""
        await self.handle_combat_command(message, context)
    
    async def handle_battle_command(self, message: Message, context: FSMContext) -> None:
        """Handle /battle command (alias for /combat)."""
        await self.handle_combat_command(message, context)
    
    async def _get_player_data(self, user_id: int) -> Optional[Dict]:
        """Get player data from database."""
        try:
            # This would typically fetch from database
            # For now, return a mock player data structure
            return {
                "name": "Test Player",
                "character_class": "warrior",
                "level": 1,
                "experience": 0,
                "health": 24,  # 20 + 4 * 1 (vitality)
                "max_health": 24,
                "gold": 100,
                "attributes": type('obj', (object,), {
                    'strength': 12,  # 10 + 2 (warrior bonus)
                    'agility': 10,
                    'intelligence': 10,
                    'vitality': 12,  # 10 + 2 (warrior bonus)
                    'luck': 10
                })(),
                "derived_stats": type('obj', (object,), {
                    'attack': 4,  # 2 + 2 (strength)
                    'magic': 2,   # 2 + 0 (intelligence)
                    'crit_chance': 5.0,  # 5 + 0.5 * 0 (agility)
                    'dodge': 2.0   # 2 + 0.4 * 0 (agility)
                })()
            }
        except Exception as e:
            print(f"Error getting player data: {e}")
            return None


# Factory function to create the handler
def create_combat_command_handler(i18n_service: I18nService, fsm_service: FSMStateService) -> CombatCommandHandler:
    """Create and return a combat command handler instance."""
    return CombatCommandHandler(i18n_service, fsm_service)

# Create a router instance for dependency injection
router = Router()
