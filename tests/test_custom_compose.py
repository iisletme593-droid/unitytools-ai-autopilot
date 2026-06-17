"""P14 (cycle 75): the freeform game composer -- from "pick a preset" to "assemble
what you described". The biggest step toward real autonomy.

compose_custom_game(player, enemy, collectible, hazard, goal, timer) assembles a valid,
playable plan from the same building blocks the blueprints use, wiring the sensible
couplings (enemies -> player health+attack + a win/lose manager; collectibles/enemies
-> a score HUD; timer -> outlast-the-clock win). parse_custom_spec turns a freeform
description into those kwargs; the `unity_compose_game` tool + an "ozel/custom oyun"
intent route it -- gated so it never steals a preset blueprint.
"""
import pytest

from unitytools.core.game_blueprint import compose_custom_game
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import parse_custom_spec, plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools
import unitytools.tools  # noqa: F401 - register tools


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


# --- the composer -----------------------------------------------------------

def test_compose_wires_combat_couplings_for_enemies():
    plan = compose_custom_game(player=True, enemy=5)
    # enemies imply the player can fight and be hurt, and a win/lose manager exists
    assert {"player", "health", "attack", "score"} <= _beh_of(plan, "Player")
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}
    tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"].startswith("Enemy")]
    assert tags == ["Enemy"] * 5


