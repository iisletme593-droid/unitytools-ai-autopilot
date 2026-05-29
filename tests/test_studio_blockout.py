"""Phase 22 tests: studio_create_blockout_group + Worker tool surface.

Validates the new one-call layout helper end-to-end with a fake Unity
bridge that records every RPC. Each layout (line / grid / circle /
cluster) gets geometry assertions so a regression in coordinate math
is caught at test time.
"""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    StudioPaths,
    StudioState,
    WORKER,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import studio_create_blockout_group


class FakeBridge:
    """Records every method+params; returns success for create + color."""

    def __init__(self, connected: bool = True, fail_color: bool = False):
        self.connected = connected
        self.fail_color = fail_color
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self) -> bool:
        return self.connected

    def call(self, method, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((method, params))
        if method == "set_material_color" and self.fail_color:
            raise RuntimeError("simulated color failure")
        if method == "create_primitive":
            return {"ok": True, "name": params.get("name")}
        if method == "set_material_color":
            return {"ok": True}
        raise AssertionError(f"unexpected method: {method}")


def _fresh_studio() -> StudioState:
    tmp = Path(tempfile.mkdtemp(prefix="block-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state


# ─────────────────────────────────────────── layout geometry


def test_line_layout_centers_on_origin() -> None:
    state = _fresh_studio()
    bridge = FakeBridge()
    init_studio_unity(bridge)

    result = studio_create_blockout_group(
        name_prefix="Wall",
        primitive_type="Cube",
        count=4,
        layout="line",
        spacing=2.0,
        origin_x=0,
        origin_y=0,
        origin_z=0,
    )
    assert result["ok"]
    assert result["count"] == 4
    xs = [o["position"]["x"] for o in result["objects"]]
    # 4 items, spacing 2 -> -3, -1, 1, 3
    assert xs == [-3.0, -1.0, 1.0, 3.0]
    assert all(o["position"]["y"] == 0 for o in result["objects"])
    assert all(o["position"]["z"] == 0 for o in result["objects"])
    print("OK line layout centered on origin")


def test_grid_layout_fills_nxn_square() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge())

    result = studio_create_blockout_group(
        name_prefix="Tile",
        count=4,
        layout="grid",
        spacing=3.0,
        origin_x=0,
        origin_z=0,
    )
    assert result["count"] == 4
    # 2x2 grid, spacing 3 -> positions at (+-1.5, +-1.5)
    coords = sorted((o["position"]["x"], o["position"]["z"]) for o in result["objects"])
    assert coords == [(-1.5, -1.5), (-1.5, 1.5), (1.5, -1.5), (1.5, 1.5)]
    print("OK grid layout fills NxN square")


def test_grid_layout_handles_non_square_counts() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge())
    result = studio_create_blockout_group(name_prefix="X", count=5, layout="grid", spacing=1.0)
    assert result["count"] == 5  # 5 placed in a 3x3 (side rounded up); 4 cells empty
    assert len(result["objects"]) == 5
    print("OK grid handles non-square counts (rounds side up)")


def test_circle_layout_places_on_ring() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge())
    result = studio_create_blockout_group(
        name_prefix="Ring",
        count=6,
        layout="circle",
        spacing=4.0,  # radius
        origin_x=10,
        origin_z=20,
    )
    assert result["count"] == 6
    # Every object should be exactly radius=4 from (10, 20)
    for o in result["objects"]:
        dx = o["position"]["x"] - 10
        dz = o["position"]["z"] - 20
        radius = math.sqrt(dx * dx + dz * dz)
        assert abs(radius - 4.0) < 1e-6, f"point not on ring: {o}"
    print("OK circle layout puts every point exactly on the ring")


