"""
World and region system for the Telegram RPG game bot.

This module defines the world structure with regions, difficulty tiers,
and progression mechanics.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import random


class RegionTier(str, Enum):
    """Region difficulty tiers."""
    TIER_1 = "tier_1"  # Beginner areas
    TIER_2 = "tier_2"  # Intermediate areas
    TIER_3 = "tier_3"  # Advanced areas


class RegionType(str, Enum):
    """Types of regions."""
    FOREST = "forest"
    RUINS = "ruins"
    MINES = "mines"
    DUNGEON = "dungeon"
    WILDERNESS = "wilderness"


@dataclass
class RegionDifficulty:
    """Difficulty settings for a region."""
    tier: RegionTier
    level_range: Tuple[int, int]  # (min_level, max_level)
    stat_multiplier: float  # Multiplier for enemy stats
    xp_multiplier: float  # Multiplier for XP rewards
    gold_multiplier: float  # Multiplier for gold rewards
    unlock_requirement: Dict[str, Any]  # Requirements to unlock this region


@dataclass
class RegionEvent:
    """Events that can occur in a region."""
    event_id: str
    name: str
    description: str
    event_type: str  # "combat", "treasure", "story", "trap", "merchant"
    weight: float  # Probability weight
    requirements: List[str] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    consequences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionEnemy:
    """Enemy types available in a region."""
    enemy_type: str
    name: str
    base_level: int
    spawn_weight: float  # Probability weight for spawning
    special_abilities: List[str] = field(default_factory=list)
    loot_table: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RegionLoot:
    """Loot items available in a region."""
    item_id: str
    name: str
    rarity: str  # "common", "uncommon", "rare", "epic", "legendary"
    drop_weight: float
    requirements: List[str] = field(default_factory=list)


@dataclass
class Region:
    """A game region with its properties and content."""
    region_id: str
    name: str
    description: str
    region_type: RegionType
    difficulty: RegionDifficulty
    events: List[RegionEvent] = field(default_factory=list)
    enemies: List[RegionEnemy] = field(default_factory=list)
    loot: List[RegionLoot] = field(default_factory=list)
    connected_regions: List[str] = field(default_factory=list)
    is_unlocked: bool = False


class WorldManager:
    """Manages the game world and region progression."""
    
    # Region definitions
    REGIONS: Dict[str, Region] = {
        "forest_path": Region(
            region_id="forest_path",
            name="Forest Path",
            description="A winding path through ancient woods, where sunlight filters through the canopy above. Perfect for beginning adventurers.",
            region_type=RegionType.FOREST,
            difficulty=RegionDifficulty(
                tier=RegionTier.TIER_1,
                level_range=(1, 3),
                stat_multiplier=1.0,
                xp_multiplier=1.0,
                gold_multiplier=1.0,
                unlock_requirement={"level": 1}  # Always unlocked
            ),
            events=[
                RegionEvent(
                    event_id="forest_goblin_encounter",
                    name="Goblin Ambush",
                    description="A group of goblins jumps out from behind the trees!",
                    event_type="combat",
                    weight=0.4,
                    rewards={"xp": "1d4+2", "gold": "1d6+1"}
                ),
                RegionEvent(
                    event_id="forest_treasure_chest",
                    name="Abandoned Chest",
                    description="You find a weathered chest hidden under some leaves.",
                    event_type="treasure",
                    weight=0.2,
                    rewards={"gold": "2d4+3", "items": ["health_potion"]}
                ),
                RegionEvent(
                    event_id="forest_merchant",
                    name="Traveling Merchant",
                    description="A friendly merchant offers to trade with you.",
                    event_type="merchant",
                    weight=0.15,
                    rewards={"shop_access": True}
                ),
                RegionEvent(
                    event_id="forest_rest_spot",
                    name="Peaceful Clearing",
                    description="A quiet clearing perfect for resting and recovering.",
                    event_type="story",
                    weight=0.25,
                    rewards={"heal": "1d4+2"}
                )
            ],
            enemies=[
                RegionEnemy(
                    enemy_type="goblin",
                    name="Forest Goblin",
                    base_level=1,
                    spawn_weight=0.6,
                    loot_table=[{"item": "goblin_ear", "chance": 0.3}]
                ),
                RegionEnemy(
                    enemy_type="wolf",
                    name="Wild Wolf",
                    base_level=1,
                    spawn_weight=0.3,
                    loot_table=[{"item": "wolf_pelt", "chance": 0.4}]
                ),
                RegionEnemy(
                    enemy_type="spider",
                    name="Giant Spider",
                    base_level=2,
                    spawn_weight=0.1,
                    loot_table=[{"item": "spider_silk", "chance": 0.2}]
                )
            ],
            loot=[
                RegionLoot(
                    item_id="health_potion",
                    name="Health Potion",
                    rarity="common",
                    drop_weight=0.3
                ),
                RegionLoot(
                    item_id="forest_herbs",
                    name="Forest Herbs",
                    rarity="common",
                    drop_weight=0.4
                ),
                RegionLoot(
                    item_id="iron_sword",
                    name="Iron Sword",
                    rarity="uncommon",
                    drop_weight=0.1
                )
            ],
            is_unlocked=True  # Always available
        ),
        
        "old_ruins": Region(
            region_id="old_ruins",
            name="Old Ruins",
            description="Ancient stone structures covered in moss and vines. The air hums with mysterious energy, and shadows seem to move on their own.",
            region_type=RegionType.RUINS,
            difficulty=RegionDifficulty(
                tier=RegionTier.TIER_2,
                level_range=(3, 6),
                stat_multiplier=1.5,
                xp_multiplier=1.3,
                gold_multiplier=1.2,
                unlock_requirement={"level": 3}
            ),
            events=[
                RegionEvent(
                    event_id="ruins_skeleton_encounter",
                    name="Undead Guardians",
                    description="Ancient skeletons rise from the rubble to defend their resting place!",
                    event_type="combat",
                    weight=0.5,
                    rewards={"xp": "2d4+3", "gold": "2d6+2"}
                ),
                RegionEvent(
                    event_id="ruins_ancient_treasure",
                    name="Ancient Artifact",
                    description="You discover a glowing artifact buried in the ruins.",
                    event_type="treasure",
                    weight=0.2,
                    rewards={"gold": "3d6+5", "items": ["ancient_amulet"]}
                ),
                RegionEvent(
                    event_id="ruins_trap",
                    name="Crumbling Floor",
                    description="The floor gives way beneath you! You barely avoid falling into a pit.",
                    event_type="trap",
                    weight=0.15,
                    consequences={"damage": "1d4+1"}
                ),
                RegionEvent(
                    event_id="ruins_ghost_encounter",
                    name="Wailing Spirit",
                    description="A ghostly figure appears, seeking help to find peace.",
                    event_type="story",
                    weight=0.15,
                    rewards={"xp": "1d6+2", "quest": "help_ghost"}
                )
            ],
            enemies=[
                RegionEnemy(
                    enemy_type="skeleton",
                    name="Ancient Skeleton",
                    base_level=3,
                    spawn_weight=0.5,
                    special_abilities=["undead_resistance"],
                    loot_table=[{"item": "bone_fragment", "chance": 0.4}]
                ),
                RegionEnemy(
                    enemy_type="ghost",
                    name="Wailing Ghost",
                    base_level=4,
                    spawn_weight=0.3,
                    special_abilities=["ethereal", "fear_aura"],
                    loot_table=[{"item": "ectoplasm", "chance": 0.3}]
                ),
                RegionEnemy(
                    enemy_type="gargoyle",
                    name="Stone Gargoyle",
                    base_level=5,
                    spawn_weight=0.2,
                    special_abilities=["stone_skin", "flight"],
                    loot_table=[{"item": "stone_shard", "chance": 0.2}]
                )
            ],
            loot=[
                RegionLoot(
                    item_id="ancient_amulet",
                    name="Ancient Amulet",
                    rarity="rare",
                    drop_weight=0.05
                ),
                RegionLoot(
                    item_id="magic_scroll",
                    name="Magic Scroll",
                    rarity="uncommon",
                    drop_weight=0.15
                ),
                RegionLoot(
                    item_id="ruins_gold",
                    name="Ancient Coins",
                    rarity="common",
                    drop_weight=0.4
                )
            ],
            connected_regions=["forest_path"]
        ),
        
        "dwarven_mines": Region(
            region_id="dwarven_mines",
            name="Dwarven Mines",
            description="Deep underground tunnels carved into the mountain. The sound of pickaxes echoes through the darkness, but no living dwarf has been seen here in years.",
            region_type=RegionType.MINES,
            difficulty=RegionDifficulty(
                tier=RegionTier.TIER_3,
                level_range=(6, 10),
                stat_multiplier=2.0,
                xp_multiplier=1.8,
                gold_multiplier=1.5,
                unlock_requirement={"level": 6, "quest": "clear_ruins"}
            ),
            events=[
                RegionEvent(
                    event_id="mines_cave_in",
                    name="Cave In",
                    description="The tunnel collapses behind you! You must find another way out.",
                    event_type="trap",
                    weight=0.2,
                    consequences={"blocked_exit": True}
                ),
                RegionEvent(
                    event_id="mines_dragon_encounter",
                    name="Ancient Dragon",
                    description="A massive dragon awakens from its slumber, its eyes glowing with ancient wisdom and power!",
                    event_type="combat",
                    weight=0.1,
                    rewards={"xp": "5d8+10", "gold": "10d10+20", "items": ["dragon_scale"]}
                ),
                RegionEvent(
                    event_id="mines_dwarven_treasure",
                    name="Dwarven Vault",
                    description="You discover a hidden vault filled with dwarven treasures and artifacts.",
                    event_type="treasure",
                    weight=0.3,
                    rewards={"gold": "8d12+15", "items": ["dwarven_armor", "mithril_ore"]}
                ),
                RegionEvent(
                    event_id="mines_forge_discovery",
                    name="Ancient Forge",
                    description="You find an ancient dwarven forge still burning with magical flames.",
                    event_type="story",
                    weight=0.2,
                    rewards={"crafting_access": True, "xp": "2d6+3"}
                ),
                RegionEvent(
                    event_id="mines_underground_lake",
                    name="Underground Lake",
                    description="A beautiful underground lake with crystal-clear water and glowing fish.",
                    event_type="story",
                    weight=0.2,
                    rewards={"heal": "2d6+4", "items": ["glowing_pearl"]}
                )
            ],
            enemies=[
                RegionEnemy(
                    enemy_type="cave_troll",
                    name="Cave Troll",
                    base_level=6,
                    spawn_weight=0.4,
                    special_abilities=["regeneration", "stone_throw"],
                    loot_table=[{"item": "troll_claw", "chance": 0.3}]
                ),
                RegionEnemy(
                    enemy_type="earth_elemental",
                    name="Earth Elemental",
                    base_level=7,
                    spawn_weight=0.3,
                    special_abilities=["earth_magic", "immune_physical"],
                    loot_table=[{"item": "earth_crystal", "chance": 0.4}]
                ),
                RegionEnemy(
                    enemy_type="dragon",
                    name="Ancient Dragon",
                    base_level=10,
                    spawn_weight=0.1,
                    special_abilities=["fire_breath", "flight", "magic_resistance"],
                    loot_table=[{"item": "dragon_scale", "chance": 0.8}]
                ),
                RegionEnemy(
                    enemy_type="dark_dwarf",
                    name="Corrupted Dwarf",
                    base_level=8,
                    spawn_weight=0.2,
                    special_abilities=["dark_magic", "mining_expertise"],
                    loot_table=[{"item": "corrupted_ore", "chance": 0.5}]
                )
            ],
            loot=[
                RegionLoot(
                    item_id="dragon_scale",
                    name="Dragon Scale",
                    rarity="legendary",
                    drop_weight=0.01
                ),
                RegionLoot(
                    item_id="mithril_ore",
                    name="Mithril Ore",
                    rarity="epic",
                    drop_weight=0.05
                ),
                RegionLoot(
                    item_id="dwarven_armor",
                    name="Dwarven Armor",
                    rarity="rare",
                    drop_weight=0.1
                ),
                RegionLoot(
                    item_id="earth_crystal",
                    name="Earth Crystal",
                    rarity="uncommon",
                    drop_weight=0.2
                )
            ],
            connected_regions=["old_ruins"]
        )
    }
    
    @staticmethod
    def get_available_regions(player_level: int, completed_quests: List[str] = None) -> List[Region]:
        """Get regions available to a player based on their level and progress."""
        if completed_quests is None:
            completed_quests = []
        
        available = []
        for region in WorldManager.REGIONS.values():
            if WorldManager._can_access_region(region, player_level, completed_quests):
                available.append(region)
        
        return available
    
    @staticmethod
    def _can_access_region(region: Region, player_level: int, completed_quests: List[str]) -> bool:
        """Check if a player can access a specific region."""
        req = region.difficulty.unlock_requirement
        
        # Check level requirement
        if "level" in req and player_level < req["level"]:
            return False
        
        # Check quest requirement
        if "quest" in req and req["quest"] not in completed_quests:
            return False
        
        return True
    
    @staticmethod
    def get_region_by_id(region_id: str) -> Optional[Region]:
        """Get a region by its ID."""
        return WorldManager.REGIONS.get(region_id)
    
    @staticmethod
    def get_random_event(region: Region, player_stats: Dict[str, Any] = None) -> Optional[RegionEvent]:
        """Get a random event for a region based on weights and requirements."""
        if player_stats is None:
            player_stats = {}
        
        # Filter events by requirements
        available_events = []
        for event in region.events:
            if WorldManager._meets_requirements(event.requirements, player_stats):
                available_events.append(event)
        
        if not available_events:
            return None
        
        # Weighted random selection
        total_weight = sum(event.weight for event in available_events)
        if total_weight == 0:
            return None
        
        random_value = random.random() * total_weight
        current_weight = 0
        
        for event in available_events:
            current_weight += event.weight
            if random_value <= current_weight:
                return event
        
        return available_events[-1]  # Fallback
    
    @staticmethod
    def get_random_enemy(region: Region, player_level: int) -> Optional[RegionEnemy]:
        """Get a random enemy for a region based on weights and level scaling."""
        # Filter enemies by level range
        available_enemies = []
        for enemy in region.enemies:
            if region.difficulty.level_range[0] <= enemy.base_level <= region.difficulty.level_range[1]:
                available_enemies.append(enemy)
        
        if not available_enemies:
            return None
        
        # Weighted random selection
        total_weight = sum(enemy.spawn_weight for enemy in available_enemies)
        if total_weight == 0:
            return None
        
        random_value = random.random() * total_weight
        current_weight = 0
        
        for enemy in available_enemies:
            current_weight += enemy.spawn_weight
            if random_value <= current_weight:
                return enemy
        
        return available_enemies[-1]  # Fallback
    
    @staticmethod
    def get_random_loot(region: Region, player_stats: Dict[str, Any] = None) -> List[RegionLoot]:
        """Get random loot from a region based on weights and requirements."""
        if player_stats is None:
            player_stats = {}
        
        # Filter loot by requirements
        available_loot = []
        for loot in region.loot:
            if WorldManager._meets_requirements(loot.requirements, player_stats):
                available_loot.append(loot)
        
        if not available_loot:
            return []
        
        # Random selection based on weights
        selected_loot = []
        for loot in available_loot:
            if random.random() < loot.drop_weight:
                selected_loot.append(loot)
        
        return selected_loot
    
    @staticmethod
    def _meets_requirements(requirements: List[str], player_stats: Dict[str, Any]) -> bool:
        """Check if player meets event/loot requirements."""
        for req in requirements:
            if req.startswith("level>="):
                min_level = int(req.split(">=")[1])
                if player_stats.get("level", 1) < min_level:
                    return False
            elif req.startswith("stat:"):
                # Handle stat requirements (e.g., "stat:strength>=15")
                stat_req = req.split(":")[1]
                if ">=" in stat_req:
                    stat_name, min_value = stat_req.split(">=")
                    if player_stats.get(stat_name, 0) < int(min_value):
                        return False
            # Add more requirement types as needed
        
        return True
    
    @staticmethod
    def get_region_difficulty_multiplier(region: Region) -> float:
        """Get the stat multiplier for enemies in a region."""
        return region.difficulty.stat_multiplier
    
    @staticmethod
    def get_region_reward_multipliers(region: Region) -> Tuple[float, float]:
        """Get XP and gold multipliers for a region."""
        return region.difficulty.xp_multiplier, region.difficulty.gold_multiplier
