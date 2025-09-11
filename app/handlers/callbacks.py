from aiogram.filters.callback_data import CallbackData

class ActionCB(CallbackData, prefix="act"):
    a: str  # action (e.g., "attack")
    s: str  # scene_id


class QuestActionCB(CallbackData, prefix="qa"):
    """Quest action callback data with prefix 'qa'."""
    action: str  # Supported actions: "accept", "decline", "ask", "continue", "attack", "defend", "flee", "loot", "next", "search_new"
    quest_id: str = ""  # Optional quest identifier
    scene_id: str = ""  # Optional scene identifier
