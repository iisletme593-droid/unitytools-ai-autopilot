"""P7 (cycle 23): a SECOND game blueprint — dodge — proving the pattern generalizes.

Same building blocks, different game: ground + WASD player + N moving hazards
(mover + killzone) + goal. unity_build_simple_game(game_type='dodge') plans/builds it.
"""
import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_dodge_game, group_execution_plan


def _behaviours_on(plan, obj):
    return [s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if "script_behaviour" in s and s["script_behaviour"]["object"] == obj]


def test_dodge_plan_structure():
    plan = plan_dodge_game(obstacle_count=3)
    assert plan["ok"] is True and plan["game"] == "dodge"
    assert plan["steps"][0] == {"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}}
    # player tagged + controller
    assert _behaviours_on(plan, "Player") == ["player"]
    # each obstacle is a MOVING hazard: mover + killzone
    assert _behaviours_on(plan, "Obstacle_0") == ["mover", "killzone"]
    assert _behaviours_on(plan, "Obstacle_2") == ["mover", "killzone"]
    # a goal to reach
    assert _behaviours_on(plan, "Goal") == ["goal"]


def test_obstacle_count_clamped():
    assert plan_dodge_game(obstacle_count=0)["obstacle_count"] == 1
    assert plan_dodge_game(obstacle_count=99)["obstacle_count"] == 50


def test_dodge_groups_to_four_unique_scripts():
    grouped = group_execution_plan(plan_dodge_game(obstacle_count=3)["steps"])
    assert grouped["script_behaviours"] == ["player", "mover", "killzone", "goal"]
    # attachments: player(1) + 3 obstacles*2 + goal(1) = 8
    assert len(grouped["attachments"]) == 8


# --- the tool --------------------------------------------------------------

def test_tool_dodge_dry_run(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_build_simple_game(collectible_count=4, game_type="dodge")
    assert r["ok"] is True and r["dry_run"] is True
    assert r["game"] == "dodge" and r["obstacle_count"] == 4


def test_collectathon_still_default(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_build_simple_game(collectible_count=3)   # no game_type -> collectathon
    assert r["game"] == "collectathon"


class _GameBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params=None, timeout=None):
        self.calls.append(method)
        if method == "get_editor_state":
            return {"is_compiling": False}
        return {"ok": True}


def test_tool_dodge_execute_imports_unique_scripts_once(monkeypatch):
    fb = _GameBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_build_simple_game(collectible_count=3, execute=True, game_type="dodge")
    assert r["executed"] is True
    # 4 unique scripts (player/mover/killzone/goal) imported once each
    assert fb.calls.count("import_asset") == 4
    assert r["unique_scripts"] == 4
    # 8 attachments
    assert fb.calls.count("add_component") == 8
