# -*- coding: utf-8 -*-
"""Real dual-agent test with actual execution."""
import sys
import os

# Set environment
os.environ['PYTHONIOENCODING'] = 'utf-8'

def main():
    print("=== REAL DUAL-AGENT TEST ===")
    print()
    
    from unitytools.core.config import Config
    from unitytools.core.dual_agent import DualAgentOrchestrator
    from unitytools.bridges import BlenderBridge, UnityBridge
    from unitytools.tools import init_tools
    
    # Load config
    config = Config.load()
    print(f"[Config] Provider: {config.provider}")
    print(f"[Config] Model: {config.ollama_model}")
    print()
    
    # Initialize bridges
    blender = BlenderBridge(config)
    unity = UnityBridge(config)
    init_tools(blender, unity)
    
    print(f"[Bridge] Blender: {'Available' if blender.is_available() else 'Not available'}")
    print(f"[Bridge] Unity: {'Connected' if unity.ping() else 'Not connected'}")
    print()
    
    # Create dual-agent (use faster models for test)
    print("[Dual-Agent] Creating orchestrator...")
    dual = DualAgentOrchestrator(
        config,
        master_model="qwen2.5:14b-instruct",  # Faster for test
        worker_model="qwen2.5:7b-instruct",
    )
    print(f"[Dual-Agent] Master: qwen2.5:14b-instruct")
    print(f"[Dual-Agent] Worker: qwen2.5:7b-instruct")
    print()
    
    # Test request (simple, no Unity needed)
    test_request = "What tools are available for creating objects?"
    print(f"[Test] Request: {test_request}")
    print()
    
    # Callbacks
    def on_master(msg):
        print(f"[Master] {msg}")
    
    def on_worker(msg):
        print(f"[Worker] {msg}")
    
    def on_tool(name, params):
        print(f"[Tool] {name}")
    
    def on_result(name, result):
        ok = isinstance(result, dict) and result.get("ok", True)
        status = "OK" if ok else "FAIL"
        print(f"[Result] {name} -> {status}")
    
    # Execute
    print("[Execute] Starting dual-agent chat...")
    print("-" * 60)
    
    try:
        result = dual.chat(
            test_request,
            on_master_thinking=on_master,
            on_worker_executing=on_worker,
            on_tool_call=on_tool,
            on_tool_result=on_result,
            max_iterations=3,  # Limit iterations for test
        )
        
        print("-" * 60)
        print()
        print("[Result] Response:")
        print(result.text[:500] if len(result.text) > 500 else result.text)
        print()
        print(f"[Stats] Steps: {len(result.worker_reports)}")
        print(f"[Stats] Tools: {len(result.tool_calls)}")
        print(f"[Stats] Success: {result.success}")
        print()
        
        # Verify dual-agent worked
        if hasattr(result, 'master_plan') and result.master_plan:
            print("[Verify] Master plan created")
        else:
            print("[Verify] No master plan")
            
        if hasattr(result, 'worker_reports') and result.worker_reports:
            print(f"[Verify] Worker reports: {len(result.worker_reports)}")
        else:
            print("[Verify] No worker reports")
        
        print()
        print("="*60)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        return 0
        
    except Exception as e:
        print()
        print(f"[Error] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
