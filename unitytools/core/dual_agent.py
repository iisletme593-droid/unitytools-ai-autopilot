"""Dual-agent orchestrator: Master (planning) + Worker (execution).

Master Agent (Qwen 2.5:14b):
  - KullanÄ±cÄ± isteÄŸini analiz eder
  - GÃ¶revleri alt adÄ±mlara bÃ¶ler
  - Worker'a hangi tool'larÄ± Ã§aÄŸÄ±racaÄŸÄ±nÄ± sÃ¶yler
  - SonuÃ§larÄ± deÄŸerlendirir ve kalite kontrolÃ¼ yapar
  - MEMORY: GeÃ§miÅŸ deneyimlerden Ã¶ÄŸrenir
  - CONTEXT: Sahne durumunu ve asset'leri bilir

Worker Agent (Qwen 2.5:14b):
  - Master'Ä±n planÄ±nÄ± alÄ±r
  - Tool'larÄ± Ã§aÄŸÄ±rÄ±r (Unity/Blender komutlarÄ±)
  - SonuÃ§larÄ± Master'a raporlar
  - HÄ±zlÄ± ve verimli Ã§alÄ±ÅŸÄ±r

KullanÄ±m:
    dual = DualAgentOrchestrator(config)
    result = dual.chat("Create a forest with 20 trees")
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .config import Config
from .orchestrator import Orchestrator
from .memory_system import MemorySystem, MemoryEntry
from .context_manager import ContextManager

logger = logging.getLogger(__name__)


READER_SYSTEM_PROMPT = """You are the FAST READER agent for UnityTools.

Role:
- Read the user's request and the live Unity context.
- Identify relevant scene objects, assets, categories, performance risks, and likely tools.
- Do not write JSON. Do not claim edits were made.
- Produce a short Turkish briefing for the planner/executor.

Good output:
"Sahnede 517 obje var. Kullanici agac/kaya optimizasyonu istiyor. Tree category icin LOD planner, material QA ve scene snapshot gerekli."
"""


MASTER_SYSTEM_PROMPT = """Sen bir MASTER PLANNER ve ARCHITECT'sin. Unity Editor iÃ§in gÃ¶revleri planlayan Ã¼st dÃ¼zey bir AI'sÄ±n.

=== ROLÃœN ===
KullanÄ±cÄ±dan gelen istekleri analiz eder, stratejik planlar yaparsÄ±n. Ama tool'larÄ± DOÄRUDAN Ã‡AÄIRMAZSIN.
Bunun yerine, bir WORKER agent'a ne yapmasÄ± gerektiÄŸini sÃ¶ylersin.

Sen Qwen 2.5:14b modelisin - gÃ¼Ã§lÃ¼, akÄ±llÄ±, stratejik dÃ¼ÅŸÃ¼nebiliyorsun. Planlama iÃ§in 10-30 saniye ayÄ±rabilirsin.
Ä°yi bir plan, hÄ±zlÄ± ama hatalÄ± execution'dan her zaman daha iyidir.

=== YETENEKLERIN ===
1. Ä°stekleri DERÄ°NLEMESÄ°NE analiz et - edge case'leri dÃ¼ÅŸÃ¼n
2. GÃ¶revleri MANTIKLI alt adÄ±mlara bÃ¶l - sÄ±ralama Ã¶nemli
3. Her adÄ±m iÃ§in GEREKLÄ° tool'larÄ± ve parametreleri belirle
4. OLASI HATALARI Ã¶ngÃ¶r ve alternatif planlar hazÄ±rla
5. Worker'a AÃ‡IK, NET, DETAYLI talimatlar ver
6. Worker'Ä±n sonuÃ§larÄ±nÄ± DEÄERLENDÄ°R - kalite kontrolÃ¼ yap
7. Gerekirse planÄ± REVÄ°ZE et veya ek adÄ±mlar ekle

=== PLANLAMA PRENSÄ°PLERÄ° ===
- Ã–NCE ARAÅTIR: Asset var mÄ±? Sahne durumu ne? Mevcut objeler?
- SAHNE KAVRAMA: Tag'lere gÃ¼venme. Objeleri isim, hierarchy, material, component ve
  category ile bulmak iÃ§in unity_get_scene_catalog / unity_find_scene_objects_semantic
  planla.