def test_compose_collectibles_add_a_score_hud():
    plan = compose_custom_game(player=True, collectible=4)
    assert "score" in _beh_of(plan, "Player")
    coll = [s["script_behaviour"]["object"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("behaviour") == "collectible"]
    assert coll == [f"Collectible_{i}" for i in range(4)]


def test_compose_timer_adds_an_outlast_manager():
    plan = compose_custom_game(player=True, timer=True)
    # even with no enemies a timer creates the manager (outlast-the-clock win)
    assert "timer" in _beh_of(plan, "GameManager")
    assert "gameover" in _beh_of(plan, "GameManager")


def test_compose_hazards_and_goal():
    plan = compose_custom_game(player=True, hazard=3, goal=True)
    haz = [s["script_behaviour"]["object"] for s in plan["steps"]
           if s.get("script_behaviour", {}).get("behaviour") == "killzone"]
    assert haz == [f"Hazard_{i}" for i in range(3)]
    assert _beh_of(plan, "Goal") == {"goal"}


def test_compose_is_valid_playable_deterministic():
    plan = compose_custom_game(player=True, enemy=4, collectible=2, hazard=1, timer=True, goal=True)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert compose_custom_game(player=True, enemy=4, collectible=2, hazard=1, timer=True, goal=True) == plan


def test_compose_clamps_counts_and_records_spec():
    plan = compose_custom_game(player=True, enemy=99, collectible=-3)
    assert plan["spec"]["enemy"] == 30 and plan["spec"]["collectible"] == 0
    assert plan["game"] == "custom"


def test_compose_player_only_is_an_honest_sandbox():
    # exactly what was asked: a player and nothing to do -> assessed not playable (honest)
    plan = compose_custom_game(player=True)
    assert validate_plan(plan)["ok"] is True
    assert assess_game_readiness(plan)["playable"] is False


# --- the NL spec parser -----------------------------------------------------

def test_parse_counts_and_flags():
    spec = parse_custom_spec("ozel oyun: 5 dusman 3 toplanabilir ve bir sayac olsun")
    assert spec == {"player": True, "enemy": 5, "collectible": 3, "hazard": 0,
                    "goal": False, "timer": True, "spawner": 0, "ranged": False, "guard": 0,
                    "crate": 0, "moving_hazard": 0, "turret": 0, "deadline": False,
                    "player_flash": False, "key": 0}


def test_parse_number_words_and_goal():
    spec = parse_custom_spec("custom game with two enemies and a goal")
    assert spec["enemy"] == 2 and spec["goal"] is True and spec["timer"] is False


def test_parse_bare_word_is_one():
    spec = parse_custom_spec("ozel oyun dusman ve engel olsun")
    assert spec["enemy"] == 1 and spec["hazard"] == 1


# --- the tool + intent ------------------------------------------------------

def test_compose_tool_registered_and_pure():
    tool = {t.name: t for t in get_all_tools()}.get("unity_compose_game")
    assert tool is not None
    out = tool.fn(enemy=3, collectible=2)
    assert out["ok"] is True and out["dry_run"] is True
    assert out["assessment"]["playable"] is True


@pytest.mark.parametrize("prompt", [
    "ozel oyun kur 5 dusman 3 toplanabilir",
    "custom game yap 4 dusman",
    "kendi oyunu kur bir sayac ve 2 dusman",
    "karisik oyun: 6 engel",
])
def test_compose_intent_routes(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_compose_game", prompt


def test_compose_intent_carries_the_parsed_spec():
    kw = plan_unity_fast_action("ozel oyun kur 5 dusman 3 toplanabilir ve sayac")["steps"][0]["kwargs"]
    assert kw["enemy"] == 5 and kw["collectible"] == 3 and kw["timer"] is True
    assert kw["execute"] is False


def test_compose_intent_does_not_steal_presets():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    # presets with element counts must still route to the preset builder, not the composer
    assert tool("toplama oyunu yap") == "unity_build_simple_game" and gt("toplama oyunu yap") == "collectathon"
    assert gt("arena oyunu kur 6 dusman") == "arena"
    assert gt("kule savunma yap") == "tower_defense"
    assert gt("dodge oyunu yap") == "dodge"


# --- cycle 76: keyword-less routing + seed ---------------------------------

@pytest.mark.parametrize("prompt,expect", [
    ("5 dusman 3 toplanabilir oyun yap", {"enemy": 5, "collectible": 3}),
    ("bir oyuncu 4 dusman ve bir sayac olsun oyun kur", {"enemy": 4, "timer": True}),
    ("8 engel olan oyun yap", {"hazard": 8}),
])
def test_keywordless_freeform_routes_to_composer(prompt, expect):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_compose_game", prompt
    for k, v in expect.items():
        assert step["kwargs"][k] == v, (prompt, k)


def test_keywordless_does_not_steal_presets_or_bare_build():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    # a bare build with NO elements still falls through to the default collectathon
    assert tool("oyun yap") == "unity_build_simple_game" and gt("oyun yap") == "collectathon"
    assert gt("bir oyun kur") == "collectathon"
    # explicit "toplama" still builds a collectathon even though it looks element-ish
    assert tool("toplama oyunu yap") == "unity_build_simple_game"
    # every other preset still wins over the keyword-less composer
    for p, expected in [("zamana karsi oyun kur", "time_survival"), ("labirent oyunu kur", "maze"),
                        ("horde oyunu kur", "horde"), ("runner oyunu kur", "runner"),
                        ("platform oyunu yap", "platformer"), ("kovalamaca oyunu", "chase")]:
        assert gt(p) == expected, p


def test_keywordless_extracts_seed():
    kw = plan_unity_fast_action("oyun yap 6 dusman tohum 7")["steps"][0]["kwargs"]
    assert kw["enemy"] == 6 and kw["seed"] == "7"


def test_compose_seed_is_deterministic_and_varies_layout():
    a = compose_custom_game(enemy=5, collectible=3, seed="7")
    assert a == compose_custom_game(enemy=5, collectible=3, seed="7")      # reproducible
    assert a != compose_custom_game(enemy=5, collectible=3, seed="9")      # seed matters
    assert compose_custom_game(enemy=5, seed=None) == compose_custom_game(enemy=5)  # None = plain
    assert a != compose_custom_game(enemy=5, collectible=3)                # seeded differs from plain
    # a seeded compose is still valid + playable
    assert validate_plan(a)["ok"] is True and assess_game_readiness(a)["playable"] is True


# --- cycle 78: spawner + ranged elements ------------------------------------

def test_compose_spawners_are_wave_sources():
    plan = compose_custom_game(player=True, spawner=3)
    spw = [s["script_behaviour"]["object"] for s in plan["steps"]
           if s.get("script_behaviour", {}).get("behaviour") == "spawner"]
    assert spw == [f"Spawner_{i}" for i in range(3)]
    # spawners make a playable survival-style game on their own, with no design notes
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["design_notes"] == []
    assert plan["spec"]["spawner"] == 3


def test_compose_ranged_gives_the_player_a_weapon():
    plan = compose_custom_game(player=True, enemy=4, ranged=True)
    assert "ranged" in _beh_of(plan, "Player")
    assert plan["spec"]["ranged"] is True
    assert assess_game_readiness(plan)["design_notes"] == []   # ranged + enemies is coherent


def test_compose_ranged_without_enemies_is_flagged_by_the_critique():
    plan = compose_custom_game(player=True, ranged=True)
    notes = assess_game_readiness(plan)["design_notes"]
    assert any("no enemies in range" in n for n in notes)


def test_compose_new_elements_valid_playable_deterministic():
    plan = compose_custom_game(player=True, enemy=3, ranged=True, spawner=2, seed="w")
    assert validate_plan(plan)["ok"] is True
    assert assess_game_readiness(plan)["playable"] is True
    assert plan == compose_custom_game(player=True, enemy=3, ranged=True, spawner=2, seed="w")


def test_compose_spawner_count_clamped():
    assert compose_custom_game(spawner=99)["spec"]["spawner"] == 20


def test_parse_recognizes_spawner_and_ranged():
    spec = parse_custom_spec("ozel oyun 4 dusman menzilli ve 2 uretici")
    assert spec["enemy"] == 4 and spec["spawner"] == 2 and spec["ranged"] is True


def test_compose_guards_make_a_stealth_style_game():
    plan = compose_custom_game(player=True, guard=3)
    # guards patrol + detect, are NOT tagged Enemy, and auto-add a goal + a manager so
    # there is a real win (reach the goal) / lose (get caught) loop
    guard_objs = [s["script_behaviour"]["object"] for s in plan["steps"]
                  if s.get("script_behaviour", {}).get("behaviour") == "detector"]
    assert guard_objs == [f"Guard_{i}" for i in range(3)]
    assert _beh_of(plan, "Guard_0") == {"patrol", "detector"}
    assert plan["spec"]["guard"] == 3 and plan["spec"]["goal"] is True
    assert _beh_of(plan, "Goal") == {"goal"}
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}
    enemy_tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                  and s["kwargs"]["tag"] == "Enemy"]
    assert enemy_tags == []                                    # guards are not enemies


