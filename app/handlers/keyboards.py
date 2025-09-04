from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from app.handlers.callbacks import ActionCB
from app.game.actions import Action
from app.services.ai import ActionLabelGenerator

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
