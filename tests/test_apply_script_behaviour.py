"""P7 (cycle 18): end-to-end scripted-behaviour flow (generate -> import -> wait
for recompile -> attach). The recompile wait is a pure, injectable poll so the
orchestration is fully unit-tested without real time or a live Unity domain reload.
"""
import unitytools.tools.unity_tools as ut
from unitytools.core.gameplay import wait_until_compiled


# --- pure compile-wait -----------------------------------------------------

def test_wait_returns_true_when_compile_finishes():
    seq = [{"is_compiling": True}, {"is_compiling": True}, {"is_compiling": False}]
    box = {"i": 0}

    def get_state():
        s = seq[min(box["i"], len(seq) - 1)]
        box["i"] += 1
        return s

    slept = []
    assert wait_until_compiled(get_state, slept.append, max_attempts=5, interval=2.0) is True
    assert len(slept) == 2          # waited through the two "compiling" polls


def test_wait_times_out_if_never_done():
    assert wait_until_compiled(lambda: {"is_compiling": True}, lambda *a: None, max_attempts=3) is False


def test_wait_tolerates_get_state_errors():
    def boom():
        raise RuntimeError("bridge busy during reload")
    assert wait_until_compiled(boom, lambda *a: None, max_attempts=2) is False


# --- end-to-end tool -------------------------------------------------------

class _CompileBridge:
    """import_asset ok; get_editor_state is_compiling for N polls then done; add_component ok."""

    def __init__(self, compiling_polls=2):
        self.calls = []
        self._polls = 0
        self._compiling_polls = compiling_polls

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, params))
        if method == "import_asset":
            return {"ok": True}
        if method == "get_editor_state":
            self._polls += 1
            return {"ok": True, "is_compiling": self._polls <= self._compiling_polls}
        if method == "add_component":
            return {"ok": True, "component": params.get("type")}
        return {"ok": True}


def test_full_flow_import_wait_attach(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *a: None)
    fb = _CompileBridge(compiling_polls=2)
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_apply_script_behaviour("Coin", "rotate", max_compile_wait=30.0)

    methods = [m for (m, _p) in fb.calls]
    assert "import_asset" in methods
    assert "get_editor_state" in methods
    assert "add_component" in methods
    # correct ordering: import before the recompile wait before attach
    assert methods.index("import_asset") < methods.index("get_editor_state") < methods.index("add_component")

    assert r["ok"] is True
    assert r["compiled_in_time"] is True
    assert r["class_name"] == "AutopilotRotator"
    add_params = [p for (m, p) in fb.calls if m == "add_component"][0]
    assert add_params["name"] == "Coin" and add_params["type"] == "AutopilotRotator"


def test_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_apply_script_behaviour("Coin", "rotate")["ok"] is False


def test_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_apply_script_behaviour") is not None
