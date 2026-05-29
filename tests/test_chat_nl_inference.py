"""Phase 87: natural-language -> slash inference.

The operator wants to drive the studio by talking, not by typing '/'.
infer_command() maps a plain sentence to a slash dispatch line for the
READ/REPORT surface, and returns None for anything creative / ambiguous
so full free-text LLM power is preserved for scene building + code.

Two invariants this file guards:
  1. Report-intent sentences (TR + EN) resolve to the right command.
  2. Creative / mutation / engine sentences NEVER get hijacked — they
     must return None so they reach the LLM tool loop intact.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.cli.chat_commands import infer_command, dispatch


# ─────────────────────────────────────── positive: report intents


def test_nl_daily_flow_intents() -> None:
    assert infer_command("bana standup ver") == "standup"
    assert infer_command("bugün ne oldu?") == "standup"
    assert infer_command("daily digest") == "standup"
    assert infer_command("günü bitir") == "wrap-up"
    assert infer_command("wrap up please") == "wrap-up"
    assert infer_command("sıradaki ne yapayım") == "next"
    assert infer_command("what's next") == "next"
    assert infer_command("sprint planı ne") == "sprint"
    print("OK daily-flow NL intents (standup/wrap-up/next/sprint)")


def test_nl_triage_intents() -> None:
    assert infer_command("neler bloke durumda") == "blocked"
    assert infer_command("what's blocked") == "blocked"
    assert infer_command("ne üstünde çalışılıyor") == "inflight"
    assert infer_command("work in progress") == "inflight"
    print("OK triage NL intents (blocked/inflight)")


def test_nl_inventory_and_aggregate_intents() -> None:
    assert infer_command("görev listesi") == "tasks"
    assert infer_command("kilometre taşları") == "milestones"
    assert infer_command("kararlar neler") == "decisions"
    assert infer_command("genel durum") == "dashboard"
    assert infer_command("yayına hazır mı") == "ship"
    assert infer_command("maliyet ne kadar") == "cost"
    assert infer_command("son aktiviteler neler") == "recent"
    assert infer_command("ilerleme grafiği") == "burndown"
    print("OK inventory + aggregate NL intents")


def test_nl_meta_intents() -> None:
    assert infer_command("komutlar neler") == "help"
    assert infer_command("ne yapabilirsin") == "help"
    assert infer_command("sistem durumu") == "diag"
    assert infer_command("kaç tool var") == "diag"
    assert infer_command("unity bağlı mı") == "status"
    assert infer_command("stüdyo özeti") == "studio"
    print("OK meta NL intents (help/diag/status/studio)")


def test_nl_argumented_find_show_why() -> None:
    assert infer_command("lighthouse ara") == "find lighthouse"
    assert infer_command("boss arena bul") == "find boss arena"
    assert infer_command("ara: pickup vfx") == "find pickup vfx"
    assert infer_command("search for hearth") == "find hearth"
    # why / show need an explicit id-like token
    why = infer_command("neden 1a2b3c4d bloke")
    assert why == "why 1a2b3c4d", f"got {why!r}"
    show = infer_command("1a2b3c4d detayını göster")
    assert show == "show 1a2b3c4d", f"got {show!r}"
    print("OK argumented NL intents (find/why/show with explicit arg)")


# ─────────────────────────────────────── negative: never hijack


def test_nl_guard_blocks_creative_instructions() -> None:
    """Scene-building / creative prose must fall through to the LLM."""
    for txt in (
        "bir küp yarat 0 5 0",
        "forest sahnesini kur",
        "realistic bir orman sahnesi oluştur ışıklandır",
        "Player prefabına Rigidbody ekle",
        "sahneye bir directional light ekle",
        "make a cube and attach a script",
        "import the rock mesh from blender",
        "terrain texture'ını değiştir",
    ):
        assert infer_command(txt) is None, f"must NOT hijack: {txt!r}"
    print("OK creative/scene prose → None (LLM keeps it)")


def test_nl_guard_blocks_mutations() -> None:
    """Vague mutation language must not silently mutate the backlog."""
    for txt in (
        "şu taskı sil",
        "commit at ve push'la",
        "bu değişiklikleri kaldır",
    ):
        assert infer_command(txt) is None, f"must NOT infer mutation: {txt!r}"
    print("OK vague mutation prose → None (no silent backlog/git changes)")


def test_nl_ignores_slash_and_empty_and_long() -> None:
    assert infer_command("") is None
    assert infer_command("   ") is None
    assert infer_command("/standup") is None  # already a slash command
    # Very long prose is an LLM instruction, not a terse command
    long_prose = (
        "şimdi şöyle yapalım önce valley sahnesini gez sonra bana her "
        "ağacın poligon sayısını söyle ve hangi materyaller pahalı "
        "ölç sonra rapor çıkar bu arada ışıkları da kontrol et lütfen"
    )
    assert infer_command(long_prose) is None
    print("OK empty / slash / long-prose → None")


def test_nl_short_find_arg_rejected() -> None:
    """A find/why/show capture that's too short shouldn't fire — avoids
    'x ara' nonsense becoming a 1-char search."""
    r = infer_command("x ara")
    # Either None or not a find with a 1-char query
    assert r is None or not r.startswith("find "), f"got {r!r}"
    print("OK too-short find argument rejected")


# ─────────────────────────────────────── integration: inferred line dispatches


def test_inferred_line_actually_dispatches() -> None:
    """The whole point: an inferred line must be a real dispatch line.
    'komutlar neler' → 'help' → dispatch('help') handled=True."""
    line = infer_command("komutlar neler")
    assert line == "help"
    r = dispatch(line)
    assert r.handled is True
    assert r.ok is True
    assert r.tool_name == "help"
    print("OK inferred 'help' line dispatches end-to-end")


def test_inferred_find_line_dispatches_with_query() -> None:
    line = infer_command("hearth bul")
    assert line == "find hearth"
    # dispatch needs studio state for find; just assert it's recognised
    # (handled True/False both fine — we only assert it parses to find)
    assert line.split()[0] == "find"
    assert line.split(maxsplit=1)[1] == "hearth"
    print("OK inferred find line carries the query through")


def run_test() -> None:
    test_nl_daily_flow_intents()
    test_nl_triage_intents()
    test_nl_inventory_and_aggregate_intents()
    test_nl_meta_intents()
    test_nl_argumented_find_show_why()
    test_nl_guard_blocks_creative_instructions()
    test_nl_guard_blocks_mutations()
    test_nl_ignores_slash_and_empty_and_long()
    test_nl_short_find_arg_rejected()
    test_inferred_line_actually_dispatches()
    test_inferred_find_line_dispatches_with_query()
    print("All Phase 87 natural-language inference tests passed")


if __name__ == "__main__":
    run_test()
