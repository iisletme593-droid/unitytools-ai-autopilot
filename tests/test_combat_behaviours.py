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


# --- enemy (chase + attack in one) ------------------------------------------

def test_enemy_source():
    s = generate_behaviour_script("enemy")
    assert s["ok"] is True and s["class_name"] == "AutopilotEnemy"
    src = s["source"]
    assert 'FindWithTag("Player")' in src                 # targets the player
    assert "Vector3.MoveTowards" in src and "Vector3.Distance" in src  # chases
    assert "attackRange" in src and "attackCooldown" in src
    assert 'SendMessage("TakeDamage", damage' in src       # attacks in range
    assert "if (target == null) return;" in src            # no-op without a player


def test_enemy_is_decoupled_from_health_type():
    src = generate_behaviour_script("enemy")["source"]
    assert "AutopilotHealth." not in src
    assert "GetComponent<AutopilotHealth>" not in src


def test_enemy_is_pure_ascii_and_balanced():
    src = generate_behaviour_script("enemy")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src


@pytest.mark.parametrize("alias", ["dusman", "enemy", "mob", "canavar"])
def test_enemy_aliases(alias):
    assert normalize_behaviour(alias) == "enemy"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotEnemy"


# --- xp / leveling (RPG progression) ----------------------------------------

def test_xp_source():
    s = generate_behaviour_script("xp")
    assert s["ok"] is True and s["class_name"] == "AutopilotXP"
    src = s["source"]
    assert "public static int XP" in src and "public static int Level" in src
    assert "public static void Add(int amount)" in src     # direct helper
    assert "void AddXP(int amount)" in src                  # SendMessage target
    assert "Level++" in src and "Level * 100" in src        # level-up at a threshold
    assert '"Lv "' in src                                   # the Lv/XP HUD


def test_xp_is_pure_ascii_and_balanced():
    src = generate_behaviour_script("xp")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src


@pytest.mark.parametrize("alias", ["xp", "seviye", "level", "tecrube", "deneyim"])
def test_xp_aliases(alias):
    assert normalize_behaviour(alias) == "xp"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotXP"


# --- reward (killable enemy that grants XP) ---------------------------------

def test_reward_source():
    s = generate_behaviour_script("reward")
    assert s["ok"] is True and s["class_name"] == "AutopilotReward"
    src = s["source"]
    assert "public int xpReward" in src and "public int currentHP" in src
    assert "public void TakeDamage(int amount)" in src     # killable (takes damage)
    assert 'SendMessage("AddXP", xpReward' in src          # grants XP to the player
    assert "Destroy(gameObject)" in src                    # dies


def test_reward_is_decoupled_from_xp_type():
    src = generate_behaviour_script("reward")["source"]
    assert "AutopilotXP." not in src                       # grants via SendMessage, no hard ref
    assert "GetComponent<AutopilotXP>" not in src


def test_reward_is_pure_ascii_and_balanced():
    src = generate_behaviour_script("reward")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src


@pytest.mark.parametrize("alias", ["odul", "reward", "ganimet", "xpdrop"])
def test_reward_aliases(alias):
    assert normalize_behaviour(alias) == "reward"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotReward"


# --- loot + inventory (item pickups) ----------------------------------------

def test_loot_source():
    s = generate_behaviour_script("loot")
    assert s["ok"] is True and s["class_name"] == "AutopilotLoot"
    src = s["source"]
    assert "OnTriggerEnter(Collider other)" in src and 'CompareTag("Player")' in src
    assert 'SendMessage("AddItem", amount' in src          # adds to inventory
    assert "Destroy(gameObject)" in src
    assert "isTrigger = true" in src


def test_inventory_source():
    s = generate_behaviour_script("inventory")
    assert s["ok"] is True and s["class_name"] == "AutopilotInventory"
    src = s["source"]
    assert "public static int Items" in src
    assert "public static void Add(int amount)" in src      # static helper
    assert "void AddItem(int amount)" in src                # SendMessage target
    assert '"Items: "' in src                               # HUD


def test_loot_is_decoupled_from_inventory_type():
    src = generate_behaviour_script("loot")["source"]
    assert "AutopilotInventory." not in src                 # signals via SendMessage
    assert "GetComponent<AutopilotInventory>" not in src


@pytest.mark.parametrize("behaviour", ["loot", "inventory"])
def test_loot_inventory_pure_ascii_and_balanced(behaviour):
    src = generate_behaviour_script(behaviour)["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src


@pytest.mark.parametrize("alias,expected", [
    ("item", "loot"), ("esya", "loot"), ("loot", "loot"), ("drop", "loot"),
    ("envanter", "inventory"), ("inventory", "inventory"), ("canta", "inventory"),
    ("ganimet", "reward"),   # ganimet stays with reward — no collision
])
def test_loot_inventory_aliases(alias, expected):
    assert normalize_behaviour(alias) == expected


def test_loot_inventory_form_a_pickup_chain():
    # loot SendMessage("AddItem") -> inventory AddItem(int)
    loot = generate_behaviour_script("loot")["source"]
    inv = generate_behaviour_script("inventory")["source"]
    assert 'SendMessage("AddItem"' in loot
    assert "void AddItem(int amount)" in inv


def test_combat_loop_chain_is_complete():
    # player attack -> reward.TakeDamage -> SendMessage AddXP -> xp.AddXP; enemy -> player health
    attack = generate_behaviour_script("attack")["source"]
    reward = generate_behaviour_script("reward")["source"]
    xp = generate_behaviour_script("xp")["source"]
    enemy = generate_behaviour_script("enemy")["source"]
    health = generate_behaviour_script("health")["source"]
    assert 'targetTag = "Enemy"' in attack and 'SendMessage("TakeDamage"' in attack
    assert "public void TakeDamage(int amount)" in reward and 'SendMessage("AddXP"' in reward
    assert "void AddXP(int amount)" in xp
    assert 'FindWithTag("Player")' in enemy and 'SendMessage("TakeDamage"' in enemy
    assert "public void TakeDamage(int amount)" in health
