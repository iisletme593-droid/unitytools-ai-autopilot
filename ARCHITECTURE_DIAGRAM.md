# 🏗️ UnityTools AI - Sistem Mimarisi

## 📊 Genel Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                        UNITY EDITOR                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  ChatWindow.cs (AI Panel)                              │    │
│  │  - User input                                           │    │
│  │  - Message display                                      │    │
│  │  - Dual-agent status                                    │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │ TCP 7778                                  │
│  ┌──────────────────▼─────────────────────────────────────┐    │
│  │  BridgeServer.cs (Unity Command Bridge)                │    │
│  │  - Receives tool calls                                  │    │
│  │  - Executes Unity commands                              │    │
│  │  - Returns results                                      │    │
│  └──────────────────▲─────────────────────────────────────┘    │
│                     │ TCP 7777                                  │
└─────────────────────┼─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                   PYTHON CHAT CORE                             │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  ChatServer (unitytools/core/chat_server.py)           │   │
│  │  - WebSocket server (port 7778)                        │   │
│  │  - Message routing                                      │   │
│  │  - Dual-agent orchestration                            │   │
│  └──────────────────┬─────────────────────────────────────┘   │
│                     │                                           │
│  ┌──────────────────▼─────────────────────────────────────┐   │
│  │  DualAgentOrchestrator                                  │   │
│  │  (unitytools/core/dual_agent.py)                       │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────┐    │   │
│  │  │  MASTER AGENT (Qwen 2.5:14b - 9GB)               │    │   │
│  │  │  ┌──────────────────────────────────────────┐ │    │   │
│  │  │  │  1. Context Analysis                     │ │    │   │
│  │  │  │     - Scene state                        │ │    │   │
│  │  │  │     - Available assets                   │ │    │   │
│  │  │  │     - Recent actions                     │ │    │   │
│  │  │  └──────────────────────────────────────────┘ │    │   │
│  │  │  ┌──────────────────────────────────────────┐ │    │   │
│  │  │  │  2. Memory Recall                        │ │    │   │
│  │  │  │     - Similar experiences                │ │    │   │
│  │  │  │     - Learned lessons                    │ │    │   │
│  │  │  │     - Success patterns                   │ │    │   │
│  │  │  └──────────────────────────────────────────┘ │    │   │
│  │  │  ┌──────────────────────────────────────────┐ │    │   │
│  │  │  │  3. Deep Planning (10-30s)               │ │    │   │
│  │  │  │     - Analyze request                    │ │    │   │
│  │  │  │     - Detect edge cases                  │ │    │   │
│  │  │  │     - Create detailed plan               │ │    │   │
│  │  │  │     - Prepare fallbacks                  │ │    │   │
│  │  │  └──────────────────────────────────────────┘ │    │   │
│  │  │  ┌──────────────────────────────────────────┐ │    │   │
│  │  │  │  4. JSON Plan Output                     │ │    │   │
│  │  │  │     {                                     │ │    │   │
│  │  │  │       "task": "...",                      │ │    │   │
│  │  │  │       "steps": [...]                      │ │    │   │
│  │  │  │     }                                     │ │    │   │
│  │  │  └──────────────────────────────────────────┘ │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  │                     │                                    │   │
│  │                     │ Plan                               │   │
│  │                     â–¼                                    │   │
│  │  ┌────────────────────────────────────────────────┐    │   │
│  │  │  WORKER AGENT (Qwen 2.5:14b - 9GB)            │    │   │
│  │  │  ┌──────────────────────────────────────────┐ │    │   │
│  │  │  │  1. Receive Plan                         │ │    │   │
│  │  │  │     - Parse steps                        │ │    │   │
│  │  │  │     - Understand parameters              │ │    │   │
│  │  │  └──────────────────────────────────────────┘ │    │   │
│  │  │  ┌──────────────────────────────────────────┐ │    │   │
│  │  │  │  2. Execute Steps (Fast)                 │ │    │   │
│  │  │  │     - Call Unity tools                   │ │    │   │
│  │  │  │     - Call Blender tools                 │ │    │   │
│  │  │  │     - Handle errors                      │ │    │   │
│  │  │  └──────────────────────────────────────────┘ │    │   │
│  │  │  ┌──────────────────────────────────────────┐ │    │   │
│  │  │  │  3. Report Results                       │ │    │   │
│  │  │  │     {                                     │ │    │   │
│  │  │  │       "step_id": 1,                       │ │    │   │
│  │  │  │       "success": true,                    │ │    │   │
│  │  │  │       "tool_calls": [...]                 │ │    │   │
│  │  │  │     }                                     │ │    │   │
│  │  │  └──────────────────────────────────────────┘ │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  │                     │                                    │   │
│  │                     │ Reports                            │   │
│  │                     â–¼                                    │   │
│  │  ┌────────────────────────────────────────────────┐    │   │
│  │  │  MASTER AGENT                                   │    │   │
│  │  │  - Summarize results                            │    │   │
│  │  │  - Quality check                                │    │   │
│  │  │  - User response                                │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  │                     │                                    │   │
│  │                     │ Learn & Update                     │   │
│  │                     â–¼                                    │   │
│  │  ┌────────────────────────────────────────────────┐    │   │
│  │  │  MEMORY SYSTEM                                  │    │   │
│  │  │  (unitytools/core/memory_system.py)            │    │   │
│  │  │  - Store experience                             │    │   │
│  │  │  - Update patterns                              │    │   │
│  │  │  - Calculate success rate                       │    │   │
│  │  │  - Learn lessons                                │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────┐    │   │
│  │  │  CONTEXT MANAGER                                │    │   │
│  │  │  (unitytools/core/context_manager.py)          │    │   │
│  │  │  - Update scene state                           │    │   │
│  │  │  - Track assets                                 │    │   │
│  │  │  - Record actions                               │    │   │
│  │  │  - Generate suggestions                         │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────────────────────────┘   │
│                     │                                           │
│  ┌──────────────────▼─────────────────────────────────────┐   │
│  │  UnityBridge (unitytools/bridges/unity.py)             │   │
│  │  - TCP client to Unity (port 7777)                     │   │
│  │  - 60+ Unity tools                                      │   │
│  │  - GameObject, Transform, Components, etc.             │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  BlenderBridge (unitytools/bridges/blender.py)         │   │
│  │  - Headless Blender execution                          │   │
│  │  - FBX export/import                                    │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                   PERSISTENT STORAGE                           │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  ~/.unitytools/memory/                                  │   │
│  │  ├── long_term_memory.jsonl  (All experiences)         │   │
│  │  └── patterns.json            (Learned patterns)       │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 İşlem Akışı