def test_compose_guard_game_is_coherent_no_design_notes():
    # goal-win + detector-lose with a gameover manager must NOT be flagged "can only be lost"
    plan = compose_custom_game(player=True, guard=4)
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["design_notes"] == []


def test_compose_guard_valid_playable_deterministic_with_seed():
    plan = compose_custom_game(player=True, guard=3, hazard=2, seed="sneak")
    assert validate_plan(plan)["ok"] is True
    assert assess_game_readiness(plan)["playable"] is True
    assert plan == compose_custom_game(player=True, guard=3, hazard=2, seed="sneak")


def test_compose_guard_count_clamped():
    assert compose_custom_game(guard=99)["spec"]["guard"] == 30


def test_parse_recognizes_guard():
    spec = parse_custom_spec("ozel oyun 3 muhafiz ve bir hedef")
    assert spec["guard"] == 3 and spec["goal"] is True


def test_guard_routes_keywordless_to_composer_without_stealing_stealth():
    def route(p):
        s = plan_unity_fast_action(p)["steps"][0]
        return (s["tool"], s["kwargs"].get("game_type"))
    # a freeform guard count (no stealth keyword) composes a custom game...
    t, _ = route("3 muhafiz olan oyun yap")
    assert t == "unity_compose_game"
    # ...but the stealth PRESET keywords still build the stealth blueprint
    assert route("gizli gec oyunu kur") == ("unity_build_simple_game", "stealth")
    assert route("stealth oyunu yap") == ("unity_build_simple_game", "stealth")


