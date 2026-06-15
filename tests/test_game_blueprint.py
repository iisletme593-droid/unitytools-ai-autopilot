"""P7 (cycle 21): assemble a playable game skeleton from the building blocks.

plan_collectathon_game emits the full ordered plan (ground + tagged player with
controller + N collectibles + goal); unity_build_simple_game returns it (execute=
False, safe) or builds it (execute=True, triggers recompiles).
"""
import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_collectathon_game


def _script_targets(plan, behaviour):
    return [s["script_behaviour"]["object"] for s in plan["steps"]
            if "script_behaviour" in s and s["script_behaviour"]["behaviour"] == behaviour]


def test_plan_has_ground_player_collectibles_goal():
    plan = plan_collectathon_game(collectible_count=4)
    assert plan["ok"] is True and plan["game"] == "collectathon"
    # ground first
    assert plan["steps"][0] == {"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}}
    # player is created, tagged Player, and gets the controller behaviour
    tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"]
    assert tags and tags[0]["kwargs"] == {"name": "Player", "tag": "Player"}
    assert _script_targets(plan, "player") == ["Player"]
    # one collectible behaviour per collectible
    assert _script_targets(plan, "collectible") == [f"Collectible_{i}" for i in range(4)]
    # a goal zone with the goal behaviour
    assert _script_targets(plan, "goal") == ["Goal"]


def test_collectible_count_clamped_and_respected():
    assert plan_collectathon_game(collectible_count=0)["collectible_count"] == 1
    assert plan_collectathon_game(collectible_count=99)["collectible_count"] == 50
    assert plan_collectathon_game(collectible_count=7)["collectible_count"] == 7


def test_every_step_is_well_formed():
    for step in plan_collectathon_game()["steps"]:
        assert ("tool" in step) ^ ("script_behaviour" in step)
        if "tool" in step:
            assert step["tool"].startswith("unity_")
        else:
            assert {"object", "behaviour"} <= set(step["script_behaviour"])


# --- the tool --------------------------------------------------------------

def test_tool_dry_run_default_no_scene_changes(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)   # dry-run must not need a bridge
    r = ut.unity_build_simple_game(collectible_count=3)
    assert r["ok"] is True and r["dry_run"] is True
    assert r["collectible_count"] == 3
    assert len(r["steps"]) > 5


class _GameBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params=None, timeout=None):
        self.calls.append(method)
        if method == "get_editor_state":
            return {"is_compiling": False}   # never compiling -> wait returns at once
        return {"ok": True}


def test_tool_execute_builds_geometry_and_scripts(monkeypatch):
    fb = _GameBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_build_simple_game(collectible_count=2, execute=True)
    assert r["executed"] is True
    # geometry + tagging happened against the bridge
    assert "create_primitive" in fb.calls
    assert "set_tag" in fb.calls
    # script behaviours went through the import flow
    assert "import_asset" in fb.calls and "add_component" in fb.calls
    assert r["ok"] is True


def test_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_build_simple_game") is not None


# --- grouped execution (one recompile, not N) ------------------------------

def test_group_execution_plan_dedupes_scripts():
    from unitytools.core.game_blueprint import plan_collectathon_game, group_execution_plan
    grouped = group_execution_plan(plan_collectathon_game(collectible_count=3)["steps"])
    # 3 distinct behaviours even though there are 5 script steps (player + 3 collectible + goal)
    assert grouped["script_behaviours"] == ["player", "collectible", "goal"]
    assert len(grouped["attachments"]) == 5
    assert all("tool" in s for s in grouped["geometry"])


def test_execute_imports_each_unique_script_once(monkeypatch):
    fb = _GameBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_build_simple_game(collectible_count=4, execute=True)
    # 3 unique scripts (player/collectible/goal) -> 3 imports, NOT 6 (one per script step)
    assert fb.calls.count("import_asset") == 3
    assert r["unique_scripts"] == 3
    # 6 attachments: Player + 4 collectibles + Goal
    assert fb.calls.count("add_component") == 6
    # exactly one recompile wait phase (state polled, not once-per-script)
    assert "get_editor_state" in fb.calls
    assert r["executed"] is True
