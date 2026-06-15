"""P7 (cycle 24): spawner / wave behaviour — timed object generation.

AutopilotSpawner: InvokeRepeating spawns physics cubes at an interval up to maxCount —
the basis for waves / endless generation.
"""
import pytest

from unitytools.core.gameplay import generate_behaviour_script, normalize_behaviour


def test_spawner_source():
    s = generate_behaviour_script("spawner")
    assert s["class_name"] == "AutopilotSpawner"
    src = s["source"]
    assert "InvokeRepeating" in src
    assert "CreatePrimitive(PrimitiveType.Cube)" in src
    assert "maxCount" in src and "interval" in src
    assert "CancelInvoke" in src
    assert src.count("{") == src.count("}")          # compilable shape


def test_spawner_custom_interval():
    src = generate_behaviour_script("spawner", speed=0.5)["source"]
    assert "interval = 0.5f" in src


@pytest.mark.parametrize("alias", ["spawn", "wave", "dalga", "uretici"])
def test_spawner_aliases(alias):
    assert normalize_behaviour(alias) == "spawner"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotSpawner"
