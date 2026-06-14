"""Registry integrity: no two tool modules may register the same @tool name.

Last-import-wins silently shadows the earlier definition (the scan found ~15 such
dead duplicates). This guards against regressions by scanning the source directly,
independent of import order / registry state.
"""
import ast
import collections
import pathlib

import unitytools.tools  # noqa: F401 - registers all tools
from unitytools.core.tool_registry import get_all_tools, get_collisions

TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1] / "unitytools" / "tools"


def _tool_names_per_module() -> dict[str, list[str]]:
    name2mods: dict[str, list[str]] = collections.defaultdict(list)
    for py in sorted(TOOLS_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        tree = ast.parse(py.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and any(
                isinstance(d, ast.Call) and getattr(d.func, "id", None) == "tool"
                for d in node.decorator_list
            ):
                name2mods[node.name].append(py.stem)
    return name2mods


def test_no_duplicate_tool_names_across_modules():
    name2mods = _tool_names_per_module()
    dups = {n: ms for n, ms in name2mods.items() if len(ms) > 1}
    assert dups == {}, f"duplicate @tool names across modules (last-import shadows): {dups}"


def test_registry_still_broad():
    # sanity: consolidating duplicates must not shrink the exposed tool surface
    assert len(get_all_tools()) > 120


def test_get_collisions_is_available():
    # the introspection helper exists and returns a mapping
    assert isinstance(get_collisions(), dict)
