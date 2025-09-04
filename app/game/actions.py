from enum import StrEnum
from dataclasses import dataclass

class Action(StrEnum):
    ATTACK = "attack"
    DEFEND = "defend"
    CAST = "cast"
    USE_ITEM = "use_item"
    TALK = "talk"
    SNEAK = "sneak"
    LOOT = "loot"
    FLEE = "flee"
    WAIT = "wait"
    BACK = "back"
    ACCEPT = "accept"
    INVESTIGATE = "investigate"
    PREPARE = "prepare"

@dataclass(frozen=True)
class ActionMeta:
    prompt_key: str   # localization hint for LLM
    fallback_key: str # fallback button label key
    max_len: int = 14

ACTION_META: dict[Action, ActionMeta] = {
    Action.ATTACK:   ActionMeta("action.attack", "btn.attack"),
    Action.DEFEND:   ActionMeta("action.defend", "btn.defend"),
    Action.CAST:     ActionMeta("action.cast", "btn.cast"),
    Action.USE_ITEM: ActionMeta("action.use_item", "btn.use_item"),
    Action.TALK:     ActionMeta("action.talk", "btn.talk"),
    Action.SNEAK:    ActionMeta("action.sneak", "btn.sneak"),
    Action.LOOT:     ActionMeta("action.loot", "btn.loot"),
    Action.FLEE:     ActionMeta("action.flee", "btn.flee"),
    Action.WAIT:     ActionMeta("action.wait", "btn.wait"),
    Action.BACK:     ActionMeta("action.back", "btn.back"),
    Action.ACCEPT:   ActionMeta("action.accept", "btn.accept"),
    Action.INVESTIGATE: ActionMeta("action.investigate", "btn.investigate"),
    Action.PREPARE:  ActionMeta("action.prepare", "btn.prepare"),
}