def test_composer_report_is_code_derived_from_the_spec_parser():
    from unitytools.core.game_studio_actions import (
        build_composer_report, _SPEC_ELEMENT_WORDS, _SPEC_FLAG_WORDS, _SPEC_FLAG_PHRASES,
        _COMPOSER_COUPLINGS)
    rep = build_composer_report()
    assert all(ord(c) < 128 for c in rep)
    # every element + flag (single-word AND phrase) the parser knows is listed (no drift)
    all_flags = {**_SPEC_FLAG_WORDS, **_SPEC_FLAG_PHRASES}
    for key in list(_SPEC_ELEMENT_WORDS) + list(all_flags):
        assert f"**{key}**" in rep, key
        for word in (list(_SPEC_ELEMENT_WORDS.get(key, ())) + list(all_flags.get(key, ()))):
            assert word in rep, (key, word)
    assert "## Automatic couplings" in rep and "health + attack" in rep
    # every coupling names a real spec element (no phantom couplings)
    for key, _effect in _COMPOSER_COUPLINGS:
        assert key in _SPEC_ELEMENT_WORDS or key in all_flags, key


def test_composer_report_tool_and_intent():
    tool = {t.name: t for t in get_all_tools()}.get("unity_composer_report")
    assert tool is not None
    assert "Custom Game Composer" in tool.fn()["report"]
    for prompt in ("composer raporu ver", "ne tarif edebilirim", "hangi ogeler var",
                   "what can i compose"):
        assert plan_unity_fast_action(prompt)["steps"][0]["tool"] == "unity_composer_report", prompt


def test_composer_report_intent_does_not_steal_other_reports():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    assert tool("studio raporu ver") == "unity_studio_report"
    assert tool("studio sagligi") == "unity_studio_health"
    assert tool("neler yapabilirsin") == "unity_game_catalog"
    assert tool("3 kutu olan oyun yap") == "unity_compose_game"


def test_compose_crates_make_a_sokoban_style_game():
    plan = compose_custom_game(player=True, crate=3)
    # N pushable crates + N Target_* markers + a puzzle win manager
    assert _beh_of(plan, "Crate_0") == {"pushable"}
    crates = [s["script_behaviour"]["object"] for s in plan["steps"]
              if s.get("script_behaviour", {}).get("behaviour") == "pushable"]
    assert crates == [f"Crate_{i}" for i in range(3)]
    targets = [s for s in plan["steps"] if s.get("tool") == "unity_place_primitives"
               and s["kwargs"]["name_prefix"] == "Target"]
    assert targets and targets[0]["kwargs"]["count"] == 3
    assert "puzzle" in _beh_of(plan, "GameManager")
    assert plan["spec"]["crate"] == 3


def test_compose_crate_game_is_coherent_valid_playable_deterministic():
    plan = compose_custom_game(player=True, crate=4, seed="box")
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["design_notes"] == []     # puzzle win, no false flags
    assert plan == compose_custom_game(player=True, crate=4, seed="box")


def test_compose_crate_count_clamped():
    assert compose_custom_game(crate=99)["spec"]["crate"] == 20


def test_parse_recognizes_crate():
    spec = parse_custom_spec("ozel oyun 4 kutu")
    assert spec["crate"] == 4


def test_crate_routes_keywordless_to_composer_but_sokoban_keeps_the_preset():
    def route(p):
        s = plan_unity_fast_action(p)["steps"][0]
        return (s["tool"], s["kwargs"].get("game_type"))
    # a freeform crate count composes (crate is no longer a preset trigger on its own)...
    t, _ = route("3 kutu olan oyun yap")
    assert t == "unity_compose_game"
    assert plan_unity_fast_action("3 kutu olan oyun yap")["steps"][0]["kwargs"]["crate"] == 3
    # ...but the push phrasing / sokoban / bulmaca still build the puzzle PRESET
    assert route("sokoban yap") == ("unity_build_simple_game", "puzzle")
    assert route("kutu itme oyunu yap") == ("unity_build_simple_game", "puzzle")
    assert route("bulmaca oyunu kur") == ("unity_build_simple_game", "puzzle")


def test_spawner_ranged_route_keywordless_without_stealing_horde():
    def route(p):
        s = plan_unity_fast_action(p)["steps"][0]
        return (s["tool"], s["kwargs"].get("game_type"))
    # a keyword-less spawner list composes...
    t, _ = route("3 uretici olan oyun yap")
    assert t == "unity_compose_game"
    # ...but the horde preset ("dalga modu") is NOT stolen by the spawner word "dalga"
    assert route("dalga modu oyunu kur") == ("unity_build_simple_game", "horde")
    assert route("horde oyunu kur") == ("unity_build_simple_game", "horde")


