"""Phase 91: fetch a real-world heightmap (free, keyless Open-Meteo
elevation API) and sculpt a Unity Terrain with biome ground bands.
Mountains + valleys + plains from REAL geography. No Google key needed.
"""
import math, json, time, urllib.request, urllib.parse
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

# A real region with the mix the user asked for: valley plains ->
# forested slopes -> rocky peaks. Bavarian Alps foothills (Tegernsee).
CENTER_LAT = 47.66
CENTER_LNG = 11.74
SPAN_KM = 16.0
RES = 33                       # Unity heightmap res (2^5+1); coarser
                               # = far fewer API calls (avoids 429)

def latlng_grid(lat, lng, span_km, res):
    dlat = (span_km / 111.0)
    dlng = (span_km / (111.0 * math.cos(math.radians(lat))))
    pts = []
    for iy in range(res):
        fy = iy / (res - 1) - 0.5
        for ix in range(res):
            fx = ix / (res - 1) - 0.5
            pts.append((lat + fy * dlat, lng + fx * dlng))
    return pts

def fetch_elevations(points, chunk=100):  # Open-Meteo hard max = 100/call
    out = []
    for i in range(0, len(points), chunk):
        seg = points[i:i + chunk]
        lats = ",".join(f"{a:.5f}" for a, _ in seg)
        lngs = ",".join(f"{b:.5f}" for _, b in seg)
        url = ("https://api.open-meteo.com/v1/elevation?latitude="
               + lats + "&longitude=" + lngs)
        ok = False
        for attempt in range(6):
            try:
                r = urllib.request.urlopen(url, timeout=25)
                d = json.loads(r.read())
                out.extend(d["elevation"])
                ok = True
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"  429 rate-limited, backoff {wait}s "
                          f"(attempt {attempt+1})", flush=True)
                    time.sleep(wait)
                else:
                    if attempt == 5:
                        raise
                    time.sleep(3)
            except Exception:
                if attempt == 5:
                    raise
                time.sleep(3)
        if not ok:
            raise RuntimeError("elevation fetch failed after retries")
        print(f"  fetched {len(out)}/{len(points)}", flush=True)
        time.sleep(2.0)   # polite spacing to stay under the free tier
    return out

print(f"Sampling {RES}x{RES} = {RES*RES} real points around "
      f"({CENTER_LAT},{CENTER_LNG}) span {SPAN_KM}km ...", flush=True)
pts = latlng_grid(CENTER_LAT, CENTER_LNG, SPAN_KM, RES)
elev = fetch_elevations(pts)
emin, emax = min(elev), max(elev)
relief = emax - emin
print(f"elevation real range: {emin:.0f}..{emax:.0f} m (relief {relief:.0f} m)", flush=True)

# normalize 0..1 row-major (matches C# arr[y*res+x])
norm = [ (e - emin) / (relief if relief > 1 else 1) for e in elev ]

c, b, unity = _bootstrap(); unity.connect(timeout=6.0)
init_studio_unity(unity); ut._UNITY = unity
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
init_studio_tools(StudioState(P))
from unitytools.tools.unity_tools import unity_open_scene, unity_save_scene
from unitytools.studio.tools import studio_capture_screenshot

unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")
# size_xz = real footprint in metres; size_y = real relief, mild boost
res_build = unity.call("build_terrain_from_heightmap", {
    "resolution": RES,
    "size_xz": SPAN_KM * 1000.0,
    "size_y": max(120.0, relief * 1.15),
    "heights": norm,
})
print("BUILD:", json.dumps(res_build)[:300] if isinstance(res_build, dict) else str(res_build)[:300], flush=True)

unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_world_terrain"), indent=1)[:220], flush=True)
print("WORLD TERRAIN DONE", flush=True)
