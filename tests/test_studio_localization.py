"""Phase 39 tests: Localization Lead role + string table tools.

Covers: locale code validation, read/write/merge/replace semantics,
list_locales, localization_audit verdicts, the LocalizedText
behaviour in the library, role allowlist, dispatch routing.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    ART_DIRECTOR,
    ATMOSPHERE_DIRECTOR,
    AUDIO_DIRECTOR,
    BUILD_ENGINEER,
    CAMERA_DIRECTOR,
    DESIGNER,
    DISPATCH_MAP,
    GAME_BALANCER,
    LIGHTING_DIRECTOR,
    LOCALIZATION_LEAD,
    MARKETING_DIRECTOR,
    MATERIAL_ARTIST,
    PHYSICS_QA,
    StudioPaths,
    StudioState,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
    init_studio_tools,
)
from unitytools.studio.tools import (
    studio_list_locales,
    studio_localization_audit,
    studio_read_strings,
    studio_write_strings,
)
from unitytools.tools.unity_tools import _BEHAVIOUR_LIBRARY


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="loc-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── locale code validation


def test_write_strings_rejects_invalid_locale_codes() -> None:
    _fresh_studio()
    for bad in ("EN", "english", "en_US", "en-us", "x", "", "123"):
        result = studio_write_strings(locale=bad, strings={"k": "v"})
        assert result["ok"] is False, f"locale {bad!r} should have been rejected"
        assert "locale" in result["error"].lower() or "required" in result["error"].lower()
    print("OK invalid locale codes rejected (uppercase / underscore / wrong shape / empty)")


def test_write_strings_accepts_valid_locale_codes() -> None:
    _fresh_studio()
    for good in ("en", "tr", "pt-BR", "zh-CN"):
        result = studio_write_strings(locale=good, strings={"k": "v"})
        assert result["ok"] is True, f"locale {good!r} should have been accepted; got {result}"
    print("OK valid locale codes accepted (en, tr, pt-BR, zh-CN)")


# ───────────────────────────────────────────── read / write / merge


def test_read_strings_returns_empty_when_absent() -> None:
    _fresh_studio()
    result = studio_read_strings(locale="en")
    assert result["ok"] is True
    assert result["strings"] == {}
    print("OK read_strings: empty when locale file absent")


def test_write_then_read_round_trip() -> None:
    state, _ = _fresh_studio()
    result = studio_write_strings(locale="en", strings={
        "title.main": "Project Xenon",
        "btn.start": "Start",
    })
    assert result["ok"] is True
    assert (state.paths.strings / "en.json").exists()
    read = studio_read_strings(locale="en")
    assert read["strings"]["title.main"] == "Project Xenon"
    assert read["strings"]["btn.start"] == "Start"
    print("OK write then read round-trips")


def test_write_strings_merge_preserves_existing() -> None:
    """mode='merge' (default) keeps keys not in the new dict."""
    _fresh_studio()
    studio_write_strings(locale="en", strings={"a": "alpha", "b": "beta"})
    studio_write_strings(locale="en", strings={"c": "gamma"})  # default merge
    read = studio_read_strings(locale="en")
    assert read["strings"] == {"a": "alpha", "b": "beta", "c": "gamma"}
    print("OK merge mode preserves untouched keys")


def test_write_strings_replace_wipes_existing() -> None:
    _fresh_studio()
    studio_write_strings(locale="en", strings={"a": "alpha", "b": "beta"})
    studio_write_strings(locale="en", strings={"c": "gamma"}, mode="replace")
    read = studio_read_strings(locale="en")
    assert read["strings"] == {"c": "gamma"}
    print("OK replace mode wipes the file")


def test_write_strings_rejects_invalid_mode() -> None:
    _fresh_studio()
    result = studio_write_strings(locale="en", strings={"k": "v"}, mode="weird")
    assert result["ok"] is False
    assert "mode" in result["error"]
    print("OK unknown mode rejected")


def test_write_strings_rejects_non_string_values() -> None:
    _fresh_studio()
    result = studio_write_strings(locale="en", strings={"k": 42})  # type: ignore
    assert result["ok"] is False
    assert "strings" in result["error"].lower()
    print("OK non-string values rejected")


def test_write_strings_handles_unicode() -> None:
    """Turkish / accented chars should round-trip cleanly."""
    state, _ = _fresh_studio()
    studio_write_strings(locale="tr", strings={
        "title.main": "Şato Projesi",
        "btn.start": "Başla",
        "msg.win": "Tebrikler! 🎉",
    })
    raw = (state.paths.strings / "tr.json").read_text(encoding="utf-8")
    # JSON written with ensure_ascii=False so the actual chars are in the file
    assert "Şato" in raw
    assert "Başla" in raw
    read = studio_read_strings(locale="tr")
    assert read["strings"]["msg.win"] == "Tebrikler! 🎉"
    print("OK Unicode + emoji round-trip cleanly")


def test_read_strings_handles_malformed_file() -> None:
    state, _ = _fresh_studio()
    state.paths.strings.mkdir(parents=True, exist_ok=True)
    (state.paths.strings / "en.json").write_text("not valid json", encoding="utf-8")
    result = studio_read_strings(locale="en")
    assert result["ok"] is False
    assert "malformed" in result["error"].lower() or "json" in result["error"].lower()
    print("OK malformed locale file -> clean error")


# ───────────────────────────────────────────── list_locales


def test_list_locales_empty_dir() -> None:
    _fresh_studio()
    result = studio_list_locales()
    assert result["ok"] is True
    assert result["count"] == 0
    print("OK list_locales: zero count when dir empty")


def test_list_locales_returns_each_locale_with_key_count() -> None:
    _fresh_studio()
    studio_write_strings(locale="en", strings={"a": "1", "b": "2", "c": "3"})
    studio_write_strings(locale="tr", strings={"a": "bir"})
    studio_write_strings(locale="pt-BR", strings={"a": "um", "b": "dois"})
    result = studio_list_locales()
    assert result["count"] == 3
    rows = {r["locale"]: r["key_count"] for r in result["locales"]}
    assert rows == {"en": 3, "tr": 1, "pt-BR": 2}
    print("OK list_locales returns each locale + key count")


# ───────────────────────────────────────────── audit


def test_audit_pass_when_all_locales_have_full_coverage() -> None:
    _fresh_studio()
    studio_write_strings(locale="en", strings={"a": "1", "b": "2"})
    studio_write_strings(locale="tr", strings={"a": "bir", "b": "iki"})
    result = studio_localization_audit(base_locale="en")
    assert result["verdict"] == "pass"
    assert result["violations"] == []
    print("OK audit pass when every locale matches en keys")


def test_audit_fails_with_missing_keys_per_locale() -> None:
    _fresh_studio()
    studio_write_strings(locale="en", strings={"a": "1", "b": "2", "c": "3"})
    studio_write_strings(locale="tr", strings={"a": "bir"})  # missing b, c
    result = studio_localization_audit(base_locale="en")
    assert result["verdict"] == "fail"
    tr_row = next(r for r in result["locales"] if r["locale"] == "tr")
    assert tr_row["missing_count"] == 2
    assert "b" in tr_row["missing_keys"] and "c" in tr_row["missing_keys"]
    assert any(v.startswith("missing_keys:tr") for v in result["violations"])
    print("OK audit flags per-locale missing keys + sample list")


def test_audit_fails_when_no_strings_dir() -> None:
    state, _ = _fresh_studio()
    # Remove the strings dir so we hit the "no_strings_dir" branch
    import shutil
    shutil.rmtree(state.paths.strings)
    result = studio_localization_audit()
    assert result["verdict"] == "fail"
    assert "no_strings_dir" in result["violations"]
    print("OK audit flags missing strings/ dir cleanly")


def test_audit_fails_when_base_locale_missing() -> None:
    _fresh_studio()
    studio_write_strings(locale="tr", strings={"a": "bir"})
    # No en table at all
    result = studio_localization_audit(base_locale="en")
    assert result["verdict"] == "fail"
    assert any(v.startswith("base_locale_missing") for v in result["violations"])
    print("OK audit flags missing base locale")


# ───────────────────────────────────────────── runtime behaviour


def test_localized_text_in_behaviour_library() -> None:
    assert "LocalizedText" in _BEHAVIOUR_LIBRARY
    print("OK LocalizedText registered in the behaviour library")


def test_localized_text_cs_file_exists() -> None:
    path = _REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours" / "LocalizedText.cs"
    assert path.exists()
    body = path.read_text(encoding="utf-8")
    assert "namespace UnityTools.Behaviours" in body
    assert "class LocalizedText" in body
    # Must require Text component so attach is well-defined
    assert "RequireComponent(typeof(Text))" in body
    # Must NOT use UnityEditor unconditionally
    assert "using UnityEditor;" not in body
    print("OK LocalizedText.cs exists, right namespace, requires Text, no UnityEditor")


# ───────────────────────────────────────────── role allowlist


def test_localization_lead_allowlist() -> None:
    assert "studio_list_locales" in LOCALIZATION_LEAD.tool_set
    assert "studio_read_strings" in LOCALIZATION_LEAD.tool_set
    assert "studio_write_strings" in LOCALIZATION_LEAD.tool_set
    assert "studio_localization_audit" in LOCALIZATION_LEAD.tool_set
    # Reads GDD + Press Kit for context
    assert "studio_read_gdd" in LOCALIZATION_LEAD.tool_set
    assert "studio_read_press_kit" in LOCALIZATION_LEAD.tool_set
    # Cannot write GDD / Art Bible / Audio Brief / Press Kit
    assert "studio_write_gdd" not in LOCALIZATION_LEAD.tool_set
    assert "studio_write_art_bible" not in LOCALIZATION_LEAD.tool_set
    assert "studio_write_audio_brief" not in LOCALIZATION_LEAD.tool_set
    assert "studio_write_press_kit" not in LOCALIZATION_LEAD.tool_set
    # Cannot mutate scene
    assert "unity_create_primitive" not in LOCALIZATION_LEAD.tool_set
    assert "unity_create_ui_text" not in LOCALIZATION_LEAD.tool_set
    # Lifecycle + escalation
    assert "studio_update_task_status" in LOCALIZATION_LEAD.tool_set
    assert "studio_add_task" in LOCALIZATION_LEAD.tool_set
    print("OK Localization Lead allowlist: string tables only, no other doc writes, no scene mutation")


def test_other_roles_lack_write_strings() -> None:
    """Only Localization Lead writes the string tables."""
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR, UI_BUILDER,
                  BUILD_ENGINEER, ATMOSPHERE_DIRECTOR, MATERIAL_ARTIST,
                  MARKETING_DIRECTOR, GAME_BALANCER):
        assert "studio_write_strings" not in role.tool_set, (
            f"{role.id} must not write string tables"
        )
    print("OK only Localization Lead writes string tables")


def test_localization_lead_doc_only_no_engine() -> None:
    assert LOCALIZATION_LEAD.needs_engine is False
    assert LOCALIZATION_LEAD.needs_vision is False
    print("OK Localization Lead is engine-free + vision-free")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_localization_lead_to_self() -> None:
    assert DISPATCH_MAP["localization_lead"] == "localization_lead"
    print("OK DISPATCH_MAP[localization_lead] -> localization_lead")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["marketing_director"] == "marketing_director"
    assert DISPATCH_MAP["game_balancer"] == "game_balancer"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after localization_lead addition")


def run_test() -> None:
    # Locale validation
    test_write_strings_rejects_invalid_locale_codes()
    test_write_strings_accepts_valid_locale_codes()
    # Read/write
    test_read_strings_returns_empty_when_absent()
    test_write_then_read_round_trip()
    test_write_strings_merge_preserves_existing()
    test_write_strings_replace_wipes_existing()
    test_write_strings_rejects_invalid_mode()
    test_write_strings_rejects_non_string_values()
    test_write_strings_handles_unicode()
    test_read_strings_handles_malformed_file()
    # list_locales
    test_list_locales_empty_dir()
    test_list_locales_returns_each_locale_with_key_count()
    # Audit
    test_audit_pass_when_all_locales_have_full_coverage()
    test_audit_fails_with_missing_keys_per_locale()
    test_audit_fails_when_no_strings_dir()
    test_audit_fails_when_base_locale_missing()
    # Runtime behaviour
    test_localized_text_in_behaviour_library()
    test_localized_text_cs_file_exists()
    # Role
    test_localization_lead_allowlist()
    test_other_roles_lack_write_strings()
    test_localization_lead_doc_only_no_engine()
    # Dispatch
    test_dispatch_map_routes_localization_lead_to_self()
    test_existing_routes_unchanged()
    print("All Phase 39 localization tests passed")


if __name__ == "__main__":
    run_test()
