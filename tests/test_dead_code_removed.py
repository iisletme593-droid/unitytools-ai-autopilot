"""Cycle 7: regression guard for the dead code removed in the cleanup.

The scan flagged orphaned/decorative code: SimpleDualAgent (no importers),
the TaskQueue class (exported, never used), and protocol.UNITY_METHODS (unused,
listed a phantom run_csharp_script). This locks in their removal.
"""
import importlib

import pytest

import unitytools.core as core
import unitytools.core.protocol as protocol


def test_unity_methods_phantom_removed():
    # The stale reference set (with phantom run_csharp_script) is gone.
    assert not hasattr(protocol, "UNITY_METHODS")


def test_taskqueue_export_removed():
    assert "TaskQueue" not in core.__all__
    assert "Task" not in core.__all__
    assert "TaskStatus" not in core.__all__


@pytest.mark.parametrize("mod", [
    "unitytools.core.simple_dual_agent",
    "unitytools.core.task_queue",
])
def test_orphan_modules_deleted(mod):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(mod)


def test_core_public_api_still_intact():
    # the live exports must still import
    from unitytools.core import Config, RpcRequest, RpcResponse, ChatServer  # noqa: F401
