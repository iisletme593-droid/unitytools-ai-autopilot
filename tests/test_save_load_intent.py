"""P8 (cycle 42): save / load / list-saved natural-language intents.

"oyunu kaydet" / "save as X" → unity_save_game, "oyunu yükle X" / "load X" →
unity_load_game, "kayıtlı oyunlar" → unity_list_saved_games. These beat the
build/assess/variations/catalog intents (distinctive verbs), and scene-level
"save"/"yükle" without a game context are left alone. extract_game_name is tested
directly.
"""
import pytest

from unitytools.core.game_studio_actions import plan_unity_fast_action, extract_game_name


def _step(prompt):
    steps = plan_unity_fast_action(prompt)["steps"]
    return steps[0] if steps else {}


def _tool(prompt):
    return _step(prompt).get("tool", "")


# --- name extraction (pure) -------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ('kaydet "my boss fight"', "my boss fight"),     # quoted
    ("save the game as level1", "level1"),           # english "as X"
    ("dodge oyununu boss olarak kaydet", "boss"),    # turkish "X olarak"
    ("kaydet boss-fight", "boss-fight"),             # verb-prefixed
    ("load game level1", "level1"),                  # verb + filler word skipped
    ("boss oyununu yukle", "boss"),                  # possessive "X oyununu"
    ("oyunu kaydet", None),                          # no name -> fall back to type
    ("save my work", None),                          # "my" is a stopword
])
def test_extract_game_name(text, expected):
    assert extract_game_name(text) == expected


# --- save intent ------------------------------------------------------------

def test_save_routes_with_extracted_name():
    s = _step("dodge oyununu boss olarak kaydet")
    assert s["tool"] == "unity_save_game"
    assert s["kwargs"]["game_type"] == "dodge"
    assert s["kwargs"]["name"] == "boss"
    assert s["write"] is True


def test_save_defaults_name_to_game_type():
    s = _step("chase oyununu kaydet")
    assert s["tool"] == "unity_save_game"
    assert s["kwargs"]["name"] == "chase" and s["kwargs"]["game_type"] == "chase"


def test_save_with_only_a_name_no_game_word():
    assert _tool('kaydet "my level"') == "unity_save_game"
    assert _tool("kaydet boss") == "unity_save_game"


def test_save_difficulty_sets_count():
    assert _step("zor dodge oyununu kaydet")["kwargs"]["collectible_count"] == 8


# --- load intent ------------------------------------------------------------

@pytest.mark.parametrize("prompt,name", [
    ("oyunu yukle boss", "boss"),
    ("boss oyununu yukle", "boss"),
    ("load game level1", "level1"),
])
def test_load_routes_with_name(prompt, name):
    s = _step(prompt)
    assert s["tool"] == "unity_load_game"
    assert s["kwargs"]["name"] == name
    assert s["write"] is False                       # load only returns a plan


# --- list intent ------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "kayitli oyunlar",
    "kayitli oyunlari goster",
    "saved games",
    "diskteki oyunlar neler",
])
def test_list_saved_routes(prompt):
    assert _tool(prompt) == "unity_list_saved_games"


# --- no collisions with the other game intents ------------------------------

def test_other_game_intents_unchanged():
    assert _tool("dodge oyunu yap") == "unity_build_simple_game"
    assert _tool("dodge oyununu degerlendir") == "unity_assess_game"
    assert _tool("dodge varyasyonlari goster") == "unity_game_variations"
    assert _tool("hangi oyunlar yapabilirsin") == "unity_game_catalog"


def test_scene_save_and_restore_not_hijacked():
    # no game context -> these are not game save/load
    assert _tool("save my work") != "unity_save_game"
    assert _tool("sahneyi geri yukle") != "unity_load_game"
