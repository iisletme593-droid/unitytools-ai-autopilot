"""Phase 27 tests: Audio Engineer role + audio engine tools.

Covers: import + attach happy path, bridge / connection guards,
suffix + range validation, role allowlist, dispatch routing.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    ART_DIRECTOR,
    AUDIO_DIRECTOR,
    AUDIO_ENGINEER,
    DESIGNER,
    DISPATCH_MAP,
    StudioPaths,
    StudioState,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import (
    studio_unity_attach_audio_source,
    studio_unity_import_audio,
)


class FakeUnity:
    """Records bridge calls and lets each test choose a failure mode."""

    def __init__(
        self,
        connected: bool = True,
        import_ok: bool = True,
        attach_ok: bool = True,
    ):
        self._connected = connected
        self._import_ok = import_ok
        self._attach_ok = attach_ok
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self):
        return self._connected

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if method == "import_asset":
            if not self._import_ok:
                raise RuntimeError("simulated import failure")
            return {
                "ok": True,
                "imported_object_paths": [
                    (params.get("destination") or "Assets/Studio/Audio")
                    + "/"
                    + Path(params["source_path"]).name
                ],
            }
        if method == "set_audio_source":
            if not self._attach_ok:
                return {"ok": False, "error": "object not found"}
            return {
                "ok": True,
                "name": params["name"],
                "clip_path": params.get("clip_path", ""),
                "loop": bool(params.get("loop", False)),
                "spatial_blend": float(params.get("spatial_blend", 0.0)),
            }
        raise AssertionError(f"unexpected bridge method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="audio-eng-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _make_audio_source(tmp: Path, name: str = "clip.wav") -> Path:
    p = tmp / name
    p.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")  # not a real WAV; just bytes
    return p


# ───────────────────────────────────────────── import: happy + validation


def test_import_audio_happy_path() -> None:
    state, tmp = _fresh_studio()
    fake = FakeUnity()
    init_studio_unity(fake)
    src = _make_audio_source(tmp, "ambient_pad.wav")
    result = studio_unity_import_audio(
        source_path=str(src),
        unity_destination="Assets/Studio/Audio",
    )
    assert result["ok"] is True
    assert result["source"] == str(src)
    assert result["destination"] == "Assets/Studio/Audio"
    assert result["imported_paths"]
    # Bridge saw the right call
    method, params = fake.calls[0]
    assert method == "import_asset"
    assert params["source_path"] == str(src)
    assert params["destination"] == "Assets/Studio/Audio"
    assert params["replace_existing"] is True
    print("OK studio_unity_import_audio: wav imports through bridge")


def test_import_audio_strips_trailing_slash() -> None:
    state, tmp = _fresh_studio()
    fake = FakeUnity()
    init_studio_unity(fake)
    src = _make_audio_source(tmp, "stinger.ogg")
    result = studio_unity_import_audio(
        source_path=str(src),
        unity_destination="Assets/Studio/Audio/",
    )
    assert result["ok"] is True
    # No trailing slash leaks into Unity
    _, params = fake.calls[0]
    assert params["destination"] == "Assets/Studio/Audio"
    print("OK unity_destination trailing slash stripped")


def test_import_audio_rejects_bad_extension() -> None:
    state, tmp = _fresh_studio()
    init_studio_unity(FakeUnity())
    bad = tmp / "music.mp4"
    bad.write_bytes(b"x")
    result = studio_unity_import_audio(source_path=str(bad))
    assert result["ok"] is False
    assert "Unsupported audio extension" in result["error"]
    print("OK non-audio extensions rejected")


def test_import_audio_rejects_missing_file() -> None:
    state, tmp = _fresh_studio()
    init_studio_unity(FakeUnity())
    ghost = tmp / "missing.wav"
    result = studio_unity_import_audio(source_path=str(ghost))
    assert result["ok"] is False
    assert "not found" in result["error"]
    print("OK missing audio source surfaces clean error")


def test_import_audio_requires_bridge_injection() -> None:
    state, tmp = _fresh_studio()
    import unitytools.studio.tools as st
    st._UNITY = None
    src = _make_audio_source(tmp)
    result = studio_unity_import_audio(source_path=str(src))
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing Unity bridge -> clean error on import")


def test_import_audio_requires_connection() -> None:
    state, tmp = _fresh_studio()
    init_studio_unity(FakeUnity(connected=False))
    src = _make_audio_source(tmp)
    result = studio_unity_import_audio(source_path=str(src))
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected Unity -> clean error on import")


def test_import_audio_surfaces_bridge_exception() -> None:
    state, tmp = _fresh_studio()
    init_studio_unity(FakeUnity(import_ok=False))
    src = _make_audio_source(tmp)
    result = studio_unity_import_audio(source_path=str(src))
    assert result["ok"] is False
    assert "simulated import failure" in result["error"]
    print("OK bridge import failure surfaces in error")


# ───────────────────────────────────────────── attach: happy + validation


def test_attach_audio_source_happy_path() -> None:
    state, _ = _fresh_studio()
    fake = FakeUnity()
    init_studio_unity(fake)
    result = studio_unity_attach_audio_source(
        target_name="AmbientEmitter_North",
        clip_path="Assets/Studio/Audio/ambient_pad.wav",
        loop=True,
        play_on_awake=True,
        volume=0.8,
        pitch=1.0,
        spatial_blend=1.0,
        min_distance=1.0,
        max_distance=25.0,
    )
    assert result["ok"] is True
    assert result["target"] == "AmbientEmitter_North"
    method, params = fake.calls[0]
    assert method == "set_audio_source"
    assert params["name"] == "AmbientEmitter_North"
    assert params["loop"] is True
    assert params["volume"] == 0.8
    assert params["spatial_blend"] == 1.0
    assert params["clip_path"] == "Assets/Studio/Audio/ambient_pad.wav"
    print("OK attach_audio_source forwards full param block to bridge")


def test_attach_audio_source_omits_clip_when_blank() -> None:
    """Empty clip_path means 'leave clip alone' — do not send the field."""
    state, _ = _fresh_studio()
    fake = FakeUnity()
    init_studio_unity(fake)
    result = studio_unity_attach_audio_source(
        target_name="Speaker",
        clip_path="",
        loop=False,
    )
    assert result["ok"] is True
    _, params = fake.calls[0]
    assert "clip_path" not in params, "blank clip_path must be omitted, not sent as ''"
    print("OK blank clip_path is not forwarded")


def test_attach_audio_source_requires_target_name() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity())
    result = studio_unity_attach_audio_source(target_name="")
    assert result["ok"] is False
    assert "target_name" in result["error"]
    print("OK empty target_name rejected")


def test_attach_audio_source_validates_volume_range() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity())
    too_loud = studio_unity_attach_audio_source(target_name="X", volume=1.5)
    assert too_loud["ok"] is False
    assert "volume" in too_loud["error"]
    negative = studio_unity_attach_audio_source(target_name="X", volume=-0.1)
    assert negative["ok"] is False
    assert "volume" in negative["error"]
    print("OK volume range [0,1] enforced")


def test_attach_audio_source_validates_spatial_blend_range() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity())
    result = studio_unity_attach_audio_source(target_name="X", spatial_blend=2.0)
    assert result["ok"] is False
    assert "spatial_blend" in result["error"]
    print("OK spatial_blend range [0,1] enforced")


def test_attach_audio_source_requires_bridge() -> None:
    state, _ = _fresh_studio()
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_unity_attach_audio_source(target_name="X")
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing Unity bridge -> clean error on attach")


def test_attach_audio_source_requires_connection() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(connected=False))
    result = studio_unity_attach_audio_source(target_name="X")
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected Unity -> clean error on attach")


def test_attach_audio_source_surfaces_unity_failure() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(attach_ok=False))
    result = studio_unity_attach_audio_source(target_name="Ghost")
    assert result["ok"] is False
    assert "set_audio_source failure" in result["error"]
    print("OK Unity reporting ok=false surfaces failure")


# ───────────────────────────────────────────── role allowlist


def test_audio_engineer_owns_engine_tools() -> None:
    assert "studio_unity_import_audio" in AUDIO_ENGINEER.tool_set
    assert "studio_unity_attach_audio_source" in AUDIO_ENGINEER.tool_set
    assert "unity_create_scene_snapshot" in AUDIO_ENGINEER.tool_set
    assert "unity_find_scene_objects" in AUDIO_ENGINEER.tool_set
    assert "unity_save_scene" in AUDIO_ENGINEER.tool_set
    # Lifecycle
    assert "studio_update_task_status" in AUDIO_ENGINEER.tool_set
    # Reads the brief; does NOT write it
    assert "studio_read_audio_brief" in AUDIO_ENGINEER.tool_set
    assert "studio_write_audio_brief" not in AUDIO_ENGINEER.tool_set
    # Cannot edit GDD / Art Bible
    assert "studio_write_gdd" not in AUDIO_ENGINEER.tool_set
    assert "studio_write_art_bible" not in AUDIO_ENGINEER.tool_set
    # Cannot place / mutate scene objects beyond AudioSource
    assert "unity_create_primitive" not in AUDIO_ENGINEER.tool_set
    assert "unity_set_position" not in AUDIO_ENGINEER.tool_set
    print("OK Audio Engineer allowlist: import+attach+snapshot+save+lifecycle, no scene mutation, no doc writes")


def test_other_roles_lack_audio_engine_tools() -> None:
    """Audio engine tools belong to AUDIO_ENGINEER only — not the
    Director (doc-only) or unrelated roles."""
    for role in (AUDIO_DIRECTOR, ART_DIRECTOR, DESIGNER):
        assert "studio_unity_import_audio" not in role.tool_set, f"{role.id} must not import audio"
        assert "studio_unity_attach_audio_source" not in role.tool_set, f"{role.id} must not attach audio sources"
    print("OK only Audio Engineer can touch the audio engine tools")


def test_audio_engineer_needs_engine_no_vision() -> None:
    """Engine-aware role (Unity), vision-free (no compare_to_reference)."""
    assert AUDIO_ENGINEER.needs_engine is True
    assert AUDIO_ENGINEER.needs_vision is False
    print("OK Audio Engineer needs engine, not vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_audio_engineer_to_self() -> None:
    assert DISPATCH_MAP["audio_engineer"] == "audio_engineer"
    print("OK DISPATCH_MAP[audio_engineer] -> audio_engineer")


def test_existing_routes_unchanged() -> None:
    """Adding the audio_engineer rule must not disturb earlier ones."""
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after audio_engineer addition")


def run_test() -> None:
    # Import path
    test_import_audio_happy_path()
    test_import_audio_strips_trailing_slash()
    test_import_audio_rejects_bad_extension()
    test_import_audio_rejects_missing_file()
    test_import_audio_requires_bridge_injection()
    test_import_audio_requires_connection()
    test_import_audio_surfaces_bridge_exception()
    # Attach path
    test_attach_audio_source_happy_path()
    test_attach_audio_source_omits_clip_when_blank()
    test_attach_audio_source_requires_target_name()
    test_attach_audio_source_validates_volume_range()
    test_attach_audio_source_validates_spatial_blend_range()
    test_attach_audio_source_requires_bridge()
    test_attach_audio_source_requires_connection()
    test_attach_audio_source_surfaces_unity_failure()
    # Role allowlist
    test_audio_engineer_owns_engine_tools()
    test_other_roles_lack_audio_engine_tools()
    test_audio_engineer_needs_engine_no_vision()
    # Dispatch
    test_dispatch_map_routes_audio_engineer_to_self()
    test_existing_routes_unchanged()
    print("All Phase 27 audio engineer tests passed")


if __name__ == "__main__":
    run_test()
