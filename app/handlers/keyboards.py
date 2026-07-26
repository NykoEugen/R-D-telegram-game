from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_hero_class_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for hero class selection."""
    builder = InlineKeyboardBuilder()

    classes = [
        ("⚔️ Warrior", "hero_class_warrior"),
        ("🗡️ Rogue", "hero_class_rogue"),
        ("🔮 Mage", "hero_class_mage"),
        ("⛑️ Cleric", "hero_class_cleric"),
        ("🏹 Ranger", "hero_class_ranger")
    ]

    for text, callback_data in classes:
        builder.button(text=text, callback_data=callback_data)

    builder.adjust(2, 2, 1)  # 2 buttons on first two rows, 1 on last row
    return builder.as_markup()


def build_hero_management_keyboard(has_hero: bool = True) -> InlineKeyboardMarkup:
    """Build keyboard for hero management menu."""
    builder = InlineKeyboardBuilder()

    if has_hero:
        # Hero management options
        builder.button(text="👤 View Hero", callback_data="view_hero")
        builder.button(text="📊 Stats", callback_data="hero_stats")
        builder.button(text="⬆️ Level Up", callback_data="hero_level_up")
        builder.button(text="🎯 Distribute Points", callback_data="hero_distribute")
        builder.button(text="🔄 Create New Hero", callback_data="create_new_hero")
        builder.adjust(2, 2, 1)  # 2 buttons on first two rows, 1 on last row
    else:
        # Hero creation options
        builder.button(text="🎭 Create New Hero", callback_data="create_hero")
        builder.button(text="ℹ️ About Heroes", callback_data="hero_info")
        builder.adjust(1)  # One button per row

    return builder.as_markup()


def build_hero_creation_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for hero creation flow."""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Create Hero", callback_data="confirm_hero_creation")
    builder.button(text="❌ Cancel", callback_data="cancel_hero_creation")

    builder.adjust(2)  # Two buttons on one row
    return builder.as_markup()


def build_hero_stat_distribution_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for hero stat point distribution."""
    builder = InlineKeyboardBuilder()

    # Stat buttons
    builder.button(text="💪 +STR", callback_data="hero_dist_str")
    builder.button(text="🏃 +AGI", callback_data="hero_dist_agi")
    builder.button(text="🧠 +INT", callback_data="hero_dist_int")
    builder.button(text="❤️ +VIT", callback_data="hero_dist_vit")
    builder.button(text="🍀 +LUK", callback_data="hero_dist_luk")

    # Action buttons
    builder.button(text="✅ Confirm", callback_data="hero_confirm_dist")
    builder.button(text="❌ Cancel", callback_data="hero_cancel_dist")

    builder.adjust(2, 2, 1, 2)  # 2, 2, 1, 2 buttons per row
    return builder.as_markup()


def build_hero_navigation_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for hero navigation (back to menu, etc.)."""
    builder = InlineKeyboardBuilder()

    builder.button(text="⬅️ Back to Menu", callback_data="back_to_hero_menu")

    builder.adjust(1)  # One button per row
    return builder.as_markup()
