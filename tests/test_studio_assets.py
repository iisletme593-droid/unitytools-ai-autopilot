"""Phase 25 tests: studio_generate_prop_asset + Worker chain.

Validates: prop_type validation, FBX path conventions, regression
log emission, optional Unity-import chain, Worker allowlist surface,
and error paths (Blender missing, bridge failure, FBX not produced).
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    StudioPaths,
    StudioState,
    WORKER,
    init_studio_blender,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import studio_generate_prop_asset


@dataclass
class FakeResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0


class FakeBlender:
    """Fakes BlenderBridge.generate_prop by writing a dummy FBX file."""

    SUPPORTED_PROP_TYPES = ("rock", "crate", "pillar", "column")

    def __init__(self, available: bool = True, fail: bool = False, skip_write: bool = False):
        self._available = available
        self._fail = fail
        self._skip_write = skip_write
        self.calls: list[dict] = []

    def is_available(self) -> bool:
        return self._available

    def generate_prop(self, prop_type, output_path, seed=0, scale=1.0, timeout=120):
        self.calls.append(
            {"prop_type": prop_type, "output": str(output_path), "seed": seed, "scale": scale}
        )
        if self._fail:
            return FakeResult(success=False, return_code=3, stderr="simulated build failure")
        # Optionally simulate "success but no file" (script bug)
        if not self._skip_write:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            # 24-byte FBX-ish header is enough for size assertions
            Path(output_path).write_bytes(b"FAKE_FBX_HEADER_AND_DATA")
        return FakeResult(success=True, stdout="PROP_GENERATED: " + str(output_path))


class FakeUnity:
    """Records import_asset calls."""

    def __init__(self, connected: bool = True, import_ok: bool = True):
        self._connected = connected
        self._import_ok = import_ok
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self):
        return self._connected

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if method == "import_asset":
            if not self._import_ok:
                raise RuntimeError("simulated import failure")
            return {"ok": True, "imported_object_paths": [params["destination"] + "/X.fbx"]}
        raise AssertionError(f"unexpected method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="assetgen-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── happy path


def test_rock_generates_under_studio_assets_generated() -> None:
    state, _ = _fresh_studio()
    fake = FakeBlender()
    init_studio_blender(fake)
    result = studio_generate_prop_asset(prop_type="rock", name="boulder_01", seed=42)
    assert result["ok"] is True
    assert result["prop_type"] == "rock"
    assert result["name"] == "boulder_01"
    assert result["seed"] == 42
    assert result["size_bytes"] > 0
    # FBX landed under studio/assets/generated/
    fbx_path = Path(result["fbx_path"])
    assert fbx_path.exists()
    assert fbx_path.parent == state.paths.root / "assets" / "generated"
    assert fbx_path.suffix == ".fbx"
    # Blender saw the right args
    assert len(fake.calls) == 1
    assert fake.calls[0]["prop_type"] == "rock"
    assert fake.calls[0]["seed"] == 42
    print("OK rock prop generated under studio/assets/generated/")


def test_name_sanitised_and_default_falls_back() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender())
    # Slashes/spaces -> underscores
    a = studio_generate_prop_asset(prop_type="crate", name="my/weird name.fbx")
    assert "/" not in a["name"]
    assert a["name"]
    # Empty name -> fallback to prop_type + seed
    b = studio_generate_prop_asset(prop_type="pillar", name="", seed=7)
    assert b["name"] == "pillar_7"
    print("OK name sanitised + default fallback")


def test_regression_log_entry_written() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender())
    studio_generate_prop_asset(prop_type="column", name="palace_pillar", seed=1, scale=2.0)
    log_text = state.paths.qa_regression.read_text(encoding="utf-8").strip()
    rows = [json.loads(line) for line in log_text.splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "asset_generated"
    assert row["prop_type"] == "column"
    assert row["name"] == "palace_pillar"
    assert row["seed"] == 1
    assert row["size_bytes"] > 0
    print("OK regression log gets asset_generated row")


# ───────────────────────────────────────────── validation


def test_unknown_prop_type_rejected() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender())
    result = studio_generate_prop_asset(prop_type="dragon")
    assert result["ok"] is False
    assert "prop_type" in result["error"]
    print("OK unknown prop_type rejected")


def test_missing_blender_bridge_returns_error() -> None:
    state, _ = _fresh_studio()
    # No init_studio_blender call
    import unitytools.studio.tools as st
    st._BLENDER = None
    result = studio_generate_prop_asset(prop_type="rock")
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing bridge -> clean error")


def test_blender_unavailable_returns_error() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender(available=False))
    result = studio_generate_prop_asset(prop_type="rock")
    assert result["ok"] is False
    assert "Blender executable" in result["error"]
    print("OK unavailable Blender -> clean error")


def test_blender_failure_surfaces_stderr() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender(fail=True))
    result = studio_generate_prop_asset(prop_type="rock")
    assert result["ok"] is False
    assert "Blender generation failed" in result["error"]
    assert "simulated build failure" in result["error"]
    print("OK Blender RC>0 surfaces stderr tail")


def test_blender_success_but_no_file_returns_error() -> None:
    """Defensive: the Blender script might log PROP_GENERATED but the
    file might be missing (e.g. write permission issue). The tool must
    catch that, not blindly trust success=True."""
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender(skip_write=True))
    result = studio_generate_prop_asset(prop_type="rock")
    assert result["ok"] is False
    assert "FBX not at" in result["error"]
    print("OK success-but-no-file caught defensively")


# ───────────────────────────────────────────── optional Unity import


def test_import_into_unity_chains_when_bridge_present() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender())
    fake_unity = FakeUnity()
    init_studio_unity(fake_unity)
    result = studio_generate_prop_asset(
        prop_type="rock",
        name="boulder",
        seed=10,
        import_into_unity=True,
        unity_destination="Assets/MyProject/Rocks",
    )
    assert result["ok"] is True
    assert result["unity_import"]["ok"] is True
    # Bridge saw the import_asset call with the right params
    assert fake_unity.calls
    method, params = fake_unity.calls[0]
    assert method == "import_asset"
    assert params["destination"] == "Assets/MyProject/Rocks"
    assert params["source_path"].endswith("boulder.fbx")
    print("OK import_into_unity chain works")


def test_import_skipped_when_unity_disconnected() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender())
    init_studio_unity(FakeUnity(connected=False))
    result = studio_generate_prop_asset(
        prop_type="crate", name="box", import_into_unity=True
    )
    # Asset generation still succeeds; import section reports clean error
    assert result["ok"] is True
    assert result["unity_import"]["ok"] is False
    assert "not connected" in result["unity_import"]["error"].lower()
    print("OK disconnected Unity -> asset still generated, import skipped cleanly")


def test_import_skipped_when_no_unity_bridge() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender())
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_generate_prop_asset(prop_type="rock", import_into_unity=True)
    assert result["ok"] is True
    assert result["unity_import"]["ok"] is False
    assert "not injected" in result["unity_import"]["error"]
    print("OK no Unity bridge -> import_into_unity records clean error")


def test_import_failure_does_not_fail_asset_gen() -> None:
    state, _ = _fresh_studio()
    init_studio_blender(FakeBlender())
    init_studio_unity(FakeUnity(import_ok=False))
    result = studio_generate_prop_asset(
        prop_type="pillar", import_into_unity=True
    )
    # Asset gen succeeded even though import raised
    assert result["ok"] is True
    assert result["unity_import"]["ok"] is False
    print("OK import failure does not roll back asset generation")


# ───────────────────────────────────────────── role surface


def test_worker_allowlist_includes_generate_prop() -> None:
    assert "studio_generate_prop_asset" in WORKER.tool_set
    print("OK Worker allowlist includes studio_generate_prop_asset")


def run_test() -> None:
    test_rock_generates_under_studio_assets_generated()
    test_name_sanitised_and_default_falls_back()
    test_regression_log_entry_written()
    test_unknown_prop_type_rejected()
    test_missing_blender_bridge_returns_error()
    test_blender_unavailable_returns_error()
    test_blender_failure_surfaces_stderr()
    test_blender_success_but_no_file_returns_error()
    test_import_into_unity_chains_when_bridge_present()
    test_import_skipped_when_unity_disconnected()
    test_import_skipped_when_no_unity_bridge()
    test_import_failure_does_not_fail_asset_gen()
    test_worker_allowlist_includes_generate_prop()
    print("All Phase 25 asset-gen tests passed")


if __name__ == "__main__":
    run_test()
