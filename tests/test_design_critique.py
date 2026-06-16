"""P14 (cycle 77): the design critique -- the studio reviewing its own output beyond
"is it playable". Honest: derived purely from the plan's behaviour counts, no faked
simulation. Surfaced as `design_notes` in assess_game_readiness / unity_assess_game.
"""
import pytest

from unitytools.core.game_qa import critique_design, assess_game_readiness
from unitytools.core.game_blueprint import plan_game, compose_custom_game, BLUEPRINTS


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_every_blueprint_is_well_formed_no_design_notes(game_type):
    # the 11 shipped blueprints are coherent -- the critique must not flag them (no
    # false positives), which also guards against future blueprints regressing balance
    report = assess_game_readiness(plan_game(game_type, 4))
    assert report["design_notes"] == [], (game_type, report["design_notes"])


def test_enemies_without_health_is_a_one_sided_fight():
    notes = critique_design({"enemy": 3})
    assert any("cannot be defeated" in n for n in notes)


def test_enemies_without_attack_is_one_sided():
    notes = critique_design({"enemy": 3, "health": 1})        # player can be hurt but can't fight
    assert any("only flee" in n for n in notes)


def test_attack_with_no_enemies():
    notes = critique_design({"attack": 1, "player": 1})
    assert any("no enemies to fight" in n for n in notes)


def test_ranged_with_no_enemies():
    notes = critique_design({"ranged": 2})
    assert any("no enemies in range" in n for n in notes)


def test_gameover_with_no_win_trigger():
    notes = critique_design({"gameover": 1, "player": 1})     # no enemies, no timer
    assert any("can only be lost" in n for n in notes)


def test_timer_with_no_lose_path():
    notes = critique_design({"timer": 1, "player": 1})        # nothing can defeat the player
    assert any("cannot actually be lost" in n for n in notes)


def test_a_healthy_combat_game_has_no_notes():
    # enemies + player health + attack + a manager with both win paths -> coherent
    notes = critique_design({"enemy": 5, "health": 1, "attack": 1, "gameover": 1})
    assert notes == []


def test_a_healthy_timer_game_has_no_notes():
    notes = critique_design({"enemy": 4, "health": 1, "attack": 1, "timer": 1, "gameover": 1})
    assert notes == []


def test_composer_surfaces_the_critique_through_assess():
    # a composed "player + timer, no enemies" is structurally playable-ish but has no
    # real lose path; the critique says so honestly
    plan = compose_custom_game(player=True, timer=True)
    notes = assess_game_readiness(plan)["design_notes"]
    assert any("cannot actually be lost" in n for n in notes)


def test_design_notes_key_is_always_present_as_a_list():
    for plan in (plan_game("arena", 4), compose_custom_game(player=True, enemy=2)):
        report = assess_game_readiness(plan)
        assert isinstance(report["design_notes"], list)
