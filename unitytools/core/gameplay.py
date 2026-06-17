"""Gameplay behaviour catalog — the first step from "scene decorator" to
"game maker".

Each behaviour composes EXISTING, configurable bridge tools (Rigidbody via
set_rigidbody, colliders via add_collider) into a real gameplay primitive, so the
autopilot can give an object physics with no new C# code. Behaviours that need a
custom MonoBehaviour (rotate/patrol/follow) are listed in NEEDS_SCRIPT and reported
as not-yet-supported — they await a future `add_script_behaviour` bridge command
rather than silently failing.

Pure data + planning here; the unity_add_gameplay_behaviour tool executes the plan.
"""
from __future__ import annotations

from typing import Any

# behaviour -> ordered (tool_name, extra_kwargs) steps. "name" is injected later.
GAMEPLAY_BEHAVIOURS: dict[str, list[tuple[str, dict[str, Any]]]] = {
    # gravity-driven rigid body that collides with the world
    "physics": [
        ("unity_set_rigidbody", {"use_gravity": True}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    "falling": [
        ("unity_set_rigidbody", {"use_gravity": True}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    "heavy": [
        ("unity_set_rigidbody", {"use_gravity": True, "mass": 10.0}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    "floaty": [
        ("unity_set_rigidbody", {"use_gravity": True, "drag": 4.0}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    # script-driven movement without physics gravity (e.g. a moving platform)
    "kinematic": [
        ("unity_set_rigidbody", {"is_kinematic": True, "use_gravity": False}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    # solid, non-moving obstacle (collider only, no rigidbody)
    "static_obstacle": [
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
}

# Behaviours that genuinely need a custom MonoBehaviour script. Honestly flagged
# instead of faked; unlocked by a future add_script_behaviour bridge command.
NEEDS_SCRIPT: frozenset[str] = frozenset({
    "rotate", "spin", "spinner", "patrol", "follow", "chase", "orbit",
    "move", "bob", "bounce", "wander", "player", "controller",
    "collectible", "goal", "killzone", "spawner", "score", "health", "attack", "enemy", "xp", "reward",
    "loot", "inventory", "ranged", "horde", "gameover", "title", "sound", "runner", "timer", "detector",
    "pushable", "puzzle", "holdzone",
})

# friendly aliases (incl. Turkish)
_ALIASES = {
    "fall": "falling", "dus": "falling", "dusen": "falling",
    "fizik": "physics", "agir": "heavy", "hafif": "floaty",
    "engel": "static_obstacle", "obstacle": "static_obstacle", "solid": "static_obstacle",
    "platform": "kinematic",
    "don": "rotate", "donen": "rotate", "donder": "rotate",
    "hareket": "move", "takip": "follow", "devriye": "patrol", "zipla": "bounce",
    "oyuncu": "player", "kontrolcu": "player", "karakter": "player", "pawn": "player",
    "toplanabilir": "collectible", "pickup": "collectible", "coin": "collectible", "topla": "collectible",
    "hedef": "goal", "finish": "goal", "win": "goal", "bitis": "goal",
    "olum": "killzone", "death": "killzone", "hazard": "killzone", "lava": "killzone", "tuzak": "killzone",
    "spawn": "spawner", "wave": "spawner", "dalga": "spawner", "uretici": "spawner",
    "skor": "score", "puan": "score", "hud": "score", "points": "score", "sayac": "score",
    "can": "health", "saglik": "health", "hp": "health", "health": "health", "canli": "health",
    "saldiri": "attack", "saldir": "attack", "vur": "attack", "vurus": "attack", "hit": "attack",
    "dusman": "enemy", "enemy": "enemy", "mob": "enemy", "canavar": "enemy",
    "xp": "xp", "seviye": "xp", "level": "xp", "tecrube": "xp", "deneyim": "xp",
    "odul": "reward", "reward": "reward", "ganimet": "reward", "xpdrop": "reward",
    "item": "loot", "esya": "loot", "loot": "loot", "drop": "loot",
    "envanter": "inventory", "inventory": "inventory", "canta": "inventory", "items": "inventory",
    "menzilli": "ranged", "nisan": "ranged", "ates": "ranged", "ranged": "ranged", "shoot": "ranged", "mermi": "ranged",
    "horde": "horde", "akin": "horde", "dalgalar": "horde", "surusel": "horde",
    "gameover": "gameover", "oyunsonu": "gameover", "sonekran": "gameover", "winlose": "gameover", "kazankaybet": "gameover",
    "title": "title", "baslik": "title", "menu": "title", "anaekran": "title", "baslangic": "title", "startscreen": "title",
    "sound": "sound", "ses": "sound", "audio": "sound", "beep": "sound", "sfx": "sound", "sescue": "sound",
    "runner": "runner", "kosu": "runner", "kosucu": "runner", "endless": "runner", "kosan": "runner",
    "timer": "timer", "sure": "timer", "zaman": "timer", "countdown": "timer", "gerisayim": "timer", "saat": "timer",
    "detector": "detector", "dedektor": "detector", "gorus": "detector", "sight": "detector", "algilayici": "detector", "nobetci": "detector",
    "pushable": "pushable", "itilebilir": "pushable", "kutu": "pushable", "crate": "pushable", "sandik": "pushable",
    "puzzle": "puzzle", "bulmaca": "puzzle", "sokoban": "puzzle", "hedefsayac": "puzzle",
    "holdzone": "holdzone", "hold": "holdzone", "bolge": "holdzone", "zone": "holdzone", "tepe": "holdzone", "kapma": "holdzone",
}


def normalize_behaviour(behaviour: str) -> str:
    b = (behaviour or "").strip().lower()
    return _ALIASES.get(b, b)


def plan_gameplay_behaviour(behaviour: str, object_name: str) -> dict[str, Any]:
    """Plan the tool steps for a gameplay behaviour on ``object_name``.

    Returns {ok, behaviour, steps:[{tool, kwargs}]} on success; otherwise
    {ok: False, error, ...} (with needs_script=True for script-only behaviours).
    """
    b = normalize_behaviour(behaviour)
    if not object_name:
        return {"ok": False, "error": "object_name is required", "behaviour": b}
    if b in NEEDS_SCRIPT:
        out = {
            "ok": False,
            "behaviour": b,
            "needs_script": True,
            "error": f"'{b}' needs a MonoBehaviour script (use unity_add_script_behaviour)",
        }
        script = generate_behaviour_script(b)
        if script.get("ok"):
            out["script"] = {
                "class_name": script["class_name"],
                "filename": script["filename"],
                "source": script["source"],
            }
        return out
    steps = GAMEPLAY_BEHAVIOURS.get(b)
    if steps is None:
        return {
            "ok": False,
            "behaviour": b,
            "error": f"unknown gameplay behaviour: {behaviour!r}",
            "available": sorted(GAMEPLAY_BEHAVIOURS),
        }
    plan = [{"tool": tool, "kwargs": {"name": object_name, **kw}} for tool, kw in steps]
    return {"ok": True, "behaviour": b, "steps": plan}


# --- scripted behaviour MonoBehaviour templates ----------------------------
# Pure C# source generators for the script-driven behaviours. STEP A toward
# scripted gameplay: deterministic, unit-tested source. STEP B (a separate
# cycle, compile-risky) wires a bridge command to write + attach them.
_ROTATOR_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Spins the object every frame.
public class __CLASS__ : MonoBehaviour
{
    public Vector3 axis = new Vector3(__AX__f, __AY__f, __AZ__f);
    public float speed = __SPEED__f;

    void Update()
    {
        transform.Rotate(axis * speed * Time.deltaTime);
    }
}
"""

_MOVER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Moves the object every frame.
public class __CLASS__ : MonoBehaviour
{
    public Vector3 direction = new Vector3(__AX__f, __AY__f, __AZ__f);
    public float speed = __SPEED__f;

    void Update()
    {
        transform.Translate(direction * speed * Time.deltaTime);
    }
}
"""

_PLAYER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Simple WASD player movement with jump.
public class __CLASS__ : MonoBehaviour
{
    public float moveSpeed = __SPEED__f;
    public float jumpForce = 7f;
    public float gravity = 20f;
    public float groundY = 0.5f;
    private float verticalVelocity = 0f;

    void Update()
    {
        float h = Input.GetAxis("Horizontal");
        float v = Input.GetAxis("Vertical");
        Vector3 move = new Vector3(h, 0f, v) * moveSpeed;

        bool grounded = transform.position.y <= groundY + 0.01f;
        if (grounded && Input.GetKeyDown(KeyCode.Space))
        {
            verticalVelocity = jumpForce;
        }
        verticalVelocity -= gravity * Time.deltaTime;
        move.y = verticalVelocity;

        transform.Translate(move * Time.deltaTime, Space.World);

        if (transform.position.y < groundY)
        {
            Vector3 p = transform.position;
            p.y = groundY;
            transform.position = p;
            verticalVelocity = 0f;
        }
    }
}
"""

_COLLECTIBLE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Collectible pickup (trigger).
[RequireComponent(typeof(Collider))]
public class __CLASS__ : MonoBehaviour
{
    void Reset()
    {
        Collider c = GetComponent<Collider>();
        if (c != null) c.isTrigger = true;
    }

    void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Player"))
        {
            // Tell the player's score HUD, if it has one. SendMessage with
            // DontRequireReceiver keeps this collectible self-contained: it
            // compiles and runs with or without an AutopilotScore present.
            other.SendMessage("AddScore", 1, SendMessageOptions.DontRequireReceiver);
            Debug.Log("Collected: " + gameObject.name);
            Destroy(gameObject);
        }
    }
}
"""

_SCORE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Global score counter + on-screen HUD.
// Attach to one persistent object (the collectathon blueprint puts it on the
// Player). Add points via the static AutopilotScore.Add(n) helper, or via
// SendMessage("AddScore", n) -- the collectible uses the latter so it needs no
// reference to this type. The current score draws in the top-left corner.
public class __CLASS__ : MonoBehaviour
{
    public static int Score = 0;

    void Awake()
    {
        Score = 0;   // statics persist across editor play sessions; start fresh
    }

    public static void Add(int amount)
    {
        Score += amount;
    }

    // SendMessage target (instance) so callers need no reference to this type.
    void AddScore(int amount)
    {
        Score += amount;
    }

    void OnGUI()
    {
        GUI.Label(new Rect(10f, 10f, 200f, 24f), "Score: " + Score);
    }
}
"""

_GOAL_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Goal / win zone (trigger).
[RequireComponent(typeof(Collider))]
public class __CLASS__ : MonoBehaviour
{
    public bool won = false;

    void Reset()
    {
        Collider c = GetComponent<Collider>();
        if (c != null) c.isTrigger = true;
    }

    void OnTriggerEnter(Collider other)
    {
        if (!won && other.CompareTag("Player"))
        {
            won = true;
            Debug.Log("You win!");
            // tell a GameManager the goal was reached so a win/lose screen can declare a
            // WIN (decoupled, by name); a no-op in games without a manager (most of them)
            GameObject.Find("GameManager")?.SendMessage("ReachedGoal", SendMessageOptions.DontRequireReceiver);
        }
    }
}
"""

_KILLZONE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Kill zone -- respawns the player.
[RequireComponent(typeof(Collider))]
public class __CLASS__ : MonoBehaviour
{
    public Vector3 spawnPoint = new Vector3(0f, 1f, 0f);

    void Reset()
    {
        Collider c = GetComponent<Collider>();
        if (c != null) c.isTrigger = true;
    }

    void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Player"))
        {
            Debug.Log("Player died - respawning.");
            other.transform.position = spawnPoint;
            // decoupled hit cue: plays only if the player carries an AutopilotSound
            other.SendMessage("PlayCue", 200f, SendMessageOptions.DontRequireReceiver);
        }
    }
}
"""

_SPAWNER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Spawns physics cubes on a timer (waves).
public class __CLASS__ : MonoBehaviour
{
    public float interval = __SPEED__f;
    public int maxCount = 20;
    private int spawned = 0;

    void Start()
    {
        InvokeRepeating(nameof(SpawnOne), interval, interval);
    }

    void SpawnOne()
    {
        if (maxCount > 0 && spawned >= maxCount)
        {
            CancelInvoke(nameof(SpawnOne));
            return;
        }
        GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
        obj.name = gameObject.name + "_Spawn_" + spawned;
        obj.transform.position = transform.position;
        obj.AddComponent<Rigidbody>();
        spawned++;
    }
}
"""

_BOB_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Bobs the object up and down (sine wave)
// around its starting position.
public class __CLASS__ : MonoBehaviour
{
    public float amplitude = __AY__f;
    public float frequency = __SPEED__f;
    private Vector3 startPos;

    void Start()
    {
        startPos = transform.position;
    }

    void Update()
    {
        float offset = Mathf.Sin(Time.time * frequency) * amplitude;
        transform.position = startPos + new Vector3(0f, offset, 0f);
    }
}
"""

_BOUNCE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Bounces the object off its start height
// (abs(sine) so it never dips below the resting position).
public class __CLASS__ : MonoBehaviour
{
    public float height = __AY__f;
    public float frequency = __SPEED__f;
    private Vector3 startPos;

    void Start()
    {
        startPos = transform.position;
    }

    void Update()
    {
        float offset = Mathf.Abs(Mathf.Sin(Time.time * frequency)) * height;
        transform.position = startPos + new Vector3(0f, offset, 0f);
    }
}
"""

_PATROL_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Patrols back and forth between its start
// point and a point `distance` away along `axis` (PingPong, smooth).
public class __CLASS__ : MonoBehaviour
{
    public Vector3 axis = new Vector3(__AX__f, __AY__f, __AZ__f);
    public float distance = 5f;
    public float speed = __SPEED__f;
    private Vector3 pointA;
    private Vector3 pointB;

    void Start()
    {
        pointA = transform.position;
        pointB = transform.position + axis.normalized * distance;
    }

    void Update()
    {
        float t = Mathf.PingPong(Time.time * speed, 1f);
        transform.position = Vector3.Lerp(pointA, pointB, t);
    }
}
"""

_FOLLOWER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Chases the Player (tag "Player") if one
// exists, stopping `stopDistance` short. No-op when there is no player.
public class __CLASS__ : MonoBehaviour
{
    public float speed = __SPEED__f;
    public float stopDistance = 1f;
    private Transform target;

    void Start()
    {
        GameObject player = GameObject.FindWithTag("Player");
        if (player != null) target = player.transform;
    }

    void Update()
    {
        if (target == null) return;
        if (Vector3.Distance(transform.position, target.position) > stopDistance)
        {
            transform.position = Vector3.MoveTowards(transform.position, target.position, speed * Time.deltaTime);
        }
    }
}
"""

_ORBIT_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Orbits around its starting point on
// `axis` at `radius`, `speed` degrees per second.
public class __CLASS__ : MonoBehaviour
{
    public Vector3 axis = new Vector3(__AX__f, __AY__f, __AZ__f);
    public float radius = 3f;
    public float speed = __SPEED__f;
    private Vector3 center;

    void Start()
    {
        center = transform.position;
        transform.position = center + new Vector3(radius, 0f, 0f);
    }

    void Update()
    {
        transform.RotateAround(center, axis, speed * Time.deltaTime);
    }
}
"""

_WANDER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Wanders to random points near its home,
// picking a fresh target every `retargetInterval` seconds.
public class __CLASS__ : MonoBehaviour
{
    public float speed = __SPEED__f;
    public float range = 5f;
    public float retargetInterval = 2f;
    private Vector3 home;
    private Vector3 target;
    private float timer;

    void Start()
    {
        home = transform.position;
        target = home;
    }

    void Update()
    {
        timer -= Time.deltaTime;
        if (timer <= 0f)
        {
            Vector2 r = Random.insideUnitCircle * range;
            target = home + new Vector3(r.x, 0f, r.y);
            timer = retargetInterval;
        }
        transform.position = Vector3.MoveTowards(transform.position, target, speed * Time.deltaTime);
    }
}
"""

_HEALTH_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Hit points + damage (the base of combat).
// Other scripts call TakeDamage(n) / Heal(n) (e.g. via SendMessage so they need no
// reference to this type). A small HP label draws in the top-right. On death the
// object respawns at its start position, or set destroyOnDeath to remove it.
public class __CLASS__ : MonoBehaviour
{
    public int maxHP = 100;
    public int currentHP = 100;
    public bool destroyOnDeath = false;
    private Vector3 spawnPoint;

    void Start()
    {
        spawnPoint = transform.position;
        currentHP = maxHP;
    }

    public void TakeDamage(int amount)
    {
        currentHP -= amount;
        if (currentHP <= 0)
        {
            currentHP = 0;
            Die();
        }
    }

    public void Heal(int amount)
    {
        currentHP += amount;
        if (currentHP > maxHP) currentHP = maxHP;
    }

    void Die()
    {
        // tell a game-state manager, if one is in the scene (decoupled: found by
        // name, no hard reference; a no-op when there is no GameManager)
        GameObject manager = GameObject.Find("GameManager");
        if (manager != null) manager.SendMessage("PlayerDied", SendMessageOptions.DontRequireReceiver);
        if (destroyOnDeath)
        {
            Destroy(gameObject);
            return;
        }
        currentHP = maxHP;
        transform.position = spawnPoint;
    }

    void OnGUI()
    {
        GUI.Label(new Rect(Screen.width - 150f, 10f, 140f, 24f), "HP: " + currentHP + "/" + maxHP);
    }
}
"""

_ATTACK_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Melee attack: every `cooldown` seconds,
// damages any object tagged `targetTag` within `range` by SendMessage-ing
// TakeDamage to it. Works with AutopilotHealth's TakeDamage(int) but holds NO hard
// reference to that type (decoupled), so it compiles and runs on its own.
public class __CLASS__ : MonoBehaviour
{
    public string targetTag = "Enemy";
    public int damage = 10;
    public float range = 1.5f;
    public float cooldown = 1.0f;
    private float timer = 0f;

    void Update()
    {
        timer -= Time.deltaTime;
        if (timer > 0f) return;
        Collider[] hits = Physics.OverlapSphere(transform.position, range);
        for (int i = 0; i < hits.Length; i++)
        {
            if (hits[i].CompareTag(targetTag))
            {
                hits[i].SendMessage("TakeDamage", damage, SendMessageOptions.DontRequireReceiver);
                timer = cooldown;
                break;
            }
        }
    }
}
"""

_ENEMY_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A simple action-RPG enemy: finds the
// Player (tag), chases it with MoveTowards when out of range, and once within
// attackRange stops and attacks on a cooldown by SendMessage-ing TakeDamage to the
// player. Decoupled: no hard reference to AutopilotHealth (works if the player has
// one, no-op if not). No-op entirely when there is no Player.
public class __CLASS__ : MonoBehaviour
{
    public float moveSpeed = 2.5f;
    public float attackRange = 1.5f;
    public float attackCooldown = 1.0f;
    public int damage = 10;
    private Transform target;
    private float timer = 0f;

    void Start()
    {
        GameObject player = GameObject.FindWithTag("Player");
        if (player != null) target = player.transform;
    }

    void Update()
    {
        if (target == null) return;
        if (timer > 0f) timer -= Time.deltaTime;
        float dist = Vector3.Distance(transform.position, target.position);
        if (dist > attackRange)
        {
            transform.position = Vector3.MoveTowards(transform.position, target.position, moveSpeed * Time.deltaTime);
        }
        else if (timer <= 0f)
        {
            target.SendMessage("TakeDamage", damage, SendMessageOptions.DontRequireReceiver);
            timer = attackCooldown;
        }
    }
}
"""

_XP_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Experience + leveling (RPG progression).
// Add XP via the static AutopilotXP.Add(n) helper or SendMessage("AddXP", n) (so a
// dying enemy can grant XP with no hard reference). At Level*100 XP the level goes
// up, carrying the remainder. A "Lv N - XP x/need" label draws top-right.
public class __CLASS__ : MonoBehaviour
{
    public static int XP = 0;
    public static int Level = 1;

    void Awake()
    {
        XP = 0;
        Level = 1;
    }

    public static void Add(int amount)
    {
        XP += amount;
        int need = Level * 100;
        while (XP >= need)
        {
            XP -= need;
            Level++;
            need = Level * 100;
        }
    }

    void AddXP(int amount)
    {
        Add(amount);
    }

    void OnGUI()
    {
        GUI.Label(new Rect(Screen.width - 150f, 40f, 140f, 24f), "Lv " + Level + " - XP " + XP + "/" + (Level * 100));
    }
}
"""

_REWARD_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A killable that rewards XP -- an enemy's
// HP and loot in one. Takes damage via SendMessage("TakeDamage"); when HP runs out
// it grants xpReward to the Player (SendMessage "AddXP") and destroys itself. Fully
// decoupled: no reference to AutopilotXP or the attacker's type.
public class __CLASS__ : MonoBehaviour
{
    public int maxHP = 30;
    public int currentHP = 30;
    public int xpReward = 25;

    void Start()
    {
        currentHP = maxHP;
    }

    public void TakeDamage(int amount)
    {
        currentHP -= amount;
        if (currentHP <= 0)
        {
            GameObject player = GameObject.FindWithTag("Player");
            if (player != null) player.SendMessage("AddXP", xpReward, SendMessageOptions.DontRequireReceiver);
            Destroy(gameObject);
        }
    }
}
"""

_LOOT_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A loot pickup (trigger). When the Player
// touches it, it adds items to the player's inventory via SendMessage("AddItem")
// (decoupled, no reference to the inventory type) and destroys itself.
[RequireComponent(typeof(Collider))]
public class __CLASS__ : MonoBehaviour
{
    public int amount = 1;

    void Reset()
    {
        Collider c = GetComponent<Collider>();
        if (c != null) c.isTrigger = true;
    }

    void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Player"))
        {
            other.SendMessage("AddItem", amount, SendMessageOptions.DontRequireReceiver);
            Destroy(gameObject);
        }
    }
}
"""

_INVENTORY_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A simple item count + HUD. Add items via
// the static AutopilotInventory.Add(n) helper or SendMessage("AddItem", n); the
// count draws top-left, under the score HUD.
public class __CLASS__ : MonoBehaviour
{
    public static int Items = 0;

    void Awake()
    {
        Items = 0;
    }

    public static void Add(int amount)
    {
        Items += amount;
    }

    void AddItem(int amount)
    {
        Items += amount;
    }

    void OnGUI()
    {
        GUI.Label(new Rect(10f, 34f, 200f, 24f), "Items: " + Items);
    }
}
"""

_RANGED_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A ranged attack (gun/bow). Every
// `cooldown` seconds it finds the NEAREST object tagged `targetTag` within `range`
// (a long reach, unlike melee), aims at it, and damages it via
// SendMessage("TakeDamage") (decoupled, no hard reference to a health type).
public class __CLASS__ : MonoBehaviour
{
    public string targetTag = "Enemy";
    public int damage = 8;
    public float range = 12f;
    public float cooldown = 0.6f;
    private float timer = 0f;

    void Update()
    {
        timer -= Time.deltaTime;
        if (timer > 0f) return;
        Collider[] hits = Physics.OverlapSphere(transform.position, range);
        Transform nearest = null;
        float best = float.MaxValue;
        for (int i = 0; i < hits.Length; i++)
        {
            if (!hits[i].CompareTag(targetTag)) continue;
            float d = Vector3.Distance(transform.position, hits[i].transform.position);
            if (d < best)
            {
                best = d;
                nearest = hits[i].transform;
            }
        }
        if (nearest != null)
        {
            transform.forward = (nearest.position - transform.position).normalized;
            nearest.SendMessage("TakeDamage", damage, SendMessageOptions.DontRequireReceiver);
            timer = cooldown;
        }
    }
}
"""

_HORDE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A horde / survival-brawler driver: spawns
// escalating waves of enemies. Every waveInterval seconds it spawns
// baseCount + (wave-1)*waveGrowth enemy cubes (tagged Enemy, with the enemy AI +
// reward) in a ring, up to maxWaves. Requires AutopilotEnemy + AutopilotReward in
// the project (it AddComponents them), so use it in a combat game that ships those.
public class __CLASS__ : MonoBehaviour
{
    public float waveInterval = 8f;
    public int baseCount = 3;
    public int waveGrowth = 2;
    public int maxWaves = 5;
    public float spawnRadius = 8f;
    private int wave = 0;

    void Start()
    {
        InvokeRepeating(nameof(SpawnWave), 1f, waveInterval);
    }

    void SpawnWave()
    {
        if (maxWaves > 0 && wave >= maxWaves)
        {
            CancelInvoke(nameof(SpawnWave));
            return;
        }
        wave++;
        int count = baseCount + (wave - 1) * waveGrowth;
        for (int i = 0; i < count; i++)
        {
            float ang = (360f / count) * i * Mathf.Deg2Rad;
            Vector3 pos = transform.position + new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang)) * spawnRadius;
            GameObject e = GameObject.CreatePrimitive(PrimitiveType.Cube);
            e.name = "WaveEnemy_" + wave + "_" + i;
            e.transform.position = pos;
            e.tag = "Enemy";
            e.AddComponent<AutopilotEnemy>();
            e.AddComponent<AutopilotReward>();
        }
    }
}
"""

_GAMEOVER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Win/lose state + end screen. WIN once no
// objects tagged "Enemy" remain (after at least one existed); LOSE when something
// SendMessages "PlayerDied" to it. Draws a centered result, pauses the game, and
// reloads the scene on R. Attach to one manager object.
public class __CLASS__ : MonoBehaviour
{
    public static bool IsOver = false;
    public static bool Won = false;
    private bool sawEnemy = false;

    void Awake()
    {
        IsOver = false;
        Won = false;
        Time.timeScale = 1f;
    }

    void Update()
    {
        if (IsOver)
        {
            if (Input.GetKeyDown(KeyCode.R))
            {
                Time.timeScale = 1f;
                UnityEngine.SceneManagement.SceneManager.LoadScene(
                    UnityEngine.SceneManagement.SceneManager.GetActiveScene().buildIndex);
            }
            return;
        }
        GameObject[] enemies = GameObject.FindGameObjectsWithTag("Enemy");
        if (enemies.Length > 0)
        {
            sawEnemy = true;
        }
        else if (sawEnemy)
        {
            Won = true;
            IsOver = true;
            Time.timeScale = 0f;
            // fire-once cue on the win transition; no-op if no AutopilotSound is present
            SendMessage("PlayCue", 880f, SendMessageOptions.DontRequireReceiver);
        }
    }

    void PlayerDied()
    {
        if (IsOver) return;
        Won = false;
        IsOver = true;
        Time.timeScale = 0f;
        // fire-once cue on the lose transition (lower pitch); no-op without AutopilotSound
        SendMessage("PlayCue", 160f, SendMessageOptions.DontRequireReceiver);
    }

    // an alternate WIN path (mirrors PlayerDied): an AutopilotTimer SendMessages this
    // when its countdown ends, so "outlast the clock" games are won by surviving
    void Survived()
    {
        if (IsOver) return;
        Won = true;
        IsOver = true;
        Time.timeScale = 0f;
        SendMessage("PlayCue", 880f, SendMessageOptions.DontRequireReceiver);
    }

    // a third WIN path: an AutopilotGoalZone SendMessages this when the player reaches
    // the goal, so "reach the exit" games (e.g. stealth) are won by getting there
    void ReachedGoal()
    {
        if (IsOver) return;
        Won = true;
        IsOver = true;
        Time.timeScale = 0f;
        SendMessage("PlayCue", 880f, SendMessageOptions.DontRequireReceiver);
    }

    void OnGUI()
    {
        if (!IsOver) return;
        string msg = Won ? "YOU WIN" : "GAME OVER";
        GUI.Label(new Rect(Screen.width / 2f - 60f, Screen.height / 2f - 20f, 160f, 24f), msg);
        GUI.Label(new Rect(Screen.width / 2f - 60f, Screen.height / 2f + 6f, 160f, 24f), "Press R to restart");
    }
}
"""

_TITLE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A start/title screen. Draws the title and
// "Press SPACE to start" centered, and holds the game paused until Space is pressed.
// Sets Time.timeScale = 0 in Start (NOT Awake) on purpose: AutopilotGameOver resets
// timeScale to 1 in its Awake, and Unity runs every Awake before any Start, so doing
// this in Start guarantees it runs last -- the game reliably begins paused on the
// title screen even when a game-over manager is present. Space starts and hides it.
public class __CLASS__ : MonoBehaviour
{
    public string titleText = "GAME";
    private bool started = false;

    void Start()
    {
        Time.timeScale = 0f;
    }

    void Update()
    {
        if (started) return;
        if (Input.GetKeyDown(KeyCode.Space))
        {
            started = true;
            Time.timeScale = 1f;
        }
    }

    void OnGUI()
    {
        if (started) return;
        GUI.Label(new Rect(Screen.width / 2f - 80f, Screen.height / 2f - 30f, 200f, 28f), titleText);
        GUI.Label(new Rect(Screen.width / 2f - 80f, Screen.height / 2f + 2f, 200f, 24f), "Press SPACE to start");
    }
}
"""

_SOUND_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A procedural sound cue, HONEST about being
// generate-only: it ships NO audio asset and loads nothing from Resources. Instead it
// BUILDS its clip at runtime with AudioClip.Create + a deterministic sine wave (Mathf.Sin,
// no Math.random), so the cue is fully self-contained and reproducible. Decoupled: other
// behaviours fire it with SendMessage("PlayCue", DontRequireReceiver), optionally passing
// a frequency. Attach to one object (often the GameManager).
public class __CLASS__ : MonoBehaviour
{
    public float frequency = 440f;
    public float duration = 0.15f;
    public float volume = 0.5f;
    private const int SampleRate = 44100;
    private AudioSource source;

    void Awake()
    {
        source = gameObject.AddComponent<AudioSource>();
        source.playOnAwake = false;
    }

    private AudioClip BuildClip(float freq)
    {
        int samples = Mathf.Max(1, (int)(SampleRate * duration));
        AudioClip clip = AudioClip.Create("AutopilotCue", samples, 1, SampleRate, false);
        float[] data = new float[samples];
        for (int i = 0; i < samples; i++)
        {
            float t = (float)i / SampleRate;
            // deterministic sine with a short linear fade-out so it does not click
            float fade = 1f - ((float)i / samples);
            data[i] = Mathf.Sin(2f * Mathf.PI * freq * t) * volume * fade;
        }
        clip.SetData(data, 0);
        return clip;
    }

    // called directly or via SendMessage("PlayCue") -- plays the default pitch
    public void PlayCue()
    {
        PlayCue(frequency);
    }

    // called via SendMessage("PlayCue", 660f) -- plays an arbitrary pitch
    public void PlayCue(float freq)
    {
        if (source == null) return;
        source.PlayOneShot(BuildClip(freq));
    }
}
"""

_RUNNER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. An endless-runner controller: the object
// auto-runs FORWARD (+Z) at runSpeed; A/D strafe between lanes and Space jumps (a
// simple gravity arc, no Rigidbody). Distance scoring is decoupled: every
// scoreInterval seconds it SendMessage("AddScore", 1) to itself, so an AutopilotScore
// on the same object ticks up with distance (a no-op when there is none). Fully
// deterministic -- no RNG, no time-of-day.
public class __CLASS__ : MonoBehaviour
{
    public float runSpeed = 6f;
    public float strafeSpeed = 5f;
    public float jumpForce = 7f;
    public float gravity = 20f;
    public float groundY = 0.5f;
    public float scoreInterval = 1f;
    private float verticalVelocity = 0f;
    private float scoreTimer = 0f;

    void Update()
    {
        float h = Input.GetAxis("Horizontal");
        bool grounded = transform.position.y <= groundY + 0.01f;
        if (grounded && Input.GetKeyDown(KeyCode.Space))
        {
            verticalVelocity = jumpForce;
        }
        verticalVelocity -= gravity * Time.deltaTime;

        Vector3 move = new Vector3(h * strafeSpeed, verticalVelocity, runSpeed);
        transform.Translate(move * Time.deltaTime, Space.World);

        if (transform.position.y < groundY)
        {
            Vector3 p = transform.position;
            p.y = groundY;
            transform.position = p;
            verticalVelocity = 0f;
        }

        scoreTimer += Time.deltaTime;
        if (scoreTimer >= scoreInterval)
        {
            scoreTimer -= scoreInterval;
            // decoupled distance score; no-op without an AutopilotScore on this object
            SendMessage("AddScore", 1, SendMessageOptions.DontRequireReceiver);
        }
    }
}
"""

_TIMER_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A countdown timer + HUD. Counts `duration`
// seconds down (Time.deltaTime, so it freezes while the game is paused), draws the
// remaining time top-right, and on reaching zero fires ONCE a decoupled
// SendMessage("Survived") -- a win signal a manager (e.g. AutopilotGameOver) reacts to
// ("you outlasted the clock"). No-op without a receiver. Deterministic: no RNG, no
// time-of-day; it only reads Time.deltaTime.
public class __CLASS__ : MonoBehaviour
{
    public float duration = 30f;
    private float remaining;
    private bool fired = false;

    void Awake()
    {
        remaining = duration;
    }

    void Update()
    {
        if (fired) return;
        remaining -= Time.deltaTime;
        if (remaining <= 0f)
        {
            remaining = 0f;
            fired = true;
            SendMessage("Survived", SendMessageOptions.DontRequireReceiver);
        }
    }

    void OnGUI()
    {
        int secs = Mathf.CeilToInt(Mathf.Max(0f, remaining));
        GUI.Label(new Rect(Screen.width - 120f, 10f, 110f, 24f), "Time: " + secs);
    }
}
"""

_DETECTOR_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A guard's line-of-sight detector: each frame
// it finds the Player and, if within sightRange, SendMessages "PlayerDied" to a
// GameManager (caught -> you lose) -- decoupled, by name, a no-op when there is no
// manager. Pair it with `patrol` to make a moving guard for a stealth game. Fires once.
// Deterministic: no RNG, only distance.
public class __CLASS__ : MonoBehaviour
{
    public float sightRange = 6f;
    private bool caught = false;

    void Update()
    {
        if (caught) return;
        GameObject player = GameObject.FindWithTag("Player");
        if (player == null) return;
        if (Vector3.Distance(transform.position, player.transform.position) <= sightRange)
        {
            caught = true;
            GameObject.Find("GameManager")?.SendMessage("PlayerDied", SendMessageOptions.DontRequireReceiver);
        }
    }
}
"""

_PUSHABLE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A pushable crate (sokoban-style). When the
// Player gets within pushRange it slides one notch AWAY from the player (push it onto a
// target). Decoupled (finds the Player by tag, no hard reference) and deterministic --
// it only reads positions, no RNG, no physics tuning, no custom tags. Name a crate
// "Crate_*" so the puzzle manager can score it.
public class __CLASS__ : MonoBehaviour
{
    public float pushRange = 1.4f;
    public float pushSpeed = 3f;
    public float groundY = 0.5f;

    void Update()
    {
        GameObject player = GameObject.FindWithTag("Player");
        if (player == null) return;
        Vector3 away = transform.position - player.transform.position;
        away.y = 0f;
        float dist = away.magnitude;
        if (dist > 0.01f && dist < pushRange)
        {
            transform.position += away.normalized * pushSpeed * Time.deltaTime;
            Vector3 p = transform.position;
            p.y = groundY;
            transform.position = p;
        }
    }
}
"""

_PUZZLE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A sokoban WIN manager. Each frame it finds
// every object named "Target_*" and every "Crate_*" (by name, so no custom Unity tags
// are needed and it stays decoupled), marks a target covered when a crate rests within
// coverRange, draws "Crates: covered/total", and WINS once every target is covered
// (pauses, beeps via a decoupled PlayCue, R restarts). Deterministic: only positions.
public class __CLASS__ : MonoBehaviour
{
    public float coverRange = 0.9f;
    public static bool Solved = false;
    private int coveredCount = 0;
    private int totalCount = 0;

    void Awake()
    {
        Solved = false;
        Time.timeScale = 1f;
    }

    void Update()
    {
        if (Solved)
        {
            if (Input.GetKeyDown(KeyCode.R))
            {
                Time.timeScale = 1f;
                UnityEngine.SceneManagement.SceneManager.LoadScene(
                    UnityEngine.SceneManagement.SceneManager.GetActiveScene().buildIndex);
            }
            return;
        }
        Transform[] all = FindObjectsOfType<Transform>();
        int total = 0;
        int covered = 0;
        for (int i = 0; i < all.Length; i++)
        {
            if (!all[i].name.StartsWith("Target")) continue;
            total++;
            for (int j = 0; j < all.Length; j++)
            {
                if (!all[j].name.StartsWith("Crate")) continue;
                Vector3 d = all[j].position - all[i].position;
                d.y = 0f;
                if (d.magnitude < coverRange) { covered++; break; }
            }
        }
        coveredCount = covered;
        totalCount = total;
        if (total > 0 && covered >= total)
        {
            Solved = true;
            Time.timeScale = 0f;
            SendMessage("PlayCue", 880f, SendMessageOptions.DontRequireReceiver);
        }
    }

    void OnGUI()
    {
        GUI.Label(new Rect(10f, 10f, 240f, 24f), "Crates: " + coveredCount + "/" + totalCount);
        if (Solved)
        {
            GUI.Label(new Rect(Screen.width / 2f - 60f, Screen.height / 2f - 20f, 200f, 24f), "PUZZLE SOLVED");
            GUI.Label(new Rect(Screen.width / 2f - 60f, Screen.height / 2f + 6f, 200f, 24f), "Press R to restart");
        }
    }
}
"""

_HOLDZONE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. A capture / hold zone (king of the hill).
// While the Player stays within `radius`, a hold meter fills; once it reaches
// `holdTime` it SendMessages "Survived" to a GameManager (decoupled, by name) -- the
// WIN. Stepping out pauses the fill (it does not reset). Draws "Hold: filled/target".
// Deterministic: only positions + time; fires once.
public class __CLASS__ : MonoBehaviour
{
    public float radius = 4f;
    public float holdTime = 15f;
    private float held = 0f;
    private bool won = false;

    void Update()
    {
        if (won) return;
        GameObject player = GameObject.FindWithTag("Player");
        if (player != null)
        {
            Vector3 d = player.transform.position - transform.position;
            d.y = 0f;
            if (d.magnitude <= radius)
            {
                held += Time.deltaTime;
            }
        }
        if (held >= holdTime)
        {
            won = true;
            GameObject.Find("GameManager")?.SendMessage("Survived", SendMessageOptions.DontRequireReceiver);
        }
    }

    void OnGUI()
    {
        int cur = Mathf.FloorToInt(Mathf.Min(held, holdTime));
        int tot = Mathf.CeilToInt(holdTime);
        GUI.Label(new Rect(10f, 34f, 220f, 24f), "Hold: " + cur + "/" + tot);
    }
}
"""

# behaviour -> (class name, template, default axis, default speed)
_SCRIPT_TEMPLATES: dict[str, tuple[str, str, tuple[float, float, float], float]] = {
    "rotate": ("AutopilotRotator", _ROTATOR_TEMPLATE, (0.0, 1.0, 0.0), 90.0),
    "spin": ("AutopilotRotator", _ROTATOR_TEMPLATE, (0.0, 1.0, 0.0), 90.0),
    "spinner": ("AutopilotRotator", _ROTATOR_TEMPLATE, (0.0, 1.0, 0.0), 90.0),
    "move": ("AutopilotMover", _MOVER_TEMPLATE, (0.0, 0.0, 1.0), 3.0),
    "mover": ("AutopilotMover", _MOVER_TEMPLATE, (0.0, 0.0, 1.0), 3.0),
    "player": ("AutopilotPlayerController", _PLAYER_TEMPLATE, (0.0, 0.0, 0.0), 5.0),
    "controller": ("AutopilotPlayerController", _PLAYER_TEMPLATE, (0.0, 0.0, 0.0), 5.0),
    "collectible": ("AutopilotCollectible", _COLLECTIBLE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "goal": ("AutopilotGoalZone", _GOAL_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "killzone": ("AutopilotKillZone", _KILLZONE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "spawner": ("AutopilotSpawner", _SPAWNER_TEMPLATE, (0.0, 0.0, 0.0), 1.5),
    "score": ("AutopilotScore", _SCORE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "bob": ("AutopilotBob", _BOB_TEMPLATE, (0.0, 1.0, 0.0), 2.0),
    "bounce": ("AutopilotBounce", _BOUNCE_TEMPLATE, (0.0, 1.0, 0.0), 3.0),
    "patrol": ("AutopilotPatrol", _PATROL_TEMPLATE, (1.0, 0.0, 0.0), 2.0),
    "follow": ("AutopilotFollower", _FOLLOWER_TEMPLATE, (0.0, 0.0, 0.0), 3.0),
    "chase": ("AutopilotFollower", _FOLLOWER_TEMPLATE, (0.0, 0.0, 0.0), 3.0),
    "orbit": ("AutopilotOrbit", _ORBIT_TEMPLATE, (0.0, 1.0, 0.0), 60.0),
    "wander": ("AutopilotWander", _WANDER_TEMPLATE, (0.0, 0.0, 0.0), 2.0),
    "health": ("AutopilotHealth", _HEALTH_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "attack": ("AutopilotAttack", _ATTACK_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "enemy": ("AutopilotEnemy", _ENEMY_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "xp": ("AutopilotXP", _XP_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "reward": ("AutopilotReward", _REWARD_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "loot": ("AutopilotLoot", _LOOT_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "inventory": ("AutopilotInventory", _INVENTORY_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "ranged": ("AutopilotRanged", _RANGED_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "horde": ("AutopilotHorde", _HORDE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "gameover": ("AutopilotGameOver", _GAMEOVER_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "title": ("AutopilotTitle", _TITLE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "sound": ("AutopilotSound", _SOUND_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "runner": ("AutopilotRunner", _RUNNER_TEMPLATE, (0.0, 0.0, 1.0), 6.0),
    "timer": ("AutopilotTimer", _TIMER_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "detector": ("AutopilotDetector", _DETECTOR_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "pushable": ("AutopilotPushable", _PUSHABLE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "puzzle": ("AutopilotPuzzle", _PUZZLE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
    "holdzone": ("AutopilotHoldZone", _HOLDZONE_TEMPLATE, (0.0, 0.0, 0.0), 0.0),
}


def _fmt(value: float) -> str:
    return repr(round(float(value), 4))


def generate_behaviour_script(
    behaviour: str,
    axis: tuple[float, float, float] | None = None,
    speed: float | None = None,
) -> dict[str, Any]:
    """Generate the C# MonoBehaviour source for a scripted behaviour.

    Returns {ok, behaviour, class_name, filename, source}; ok=False if no template
    exists for that behaviour. Deterministic and side-effect free.
    """
    b = normalize_behaviour(behaviour)
    tpl = _SCRIPT_TEMPLATES.get(b)
    if tpl is None:
        return {
            "ok": False,
            "behaviour": b,
            "error": f"no script template for behaviour {behaviour!r}",
            "available": sorted(_SCRIPT_TEMPLATES),
        }
    class_name, template, default_axis, default_speed = tpl
    ax, ay, az = axis if axis is not None else default_axis
    spd = default_speed if speed is None else float(speed)
    source = (
        template
        .replace("__CLASS__", class_name)
        .replace("__AX__", _fmt(ax))
        .replace("__AY__", _fmt(ay))
        .replace("__AZ__", _fmt(az))
        .replace("__SPEED__", _fmt(spd))
    )
    return {
        "ok": True,
        "behaviour": b,
        "class_name": class_name,
        "filename": f"Assets/AutopilotScripts/{class_name}.cs",
        "source": source,
    }


def wait_until_compiled(get_state, sleep, max_attempts: int = 15, interval: float = 2.0) -> bool:
    """Poll ``get_state()`` until the editor reports is_compiling == False.

    Used by the end-to-end scripted-behaviour flow: after a script is imported,
    Unity recompiles asynchronously, so we must wait before attaching the new
    component. ``sleep(interval)`` is injected for testability. Returns True if
    compilation finished within ``max_attempts`` polls, else False (timed out).
    """
    for _ in range(max(1, int(max_attempts))):
        try:
            state = get_state()
        except Exception:
            state = None
        if isinstance(state, dict) and state.get("is_compiling") is False:
            return True
        sleep(interval)
    return False


def _is_collider(component_name: Any) -> bool:
    return str(component_name).endswith("Collider")


def prune_redundant_steps(
    steps: list[dict[str, Any]], existing_components: list[str] | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop steps that would duplicate what the object already has.

    Currently: skip an ``unity_add_collider`` step when the object already carries
    a collider (Cube/Sphere primitives ship one), so the behaviour is idempotent.
    Returns (kept_steps, skipped_steps).
    """
    has_collider = any(_is_collider(c) for c in (existing_components or []))
    kept: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for step in steps:
        if step.get("tool") == "unity_add_collider" and has_collider:
            skipped.append({**step, "reason": "object already has a collider"})
        else:
            kept.append(step)
    return kept, skipped