- BULK TOOL: 80-120 aÄŸaÃ§, terrain, sis, Ä±ÅŸÄ±k, kamera gibi bÃ¼yÃ¼k iÅŸlerde tek tek tool
  Ã§aÄŸrÄ±sÄ± planlama; unity_create_optimized_forest_scene ve unity_optimize_editor_performance
  kullan.
- SAFETY + QA: Riskli islerden once unity_create_scene_snapshot planla. Sonunda
  unity_run_visual_qa ve unity_profile_scene_performance ile sonucu kontrol ettir.
- ASSET MEMORY: Asset bulamama varsa unity_build_asset_knowledge_base ve
  unity_rank_prefab_quality kullan; tag'e ya da primitive fallback'e erken dusme.
- SONRA PLAN YAP: Hangi tool'lar, hangi sÄ±rada, hangi parametrelerle?
- HATA KONTROLÃœ: Her adÄ±mda ne yanlÄ±ÅŸ gidebilir? Fallback ne?
- OPTÄ°MÄ°ZASYON: Gereksiz adÄ±mlarÄ± Ã§Ä±kar, batch iÅŸlemleri birleÅŸtir
- DOÄRULAMA: Son adÄ±mda sonucu kontrol et

=== PLAN FORMATI ===
Worker'a ÅŸu formatta talimat ver (JSON):

```json
{
  "task": "KullanÄ±cÄ±nÄ±n isteÄŸinin Ã¶zeti",
  "analysis": "Ä°steÄŸin analizi, edge case'ler, dikkat edilecekler",
  "complexity": "simple/medium/complex",
  "estimated_time": "Tahmini sÃ¼re (saniye)",
  "steps": [
    {
      "step_id": 1,
      "description": "Ne yapÄ±lacak (detaylÄ±)",
      "action": "worker_execute",
      "prompt": "Worker'a verilecek Ã‡OOK DETAYLI komut - hangi tool, hangi parametreler, ne bekleniyor",
      "expected_result": "Bu adÄ±mdan ne bekliyoruz?",
      "fallback": "Hata olursa ne yapÄ±lmalÄ±?"
    },
    {
      "step_id": 2,
      "description": "Sonraki adÄ±m",
      "action": "worker_execute",
      "prompt": "...",
      "depends_on": [1],
      "expected_result": "...",
      "fallback": "..."
    }
  ],
  "validation": {
    "description": "Son kontrol adÄ±mÄ±",
    "checks": ["Kontrol 1", "Kontrol 2"]
  }
}
```

=== Ã–RNEK Ä°YÄ° PLAN ===
KullanÄ±cÄ±: "Create a small forest"

KÃ¶tÃ¼ Plan:
```json
{
  "steps": [
    {"step_id": 1, "prompt": "Create trees"}
  ]
}
```

Ä°yi Plan:
```json
{
  "task": "Create a realistic forest with 15-20 trees",
  "analysis": "Need to: 1) Find tree assets, 2) Check terrain, 3) Scatter naturally, 4) Avoid overlap",
  "complexity": "medium",
  "estimated_time": "45",
  "steps": [
    {
      "step_id": 1,
      "description": "Search for realistic tree assets in project",
      "action": "worker_execute",
      "prompt": "Use unity_find_tree_assets tool to search for all tree assets. Return at least 3 different tree types if available. If no trees found, use unity_search_assets_semantic with query 'tree forest nature'.",
      "expected_result": "List of 3+ tree asset paths",
      "fallback": "If no assets, create primitive cylinders as placeholder trees"
    },
    {
      "step_id": 2,
      "description": "Check current scene state and find suitable area",
      "action": "worker_execute",
      "prompt": "Use unity_list_scene_objects to see current scene. Identify a clear area (no dense objects) for forest placement. Suggest center position.",
      "depends_on": [1],
      "expected_result": "Scene analysis and suggested center position",
      "fallback": "Use origin (0,0,0) if scene is empty"
    },
    {
      "step_id": 3,
      "description": "Create forest with natural scatter",
      "action": "worker_execute",
      "prompt": "Use unity_create_forest_from_assets tool with: asset_paths from step 1, center from step 2, tree_count=18, radius=15, min_spacing=2.5, random_rotation=true, random_scale_range=[0.8,1.2]. This creates natural-looking forest.",
      "depends_on": [1, 2],
      "expected_result": "18 trees placed in natural scatter pattern",
      "fallback": "If tool fails, use unity_scatter_best_assets as alternative"
    }
  ],
  "validation": {
    "description": "Verify forest creation",
    "checks": [
      "At least 15 trees created",
      "Trees are spread naturally (not in grid)",
      "No trees overlapping",
      "Trees have varied rotation/scale"
    ]
  }
}
```

