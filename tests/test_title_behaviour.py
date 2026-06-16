"""P13 (cycle 66): title / start screen UI -- the game-feel bookend before play.

`title` (AutopilotTitle) draws the game title + "Press SPACE to start", holds the
game paused, and begins play on Space. It pauses by setting Time.timeScale = 0 in
Start (not Awake) on purpose: AutopilotGameOver resets timeScale to 1 in its Awake,
and Unity runs every Awake before any Start, so the title's Start runs last and the
game reliably starts paused even when a game-over manager is in the same scene.
Pure ASCII C# source; no recompile triggered here.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)


def test_title_source():
    s = generate_behaviour_script("title")
    assert s["ok"] is True and s["class_name"] == "AutopilotTitle"
    src = s["source"]
    assert "public string titleText" in src                     # configurable title
    assert "Press SPACE to start" in src                        # start prompt
    assert "titleText" in src and "GUI.Label" in src            # title drawn via OnGUI
    assert "KeyCode.Space" in src                               # Space starts


def test_title_pauses_in_start_and_resumes_on_space():
    # timeScale=0 lives in Start (so it wins over gameover's Awake=1); Space sets =1
    src = generate_behaviour_script("title")["source"]
    start = src.index("void Start()")
    update = src.index("void Update()")
    assert "Time.timeScale = 0f;" in src[start:update]          # paused in Start
    assert "Time.timeScale = 1f;" in src[update:]               # resumed in Update (Space)
    # and it pauses in Start, never in Awake (the whole point of the ordering fix)
    assert "void Awake()" not in src


def test_title_hides_after_start():
    src = generate_behaviour_script("title")["source"]
    # once started, Update and OnGUI early-return so the screen disappears and input frees
    assert src.count("if (started) return;") >= 2
    assert "started = true;" in src


def test_title_is_pure_ascii_and_balanced():
    src = generate_behaviour_script("title")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}")
    assert src.count("(") == src.count(")")
    assert "__" not in src                                       # all placeholders substituted


@pytest.mark.parametrize("alias", ["baslik", "title", "menu", "anaekran", "baslangic", "startscreen"])
def test_title_aliases(alias):
    assert normalize_behaviour(alias) == "title"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotTitle"


def test_title_registered():
    assert "title" in NEEDS_SCRIPT
    assert "title" in _SCRIPT_TEMPLATES


def test_title_does_not_collide_with_gameover_timescale_ordering():
    # the conflict this cycle had to resolve: gameover Awake sets timeScale=1, title
    # wants 0. They coexist only because title sets it in Start (runs after all Awakes).
    title = generate_behaviour_script("title")["source"]
    gameover = generate_behaviour_script("gameover")["source"]
    # gameover still owns its Awake reset (restart-after-pause), unchanged
    assert "void Awake()" in gameover and "Time.timeScale = 1f;" in gameover
    # title deliberately avoids Awake so it never races gameover's Awake
    assert "void Awake()" not in title