# --- cycle 111: the deadline composer flag (speedrun-feel custom games) -------

def test_compose_deadline_adds_a_losing_countdown_and_implies_a_goal():
    plan = compose_custom_game(player=True, deadline=True)
    # a deadline implies a goal (the WIN) + a manager running the deadline (the LOSE)
    assert plan["spec"]["deadline"] is True and plan["spec"]["goal"] is True
    assert _beh_of(plan, "Goal") == {"goal"}
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound", "deadline"}


def test_compose_deadline_game_is_coherent_valid_playable_deterministic():
    # reach-the-goal WIN + deadline LOSE with a gameover manager must NOT be flagged
    plan = compose_custom_game(player=True, deadline=True, hazard=3, seed="dash")
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_goal"] is True and r["design_notes"] == []
    assert plan == compose_custom_game(player=True, deadline=True, hazard=3, seed="dash")


def test_compose_deadline_howto_races_the_clock():
    from unitytools.core.game_qa import game_howto_from_plan
    h = game_howto_from_plan(compose_custom_game(player=True, deadline=True, hazard=3))
    assert any("before the deadline" in w.lower() for w in h["win"])
    assert any("deadline runs out" in l.lower() for l in h["lose"])


def test_parse_recognizes_deadline_and_does_not_double_fire_the_timer():
    # the deadline phrase contains the timer word "sure"/"sayac", but the phrase-strip +
    # mutual-exclusion keep timer OFF -- a deadline is a LOSE, not the outlast-WIN timer
    for phrase in ("ozel oyun deadline olsun", "oyun yap sure dolmadan cik",
                   "sayac dolmadan bitir oyunu", "beat the clock game"):
        spec = parse_custom_spec(phrase)
        assert spec["deadline"] is True, phrase
        assert spec["timer"] is False, phrase
    # a plain timer phrase is still a timer (deadline OFF)
    plain = parse_custom_spec("ozel oyun bir sayac olsun")
    assert plain["timer"] is True and plain["deadline"] is False


def test_deadline_routes_keywordless_to_composer_without_stealing_the_speedrun_preset():
    def route(p):
        s = plan_unity_fast_action(p)["steps"][0]
        return (s["tool"], s["kwargs"].get("game_type"), s["kwargs"].get("deadline"))
    # a freeform "deadline" element composes a custom game with the flag set...
    tool, _gt, dl = route("deadline olan oyun yap")
    assert tool == "unity_compose_game" and dl is True
    # ...but the speedrun PRESET keywords still build the speedrun blueprint
    assert route("speedrun oyunu kur")[:2] == ("unity_build_simple_game", "speedrun")
    assert route("beat the clock oyunu kur")[:2] == ("unity_build_simple_game", "speedrun")


def test_compose_deadline_tool_plumbs_the_flag():
    tool = {t.name: t for t in get_all_tools()}.get("unity_compose_game")
    out = tool.fn(deadline=True, hazard=2)
    assert out["ok"] is True and out["spec"]["deadline"] is True
    assert out["assessment"]["playable"] is True and out["assessment"]["design_notes"] == []


# --- cycle 112: the player_flash juice flag (hit feedback on the player) ------

def test_compose_player_flash_adds_hitflash_to_the_player():
    plan = compose_custom_game(player=True, enemy=4, player_flash=True)
    assert "hitflash" in _beh_of(plan, "Player")
    assert plan["spec"]["player_flash"] is True
    # purely cosmetic: it changes nothing about playability or the design critique
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["design_notes"] == []


def test_compose_without_player_flash_has_no_hitflash():
    plan = compose_custom_game(player=True, enemy=4)
    assert "hitflash" not in _beh_of(plan, "Player")
    assert plan["spec"]["player_flash"] is False


def test_compose_player_flash_is_deterministic():
    a = compose_custom_game(player=True, enemy=3, player_flash=True, seed="z")
    assert a == compose_custom_game(player=True, enemy=3, player_flash=True, seed="z")
    assert validate_plan(a)["ok"] is True


