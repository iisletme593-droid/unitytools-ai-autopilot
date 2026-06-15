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
    "collectible", "goal", "killzone", "spawner", "score", "health", "attack", "enemy",
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
        }
    }
}
"""

_KILLZONE_TEMPLATE = """using UnityEngine;

// Auto-generated by UnityTools autopilot. Kill zone — respawns the player.
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