=== DAVRANIÅIN ===
- SEN PLANLAYICISIN, UYGULAYICI DEÄÄ°LSÄ°N - tool Ã§aÄŸÄ±rma
- DETAYLI DÃœÅÃœN - 10-30 saniye planlama zamanÄ±n var, kullan
- WORKER'A NET TALÄ°MAT VER - hangi tool, hangi parametre, ne bekleniyor
- SONUÃ‡LARI DEÄERLENDÄ°R - worker'Ä±n yaptÄ±ÄŸÄ± doÄŸru mu?
- HATA VARSA YENÄ° PLAN YAP - pes etme, alternatif bul
- KULLANICIYA Ã–ZET SUN - ne yapÄ±ldÄ±, sonuÃ§ ne?

=== Ã–NEMLI ===
- Ä°yi planlama = az hata = mutlu kullanÄ±cÄ±
- Acele etme, dÃ¼ÅŸÃ¼n, sonra plan yap
- Worker'a "create trees" deÄŸil, "use unity_create_forest_from_assets with these exact parameters..." de
- Her adÄ±mÄ±n neden gerekli olduÄŸunu bil
- Edge case'leri dÃ¼ÅŸÃ¼n (asset yoksa? sahne doluysa? hata olursa?)
"""


WORKER_SYSTEM_PROMPT = """Sen bir WORKER EXECUTOR'sun. Unity Editor'de komutlarÄ± Ã§alÄ±ÅŸtÄ±ran alt dÃ¼zey bir AI'sÄ±n.

=== ROLÃœN ===
Master agent'tan gelen DETAYLI talimatlarÄ± alÄ±r ve tool'larÄ± Ã§aÄŸÄ±rarak uygularsÄ±n.
Sen dÃ¼ÅŸÃ¼nmezsin, Master'Ä±n planÄ±nÄ± TAKÄ°P EDERSÄ°N.

Sen Qwen 2.5:14b modelisin - hÄ±zlÄ±, verimli, tool-calling konusunda uzman.
Master dÃ¼ÅŸÃ¼nÃ¼r, sen YAPARSIN.

=== YETENEKLERIN ===
Unity Tool'larÄ± (60+ tool):
- Scene intelligence: get_scene_catalog, find_scene_objects_semantic, delete_scene_objects_semantic,
  apply_material_palette, create_optimized_forest_scene, optimize_editor_performance
- QA/Safety: create_scene_snapshot, restore_scene_snapshot, run_visual_qa,
  profile_scene_performance, task_queue, safety_mode, asset_knowledge_base, rank_prefab_quality
- GameObject: create, delete, duplicate, set_active, set_parent
- Transform: set_position, set_rotation, set_scale, move, rotate
- Components: add_component, remove_component (Rigidbody, Collider, Light, Camera, AudioSource)
- Materials: set_material_color, create_material
- Lights: create_light (Point, Directional, Spot, Area)
- Physics: add_collider, add_rigidbody
- Assets: search, instantiate, find_tree_assets, find_rock_assets, find_prop_assets
- Procedural: create_grid, create_circle, scatter_objects, create_forest, create_rock_field
- Scene: list_scene_objects, get_object_details, save_scene
- Blender: export_fbx, import_fbx

=== DAVRANIÅIN ===
1. Master'Ä±n komutunu AL - her kelimeyi oku
2. Hangi tool'u Ã§aÄŸÄ±racaÄŸÄ±nÄ± BELÄ°RLE - komutta yazÄ±yor
3. Parametreleri HAZIRLA - komutta belirtilen deÄŸerleri kullan
4. Tool'u Ã‡AÄIR - doÄŸru parametrelerle
5. Sonucu RAPORLA - ne oldu, baÅŸarÄ±lÄ± mÄ±, hata var mÄ±?
6. Bir sonraki adÄ±ma GEÃ‡

