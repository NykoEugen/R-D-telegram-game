"""
Quest progress repository for the Telegram RPG game bot.

Quest content (text, objectives, rewards, requires-graph) lives in YAML and is
read via app/services/quest_loader.py. This repository only persists
per-player QuestProgress state (status, objective index, repeat/reset info).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lore import QuestProgress, QuestStatus


class QuestRepository:
    """Repository class for QuestProgress entity operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_quest_progress(
        self, player_id: int, quest_id: str
    ) -> QuestProgress | None:
        """Get quest progress for a player (regardless of status)."""
        stmt = select(QuestProgress).where(
            and_(
                QuestProgress.player_id == player_id,
                QuestProgress.quest_id == quest_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def start_quest(self, player_id: int, quest_id: str) -> QuestProgress:
        """Start (or restart) a quest for a player."""
        progress = await self.get_quest_progress(player_id, quest_id)
        if progress:
            progress.status = QuestStatus.ACTIVE
            progress.current_objective_idx = 0
            progress.obj_progress = None
            progress.started_at = datetime.utcnow()
            progress.completed_at = None
            progress.rewards_claimed = False
            await self.session.flush()
            return progress

        progress = QuestProgress(
            player_id=player_id,
            quest_id=quest_id,
            status=QuestStatus.ACTIVE,
            current_objective_idx=0,
            started_at=datetime.utcnow(),
        )
        self.session.add(progress)
        await self.session.flush()
        await self.session.refresh(progress)
        return progress

    async def update_progress(
        self,
        player_id: int,
        quest_id: str,
        current_objective_idx: int | None = None,
        obj_progress: dict[str, Any] | None = None,
    ) -> QuestProgress | None:
        """Persist in-progress objective state for an active quest."""
        progress = await self.get_quest_progress(player_id, quest_id)
        if not progress or progress.status != QuestStatus.ACTIVE:
            return None

        if current_objective_idx is not None:
            progress.current_objective_idx = current_objective_idx
        if obj_progress is not None:
            progress.obj_progress = obj_progress

        await self.session.flush()
        return progress

    async def complete_quest(
        self, player_id: int, quest_id: str, available_at: datetime | None = None
    ) -> QuestProgress | None:
        """Mark a quest completed; optionally schedule next availability (dailies)."""
        progress = await self.get_quest_progress(player_id, quest_id)
        if not progress or progress.status != QuestStatus.ACTIVE:
            return None

        progress.status = QuestStatus.COMPLETED
        progress.completed_at = datetime.utcnow()
        progress.repeat_count += 1
        progress.available_at = available_at
        await self.session.flush()
        return progress

    async def fail_quest(self, player_id: int, quest_id: str) -> QuestProgress | None:
        """Mark a quest as failed for a player."""
        progress = await self.get_quest_progress(player_id, quest_id)
        if not progress or progress.status != QuestStatus.ACTIVE:
            return None

        progress.status = QuestStatus.FAILED
        await self.session.flush()
        return progress

    async def abandon_quest(
        self, player_id: int, quest_id: str
    ) -> QuestProgress | None:
        """Abandon an active quest for a player."""
        progress = await self.get_quest_progress(player_id, quest_id)
        if not progress or progress.status != QuestStatus.ACTIVE:
            return None

        progress.status = QuestStatus.ABANDONED
        await self.session.flush()
        return progress

    async def get_player_quests(
        self, player_id: int, status: QuestStatus | None = None
    ) -> list[QuestProgress]:
        """Get all quest progress rows for a player, optionally filtered by status."""
        stmt = select(QuestProgress).where(QuestProgress.player_id == player_id)
        if status:
            stmt = stmt.where(QuestProgress.status == status)
        stmt = stmt.order_by(QuestProgress.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_quests(self, player_id: int) -> list[QuestProgress]:
        return await self.get_player_quests(player_id, QuestStatus.ACTIVE)

    async def get_completed_quests(self, player_id: int) -> list[QuestProgress]:
        return await self.get_player_quests(player_id, QuestStatus.COMPLETED)

    async def is_available_again(self, player_id: int, quest_id: str) -> bool:
        """Check whether a repeatable (daily/weekly) quest's cooldown has elapsed."""
        progress = await self.get_quest_progress(player_id, quest_id)
        if not progress:
            return True
        if progress.status == QuestStatus.ACTIVE:
            return False
        if progress.available_at is None:
            return progress.status != QuestStatus.COMPLETED
        return datetime.utcnow() >= progress.available_at

    async def claim_rewards(self, player_id: int, quest_id: str) -> bool:
        """Mark quest rewards as claimed. False if already claimed or not completed."""
        progress = await self.get_quest_progress(player_id, quest_id)
        if not progress or progress.status != QuestStatus.COMPLETED:
            return False
        if progress.rewards_claimed:
            return False

        progress.rewards_claimed = True
        await self.session.flush()
        return True