def test_cluster_layout_is_deterministic_per_prefix() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge())
    a = studio_create_blockout_group(name_prefix="Same", count=5, layout="cluster", spacing=10.0)
    init_studio_unity(FakeBridge())  # reset bridge so position-only equality is fair
    b = studio_create_blockout_group(name_prefix="Same", count=5, layout="cluster", spacing=10.0)
    coords_a = [(o["position"]["x"], o["position"]["z"]) for o in a["objects"]]
    coords_b = [(o["position"]["x"], o["position"]["z"]) for o in b["objects"]]
    assert coords_a == coords_b, "cluster layout must be deterministic for same prefix"

    # Different prefix produces different scatter
    init_studio_unity(FakeBridge())
    c = studio_create_blockout_group(name_prefix="Other", count=5, layout="cluster", spacing=10.0)
    coords_c = [(o["position"]["x"], o["position"]["z"]) for o in c["objects"]]
    assert coords_a != coords_c
    print("OK cluster layout is deterministic per prefix (different prefix -> different scatter)")


# ─────────────────────────────────────────── bridge interactions


def test_create_blockout_emits_create_then_color_per_object() -> None:
    state = _fresh_studio()
    bridge = FakeBridge()
    init_studio_unity(bridge)
    studio_create_blockout_group(name_prefix="Tower", count=3, layout="line")
    methods = [m for m, _ in bridge.calls]
    # Per object: create + color = 6 calls for 3 objects
    assert methods == ["create_primitive", "set_material_color"] * 3
    # Names sequential
    create_names = [p["name"] for m, p in bridge.calls if m == "create_primitive"]
    assert create_names == ["Tower_00", "Tower_01", "Tower_02"]
    print("OK each object gets create + color in order")


def test_create_blockout_continues_when_color_fails() -> None:
    state = _fresh_studio()
    bridge = FakeBridge(fail_color=True)
    init_studio_unity(bridge)
    result = studio_create_blockout_group(name_prefix="X", count=2, layout="line")
    # Objects still created
    assert result["count"] == 2
    # But errors recorded for each color call
    assert len(result["errors"]) == 2
    assert all("color" in e for e in result["errors"])
    print("OK color failures collected as errors, creation still succeeds")


# ─────────────────────────────────────────── validation


def test_invalid_layout_rejected() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge())
    result = studio_create_blockout_group(name_prefix="X", count=2, layout="spiral")
    assert result["ok"] is False
    assert "Unknown layout" in result["error"]
    print("OK invalid layout rejected")


def test_invalid_primitive_type_rejected() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge())
    result = studio_create_blockout_group(name_prefix="X", count=2, primitive_type="Pyramid")
    assert result["ok"] is False
    assert "primitive_type" in result["error"]
    print("OK invalid primitive_type rejected")


def test_count_bounds_enforced() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge())
    too_few = studio_create_blockout_group(name_prefix="X", count=0, layout="line")
    assert too_few["ok"] is False and "count" in too_few["error"]
    too_many = studio_create_blockout_group(name_prefix="X", count=51, layout="line")
    assert too_many["ok"] is False and "capped" in too_many["error"]
    print("OK count bounds enforced (>=1 and <=50)")


def test_disconnected_bridge_reports_error() -> None:
    state = _fresh_studio()
    init_studio_unity(FakeBridge(connected=False))
    result = studio_create_blockout_group(name_prefix="X", count=2, layout="line")
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected bridge surfaces clean error")


def test_worker_allowlist_includes_blockout_helper() -> None:
    assert "studio_create_blockout_group" in WORKER.tool_set
    print("OK Worker allowlist includes studio_create_blockout_group")


def run_test() -> None:
    test_line_layout_centers_on_origin()
    test_grid_layout_fills_nxn_square()
    test_grid_layout_handles_non_square_counts()
    test_circle_layout_places_on_ring()
    test_cluster_layout_is_deterministic_per_prefix()
    test_create_blockout_emits_create_then_color_per_object()
    test_create_blockout_continues_when_color_fails()
    test_invalid_layout_rejected()
    test_invalid_primitive_type_rejected()
    test_count_bounds_enforced()
    test_disconnected_bridge_reports_error()
    test_worker_allowlist_includes_blockout_helper()
    print("All Phase 22 blockout tests passed")


if __name__ == "__main__":
    run_test()
