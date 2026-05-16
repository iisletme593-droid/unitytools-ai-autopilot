"""Ingest the REAL DOCS/backlog/vertical-slice-backlog.md into the
studio task framework (same architecture: milestone + tasks + roles).
Connects phases 65-86 (tasks/next/standup/dispatch) to the real game.
"""
import json, re
from pathlib import Path
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools

config, blender, unity = _bootstrap()
try: unity.connect(timeout=3.0)
except Exception: pass
init_studio_unity(unity); ut._UNITY = unity
proj = Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0')
paths = StudioPaths(project_root=proj)
[d.mkdir(parents=True, exist_ok=True) for d in paths.all_dirs()]
init_studio_tools(StudioState(paths))

from unitytools.studio.tools import (
    studio_write_gdd, studio_add_milestone, studio_add_task,
    studio_propose_decision, studio_list_tasks,
)

DOCS = Path("C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/DOCS")
backlog = (DOCS / "backlog" / "vertical-slice-backlog.md").read_text(encoding="utf-8", errors="replace")

# Parse P0/P1/P2 sections -> list of (priority, item)
items = []
cur = None
for ln in backlog.splitlines():
    s = ln.strip()
    m = re.match(r"^##\s*(P0|P1|P2|Kesinlikle Ertele)", s)
    if m:
        cur = m.group(1); continue
    if s.startswith("- ") and cur and cur != "Kesinlikle Ertele":
        items.append((cur, s[2:].strip()))

# Role mapping by keyword
def role_for(t: str) -> str:
    t = t.lower()
    if any(k in t for k in ("blockout", "route", "arena", "world partition",
                            "streaming", "briar hollow", "landmark")):
        return "level_designer"
    if any(k in t for k in ("ui", "mini map", "skill bar", "quest tracker",
                            "health/stamina")):
        return "designer"
    if any(k in t for k in ("audio", "music", "footstep", "ses", "ambient encounter")):
        return "tech_artist"
    if any(k in t for k in ("combat feel", "hit impact", "stagger",
                            "i-frame", "parry", "vfx")):
        return "tech_artist"
    return "designer"  # gameplay systems default

GDD = """# Briar Hollow — Vertical Slice (DOCS-driven)

Source of truth: C:/.../windsurf-project/DOCS (design + backlog +
implementation). This studio backlog mirrors DOCS/backlog/
vertical-slice-backlog.md. The framework (tasks/next/standup/
dispatch/roles, phases 65-86) now drives the REAL project.

## Genre mix
Valheim (chill explore + survival + camp) + V-Rising (progression
rhythm) + Knight Online (party/grind hooks, KO-Valheim realignment)
+ Remnant 2 (responsive forgiving souls-lite combat).

## Core pillars (DOCS/design/core-pillars.md)
1. Combat tok — her vuruşta ağırlık; anim+kamera+ses+hitreact aynı yön
2. Atmosfer premium — az ama hatırlanır mekan, güçlü sanat yönü
3. Dünya güzel VE tehlikeli — hayranlık + tedirginlik aynı anda
4. İlerleme açık + bağımlılık — her 15-20 dk anlamlı kazanç
5. Token sonra — önce oyun hissi

## Vertical slice spine
spawn → camp → path → landmark read → mini-boss arena, on the
real-world Briar Hollow terrain (Open-Meteo heightmap, biome
bands, sparse forest — already built via studio_realize_world).

## Scope discipline (DOCS "Kesinlikle Ertele")
NO: 100-player, full MMO economy, token, website/account,
marketplace, siege, faction war. Vertical slice only.
"""
print(json.dumps(studio_write_gdd(GDD))[:120])

ms = studio_add_milestone(
    name="Vertical Slice - Briar Hollow",
    description="DOCS-driven 4-pillar vertical slice: spawn->camp->path"
                "->landmark->mini-boss on the real-world terrain.")
mid = ms.get("milestone_id", "")
print("milestone:", ms)

# Avoid dupes if rerun: collect existing titles
existing = {t["title"] for t in studio_list_tasks().get("tasks", [])}
created = 0
for pri, item in items:
    title = f"[{pri}] {item}"
    if title in existing:
        continue
    r = studio_add_task(
        title=title, role=role_for(item),
        description=f"From DOCS/backlog/vertical-slice-backlog.md ({pri}). "
                    f"Same-architecture ingest; see DOCS/design + "
                    f"DOCS/implementation for the detailed pass specs.",
        milestone=mid)
    if r.get("ok"):
        created += 1
print(f"created {created} tasks from backlog ({len(items)} items parsed)")

for t, s, why in [
    ("DOCS is the source of truth",
     "All work mirrors C:/.../windsurf-project/DOCS; studio backlog "
     "= DOCS/backlog/vertical-slice-backlog.md.",
     "User: 'DOCS klasorunde butun dokumanlar mevcut, task olarak "
     "ordan devam et ayni mimaride'. Framework drives the real project."),
    ("Vertical slice scope lock",
     "P0 first; defer 100-player/MMO/token/marketplace/siege/faction.",
     "DOCS 'Kesinlikle Ertele' + core-pillar 5 (token sonra)."),
]:
    print("decision:", studio_propose_decision(title=t, summary=s, rationale=why).get("decision_id"))

print("BACKLOG INGEST DONE")
