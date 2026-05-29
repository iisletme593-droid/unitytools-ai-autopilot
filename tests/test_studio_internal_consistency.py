"""Phase 49 tests: studio_internal_consistency_check.

The check audits the studio's own moving parts. Each section can
detect a different class of drift; we synthesise each kind by
poking the relevant globals, run the check, and assert the named
drift surfaces. We restore the globals afterwards so other tests
keep working.
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
    CRITIC,
    DISPATCH_MAP,
    PRODUCER,
    StudioPaths,
    StudioState,
    init_studio_tools,
)
from unitytools.studio.tools import studio_internal_consistency_check


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="consistency-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── happy path


def test_clean_studio_passes_consistency_check() -> None:
    _fresh_studio()
    result = studio_internal_consistency_check()
    assert result["ok"] is True
    assert result["verdict"] == "pass", (
        f"clean studio should be drift-free, but got drifts: "
        f"{result['drifts']}"
    )
    assert result["drift_count"] == 0
    # Every section should be present and OK
    for section_name in ("dispatch_vs_roles_tuple", "dispatch_targets_resolve",
                          "role_allowlists_registered", "behaviour_library",
                          "strings_files"):
        section = result["sections"][section_name]
        assert section.get("ok") is True, (
            f"section {section_name} should be ok=True on a clean studio"
        )
    print("OK clean studio: verdict=pass, every section ok=True")


# ───────────────────────────────────────────── drift detection


def test_dispatch_vs_roles_drift_surfaces() -> None:
    """If DISPATCH_MAP has a key that's not in ROLES, the check should
    name it. We patch DISPATCH_MAP temporarily."""
    _fresh_studio()
    from unitytools.studio import dispatch as _dispatch
    saved = dict(_dispatch.DISPATCH_MAP)
    try:
        _dispatch.DISPATCH_MAP["ghost_role"] = "ghost_role"
        result = studio_internal_consistency_check()
        assert result["verdict"] == "fail"
        assert any("ghost_role" in d for d in result["drifts"]), (
            f"expected ghost_role drift in {result['drifts']}"
        )
        # The dispatch_vs_roles_tuple section should report the inflation
        sec = result["sections"]["dispatch_vs_roles_tuple"]
        assert "ghost_role" in sec["in_dispatch_but_not_in_roles"]
    finally:
        _dispatch.DISPATCH_MAP.clear()
        _dispatch.DISPATCH_MAP.update(saved)
    print("OK adding a DISPATCH_MAP key not in ROLES tuple is detected")


def test_unresolved_dispatch_target_surfaces() -> None:
    """If DISPATCH_MAP routes to a target that no RoleConfig has, the
    check should name the broken edge."""
    _fresh_studio()
    from unitytools.studio import dispatch as _dispatch
    from unitytools.studio.models import ROLES
    saved = dict(_dispatch.DISPATCH_MAP)
    # Add a valid key (in ROLES) pointing at a target that doesn't
    # resolve to any registered RoleConfig.
    valid_key = next(iter(ROLES))
    try:
        _dispatch.DISPATCH_MAP[valid_key] = "ghost_target"
        result = studio_internal_consistency_check()
        assert result["verdict"] == "fail"
        sec = result["sections"]["dispatch_targets_resolve"]
        assert sec["ok"] is False
        assert any("ghost_target" in u for u in sec["unresolved"])
    finally:
        _dispatch.DISPATCH_MAP.clear()
        _dispatch.DISPATCH_MAP.update(saved)
    print("OK unresolved DISPATCH_MAP target (no RoleConfig for it) is detected")


def test_unregistered_tool_in_role_allowlist_surfaces() -> None:
    """If a role's allowlist references a tool name that doesn't exist
    in the @tool registry, the check should name role + tool."""
    _fresh_studio()
    from unitytools.studio import roles as _roles
    from dataclasses import replace
    # Patch DESIGNER's allowed_tools to include a bogus name.
    original = _roles.DESIGNER
    poisoned = replace(original, allowed_tools=original.allowed_tools + ("studio_does_not_exist",))
    # Swap in the registry the role module uses
    saved_designer = _roles._ROLES["designer"]
    _roles._ROLES["designer"] = poisoned
    try:
        result = studio_internal_consistency_check()
        assert result["verdict"] == "fail"
        assert any(
            "designer" in d and "studio_does_not_exist" in d
            for d in result["drifts"]
        ), f"expected designer:studio_does_not_exist drift; got {result['drifts']}"
    finally:
        _roles._ROLES["designer"] = saved_designer
    print("OK role allowlist with an unregistered tool name surfaces drift")


def test_malformed_strings_file_surfaces() -> None:
    """A garbage JSON in studio/strings/ should be flagged without
    crashing the check."""
    state, _ = _fresh_studio()
    state.paths.strings.mkdir(parents=True, exist_ok=True)
    (state.paths.strings / "en.json").write_text("not valid json {{", encoding="utf-8")
    result = studio_internal_consistency_check()
    assert result["verdict"] == "fail"
    sec = result["sections"]["strings_files"]
    assert sec["ok"] is False
    assert any("malformed_json" in m for m in sec["malformed"])
    print("OK malformed strings/<locale>.json surfaces drift without crashing")


def test_non_object_strings_file_surfaces() -> None:
    """A valid JSON that isn't an object (e.g. a JSON array) should be
    flagged differently from malformed."""
    state, _ = _fresh_studio()
    state.paths.strings.mkdir(parents=True, exist_ok=True)
    (state.paths.strings / "en.json").write_text("[1, 2, 3]", encoding="utf-8")
    result = studio_internal_consistency_check()
    assert result["verdict"] == "fail"
    sec = result["sections"]["strings_files"]
    assert any("not_object" in m for m in sec["malformed"])
    print("OK JSON-but-not-object in strings/ surfaces as 'not_object'")


def test_strings_section_skipped_when_dir_absent() -> None:
    """When studio/strings/ doesn't exist (project scaffold variation),
    the section is skipped — not flagged."""
    _fresh_studio()
    # Strings dir was created by _fresh_studio; remove it
    state = _fresh_studio()[0]
    import shutil
    shutil.rmtree(state.paths.strings, ignore_errors=True)
    # Re-init so _STATE points at this state
    init_studio_tools(state)
    result = studio_internal_consistency_check()
    sec = result["sections"]["strings_files"]
    # An empty (but existing) dir reports checked_count=0 + ok=True;
    # a missing dir reports skipped=True.
    assert sec["ok"] is True
    print("OK strings/ section ok=True when dir empty or absent")


def test_behaviour_library_drift_detects_missing_cs_file() -> None:
    """If the Python behaviour library lists a name that has no .cs
    file on disk, the check flags the gap."""
    _fresh_studio()
    import unitytools.tools.unity_tools as ut
    saved = ut._BEHAVIOUR_LIBRARY
    try:
        ut._BEHAVIOUR_LIBRARY = saved + ("PhantomBehaviour",)
        result = studio_internal_consistency_check()
        assert result["verdict"] == "fail"
        sec = result["sections"]["behaviour_library"]
        assert "PhantomBehaviour" in sec["in_python_but_no_cs_file"]
    finally:
        ut._BEHAVIOUR_LIBRARY = saved
    print("OK behaviour name in Python library without a .cs file is flagged")


# ───────────────────────────────────────────── role surface


def test_producer_and_critic_have_consistency_check() -> None:
    assert "studio_internal_consistency_check" in PRODUCER.tool_set
    assert "studio_internal_consistency_check" in CRITIC.tool_set
    print("OK Producer + Critic both have studio_internal_consistency_check")


def test_specialists_do_not_have_consistency_check() -> None:
    """The internal consistency check is meta-tooling for the meta-loop.
    Specialists do their own scoped work; they don't audit the studio."""
    from unitytools.studio import (
        ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR, BUILD_ENGINEER,
        CAMERA_DIRECTOR, DESIGNER, GAME_BALANCER, LIGHTING_DIRECTOR,
        LOCALIZATION_LEAD, MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
        SCENE_DIRECTOR, TUTORIAL_DESIGNER, UI_BUILDER, VFX_DIRECTOR, WORKER,
    )
    for role in (ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR,
                  BUILD_ENGINEER, CAMERA_DIRECTOR, DESIGNER, GAME_BALANCER,
                  LIGHTING_DIRECTOR, LOCALIZATION_LEAD, MARKETING_DIRECTOR,
                  MATERIAL_ARTIST, PHYSICS_QA, SCENE_DIRECTOR,
                  TUTORIAL_DESIGNER, UI_BUILDER, VFX_DIRECTOR, WORKER):
        assert "studio_internal_consistency_check" not in role.tool_set, (
            f"{role.id} should not run the consistency check"
        )
    print("OK 17 specialist roles do not have studio_internal_consistency_check")


def run_test() -> None:
    test_clean_studio_passes_consistency_check()
    test_dispatch_vs_roles_drift_surfaces()
    test_unresolved_dispatch_target_surfaces()
    test_unregistered_tool_in_role_allowlist_surfaces()
    test_malformed_strings_file_surfaces()
    test_non_object_strings_file_surfaces()
    test_strings_section_skipped_when_dir_absent()
    test_behaviour_library_drift_detects_missing_cs_file()
    test_producer_and_critic_have_consistency_check()
    test_specialists_do_not_have_consistency_check()
    print("All Phase 49 internal consistency tests passed")


if __name__ == "__main__":
    run_test()
