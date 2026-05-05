"""Semantic Unity asset catalogue and placement tools.

These tools sit above the low-level Unity AssetDatabase RPCs. They make the
LLM prefer real project assets (trees, rocks, props, characters, materials)
instead of falling back to primitives when the user asks for realistic content.
"""
from __future__ import annotations

import math
import random
import re
from difflib import SequenceMatcher
from pathlib import PurePosixPath
from typing import Any

from ..core.tool_registry import tool


_UNITY = None  # type: ignore


_INSTANTIABLE_EXTENSIONS = {".prefab", ".fbx", ".glb", ".gltf", ".obj"}
_MATERIAL_EXTENSIONS = {".mat"}
_TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".exr", ".hdr", ".psd"}
_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".aif", ".aiff"}


_CATEGORY_TERMS: dict[str, list[str]] = {
    "tree": [
        "tree", "trees", "pine", "fir", "oak", "birch", "spruce", "trunk", "stump",
        "forest", "wood", "woods", "leaf", "leaves", "foliage", "islandtree", "deadtree",
    ],
    "rock": [
        "rock", "rocks", "boulder", "stone", "stones", "cliff", "cliffs", "cave",
        "moss", "mossy", "gravel", "mountain", "rockface",
    ],
    "grass": [
        "grass", "bush", "bushes", "shrub", "shrubs", "fern", "plant", "plants",
        "flower", "flowers", "foliage", "weed", "weeds", "nature",
    ],
    "building": [
        "building", "house", "hut", "cabin", "castle", "tower", "wall", "gate",
        "village", "ruin", "ruins", "fort", "bridge", "roof", "door", "window",
    ],
    "prop": [
        "prop", "barrel", "crate", "chest", "box", "lantern", "torch", "bucket",
        "basket", "table", "chair", "sign", "pot", "vase", "bag", "campfire",
    ],
    "character": [
        "character", "human", "humanoid", "warrior", "mage", "wizard", "archer",
        "ninja", "shaman", "enemy", "monster", "orc", "goblin", "player", "body",
    ],
    "weapon": [
        "weapon", "sword", "axe", "bow", "crossbow", "staff", "wand", "shield",
        "dagger", "knife", "spear", "hammer", "mace", "arrow",
    ],
    "armor": [
        "armor", "armour", "helmet", "glove", "gloves", "boots", "belt", "cloak",
        "robe", "gauntlet", "mask", "hood", "chestplate",
    ],
    "material": [
        "material", "mat", "pbr", "surface", "metal", "wood", "stone", "rock",
        "grass", "mud", "water", "fabric", "leather",
    ],
    "texture": [
        "texture", "textures", "albedo", "normal", "roughness", "metallic", "mask",
        "diffuse", "basecolor", "height", "ao",
    ],
    "audio": [
        "audio", "sound", "sfx", "music", "ambience", "ambient", "wav", "ogg", "mp3",
    ],
}

_QUALITY_TERMS = {
    "real", "realistic", "realist", "relis", "relise", "hd", "high", "quality",
    "pbr", "scanned", "scan", "photogrammetry", "polyhaven", "sketchfab", "fantasy",
}


def _ensure_unity() -> tuple[bool, str]:
    if _UNITY is None:
        return False, "UnityBridge is not initialized"
    if not _UNITY.is_connected():
        return False, "Could not connect to the Unity Editor"
    return True, ""


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _tokens(value: str) -> list[str]:
    return [token for token in _norm(value).split() if token]


