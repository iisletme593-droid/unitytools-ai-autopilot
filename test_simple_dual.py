# -*- coding: utf-8 -*-
"""Test simple dual-agent routing."""
import sys
from unitytools.core.config import Config
from unitytools.core.simple_dual_agent import SimpleDualAgent
from unitytools.bridges import BlenderBridge, UnityBridge
from unitytools.tools import init_tools

def main():
    print("Testing Simple Dual-Agent Routing...")
    print("=" * 60)
    
    config = Config.load()
    blender = BlenderBridge(config)
    unity = UnityBridge(config)
    init_tools(blender, unity)
    
    dual = SimpleDualAgent(
        config,
        complex_model="qwen2.5:14b-instruct",  # Use 14b for complex
        simple_model="qwen2.5:7b-instruct",    # Use 7b for simple
    )
    
    print("[OK] Complex model: qwen2.5:14b-instruct")
    print("[OK] Simple model: qwen2.5:7b-instruct")
    print("[OK] Unity:", "Connected" if unity.ping() else "Not connected")
    print("=" * 60)
    
    # Test simple request
    test_request = "List all objects in the scene"
    print(f"\nTest: {test_request}")
    
    def on_model(model):
        print(f"[Router] Selected model: {model}")
    
    def on_tool(name, params):
        print(f"[Tool] {name}")
    
    def on_result(name, result):
        ok = isinstance(result, dict) and result.get("ok", True)
        print(f"[{'OK' if ok else 'FAIL'}] {name}")
    
    try:
        result = dual.chat(
            test_request,
            on_model_selected=on_model,
            on_tool_call=on_tool,
            on_tool_result=on_result,
        )
        
        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(result.text[:500])  # First 500 chars
        print("=" * 60)
        print(f"Tools called: {len(result.tool_calls)}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
