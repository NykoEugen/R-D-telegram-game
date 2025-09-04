"""
Quest repository for the Telegram RPG game bot.

This module provides data access methods for Quest and QuestProgress entities.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lore import Quest, QuestProgress, QuestStatus, QuestType
from app.models.player import Player


class QuestRepository:
    """Repository class for Quest and QuestProgress entity operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Quest management methods
    async def create_quest(
        self,
        quest_id: str,
        name: str,
        quest_type: QuestType,
        **kwargs
    ) -> Quest:
        """
        Create a new quest.
        
        Args:
            quest_id: Unique quest identifier
            name: Quest name
            quest_type: Type of quest
            **kwargs: Additional quest attributes
            
        Returns:
            Quest: The created quest instance
            
        Raises:
            ValueError: If quest_id already exists
        """
        # Check if quest already exists
        existing_quest = await self.get_quest_by_quest_id(quest_id)
        if existing_quest:
            raise ValueError(f"Quest with ID {quest_id} already exists")
        
        # Create new quest
        quest_data = {
            "quest_id": quest_id,
            "name": name,
            "quest_type": quest_type,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        # Add any additional attributes
        quest_data.update(kwargs)
        
        quest = Quest(**quest_data)
        self.session.add(quest)
        await self.session.flush()
        await self.session.refresh(quest)
        
        return quest
    
    async def get_quest_by_id(self, quest_id: int) -> Optional[Quest]:
        """
        Get a quest by its database ID.
        
        Args:
            quest_id: The quest database ID
            
        Returns:
            Quest or None if not found
        """
        stmt = select(Quest).where(Quest.id == quest_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_quest_by_quest_id(self, quest_id: str) -> Optional[Quest]:
        """
        Get a quest by its unique quest identifier.
        
        Args:
            quest_id: The unique quest identifier
            
        Returns:
            Quest or None if not found
        """
        stmt = select(Quest).where(Quest.quest_id == quest_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_quests_by_type(self, quest_type: QuestType) -> List[Quest]:
        """
        Get all quests of a specific type.
        
        Args:
            quest_type: The quest type to filter by
            
        Returns:
            List of quests of the specified type
        """
        stmt = select(Quest).where(and_(Quest.quest_type == quest_type, Quest.is_active == True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_available_quests(self, player_level: int, player_flags: Optional[Dict[str, Any]] = None) -> List[Quest]:
        """
        Get quests available to a player based on level and flags.
        
        Args:
            player_level: Player's current level
            player_flags: Player's current flags
            
        Returns:
            List of available quests
        """
        stmt = select(Quest).where(
            and_(
                Quest.is_active == True,
                Quest.level_requirement <= player_level
            )
        )
        result = await self.session.execute(stmt)
        quests = list(result.scalars().all())
        
        # Filter by required flags if provided
        if player_flags:
            available_quests = []
            for quest in quests:
                if self._check_quest_requirements(quest, player_flags):
                    available_quests.append(quest)
            return available_quests
        
        return quests
    
    async def search_quests(self, query: str, limit: int = 50) -> List[Quest]:
        """
        Search for quests by name or description.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching quests
        """
        search_term = f"%{query}%"
        stmt = (
            select(Quest)
            .where(
                and_(
                    Quest.is_active == True,
                    or_(
                        Quest.name.ilike(search_term),
                        Quest.description.ilike(search_term)
                    )
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    # Quest progress management methods
    async def start_quest(self, player_id: int, quest_id: str) -> Optional[QuestProgress]:
        """
        Start a quest for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            QuestProgress or None if quest not found or already started
        """
        # Get the quest
        quest = await self.get_quest_by_quest_id(quest_id)
        if not quest:
            return None
        
        # Check if player already has progress on this quest
        existing_progress = await self.get_quest_progress(player_id, quest_id)
        if existing_progress and existing_progress.status in [QuestStatus.ACTIVE, QuestStatus.COMPLETED]:
            return None
        
        # Create or update quest progress
        if existing_progress:
            existing_progress.status = QuestStatus.ACTIVE
            existing_progress.started_at = datetime.utcnow()
            existing_progress.updated_at = datetime.utcnow()
            await self.session.flush()
            return existing_progress
        else:
            progress_data = {
                "player_id": player_id,
                "quest_id": quest.id,
                "status": QuestStatus.ACTIVE,
                "started_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            quest_progress = QuestProgress(**progress_data)
            self.session.add(quest_progress)
            await self.session.flush()
            await self.session.refresh(quest_progress)
            
            return quest_progress
    
    async def complete_quest(self, player_id: int, quest_id: str) -> Optional[QuestProgress]:
        """
        Complete a quest for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            QuestProgress or None if quest not found or not active
        """
        quest_progress = await self.get_quest_progress(player_id, quest_id)
        if not quest_progress or quest_progress.status != QuestStatus.ACTIVE:
            return None
        
        quest_progress.status = QuestStatus.COMPLETED
        quest_progress.completed_at = datetime.utcnow()
        quest_progress.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return quest_progress
    
    async def fail_quest(self, player_id: int, quest_id: str) -> Optional[QuestProgress]:
        """
        Mark a quest as failed for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            QuestProgress or None if quest not found or not active
        """
        quest_progress = await self.get_quest_progress(player_id, quest_id)
        if not quest_progress or quest_progress.status != QuestStatus.ACTIVE:
            return None
        
        quest_progress.status = QuestStatus.FAILED
        quest_progress.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return quest_progress
    
    async def abandon_quest(self, player_id: int, quest_id: str) -> Optional[QuestProgress]:
        """
        Abandon a quest for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            QuestProgress or None if quest not found or not active
        """
        quest_progress = await self.get_quest_progress(player_id, quest_id)
        if not quest_progress or quest_progress.status != QuestStatus.ACTIVE:
            return None
        
        quest_progress.status = QuestStatus.ABANDONED
        quest_progress.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return quest_progress
    
    async def update_quest_progress(
        self,
        player_id: int,
        quest_id: str,
        current_objective: Optional[int] = None,
        progress_data: Optional[Dict[str, Any]] = None
    ) -> Optional[QuestProgress]:
        """
        Update quest progress for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            current_objective: Current objective index
            progress_data: Additional progress data
            
        Returns:
            QuestProgress or None if quest not found or not active
        """
        quest_progress = await self.get_quest_progress(player_id, quest_id)
        if not quest_progress or quest_progress.status != QuestStatus.ACTIVE:
            return None
        
        if current_objective is not None:
            quest_progress.current_objective = current_objective
        
        if progress_data is not None:
            current_data = quest_progress.progress_data or {}
            current_data.update(progress_data)
            quest_progress.progress_data = current_data
        
        quest_progress.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return quest_progress
    
    async def get_quest_progress(self, player_id: int, quest_id: str) -> Optional[QuestProgress]:
        """
        Get quest progress for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            QuestProgress or None if not found
        """
        stmt = (
            select(QuestProgress)
            .join(Quest, QuestProgress.quest_id == Quest.id)
            .where(
                and_(
                    QuestProgress.player_id == player_id,
                    Quest.quest_id == quest_id
                )
            )
            .options(selectinload(QuestProgress.quest))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_player_quests(self, player_id: int, status: Optional[QuestStatus] = None) -> List[QuestProgress]:
        """
        Get all quest progress for a player.
        
        Args:
            player_id: The player ID
            status: Optional status filter
            
        Returns:
            List of quest progress with quest details
        """
        stmt = (
            select(QuestProgress)
            .where(QuestProgress.player_id == player_id)
            .options(selectinload(QuestProgress.quest))
        )
        
        if status:
            stmt = stmt.where(QuestProgress.status == status)
        
        stmt = stmt.order_by(QuestProgress.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_active_quests(self, player_id: int) -> List[QuestProgress]:
        """
        Get all active quests for a player.
        
        Args:
            player_id: The player ID
            
        Returns:
            List of active quest progress
        """
        return await self.get_player_quests(player_id, QuestStatus.ACTIVE)
    
    async def get_completed_quests(self, player_id: int) -> List[QuestProgress]:
        """
        Get all completed quests for a player.
        
        Args:
            player_id: The player ID
            
        Returns:
            List of completed quest progress
        """
        return await self.get_player_quests(player_id, QuestStatus.COMPLETED)
    
    async def get_quest_rewards(self, quest_id: str) -> Optional[Dict[str, Any]]:
        """
        Get rewards for a quest.
        
        Args:
            quest_id: The quest identifier
            
        Returns:
            Dictionary with quest rewards or None if quest not found
        """
        quest = await self.get_quest_by_quest_id(quest_id)
        if not quest:
            return None
        
        return {
            "experience_reward": quest.experience_reward,
            "coins_reward": quest.coins_reward,
            "items_reward": quest.items_reward,
        }
    
    async def claim_quest_rewards(self, player_id: int, quest_id: str) -> bool:
        """
        Mark quest rewards as claimed for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            True if rewards were claimed, False if already claimed or quest not completed
        """
        quest_progress = await self.get_quest_progress(player_id, quest_id)
        if not quest_progress or quest_progress.status != QuestStatus.COMPLETED:
            return False
        
        if quest_progress.rewards_claimed:
            return False
        
        quest_progress.rewards_claimed = True
        quest_progress.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return True
    
    async def can_repeat_quest(self, player_id: int, quest_id: str) -> bool:
        """
        Check if a player can repeat a quest.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            True if quest can be repeated, False otherwise
        """
        quest = await self.get_quest_by_quest_id(quest_id)
        if not quest or not quest.is_repeatable:
            return False
        
        quest_progress = await self.get_quest_progress(player_id, quest_id)
        if not quest_progress:
            return True
        
        # Check if max repeats reached
        if quest.max_repeats and quest_progress.repeat_count >= quest.max_repeats:
            return False
        
        return True
    
    async def repeat_quest(self, player_id: int, quest_id: str) -> Optional[QuestProgress]:
        """
        Repeat a quest for a player.
        
        Args:
            player_id: The player ID
            quest_id: The quest identifier
            
        Returns:
            QuestProgress or None if quest cannot be repeated
        """
        if not await self.can_repeat_quest(player_id, quest_id):
            return None
        
        quest_progress = await self.get_quest_progress(player_id, quest_id)
        if quest_progress:
            # Reset existing progress
            quest_progress.status = QuestStatus.ACTIVE
            quest_progress.current_objective = 0
            quest_progress.progress_data = None
            quest_progress.started_at = datetime.utcnow()
            quest_progress.completed_at = None
            quest_progress.rewards_claimed = False
            quest_progress.repeat_count += 1
            quest_progress.updated_at = datetime.utcnow()
            
            await self.session.flush()
            return quest_progress
        else:
            # Create new progress
            return await self.start_quest(player_id, quest_id)
    
    async def get_quest_statistics(self, player_id: int) -> Dict[str, Any]:
        """
        Get quest statistics for a player.
        
        Args:
            player_id: The player ID
            
        Returns:
            Dictionary with quest statistics
        """
        all_quests = await self.get_player_quests(player_id)
        
        stats = {
            "total_quests": len(all_quests),
            "active_quests": 0,
            "completed_quests": 0,
            "failed_quests": 0,
            "abandoned_quests": 0,
            "total_repeats": 0,
            "quests_by_type": {},
        }
        
        for quest_progress in all_quests:
            quest = quest_progress.quest
            quest_type = quest.quest_type.value
            
            # Count by status
            if quest_progress.status == QuestStatus.ACTIVE:
                stats["active_quests"] += 1
            elif quest_progress.status == QuestStatus.COMPLETED:
                stats["completed_quests"] += 1
            elif quest_progress.status == QuestStatus.FAILED:
                stats["failed_quests"] += 1
            elif quest_progress.status == QuestStatus.ABANDONED:
                stats["abandoned_quests"] += 1
            
            # Count repeats
            stats["total_repeats"] += quest_progress.repeat_count
            
            # Count by type
            if quest_type not in stats["quests_by_type"]:
                stats["quests_by_type"][quest_type] = {
                    "total": 0,
                    "completed": 0,
                    "active": 0,
                }
            
            stats["quests_by_type"][quest_type]["total"] += 1
            if quest_progress.status == QuestStatus.COMPLETED:
                stats["quests_by_type"][quest_type]["completed"] += 1
            elif quest_progress.status == QuestStatus.ACTIVE:
                stats["quests_by_type"][quest_type]["active"] += 1
        
        return stats
    
    def _check_quest_requirements(self, quest: Quest, player_flags: Dict[str, Any]) -> bool:
        """
        Check if a player meets the requirements for a quest.
        
        Args:
            quest: The quest to check
            player_flags: Player's current flags
            
        Returns:
            True if requirements are met, False otherwise
        """
        if not quest.required_flags:
            return True
        
        for required_flag in quest.required_flags:
            if required_flag not in player_flags:
                return False
        
        return True