### 1. Kullanıcı İsteği

```
User: "Create a forest with 20 trees"
  │
  â–¼
Unity ChatWindow
  │
  â–¼ (TCP 7778)
ChatServer
  │
  â–¼
DualAgentOrchestrator
```

### 2. Context & Memory

```
DualAgentOrchestrator
  │
  ├─► ContextManager.get_context_summary()
  │   └─► Scene: 5 objects, Has camera, Has light
  │
  └─► MemorySystem.recall_similar("Create forest")
      └─► Found 2 similar experiences (100% success)
```

### 3. Master Planning

```
Master Agent (Qwen 2.5:14b)
  │
  ├─► Analyze request
  │   └─► "forest" + "20 trees" → Need tree assets
  │
  ├─► Check context
  │   └─► Scene has space, no trees yet
  │
  ├─► Recall memory
  │   └─► Previous forest creation: search assets first
  │
  ├─► Create plan (10-30s)
  │   └─► Step 1: Search tree assets
  │       Step 2: Analyze scene
  │       Step 3: Create forest with scatter
  │
  └─► Output JSON plan
```

### 4. Worker Execution

```
Worker Agent (Qwen 2.5:14b)
  │
  ├─► Step 1: unity_find_tree_assets()
  │   └─► Found 5 tree types
  │
  ├─► Step 2: unity_list_scene_objects()
  │   └─► Scene bounds: 20x20
  │
  └─► Step 3: unity_create_forest_from_assets()
      └─► Created 20 trees with natural scatter
```

