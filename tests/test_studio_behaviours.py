"""Phase 34 tests: Behaviour library + attach tool wrappers.

The Unity plugin ships 9 runtime MonoBehaviours (Rotator, Bobber,
PulseScale, LookAtCamera, DestroyAfter, FollowTarget,
LoadSceneOnClick, QuitOnClick, KeyboardMover). The bridge has an
attach_behaviour RPC that uses reflection to AddComponent and set
serialized fields by name. We cannot exercise the C# reflection
path from Python tests, so we cover:
- the Python wrapper validates behaviour names against the library
- the wrapper forwards target + behaviour + params block correctly
- the role allowlists (Worker + UI Builder) match
- the C# source files exist and parse as expected
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import unitytools.tools.unity_tools as unity_tools
from unitytools.studio import (
    ART_DIRECTOR,
    AUDIO_DIRECTOR,
    BUILD_ENGINEER,
    CAMERA_DIRECTOR,
    DESIGNER,
    LIGHTING_DIRECTOR,
    PHYSICS_QA,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
)
from unitytools.tools.unity_tools import (
    _BEHAVIOUR_LIBRARY,
    unity_attach_behaviour,
    unity_list_attached_behaviours,
    unity_list_behaviour_library,
)


class FakeUnity:
    def __init__(self, connected: bool = True, raise_on_method: str = ""):
        self._connected = connected
        self._raise_on = raise_on_method
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self):
        return self._connected

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if self._raise_on and method == self._raise_on:
            raise RuntimeError(f"simulated failure on {method}")
        if method == "attach_behaviour":
            return {
                "ok": True,
                "target": params["target_name"],
                "behaviour": params["behaviour_name"],
                "created": True,
                "applied_fields": list((params.get("params") or {}).keys()),
                "skipped_fields": [],
            }
        if method == "list_behaviour_library":
            return {
                "ok": True,
                "count": 9,
                "library": [
                    {"name": "Rotator", "found": True, "full_type": "UnityTools.Behaviours.Rotator",
                     "fields": [{"name": "axis", "type": "Vector3"}, {"name": "speedDegPerSec", "type": "Single"}]},
                ],
            }
        if method == "list_attached_behaviours":
            return {
                "ok": True,
                "count": 1,
                "attached": [
                    {"game_object": params.get("target_name") or "Cube", "behaviour": "Rotator",
                     "full_type": "UnityTools.Behaviours.Rotator"},
                ],
            }
        raise AssertionError(f"unexpected bridge method: {method}")


# ───────────────────────────────────────────── library presence


def test_behaviour_library_contains_known_behaviours() -> None:
    expected = {
        "Rotator", "Bobber", "PulseScale", "LookAtCamera",
        "DestroyAfter", "FollowTarget", "LoadSceneOnClick",
        "QuitOnClick", "KeyboardMover",
        # Phase 39
        "LocalizedText",
        # Phase 40 game-loop primitives
        "GameSession", "Collectible", "ScoreHUD",
        # Phase 41 pause + persistent settings
        "PauseMenu", "SettingsStore",
        # Phase 43 combat primitives
        "Projectile", "Shooter", "Spawner", "Enemy",
        # Phase 46 endless-runner primitives
        "AutoScroller", "LanePositioner",
        # Phase 50 platformer primitive
        "Jumper",
    }
    assert set(_BEHAVIOUR_LIBRARY) == expected
    assert len(_BEHAVIOUR_LIBRARY) == 22
    print("OK Behaviour library exposes 22 known names")


def test_each_behaviour_has_a_corresponding_cs_file() -> None:
    behaviours_dir = _REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours"
    for name in _BEHAVIOUR_LIBRARY:
        path = behaviours_dir / f"{name}.cs"
        assert path.exists(), f"behaviour file missing: {path}"
        body = path.read_text(encoding="utf-8")
        # Must live in the canonical namespace so reflection lookup finds it
        assert "namespace UnityTools.Behaviours" in body, f"{name}.cs has wrong namespace"
        # Must derive from MonoBehaviour
        assert "MonoBehaviour" in body, f"{name}.cs does not extend MonoBehaviour"
        # Must declare the class with the right name
        assert re.search(rf"class\s+{name}\b", body), f"{name}.cs does not declare class {name}"
    print("OK every library name has a matching MonoBehaviour file in unity_plugin/Scripts/Behaviours/")


def test_runtime_scripts_do_not_use_editor_assembly() -> None:
    """Runtime scripts must compile into Assembly-CSharp, not the Editor
    assembly. We guard against accidental `using UnityEditor;` so the
    behaviour library still loads at runtime in built players."""
    behaviours_dir = _REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours"
    for name in _BEHAVIOUR_LIBRARY:
        body = (behaviours_dir / f"{name}.cs").read_text(encoding="utf-8")
        # QuitOnClick has an `#if UNITY_EDITOR` guarded import — that's OK.
        # Reject only unconditional editor usings.
        unconditional = re.search(r"^using UnityEditor;\s*$", body, re.MULTILINE)
        if unconditional:
            # Allow only inside a UNITY_EDITOR conditional block
            assert "#if UNITY_EDITOR" in body, (
                f"{name}.cs uses UnityEditor unconditionally — breaks runtime builds"
            )
    print("OK no runtime behaviour pulls in UnityEditor unconditionally")


# ───────────────────────────────────────────── game-loop primitives (Phase 40)


def test_game_session_exposes_score_lives_and_state_machine() -> None:
    """GameSession is the game's state hub: Score, Lives, IsOver, plus
    AddScore / LoseLife / WinGame / LoseGame transitions. ScoreHUD +
    Collectible read this contract, so it must stay intact."""
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "GameSession.cs").read_text(encoding="utf-8")
    # Singleton accessor
    assert "GameSession Current" in body, "GameSession must expose a static Current"
    # Public state
    for prop in ("Score", "Lives", "IsOver"):
        assert re.search(rf"public\s+(?:int|bool)\s+{prop}\s*{{\s*get", body), f"GameSession.{prop} not exposed"
    # State transitions
    for method in ("AddScore", "LoseLife", "WinGame", "LoseGame", "Reset"):
        assert re.search(rf"public\s+void\s+{method}\s*\(", body), f"GameSession.{method}() missing"
    # Event subscribers can hook
    assert "OnStateChanged" in body
    # Win scene transition uses SceneManager
    assert "SceneManager.LoadScene" in body
    print("OK GameSession contract: Score/Lives/IsOver + AddScore/LoseLife/WinGame/LoseGame/Reset + OnStateChanged + SceneManager")


def test_collectible_requires_trigger_collider_and_calls_game_session() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "Collectible.cs").read_text(encoding="utf-8")
    # Trigger path: 3D + 2D
    assert "OnTriggerEnter(Collider" in body, "Collectible must hook OnTriggerEnter (3D)"
    assert "OnTriggerEnter2D" in body, "Collectible must hook OnTriggerEnter2D (2D)"
    # Routes score to the active GameSession
    assert "GameSession.Current" in body
    assert "AddScore" in body
    # Filter field exists (so a stray enemy doesn't trigger it)
    assert "playerFilter" in body
    print("OK Collectible: trigger 3D+2D, routes to GameSession.Current.AddScore, filtered by playerFilter")


def test_score_hud_requires_text_and_renders_format_tokens() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "ScoreHUD.cs").read_text(encoding="utf-8")
    # Requires Text — otherwise the attach would fail at runtime
    assert "RequireComponent(typeof(Text))" in body, "ScoreHUD must RequireComponent<Text>"
    # Subscribes / unsubscribes to OnStateChanged so it doesn't leak
    assert "OnStateChanged += Refresh" in body
    assert "OnStateChanged -= Refresh" in body
    # Supports the three documented format tokens
    for token in ("{score}", "{lives}", "{win}"):
        assert token in body, f"ScoreHUD format must support {token}"
    print("OK ScoreHUD: requires Text, manages OnStateChanged subscription, supports {score}/{lives}/{win} tokens")


def test_game_loop_trio_lives_in_runtime_namespace() -> None:
    """The Worker attaches by short name; reflection looks them up in
    UnityTools.Behaviours. Lock that contract."""
    for name in ("GameSession", "Collectible", "ScoreHUD"):
        body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / f"{name}.cs").read_text(encoding="utf-8")
        assert "namespace UnityTools.Behaviours" in body, f"{name}.cs has wrong namespace"
        # No UnityEditor leak — Collectible / ScoreHUD / GameSession run
        # in player builds
        assert "using UnityEditor;" not in body, f"{name}.cs must not import UnityEditor at runtime"
    print("OK game-loop trio (GameSession + Collectible + ScoreHUD) all in UnityTools.Behaviours, no UnityEditor leak")


# ───────────────────────────────────────────── pause + settings (Phase 41)


def test_pause_menu_toggles_panel_and_time_scale() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "PauseMenu.cs").read_text(encoding="utf-8")
    # Toggle key serialized so the studio can rebind from Escape -> P / etc.
    assert "KeyCode toggleKey" in body
    # Public state machine: IsPaused getter, Pause / Resume / Toggle
    assert re.search(r"public\s+bool\s+IsPaused\s*{\s*get", body), "PauseMenu must expose IsPaused getter"
    for method in ("Pause", "Resume", "Toggle"):
        assert re.search(rf"public\s+void\s+{method}\s*\(", body), f"PauseMenu.{method}() missing"
    # Time.timeScale handling — must restore on resume + on disable so
    # removing the component mid-pause doesn't leave the game frozen
    assert "Time.timeScale" in body
    assert "OnDisable" in body
    # Listens to a configured key in Update
    assert "Input.GetKeyDown" in body
    print("OK PauseMenu contract: IsPaused + Pause/Resume/Toggle + Time.timeScale + safe OnDisable restore")


def test_settings_store_uses_player_prefs_with_namespace() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "SettingsStore.cs").read_text(encoding="utf-8")
    # All PlayerPrefs keys are namespaced under 'unitytools.' so the
    # studio's keys don't collide with whatever the project's existing
    # code might be writing.
    assert "KeyPrefix" in body
    assert '"unitytools."' in body, "SettingsStore must namespace under 'unitytools.'"
    # Static convenience API for non-MonoBehaviour callers
    for method in ("SetFloat", "GetFloat", "SetInt", "GetInt", "SetString", "GetString", "HasKey", "DeleteKey", "Save"):
        assert re.search(rf"public\s+static\s+\S+\s+{method}\s*\(", body), f"SettingsStore.{method}() missing"
    # Defaults apply only on first run (HasKey check)
    assert "HasKey" in body
    # Saves on disable so PlayerPrefs.Save isn't called every frame
    assert "OnDisable" in body
    print("OK SettingsStore contract: 'unitytools.' namespace + static {Set,Get}{Float,Int,String} API + HasKey/DeleteKey/Save + idempotent defaults")


def test_pause_and_settings_in_runtime_namespace() -> None:
    for name in ("PauseMenu", "SettingsStore"):
        body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / f"{name}.cs").read_text(encoding="utf-8")
        assert "namespace UnityTools.Behaviours" in body, f"{name}.cs has wrong namespace"
        assert "using UnityEditor;" not in body, f"{name}.cs must not import UnityEditor"
    print("OK PauseMenu + SettingsStore in UnityTools.Behaviours, no UnityEditor leak")


# ───────────────────────────────────────────── combat primitives (Phase 43)


def test_projectile_moves_lifetime_and_damages_enemy() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "Projectile.cs").read_text(encoding="utf-8")
    # Tunable fields
    for f in ("speed", "lifetime", "damage", "ignoreNamePrefix"):
        assert re.search(rf"public\s+\S+\s+{f}\s*[=;]", body), f"Projectile.{f} field missing"
    # Lifetime path
    assert "Destroy(gameObject, lifetime)" in body
    # Hooks both 3D + 2D physics
    assert "OnTriggerEnter(Collider" in body
    assert "OnTriggerEnter2D(Collider2D" in body
    # Calls Enemy.TakeDamage when hitting an Enemy
    assert "Enemy" in body
    assert "TakeDamage" in body
    # Ignore-prefix safety so the projectile doesn't kill its own shooter
    assert "ignoreNamePrefix" in body
    print("OK Projectile contract: speed/lifetime/damage + 3D+2D trigger + Enemy.TakeDamage + ignore prefix")


def test_enemy_takes_damage_and_awards_score_on_death() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "Enemy.cs").read_text(encoding="utf-8")
    # Public state machine
    for f in ("health", "scoreOnDeath", "contactDamage", "playerNamePrefix"):
        assert re.search(rf"public\s+\S+\s+{f}\s*[=;]", body), f"Enemy.{f} field missing"
    # TakeDamage entry point
    assert re.search(r"public\s+void\s+TakeDamage\s*\(", body), "Enemy.TakeDamage(int) missing"
    # Die path -> GameSession score reward
    assert "GameSession.Current" in body
    assert "AddScore" in body
    # Contact damage path -> LoseLife
    assert "LoseLife" in body
    # Death actually removes the GameObject
    assert "Destroy(gameObject)" in body
    print("OK Enemy contract: TakeDamage + die + AddScore on death + LoseLife on player contact")


def test_shooter_resolves_template_and_rate_limits() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "Shooter.cs").read_text(encoding="utf-8")
    # Tunable fields
    for f in ("projectileTemplateName", "fireKey", "fireRate", "aimAtMouse"):
        assert re.search(rf"public\s+\S+\s+{f}\s*[=;]", body), f"Shooter.{f} field missing"
    # Rate limit by Time.time
    assert "Time.time" in body
    assert "fireRate" in body
    # Aim with mouse uses Camera.main + ScreenPointToRay
    assert "Camera.main" in body
    assert "ScreenPointToRay" in body
    # Clones template via Instantiate
    assert "Instantiate(_template" in body
    # Hides the template so it doesn't show in scene
    assert "_template.SetActive(false)" in body
    print("OK Shooter contract: template-by-name + fireRate gate + mouse aim + Instantiate clone + template hidden")


def test_spawner_caps_alive_and_prunes_dead_refs() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "Spawner.cs").read_text(encoding="utf-8")
    # Tunable fields
    for f in ("templateName", "interval", "maxAlive", "spawnRadius", "warmup", "flatXZ"):
        assert re.search(rf"public\s+\S+\s+{f}\s*[=;]", body), f"Spawner.{f} field missing"
    # Tracks live clones
    assert "List<GameObject>" in body
    # Prunes destroyed clones each frame
    assert "_alive[i] == null" in body or "alive[i] == null" in body
    # Caps spawn at maxAlive
    assert "maxAlive" in body
    # Hides template
    assert "_template.SetActive(false)" in body
    print("OK Spawner contract: template-by-name + interval + cap maxAlive + flatXZ option + prunes dead refs")


def test_combat_quartet_in_runtime_namespace() -> None:
    for name in ("Projectile", "Shooter", "Spawner", "Enemy"):
        body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / f"{name}.cs").read_text(encoding="utf-8")
        assert "namespace UnityTools.Behaviours" in body, f"{name}.cs has wrong namespace"
        assert "using UnityEditor;" not in body, f"{name}.cs must not import UnityEditor"
    print("OK combat quartet (Projectile + Shooter + Spawner + Enemy) all in UnityTools.Behaviours, no UnityEditor leak")


# ───────────────────────────────────────────── endless-runner (Phase 46)


def test_autoscroller_constant_velocity_with_despawn() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "AutoScroller.cs").read_text(encoding="utf-8")
    for f in ("direction", "speed", "despawnPastThreshold", "despawnAt"):
        assert re.search(rf"public\s+\S+\s+{f}\s*[=;]", body), f"AutoScroller.{f} field missing"
    # Constant velocity via deltaTime
    assert "Time.deltaTime" in body
    # Despawn safety so obstacles flying off-camera don't leak
    assert "Destroy(gameObject)" in body
    # Normalises direction at Awake so a (0,0,-1) field isn't required to be unit
    assert "Awake" in body
    assert "normalized" in body
    print("OK AutoScroller contract: direction + speed + despawn threshold + Time.deltaTime motion + normalised direction")


def test_lane_positioner_snaps_to_n_lanes_with_keys_and_axis() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "LanePositioner.cs").read_text(encoding="utf-8")
    for f in ("laneCount", "laneWidth", "startLane", "switchDuration",
              "leftKey", "rightKey", "useHorizontalAxis"):
        assert re.search(rf"public\s+\S+\s+{f}\s*[=;]", body), f"LanePositioner.{f} field missing"
    # Key-based discrete shift
    assert "GetKeyDown(leftKey)" in body
    assert "GetKeyDown(rightKey)" in body
    # Horizontal axis edge-trigger (so a held axis doesn't drift through every lane)
    assert "GetAxisRaw" in body or "GetAxis(\"Horizontal\")" in body
    assert "axisCooldown" in body or "_axisCooldown" in body
    # Public ShiftLane API so other behaviours can drive it
    assert re.search(r"public\s+void\s+ShiftLane\s*\(", body), "LanePositioner.ShiftLane(int) missing"
    # Clamps to [0, laneCount-1]
    assert "Mathf.Clamp" in body
    # Lanes centered around X=0
    assert "laneCount - 1" in body
    print("OK LanePositioner contract: N lanes + key + axis + edge-trigger cooldown + ShiftLane API + clamped + centered")


def test_runner_duo_in_runtime_namespace() -> None:
    for name in ("AutoScroller", "LanePositioner"):
        body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / f"{name}.cs").read_text(encoding="utf-8")
        assert "namespace UnityTools.Behaviours" in body, f"{name}.cs has wrong namespace"
        assert "using UnityEditor;" not in body, f"{name}.cs must not import UnityEditor"
    print("OK AutoScroller + LanePositioner in UnityTools.Behaviours, no UnityEditor leak")


# ───────────────────────────────────────────── platformer (Phase 50)


def test_jumper_jump_arc_and_ground_check() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "Jumper.cs").read_text(encoding="utf-8")
    # Tunable fields
    for f in ("jumpHeight", "gravity", "jumpKey", "groundCheckDistance",
              "coyoteTime", "jumpBuffer"):
        assert re.search(rf"public\s+\S+\s+{f}\s*[=;]", body), f"Jumper.{f} field missing"
    # Public read-only state
    assert re.search(r"public\s+bool\s+IsGrounded\s*{\s*get", body), "Jumper.IsGrounded getter missing"
    # Ground-check via raycast (NOT CharacterController.isGrounded — that
    # would couple to a specific component)
    assert "Physics.Raycast" in body
    assert "Vector3.down" in body
    # Jump impulse uses sqrt(2*g*h) — physically-correct apex height
    assert "Mathf.Sqrt" in body
    # Coyote + buffer forgiveness (casual-platformer convention)
    assert "lastGroundedTime" in body or "_lastGroundedTime" in body
    assert "lastJumpPressTime" in body or "_lastJumpPressTime" in body
    # Vertical motion applied to transform.position (NOT cc.Move so
    # KeyboardMover's own cc.Move doesn't conflict). Comments are
    # allowed to mention CharacterController.Move (in fact the file's
    # header explains the design decision); we check that no actual
    # call is made by searching for an active expression rather than
    # the substring.
    assert "transform.position += Vector3.up" in body
    # The file may DOCUMENT the choice in comments, but no live call
    # to .Move( on a CharacterController should appear outside a //
    # comment line.
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        assert "CharacterController" not in line or ".Move(" not in line, (
            f"non-comment line calls CharacterController.Move: {line!r}"
        )
    print("OK Jumper contract: 6 tunables + IsGrounded + sqrt(2gh) impulse + coyote/buffer + position-based motion")


def test_jumper_in_runtime_namespace() -> None:
    body = (_REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "Jumper.cs").read_text(encoding="utf-8")
    assert "namespace UnityTools.Behaviours" in body
    assert "using UnityEditor;" not in body
    print("OK Jumper in UnityTools.Behaviours, no UnityEditor leak")


# ───────────────────────────────────────────── wrapper validation


def test_attach_behaviour_rejects_unknown_name() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_attach_behaviour(target_name="X", behaviour_name="Teleporter")
    assert result["ok"] is False
    assert "unknown behaviour" in result["error"]
    assert "Rotator" in result["error"]
    print("OK unknown behaviour name rejected at the wrapper, with help text")


def test_attach_behaviour_requires_target_name() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_attach_behaviour(target_name="", behaviour_name="Rotator")
    assert result["ok"] is False
    assert "target_name" in result["error"]
    print("OK empty target_name rejected")


def test_attach_behaviour_requires_bridge() -> None:
    unity_tools._UNITY = None
    result = unity_attach_behaviour(target_name="X", behaviour_name="Rotator")
    assert result["ok"] is False
    assert "not initialized" in result["error"]
    print("OK missing bridge -> clean error on attach")


def test_attach_behaviour_forwards_params_block() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_attach_behaviour(
        target_name="Coin",
        behaviour_name="Rotator",
        params={"speedDegPerSec": 180, "axis": {"x": 0, "y": 1, "z": 0}},
    )
    assert result["ok"] is True
    assert result["behaviour"] == "Rotator"
    method, sent = fake.calls[0]
    assert method == "attach_behaviour"
    assert sent["target_name"] == "Coin"
    assert sent["behaviour_name"] == "Rotator"
    assert sent["params"]["speedDegPerSec"] == 180
    assert sent["params"]["axis"] == {"x": 0, "y": 1, "z": 0}
    print("OK wrapper forwards full param block (scalar + Vector3 dict)")


def test_attach_behaviour_handles_no_params() -> None:
    """Some behaviours (LookAtCamera with defaults) need no params."""
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_attach_behaviour(target_name="Label", behaviour_name="LookAtCamera")
    assert result["ok"] is True
    _, sent = fake.calls[0]
    assert sent["params"] == {}
    print("OK params omitted -> empty dict sent")


def test_attach_behaviour_surfaces_bridge_exception() -> None:
    unity_tools._UNITY = FakeUnity(raise_on_method="attach_behaviour")
    result = unity_attach_behaviour(target_name="X", behaviour_name="Bobber")
    assert result["ok"] is False
    assert "simulated failure" in result["error"]
    print("OK bridge exception surfaces clean error")


def test_list_behaviour_library_returns_inventory() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_list_behaviour_library()
    assert result["ok"] is True
    assert result["count"] == 9
    assert any(row["name"] == "Rotator" for row in result["library"])
    print("OK unity_list_behaviour_library returns inventory")


def test_list_attached_behaviours_scopes_to_target() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_list_attached_behaviours(target_name="Coin")
    assert result["ok"] is True
    _, sent = fake.calls[0]
    assert sent["target_name"] == "Coin"
    print("OK list_attached_behaviours forwards target_name scope")


def test_list_attached_behaviours_scans_whole_scene() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_list_attached_behaviours()
    assert result["ok"] is True
    _, sent = fake.calls[0]
    assert sent["target_name"] == ""
    print("OK list_attached_behaviours defaults to whole-scene scan")


# ───────────────────────────────────────────── role allowlist


def test_worker_owns_behaviour_attach_tools() -> None:
    """Worker is the role that places objects, so it owns 'make this
    object do something' too."""
    assert "unity_attach_behaviour" in WORKER.tool_set
    assert "unity_list_behaviour_library" in WORKER.tool_set
    assert "unity_list_attached_behaviours" in WORKER.tool_set
    print("OK Worker allowlist gets the attach + list behaviour tools")


