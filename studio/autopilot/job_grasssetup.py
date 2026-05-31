"""Cim malzemesi kurulumu: GrassBlade.png + GrassBladeClump.glb'yi Unity'ye
import et, GUID al, HDRP_M_GrassBlade.mat uret (CardNeedle alpha-clip sablonu).
Play KAPALI. Sadece kurulum — scatter ayri job'da.
"""
import sys, time, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *

MATDIR = Path("C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject/Assets/FantasyRPG/Generated/Materials")
TEX_REL = "FantasyRPG/Textures/Foliage/GrassBlade.png"
out = []

connect()
es = rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    rc("play_mode", {"play": False}, 40); time.sleep(3); fresh()
guard_scene()

rc("refresh_assets", {}, 40)
time.sleep(3); fresh()

guid = None
for _ in range(5):
    guid = asset_guid(TEX_REL)
    if guid: break
    rc("refresh_assets", {}, 40); time.sleep(3)
out.append(f"grassblade_guid={guid}")

if guid:
    src = (MATDIR / "HDRP_M_CardNeedle.mat").read_text(encoding="utf-8", errors="replace")
    NEEDLE = "a0222deb23edbf646b769a2353adbcd4"
    t = src.replace("HDRP_M_CardNeedle", "HDRP_M_GrassBlade")
    swaps = t.count(NEEDLE)
    t = t.replace(NEEDLE, guid)
    # doku zaten yesil; BaseColor'i hafif acik tut ki doku rengi gozuksun
    t = re.sub(r"- _BaseColor: \{[^}]*\}", "- _BaseColor: {r: 0.78, g: 0.85, b: 0.62, a: 1}", t)
    t = re.sub(r"- _Color: \{[^}]*\}", "- _Color: {r: 0.78, g: 0.85, b: 0.62, a: 1}", t, count=1)
    (MATDIR / "HDRP_M_GrassBlade.mat").write_text(t, encoding="utf-8")
    time.sleep(0.5)
    rc("refresh_assets", {}, 40)
    chk = (MATDIR / "HDRP_M_GrassBlade.mat").read_text(encoding="utf-8")
    out.append(f"mat_yazildi tex_swap={swaps} guid_bagli={guid in chk} alpha_clip={'_ALPHATEST_ON' in chk}")
else:
    out.append("GUID_YOK - import basarisiz")

Path("studio/autopilot/_grasssetup.txt").write_text("\n".join(out), encoding="utf-8")
print("GRASSSETUP_DONE")
