"""
Quest progress models for the Telegram RPG game bot.

Quest content (text, objectives, rewards) lives in YAML (app/game/quests/),
loaded via app/services/quest_loader.py. These models track only per-player
quest state.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class QuestStatus(str, Enum):
    """Quest status enumeration."""
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class QuestType(str, Enum):
    """Quest type enumeration."""
    MAIN = "main"
    SIDE = "side"
    DAILY = "daily"
    WEEKLY = "weekly"
    EVENT = "event"
    TUTORIAL = "tutorial"


class QuestProgress(Base):
    """Tracks a player's progress on a YAML-defined quest."""

    __tablename__ = "quest_progress"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to Player
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)

    # Quest identification (matches QuestDef.id in YAML content, not a DB FK)
    quest_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    # Quest progress
    status: Mapped[QuestStatus] = mapped_column(String(20), default=QuestStatus.ACTIVE, nullable=False)
    current_objective_idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    obj_progress: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Quest completion / repeat tracking (repeat_count also used for daily/weekly resets)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    repeat_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # When this quest becomes available again (used for DAILY/WEEKLY reset_cadence)
    available_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rewards_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="quest_progress")

    def __repr__(self) -> str:
        return (
            f"<QuestProgress(id={self.id}, player_id={self.player_id}, "
            f"quest_id={self.quest_id}, status={self.status})>"
        )
