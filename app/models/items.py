"""
Items and inventory models for the Telegram RPG game bot.

This module defines Item and InventoryItem models with rarity, attributes, and stackability.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ItemRarity(str, Enum):
    """Item rarity enumeration."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class ItemType(str, Enum):
    """Item type enumeration."""
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    QUEST_ITEM = "quest_item"
    CURRENCY = "currency"
    MISC = "misc"


class Item(Base):
    """Item model representing game items with properties and attributes."""
    
    __tablename__ = "items"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Item identification
    item_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Item properties
    item_type: Mapped[ItemType] = mapped_column(String(50), nullable=False)
    rarity: Mapped[ItemRarity] = mapped_column(String(20), nullable=False)
    level_requirement: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Stackability and quantity
    is_stackable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_stack_size: Mapped[int] = mapped_column(Integer, default=99, nullable=False)
    
    # Item attributes (JSON for flexibility)
    attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Item stats (for equipment)
    health_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mana_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    strength_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agility_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    intelligence_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vitality_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Item value and economy
    base_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sell_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Item availability
    is_tradeable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_droppable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Item effects (for consumables and special items)
    effects: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Item tags for categorization
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    inventory_items: Mapped[List["InventoryItem"]] = relationship("InventoryItem", back_populates="item")
    
    def __repr__(self) -> str:
        return f"<Item(id={self.id}, item_id={self.item_id}, name={self.name}, rarity={self.rarity})>"


class InventoryItem(Base):
    """InventoryItem model representing items owned by players."""
    
    __tablename__ = "inventory_items"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"), nullable=False)
    
    # Item instance properties
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    equipment_slot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # For equipped items
    
    # Item instance data (for unique items with custom properties)
    instance_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Item condition and durability
    durability: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_durability: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Item acquisition
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    acquired_from: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # How the item was obtained
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="inventory_items")
    item: Mapped["Item"] = relationship("Item", back_populates="inventory_items")
    
    def __repr__(self) -> str:
        return f"<InventoryItem(id={self.id}, player_id={self.player_id}, item_id={self.item_id}, quantity={self.quantity})>"
