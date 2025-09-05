"""
Player progress and world exploration tracking for the Telegram RPG game bot.

This module defines models for tracking player progress, unlocked regions,
completed quests, and exploration history.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, List, Optional, Any
import json

Base = declarative_base()


class PlayerProgress(Base):
    """Tracks player's overall progress and unlocked content."""
    __tablename__ = "player_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    current_level = Column(Integer, default=1, nullable=False)
    total_experience = Column(Integer, default=0, nullable=False)
    completed_quests = Column(JSON, default=list)  # List of completed quest IDs
    unlocked_regions = Column(JSON, default=list)  # List of unlocked region IDs
    visited_locations = Column(JSON, default=dict)  # Dict of location_id: visit_count
    achievements = Column(JSON, default=list)  # List of achievement IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="progress")
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.current_level = 1
        self.total_experience = 0
        self.completed_quests = []
        self.unlocked_regions = ["forest_path"]  # Forest Path is always unlocked
        self.visited_locations = {}
        self.achievements = []
    
    def add_experience(self, xp: int) -> bool:
        """Add experience and return True if level up occurred."""
        self.total_experience += xp
        old_level = self.current_level
        
        # Calculate new level based on total XP
        new_level = self._calculate_level_from_xp(self.total_experience)
        if new_level > old_level:
            self.current_level = new_level
            return True
        return False
    
    def _calculate_level_from_xp(self, total_xp: int) -> int:
        """Calculate level from total XP using the same formula as character progression."""
        level = 1
        xp_required = 0
        
        while True:
            xp_for_next = 50 + 25 * level
            if xp_required + xp_for_next > total_xp:
                break
            xp_required += xp_for_next
            level += 1
        
        return level
    
    def complete_quest(self, quest_id: str):
        """Mark a quest as completed."""
        if quest_id not in self.completed_quests:
            self.completed_quests.append(quest_id)
    
    def unlock_region(self, region_id: str):
        """Unlock a new region."""
        if region_id not in self.unlocked_regions:
            self.unlocked_regions.append(region_id)
    
    def visit_location(self, location_id: str):
        """Record a visit to a location."""
        if location_id not in self.visited_locations:
            self.visited_locations[location_id] = 0
        self.visited_locations[location_id] += 1
    
    def add_achievement(self, achievement_id: str):
        """Add an achievement."""
        if achievement_id not in self.achievements:
            self.achievements.append(achievement_id)
    
    def get_available_regions(self) -> List[str]:
        """Get list of regions available to this player."""
        return self.unlocked_regions.copy()
    
    def can_access_region(self, region_id: str) -> bool:
        """Check if player can access a specific region."""
        return region_id in self.unlocked_regions
    
    def get_visit_count(self, location_id: str) -> int:
        """Get number of times player has visited a location."""
        return self.visited_locations.get(location_id, 0)
    
    def has_completed_quest(self, quest_id: str) -> bool:
        """Check if player has completed a specific quest."""
        return quest_id in self.completed_quests
    
    def has_achievement(self, achievement_id: str) -> bool:
        """Check if player has a specific achievement."""
        return achievement_id in self.achievements


class ExplorationSession(Base):
    """Tracks individual exploration sessions in regions."""
    __tablename__ = "exploration_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    region_id = Column(String, nullable=False)
    session_start = Column(DateTime(timezone=True), server_default=func.now())
    session_end = Column(DateTime(timezone=True), nullable=True)
    events_encountered = Column(JSON, default=list)  # List of event IDs encountered
    enemies_defeated = Column(JSON, default=list)  # List of enemy types defeated
    loot_obtained = Column(JSON, default=list)  # List of items obtained
    experience_gained = Column(Integer, default=0)
    gold_gained = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("User")
    
    def end_session(self):
        """End the exploration session."""
        self.session_end = func.now()
        self.is_active = False
    
    def add_event(self, event_id: str):
        """Record an event encountered."""
        if event_id not in self.events_encountered:
            self.events_encountered.append(event_id)
    
    def add_enemy_defeated(self, enemy_type: str):
        """Record an enemy defeated."""
        if enemy_type not in self.enemies_defeated:
            self.enemies_defeated.append(enemy_type)
    
    def add_loot(self, item_id: str):
        """Record loot obtained."""
        if item_id not in self.loot_obtained:
            self.loot_obtained.append(item_id)
    
    def add_rewards(self, xp: int, gold: int):
        """Add experience and gold rewards."""
        self.experience_gained += xp
        self.gold_gained += gold