def _similar(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.88
    return SequenceMatcher(None, a, b).ratio()


def _best_category(query: str, explicit: str = "") -> str:
    explicit = _norm(explicit)
    if explicit in _CATEGORY_TERMS:
        return explicit
    query_tokens = _tokens(query)
    best_name = ""
    best_score = 0.0
    for category, terms in _CATEGORY_TERMS.items():
        score = 0.0
        for qt in query_tokens:
            score = max(score, max(_similar(qt, term) for term in terms))
        if score > best_score:
            best_name = category
            best_score = score
    return best_name if best_score >= 0.62 else ""


def _expanded_terms(query: str, category: str = "") -> list[str]:
    query_tokens = _tokens(query)
    terms: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        value = _norm(value)
        if value and value not in seen:
            seen.add(value)
            terms.append(value)

    add(query)
    for token in query_tokens:
        if token not in _QUALITY_TERMS:
            add(token)

    category = _best_category(query, category)
    if category:
        for term in _CATEGORY_TERMS[category]:
            add(term)

    for token in query_tokens:
        for cat_terms in _CATEGORY_TERMS.values():
            for term in cat_terms:
                if _similar(token, term) >= 0.78:
                    add(term)

    # Keep RPC count bounded; Unity AssetDatabase calls are fast individually but
    # many sequential calls can make local models look like they timed out.
    return terms[:10]


def _asset_name(path: str) -> str:
    return PurePosixPath(path).stem


def _extension(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def _folder(path: str) -> str:
    return str(PurePosixPath(path).parent)


def _category_for_asset(path: str, main_type: str = "") -> str:
    hay = _norm(f"{path} {main_type}")
    best_name = "other"
    best_score = 0.0
    for category, terms in _CATEGORY_TERMS.items():
        score = max((_similar(term, token) for term in terms for token in hay.split()), default=0.0)
        if score > best_score:
            best_name = category
            best_score = score
    return best_name if best_score >= 0.72 else "other"


def _is_instantiable(asset: dict[str, Any]) -> bool:
    path = str(asset.get("path", ""))
    main_type = str(asset.get("main_type", ""))
    return _extension(path) in _INSTANTIABLE_EXTENSIONS or main_type in {"GameObject", "Prefab"}


def _call_find_assets(query: str, asset_type: str = "", folders: list[str] | None = None, max_results: int = 100) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"query": query, "type": asset_type, "max_results": max_results}
    if folders:
        params["folders"] = folders
    result = _UNITY.call("find_assets", params, timeout=30)
    if not isinstance(result, dict):
        return []
    return [item for item in result.get("results", []) if isinstance(item, dict)]


def _search_candidates(
    query: str = "",
    category: str = "",
    asset_types: list[str] | None = None,
    folders: list[str] | None = None,
    max_results: int = 50,
    instantiable_only: bool = False,
) -> list[dict[str, Any]]:
    asset_types = asset_types or ["GameObject", ""]
    terms = _expanded_terms(query or category, category)
    by_path: dict[str, dict[str, Any]] = {}

    for term in terms:
        for asset_type in asset_types:
            for item in _call_find_assets(term, asset_type, folders, max(max_results, 80)):
                path = str(item.get("path", ""))
                if not path:
                    continue
                if instantiable_only and not _is_instantiable(item):
                    continue
                current = by_path.setdefault(path, dict(item))
                current.setdefault("_matched_terms", [])
                current["_matched_terms"].append(term)

    ranked = [_rank_asset(item, query, category) for item in by_path.values()]
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:max_results]


def _rank_asset(asset: dict[str, Any], query: str, category: str = "") -> dict[str, Any]:
    path = str(asset.get("path", ""))
    main_type = str(asset.get("main_type", ""))
    name = _asset_name(path)
    hay_tokens = _tokens(f"{path} {main_type}")
    query_tokens = [t for t in _tokens(query) if t not in _QUALITY_TERMS]
    expanded = _expanded_terms(query, category)
    score = 0.0

    for qt in query_tokens:
        score += max((_similar(qt, token) for token in hay_tokens), default=0.0) * 10.0
    for term in expanded:
        term_tokens = _tokens(term)
        if any(token in hay_tokens for token in term_tokens):
            score += 4.0
    for matched in asset.get("_matched_terms", []):
        score += 1.5

    lower_path = path.lower()
    if "polyhaven" in lower_path:
        score += 8.0
    if "sketchfab" in lower_path:
        score += 5.0
    if "fantasyrpg" in lower_path:
        score += 3.0
    if _is_instantiable(asset):
        score += 12.0
    if _extension(path) == ".prefab":
        score += 5.0
    if "generated" in lower_path:
        score -= 2.0

    detected_category = _category_for_asset(path, main_type)
    requested_category = _best_category(query, category)
    if requested_category and detected_category == requested_category:
        score += 15.0

    clean = {k: v for k, v in asset.items() if not k.startswith("_")}
    clean.update(
        {
            "name": name,
            "folder": _folder(path),
            "extension": _extension(path),
            "category": detected_category,
            "instantiable": _is_instantiable(asset),
            "score": round(score, 3),
        }
    )
    return clean