=== RAPOR FORMATI ===
Her adÄ±m sonrasÄ± JSON rapor:

```json
{
  "step_id": 1,
  "success": true/false,
  "action": "YapÄ±lan iÅŸlem Ã¶zeti",
  "tool_calls": ["tool1", "tool2"],
  "results": {
    "tool1": "SonuÃ§ detayÄ±",
    "tool2": "SonuÃ§ detayÄ±"
  },
  "errors": [],
  "data": {
    "created_objects": ["obj1", "obj2"],
    "asset_paths": ["path1", "path2"]
  }
}
```

=== Ã–RNEK EXECUTION ===
Master komutu:
"Use unity_find_tree_assets tool to search for all tree assets. Return at least 3 different tree types."

Senin yapman gereken:
1. unity_find_tree_assets() tool'unu Ã§aÄŸÄ±r
2. Sonucu al (Ã¶rn: 5 tree asset bulundu)
3. Rapor et:
```json
{
  "step_id": 1,
  "success": true,
  "action": "Searched for tree assets in project",
  "tool_calls": ["unity_find_tree_assets"],
  "results": {
    "unity_find_tree_assets": "Found 5 tree assets: Oak, Pine, Birch, Willow, Maple"
  },
  "data": {
    "asset_paths": [
      "Assets/Trees/Oak.prefab",
      "Assets/Trees/Pine.prefab",
      "Assets/Trees/Birch.prefab",
      "Assets/Trees/Willow.prefab",
      "Assets/Trees/Maple.prefab"
    ],
    "count": 5
  }
}
```

=== HATA DURUMU ===
EÄŸer tool hata verirse:
```json
{
  "step_id": 1,
  "success": false,
  "action": "Attempted to search for tree assets",
  "tool_calls": ["unity_find_tree_assets"],
  "errors": ["No tree assets found in project"],
  "fallback_attempted": "Tried unity_search_assets_semantic with 'tree' query",
  "fallback_result": "Found 2 generic nature assets"
}
```

=== Ã–NEMLI KURALLAR ===
- Master ne derse ONU YAP - kendi fikrin yok
- Tool parametrelerini DOÄRU VER - master'Ä±n belirttiÄŸi gibi
- Hata olursa DETAYLI RAPORLA - ne, neden, nasÄ±l
- HIZLI Ã‡ALIÅ - sen execution engine'sin
- Fazla DÃœÅÃœNME - master dÃ¼ÅŸÃ¼ndÃ¼, sen uygula
- Her tool Ã§aÄŸrÄ±sÄ±nÄ± RAPORLA - master takip etsin

=== TOOL Ã‡AÄIRMA KURALLARI ===
1. Tool adÄ±nÄ± TAM VER - "unity_create_primitive" not "create primitive"
2. Parametreleri DOÄRU TÄ°PTE VER - string, int, float, bool, list
3. Zorunlu parametreleri ATLA - hata alÄ±rsÄ±n
4. Sonucu BEKLE - tool bitmeden devam etme
5. Hata varsa TEKRAR DENEME - farklÄ± parametre dene