def test_parse_recognizes_player_flash():
    for phrase in ("ozel oyun 4 dusman parlama olsun", "5 dusman hitflash oyunu yap",
                   "custom game with 3 enemies and flash"):
        spec = parse_custom_spec(phrase)
        assert spec["player_flash"] is True, phrase
    # absent by default
    assert parse_custom_spec("ozel oyun 4 dusman")["player_flash"] is False


def test_player_flash_is_juice_not_an_element_so_it_does_not_route_alone():
    # a juice word with NO real elements must NOT route to the composer (it is not a game)
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    assert tool("parlama olan oyun yap") != "unity_compose_game"
    # ...but combined with a real element it composes WITH the flag on
    step = plan_unity_fast_action("4 dusman parlamali oyun yap")["steps"][0]
    assert step["tool"] == "unity_compose_game" and step["kwargs"]["player_flash"] is True


def test_compose_player_flash_tool_plumbs_the_flag():
    tool = {t.name: t for t in get_all_tools()}.get("unity_compose_game")
    out = tool.fn(enemy=3, player_flash=True)
    assert out["ok"] is True and out["spec"]["player_flash"] is True
    assert out["assessment"]["playable"] is True


# --- cycle 116: the key element (keydoor mechanic, freeform) ------------------

def test_compose_keys_make_a_key_and_door_game():
    plan = compose_custom_game(player=True, key=3)
    # N keys (collectibles named Key_*) + a LOCKED Door (lockgoal) + score + a gameover manager
    keys = [s["script_behaviour"]["object"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("behaviour") == "collectible"]
    assert keys == [f"Key_{i}" for i in range(3)]
    assert _beh_of(plan, "Door") == {"lockgoal"}
    assert "score" in _beh_of(plan, "Player")
    assert "gameover" in _beh_of(plan, "GameManager")
    assert plan["spec"]["key"] == 3
    # no plain Goal object -- the locked door IS the exit
    assert _beh_of(plan, "Goal") == set()


def test_compose_key_game_is_coherent_valid_playable_deterministic():
    plan = compose_custom_game(player=True, key=3, hazard=2, seed="lock")
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_goal"] is True       # lockgoal counts as the exit
    assert r["design_notes"] == []                               # lockgoal is a real WIN trigger
    assert plan == compose_custom_game(player=True, key=3, hazard=2, seed="lock")


def test_compose_key_replaces_the_plain_goal_even_with_a_deadline():
    # a deadline normally auto-adds a plain goal; with keys, the LOCKED door is the exit instead
    plan = compose_custom_game(player=True, key=2, deadline=True)
    assert _beh_of(plan, "Door") == {"lockgoal"}
    assert _beh_of(plan, "Goal") == set()
    assert "deadline" in _beh_of(plan, "GameManager")            # reach the locked exit before the clock
    assert assess_game_readiness(plan)["design_notes"] == []


def test_compose_key_count_clamped():
    assert compose_custom_game(key=99)["spec"]["key"] == 30


def test_parse_recognizes_key():
    spec = parse_custom_spec("ozel oyun 3 anahtar olsun")
    assert spec["key"] == 3
    assert parse_custom_spec("custom game with 2 keys")["key"] == 2


def test_key_routes_keywordless_to_composer_without_stealing_the_keydoor_preset():
    def route(p):
        s = plan_unity_fast_action(p)["steps"][0]
        return (s["tool"], s["kwargs"].get("game_type"), s["kwargs"].get("key"))
    # a freeform key count composes a custom game with the key element...
    tool, _gt, k = route("3 anahtar olan oyun yap")
    assert tool == "unity_compose_game" and k == 3
    # ...but the keydoor PRESET phrases still build the keydoor blueprint
    assert route("anahtarli kapi oyunu kur")[:2] == ("unity_build_simple_game", "keydoor")
    assert route("keydoor oyunu kur")[:2] == ("unity_build_simple_game", "keydoor")


def test_compose_key_tool_plumbs_the_element():
    tool = {t.name: t for t in get_all_tools()}.get("unity_compose_game")
    out = tool.fn(key=3, hazard=2)
    assert out["ok"] is True and out["spec"]["key"] == 3
    assert out["assessment"]["playable"] is True and out["assessment"]["design_notes"] == []
