"""P14 (cycle 79): composer + persistence -- describe -> keep -> reload -> build.

A composed custom game (game='custom', with its spec) round-trips through game_io
exactly like a blueprint: serialize/deserialize/validate/assess. The
`unity_save_composed_game` tool composes + writes it (path-traversal-guarded), and a
freeform "ozel oyunu X olarak kaydet" routes there -- without stealing the preset save.
"""
import pytest

from unitytools.core.game_blueprint import compose_custom_game
from unitytools.core.game_io import (
    serialize_plan, deserialize_plan, validate_plan,
    save_plan_to_file, load_plan_from_file, list_saved_games)
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools
import unitytools.tools  # noqa: F401 - register tools


# --- the custom plan round-trips like any blueprint -------------------------

def test_custom_plan_serialize_deserialize_preserves_everything():
    plan = compose_custom_game(player=True, enemy=4, collectible=3, spawner=2,
                               ranged=True, timer=True, seed="x")
    back = deserialize_plan(serialize_plan(plan))
    assert back["steps"] == plan["steps"]
    assert back["spec"] == plan["spec"]          # the composed spec survives
    assert back["game"] == "custom"
    assert validate_plan(back)["ok"] is True
    assert assess_game_readiness(back)["playable"] is True


def test_custom_save_load_round_trip_on_disk(tmp_path):
    plan = compose_custom_game(player=True, enemy=5, collectible=2, ranged=True, seed="b")
    res = save_plan_to_file(plan, "my boss arena", root=tmp_path)
    assert res["ok"] is True
    assert (tmp_path / "my_boss_arena.json").is_file()
    assert list_saved_games(root=tmp_path) == ["my_boss_arena"]
    assert load_plan_from_file("my boss arena", root=tmp_path) == plan   # exact reload


def test_composed_save_is_path_traversal_guarded(tmp_path):
    plan = compose_custom_game(player=True, enemy=2)
    res = save_plan_to_file(plan, "../../escape", root=tmp_path)
    written = tmp_path / (res["name"] + ".json")
    assert written.is_file() and written.resolve().parent == tmp_path.resolve()


# --- the tool ---------------------------------------------------------------

def test_save_composed_tool_is_registered():
    tool = {t.name: t for t in get_all_tools()}.get("unity_save_composed_game")
    assert tool is not None


# --- intent routing ---------------------------------------------------------

@pytest.mark.parametrize("prompt,name,enemy", [
    ("ozel oyunu boss olarak kaydet", "boss", 0),
    ("5 dusman 3 toplanabilir oyununu mygame olarak kaydet", "mygame", 5),
    ("4 dusman 2 uretici oyununu sapanca olarak kaydet", "sapanca", 4),
    ("menzilli 5 dusman oyununu kalkan olarak kaydet", "kalkan", 5),
])
def test_composed_save_intent_routes(prompt, name, enemy):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_save_composed_game", prompt
    assert step["kwargs"]["name"] == name
    assert step["kwargs"]["enemy"] == enemy


def test_composed_save_does_not_steal_preset_or_plain_saves():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    # a preset save with no element list still saves the preset
    assert tool("dodge oyununu kaydet") == "unity_save_game"
    assert tool("toplama oyununu kaydet") == "unity_save_game"
    # a bare named save (no elements, no custom framing) still saves a collectathon preset
    assert tool("kaydet boss") == "unity_save_game"
    assert tool("oyunu boss olarak kaydet") == "unity_save_game"


def test_composed_save_passes_seed_through():
    kw = plan_unity_fast_action("ozel oyun 5 dusman tohum 9 boss olarak kaydet")["steps"][0]["kwargs"]
    assert kw["enemy"] == 5 and kw["seed"] == "9"


def test_loading_a_saved_custom_game_yields_a_buildable_plan(tmp_path):
    # the existing load path returns any plan, custom included -> ready to build
    plan = compose_custom_game(player=True, enemy=3, spawner=1)
    save_plan_to_file(plan, "wave", root=tmp_path)
    loaded = load_plan_from_file("wave", root=tmp_path)
    assert validate_plan(loaded)["ok"] is True
    assert assess_game_readiness(loaded)["playable"] is True
