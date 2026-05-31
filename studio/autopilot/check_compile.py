"""Ground-truth compile check: read Unity Editor.log, report CS errors after the
most recent compile boundary. Run after ANY .cs change before claiming success.
is_compiling=false alone is NOT enough (it can finish WITH errors)."""
from pathlib import Path

LOG = Path("C:/Users/Kitli Matmazel/AppData/Local/Unity/Editor/Editor.log")
OUT = Path("studio/autopilot/_compile.txt")

def main():
    if not LOG.exists():
        OUT.write_text("NO_LOG", encoding="utf-8"); print("NO_LOG"); return
    text = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    last = 0
    for i, ln in enumerate(text):
        if ("Starting compile" in ln or "CompileScripts:" in ln
                or "- Finished compile" in ln or "Reloading assemblies" in ln):
            last = i
    errs = []
    for ln in text[last:]:
        if "error CS" in ln:
            e = ln.strip()
            if e not in errs: errs.append(e)
    if not errs:
        OUT.write_text("OK 0 errors", encoding="utf-8"); print("OK 0 errors")
    else:
        body = f"ERRORS {len(errs)}\n" + "\n".join(errs[:30])
        OUT.write_text(body, encoding="utf-8"); print(body[:400])

main()
