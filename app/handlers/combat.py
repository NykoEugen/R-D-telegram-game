"""
Combat handlers for the Telegram RPG game bot.

This module handles combat-related interactions including combat flow,
action processing, and combat state management.
"""

from typing import Dict, List, Optional, Tuple, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.models.combat import (
    CombatState, Enemy, CombatAction, ClassSkill, StatusEffect,
    CombatCalculator, CombatActions, EnemyGenerator, StatusEffectInstance
)
from app.models.character import CharacterClass
from app.services.i18n_service import I18nService
from app.services.fsm_service import FSMService
from app.core.utils import get_user_language


class CombatStates(StatesGroup):
    """Combat-specific FSM states."""
    COMBAT_ACTIVE = State()
    COMBAT_ACTION = State()
    COMBAT_SKILL_SELECT = State()
    COMBAT_ITEM_SELECT = State()


class CombatHandler:
    """Handles combat interactions and flow."""
    
    def __init__(self, i18n_service: I18nService, fsm_service: FSMService):
        self.i18n_service = i18n_service
        self.fsm_service = fsm_service
        self.router = Router()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup combat-related handlers."""
        self.router.callback_query.register(
            self.handle_combat_action,
            F.data.startswith("combat_")
        )
        self.router.callback_query.register(
            self.handle_skill_select,
            F.data.startswith("skill_")
        )
        self.router.callback_query.register(
            self.handle_item_select,
            F.data.startswith("item_")
        )
    
    async def start_combat(
        self, 
        message: Message, 
        context: FSMContext, 
        player_data: Dict,
        enemy_type: str = "goblin"
    ) -> None:
        """Start a combat encounter."""
        language = await get_user_language(message.from_user.id)
        
        # Generate enemy
        enemy = EnemyGenerator.generate_enemy(player_data["level"], enemy_type)
        
        # Calculate initiative
        turn_order = CombatCalculator.calculate_initiative(
            player_data["attributes"].agility,
            enemy.agility
        )
        
        # Create combat state
        combat_state = CombatState(
            player_hp=player_data["health"],
            player_max_hp=player_data["max_health"],
            enemy=enemy,
            turn_order=turn_order
        )
        
        # Store combat state
        await context.update_data(combat_state=combat_state)
        await context.set_state(CombatStates.COMBAT_ACTIVE)
        
        # Send combat start message
        combat_text = await self._format_combat_status(combat_state, language)
        keyboard = await self._get_combat_keyboard(player_data, language)
        
        await message.answer(combat_text, reply_markup=keyboard)
    
    async def handle_combat_action(self, callback: CallbackQuery, context: FSMContext) -> None:
        """Handle combat action selection."""
        await callback.answer()
        
        data = await context.get_data()
        combat_state: CombatState = data.get("combat_state")
        player_data = data.get("player_data")
        
        if not combat_state or not player_data:
            await callback.message.edit_text("Combat state not found!")
            return
        
        language = await get_user_language(callback.from_user.id)
        action = callback.data.split("_")[1]
        
        if action == "attack":
            await self._execute_player_attack(callback, context, combat_state, player_data, language)
        elif action == "skill":
            await self._show_skill_selection(callback, context, combat_state, player_data, language)
        elif action == "item":
            await self._show_item_selection(callback, context, combat_state, player_data, language)
        elif action == "run":
            await self._execute_escape_attempt(callback, context, combat_state, player_data, language)
    
    async def handle_skill_select(self, callback: CallbackQuery, context: FSMContext) -> None:
        """Handle skill selection."""
        await callback.answer()
        
        data = await context.get_data()
        combat_state: CombatState = data.get("combat_state")
        player_data = data.get("player_data")
        
        if not combat_state or not player_data:
            await callback.message.edit_text("Combat state not found!")
            return
        
        language = await get_user_language(callback.from_user.id)
        skill_name = callback.data.split("_")[1]
        
        try:
            skill = ClassSkill(skill_name)
            await self._execute_player_skill(callback, context, combat_state, player_data, skill, language)
        except ValueError:
            await callback.message.edit_text("Invalid skill selected!")
    
    async def handle_item_select(self, callback: CallbackQuery, context: FSMContext) -> None:
        """Handle item selection."""
        await callback.answer()
        
        # TODO: Implement item usage
        await callback.message.edit_text("Item usage not implemented yet!")
    
    async def _execute_player_attack(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Execute player attack."""
        # Execute attack
        damage, is_crit, result = CombatActions.execute_attack(
            combat_state, 
            {
                "attack": player_data["derived_stats"].attack,
                "agility": player_data["attributes"].agility,
                "crit_chance": player_data["derived_stats"].crit_chance
            }, 
            True
        )
        
        # Add to combat log
        if result == "miss":
            combat_state.combat_log.append("You miss your attack!")
        elif is_crit:
            combat_state.combat_log.append(f"Critical hit! You deal {damage} damage!")
        else:
            combat_state.combat_log.append(f"You deal {damage} damage!")
        
        # Check if enemy is defeated
        if combat_state.enemy.hp_current <= 0:
            await self._handle_combat_victory(callback, context, combat_state, player_data, language)
            return
        
        # Enemy turn
        await self._execute_enemy_turn(callback, context, combat_state, player_data, language)
    
    async def _execute_player_skill(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        skill: ClassSkill, 
        language: str
    ) -> None:
        """Execute player skill."""
        # Check cooldown
        if skill in combat_state.player_skill_cooldowns and combat_state.player_skill_cooldowns[skill] > 0:
            await callback.message.edit_text(f"Skill is on cooldown for {combat_state.player_skill_cooldowns[skill]} turns!")
            return
        
        # Execute skill
        damage, is_crit, result, new_effects = CombatActions.execute_skill(
            combat_state,
            {
                "attack": player_data["derived_stats"].attack,
                "magic": player_data["derived_stats"].magic,
                "agility": player_data["attributes"].agility,
                "intelligence": player_data["attributes"].intelligence,
                "crit_chance": player_data["derived_stats"].crit_chance
            },
            skill
        )
        
        # Add skill to cooldown
        combat_state.player_skill_cooldowns[skill] = 2  # Most skills have 2-turn cooldown
        
        # Add effects to enemy
        combat_state.enemy_status_effects.extend(new_effects)
        
        # Add to combat log
        skill_name = skill.value.replace("_", " ").title()
        if result == "miss":
            combat_state.combat_log.append(f"{skill_name} misses!")
        elif is_crit:
            combat_state.combat_log.append(f"Critical {skill_name}! You deal {damage} damage!")
        else:
            combat_state.combat_log.append(f"{skill_name} deals {damage} damage!")
        
        # Add effect messages
        for effect in new_effects:
            effect_name = effect.effect_type.value.title()
            combat_state.combat_log.append(f"Enemy is affected by {effect_name}!")
        
        # Check if enemy is defeated
        if combat_state.enemy.hp_current <= 0:
            await self._handle_combat_victory(callback, context, combat_state, player_data, language)
            return
        
        # Enemy turn
        await self._execute_enemy_turn(callback, context, combat_state, player_data, language)
    
    async def _execute_enemy_turn(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Execute enemy turn."""
        # Check if enemy is stunned
        enemy_stunned = any(effect.effect_type == StatusEffect.STUN for effect in combat_state.enemy_status_effects)
        
        if enemy_stunned:
            combat_state.combat_log.append("Enemy is stunned and skips their turn!")
        else:
            # Execute enemy attack
            damage, is_crit, result = CombatActions.execute_attack(
                combat_state,
                {
                    "attack": combat_state.enemy.attack,
                    "agility": combat_state.enemy.agility,
                    "crit_chance": 5.0
                },
                False
            )
            
            # Add to combat log
            if result == "miss":
                combat_state.combat_log.append("Enemy misses their attack!")
            elif is_crit:
                combat_state.combat_log.append(f"Enemy critical hit! You take {damage} damage!")
            else:
                combat_state.combat_log.append(f"Enemy deals {damage} damage!")
        
        # Process status effects
        status_logs = CombatActions.process_status_effects(combat_state, {
            "attack": player_data["derived_stats"].attack,
            "agility": player_data["attributes"].agility,
            "intelligence": player_data["attributes"].intelligence
        })
        combat_state.combat_log.extend(status_logs)
        
        # Update cooldowns
        CombatActions.update_skill_cooldowns(combat_state)
        
        # Reset temporary bonuses
        combat_state.player_crit_bonus = 0.0
        
        # Check if player is defeated
        if combat_state.player_hp <= 0:
            await self._handle_combat_defeat(callback, context, combat_state, player_data, language)
            return
        
        # Continue combat
        await self._update_combat_display(callback, context, combat_state, player_data, language)
    
    async def _execute_escape_attempt(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Execute escape attempt."""
        success = CombatActions.execute_escape(combat_state, {
            "agility": player_data["attributes"].agility
        })
        
        if success:
            combat_state.combat_log.append("You successfully escape from combat!")
            await self._handle_combat_escape(callback, context, combat_state, player_data, language)
        else:
            combat_state.combat_log.append("Escape attempt failed!")
            # Enemy turn after failed escape
            await self._execute_enemy_turn(callback, context, combat_state, player_data, language)
    
    async def _handle_combat_victory(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Handle combat victory."""
        # Calculate rewards
        xp_gained = combat_state.enemy.xp_reward
        gold_gained = combat_state.enemy.gold_reward
        
        # Add XP and gold to player
        player_data["experience"] += xp_gained
        player_data["gold"] = player_data.get("gold", 0) + gold_gained
        
        # Check for level up
        from app.models.character import CharacterManager
        old_level = player_data["level"]
        player_data = CharacterManager.add_experience(player_data, 0)  # Just recalculate level
        
        level_up_text = ""
        if player_data["level"] > old_level:
            level_up_text = f"\n🎉 Level up! You are now level {player_data['level']}!"
        
        # Victory message
        victory_text = f"""
🎉 **Victory!**

You defeated the {combat_state.enemy.name}!

**Rewards:**
• XP: +{xp_gained}
• Gold: +{gold_gained}
{level_up_text}

**Combat Log:**
{chr(10).join(combat_state.combat_log[-5:])}
"""
        
        # Update player data
        await context.update_data(player_data=player_data)
        await context.set_state(None)  # Exit combat state
        
        await callback.message.edit_text(victory_text)
    
    async def _handle_combat_defeat(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Handle combat defeat."""
        # Calculate penalty
        gold_penalty = int(player_data.get("gold", 0) * 0.1)
        player_data["gold"] = max(0, player_data.get("gold", 0) - gold_penalty)
        player_data["health"] = 1  # Set HP to 1
        
        # Defeat message
        defeat_text = f"""
💀 **Defeat!**

You were defeated by the {combat_state.enemy.name}!

**Penalties:**
• Gold lost: -{gold_penalty}
• HP: Set to 1

You return to town to recover...

**Combat Log:**
{chr(10).join(combat_state.combat_log[-5:])}
"""
        
        # Update player data
        await context.update_data(player_data=player_data)
        await context.set_state(None)  # Exit combat state
        
        await callback.message.edit_text(defeat_text)
    
    async def _handle_combat_escape(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Handle successful escape."""
        escape_text = f"""
🏃 **Escape!**

You successfully escaped from the {combat_state.enemy.name}!

**Combat Log:**
{chr(10).join(combat_state.combat_log[-3:])}
"""
        
        await context.set_state(None)  # Exit combat state
        await callback.message.edit_text(escape_text)
    
    async def _update_combat_display(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Update combat display with current state."""
        combat_text = await self._format_combat_status(combat_state, language)
        keyboard = await self._get_combat_keyboard(player_data, language)
        
        await context.update_data(combat_state=combat_state)
        await callback.message.edit_text(combat_text, reply_markup=keyboard)
    
    async def _format_combat_status(self, combat_state: CombatState, language: str) -> str:
        """Format combat status display."""
        player_hp_percent = (combat_state.player_hp / combat_state.player_max_hp) * 100
        enemy_hp_percent = (combat_state.enemy.hp_current / combat_state.enemy.hp_max) * 100
        
        # Create HP bars
        player_hp_bar = "█" * int(player_hp_percent / 10) + "░" * (10 - int(player_hp_percent / 10))
        enemy_hp_bar = "█" * int(enemy_hp_percent / 10) + "░" * (10 - int(enemy_hp_percent / 10))
        
        # Status effects
        player_effects = [effect.effect_type.value for effect in combat_state.player_status_effects]
        enemy_effects = [effect.effect_type.value for effect in combat_state.enemy_status_effects]
        
        effects_text = ""
        if player_effects:
            effects_text += f"**Your effects:** {', '.join(player_effects)}\n"
        if enemy_effects:
            effects_text += f"**Enemy effects:** {', '.join(enemy_effects)}\n"
        
        combat_text = f"""
⚔️ **Combat**

**{combat_state.enemy.name}** (Level {combat_state.enemy.level})
HP: {enemy_hp_bar} {combat_state.enemy.hp_current}/{combat_state.enemy.hp_max}

**You**
HP: {player_hp_bar} {combat_state.player_hp}/{combat_state.player_max_hp}

{effects_text}
**Recent Actions:**
{chr(10).join(combat_state.combat_log[-3:]) if combat_state.combat_log else "Combat begins!"}
"""
        
        return combat_text
    
    async def _get_combat_keyboard(self, player_data: Dict, language: str) -> InlineKeyboardMarkup:
        """Get combat action keyboard."""
        buttons = [
            [InlineKeyboardButton(text="⚔️ Attack", callback_data="combat_attack")],
        ]
        
        # Add skill button if available
        available_skills = CombatActions.get_available_skills(
            player_data["character_class"], 
            {}  # TODO: Get actual cooldowns from combat state
        )
        
        if available_skills:
            skill_name = available_skills[0].value.replace("_", " ").title()
            buttons.append([InlineKeyboardButton(text=f"🎯 {skill_name}", callback_data="combat_skill")])
        
        buttons.extend([
            [InlineKeyboardButton(text="🧪 Item", callback_data="combat_item")],
            [InlineKeyboardButton(text="🏃 Run", callback_data="combat_run")]
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    async def _show_skill_selection(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Show skill selection keyboard."""
        data = await context.get_data()
        combat_state = data.get("combat_state")
        
        available_skills = CombatActions.get_available_skills(
            player_data["character_class"], 
            combat_state.player_skill_cooldowns
        )
        
        if not available_skills:
            await callback.message.edit_text("No skills available!")
            return
        
        buttons = []
        for skill in available_skills:
            skill_name = skill.value.replace("_", " ").title()
            buttons.append([InlineKeyboardButton(text=skill_name, callback_data=f"skill_{skill.value}")])
        
        buttons.append([InlineKeyboardButton(text="Back", callback_data="combat_back")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text("Select a skill:", reply_markup=keyboard)
    
    async def _show_item_selection(
        self, 
        callback: CallbackQuery, 
        context: FSMContext, 
        combat_state: CombatState, 
        player_data: Dict, 
        language: str
    ) -> None:
        """Show item selection keyboard."""
        # TODO: Implement item selection
        await callback.message.edit_text("No items available!")
