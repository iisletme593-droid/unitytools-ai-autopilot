"""P13 (cycle 68): procedural sound cue -- audio, done HONESTLY.

The studio is generate-only: it never imports real audio assets, so a sound behaviour
must NOT reference a fake AudioClip or Resources.Load("clip"). `sound` (AutopilotSound)
is honest about this -- it BUILDS its clip at runtime with AudioClip.Create + a
deterministic sine wave (Mathf.Sin, no Math.random), self-contained and reproducible.
Decoupled: fired via SendMessage("PlayCue") (optionally with a frequency).
Pure ASCII C# source; no recompile triggered here.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)


def test_sound_source():
    s = generate_behaviour_script("sound")
    assert s["ok"] is True and s["class_name"] == "AutopilotSound"
    src = s["source"]
    assert "public void PlayCue()" in src                       # decoupled trigger
    assert "public void PlayCue(float freq)" in src             # pitch override
    assert "frequency" in src and "duration" in src             # configurable cue


def test_sound_is_built_procedurally_not_a_fake_asset():
    # the honesty contract: build the clip at runtime, never pretend to own one
    src = generate_behaviour_script("sound")["source"]
    assert "AudioClip.Create(" in src                           # runtime-generated clip
    assert "Mathf.Sin(" in src                                  # deterministic sine wave
    assert "SetData(" in src                                    # fills the samples
    assert "Resources.Load" not in src                          # NOT a fake/missing asset
    assert "Math.random" not in src.lower()                     # deterministic


def test_sound_is_decoupled_via_sendmessage():
    # other behaviours fire it without a hard type reference; the docstring documents it
    src = generate_behaviour_script("sound")["source"]
    assert 'SendMessage("PlayCue"' in src                       # the intended trigger
    assert "PlayOneShot(" in src                                # plays the built clip


def test_sound_is_deterministic_no_randomness():
    src = generate_behaviour_script("sound")["source"]
    for forbidden in ("Random.", "Random.Range", "DateTime", "System.Random"):
        assert forbidden not in src


def test_sound_is_pure_ascii_and_balanced():
    src = generate_behaviour_script("sound")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}")
    assert src.count("(") == src.count(")")
    assert "__" not in src                                       # all placeholders substituted


@pytest.mark.parametrize("alias", ["ses", "sound", "audio", "beep", "sfx", "sescue"])
def test_sound_aliases(alias):
    assert normalize_behaviour(alias) == "sound"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotSound"


def test_sound_registered():
    assert "sound" in NEEDS_SCRIPT
    assert "sound" in _SCRIPT_TEMPLATES
