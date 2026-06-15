"""P7 (cycle 29): in-game score / HUD — AutopilotScore.

A global counter with an on-screen OnGUI HUD. Collectibles increment it without a
hard reference to the type (SendMessage("AddScore")), so the collectible stays
self-contained while the collectathon shows a live score. Pure, deterministic
C# source — no recompile triggered here.
"""
import pytest

from unitytools.core.gameplay import generate_behaviour_script, normalize_behaviour
from unitytools.core.game_blueprint import plan_collectathon_game, group_execution_plan


def test_score_source():
    s = generate_behaviour_script("score")
    assert s["ok"] is True
    assert s["class_name"] == "AutopilotScore"
    src = s["source"]
    assert "public static int Score" in src
    assert "public static void Add(int amount)" in src   # direct static helper
    assert "void AddScore(int amount)" in src             # SendMessage target
    assert "void OnGUI()" in src
    assert '"Score: " + Score' in src                     # the HUD label
    assert src.count("{") == src.count("}")               # balanced braces


@pytest.mark.parametrize("alias", ["skor", "puan", "hud", "points", "sayac"])
def test_score_aliases(alias):
    assert normalize_behaviour(alias) == "score"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotScore"


def test_collectible_increments_score_without_hard_dependency():
    """The collectible must signal the score by SendMessage (no type reference),
    so it still compiles and runs whether or not a score HUD is present."""
    src = generate_behaviour_script("collectible")["source"]
    assert 'SendMessage("AddScore"' in src
    assert "DontRequireReceiver" in src
    assert "AutopilotScore." not in src                   # no code reference to the type's members
    assert "GetComponent<AutopilotScore>" not in src      # nor a component lookup
    # and it still does its original job
    assert "Destroy(gameObject)" in src


def test_collectathon_ships_a_score_hud_on_the_player():
    plan = plan_collectathon_game(collectible_count=3)
    # score behaviour is attached to the Player (one persistent object, no stray HUD)
    score_targets = [s["script_behaviour"]["object"] for s in plan["steps"]
                     if "script_behaviour" in s and s["script_behaviour"]["behaviour"] == "score"]
    assert score_targets == ["Player"]
    grouped = group_execution_plan(plan["steps"])
    assert "score" in grouped["script_behaviours"]
    # still collapses to one import per unique script (player/score/collectible/goal)
    assert grouped["script_behaviours"] == ["player", "score", "collectible", "goal"]


def test_score_compilable_shape():
    src = generate_behaviour_script("score")["source"]
    assert src.count("(") == src.count(")")
    assert "MonoBehaviour" in src
