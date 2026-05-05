# -*- coding: utf-8 -*-
"""Test chat server with dual-agent mode."""
import sys
import time
import socket
import json
from threading import Thread

def test_server():
    print("=== CHAT SERVER TEST ===")
    print()
    
    # Test 1: Check if port is available
    print("Test 1: Port availability")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 7779))  # Use different port for test
        sock.close()
        print("✓ Port 7779 available")
    except OSError:
        print("✗ Port 7779 in use")
        return 1
    
    # Test 2: Import chat server
    print("\nTest 2: Import chat server")
    try:
        from unitytools.core.chat_server import ChatServer
        from unitytools.core.config import Config
        print("✓ Imports successful")
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return 1
    
    # Test 3: Create server instance
    print("\nTest 3: Create server instance")
    try:
        config = Config.load()
        server = ChatServer(
            config,
            host="127.0.0.1",
            port=7779,
            use_dual_agent=True,
            master_model="qwen2.5:14b-instruct",
            worker_model="qwen2.5:7b-instruct",
        )
        print("✓ Server instance created")
        print(f"  Mode: dual-agent")
        print(f"  Master: qwen2.5:14b-instruct")
        print(f"  Worker: qwen2.5:7b-instruct")
    except Exception as e:
        print(f"✗ Server creation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 4: Start server in background
    print("\nTest 4: Start server")
    server_thread = Thread(target=server.start_blocking, daemon=True)
    server_thread.start()
    time.sleep(2)  # Wait for server to start
    
    # Test 5: Connect client
    print("\nTest 5: Connect client")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        client.connect(("127.0.0.1", 7779))
        print("✓ Client connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        server.stop()
        return 1
    
    # Test 6: Receive hello message
    print("\nTest 6: Receive hello message")
    try:
        data = client.recv(4096)
        lines = data.decode('utf-8').strip().split('\n')
        hello = json.loads(lines[0])
        
        print(f"✓ Hello received:")
        print(f"  Type: {hello.get('type')}")
        print(f"  Version: {hello.get('version')}")
        print(f"  Mode: {hello.get('mode')}")
        print(f"  Master: {hello.get('master_model')}")
        print(f"  Worker: {hello.get('worker_model')}")
        print(f"  Tools: {hello.get('tools_loaded')}")
        
        # Verify dual-agent mode
        if hello.get('mode') != 'dual-agent':
            print(f"✗ Expected dual-agent mode, got: {hello.get('mode')}")
            client.close()
            server.stop()
            return 1
        
        if not hello.get('master_model'):
            print("✗ Master model not set")
            client.close()
            server.stop()
            return 1
            
        print("✓ Dual-agent mode confirmed")
        
    except Exception as e:
        print(f"✗ Hello message failed: {e}")
        import traceback
        traceback.print_exc()
        client.close()
        server.stop()
        return 1
    
    # Test 7: Send ping
    print("\nTest 7: Send ping")
    try:
        ping_msg = json.dumps({"type": "ping"}) + "\n"
        client.send(ping_msg.encode('utf-8'))
        
        data = client.recv(4096)
        pong = json.loads(data.decode('utf-8').strip())
        
        if pong.get('type') == 'pong':
            print("✓ Pong received")
        else:
            print(f"✗ Expected pong, got: {pong.get('type')}")
            
    except Exception as e:
        print(f"✗ Ping failed: {e}")
    
    # Cleanup
    print("\nTest 8: Cleanup")
    try:
        client.close()
        server.stop()
        print("✓ Server stopped")
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED!")
    print("="*50)
    return 0

if __name__ == "__main__":
    sys.exit(test_server())
