"""Handles XP grants, level-ups, and reward distribution for players."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import CharacterClass, CharacterProgression
from app.models.player import Player
from app.services.logging_service import get_logger

logger = get_logger(__name__)


@dataclass
class LevelUpResult:
    leveled_up: bool
    old_level: int
    new_level: int
    xp_gained: int
    gold_gained: int
    stat_points_gained: int


class ProgressionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def award_quest_rewards(
        self,
        player: Player,
        xp: int,
        gold: int,
        partial: float = 1.0,
    ) -> LevelUpResult:
        """
        Award XP and gold from a completed quest.
        partial=0.25 for failure (consolation).
        Modifies player in-place and flushes to DB.
        """
        xp_awarded = max(1, int(xp * partial))
        gold_awarded = max(0, int(gold * partial))

        old_level = player.level
        player.experience += xp_awarded
        player.coins += gold_awarded

        new_level = CharacterProgression.get_level_from_xp(player.experience)
        stat_points_gained = 0

        if new_level > old_level:
            levels_gained = new_level - old_level
            player.level = new_level
            stat_points_gained = levels_gained * 2
            player.available_stat_points += stat_points_gained

            # Apply automatic class bonuses for each level
            if player.character_class:
                try:
                    cc = CharacterClass(str(player.character_class))
                    bonus_attrs = CharacterProgression.CLASS_DEFINITIONS[cc].level_up_bonus
                    for _ in range(levels_gained):
                        for attr in bonus_attrs:
                            setattr(player, attr, getattr(player, attr) + 1)
                except (ValueError, KeyError):
                    pass

            # Full heal on level up
            player.max_health = player.get_max_health()
            player.health = player.max_health

        await self.session.flush()

        logger.info(
            "Quest rewards awarded",
            player_id=player.id,
            xp=xp_awarded,
            gold=gold_awarded,
            old_level=old_level,
            new_level=player.level,
        )

        return LevelUpResult(
            leveled_up=new_level > old_level,
            old_level=old_level,
            new_level=player.level,
            xp_gained=xp_awarded,
            gold_gained=gold_awarded,
            stat_points_gained=stat_points_gained,
        )

    @staticmethod
    def calc_xp_bar(player: Player) -> str:
        """Returns a visual XP progress bar string."""
        current, required = CharacterProgression.get_xp_progress_to_next_level(
            player.level, player.experience
        )
        filled = int((current / required) * 10) if required else 10
        bar = "█" * filled + "░" * (10 - filled)
        return f"[{bar}] {current}/{required}"
