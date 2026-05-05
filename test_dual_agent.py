#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test script for dual-agent mode."""
import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")

from unitytools.core.config import Config
from unitytools.core.dual_agent import DualAgentOrchestrator
from unitytools.bridges import BlenderBridge, UnityBridge
from unitytools.tools import init_tools

def main():
    print("Testing Dual-Agent Mode...")
    print("=" * 60)
    
    # Load config
    config = Config.load()
    if config.provider != "ollama":
        print("âŒ Dual-agent requires UNITYTOOLS_PROVIDER=ollama")
        return 1
    
    # Initialize bridges and tools
    blender = BlenderBridge(config)
    unity = UnityBridge(config)
    init_tools(blender, unity)
    
    # Create dual-agent orchestrator with Qwen 2.5:14b master
    dual = DualAgentOrchestrator(
        config,
        master_model="qwen2.5:14b-instruct",        # Powerful planner (10-30s)
        worker_model="qwen2.5:14b-instruct",  # Fast executor
    )
    
    print("[OK] Master: qwen2.5:14b-instruct (powerful planner)")
    print("[OK] Worker: qwen2.5:14b-instruct (fast executor)")
    print("[OK] Unity:", "Connected" if unity.ping() else "Not connected")
    print("=" * 60)
    print("[INFO] Master may take 10-30s for planning - this is normal!")
    print("[INFO] Good planning = fewer errors = better results")
    print("=" * 60)
    
    # Test request - something that benefits from good planning
    test_request = "Create a small forest with realistic trees"
    print(f"\nTest Request: {test_request}")
    print("[INFO] This requires: asset search, scene analysis, placement strategy")
    print("[INFO] Master will create detailed plan, worker will execute\n")
    
    def on_master(msg):
        print(f"[Master] {msg}")
    
    def on_worker(msg):
        print(f"[Worker] {msg}")
    
    def on_tool(name, params):
        print(f"[Tool] {name}")
    
    def on_result(name, result):
        if isinstance(result, dict) and result.get("ok"):
            print(f"[OK] {name} succeeded")
        else:
            print(f"[FAIL] {name} failed")
    
    try:
        result = dual.chat(
            test_request,
            on_master_thinking=on_master,
            on_worker_executing=on_worker,
            on_tool_call=on_tool,
            on_tool_result=on_result,
        )
        
        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(result.text)
        print("\n" + "=" * 60)
        print(f"Steps: {len(result.worker_reports)}")
        print(f"Tools: {len(result.tool_calls)}")
        print(f"Success: {'YES' if result.success else 'NO'}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

