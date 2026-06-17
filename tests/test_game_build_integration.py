"""Cycle 99: END-TO-END game-build integration -- the chat->Unity path, proven in-process.

The whole game studio is unit-tested at the PLAN level (execute=False). This file closes the
gap: it drives the REAL execute path (unity_build_simple_game(execute=True) ->
_execute_grouped_behaviour_plan) against a RECORDING fake bridge that speaks the same
contract as the live C# BridgeServer, and asserts the actual bridge call SEQUENCE:

    geometry (create_primitive / set_tag / ...) -> import each UNIQUE script once
    (import_asset) -> poll get_editor_state until compiled -> attach (add_component) per object.

No live Unity needed: the fake bridge records every (method, params) the way the editor's
CommandHandlers would receive them. A companion test (test_bridge_protocol_parity.py) proves
every method emitted here is actually handled by the C# side.
"""
import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_game, group_execution_plan, BLUEPRINTS


class RecordingBridge:
    """A fake UnityBridge that records calls and answers like the live editor would:
    get_editor_state -> not compiling (so the build does not block), create_primitive ->
    echoes the name. Everything else -> {ok: True}. Stands in for the C# BridgeServer."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if method == "get_editor_state":
            return {"is_compiling": False}      # so wait_until_compiled returns at once
        if method == "create_primitive":
            return {"name": (params or {}).get("name", "obj")}
        return {"ok": True}

    def methods(self):
        return [m for m, _ in self.calls]

    def count(self, method):
        return sum(1 for m, _ in self.calls if m == method)


@pytest.fixture
def bridge(monkeypatch):
    rb = RecordingBridge()
    monkeypatch.setattr(ut, "_UNITY", rb)
    return rb


# --- the execute path is plan-only until you opt in ------------------------

def test_execute_false_is_plan_only_and_never_touches_the_bridge(bridge):
    out = ut.unity_build_simple_game(execute=False, game_type="collectathon")
    assert out["ok"] is True and out.get("dry_run") is True
    assert bridge.calls == []                    # not a single bridge call without execute=True


def test_no_bridge_fails_safe(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    out = ut.unity_build_simple_game(execute=True, game_type="collectathon")
    assert out["ok"] is False and "not initialized" in out["error"].lower()


# --- the real build sequence -----------------------------------------------

def test_collectathon_build_emits_the_right_bridge_sequence(bridge):
    out = ut.unity_build_simple_game(execute=True, game_type="collectathon", collectible_count=5)
    assert out["ok"] is True and out["executed"] is True

    plan = plan_game("collectathon", 5)
    grouped = group_execution_plan(plan["steps"])
    n_unique = len(grouped["script_behaviours"])
    n_attach = len(grouped["attachments"])

    # geometry created objects, the player got tagged
    assert bridge.count("create_primitive") >= 1
    assert ("set_tag", {"name": "Player", "tag": "Player"}) in bridge.calls
    # each UNIQUE behaviour script imported exactly once (not once per object)
    assert bridge.count("import_asset") == n_unique
    # the single recompile was awaited
    assert "get_editor_state" in bridge.methods()
    # one component attached per (object, behaviour) pair
    assert bridge.count("add_component") == n_attach
    # ordering: all imports happen before the first attach (geometry/import/wait/attach phases)
    methods = bridge.methods()
    last_import = max(i for i, m in enumerate(methods) if m == "import_asset")
    first_attach = min(i for i, m in enumerate(methods) if m == "add_component")
    assert last_import < first_attach


def test_unique_scripts_imported_once_even_with_many_objects(bridge):
    # 12 collectibles share ONE collectible script -> still a single import for it
    ut.unity_build_simple_game(execute=True, game_type="collectathon", collectible_count=12)
    grouped = group_execution_plan(plan_game("collectathon", 12)["steps"])
    assert bridge.count("import_asset") == len(grouped["script_behaviours"])
    # but 12 collectibles each get their own component attachment
    assert bridge.count("add_component") == len(grouped["attachments"])


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_every_game_type_builds_through_the_bridge(game_type, bridge):
    out = ut.unity_build_simple_game(execute=True, game_type=game_type, collectible_count=4)
    assert out["ok"] is True and out["executed"] is True, game_type
    grouped = group_execution_plan(plan_game(game_type, 4)["steps"])
    # the import-once / attach-per-object invariants hold for every blueprint
    assert bridge.count("import_asset") == len(grouped["script_behaviours"]), game_type
    assert bridge.count("add_component") == len(grouped["attachments"]), game_type


def test_arena_mini_boss_attaches_the_boss_component(bridge):
    ut.unity_build_simple_game(execute=True, game_type="arena", collectible_count=4)
    # the Boss object exists and the boss behaviour was generated/imported
    assert ("set_tag", {"name": "Boss", "tag": "Enemy"}) in bridge.calls
    assert any(p.get("name") == "Boss" for m, p in bridge.calls if m == "create_primitive")


# --- composed (freeform) games build the same way --------------------------

def test_composed_game_builds_through_the_bridge(bridge):
    out = ut.unity_compose_game(enemy=3, collectible=2, moving_hazard=2, execute=True)
    assert out["ok"] is True and out.get("executed") is True
    assert bridge.count("create_primitive") >= 1
    assert bridge.count("import_asset") >= 1
    assert "get_editor_state" in bridge.methods()


# --- the WHOLE chat loop: a natural-language string -> a real build ---------

def _registry_resolver():
    import unitytools.tools  # noqa: F401 - register every @tool
    from unitytools.core.tool_registry import get_all_tools
    return {t.name: t.fn for t in get_all_tools()}.get


def test_chat_string_to_real_build_through_the_fast_path(bridge):
    from unitytools.core.game_studio_actions import run_unity_fast_action
    out = run_unity_fast_action("boss arena oyunu kur ve uygula", _registry_resolver())
    assert out is not None and out["ok"] is True
    # the sentence alone drove a REAL build: geometry + script import + component attach
    assert bridge.count("create_primitive") >= 1
    assert bridge.count("import_asset") >= 1
    assert bridge.count("add_component") >= 1
    assert "get_editor_state" in bridge.methods()


def test_chat_string_without_execute_never_touches_the_scene(bridge):
    from unitytools.core.game_studio_actions import run_unity_fast_action
    out = run_unity_fast_action("boss arena oyunu kur", _registry_resolver())  # no "ve uygula"
    assert out is not None
    assert bridge.calls == []                     # planned only, zero scene mutation


def test_fast_path_execute_trigger_is_explicit_and_safe():
    from unitytools.core.game_studio_actions import plan_unity_fast_action

    def kw(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"]

    # the safe default: a plain build is plan-only
    assert kw("boss arena oyunu kur")["execute"] is False
    assert kw("dodge oyunu yap")["execute"] is False
    # explicit opt-in actually builds, and the step is marked a scene write
    assert kw("boss arena oyunu kur ve uygula")["execute"] is True
    assert kw("dodge oyunu yap ve uygula")["execute"] is True
    assert kw("sahneye uygula bir runner oyunu kur")["execute"] is True
    step = plan_unity_fast_action("arena oyunu kur ve uygula")["steps"][0]
    assert step["write"] is True
    # the composer opts in the same way
    assert plan_unity_fast_action("ozel oyun 5 dusman ve uygula")["steps"][0]["kwargs"]["execute"] is True
