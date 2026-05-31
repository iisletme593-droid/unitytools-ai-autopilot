"""BONUS: TEK-KOMUT REVIEW DONGUSU — capture + triage'i birlestirir.
Calistirinca: hedef cevresinde N acidan kare ceker -> hepsini eler ->
en kritik+cesitli ~22 kareyi studio/autopilot/review/ icine koyar -> ben sadece
onlari okurum. 'Surekli snapshot cek, sen degerlendirip duzelt' dongusunun
capture+triage yarisi tek komutta.

Kullanim: python review_loop.py [merkez=Campfire] [sizes=55,110,200] [yawstep=45]
"""
import sys, subprocess, time
from pathlib import Path
HERE = Path(__file__).parent
center  = sys.argv[1] if len(sys.argv) > 1 else "Campfire"
sizes   = sys.argv[2] if len(sys.argv) > 2 else "55,110,200"
yawstep = sys.argv[3] if len(sys.argv) > 3 else "45"

print("== CAPTURE ==")
subprocess.run([sys.executable, str(HERE/"capture_orbit.py"), center, sizes, yawstep],
               cwd=str(Path.cwd()))
print("== TRIAGE ==")
subprocess.run([sys.executable, str(HERE/"shot_triage.py")], cwd=str(Path.cwd()))
print("REVIEW_LOOP_DONE -> studio/autopilot/review/ + _triage.json")