Sen bir ROBOT gibisin - master'Ä±n emirlerini kusursuz uygularsÄ±n.
HÄ±z, doÄŸruluk, gÃ¼venilirlik senin Ã¶nceliÄŸin.
"""


@dataclass
class DualAgentResult:
    """Dual-agent execution result."""
    text: str
    reader_brief: str = ""
    master_plan: dict[str, Any] = field(default_factory=dict)
    worker_reports: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True


class DualAgentOrchestrator:
    """Hierarchical dual-agent system with master planner and worker executor.
    
    Enhanced with:
    - Memory system (learns from past experiences)
    - Context management (tracks scene state and assets)
    - Self-improvement (adapts based on success/failure)
    """

    def __init__(
        self,
        config: Config,
        master_model: str = "qwen3.6:latest",
        worker_model: str = "qwen2.5:14b-instruct",
        reader_model: str = "qwen2.5:14b-instruct",
        enable_memory: bool = True,
        enable_context: bool = True,
    ) -> None:
        self.config = config
        self.master_model = master_model
        self.worker_model = worker_model
        self.reader_model = reader_model

        # Reader orchestrator (fast context interpretation, no writes)
        reader_config = self._clone_config(config, reader_model)
        self.reader = Orchestrator(reader_config)
        self.reader.max_tokens = 2048

        # Master orchestrator (planning, no tools)
        master_config = self._clone_config(config, master_model)
        self.master = Orchestrator(master_config)
        self.master.max_tokens = 4096  # Master doesn't need huge context

        # Worker orchestrator (execution, with tools)
        worker_config = self._clone_config(config, worker_model)
        self.worker = Orchestrator(worker_config)
        self.worker.max_tokens = 8192  # Worker needs more for tool results
        
        # Memory system (learning)
        self.memory = MemorySystem() if enable_memory else None
        
        # Context manager (scene awareness)
        self.context = ContextManager() if enable_context else None

        logger.info(
            "DualAgent initialized: Reader=%s, Master=%s, Worker=%s, Memory=%s, Context=%s",
            reader_model,
            master_model,
            worker_model,
            enable_memory,
            enable_context,
        )

    def reset(self) -> None:
        """Reset both agents' history."""
        self.reader.reset()
        self.master.reset()
        self.worker.reset()

    def chat(
        self,
        user_message: str,
        on_master_thinking: Optional[Callable[[str], None]] = None,
        on_worker_executing: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
        max_iterations: int = 5,
    ) -> DualAgentResult:
        """Execute user request using master-worker hierarchy with memory and context.

        Args:
            user_message: User's request
            on_master_thinking: Callback when master is planning
            on_worker_executing: Callback when worker is executing
            on_tool_call: Callback when worker calls a tool
            on_tool_result: Callback when tool returns result
            max_iterations: Max master-worker cycles

        Returns:
            DualAgentResult with plan, reports, and final text
        """
        start_time = time.time()
        all_tool_calls: list[dict[str, Any]] = []
        worker_reports: list[dict[str, Any]] = []
        master_plan: dict[str, Any] = {}
        reader_brief = ""
        live_context: dict[str, Any] = {}

        # Phase 0: Gather context and recall similar experiences
        context_info = ""
        similar_experiences = []
        learned_lessons = []
        
        if self.context:
            context_info = self.context.get_context_summary()
            if on_master_thinking:
                on_master_thinking(f"Analyzing current context...")
        
        if self.memory:
            similar_experiences = self.memory.recall_similar(user_message, limit=3)
            learned_lessons = self.memory.get_lessons(user_message)
            pattern = self.memory.get_pattern(user_message)
            
            if similar_experiences and on_master_thinking:
                on_master_thinking(f"Recalled {len(similar_experiences)} similar past experiences")
            
            if learned_lessons and on_master_thinking:
                on_master_thinking(f"Found {len(learned_lessons)} lessons from past mistakes")

        # Phase 0b: Fast deterministic read pass + qwen2.5 reader brief.
        # This keeps the stronger planner from guessing and keeps read-heavy
        # scene/asset discovery away from the execution step.
        if on_master_thinking:
            on_master_thinking("Reader agent scanning scene/assets...")
        live_context = self._gather_live_context(
            user_message,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
        )
        if live_context:
            reader_brief = self._reader_brief(user_message, live_context)
            if on_master_thinking and reader_brief:
                on_master_thinking("Reader brief ready")

        # Phase 1: Master creates plan (with context and memory)
        if on_master_thinking:
            on_master_thinking("Master agent analyzing request...")

        master_prompt = self._build_master_prompt(
            user_message,
            context_info,
            similar_experiences,
            learned_lessons,
            reader_brief,
            live_context,
        )

        try:
            # Master creates plan (no tools, just thinking)
            master_result = self._master_plan(master_prompt)
            plan_text = master_result.text

            # Extract JSON plan from master's response
            master_plan = self._extract_json_plan(plan_text)
            if not master_plan or "steps" not in master_plan:
                # Fallback: treat entire request as single step
                master_plan = {
                    "task": user_message,
                    "complexity": "simple",
                    "steps": [
                        {
                            "step_id": 1,
                            "description": "Execute user request",
                            "action": "worker_execute",
                            "prompt": user_message,
                        }
                    ],
                }

            logger.info("Master plan: %d steps", len(master_plan.get("steps", [])))

            # Phase 2: Worker executes each step
            for step in master_plan.get("steps", []):
                step_id = step.get("step_id", 0)
                worker_prompt = step.get("prompt", "")
                description = step.get("description", "")

                if on_worker_executing:
                    on_worker_executing(f"Step {step_id}: {description}")

                logger.info("Worker executing step %d: %s", step_id, description)

                # Worker executes with tools
                worker_result = self.worker.chat(
                    worker_prompt,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                    max_iterations=10,
                )

                # Collect results
                all_tool_calls.extend(worker_result.tool_calls)
                worker_reports.append(
                    {
                        "step_id": step_id,
                        "description": description,
                        "result": worker_result.text,
                        "tool_calls": len(worker_result.tool_calls),
                        "success": worker_result.stop_reason != "max_iterations",
                    }
                )
                
                # Update context with tool results
                if self.context:
                    self._update_context_from_tools(worker_result.tool_calls)

            # Phase 3: Master summarizes results
            if on_master_thinking:
                on_master_thinking("Master agent summarizing results...")

            summary_prompt = f"""Worker agent ÅŸu adÄ±mlarÄ± tamamladÄ±:

{json.dumps(worker_reports, ensure_ascii=False, indent=2)}

KullanÄ±cÄ±ya kÄ±sa ve net bir Ã¶zet sun. Ne yapÄ±ldÄ±, sonuÃ§ ne oldu?
EÄŸer hata varsa, ne olduÄŸunu aÃ§Ä±kla.
"""

            summary_result = self._master_plan(summary_prompt)
            final_text = summary_result.text
            final_text = _humanize_final_text(final_text, worker_reports, all_tool_calls)
            
            # Phase 4: Learn from this experience
            duration = time.time() - start_time
            success = all(r.get("success", False) for r in worker_reports)
            
            if self.memory:
                errors = [
                    call.get("error", "")
                    for call in all_tool_calls
                    if not call.get("ok", True)
                ]
                
                lessons = []
                if not success:
                    lessons.append(f"Failed approach for: {user_message}")
                    if errors:
                        lessons.append(f"Common errors: {', '.join(errors[:3])}")
                
                memory_entry = MemoryEntry(
                    timestamp=start_time,
                    request=user_message,
                    plan=master_plan,
                    execution={"reports": worker_reports},
                    success=success,
                    duration=duration,
                    tools_used=[call.get("name", "") for call in all_tool_calls],
                    errors=errors,
                    lessons=lessons,
                )
                
                self.memory.remember(memory_entry)
                
                if on_master_thinking:
                    stats = self.memory.get_statistics()
                    on_master_thinking(
                        f"Learned from experience (Total patterns: {stats['patterns_learned']})"
                    )

            return DualAgentResult(
                text=final_text,
                reader_brief=reader_brief,
                master_plan=master_plan,
                worker_reports=worker_reports,
                tool_calls=all_tool_calls,
                success=success,
            )

        except Exception as e:
            logger.exception("DualAgent error")
            
            # Learn from failure
            if self.memory:
                memory_entry = MemoryEntry(
                    timestamp=start_time,
                    request=user_message,
                    plan=master_plan,
                    execution={},
                    success=False,
                    duration=time.time() - start_time,
                    tools_used=[],
                    errors=[str(e)],
                    lessons=[f"System error: {type(e).__name__}"],
                )
                self.memory.remember(memory_entry)
            
            return DualAgentResult(
                text=f"Hata oluÅŸtu: {e}",
                reader_brief=reader_brief,
                master_plan=master_plan,
                worker_reports=worker_reports,
                tool_calls=all_tool_calls,
                success=False,
            )

    def _master_plan(self, prompt: str) -> Any:
        """Master agent thinks and plans (no tool access)."""
        # Master uses simple chat without tools
        response = self.master._ollama_chat(
            [
                {"role": "system", "content": MASTER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            tools=[]
        )

        message = response.get("message", {})
        content = message.get("content", "")

        # Create result object
        from .orchestrator import OrchestratorResult
        return OrchestratorResult(text=content, stop_reason="stop")

    @staticmethod
    def _extract_json_plan(text: str) -> dict[str, Any]:
        """Extract JSON plan from master's response."""
        # Try to find JSON block
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON
        json_match = re.search(r'\{.*"steps".*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}

    @staticmethod
    def _clone_config(config: Config, model: str) -> Config:
        """Clone config with different model."""
        import copy
        new_config = copy.deepcopy(config)
        new_config.ollama_model = model
        return new_config
    
    def _build_master_prompt(
        self,
        user_message: str,
        context_info: str,
        similar_experiences: list,
        learned_lessons: list[str],
        reader_brief: str = "",
        live_context: dict[str, Any] | None = None,
    ) -> str:
        """Build enhanced master prompt with context and memory."""
        prompt_parts = [f"KullanÄ±cÄ± isteÄŸi: {user_message}\n"]

        if reader_brief:
            prompt_parts.append(f"\n=== FAST READER BRIEF ===\n{reader_brief}\n")

        if live_context:
            prompt_parts.append(
                "\n=== LIVE READ TOOL SNAPSHOT ===\n"
                + json.dumps(_compact_live_context(live_context), ensure_ascii=False, indent=2, default=str)
                + "\n"
            )
        
        # Add context
        if context_info:
            prompt_parts.append(f"\n=== CURRENT CONTEXT ===\n{context_info}\n")
        
        # Add similar experiences
        if similar_experiences:
            prompt_parts.append("\n=== SIMILAR PAST EXPERIENCES ===")
            for i, exp in enumerate(similar_experiences[:3], 1):
                success_label = "SUCCESS" if exp.success else "FAILED"
                prompt_parts.append(
                    f"{i}. [{success_label}] {exp.request[:60]}... "
                    f"(duration: {exp.duration:.1f}s, tools: {len(exp.tools_used)})"
                )
            prompt_parts.append("")
        
        # Add learned lessons
        if learned_lessons:
            prompt_parts.append("\n=== LESSONS LEARNED ===")
            for i, lesson in enumerate(learned_lessons[:5], 1):
                prompt_parts.append(f"{i}. {lesson}")
            prompt_parts.append("")
        
        # Add planning instructions
        prompt_parts.append("""
Bu isteÄŸi analiz et ve worker agent iÃ§in bir plan oluÅŸtur.
PlanÄ± ÅŸu formatta JSON olarak ver:

{
  "task": "Ä°steÄŸin Ã¶zeti",
  "complexity": "simple/medium/complex",
  "context_notes": "Context'ten Ã¶nemli notlar",
  "steps": [
    {
      "step_id": 1,
      "description": "AdÄ±m aÃ§Ä±klamasÄ±",
      "action": "worker_execute",
      "prompt": "Worker'a verilecek detaylÄ± komut",
      "expected_result": "Beklenen sonuÃ§",
      "fallback": "Hata olursa ne yapÄ±lmalÄ±"
    }
  ]
}

Ã–NEMLI:
- Context bilgisini kullan (sahne durumu, mevcut asset'ler)
- GeÃ§miÅŸ deneyimlerden Ã¶ÄŸren (benzer isteklerde ne iÅŸe yaradÄ±/yaramadÄ±)
- Learned lessons'Ä± dikkate al (aynÄ± hatalarÄ± tekrarlama)
- EÄŸer istek Ã§ok basitse, tek adÄ±m yeterli
- KarmaÅŸÄ±ksa, birden fazla adÄ±ma bÃ¶l
""")
        
        return "\n".join(prompt_parts)

    def _gather_live_context(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
    ) -> dict[str, Any]:
        """Run bounded read-only tools before planning.

        The reader phase is deterministic on purpose: qwen2.5 gets a compact
        snapshot to interpret, while mutating tools stay reserved for Worker.
        """
        from .tool_registry import get_tool

        text = (user_message or "").lower()
        plan: list[tuple[str, dict[str, Any]]] = [
            ("unity_get_project_info", {}),
            ("unity_get_scene_catalog", {"max": 350}),
        ]
        if any(w in text for w in ("asset", "prefab", "tree", "agac", "ağaç", "rock", "kaya", "prop", "real", "realistic", "relis")):
            plan.append(("unity_get_asset_catalog_summary", {}))
        if any(w in text for w in ("kas", "kasma", "performans", "performance", "triangle", "poly", "lod", "optimize")):
            plan.append(("unity_profile_scene_performance", {"max_objects": 10000}))

        results: dict[str, Any] = {}
        for tool_name, params in plan:
            spec = get_tool(tool_name)
            if spec is None:
                continue
            if on_tool_call:
                on_tool_call(tool_name, params)
            try:
                result = spec.fn(**params)
            except Exception as exc:
                result = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
            results[tool_name] = result
            if on_tool_result:
                on_tool_result(tool_name, result)
            if self.context and tool_name == "unity_get_scene_catalog" and isinstance(result, dict):
                objects = result.get("objects") or result.get("items") or []
                if isinstance(objects, list):
                    self.context.update_scene(objects)
        return results

    def _reader_brief(self, user_message: str, live_context: dict[str, Any]) -> str:
        prompt = f"""Kullanici istegi:
{user_message}

Canli okuma sonuclari:
{json.dumps(_compact_live_context(live_context), ensure_ascii=False, indent=2, default=str)}

Planner icin kisa Turkce briefing yaz. JSON yazma. Sadece ne var, ne yapilmali, hangi riskler var."""
        try:
            response = self.reader._ollama_chat(
                [
                    {"role": "system", "content": READER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                tools=[],
            )
            return (response.get("message", {}) or {}).get("content", "").strip()
        except Exception as exc:
            logger.warning("Reader brief failed: %s", exc)
            return ""
    
    def _update_context_from_tools(self, tool_calls: list[dict[str, Any]]) -> None:
        """Update context manager from tool results."""
        if not self.context:
            return
        
        for call in tool_calls:
            tool_name = call.get("name", "")
            result = call.get("result", {})
            success = call.get("ok", True)
            
            # Update scene context
            if tool_name == "unity_list_scene_objects" and success:
                objects = result.get("objects", [])
                if objects:
                    self.context.update_scene(objects)
            
            # Update asset context
            elif tool_name == "unity_find_tree_assets" and success:
                assets = result.get("results", [])
                asset_paths = [a.get("path", "") for a in assets if isinstance(a, dict)]
                self.context.update_assets("trees", asset_paths)
            
            elif tool_name == "unity_find_rock_assets" and success:
                assets = result.get("results", [])
                asset_paths = [a.get("path", "") for a in assets if isinstance(a, dict)]
                self.context.update_assets("rocks", asset_paths)
            
            # Record action
            self.context.record_action(
                action_type=tool_name,
                details=call.get("input", {}),
                success=success,
            )


def _compact_live_context(context: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for name, result in context.items():
        if not isinstance(result, dict):
            compact[name] = result
            continue
        row = {k: v for k, v in result.items() if k not in {"objects", "results", "groups", "samples", "catalog"}}
        for key in ("objects", "results", "groups", "samples", "catalog"):
            value = result.get(key)
            if isinstance(value, list):
                row[key] = value[:12]
            elif isinstance(value, dict):
                row[key] = dict(list(value.items())[:12])
        compact[name] = row
    return compact


def _humanize_final_text(text: str, worker_reports: list[dict[str, Any]], tool_calls: list[dict[str, Any]]) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return _fallback_summary(worker_reports, tool_calls)
    if _looks_like_json(stripped):
        return _fallback_summary(worker_reports, tool_calls)
    return stripped


def _looks_like_json(text: str) -> bool:
    if text.startswith("```json"):
        return True
    if not (text.startswith("{") or text.startswith("[")):
        return False
    try:
        json.loads(re.sub(r"^```json\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL))
        return True
    except Exception:
        return False


def _fallback_summary(worker_reports: list[dict[str, Any]], tool_calls: list[dict[str, Any]]) -> str:
    ok_calls = [c for c in tool_calls if c.get("ok", True)]
    bad_calls = [c for c in tool_calls if not c.get("ok", True)]
    lines = [
        "Islem akisi tamamlandi.",
        f"Calisan adim sayisi: {len(worker_reports)}",
        f"Basarili tool sayisi: {len(ok_calls)}",
    ]
    if bad_calls:
        lines.append(f"Hata veren tool sayisi: {len(bad_calls)}")
        for call in bad_calls[:3]:
            lines.append(f"- {call.get('name')}: {call.get('error') or call.get('result', {}).get('error')}")
    else:
        lines.append("Hata raporlanmadi.")
    if ok_calls:
        names = ", ".join(dict.fromkeys(str(c.get("name", "")) for c in ok_calls if c.get("name")))
        lines.append(f"Kullanilan tool'lar: {names}")
    return "\n".join(lines)
