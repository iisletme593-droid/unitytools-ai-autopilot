"""Deterministic GameStudio action planning.

The chat server should stay engine/editor focused, not game-template focused.
This module keeps template-specific shortcuts in one auditable place so local
models can be fast without turning every prompt into Arena Survivor behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re
import unicodedata


@dataclass(frozen=True)
class TemplateInfo:
    key: str
    display_name: str
    engine: str
    purpose: str
    trigger_terms: tuple[str, ...]
    safe_prefix: str
    default_level: str
    safety_notes: tuple[str, ...]


ARENA_SURVIVOR = TemplateInfo(
    key="arena_survivor",
    display_name="Arena Survivor",
    engine="unreal",
    purpose="Small survival-combat slice used to verify GameStudio tools end-to-end.",
    trigger_terms=("arena", "survivor", "asv", "wave", "dalga"),
    safe_prefix="ASV001",
    default_level="/Game/UnrealTools/Maps/UT_ArenaSurvivor_V001",
    safety_notes=(
        "Only mutate actors with the ASV001 prefix or UnrealToolsRuntime classes.",
        "Runtime reset removes transient enemies and resets counters, not project assets.",
        "Do not run this template unless the prompt explicitly mentions Arena/ASV/wave/survivor.",
    ),
)


TEMPLATES: tuple[TemplateInfo, ...] = (ARENA_SURVIVOR,)


ACTION_TERMS = (
    "uygula",
    "yap",
    "olustur",
    "spawn",
    "uret",
    "ekle",
    "test",
    "dene",
    "clear",
    "temizle",
    "ilerlet",
    "collect",
    "topla",
    "defeat",
    "oldur",
    "prototip",
    "prototype",
    "kur",
    "ayarla",
    "setup",
    "hazirla",
    "boya",
    "renklendir",
    "renk",
    "palette",
    "palet",
    "material",
    "materyal",
    "optimize",
    "optimizasyon",
    "planla",
    "analiz",
    "sec",
    "ac",
    "open",
    "select",
    "load",
    "yerlestir",
    "dagit",
    "serp",
    "scatter",
    "place",
    "populate",
    "kaldir",
    "sil",
    "delete",
    "remove",
    "hazir",
    "hazirla",
    "calis",
    "work",
    "dogrula",
    "verify",
)

READ_ONLY_TERMS = (
    "tara",
    "scan",
    "liste",
    "list",
    "bul",
    "find",
    "status",
    "durum",
    "asset",
    "actor",
    "proje",
    "project",
    "koyduk",
    "placed",
    "selected",
    "secili",
    "secilmis",
)


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "key": item.key,
            "display_name": item.display_name,
            "engine": item.engine,
            "purpose": item.purpose,
            "trigger_terms": list(item.trigger_terms),
            "safe_prefix": item.safe_prefix,
            "default_level": item.default_level,
            "safety_notes": list(item.safety_notes),
        }
        for item in TEMPLATES
    ]


def plan_unreal_fast_action(text: str) -> dict[str, Any]:
    """Return a conservative local action plan for obvious Unreal commands.

    Empty steps means the request should go to the LLM/tool orchestrator.
    """
    lower = _normalize_prompt(text)
    if not lower.strip():
        return {"ok": True, "template": None, "steps": [], "reason": "empty"}

    if _is_workbench_status_prompt(lower):
        return {
            "ok": True,
            "template": None,
            "display_name": "Unreal Scene Workbench Status",
            "steps": [
                {
                    "tool": "unreal_get_scene_workbench_status",
                    "kwargs": {"max_actors": 800, "top_n": 8, "target_triangle_budget": 5000000},
                    "write": False,
                },
            ],
            "reason": "scene workbench status requested",
            "safety_notes": ["Read-only: aggregates active scene, selected actors, generated actors, and performance risk."],
        }

    if _is_level_list_prompt(lower):
        return {
            "ok": True,
            "template": None,
            "display_name": "Unreal Level Selection",
            "steps": [
                {"tool": "unreal_get_project_info", "kwargs": {}, "write": False},
                {"tool": "unreal_list_levels", "kwargs": {"query": "", "max_results": 120}, "write": False},
            ],
            "reason": "level/map list requested",
            "safety_notes": ["Read-only: lists available level assets and active map info."],
        }

    if _is_selected_actor_prompt(lower):
        return {
            "ok": True,
            "template": None,
            "display_name": "Unreal Selection Context",
            "steps": [
                {"tool": "unreal_list_selected_actors", "kwargs": {"max_results": 100}, "write": False},
            ],
            "reason": "selected actor context requested",
            "safety_notes": ["Read-only: inspects only currently selected level actors."],
        }

    if _is_read_only_prompt(lower) and not _is_ai_placed_prompt(lower):
        steps = [
            {"tool": "unreal_get_project_info", "kwargs": {}, "write": False},
            {"tool": "unreal_scan_project", "kwargs": {"max_assets": 1500, "max_actors": 500}, "write": False},
        ]
        if any(term in lower for term in ("actor", "actors", "sahne", "level", "liste", "list")):
            steps.append({"tool": "unreal_list_level_actors", "kwargs": {"max_results": 300}, "write": False})
        return {
            "ok": True,
            "template": None,
            "display_name": "Unreal Project Inspection",
            "steps": steps,
            "reason": "generic read-only inspection",
            "safety_notes": ["Read-only fast path: does not mutate assets, actors, packages, or levels."],
        }

    if not any(term in lower for term in ACTION_TERMS):
        return {"ok": True, "template": None, "steps": [], "reason": "no action verb"}

    template = _match_template(lower)
    if template is None:
        generic = _plan_generic_unreal(lower, text or "")
        if generic["steps"]:
            return generic
        return {
            "ok": True,
            "template": None,
            "steps": [],
            "reason": "no explicit template trigger",
            "available_templates": [item.key for item in TEMPLATES],
        }

    if template.key == "arena_survivor":
        return _plan_arena_survivor(lower, template)

    return {"ok": True, "template": template.key, "steps": [], "reason": "template has no planner"}


def plan_unity_fast_action(text: str) -> dict[str, Any]:
    """Deterministic Turkish/English intent -> Unity tool-step planner.

    Mirrors plan_unreal_fast_action for the PRIMARY engine: maps common imperative
    prompts to the existing unity_* tools so the studio loop can run on Unity
    without an LLM round-trip. Returns ordered steps, each with a ``write`` flag,
    plus ``safety_notes`` for destructive ones. Compound prompts (e.g. "snapshot al
    sonra orman kur") emit multiple steps.
    """
    lower = _normalize_prompt(text)
    if not lower.strip():
        return {"ok": True, "engine": "unity", "steps": [], "reason": "empty"}

    tokens = [t.strip(".,;:!?()[]{}\"'") for t in lower.split()]

    def has(*keywords: str) -> bool:
        # Multi-word keywords match as a substring; single words match a token
        # PREFIX (Turkish suffixes attach to the end, so "kayalari" matches "kaya"
        # but "nasilsin" does NOT match "sil"). Avoids anywhere-substring false hits.
        for kw in keywords:
            if " " in kw:
                if kw in lower:
                    return True
            elif any(tok.startswith(kw) for tok in tokens):
                return True
        return False

    steps: list[dict[str, Any]] = []
    safety_notes: list[str] = []
    build_verb = has("kur", "olustur", "yap", "build", "create", "generate", "uret", "insa")

    def detect_game_type() -> str:
        if has("dodge", "kacma", "kacis"):
            return "dodge"
        if has("survival", "survive", "sag kalma", "hayatta kal"):
            return "survival"
        if has("platformer", "platform", "zipla oyunu", "ziplama oyunu", "jump game"):
            return "platformer"
        if has("chase", "kovalamaca", "takip oyunu", "takip"):
            return "chase"
        return "collectathon"

    # Assess/QA intent must beat build-game: "dodge oyununu degerlendir" contains
    # both "dodge" and "degerlendir" — the user wants an analysis, not a build. It
    # also requires a game context ("oyun"/"game") so scene-level "analiz"/"qa"
    # prompts still fall through to the visual-QA / profiling branches below.
    assess_verb = (has("degerlendir", "analiz", "assess", "readiness")
                   or has("oynanabilir mi", "oyun qa", "qa yap", "is the game playable", "hazir mi"))
    if assess_verb and has("oyun", "game"):
        gt = detect_game_type()
        return {
            "ok": True,
            "engine": "unity",
            "steps": [{
                "tool": "unity_assess_game",
                "kwargs": {"game_type": gt, "collectible_count": _infer_count(lower, 5)},
                "write": False,
                "note": f"assess the {gt} game (pure analysis: counts + playable verdict, no scene changes, no bridge)",
            }],
            "safety_notes": ["read-only QA; no scene changes"],
            "reason": f"assess-game intent -> {gt}",
        }

    # Build-a-game intent takes priority so "oyun" doesn't fall into scene branches.
    wants_game = (
        has("collectathon", "toplama oyunu", "oyun iskeleti", "dodge", "kacma oyunu", "kacis oyunu",
            "survival", "survive", "sag kalma", "hayatta kal",
            "platformer", "platform oyunu", "zipla oyunu", "ziplama oyunu", "jump game",
            "chase", "kovalamaca", "takip oyunu", "chase game")
        or ((has("oyun", "game") and build_verb))
    )
    if wants_game:
        game_type = detect_game_type()
        return {
            "ok": True,
            "engine": "unity",
            "steps": [{
                "tool": "unity_build_simple_game",
                "kwargs": {"game_type": game_type, "collectible_count": _infer_count(lower, 5), "execute": False},
                "write": False,
                "note": f"plan a {game_type} game (execute=False; real build needs execute=True + a Unity recompile)",
            }],
            "safety_notes": ["game-build plan only (execute=False); building for real triggers Unity recompiles"],
            "reason": f"build-game intent -> {game_type}",
        }

    # Decorative "living scene" intent (juice, not a game) -> animate a group.
    if has("yasayan sahne", "sahneyi canlandir", "canli sahne", "sahneye hayat",
           "living scene", "animate the scene", "animate decor", "dekoratif animasyon"):
        return {
            "ok": True,
            "engine": "unity",
            "steps": [{
                "tool": "unity_animate_group",
                "kwargs": {"count": _infer_count(lower, 8), "execute": False},
                "write": False,
                "note": "plan a living/animated decor scene (execute=False; building imports scripts -> a Unity recompile)",
            }],
            "safety_notes": ["decor plan only (execute=False); building for real triggers a Unity recompile"],
            "reason": "animate-decor intent -> unity_animate_group",
        }

    if has("snapshot", "yedek", "backup", "geri yukle", "restore point"):
        steps.append({"tool": "unity_create_scene_snapshot", "kwargs": {"label": "fast_action"},
                      "write": True, "note": "save a restore point before edits"})

    if has("orman", "forest") and build_verb:
        steps.append({"tool": "unity_create_optimized_forest_scene",
                      "kwargs": {"tree_count": _infer_count(lower, 80), "clear_scene": True},
                      "write": True, "note": "clears the scene then generates an optimized forest"})
        safety_notes.append("forest generation clears the active scene (orchestrator auto-snapshots first)")
    elif has("blockout", "kompoze", "sahne kur", "sahne olustur", "build scene", "compose scene"):
        steps.append({"tool": "unity_blockout_scene", "kwargs": {},
                      "write": True, "note": "floor + props + lighting + framed camera in one shot"})

    if has("yerlestir", "place", "scatter", "dagit", "serp") or (
        has("kup", "kure", "cube", "sphere", "silindir", "cylinder", "primitive") and build_verb
    ):
        pattern = ("circle" if has("cember", "circle", "ring") else
                   "grid" if has("izgara", "grid") else
                   "line" if has("cizgi", "line", "sira") else "scatter")
        prim = ("Sphere" if has("kure", "sphere") else
                "Cylinder" if has("silindir", "cylinder") else "Cube")
        count = _infer_count(lower, 12)
        steps.append({"tool": "unity_place_primitives",
                      "kwargs": {"count": count, "pattern": pattern, "type": prim},
                      "write": True, "note": f"place {count} {prim} in a {pattern}"})

    if has("isik", "light", "aydinlat", "studio lighting", "3 nokta"):
        steps.append({"tool": "unity_setup_studio_lighting", "kwargs": {},
                      "write": True, "note": "3-point key/fill/rim rig"})

    if has("renklendir", "boya", "palette", "palet", "recolor", "tint"):
        steps.append({"tool": "unity_apply_material_palette", "kwargs": {"palette": _infer_palette(lower)},
                      "write": True, "note": "apply a themed material palette"})

    if has("bul", "find", "search", "nerede") and not has("sil", "delete", "kaldir", "remove"):
        steps.append({"tool": "unity_find_scene_objects_semantic",
                      "kwargs": {"query": _infer_placement_category(lower)},
                      "write": False, "note": "semantic scene search (read-only)"})

    if has("sil", "delete", "kaldir", "remove", "temizle"):
        steps.append({"tool": "unity_delete_scene_objects_semantic",
                      "kwargs": {"query": _infer_placement_category(lower)},
                      "write": True, "note": "semantic delete"})
        safety_notes.append("deletion is destructive (orchestrator auto-snapshots first)")

    if has("kalite", "quality", "qa", "duzelt", "fix", "onar", "iyilestir"):
        if has("duzelt", "fix", "onar", "iyilestir", "auto"):
            steps.append({"tool": "unity_quality_pass", "kwargs": {"auto_fix": True},
                          "write": True, "note": "visual QA -> auto-fix materials/lighting -> re-check"})
        else:
            steps.append({"tool": "unity_run_visual_qa", "kwargs": {},
                          "write": False, "note": "visual QA pass (read-only)"})

    if has("performans", "performance", "profil", "profile", "fps"):
        steps.append({"tool": "unity_profile_scene_performance", "kwargs": {},
                      "write": False, "note": "render-cost profile (read-only)"})

    if has("katalog", "catalog", "listele", "envanter", "ne var"):
        steps.append({"tool": "unity_get_scene_catalog", "kwargs": {},
                      "write": False, "note": "scene catalog (read-only)"})

    if has("deney", "experiment", "olc", "measure", "ogren", "learn"):
        steps.append({"tool": "gamestudio_record_scene_experiment", "kwargs": {"game_title": "scene"},
                      "write": True, "note": "measure (QA+profile) and record a learning experiment"})

    if not steps:
        return {"ok": True, "engine": "unity", "steps": [], "reason": "no action verb"}
    return {
        "ok": True,
        "engine": "unity",
        "steps": steps,
        "safety_notes": safety_notes,
        "reason": f"matched {len(steps)} unity action(s)",
    }


def run_unity_fast_action(text, tool_resolver, emit=None):
    """Execute a deterministic Unity fast-action plan against the live tools.

    The LLM-free counterpart of chat_server's Unreal fast-path. ``tool_resolver``
    maps a tool name to a callable (or None if not registered) — passing the
    registry keeps this drift-free (no hand-maintained tool_map). ``emit`` is an
    optional callback for streaming events ({"type": "tool_call"/"tool_result"}).

    Returns None when the prompt has no fast-action plan (caller should fall
    through to the LLM); otherwise a summary dict with each executed step.
    """
    plan = plan_unity_fast_action(text)
    steps = plan.get("steps", []) if isinstance(plan, dict) else []
    if not steps:
        return None

    def _emit(ev):
        if emit:
            try:
                emit(ev)
            except Exception:
                pass

    _emit({"type": "thinking"})
    executed: list[dict[str, Any]] = []
    for step in steps:
        name = str(step.get("tool", ""))
        kwargs = step.get("kwargs", {})
        if not isinstance(kwargs, dict):
            kwargs = {}
        fn = tool_resolver(name)
        if fn is None:
            executed.append({"tool": name, "ok": False, "skipped": True, "error": "tool not registered"})
            continue
        _emit({"type": "tool_call", "tool": name, "input": {"mode": "local_unity_fast_path", **kwargs}})
        try:
            result = fn(**kwargs)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        ok = bool(result.get("ok", False)) if isinstance(result, dict) else True
        _emit({"type": "tool_result", "tool": name, "ok": ok,
               "error": result.get("error") if isinstance(result, dict) else None})
        executed.append({"tool": name, "ok": ok, "result": result})

    ran = [e for e in executed if not e.get("skipped")]
    ok_count = sum(1 for e in ran if e.get("ok"))
    return {
        "ok": bool(ran) and ok_count == len(ran),
        "engine": "unity",
        "executed": executed,
        "ran_count": len(ran),
        "ok_count": ok_count,
        "safety_notes": plan.get("safety_notes", []),
        "summary": f"Unity fast-action: {ok_count}/{len(ran)} step(s) ok",
    }


def preflight_prompt(text: str, engine: str = "unreal") -> dict[str, Any]:
    """Classify a prompt before an agent chooses tools.

    This does not execute anything. It is a cheap safety pass for local models
    and UI panels. Supports both Unreal and Unity engines.
    """
    lower = _normalize_prompt(text)
    engine = (engine or "unreal").lower()
    if engine == "unity":
        plan = plan_unity_fast_action(text)
        read_only_tools = ["unity_get_scene_catalog", "unity_list_scene_objects", "unity_get_editor_state"]
    elif engine == "unreal":
        plan = plan_unreal_fast_action(text)
        read_only_tools = ["unreal_get_project_info", "unreal_scan_project", "unreal_list_level_actors"]
    else:
        return {
            "ok": True,
            "engine": engine,
            "route": "orchestrator",
            "risk": "unknown",
            "reason": "preflight has deterministic rules for Unreal and Unity only",
            "recommended_tools": [],
        }

    steps = plan.get("steps", [])
    if steps:
        risk = "write" if any(step.get("write") for step in steps) else "read_only"
        return {
            "ok": True,
            "engine": engine,
            "route": "fast_action",
            "risk": risk,
            "template": plan.get("template"),
            "reason": plan.get("reason"),
            "recommended_tools": [step.get("tool") for step in steps],
            "safety_notes": plan.get("safety_notes", []),
        }

    if _is_read_only_prompt(lower):
        return {
            "ok": True,
            "engine": engine,
            "route": "fast_action",
            "risk": "read_only",
            "template": None,
            "reason": "generic read-only inspection",
            "recommended_tools": read_only_tools,
        }

    destructive_terms = ("sil", "delete", "remove", "wipe", "temizle", "destroy", "kaldir")
    risk = "destructive_candidate" if any(term in lower for term in destructive_terms) else "normal"
    return {
        "ok": True,
        "engine": engine,
        "route": "orchestrator",
        "risk": risk,
        "template": None,
        "reason": plan.get("reason", "no deterministic route"),
        "recommended_tools": [],
    }


def _normalize_prompt(text: str | None) -> str:
    """Fold Turkish/accented input into stable match text.

    Local models, editor panels, and Windows terminals can disagree on text
    encoding. The planner should not miss safe actions because ``isik`` arrived
    as Turkish dotted/dotless characters or with decomposed accent marks.
    """
    raw = (text or "").lower()
    translation = {
        ord("\u0131"): "i",
        ord("\u0130"): "i",
        ord("\u015f"): "s",
        ord("\u015e"): "s",
        ord("\u011f"): "g",
        ord("\u011e"): "g",
        ord("\u00fc"): "u",
        ord("\u00dc"): "u",
        ord("\u00f6"): "o",
        ord("\u00d6"): "o",
        ord("\u00e7"): "c",
        ord("\u00c7"): "c",
    }
    translated = raw.translate(translation)
    normalized = unicodedata.normalize("NFKD", translated)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _is_read_only_prompt(lower: str) -> bool:
    if not any(term in lower for term in READ_ONLY_TERMS):
        return False
    write_terms = (
        "olustur",
        "spawn",
        "ekle",
        "sil",
        "delete",
        "remove",
        "reset",
        "sifirla",
        "uygula",
        "ayarla",
        "kur",
        "import",
        "boya",
        "renklendir",
        "renk",
        "paint",
        "open",
        "select",
        "load",
        "planla",
        "optimize",
        "optimizasyon",
        "lod",
        "decimation",
        "yerlestir",
        "dagit",
        "scatter",
        "place",
        "populate",
    )
    return not any(term in lower for term in write_terms)


def _is_ai_placed_prompt(lower: str) -> bool:
    terms = ("ut_placed", "ai koydu", "ai yerlestirdi", "son koyduk", "koyduklarini", "placed actors", "placed assets", "ai placed")
    return any(term in lower for term in terms)


def _is_level_list_prompt(lower: str) -> bool:
    level_terms = ("sahne", "sahneler", "level", "levels", "map", "maps", "harita", "haritalar")
    list_terms = ("liste", "list", "goster", "göster", "say", "hangi", "available", "mevcut")
    asset_terms = ("asset", "actor", "object", "obje", "mesh", "prefab", "agac", "tree", "rock", "kaya", "tas")
    if any(term in lower for term in asset_terms):
        return False
    return any(term in lower for term in level_terms) and any(term in lower for term in list_terms) and not _has_open_level_intent(lower)


def _is_selected_actor_prompt(lower: str) -> bool:
    return any(term in lower for term in ("secili", "secilmis", "selected", "selection")) and any(
        term in lower for term in ("oku", "liste", "list", "goster", "tara", "inspect", "context", "ozet")
    )


def _is_workbench_status_prompt(lower: str) -> bool:
    scene_terms = ("sahne", "scene", "level", "map", "workbench", "calisma alani", "durum")
    status_terms = ("durum", "status", "ozet", "summary", "saglik", "health", "risk", "kontrol", "check")
    return any(term in lower for term in scene_terms) and any(term in lower for term in status_terms)


def _match_template(lower: str) -> TemplateInfo | None:
    for template in TEMPLATES:
        if any(term in lower for term in template.trigger_terms):
            return template
    return None


def _plan_generic_unreal(lower: str, raw_text: str = "") -> dict[str, Any]:
    """Plan safe non-template Unreal actions.

    These actions are intentionally small and prefix-safe. Anything broad,
    destructive, or asset-heavy should remain with the orchestrator.
    """
    steps: list[dict[str, Any]] = []

    if any(term in lower for term in ("secili", "secilmis", "selected", "selection")) and any(term in lower for term in ("oku", "liste", "list", "goster", "tara", "inspect", "context", "ozet")):
        steps.append(
            {
                "tool": "unreal_list_selected_actors",
                "kwargs": {"max_results": 100},
                "write": False,
            }
        )

    if any(term in lower for term in ("aktif sahnede calis", "bu sahnede calis", "current level", "current map", "active level", "active scene")) and any(term in lower for term in ("calis", "work", "dogrula", "verify", "remember", "hafiza")):
        steps.append(
            {
                "tool": "unreal_remember_active_level",
                "kwargs": {},
                "write": False,
            }
        )

    level_path = _extract_unreal_level_path(raw_text or lower)
    if level_path and _has_open_level_intent(lower):
        steps.append(
            {
                "tool": "unreal_open_level",
                "kwargs": {"level_path": level_path},
                "write": False,
            }
        )
    elif _has_open_level_intent(lower) and any(term in lower for term in ("sahne", "level", "map", "harita")):
        level_name = _extract_unreal_level_name(raw_text or lower)
        if level_name:
            steps.append(
                {
                    "tool": "unreal_open_level_by_name",
                    "kwargs": {"name": level_name, "remember": True},
                    "write": False,
                }
            )

    ai_placed_terms = ("ut_placed", "ai koydu", "ai yerlestirdi", "son koyduk", "koyduklarini", "placed actors", "placed assets", "ai placed")
    cleanup_terms = ("temizle", "kaldir", "sil", "delete", "remove", "cleanup", "clear")
    if any(term in lower for term in ai_placed_terms):
        if any(term in lower for term in cleanup_terms):
            dry_run = any(term in lower for term in ("onizle", "önizle", "dry run", "dry-run", "preview", "silmeden", "once goster", "önce göster"))
            steps.append(
                {
                    "tool": "unreal_cleanup_ai_placed_actors",
                    "kwargs": {
                        "prefix": "UT_Placed",
                        "category": _infer_actor_category(lower),
                        "dry_run": dry_run,
                        "save": False,
                    },
                    "write": not dry_run,
                }
            )
        elif any(term in lower for term in ("liste", "list", "say", "goster", "show", "bul")):
            steps.append(
                {
                    "tool": "unreal_list_ai_placed_actors",
                    "kwargs": {"prefix": "UT_Placed", "max_results": 500},
                    "write": False,
                }
            )

    ground_terms = ("zemin", "terrain", "landscape", "ground", "arazi", "open world", "acik dunya")
    ground_action_terms = ("hazirla", "hazir", "olustur", "kur", "ayarla", "prepare", "create", "setup")
    if any(term in lower for term in ground_terms) and any(term in lower for term in ground_action_terms):
        style = _infer_palette(lower)
        scatter_count = 0
        wants_scatter = any(term in lower for term in ("dagit", "yerlestir", "serp", "scatter", "place", "populate"))
        if wants_scatter and any(term in lower for term in ("agac", "tree", "forest", "orman", "kaya", "rock", "tas", "stone", "cali", "bush")):
            scatter_count = _infer_count(lower, default=16)
        steps.append(
            {
                "tool": "unreal_prepare_open_world_ground",
                "kwargs": {
                    "style": style,
                    "size": 12000,
                    "scatter_count": scatter_count,
                    "save": False,
                },
                "write": True,
            }
        )

    lighting_terms = ("isik", "light", "lighting", "fog", "sis", "kamera", "camera")
    has_ground_step = any(step.get("tool") == "unreal_prepare_open_world_ground" for step in steps)
    if not has_ground_step and any(term in lower for term in lighting_terms) and any(term in lower for term in ("kur", "setup", "ayarla", "ekle", "uygula")):
        style = "night" if any(term in lower for term in ("night", "gece", "dark", "karanlik")) else "premium"
        steps.append(
            {
                "tool": "unreal_setup_studio_lighting",
                "kwargs": {"style": style},
                "write": True,
            }
        )

    lod_terms = ("lod", "decimation", "triangle", "triangles", "poly", "polygon", "poligon", "optimize", "optimizasyon", "performans", "kasiyor", "agir")
    if any(term in lower for term in lod_terms) and any(term in lower for term in ("plan", "planla", "analiz", "tara", "optimize", "bak", "bul")):
        steps.append(
            {
                "tool": "unreal_plan_scene_lod_decimation",
                "kwargs": {"max_actors": 750, "top_n": 30, "target_triangle_budget": 5000000},
                "write": False,
            }
        )

    placement_terms = ("yerlestir", "dagit", "serp", "scatter", "place", "populate")
    placement_categories = ("agac", "tree", "pine", "forest", "orman", "kaya", "tas", "rock", "stone", "boulder")
    if not has_ground_step and any(term in lower for term in placement_terms) and any(term in lower for term in placement_categories):
        category = _infer_placement_category(lower)
        count = _infer_count(lower, default=24 if category in ("forest", "tree") else 12)
        radius = 1600 if category in ("forest", "tree") else 1200
        steps.append(
            {
                "tool": "unreal_place_semantic_assets",
                "kwargs": {
                    "query": "",
                    "category": category,
                    "count": count,
                    "radius": radius,
                    "prefix": "UT_Placed",
                    "palette": _infer_palette(lower) if any(term in lower for term in ("palet", "palette", "renk", "material", "forest", "dark", "desert")) else "",
                    "align_to_ground": True,
                    "ground_offset": 8.0,
                    "save": False,
                },
                "write": True,
            }
        )

    palette_terms = ("boya", "renklendir", "renk", "palette", "palet", "material", "materyal")
    if not any(step.get("tool") == "unreal_place_semantic_assets" for step in steps) and any(term in lower for term in palette_terms) and any(term in lower for term in ("uygula", "boya", "renklendir", "ayarla", "ver")):
        category = _infer_actor_category(lower)
        palette = _infer_palette(lower)
        steps.append(
            {
                "tool": "unreal_apply_actor_material_palette",
                "kwargs": {
                    "query": "",
                    "category": category,
                    "palette": palette,
                    "max_actors": 300,
                    "save": False,
                },
                "write": True,
            }
        )

    blockout_terms = ("blockout", "greybox", "graybox", "prototip harita", "prototype map", "basit harita")
    if any(term in lower for term in blockout_terms) and any(term in lower for term in ("kur", "olustur", "create", "yap")):
        create_new_level = any(term in lower for term in ("yeni level", "new level", "yeni map", "new map"))
        steps.append(
            {
                "tool": "unreal_create_blockout_map",
                "kwargs": {
                    "theme": "premium_gameplay",
                    "size": 1800,
                    "create_new_level": create_new_level,
                    "level_name": "UT_Blockout_Map",
                    "lighting": "premium",
                    "save": True,
                },
                "write": True,
            }
        )

    primitive_types = {
        "cube": "cube",
        "kup": "cube",
        "sphere": "sphere",
        "kure": "sphere",
        "cylinder": "cylinder",
        "silindir": "cylinder",
        "plane": "plane",
        "zemin": "plane",
    }
    primitive = next((value for key, value in primitive_types.items() if key in lower), None)
    if primitive and any(term in lower for term in ("spawn", "ekle", "olustur", "create")):
        steps.append(
            {
                "tool": "unreal_spawn_basic_actor",
                "kwargs": {
                    "type": primitive,
                    "label": f"UT_Generated_{primitive.title()}",
                    "location": {"x": 0, "y": 0, "z": 120 if primitive != "plane" else 0},
                },
                "write": True,
            }
        )

    return {
        "ok": True,
        "template": None,
        "display_name": "Unreal Safe Scene Action",
        "steps": steps,
        "reason": "generic safe Unreal write action" if steps else "no generic action matched",
        "safety_notes": [
            "Generic writes use UT_* labels/prefixes when creating actors.",
            "No destructive generic actions are executed by this planner.",
            "Broad asset operations remain with the orchestrator and safety checks.",
        ],
    }


def _extract_unreal_level_path(text: str) -> str:
    match = re.search(r"(/game/[a-z0-9_./-]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    path = match.group(1).rstrip(".,;")
    return "/Game/" + path[len("/Game/") :]


def _has_open_level_intent(lower: str) -> bool:
    return bool(re.search(r"\b(ac|open|sec|select|load)\b", lower))


def _extract_unreal_level_name(text: str) -> str:
    raw = (text or "").strip()
    patterns = (
        r"(?P<name>[A-Za-z0-9_./-]{3,})\s+(?:sahnesini|sahneyi|levelini|leveli|mapini|mapi|haritasini|haritayi)\s+(?:ac|aç|open|sec|seç|select|load)",
        r"(?:ac|aç|open|sec|seç|select|load)\s+(?P<name>[A-Za-z0-9_./-]{3,})",
        r"(?P<name>[A-Za-z0-9_./-]{3,})\s+(?:sahne|level|map|harita)\s+(?:ac|aç|open|sec|seç|select|load)",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            name = match.group("name").strip(" .,:;\"'")
            if name.lower() not in {"aktif", "current", "unreal", "project", "proje"}:
                return name
    return ""


def _infer_actor_category(lower: str) -> str:
    if any(term in lower for term in ("agac", "tree", "pine", "forest", "foliage")):
        return "tree"
    if any(term in lower for term in ("kaya", "tas", "rock", "stone", "boulder")):
        return "rock"
    if any(term in lower for term in ("zemin", "terrain", "landscape", "ground", "floor")):
        return "ground"
    if any(term in lower for term in ("karakter", "character", "player", "enemy", "npc")):
        return "character"
    return ""


def _infer_palette(lower: str) -> str:
    if any(term in lower for term in ("dark", "night", "gece", "karanlik", "grim")):
        return "dark"
    if any(term in lower for term in ("desert", "sand", "dry", "kurak", "kuru")):
        return "desert"
    return "forest"


def _infer_placement_category(lower: str) -> str:
    has_tree = any(term in lower for term in ("agac", "tree", "pine"))
    has_rock = any(term in lower for term in ("kaya", "tas", "rock", "stone", "boulder"))
    if any(term in lower for term in ("forest", "orman")) and (has_rock or not has_tree):
        return "forest"
    if has_tree:
        return "tree"
    if has_rock:
        return "rock"
    return "tree"


def _infer_count(lower: str, default: int) -> int:
    match = re.search(r"\b(\d{1,3})\b", lower)
    if not match:
        range_match = re.search(r"\b(\d{1,3})\s*[-/]\s*(\d{1,3})\b", lower)
        if range_match:
            return max(1, min(300, int(range_match.group(1))))
        return default
    return max(1, min(300, int(match.group(1))))


def _plan_arena_survivor(lower: str, template: TemplateInfo) -> dict[str, Any]:
    prefix = template.safe_prefix
    steps: list[dict[str, Any]] = []

    if any(term in lower for term in ("ac", "open", "prototip", "prototype", "devam", "playable")):
        steps.append(
            {
                "tool": "unreal_open_level",
                "kwargs": {"level_path": template.default_level},
                "write": False,
            }
        )

    if any(term in lower for term in ("scaffold", "runtime", "pickup", "overlap", "wave", "enemy", "spawn", "playable", "devam")):
        steps.append(
            {
                "tool": "unreal_apply_arena_survivor_runtime_scaffold",
                "kwargs": {"prefix": prefix, "save": True},
                "write": True,
            }
        )

    if any(term in lower for term in ("reset", "sifirla", "temiz state", "bastan")):
        steps.append(
            {
                "tool": "unreal_reset_arena_survivor_runtime_state",
                "kwargs": {"prefix": prefix, "save": True},
                "write": True,
            }
        )

    if any(term in lower for term in ("player", "pawn", "combat", "oynanabilir", "playable", "kontrol", "w a s d", "wasd")):
        steps.append(
            {
                "tool": "unreal_spawn_arena_survivor_player_pawn",
                "kwargs": {"prefix": prefix, "save": True},
                "write": True,
            }
        )

    if any(term in lower for term in ("enemy", "spawn", "dusman", "wave", "placeholder")):
        steps.append(
            {
                "tool": "unreal_spawn_arena_survivor_placeholder_enemies",
                "kwargs": {"prefix": prefix, "wave_index": 1, "max_enemies": 4, "save": True},
                "write": True,
            }
        )

    if any(term in lower for term in ("pickup", "overlap", "collect", "topla")):
        steps.append(
            {
                "tool": "unreal_simulate_arena_survivor_pickup_collect",
                "kwargs": {"prefix": prefix, "count": 2, "save": True},
                "write": True,
            }
        )

    if any(term in lower for term in ("clear", "defeat", "oldur", "wave iler", "dalga iler", "test wave")):
        steps.append(
            {
                "tool": "unreal_simulate_arena_survivor_wave_clear",
                "kwargs": {"prefix": prefix, "wave_index": 1, "count": 0, "save": True},
                "write": True,
            }
        )

    return {
        "ok": True,
        "template": template.key,
        "display_name": template.display_name,
        "safe_prefix": prefix,
        "steps": steps,
        "reason": "matched explicit template trigger" if steps else "template matched but no safe step matched",
        "safety_notes": list(template.safety_notes),
    }
