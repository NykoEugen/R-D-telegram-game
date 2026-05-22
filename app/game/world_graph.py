"""World map graph — BFS pathfinding between locations."""

from collections import deque
from pathlib import Path
from typing import Dict, List, Optional

import yaml

_DATA: Optional[Dict] = None
_YAML_PATH = Path(__file__).parent / "world_map.yaml"


def _load() -> Dict:
    global _DATA
    if _DATA is not None:
        return _DATA
    with open(_YAML_PATH, encoding="utf-8") as f:
        _DATA = yaml.safe_load(f)
    return _DATA


def _t(obj: dict, locale: str) -> str:
    return obj.get(locale) or obj.get("en") or ""


def get_node(node_id: str) -> Optional[Dict]:
    return _load()["nodes"].get(node_id)


def get_node_name(node_id: str, locale: str) -> str:
    node = get_node(node_id)
    return _t(node["name"], locale) if node else node_id


def get_node_description(node_id: str, locale: str) -> str:
    node = get_node(node_id)
    return _t(node["description"], locale) if node else ""


def get_edge_text(from_id: str, to_id: str, locale: str) -> str:
    edges = _load().get("edges", {})
    key = f"{from_id}→{to_id}"
    edge = edges.get(key, {})
    return _t(edge, locale) if edge else ""


def shortest_path(start: str, end: str) -> List[str]:
    """BFS — returns list of node IDs from start (exclusive) to end (inclusive)."""
    if start == end:
        return []
    nodes = _load()["nodes"]
    visited = {start}
    queue: deque[List[str]] = deque([[start]])
    while queue:
        path = queue.popleft()
        current = path[-1]
        for neighbor in nodes.get(current, {}).get("neighbors", []):
            if neighbor == end:
                return path[1:] + [neighbor]  # exclude start
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return [end]  # fallback — direct jump if graph is broken
