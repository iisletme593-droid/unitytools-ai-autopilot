# -*- coding: utf-8 -*-
"""Dual-agent test with Unity scene manipulation."""
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

def main():
    print("=== DUAL-AGENT + UNITY TEST ===")
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
    
    # Check Unity
    if not unity.ping():
        print("[ERROR] Unity Editor not connected!")
        print("[INFO] Please open Unity Editor and ensure BridgeServer is running")
        return 1
    
    print("[OK] Unity Editor connected")
    print()
    
    # Create dual-agent
    dual = DualAgentOrchestrator(
        config,
        master_model="qwen2.5:14b-instruct",
        worker_model="qwen2.5:7b-instruct",
    )
    
    print("[Dual-Agent] Master: qwen2.5:14b-instruct")
    print("[Dual-Agent] Worker: qwen2.5:7b-instruct")
    print()
    
    # Test: Create objects in Unity
    test_request = "Create 3 cubes in a line along the X axis, spaced 2 units apart"
    print(f"[Request] {test_request}")
    print()
    print("-" * 70)
    
    # Track progress
    master_messages = []
    worker_messages = []
    tool_calls = []
    
    def on_master(msg):
        master_messages.append(msg)
        print(f"[MASTER] {msg}")
    
    def on_worker(msg):
        worker_messages.append(msg)
        print(f"[WORKER] {msg}")
    
    def on_tool(name, params):
        tool_calls.append(name)
        print(f"[TOOL] {name}({list(params.keys())})")
    
    def on_result(name, result):
        ok = isinstance(result, dict) and result.get("ok", True)
        print(f"[RESULT] {name} -> {'SUCCESS' if ok else 'FAILED'}")
    
    try:
        result = dual.chat(
            test_request,
            on_master_thinking=on_master,
            on_worker_executing=on_worker,
            on_tool_call=on_tool,
            on_tool_result=on_result,
            max_iterations=5,
        )
        
        print("-" * 70)
        print()
        print("[RESPONSE]")
        print(result.text)
        print()
        
        # Analysis
        print("=" * 70)
        print("ANALYSIS")
        print("=" * 70)
        print(f"Master messages: {len(master_messages)}")
        for i, msg in enumerate(master_messages, 1):
            print(f"  {i}. {msg[:60]}...")
        
        print(f"\nWorker messages: {len(worker_messages)}")
        for i, msg in enumerate(worker_messages, 1):
            print(f"  {i}. {msg[:60]}...")
        
        print(f"\nTool calls: {len(tool_calls)}")
        for i, tool in enumerate(tool_calls, 1):
            print(f"  {i}. {tool}")
        
        print(f"\nWorker steps: {len(result.worker_reports)}")
        for i, report in enumerate(result.worker_reports, 1):
            success = report.get('success', False)
            desc = report.get('description', 'Unknown')
            print(f"  {i}. [{('SUCCESS' if success else 'FAILED')}] {desc}")
        
        print()
        print("=" * 70)
        
        # Verify
        checks = []
        checks.append(("Master created plan", hasattr(result, 'master_plan') and result.master_plan))
        checks.append(("Worker executed steps", len(result.worker_reports) > 0))
        checks.append(("Tools were called", len(tool_calls) > 0))
        checks.append(("Overall success", result.success))
        
        print("VERIFICATION")
        print("=" * 70)
        all_passed = True
        for check_name, passed in checks:
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {check_name}")
            if not passed:
                all_passed = False
        
        print("=" * 70)
        
        if all_passed:
            print()
            print("*** ALL CHECKS PASSED! DUAL-AGENT WORKING! ***")
            print()
            return 0
        else:
            print()
            print("*** SOME CHECKS FAILED ***")
            print()
            return 1
            
    except Exception as e:
        print()
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
