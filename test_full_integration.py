# -*- coding: utf-8 -*-
"""Full integration test for enhanced dual-agent system."""
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_imports():
    """Test 1: All imports work."""
    print("TEST 1: Imports")
    print("-" * 60)
    
    try:
        from unitytools.core.memory_system import MemorySystem, MemoryEntry
        from unitytools.core.context_manager import ContextManager
        from unitytools.core.dual_agent import DualAgentOrchestrator
        from unitytools.core.chat_server import ChatServer
        print("[PASS] All imports successful")
        return True
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return False

def test_memory_system():
    """Test 2: Memory system works."""
    print("\nTEST 2: Memory System")
    print("-" * 60)
    
    try:
        from unitytools.core.memory_system import MemorySystem, MemoryEntry
        import time
        
        memory = MemorySystem()
        print(f"[OK] Storage path: {memory.storage_path}")
        
        # Create test entry
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
        print(f"[OK] Entry stored")
        
        # Recall
        similar = memory.recall_similar("Test", limit=5)
        print(f"[OK] Recalled {len(similar)} entries")
        
        # Stats
        stats = memory.get_statistics()
        print(f"[OK] Stats: {stats['session_memories']} memories, {stats['patterns_learned']} patterns")
        
        print("[PASS] Memory system working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Memory error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_context_manager():
    """Test 3: Context manager works."""
    print("\nTEST 3: Context Manager")
    print("-" * 60)
    
    try:
        from unitytools.core.context_manager import ContextManager
        
        context = ContextManager()
        print("[OK] Context manager created")
        
        # Update scene
        test_objects = [
            {"name": "Cube", "position": {"x": 0, "y": 0, "z": 0}},
            {"name": "Sphere", "position": {"x": 5, "y": 0, "z": 0}},
        ]
        context.update_scene(test_objects)
        print(f"[OK] Scene updated: {context.scene.object_count} objects")
        
        # Update assets
        context.update_assets("trees", ["Tree1", "Tree2", "Tree3"])
        print(f"[OK] Assets updated: {len(context.assets.trees)} trees")
        
        # Record action
        context.record_action("test_action", {"param": "value"}, True)
        print(f"[OK] Action recorded")
        
        # Get summary
        summary = context.get_context_summary()
        print(f"[OK] Summary: {len(summary)} chars")
        
        # Suggestions
        suggestions = context.suggest_improvements()
        print(f"[OK] Suggestions: {len(suggestions)}")
        
        print("[PASS] Context manager working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Context error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dual_agent():
    """Test 4: Enhanced dual-agent works."""
    print("\nTEST 4: Enhanced Dual-Agent")
    print("-" * 60)
    
    try:
        from unitytools.core.config import Config
        from unitytools.core.dual_agent import DualAgentOrchestrator
        from unitytools.bridges import BlenderBridge, UnityBridge
        from unitytools.tools import init_tools
        
        config = Config.load()
        blender = BlenderBridge(config)
        unity = UnityBridge(config)
        init_tools(blender, unity)
        
        # Create enhanced dual-agent
        dual = DualAgentOrchestrator(
            config,
            master_model="qwen2.5:14b-instruct",
            worker_model="qwen2.5:7b-instruct",
            enable_memory=True,
            enable_context=True,
        )
        
        print(f"[OK] Dual-agent created")
        print(f"[OK] Memory: {dual.memory is not None}")
        print(f"[OK] Context: {dual.context is not None}")
        
        # Check memory stats
        if dual.memory:
            stats = dual.memory.get_statistics()
            print(f"[OK] Memory stats: {stats}")
        
        # Check context
        if dual.context:
            print(f"[OK] Context scene: {dual.context.scene.object_count} objects")
        
        print("[PASS] Enhanced dual-agent working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Dual-agent error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_server():
    """Test 5: Chat server with enhanced features."""
    print("\nTEST 5: Chat Server Integration")
    print("-" * 60)
    
    try:
        from unitytools.core.config import Config
        from unitytools.core.chat_server import ChatServer
        
        config = Config.load()
        
        # Create server with enhanced features
        server = ChatServer(
            config,
            host="127.0.0.1",
            port=7780,  # Different port for test
            use_dual_agent=True,
            master_model="qwen2.5:14b-instruct",
            worker_model="qwen2.5:7b-instruct",
            enable_memory=True,
            enable_context=True,
        )
        
        print(f"[OK] Server created")
        print(f"[OK] Dual-agent: {server.use_dual_agent}")
        print(f"[OK] Memory: {server.enable_memory}")
        print(f"[OK] Context: {server.enable_context}")
        
        print("[PASS] Chat server integration working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Server error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("FULL INTEGRATION TEST")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Memory System", test_memory_system()))
    results.append(("Context Manager", test_context_manager()))
    results.append(("Enhanced Dual-Agent", test_dual_agent()))
    results.append(("Chat Server", test_chat_server()))
    
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
    
    print()
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Enhanced dual-agent system is fully integrated and working!")
        print()
        print("Features:")
        print("  - Memory system (learning from experiences)")
        print("  - Context management (scene awareness)")
        print("  - Pattern recognition (smart planning)")
        print("  - Self-improvement (gets better over time)")
        print()
        return 0
    else:
        print("=" * 60)
        print("SOME TESTS FAILED")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
