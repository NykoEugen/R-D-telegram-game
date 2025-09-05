from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.handlers.callbacks import ActionCB
from app.game.actions import Action
from app.services.ai import ActionLabelGenerator
from app.models.world import Region
from typing import List

gen = ActionLabelGenerator()

def build_actions_kb(
    actions: list[Action],
    locale: str,
    scene_id: str,
    context_hint: str | None = None,
    row_width: int = 3,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    seen: set[str] = set()

    for a in actions:
        label = gen.generate_label(a, locale=locale, scene_id=scene_id, context_hint=context_hint)
        base = label
        n = 2
        while label in seen:
            label = f"{base[:10]} {n}"
            n += 1
        seen.add(label)
        cb = ActionCB(a=a.value, s=scene_id).pack()
        builder.button(text=label, callback_data=cb)

    builder.adjust(row_width)
    return builder.as_markup()


def build_region_keyboard(regions: List[Region]) -> InlineKeyboardMarkup:
    """Build keyboard for region selection."""
    builder = InlineKeyboardBuilder()
    
    for region in regions:
        tier_emoji = {
            "tier_1": "🟢",
            "tier_2": "🟡", 
            "tier_3": "🔴"
        }.get(region.difficulty.tier.value, "⚪")
        
        button_text = f"{tier_emoji} {region.name}"
        callback_data = f"explore_region_{region.region_id}"
        builder.button(text=button_text, callback_data=callback_data)
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def build_exploration_keyboard(event_type: str, enemy_type: str = None) -> InlineKeyboardMarkup:
    """Build keyboard for exploration events."""
    builder = InlineKeyboardBuilder()
    
    if event_type == "combat":
        builder.button(text="⚔️ Attack", callback_data=f"combat_attack_{enemy_type}")
        builder.button(text="🛡️ Defend", callback_data=f"combat_defend_{enemy_type}")
        builder.button(text="🏃 Run Away", callback_data=f"combat_run_{enemy_type}")
        builder.adjust(2, 1)  # Two buttons on first row, one on second
    elif event_type == "treasure":
        builder.button(text="💰 Take Treasure", callback_data="treasure_take")
        builder.button(text="🔍 Search More", callback_data="treasure_search")
        builder.adjust(1)
    elif event_type == "story":
        builder.button(text="📖 Continue", callback_data="story_continue")
        builder.button(text="❓ Ask Questions", callback_data="story_ask")
        builder.adjust(1)
    elif event_type == "trap":
        builder.button(text="🚨 Try to Escape", callback_data="trap_escape")
        builder.button(text="🛠️ Disarm Trap", callback_data="trap_disarm")
        builder.adjust(1)
    elif event_type == "merchant":
        builder.button(text="🛒 Browse Goods", callback_data="merchant_browse")
        builder.button(text="💰 Sell Items", callback_data="merchant_sell")
        builder.button(text="👋 Leave", callback_data="merchant_leave")
        builder.adjust(2, 1)
    else:
        # Default exploration options
        builder.button(text="🔍 Explore More", callback_data="explore_more")
        builder.button(text="🏠 Return to Regions", callback_data="back_to_regions")
        builder.adjust(1)
    
    return builder.as_markup()


def build_combat_keyboard(enemy_type: str, available_skills: List[str] = None) -> InlineKeyboardMarkup:
    """Build keyboard for combat actions."""
    builder = InlineKeyboardBuilder()
    
    # Basic combat actions
    builder.button(text="⚔️ Attack", callback_data=f"combat_attack_{enemy_type}")
    builder.button(text="🛡️ Defend", callback_data=f"combat_defend_{enemy_type}")
    
    # Add skill buttons if available
    if available_skills:
        for skill in available_skills:
            skill_name = skill.replace("_", " ").title()
            builder.button(text=f"✨ {skill_name}", callback_data=f"combat_skill_{skill}_{enemy_type}")
    
    # Escape option
    builder.button(text="🏃 Run Away", callback_data=f"combat_run_{enemy_type}")
    
    # Adjust layout based on number of skills
    if available_skills:
        builder.adjust(2, len(available_skills), 1)  # Attack/Defend, Skills, Run
    else:
        builder.adjust(2, 1)  # Attack/Defend, Run
    
    return builder.as_markup()
