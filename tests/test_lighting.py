"""P1: studio 3-point lighting rig math."""
import math

from unitytools.core.lighting import compute_studio_lighting_rig


def test_three_lights_with_roles():
    rig = compute_studio_lighting_rig()
    assert len(rig) == 3
    assert {l["role"] for l in rig} == {"key", "fill", "rim"}


def test_key_is_brightest():
    rig = compute_studio_lighting_rig(key_intensity=1.0)
    by_role = {l["role"]: l for l in rig}
    assert by_role["key"]["intensity"] > by_role["fill"]["intensity"]
    assert by_role["key"]["intensity"] >= by_role["rim"]["intensity"]
    assert by_role["rim"]["intensity"] > by_role["fill"]["intensity"]


def test_key_at_distance_from_target():
    rig = compute_studio_lighting_rig(target=(0.0, 0.0, 0.0), distance=6.0)
    key = next(l for l in rig if l["role"] == "key")
    x, _y, z = key["position"]
    assert abs(math.hypot(x, z) - 6.0) < 1e-6


def test_target_offset_applied():
    rig = compute_studio_lighting_rig(target=(10.0, 2.0, -5.0))
    assert all(l["look_at"] == (10.0, 2.0, -5.0) for l in rig)
