"""
AI-powered label generation service for action buttons.

This module handles generating contextual labels for game action buttons using AI.
"""

import hashlib
import random
from typing import Iterable
from openai import OpenAI

from app.core.config import Config
from app.services.logging_service import get_logger
from app.services.i18n_service import t
from app.game.actions import Action, ACTION_META

logger = get_logger(__name__)


class ActionLabelGenerator:
    """Generates contextual labels for action buttons using AI or fallback logic."""
    
    def __init__(self, enabled: bool = Config.OPENAI_ENABLED, model: str = Config.OPENAI_MODEL):
        self.enabled = enabled and bool(Config.OPENAI_API_KEY)
        self.model = model
        try:
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY) if self.enabled else None
        except Exception as e:
            logger.warning("Failed to initialize OpenAI client for ActionLabelGenerator", error=str(e))
            self.enabled = False
            self.client = None

    def _seed_from(self, *parts: Iterable[str]) -> int:
        """Generate a deterministic seed from input parts."""
        h = hashlib.sha256("::".join(parts).encode()).hexdigest()
        return int(h[:8], 16)

    def _generate_contextual_fallback(self, action: Action, locale: str, context_hint: str | None = None) -> str:
        """Generate contextual fallback labels based on action and context."""
        meta = ACTION_META[action]
        base_fallback = t(meta.fallback_key, locale=locale)
        
        # Contextual variations for different actions
        contextual_variations = {
            Action.ACCEPT: {
                "en": ["Accept", "Agree", "Take On", "Embrace", "Commit"],
                "uk": ["Прийняти", "Погодитися", "Взятися", "Прийняти", "Зобов'язатися"]
            },
            Action.INVESTIGATE: {
                "en": ["Investigate", "Examine", "Research", "Explore", "Study"],
                "uk": ["Розслідувати", "Дослідити", "Вивчити", "Дослідити", "Вивчити"]
            },
            Action.PREPARE: {
                "en": ["Prepare", "Ready", "Gear Up", "Arm", "Equip"],
                "uk": ["Підготуватися", "Готовий", "Озброїтися", "Озброїти", "Споряджатися"]
            },
            Action.TALK: {
                "en": ["Talk", "Speak", "Negotiate", "Persuade", "Question"],
                "uk": ["Говорити", "Розмовляти", "Переговори", "Переконати", "Розпитати"]
            },
            Action.BACK: {
                "en": ["Back", "Return", "Leave", "Exit", "Retreat"],
                "uk": ["Назад", "Повернутися", "Покинути", "Вийти", "Відступити"]
            },
            Action.RUN_AI: {
                "en": ["AI Action", "Smart Move", "AI Generate", "AI Response", "AI Help"],
                "uk": ["ШІ Дія", "Розумний Крок", "ШІ Генерація", "ШІ Відповідь", "ШІ Допомога"]
            }
        }
        
        # Get variations for this action and locale
        variations = contextual_variations.get(action, {}).get(locale, [base_fallback])
        
        # Use context hint to select appropriate variation
        if context_hint:
            context_lower = context_hint.lower()
            if any(word in context_lower for word in ["quest", "mission", "task", "challenge", "artifact", "mysterious", "ruins", "villagers", "discovered"]):
                # Quest-related context
                if action == Action.ACCEPT:
                    return variations[1] if len(variations) > 1 else variations[0]
                elif action == Action.INVESTIGATE:
                    return variations[1] if len(variations) > 1 else variations[0]
                elif action == Action.PREPARE:
                    return variations[1] if len(variations) > 1 else variations[0]
            elif any(word in context_lower for word in ["battle", "fight", "combat", "enemy", "dragon", "attack", "weapon"]):
                # Combat context
                if action == Action.ATTACK:
                    return variations[1] if len(variations) > 1 else variations[0]
                elif action == Action.DEFEND:
                    return variations[1] if len(variations) > 1 else variations[0]
            elif any(word in context_lower for word in ["magic", "spell", "cast", "enchant", "magical", "wizard"]):
                # Magic context
                if action == Action.CAST:
                    return variations[1] if len(variations) > 1 else variations[0]
            elif any(word in context_lower for word in ["ai", "smart", "intelligent", "generate", "dynamic", "automatic"]):
                # AI context
                if action == Action.RUN_AI:
                    return variations[1] if len(variations) > 1 else variations[0]
        
        # Default to first variation or base fallback
        return variations[0] if variations else base_fallback

    def generate_label(self, action: Action, locale: str, scene_id: str, context_hint: str | None = None) -> str:
        """Generate a contextual label for an action button."""
        meta = ACTION_META[action]
        fallback = t(meta.fallback_key, locale=locale)
        
        # Always use contextual fallback for now (can be enhanced with OpenAI later)
        contextual_label = self._generate_contextual_fallback(action, locale, context_hint)
        
        if not self.enabled:
            return contextual_label

        rnd = random.Random(self._seed_from(action, locale, scene_id, context_hint or ""))

        sys = (
            f"You generate ultra-short Telegram inline button labels.\n"
            f"Rules: 1) <= {meta.max_len} chars, 2) no emojis, 3) no quotes, "
            f"4) imperative or concise noun, 5) strictly use the requested language."
        )
        desc = t(meta.prompt_key, locale=locale)
        user = (
            f"Language: {locale}\n"
            f"Base action: {action}\n"
            f"Action intent: {desc}\n"
            f"Scene hint: {context_hint or 'n/a'}\n"
            f"Return ONE label only, <= {meta.max_len} chars."
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": sys},
                          {"role": "user", "content": user}],
                temperature=0.7,
                top_p=0.9,
                n=1,
            )
            text = (resp.choices[0].message.content or "").strip().replace("\n", " ")
            if len(text) > meta.max_len:
                text = text[:meta.max_len].strip()
            if rnd.random() < 0.3 and text.lower() == fallback.lower():
                text = text[: max(3, meta.max_len - 1)]
            return text or contextual_label
        except Exception:
            return contextual_label
