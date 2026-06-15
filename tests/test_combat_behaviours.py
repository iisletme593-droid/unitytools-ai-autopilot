"""P11 (cycle 51): combat / RPG building blocks — first step: health.

The studio cannot make an MMO/AAA action-RPG, but it CAN grow action-RPG-flavored
building blocks in the same deterministic MonoBehaviour-template style. First up:
`health` (AutopilotHealth) — hit points, TakeDamage/Heal, death->respawn, a HP HUD.
Pure C# source; no recompile triggered here.
"""
import pytest

from unitytools.core.gameplay import generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT


def test_health_source():
    s = generate_behaviour_script("health")
    assert s["ok"] is True and s["class_name"] == "AutopilotHealth"
    src = s["source"]
    assert "public int maxHP" in src and "public int currentHP" in src
    assert "public void TakeDamage(int amount)" in src         # combat entry point
    assert "public void Heal(int amount)" in src
    assert "transform.position = spawnPoint" in src            # death -> respawn
    assert "destroyOnDeath" in src                              # or remove
    assert '"HP: "' in src                                      # HP HUD


def test_health_is_pure_ascii_and_balanced():
    src = generate_behaviour_script("health")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}")
    assert src.count("(") == src.count(")")
    assert "__" not in src                                      # all placeholders substituted


@pytest.mark.parametrize("alias", ["can", "saglik", "hp", "health", "canli"])
def test_health_aliases(alias):
    assert normalize_behaviour(alias) == "health"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotHealth"


def test_health_registered_in_needs_script():
    assert "health" in NEEDS_SCRIPT


def test_no_behaviour_left_without_template():
    # adding health/attack must not leave any NEEDS_SCRIPT behaviour un-templated
    from unitytools.core.gameplay import _SCRIPT_TEMPLATES
    missing = sorted(b for b in NEEDS_SCRIPT if b not in _SCRIPT_TEMPLATES)
    assert missing == [], f"declared-but-unimplemented: {missing}"


# --- attack -----------------------------------------------------------------

def test_attack_source():
    s = generate_behaviour_script("attack")
    assert s["ok"] is True and s["class_name"] == "AutopilotAttack"
    src = s["source"]
    assert "public int damage" in src
    assert "public float range" in src and "public float cooldown" in src
    assert "Physics.OverlapSphere(transform.position, range)" in src   # ranged hit
    assert 'SendMessage("TakeDamage", damage' in src                   # deals damage
    assert "DontRequireReceiver" in src


def test_attack_is_decoupled_from_health_type():
    # it damages via SendMessage, with NO code reference to AutopilotHealth,
    # so attack compiles/runs whether or not a Health component is present.
    src = generate_behaviour_script("attack")["source"]
    assert "AutopilotHealth." not in src                 # no member access
    assert "GetComponent<AutopilotHealth>" not in src    # no component lookup


def test_attack_is_pure_ascii_and_balanced():
    src = generate_behaviour_script("attack")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src


@pytest.mark.parametrize("alias", ["saldiri", "saldir", "vur", "vurus", "hit", "attack"])
def test_attack_aliases(alias):
    assert normalize_behaviour(alias) == "attack"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotAttack"


def test_health_and_attack_form_a_combat_pair():
    # the decoupled chain: attack SendMessage("TakeDamage") -> health TakeDamage(int)
    attack = generate_behaviour_script("attack")["source"]
    health = generate_behaviour_script("health")["source"]
    assert 'SendMessage("TakeDamage"' in attack
    assert "public void TakeDamage(int amount)" in health
