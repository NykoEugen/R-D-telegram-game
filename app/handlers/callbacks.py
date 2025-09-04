from aiogram.filters.callback_data import CallbackData

class ActionCB(CallbackData, prefix="act"):
    a: str  # action (e.g., "attack")
    s: str  # scene_id