### 5. Master Summary

```
Master Agent
  │
  ├─► Review worker reports
  │   └─► All steps successful
  │
  ├─► Quality check
  │   └─► 20 trees created, natural distribution
  │
  └─► User response
      └─► "Created a forest with 20 trees using 5 different types..."
```

### 6. Learn & Update

```
MemorySystem
  │
  ├─► Store experience
  │   └─► Request: "Create forest"
  │       Success: true
  │       Duration: 45s
  │       Tools: [find_tree_assets, create_forest]
  │
  └─► Update pattern
      └─► Pattern: "create_forest"
          Success rate: 100% (3/3)
          Best approach: Search assets → Create with scatter

ContextManager
  │
  ├─► Update scene
  │   └─► Object count: 5 → 25
  │
  ├─► Update assets
  │   └─► Trees: 5 types known
  │
  └─► Record action
      └─► Action: create_forest
          Success: true
```

---

## 📊 Data Flow

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │ Request
       â–¼
┌─────────────┐
│   Unity     │
│  ChatWindow │
└──────┬──────┘
       │ WebSocket
       â–¼
┌─────────────┐
│ ChatServer  │
└──────┬──────┘
       │
       â–¼
┌─────────────────────────────────────┐
│     DualAgentOrchestrator           │
│                                     │
│  ┌─────────────┐  ┌──────────────┐ │
│  │   Context   │  │    Memory    │ │
│  │   Manager   │  │    System    │ │
│  └──────┬──────┘  └──────┬───────┘ │
│         │                │          │
│         └────────┬───────┘          │
│                  â–¼                  │
│         ┌────────────────┐          │
│         │ Master Agent   │          │
│         │  (Planning)    │          │
│         └────────┬───────┘          │
│                  │ Plan             │
│                  â–¼                  │
│         ┌────────────────┐          │
│         │ Worker Agent   │          │
│         │  (Execution)   │          │
│         └────────┬───────┘          │
│                  │ Reports          │
│                  â–¼                  │
│         ┌────────────────┐          │
│         │ Master Agent   │          │
│         │  (Summary)     │          │
│         └────────┬───────┘          │
│                  │                  │
│         ┌────────┴───────┐          │
│         â–¼                â–¼          │
│  ┌──────────┐    ┌──────────┐      │
│  │ Memory   │    │ Context  │      │
│  │ Update   │    │ Update   │      │
│  └──────────┘    └──────────┘      │
└─────────────────────────────────────┘
       │
       â–¼
┌─────────────┐
│ UnityBridge │
│   (Tools)   │
└──────┬──────┘
       │ RPC
       â–¼
