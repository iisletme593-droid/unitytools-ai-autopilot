"""P7 (cycle 20): win/lose trigger zones — the game-logic layer.

AutopilotCollectible / AutopilotGoalZone / AutopilotKillZone: OnTriggerEnter
MonoBehaviours that make a pickup, a win zone, and a respawn hazard. Each Reset()
sets collider.isTrigger=true so the trigger works without manual setup.
"""
import pytest

from unitytools.core.gameplay import generate_behaviour_script, normalize_behaviour, plan_gameplay_behaviour


def test_collectible_source():
    s = generate_behaviour_script("collectible")
    assert s["class_name"] == "AutopilotCollectible"
    src = s["source"]
    assert "OnTriggerEnter(Collider other)" in src
    assert 'CompareTag("Player")' in src
    assert "Destroy(gameObject)" in src
    assert "isTrigger = true" in src


def test_goal_zone_source():
    src = generate_behaviour_script("goal")["source"]
    assert "AutopilotGoalZone" in src
    assert "You win!" in src
    assert "won = true" in src


def test_kill_zone_source():
    src = generate_behaviour_script("killzone")["source"]
    assert "AutopilotKillZone" in src
    assert "spawnPoint" in src
    assert "other.transform.position = spawnPoint" in src


@pytest.mark.parametrize("alias,cls", [
    ("toplanabilir", "AutopilotCollectible"),
    ("coin", "AutopilotCollectible"),
    ("hedef", "AutopilotGoalZone"),
    ("win", "AutopilotGoalZone"),
    ("olum", "AutopilotKillZone"),
    ("lava", "AutopilotKillZone"),
])
def test_aliases(alias, cls):
    assert generate_behaviour_script(alias)["class_name"] == cls


@pytest.mark.parametrize("behaviour", ["collectible", "goal", "killzone"])
def test_trigger_scripts_compilable_shape(behaviour):
    src = generate_behaviour_script(behaviour)["source"]
    assert src.count("{") == src.count("}")          # balanced braces
    assert "RequireComponent(typeof(Collider))" in src
    assert "isTrigger = true" in src                  # auto-setup in Reset()


def test_plan_routes_collectible_with_source():
    plan = plan_gameplay_behaviour("toplanabilir", "Coin")
    assert plan["ok"] is False and plan["needs_script"] is True
    assert "OnTriggerEnter" in plan["script"]["source"]
    assert plan["script"]["class_name"] == "AutopilotCollectible"