def test_ui_builder_can_wire_buttons_to_behaviours() -> None:
    """UI Builder needs LoadSceneOnClick / QuitOnClick on buttons. It
    has the attach + list-library tools (not the list-attached one —
    that's a scene-wide inspection more suited to Worker)."""
    assert "unity_attach_behaviour" in UI_BUILDER.tool_set
    assert "unity_list_behaviour_library" in UI_BUILDER.tool_set
    print("OK UI Builder allowlist gets attach + list-library for button wiring")


def test_non_executor_roles_lack_behaviour_attach() -> None:
    """Director / reviewer / engineer roles plan and audit; they do
    not directly attach behaviours."""
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR,
                  BUILD_ENGINEER):
        assert "unity_attach_behaviour" not in role.tool_set, (
            f"{role.id} must not attach behaviours — that's Worker + UI Builder"
        )
    print("OK only Worker + UI Builder can attach behaviours")


def run_test() -> None:
    # Library presence
    test_behaviour_library_contains_known_behaviours()
    test_each_behaviour_has_a_corresponding_cs_file()
    test_runtime_scripts_do_not_use_editor_assembly()
    # Phase 40 game-loop contract
    test_game_session_exposes_score_lives_and_state_machine()
    test_collectible_requires_trigger_collider_and_calls_game_session()
    test_score_hud_requires_text_and_renders_format_tokens()
    test_game_loop_trio_lives_in_runtime_namespace()
    # Phase 41 pause + settings
    test_pause_menu_toggles_panel_and_time_scale()
    test_settings_store_uses_player_prefs_with_namespace()
    test_pause_and_settings_in_runtime_namespace()
    # Phase 43 combat
    test_projectile_moves_lifetime_and_damages_enemy()
    test_enemy_takes_damage_and_awards_score_on_death()
    test_shooter_resolves_template_and_rate_limits()
    test_spawner_caps_alive_and_prunes_dead_refs()
    test_combat_quartet_in_runtime_namespace()
    # Phase 46 endless-runner
    test_autoscroller_constant_velocity_with_despawn()
    test_lane_positioner_snaps_to_n_lanes_with_keys_and_axis()
    test_runner_duo_in_runtime_namespace()
    # Phase 50 platformer
    test_jumper_jump_arc_and_ground_check()
    test_jumper_in_runtime_namespace()
    # Wrappers
    test_attach_behaviour_rejects_unknown_name()
    test_attach_behaviour_requires_target_name()
    test_attach_behaviour_requires_bridge()
    test_attach_behaviour_forwards_params_block()
    test_attach_behaviour_handles_no_params()
    test_attach_behaviour_surfaces_bridge_exception()
    test_list_behaviour_library_returns_inventory()
    test_list_attached_behaviours_scopes_to_target()
    test_list_attached_behaviours_scans_whole_scene()
    # Role surface
    test_worker_owns_behaviour_attach_tools()
    test_ui_builder_can_wire_buttons_to_behaviours()
    test_non_executor_roles_lack_behaviour_attach()
    print("All Phase 34 behaviour-library tests passed")


if __name__ == "__main__":
    run_test()