┌─────────────┐
│   Unity     │
│   Editor    │
└─────────────┘
```

---

## 🧠 Memory System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              MEMORY SYSTEM                               │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Short-term Memory (Session)                   │    │
│  │  - Current session experiences                 │    │
│  │  - Temporary patterns                          │    │
│  │  - Quick recall                                │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│                     │ Persist                            │
│                     â–¼                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Long-term Memory (Persistent)                 │    │
│  │  ~/.unitytools/memory/long_term_memory.jsonl   │    │
│  │  - All experiences                             │    │
│  │  - Success/failure records                     │    │
│  │  - Tool usage history                          │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│                     │ Analyze                            │
│                     â–¼                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Pattern Recognition                           │    │
│  │  - Classify request types                      │    │
│  │  - Extract signatures                          │    │
│  │  - Calculate success rates                     │    │
│  │  - Identify common pitfalls                    │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│                     │ Store                              │
│                     â–¼                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Learned Patterns                              │    │
│  │  ~/.unitytools/memory/patterns.json            │    │
│  │  {                                             │    │
│  │    "create_forest": {                          │    │
│  │      "success_rate": 0.95,                     │    │
│  │      "occurrences": 20,                        │    │
│  │      "best_approach": {...},                   │    │
│  │      "common_pitfalls": [...]                  │    │
│  │    }                                           │    │
│  │  }                                             │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│                     │ Recall                             │
│                     â–¼                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Master Agent Planning                         │    │
│  │  - Use learned patterns                        │    │
│  │  - Avoid known pitfalls                        │    │
│  │  - Apply best approaches                       │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 🗺️ Context Manager Architecture

```
┌─────────────────────────────────────────────────────────┐
│            CONTEXT MANAGER                               │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Scene Context                                  │    │
│  │  - Object count                                │    │
│  │  - Scene bounds                                │    │
│  │  - Has camera/light                            │    │
│  │  - Density estimation                          │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Asset Context                                  │    │
│  │  - Trees: [Oak, Pine, Birch, ...]             │    │
│  │  - Rocks: [Boulder1, Rock2, ...]              │    │
│  │  - Props: [Barrel, Crate, ...]                │    │
│  │  - Characters: [Player, Enemy, ...]           │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Action History                                 │    │
│  │  - Last 50 actions                             │    │
│  │  - Success/failure tracking                    │    │
│  │  - Tool usage patterns                         │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│                     │ Analyze                            │
│                     â–¼                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Context Summary                                │    │
│  │  "Scene: 15 objects                            │    │
│  │   Assets: 5 trees, 3 rocks                     │    │
│  │   Recent: 3 successful actions"                │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│                     │ Suggest                            │
│                     â–¼                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Smart Suggestions                              │    │
│  │  - "Add lighting"                              │    │
│  │  - "Scene is dense, consider optimization"    │    │
│  │  - "Clear area available at (10, 0, 10)"      │    │
│  └────────────────────────────────────────────────┘    │
│                     │                                    │
│                     │ Provide                            │
│                     â–¼                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Master Agent Planning                         │    │
│  │  - Use scene state                             │    │
│  │  - Consider available assets                   │    │
│  │  - Learn from recent actions                   │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Component Interaction

```
┌──────────────┐
│    User      │
└──────┬───────┘
       │
       â–¼
┌──────────────────────────────────────────────────────┐
│  Unity ChatWindow                                     │
│  - Displays dual-agent status                        │
│  - Shows master/worker progress                      │
│  - Renders tool calls and results                    │
└──────┬───────────────────────────────────────────────┘
       │
       â–¼
┌──────────────────────────────────────────────────────┐
│  ChatServer                                           │
│  - Routes messages                                    │
│  - Manages dual-agent orchestrator                   │
│  - Handles WebSocket connections                     │
└──────┬───────────────────────────────────────────────┘
       │
       â–¼
┌──────────────────────────────────────────────────────┐
│  DualAgentOrchestrator                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │  Context   │  │   Memory   │  │   Master   │    │
│  │  Manager   │◄─┤   System   │◄─┤   Agent    │    │
│  └────────────┘  └────────────┘  └──────┬─────┘    │
│                                          │           │
│                                          â–¼           │
│                                   ┌────────────┐    │
│                                   │   Worker   │    │
│                                   │   Agent    │    │
│                                   └──────┬─────┘    │
│                                          │           │
│  ┌────────────┐  ┌────────────┐        │           │
│  │  Context   │◄─┤   Memory   │◄───────┘           │
│  │  Update    │  │   Update   │                     │
│  └────────────┘  └────────────┘                     │
└──────┬───────────────────────────────────────────────┘
       │
       â–¼
┌──────────────────────────────────────────────────────┐
│  UnityBridge / BlenderBridge                         │
│  - Execute tools                                      │
│  - Return results                                     │
└──────┬───────────────────────────────────────────────┘
       │
       â–¼
┌──────────────┐
│ Unity Editor │
└──────────────┘
```

---

**Mimari Versiyon**: 2.3.0  
**Son Güncelleme**: 2026-05-05  
**Durum**: Production Ready ✅