def _group_assets(assets: list[dict[str, Any]], group_by: str, max_per_group: int) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        key = str(asset.get(group_by, "")) if group_by in asset else str(asset.get("category", "other"))
        if not key:
            key = "other"
        groups.setdefault(key, [])
        if len(groups[key]) < max_per_group:
            groups[key].append(asset)
    return dict(sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def _instantiate_items(items: list[dict[str, Any]], max_items: int = 200) -> dict:
    result = _UNITY.call("instantiate_prefabs", {"items": items, "max": max_items}, timeout=60)
    return result if isinstance(result, dict) else {"result": result}


@tool(description="Semantic Unity asset search. Use this before primitives for realistic trees, rocks, props, buildings, characters, materials, or misspelled asset requests.")
def unity_search_assets_semantic(
    query: str,
    category: str = "",
    folders: list[str] | None = None,
    max_results: int = 50,
    group_by: str = "",
    instantiable_only: bool = False,
) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        assets = _search_candidates(query, category, folders=folders, max_results=max_results, instantiable_only=instantiable_only)
        result: dict[str, Any] = {
            "ok": True,
            "action_performed": "search_only",
            "placed_in_scene": False,
            "query": query,
            "category": _best_category(query, category) or category,
            "expanded_terms": _expanded_terms(query, category),
            "count": len(assets),
            "results": assets,
        }
        if group_by:
            result["groups"] = _group_assets(assets, group_by, max_per_group=12)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Rank Unity asset candidates for a natural-language query, returning the best real project assets first.")
def unity_rank_asset_candidates(query: str, category: str = "", max_results: int = 25) -> dict:
    return unity_search_assets_semantic(query=query, category=category, max_results=max_results, instantiable_only=False)


@tool(description="Search and group Unity assets by category/folder/main_type/extension. Useful to show what real assets exist before placing them.")
def unity_group_assets_by_category(query: str = "", max_results: int = 120, max_per_group: int = 20, group_by: str = "category") -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        assets = _search_candidates(query or "nature prop character weapon", max_results=max_results)
        return {
            "ok": True,
            "action_performed": "search_only",
            "placed_in_scene": False,
            "query": query,
            "group_by": group_by,
            "groups": _group_assets(assets, group_by, max_per_group),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Summarize the project's real asset catalogue by common categories such as tree, rock, grass, building, prop, character, weapon, material, texture.")
def unity_get_asset_catalog_summary(max_per_group: int = 10) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        summary: dict[str, Any] = {}
        for category in _CATEGORY_TERMS:
            assets = _search_candidates(category, category=category, max_results=max_per_group, instantiable_only=False)
            summary[category] = {"count_sampled": len(assets), "results": assets[:max_per_group]}
        return {"ok": True, "action_performed": "search_only", "placed_in_scene": False, "groups": summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find realistic/high-quality assets matching a query. Expands real/realistic/PBR/PolyHaven/Sketchfab-style terms.")
def unity_find_realistic_assets(query: str, max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=f"realistic pbr polyhaven sketchfab {query}", max_results=max_results)


@tool(description="Find real tree/forest assets in the Unity project.")
def unity_find_tree_assets(query: str = "realistic tree", max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=query, category="tree", max_results=max_results, instantiable_only=True)


@tool(description="Find real rock/boulder/cliff assets in the Unity project.")
def unity_find_rock_assets(query: str = "realistic rock", max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=query, category="rock", max_results=max_results, instantiable_only=True)


@tool(description="Find real grass/bush/plant/foliage assets in the Unity project.")
def unity_find_grass_assets(query: str = "grass foliage", max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=query, category="grass", max_results=max_results, instantiable_only=True)


@tool(description="Find real building/house/castle/ruin assets in the Unity project.")
def unity_find_building_assets(query: str = "building", max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=query, category="building", max_results=max_results, instantiable_only=True)


@tool(description="Find real prop assets such as barrels, crates, chests, lanterns, furniture, camp props.")
def unity_find_prop_assets(query: str = "prop", max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=query, category="prop", max_results=max_results, instantiable_only=True)


@tool(description="Find real character/enemy/humanoid assets in the Unity project.")
def unity_find_character_assets(query: str = "character", max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=query, category="character", max_results=max_results, instantiable_only=True)


@tool(description="Find real weapon assets in the Unity project.")
def unity_find_weapon_assets(query: str = "weapon", max_results: int = 50) -> dict:
    return unity_search_assets_semantic(query=query, category="weapon", max_results=max_results, instantiable_only=True)


@tool(description="Find Unity material assets (.mat or material-like assets).")
def unity_find_material_assets(query: str = "material", max_results: int = 50) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        assets = _search_candidates(query, category="material", asset_types=["Material", ""], max_results=max_results)
        assets = [a for a in assets if a["extension"] in _MATERIAL_EXTENSIONS or a.get("main_type") == "Material"][:max_results]
        return {"ok": True, "action_performed": "search_only", "placed_in_scene": False, "query": query, "count": len(assets), "results": assets}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find texture/image assets such as albedo, normal, roughness, HDRI, PNG, JPG, TGA, EXR.")
def unity_find_texture_assets(query: str = "texture", max_results: int = 50) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        assets = _search_candidates(query, category="texture", asset_types=["Texture2D", ""], max_results=max_results)
        assets = [a for a in assets if a["extension"] in _TEXTURE_EXTENSIONS or a.get("main_type") == "Texture2D"][:max_results]
        return {"ok": True, "action_performed": "search_only", "placed_in_scene": False, "query": query, "count": len(assets), "results": assets}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find audio assets such as music, ambience, SFX, WAV, OGG, MP3.")
def unity_find_audio_assets(query: str = "audio", max_results: int = 50) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        assets = _search_candidates(query, category="audio", asset_types=["AudioClip", ""], max_results=max_results)
        assets = [a for a in assets if a["extension"] in _AUDIO_EXTENSIONS or a.get("main_type") == "AudioClip"][:max_results]
        return {"ok": True, "action_performed": "search_only", "placed_in_scene": False, "query": query, "count": len(assets), "results": assets}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Instantiate the best matching real project asset for a natural-language query. Prefer this over creating a primitive for trees, rocks, props, buildings, and characters.")
def unity_instantiate_best_asset(
    query: str,
    name: str = "",
    category: str = "",
    position_x: float = 0.0,
    position_y: float = 0.0,
    position_z: float = 0.0,
    scale: float = 1.0,
) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        candidates = _search_candidates(query, category=category, max_results=20, instantiable_only=True)
        if not candidates:
            return {"ok": False, "error": f"No instantiable asset found for '{query}'", "query": query}
        best = candidates[0]
        item = {
            "path": best["path"],
            "name": name or best["name"],
            "position": {"x": position_x, "y": position_y, "z": position_z},
            "scale": {"x": scale, "y": scale, "z": scale},
        }
        result = _instantiate_items([item], max_items=1)
        return {"ok": bool(result.get("ok", True)), "selected": best, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Scatter real project assets matching a query across a rectangular area. Uses batch instantiate to avoid Unity RPC timeouts.")
def unity_scatter_best_assets(
    query: str,
    count: int = 20,
    category: str = "",
    center_x: float = 0.0,
    center_y: float = 0.0,
    center_z: float = 0.0,
    range_x: float = 30.0,
    range_z: float = 30.0,
    min_scale: float = 0.8,
    max_scale: float = 1.4,
    seed: int = 0,
) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        candidates = _search_candidates(query, category=category, max_results=12, instantiable_only=True)
        if not candidates:
            return {"ok": False, "error": f"No instantiable assets found for '{query}'", "query": query}
        rng = random.Random(seed or None)
        items = []
        for i in range(max(1, min(count, 200))):
            asset = candidates[i % len(candidates)]
            s = rng.uniform(min_scale, max_scale)
            items.append(
                {
                    "path": asset["path"],
                    "name": f"{asset['name']}_{i + 1:02d}",
                    "position": {
                        "x": center_x + rng.uniform(-range_x * 0.5, range_x * 0.5),
                        "y": center_y,
                        "z": center_z + rng.uniform(-range_z * 0.5, range_z * 0.5),
                    },
                    "rotation": {"x": 0.0, "y": rng.uniform(0.0, 360.0), "z": 0.0},
                    "scale": {"x": s, "y": s, "z": s},
                }
            )
        result = _instantiate_items(items, max_items=200)
        return {"ok": bool(result.get("ok", True)), "query": query, "candidate_count": len(candidates), "selected_assets": candidates, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Place real project assets matching a query in a straight line.")
def unity_create_asset_line(query: str, count: int = 5, spacing: float = 3.0, start_x: float = 0.0, start_y: float = 0.0, start_z: float = 0.0) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        candidates = _search_candidates(query, max_results=max(1, min(count, 20)), instantiable_only=True)
        if not candidates:
            return {"ok": False, "error": f"No instantiable assets found for '{query}'"}
        items = []
        for i in range(max(1, min(count, 200))):
            asset = candidates[i % len(candidates)]
            items.append({"path": asset["path"], "name": f"{asset['name']}_Line_{i + 1:02d}", "position": {"x": start_x + i * spacing, "y": start_y, "z": start_z}})
        result = _instantiate_items(items)
        return {"ok": bool(result.get("ok", True)), "selected_assets": candidates, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Place real project assets matching a query in a grid layout.")
def unity_create_asset_grid(
    query: str,
    rows: int = 3,
    columns: int = 3,
    spacing_x: float = 4.0,
    spacing_z: float = 4.0,
    start_x: float = 0.0,
    start_y: float = 0.0,
    start_z: float = 0.0,
) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        total = max(1, min(rows * columns, 200))
        candidates = _search_candidates(query, max_results=min(total, 20), instantiable_only=True)
        if not candidates:
            return {"ok": False, "error": f"No instantiable assets found for '{query}'"}
        items = []
        for index in range(total):
            row = index // max(1, columns)
            col = index % max(1, columns)
            asset = candidates[index % len(candidates)]
            items.append(
                {
                    "path": asset["path"],
                    "name": f"{asset['name']}_Grid_{index + 1:02d}",
                    "position": {"x": start_x + col * spacing_x, "y": start_y, "z": start_z + row * spacing_z},
                }
            )
        result = _instantiate_items(items)
        return {"ok": bool(result.get("ok", True)), "selected_assets": candidates, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Place real project assets matching a query around a ring/circle.")
def unity_place_asset_ring(query: str, count: int = 12, radius: float = 8.0, center_x: float = 0.0, center_y: float = 0.0, center_z: float = 0.0) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        candidates = _search_candidates(query, max_results=max(1, min(count, 20)), instantiable_only=True)
        if not candidates:
            return {"ok": False, "error": f"No instantiable assets found for '{query}'"}
        items = []
        for i in range(max(1, min(count, 200))):
            angle = (math.tau * i) / max(1, count)
            asset = candidates[i % len(candidates)]
            items.append(
                {
                    "path": asset["path"],
                    "name": f"{asset['name']}_Ring_{i + 1:02d}",
                    "position": {"x": center_x + math.cos(angle) * radius, "y": center_y, "z": center_z + math.sin(angle) * radius},
                    "rotation": {"x": 0.0, "y": math.degrees(-angle) + 90.0, "z": 0.0},
                }
            )
        result = _instantiate_items(items)
        return {"ok": bool(result.get("ok", True)), "selected_assets": candidates, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a small forest using real tree assets from the project.")
def unity_create_forest_from_assets(count: int = 35, center_x: float = 0.0, center_z: float = 0.0, width: float = 50.0, depth: float = 50.0, seed: int = 0) -> dict:
    return unity_scatter_best_assets(
        query="realistic tree forest pine fir",
        count=count,
        category="tree",
        center_x=center_x,
        center_z=center_z,
        range_x=width,
        range_z=depth,
        min_scale=0.75,
        max_scale=1.8,
        seed=seed,
    )


@tool(description="Create a natural rock field using real rock/boulder assets from the project.")
def unity_create_rock_field_from_assets(count: int = 20, center_x: float = 0.0, center_z: float = 0.0, width: float = 35.0, depth: float = 35.0, seed: int = 0) -> dict:
    return unity_scatter_best_assets(
        query="realistic rock boulder cliff stone",
        count=count,
        category="rock",
        center_x=center_x,
        center_z=center_z,
        range_x=width,
        range_z=depth,
        min_scale=0.6,
        max_scale=1.5,
        seed=seed,
    )


@tool(description="Create a prop cluster using real prop assets from the project.")
def unity_create_prop_cluster_from_assets(query: str = "barrel crate chest lantern", count: int = 12, center_x: float = 0.0, center_z: float = 0.0, radius: float = 8.0, seed: int = 0) -> dict:
    return unity_scatter_best_assets(
        query=query,
        count=count,
        category="prop",
        center_x=center_x,
        center_z=center_z,
        range_x=radius * 2.0,
        range_z=radius * 2.0,
        min_scale=0.85,
        max_scale=1.2,
        seed=seed,
    )


@tool(description="Inspect asset folder distribution for a query, useful for discovering where real project assets live.")
def unity_inspect_asset_folders(query: str = "tree rock prop character", max_results: int = 200) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        assets = _search_candidates(query, max_results=max_results)
        folders: dict[str, int] = {}
        for asset in assets:
            folders[asset["folder"]] = folders.get(asset["folder"], 0) + 1
        ranked = [{"folder": folder, "count": count} for folder, count in sorted(folders.items(), key=lambda kv: (-kv[1], kv[0]))]
        return {
            "ok": True,
            "action_performed": "search_only",
            "placed_in_scene": False,
            "query": query,
            "folder_count": len(ranked),
            "folders": ranked,
            "sample_assets": assets[:20],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
