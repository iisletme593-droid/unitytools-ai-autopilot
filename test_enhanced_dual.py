# -*- coding: utf-8 -*-
"""Test enhanced dual-agent with memory and context."""
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

def main():
    print("=== ENHANCED DUAL-AGENT TEST ===")
    print()
    
    from unitytools.core.config import Config
    from unitytools.core.dual_agent import DualAgentOrchestrator
    from unitytools.bridges import BlenderBridge, UnityBridge
    from unitytools.tools import init_tools
    
    # Setup
    config = Config.load()
    blender = BlenderBridge(config)
    unity = UnityBridge(config)
    init_tools(blender, unity)
    
    print("[Config] Provider:", config.provider)
    print("[Bridge] Unity:", "Connected" if unity.ping() else "Not connected")
    print()
    
    # Create enhanced dual-agent
    print("[Creating] Enhanced dual-agent with memory and context...")
    dual = DualAgentOrchestrator(
        config,
        master_model="qwen2.5:14b-instruct",
        worker_model="qwen2.5:7b-instruct",
        enable_memory=True,
        enable_context=True,
    )
    
    print("[OK] Master: qwen2.5:14b-instruct")
    print("[OK] Worker: qwen2.5:7b-instruct")
    print("[OK] Memory: Enabled")
    print("[OK] Context: Enabled")
    print()
    
    # Test 1: Simple request
    print("=" * 70)
    print("TEST 1: Simple Request")
    print("=" * 70)
    
    request1 = "List all objects in the scene"
    print(f"Request: {request1}")
    print()
    
    def on_master(msg):
        print(f"[Master] {msg}")
    
    def on_worker(msg):
        print(f"[Worker] {msg}")
    
    try:
        result1 = dual.chat(
            request1,
            on_master_thinking=on_master,
            on_worker_executing=on_worker,
            max_iterations=3,
        )
        
        print()
        print("[Result]", result1.text[:200])
        print()
        
        # Check memory
        if dual.memory:
            stats = dual.memory.get_statistics()
            print(f"[Memory] Session memories: {stats['session_memories']}")
            print(f"[Memory] Patterns learned: {stats['patterns_learned']}")
        
        # Check context
        if dual.context:
            print(f"[Context] Scene objects: {dual.context.scene.object_count}")
            print(f"[Context] Has camera: {dual.context.scene.has_camera}")
            print(f"[Context] Has light: {dual.context.scene.has_light}")
        
        print()
        
    except Exception as e:
        print(f"[Error] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 2: Similar request (should use memory)
    print("=" * 70)
    print("TEST 2: Similar Request (Memory Test)")
    print("=" * 70)
    
    request2 = "Show me all scene objects"
    print(f"Request: {request2}")
    print()
    
    try:
        result2 = dual.chat(
            request2,
            on_master_thinking=on_master,
            on_worker_executing=on_worker,
            max_iterations=3,
        )
        
        print()
        print("[Result]", result2.text[:200])
        print()
        
        # Check if memory was used
        if dual.memory:
            similar = dual.memory.recall_similar(request2, limit=3)
            print(f"[Memory] Recalled {len(similar)} similar experiences")
            for exp in similar:
                print(f"  - {exp.request[:50]}... (success={exp.success})")
            
            stats = dual.memory.get_statistics()
            print(f"[Memory] Total patterns: {stats['patterns_learned']}")
        
        print()
        
    except Exception as e:
        print(f"[Error] {e}")
        return 1
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if dual.memory:
        stats = dual.memory.get_statistics()
        print(f"Memory Statistics:")
        print(f"  - Session memories: {stats['session_memories']}")
        print(f"  - Patterns learned: {stats['patterns_learned']}")
        print(f"  - Total occurrences: {stats['total_occurrences']}")
        print(f"  - Avg success rate: {stats['average_success_rate']:.2%}")
    
    if dual.context:
        print(f"\nContext Statistics:")
        print(f"  - Scene objects: {dual.context.scene.object_count}")
        print(f"  - Recent actions: {len(dual.context.history.get_recent(10))}")
        
        suggestions = dual.context.suggest_improvements()
        if suggestions:
            print(f"  - Suggestions: {len(suggestions)}")
            for sug in suggestions[:3]:
                print(f"    * {sug}")
    
    print()
    print("=" * 70)
    print("ENHANCED DUAL-AGENT TEST COMPLETED!")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
