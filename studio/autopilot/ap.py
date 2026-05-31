"""Autopilot shared helpers for the overnight Briar Hollow build.
Usage in a job:  from ap import *  ; connect() ; guard_scene() ; ...

IMPORT FIX: when a job is run as `python studio/autopilot/job.py`, Python puts
the script dir on sys.path[0], NOT the cwd, so `unitytools` (resolved via the
worktree root) is not importable. We prepend cwd here so it resolves. We also
DEFER the Unity bootstrap into connect() so importing ap.py is cheap/safe.

Hard rules baked in (lessons this session):
  * NEVER play_mode while editing assets (domain reload silently switches scene
    to Main.unity).
  * ALWAYS guard_scene() so we operate on ForgottenValley_VS.
  * GLB imports are Y-up (rot x=0); FBX from Blender are Z-up (rot x=-90).
  * place_asset_on_terrain spiral-search scatters objects -> search_radius=0 +
    a tiny probe to read terrain height.
  * scatter_terrain_glb_trees DESTROYS WorldForestGLB -> never use it for props.
  * save_scene after meaningful edits; verify before claiming success.
"""
import os, sys, time, json, math
# make `unitytools` importable regardless of how the script was launched
sys.path.insert(0, os.getcwd())
from pathlib import Path

SCENE = "Assets/Scenes/ForgottenValley_VS.unity"
U = None
_studio_shot = None

def connect(t=14):
    """Bootstrap + connect to Unity (deferred so import is cheap)."""
    global U, _studio_shot
    if U is None:
        from unitytools.cli.entry import _bootstrap
        from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
        from unitytools.studio.tools import studio_capture_screenshot
        _c, _b, U = _bootstrap()
        init_studio_unity(U)
        init_studio_tools(StudioState(StudioPaths(project_root=Path('.'))))
        _studio_shot = studio_capture_screenshot
    return fresh(t)

def fresh(t=12):
    try: U.disconnect()
    except Exception: pass
    try: return U.connect(timeout=t)
    except Exception: return False

def rc(cmd, p=None, t=60, retries=4):
    p = p or {}
    for k in range(retries):
        try: return U.call(cmd, p, t)
        except Exception as e:
            if k == retries-1: print(f"  [rc fail] {cmd}: {str(e)[:50]}")
            fresh(); time.sleep(2)
    return {}

def guard_scene():
    s = rc("list_scenes", {}, 15) or {}
    act = str(s.get("active_scene", ""))
    if "ForgottenValley" not in act:
        print(f"  [guard] wrong scene ({act}) -> reopening")
        rc("open_scene", {"path": SCENE}, 60)
        time.sleep(2); fresh()
        s = rc("list_scenes", {}, 15) or {}
        act = str(s.get("active_scene", ""))
    return "ForgottenValley" in act

def pos_of(name, dx=0, dy=0, dz=0):
    d = rc("get_object_details", {"name": name}, 15) or {}
    if not d.get("name"): return None
    p = d.get("position") or {}
    return (float(p.get("x", dx)), float(p.get("y", dy)), float(p.get("z", dz)))

def child_count(name):
    d = rc("get_object_details", {"name": name}, 15) or {}
    return d.get("child_count") if d.get("name") else None

def surf(x, z, fb=120.0):
    r = rc("place_asset_on_terrain", {"asset_path": "Assets/Art/HQ/CardFir.glb",
        "x": x, "z": z, "scale": 0.001, "name": "_ap_probe",
        "min_surface_y": 0.0, "max_slope_deg": 89.0, "search_radius": 0.0, "y_offset": 0.0}, 35)
    y = (r or {}).get("surface_y", fb)
    rc("delete_object", {"name": "_ap_probe"}, 10)
    return float(y)

def place_pinned(asset, x, z, scale, name, parent=None, y_offset=0.0, rot_y=0.0,
                 glb=True, min_surface_y=0.0, max_slope_deg=89.0):
    pr = {"asset_path": asset, "x": x, "z": z, "scale": float(scale), "rot_y": rot_y,
          "name": name, "min_surface_y": min_surface_y, "max_slope_deg": max_slope_deg,
          "search_radius": 0.0, "y_offset": y_offset}
    if parent: pr["parent"] = parent
    r = rc("place_asset_on_terrain", pr, 45)
    ok = isinstance(r, dict) and r.get("ok")
    if ok:
        rc("set_rotation", {"name": name, "x": 0 if glb else -90, "y": rot_y, "z": 0}, 12)
    return r if ok else None

def color(name, r, g, b, smooth=0.1, metallic=0.0):
    rc("set_material_color", {"name": name, "r": r, "g": g, "b": b, "a": 1.0}, 12)
    rc("set_material_pbr", {"name": name, "metallic": metallic, "smoothness": smooth}, 12)

def light(name, kind, intensity, rng, col, x, y, z, parent=None):
    for _ in range(2): rc("delete_object", {"name": name}, 8)
    rc("create_light", {"light_type": kind, "name": name, "intensity": intensity,
        "range": rng, "color": {"r": col[0], "g": col[1], "b": col[2]},
        "position": {"x": x, "y": y, "z": z}}, 18)
    if parent: rc("set_parent", {"child": name, "parent": parent}, 10)

def prim(ptype, name, x, y, z, sx, sy, sz, parent=None, rotY=0.0, col=None, smooth=0.12):
    rc("create_primitive", {"type": ptype, "name": name,
        "position": {"x": x, "y": y, "z": z}, "scale": {"x": sx, "y": sy, "z": sz}}, 18)
    if rotY: rc("set_rotation", {"name": name, "x": 0, "y": rotY, "z": 0}, 10)
    if parent: rc("set_parent", {"child": name, "parent": parent}, 10)
    if col: color(name, col[0], col[1], col[2], smooth=smooth)

def empty(name, x, y, z, parent=None):
    for _ in range(2): rc("delete_object", {"name": name}, 8)
    rc("create_empty", {"name": name, "position": {"x": x, "y": y, "z": z}}, 12)
    if parent: rc("set_parent", {"child": name, "parent": parent}, 10)

def group(name, x, y, z):
    for _ in range(2): rc("delete_object", {"name": name}, 10)
    rc("create_empty", {"name": name, "position": {"x": x, "y": y, "z": z}}, 12)

def save():
    r = rc("save_scene", {}, 40)
    return isinstance(r, dict) and r.get("ok")

def shot(name, px, py, pz, size, pitch, yaw, target=None):
    p = {"size": size, "pitch": pitch, "yaw": yaw}
    if target: p["target"] = target
    else: p.update({"pivot_x": px, "pivot_y": py, "pivot_z": pz})
    rc("set_scene_view", p, 30)
    time.sleep(1.4)
    r = _studio_shot(name=name)
    return (r or {}).get("path", "")
