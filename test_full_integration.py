# -*- coding: utf-8 -*-
"""Full integration test for enhanced dual-agent system."""
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"


def test_imports():
    from unitytools.core.chat_server import ChatServer
    from unitytools.core.context_manager import ContextManager
    from unitytools.core.dual_agent import DualAgentOrchestrator
    from unitytools.core.memory_system import MemoryEntry, MemorySystem

    assert ChatServer
    assert ContextManager
    assert DualAgentOrchestrator
    assert MemoryEntry
    assert MemorySystem


def test_memory_system():
    import time

    from unitytools.core.memory_system import MemoryEntry, MemorySystem

    memory = MemorySystem()
    entry = MemoryEntry(
        timestamp=time.time(),
        request="Test request",
        plan={"steps": []},
        execution={},
        success=True,
        duration=1.0,
        tools_used=["test_tool"],
        errors=[],
        lessons=[],
    )

    memory.remember(entry)
    similar = memory.recall_similar("Test", limit=5)
    stats = memory.get_statistics()

    assert isinstance(similar, list)
    assert stats["session_memories"] >= 1
    assert "patterns_learned" in stats


def test_context_manager():
    from unitytools.core.context_manager import ContextManager

    context = ContextManager()
    context.update_scene([
        {"name": "Cube", "position": {"x": 0, "y": 0, "z": 0}},
        {"name": "Sphere", "position": {"x": 5, "y": 0, "z": 0}},
    ])
    context.update_assets("trees", ["Tree1", "Tree2", "Tree3"])
    context.record_action("test_action", {"param": "value"}, True)

    assert context.scene.object_count == 2
    assert len(context.assets.trees) == 3
    assert context.get_context_summary()
    assert isinstance(context.suggest_improvements(), list)


def test_dual_agent():
    from unitytools.bridges import BlenderBridge, UnityBridge
    from unitytools.core.config import Config
    from unitytools.core.dual_agent import DualAgentOrchestrator
    from unitytools.tools import init_tools

    config = Config.load()
    blender = BlenderBridge(config)
    unity = UnityBridge(config)
    init_tools(blender, unity)

    dual = DualAgentOrchestrator(
        config,
        master_model="qwen2.5:14b-instruct",
        worker_model="qwen2.5:7b-instruct",
        enable_memory=True,
        enable_context=True,
    )

    assert dual.memory is not None
    assert dual.context is not None
    assert isinstance(dual.memory.get_statistics(), dict)


def test_chat_server():
    from unitytools.core.chat_server import ChatServer
    from unitytools.core.config import Config

    config = Config.load()
    server = ChatServer(
        config,
        host="127.0.0.1",
        port=7780,
        use_dual_agent=True,
        master_model="qwen2.5:14b-instruct",
        worker_model="qwen2.5:7b-instruct",
        enable_memory=True,
        enable_context=True,
    )

    assert server.use_dual_agent is True
    assert server.enable_memory is True
    assert server.enable_context is True


def main():
    tests = [
        test_imports,
        test_memory_system,
        test_context_manager,
        test_dual_agent,
        test_chat_server,
    ]
    for fn in tests:
        fn()
    return 0


if __name__ == "__main__":
    sys.exit(main())
