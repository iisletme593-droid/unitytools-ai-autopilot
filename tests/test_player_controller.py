"""P7 (cycle 19): player controller / input primitive.

AutopilotPlayerController MonoBehaviour: WASD movement (Input.GetAxis) + Space jump.
Pure, deterministic, balanced-brace source — the input layer of an actual game.
"""
import unitytools.tools.unity_tools as ut
from unitytools.core.gameplay import generate_behaviour_script, plan_gameplay_behaviour, normalize_behaviour


def test_player_source():
    s = generate_behaviour_script("player")
    assert s["ok"] is True
    assert s["class_name"] == "AutopilotPlayerController"
    src = s["source"]
    assert 'Input.GetAxis("Horizontal")' in src
    assert 'Input.GetAxis("Vertical")' in src
    assert "KeyCode.Space" in src
    assert "moveSpeed" in src and "jumpForce" in src
    assert "MonoBehaviour" in src
    assert src.count("{") == src.count("}")     # compilable shape


def test_player_custom_move_speed():
    s = generate_behaviour_script("player", speed=8.0)
    assert "moveSpeed = 8.0f" in s["source"]


def test_turkish_and_english_aliases():
    assert normalize_behaviour("oyuncu") == "player"
    assert normalize_behaviour("kontrolcu") == "player"
    assert generate_behaviour_script("oyuncu")["class_name"] == "AutopilotPlayerController"
    assert generate_behaviour_script("controller")["class_name"] == "AutopilotPlayerController"


def test_plan_player_needs_script_with_source():
    plan = plan_gameplay_behaviour("player", "Hero")
    assert plan["ok"] is False and plan["needs_script"] is True
    assert 'Input.GetAxis' in plan["script"]["source"]
    assert plan["script"]["class_name"] == "AutopilotPlayerController"


def test_tool_generates_player_script(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)   # generate-only path needs no bridge
    r = ut.unity_add_script_behaviour("Hero", "oyuncu")
    assert r["ok"] is True
    assert r["class_name"] == "AutopilotPlayerController"
    assert "Input.GetAxis" in r["source"]
