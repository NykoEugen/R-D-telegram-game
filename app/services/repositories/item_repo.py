"""
Item repository for the Telegram RPG game bot.

This module provides data access methods for Item and InventoryItem entities.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.items import Item, InventoryItem, ItemRarity, ItemType
from app.models.player import Player


class ItemRepository:
    """Repository class for Item and InventoryItem entity operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Item management methods
    async def create_item(
        self,
        item_id: str,
        name: str,
        item_type: ItemType,
        rarity: ItemRarity = ItemRarity.COMMON,
        **kwargs
    ) -> Item:
        """
        Create a new item.
        
        Args:
            item_id: Unique item identifier
            name: Item name
            item_type: Type of item
            rarity: Item rarity
            **kwargs: Additional item attributes
            
        Returns:
            Item: The created item instance
            
        Raises:
            ValueError: If item_id already exists
        """
        # Check if item already exists
        existing_item = await self.get_item_by_item_id(item_id)
        if existing_item:
            raise ValueError(f"Item with ID {item_id} already exists")
        
        # Create new item
        item_data = {
            "item_id": item_id,
            "name": name,
            "item_type": item_type,
            "rarity": rarity,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        # Add any additional attributes
        item_data.update(kwargs)
        
        item = Item(**item_data)
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        
        return item
    
    async def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """
        Get an item by its database ID.
        
        Args:
            item_id: The item database ID
            
        Returns:
            Item or None if not found
        """
        stmt = select(Item).where(Item.id == item_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_item_by_item_id(self, item_id: str) -> Optional[Item]:
        """
        Get an item by its unique item identifier.
        
        Args:
            item_id: The unique item identifier
            
        Returns:
            Item or None if not found
        """
        stmt = select(Item).where(Item.item_id == item_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_items_by_type(self, item_type: ItemType) -> List[Item]:
        """
        Get all items of a specific type.
        
        Args:
            item_type: The item type to filter by
            
        Returns:
            List of items of the specified type
        """
        stmt = select(Item).where(and_(Item.item_type == item_type, Item.is_active == True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_items_by_rarity(self, rarity: ItemRarity) -> List[Item]:
        """
        Get all items of a specific rarity.
        
        Args:
            rarity: The item rarity to filter by
            
        Returns:
            List of items of the specified rarity
        """
        stmt = select(Item).where(and_(Item.rarity == rarity, Item.is_active == True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_items(self, query: str, limit: int = 50) -> List[Item]:
        """
        Search for items by name or description.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching items
        """
        search_term = f"%{query}%"
        stmt = (
            select(Item)
            .where(
                and_(
                    Item.is_active == True,
                    or_(
                        Item.name.ilike(search_term),
                        Item.description.ilike(search_term)
                    )
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    # Inventory management methods
    async def add_item_to_inventory(
        self,
        player_id: int,
        item_id: str,
        quantity: int = 1,
        acquired_from: Optional[str] = None,
        **kwargs
    ) -> Optional[InventoryItem]:
        """
        Add an item to a player's inventory.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            quantity: Quantity to add
            acquired_from: How the item was obtained
            **kwargs: Additional inventory item attributes
            
        Returns:
            InventoryItem or None if item not found
        """
        # Get the item
        item = await self.get_item_by_item_id(item_id)
        if not item:
            return None
        
        # Check if player already has this item and if it's stackable
        existing_inventory_item = await self.get_inventory_item(player_id, item_id)
        
        if existing_inventory_item and item.is_stackable:
            # Add to existing stack
            new_quantity = existing_inventory_item.quantity + quantity
            if new_quantity > item.max_stack_size:
                # Split into multiple stacks if needed
                remaining_quantity = new_quantity - item.max_stack_size
                existing_inventory_item.quantity = item.max_stack_size
                await self.session.flush()
                
                # Create new stack for remaining quantity
                return await self.add_item_to_inventory(
                    player_id, item_id, remaining_quantity, acquired_from, **kwargs
                )
            else:
                existing_inventory_item.quantity = new_quantity
                existing_inventory_item.updated_at = datetime.utcnow()
                await self.session.flush()
                return existing_inventory_item
        else:
            # Create new inventory item
            inventory_data = {
                "player_id": player_id,
                "item_id": item.id,
                "quantity": min(quantity, item.max_stack_size),
                "acquired_from": acquired_from,
                "acquired_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            # Add any additional attributes
            inventory_data.update(kwargs)
            
            inventory_item = InventoryItem(**inventory_data)
            self.session.add(inventory_item)
            await self.session.flush()
            await self.session.refresh(inventory_item)
            
            # If quantity exceeds max stack size, create additional stacks
            remaining_quantity = quantity - inventory_item.quantity
            if remaining_quantity > 0:
                await self.add_item_to_inventory(
                    player_id, item_id, remaining_quantity, acquired_from, **kwargs
                )
            
            return inventory_item
    
    async def remove_item_from_inventory(
        self,
        player_id: int,
        item_id: str,
        quantity: int = 1
    ) -> bool:
        """
        Remove items from a player's inventory.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            quantity: Quantity to remove
            
        Returns:
            True if items were removed, False if insufficient quantity
        """
        # Get inventory items for this item
        inventory_items = await self.get_inventory_items_by_item_id(player_id, item_id)
        
        if not inventory_items:
            return False
        
        # Calculate total available quantity
        total_quantity = sum(inv_item.quantity for inv_item in inventory_items)
        
        if total_quantity < quantity:
            return False
        
        # Remove items starting from the first inventory item
        remaining_to_remove = quantity
        
        for inv_item in inventory_items:
            if remaining_to_remove <= 0:
                break
            
            if inv_item.quantity <= remaining_to_remove:
                # Remove entire stack
                remaining_to_remove -= inv_item.quantity
                await self.session.delete(inv_item)
            else:
                # Reduce quantity in this stack
                inv_item.quantity -= remaining_to_remove
                inv_item.updated_at = datetime.utcnow()
                remaining_to_remove = 0
        
        await self.session.flush()
        return True
    
    async def get_inventory_item(self, player_id: int, item_id: str) -> Optional[InventoryItem]:
        """
        Get a specific inventory item for a player.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            
        Returns:
            InventoryItem or None if not found
        """
        stmt = (
            select(InventoryItem)
            .join(Item, InventoryItem.item_id == Item.id)
            .where(
                and_(
                    InventoryItem.player_id == player_id,
                    Item.item_id == item_id
                )
            )
            .options(selectinload(InventoryItem.item))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_inventory_items_by_item_id(self, player_id: int, item_id: str) -> List[InventoryItem]:
        """
        Get all inventory items of a specific item type for a player.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            
        Returns:
            List of inventory items
        """
        stmt = (
            select(InventoryItem)
            .join(Item, InventoryItem.item_id == Item.id)
            .where(
                and_(
                    InventoryItem.player_id == player_id,
                    Item.item_id == item_id
                )
            )
            .options(selectinload(InventoryItem.item))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_player_inventory(self, player_id: int) -> List[InventoryItem]:
        """
        Get all items in a player's inventory.
        
        Args:
            player_id: The player ID
            
        Returns:
            List of inventory items with item details
        """
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.player_id == player_id)
            .options(selectinload(InventoryItem.item))
            .order_by(InventoryItem.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_equipped_items(self, player_id: int) -> List[InventoryItem]:
        """
        Get all equipped items for a player.
        
        Args:
            player_id: The player ID
            
        Returns:
            List of equipped inventory items
        """
        stmt = (
            select(InventoryItem)
            .where(
                and_(
                    InventoryItem.player_id == player_id,
                    InventoryItem.is_equipped == True
                )
            )
            .options(selectinload(InventoryItem.item))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def equip_item(self, player_id: int, item_id: str, equipment_slot: str) -> bool:
        """
        Equip an item for a player.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            equipment_slot: The equipment slot to equip to
            
        Returns:
            True if equipped, False if item not found or already equipped
        """
        inventory_item = await self.get_inventory_item(player_id, item_id)
        if not inventory_item or inventory_item.is_equipped:
            return False
        
        # Unequip any item in the same slot first
        await self.unequip_slot(player_id, equipment_slot)
        
        # Equip the new item
        inventory_item.is_equipped = True
        inventory_item.equipment_slot = equipment_slot
        inventory_item.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return True
    
    async def unequip_item(self, player_id: int, item_id: str) -> bool:
        """
        Unequip an item for a player.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            
        Returns:
            True if unequipped, False if item not found or not equipped
        """
        inventory_item = await self.get_inventory_item(player_id, item_id)
        if not inventory_item or not inventory_item.is_equipped:
            return False
        
        inventory_item.is_equipped = False
        inventory_item.equipment_slot = None
        inventory_item.updated_at = datetime.utcnow()
        
        await self.session.flush()
        return True
    
    async def unequip_slot(self, player_id: int, equipment_slot: str) -> bool:
        """
        Unequip any item in a specific equipment slot.
        
        Args:
            player_id: The player ID
            equipment_slot: The equipment slot to unequip
            
        Returns:
            True if an item was unequipped, False if slot was empty
        """
        stmt = (
            update(InventoryItem)
            .where(
                and_(
                    InventoryItem.player_id == player_id,
                    InventoryItem.equipment_slot == equipment_slot,
                    InventoryItem.is_equipped == True
                )
            )
            .values(
                is_equipped=False,
                equipment_slot=None,
                updated_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_inventory_count(self, player_id: int) -> int:
        """
        Get the total number of items in a player's inventory.
        
        Args:
            player_id: The player ID
            
        Returns:
            Total number of inventory items
        """
        stmt = select(func.count(InventoryItem.id)).where(InventoryItem.player_id == player_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_item_quantity(self, player_id: int, item_id: str) -> int:
        """
        Get the total quantity of a specific item in a player's inventory.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            
        Returns:
            Total quantity of the item
        """
        stmt = (
            select(func.sum(InventoryItem.quantity))
            .join(Item, InventoryItem.item_id == Item.id)
            .where(
                and_(
                    InventoryItem.player_id == player_id,
                    Item.item_id == item_id
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def has_item(self, player_id: int, item_id: str, quantity: int = 1) -> bool:
        """
        Check if a player has a specific item in sufficient quantity.
        
        Args:
            player_id: The player ID
            item_id: The item identifier
            quantity: Required quantity
            
        Returns:
            True if player has sufficient quantity, False otherwise
        """
        available_quantity = await self.get_item_quantity(player_id, item_id)
        return available_quantity >= quantity
    
    async def transfer_item(
        self,
        from_player_id: int,
        to_player_id: int,
        item_id: str,
        quantity: int = 1
    ) -> bool:
        """
        Transfer items between players.
        
        Args:
            from_player_id: Source player ID
            to_player_id: Destination player ID
            item_id: The item identifier
            quantity: Quantity to transfer
            
        Returns:
            True if transfer successful, False if insufficient items
        """
        # Check if source player has enough items
        if not await self.has_item(from_player_id, item_id, quantity):
            return False
        
        # Remove from source player
        if not await self.remove_item_from_inventory(from_player_id, item_id, quantity):
            return False
        
        # Add to destination player
        inventory_item = await self.add_item_to_inventory(
            to_player_id, item_id, quantity, acquired_from=f"transfer_from_player_{from_player_id}"
        )
        
        return inventory_item is not None
    
    async def get_inventory_summary(self, player_id: int) -> Dict[str, Any]:
        """
        Get a summary of a player's inventory.
        
        Args:
            player_id: The player ID
            
        Returns:
            Dictionary with inventory summary
        """
        inventory_items = await self.get_player_inventory(player_id)
        equipped_items = await self.get_equipped_items(player_id)
        
        # Group items by type
        items_by_type = {}
        total_items = 0
        total_value = 0
        
        for inv_item in inventory_items:
            item = inv_item.item
            item_type = item.item_type.value
            
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            
            items_by_type[item_type].append({
                "item_id": item.item_id,
                "name": item.name,
                "quantity": inv_item.quantity,
                "rarity": item.rarity.value,
                "is_equipped": inv_item.is_equipped,
                "equipment_slot": inv_item.equipment_slot,
            })
            
            total_items += inv_item.quantity
            total_value += item.base_value * inv_item.quantity
        
        return {
            "total_items": total_items,
            "total_value": total_value,
            "equipped_count": len(equipped_items),
            "items_by_type": items_by_type,
            "inventory_count": len(inventory_items),
        }