class RegionUnlock(Base):
    """Tracks region unlock requirements and progress."""
    __tablename__ = "region_unlocks"
    
    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(String, unique=True, nullable=False)
    unlock_type = Column(String, nullable=False)  # "level", "quest", "achievement"
    unlock_value = Column(String, nullable=False)  # The specific requirement value
    description = Column(Text, nullable=True)
    is_unlocked_by_default = Column(Boolean, default=False)
    
    def __init__(self, region_id: str, unlock_type: str, unlock_value: str, 
                 description: str = None, is_unlocked_by_default: bool = False):
        self.region_id = region_id
        self.unlock_type = unlock_type
        self.unlock_value = unlock_value
        self.description = description
        self.is_unlocked_by_default = is_unlocked_by_default


class PlayerStats(Base):
    """Tracks player statistics and achievements."""
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    total_enemies_defeated = Column(Integer, default=0)
    total_quests_completed = Column(Integer, default=0)
    total_regions_explored = Column(Integer, default=0)
    total_exploration_time = Column(Integer, default=0)  # In minutes
    favorite_region = Column(String, nullable=True)
    longest_exploration_session = Column(Integer, default=0)  # In minutes
    total_gold_earned = Column(Integer, default=0)
    total_experience_gained = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User")
    
    def update_enemies_defeated(self, count: int = 1):
        """Update total enemies defeated."""
        self.total_enemies_defeated += count
    
    def update_quests_completed(self, count: int = 1):
        """Update total quests completed."""
        self.total_quests_completed += count
    
    def update_regions_explored(self, count: int = 1):
        """Update total regions explored."""
        self.total_regions_explored += count
    
    def update_exploration_time(self, minutes: int):
        """Update total exploration time."""
        self.total_exploration_time += minutes
        if minutes > self.longest_exploration_session:
            self.longest_exploration_session = minutes
    
    def update_gold_earned(self, amount: int):
        """Update total gold earned."""
        self.total_gold_earned += amount
    
    def update_experience_gained(self, amount: int):
        """Update total experience gained."""
        self.total_experience_gained += amount
    
    def set_favorite_region(self, region_id: str):
        """Set favorite region based on exploration frequency."""
        self.favorite_region = region_id


class ProgressManager:
    """Manages player progress and region unlocking logic."""
    
    @staticmethod
    def check_region_unlock_requirements(progress: PlayerProgress, region_id: str) -> bool:
        """Check if player meets requirements to unlock a region."""
        from .world import WorldManager
        
        region = WorldManager.get_region_by_id(region_id)
        if not region:
            return False
        
        req = region.difficulty.unlock_requirement
        
        # Check level requirement
        if "level" in req and progress.current_level < req["level"]:
            return False
        
        # Check quest requirement
        if "quest" in req and not progress.has_completed_quest(req["quest"]):
            return False
        
        return True
    
    @staticmethod
    def unlock_available_regions(progress: PlayerProgress) -> List[str]:
        """Check and unlock any regions that player can now access."""
        from .world import WorldManager
        
        newly_unlocked = []
        for region_id, region in WorldManager.REGIONS.items():
            if region_id not in progress.unlocked_regions:
                if ProgressManager.check_region_unlock_requirements(progress, region_id):
                    progress.unlock_region(region_id)
                    newly_unlocked.append(region_id)
        
        return newly_unlocked
    
    @staticmethod
    def get_player_summary(progress: PlayerProgress, stats: PlayerStats = None) -> Dict[str, Any]:
        """Get a comprehensive summary of player progress."""
        from .world import WorldManager
        
        available_regions = []
        for region_id in progress.unlocked_regions:
            region = WorldManager.get_region_by_id(region_id)
            if region:
                available_regions.append({
                    "id": region_id,
                    "name": region.name,
                    "tier": region.difficulty.tier.value,
                    "level_range": region.difficulty.level_range,
                    "visit_count": progress.get_visit_count(region_id)
                })
        
        summary = {
            "level": progress.current_level,
            "experience": progress.total_experience,
            "completed_quests": len(progress.completed_quests),
            "unlocked_regions": len(progress.unlocked_regions),
            "achievements": len(progress.achievements),
            "available_regions": available_regions
        }
        
        if stats:
            summary.update({
                "total_enemies_defeated": stats.total_enemies_defeated,
                "total_quests_completed": stats.total_quests_completed,
                "total_regions_explored": stats.total_regions_explored,
                "total_exploration_time": stats.total_exploration_time,
                "favorite_region": stats.favorite_region,
                "total_gold_earned": stats.total_gold_earned
            })
        
        return summary
