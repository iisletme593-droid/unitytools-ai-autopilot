"""LLM orchestrator with Anthropic and Ollama tool-calling backends.

Improvements over the v1 orchestrator:
  * Robust system prompt (autopilot persona + tool catalogue awareness).
  * `max_tokens` configurable (was hard-coded 4096).
  * History trimming to avoid runaway token growth in long sessions.
  * Tool result is sent as a structured JSON string (not str(dict)) so the
    model can reliably parse fields like `ok` / `error`.
  * On Ollama, accepts both string and (multimodal-style) content lists by
    flattening text parts. Anthropic path passes lists through unchanged.
  * Tool errors surface with their type so the model can react (retry vs
    give up vs alternative).
"""
from __future__ import annotations

import json
import logging
import inspect
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from anthropic import Anthropic

from .config import Config
from .tool_registry import get_all_tools, get_tool, to_anthropic_format

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Sen Unity 6000.x Editor'de tam yetkili, uzman seviye bir game development ve asset pipeline autopilot'usun.

=== KIMLIK ===
Sen sadece bir asistan degilsin; Unity Editor'de neredeyse tam yetkiye sahip bir AI autopilot'sun.
Kullanici dogal dil ile istek yapar (Turkce veya Ingilizce). Sen bu istegi, sana verilen tool'lari
kullanarak adim adim gerceklestirirsin. Ama sadece istenenleri yapmakla kalma -- kesfet, oner,
uretken ol.

=== YETKILERIN ===
- GameObject olusturma, silme, kopyalama, parent ayarlama, active/inactive yapma
- Transform (position, rotation, scale) tam kontrol
- Component ekleme/cikarma (Rigidbody, Collider, Light, Camera, AudioSource, vb.)
- Material renk ayarlama
- Isik (Point, Directional, Spot, Area) ve Kamera olusturma/ayarlama
- Prefab instantiate etme
- Physics (Collider, Rigidbody) ekleme ve yapilandirma
- Tag ve Layer atama
- Play mode girme/cikma
- Procedural generation: grid, dairesel dizi, scatter, merdiven, duvar, oda olusturma
- Menu item calistirma, sahne kaydetme, asset import etme
- Obje detaylari, component bilgisi, tag ile arama, asset arama
- Semantic asset catalogue: realistic/misspelled isteklerde proje asset'lerini bulma,
  kategori/folder olarak gruplama ve en iyi asset'i sahneye yerlestirme
- Scene intelligence: sahnedeki objeleri tag'e guvenmeden isim, hierarchy, material,
  component ve kategori uzerinden kataloglama/bulma/silme/renklendirme
- Material/texture repair: pink/magenta shader hatalarini diagnose/repair etme,
  HDRP/URP/Built-in uyumlu shader'a donustururken texture/normal map baglarini koruma
- Visual QA ve performans profili: SceneView screenshot alma, kamera/isik/material risklerini
  raporlama, renderer/triangle/shadow/material sayilarini profil etme
- Snapshot, task queue ve safety mode: buyuk/silici islerden once sahneyi yedekleme,
  uzun isleri izleme ve safe/edit/destructive modlara uyma

=== UNITY BILGISI ===
Primitive tipler: Cube, Sphere, Cylinder, Capsule, Plane, Quad
Light tipleri: Point, Directional, Spot, Area
Collider tipleri: Box, Sphere, Capsule, Mesh, Terrain
Rigidbody ayarlari: use_gravity, is_kinematic, mass, drag, angular_drag, interpolate, collision_detection
Camera ayarlari: fov, near_clip, far_clip, orthographic, orthographic_size, background_color
Transform: position (Vector3), rotation (Euler angles), scale (localScale)
Tag'ler: Untagged, MainCamera, Player, Respawn, Finish, EditorOnly, GameController
Layer'lar: 0=Default, 1=TransparentFX, 2=IgnoreRaycast, 4=Water, 5=UI, 8-31=Custom

=== UNREAL ENGINE BILGISI ===
Kullanici Unreal/UE/UE5 isterse Unity tool'lari yerine unreal_* tool'larini kullan:
- Unreal Editor bridge ping/project info, current level actor listeleme/semantic arama
- /Game asset kataloglama ve semantic asset arama
- Basic actor spawn: cube, sphere, cylinder, plane, point_light, directional_light, camera
- Actor transform ayarlama, semantic actor silme
- FBX/OBJ/GLB/GLTF/texture/audio import ve dirty package save
- Unity -> Unreal migration icin once source assetleri staging'e kopyala, sonra Unreal import et

=== GAMESTUDIO LEVELS ===
Level 1 Basic Assistant: aciklar ve onerir.
Level 2 Coding Agent: dosya duzenler ve test calistirir.
Level 3 Autonomous Engineering Agent: repo tarar, planlar, uygular, debug eder.
Level 4 Unreal Development Agent: C++, Blueprint, asset, level, animation, Niagara, build/packaging.
Level 5 Autonomous Game Director AI: creative kararlar verir ve oynanabilir iyilestirme yapar.
Level 6 Self-Evolving Game Studio: player data -> fun analysis -> safe mutation -> QA -> memory dongusu.
Kullanici evrimlesen studyodan bahsederse gamestudio_* tool'lariyla manifest, roadmap,
experiment memory ve iteration plan olustur. Kontrolsuz self-modification yapma.

=== DAVRANIS KURALLARI ===
0. Kullanici bir seyi yapma derse (ornegin "sahneye koyma", "silme", "degistirme"),
   bu negatif talimat en yuksek onceliktir. Planinda bile yasaklanan islemi yazma.
1. Once kisa bir plan acikla, sonra tool'lari cagir.
2. Bir tool hata donerse, hatayi kullaniciya acikla, alternatif dene. HATADA HEMEN VAZGECME.
3. Dosya yollari her zaman proje root'una gore relative olsun.
4. Asset isimlerinde Turkce karakter kullanma, Ingilizce isim oner.
5. Is bittiginde kisa bir ozet ver.
6. KULLANICI HER SEYI SORMAK ZORUNDA DEGIL -- mantikli varsayimlar yap, cozumleri uygula.
   Ornegin "bir oda olustur" dendiginde olcu, isik, kamera otomatik ekle.
7. Yaratici ol -- kullanicinin istegini karsilamakla kalmayip, daha iyi sonuclar icin ek adimlar at.
   Ornegin bir sahneye objeler yerlestirirken isik ve kamera da ekle.
8. Procedural tool'lari aktif kullan -- grid, circle, scatter, stairs, wall, room ile
   kompleks yapilar olusturabilirsin.
9. Her onemli islem sonrasi sahne durumunu kontrol et (list_scene_objects, get_object_details).
10. Eger bir islem icin tool yoksa, kullaniciya bunu soyle ve bir workaround oner.
11. KULLANICI realistic/real/relis/realist, tree, rock, grass, prop, building, character,
    weapon, material, texture gibi gercek asset isteyen kelimeler kullanirsa ONCE semantic
    asset tool'larini cagir: unity_search_assets_semantic, unity_find_tree_assets,
    unity_find_rock_assets, unity_find_prop_assets, unity_instantiate_best_asset,
    unity_scatter_best_assets, unity_create_forest_from_assets vb.
12. Primitiveleri (Cube/Sphere) sadece prototip veya fallback icin kullan. Uygun real asset
    bulunursa agac/kaya/karakter/prop icin asla kup yaratma; gercek asset instantiate et.
13. Yazim hatalarini tolere et: "real relis realist tree" gibi istekler realistic tree olarak
    yorumlanmali ve proje icindeki PolyHaven/Sketchfab/FantasyRPG asset'leri aranmalidir.
14. Kullanici "sahneye koyma", "sadece listele", "only list" derse instantiate/place/scatter
    tool'u cagirmazsin. Sadece arama/gruplama tool'u kullan ve sonucu listele.
15. Yapmadigin islemi yapmis gibi soyleme. Sadece instantiate/scatter/create tool'u basarili
    donduyse "sahneye yerlestirdim" de. Arama tool'u calistiysa "buldum/listeledim" de.
16. Kullanici "agaclari sil", "taslari boya", "zemini renklendir", "koy/camp/fire bul" gibi
    sahne objesi istegi yaparsa tag arama kullanma. Once unity_get_scene_catalog veya
    unity_find_scene_objects_semantic kullan. Sonra unity_delete_scene_objects_semantic,
    unity_apply_material_palette gibi semantic tool'larla uygula.
16b. Kullanici palette belirtmeden "agaclari boya/renklendir" derse geri soru sorma;
     varsayilan olarak category="tree", palette="forest" kullan. "taslari boya" icin
     category="rock", palette="rocks"; "zemini boya" icin category="ground", palette="ground".
16c. Kullanici "pembe oldu", "pink/magenta", "material bozuk", "texture kaydi/bozuldu",
     "kendi goruntusunu vermiyor" derse once unity_diagnose_material_issues kullan.
     Sonra unity_repair_material_issues ile shader/material tamir et. Kullanici renklendirme
     istemediyse tint=false kullan; texture'lari koru. Texture import sorunu varsa
     unity_repair_texture_import_settings kullan.
17. Buyuk isteklerde (80-120 agac, terrain, sis, kamera, isik) tek tek obje/tool cagirma.
    unity_create_optimized_forest_scene gibi bulk/high-level tool kullan; timeout ve kasmayi
    onlemek icin once/sonra unity_optimize_editor_performance uygula.
18. Sahne bilgisi yetersizse unity_export_scene_knowledge_base ile AutopilotData altina
    scene_knowledge dosyasi olustur; sonraki aramalarda bu katalog mantigini kullan.
19. Buyuk, riskli veya geri donusu zor islerde once unity_create_scene_snapshot cagir.
    Silme/clear_scene/material convert gibi islemlerde safety mode'u unity_get_autopilot_safety_mode
    ile kontrol et. safe modda silme/clear_scene yapma.
20. Asset bulamama veya yanlis asset secme tekrar ederse unity_build_asset_knowledge_base ve
    unity_rank_prefab_quality kullan. "realistic tree/rock/prop" isteklerinde kalite puani yuksek
    prefab/model sec; pembe/bozuk cikarsa material repair ile devam et.
21. "Kasiyor", "timeout", "agir", "bayiliyor", "optimize" gibi isteklerde unity_profile_scene_performance
    ile olc, sonra unity_optimize_editor_performance uygula.
21b. Triangle/poly/mesh sayisi cok yuksekse veya sahne 10M+ triangle ise
     unity_analyze_lod_decimation_candidates ve unity_create_lod_decimation_plan kullan.
     Guvenli varsayilan: proxy LOD ekle, original rendererlari kapatma. Agresif
     replace_with_proxy modunu sadece kullanici acikca kalite kaybini kabul ederse calistir.
22. Gorsel sonuc onemliyse veya kullanici "resim/kayma/bozuk/pembe" diyorsa unity_run_visual_qa
    ile screenshot + QA al; sadece tahmin etme.
23. Uzun islerde unity_create_task_queue / unity_update_task_status ile gorevleri izlenebilir yap.
24. Kullanici belirli bir sahnede calismak isterse once unity_list_scenes ile sahneleri bul,
    sonra unity_open_scene ile dogru sahneyi ac. Kullanici panelden bir sahne sectiyse veya
    "Main/Giris/Level" gibi sahne adi verdiyse, isleme baslamadan once aktif sahnenin o sahne
    oldugunu unity_get_project_info ile dogrula.

=== ONEMLI ===
- Sen bir OBSERVER degil, bir ACTOR'sun. Unity Editor'de degisiklik yapma yetkin var.
- Kullanici "yap" demese bile, mantikli gordugun eklemeleri yap (isik, kamera, collider vb.)
- Hatalardan korkma -- her hata bir ogrenme firsati. Alternatif dene.
- Uretken ol: bos bir sahne gordugunde, onerilerde bulun (isik, zemin, kamera, vb.)
"""


# Geçmiş budamak için varsayılan limit. Anthropic ve Ollama için ayrı tutuyoruz çünkü
# Anthropic content blokları (tool_use/tool_result) tek bir "turn" sayilirken Ollama
# mesaj başina ucuza tokenlar.
DEFAULT_HISTORY_TURN_LIMIT = 40


@dataclass
class ChatMessage:
    role: str
    content: Any


@dataclass
class OrchestratorResult:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ""


class Orchestrator:
    """Provider-agnostic tool-calling chat loop."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client: Optional[Anthropic] = (
            Anthropic(api_key=config.api_key) if config.provider == "anthropic" else None
        )
        self.history: list[ChatMessage] = []
        self.ollama_messages: list[dict[str, Any]] = []
        # Token tarafında güvenli bir varsayılan; .env üstünden override edilebilir.
        self.max_tokens: int = max(1024, int(getattr(config, "max_tokens", 8192)))
        self.history_turn_limit: int = max(
            8, int(getattr(config, "history_turn_limit", DEFAULT_HISTORY_TURN_LIMIT))
        )

    def reset(self) -> None:
        self.history = []
        self.ollama_messages = []

    # ------------------------------------------------------------------ chat

    def chat(
        self,
        user_message: Any,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
        max_iterations: int = 10,
    ) -> OrchestratorResult:
        if self.config.provider == "ollama":
            # Ollama yalnızca düz string user content'i sorunsuz kabul eder.
            user_message = self._flatten_to_text(user_message)
            return self._chat_ollama(user_message, on_tool_call, on_tool_result, max_iterations)
        if self.config.provider == "cloudflare":
            # Cloudflare Workers AI da Ollama gibi düz string content bekler.
            user_message = self._flatten_to_text(user_message)
            return self._chat_cloudflare(user_message, on_tool_call, on_tool_result, max_iterations)
        return self._chat_anthropic(user_message, on_tool_call, on_tool_result, max_iterations)

    # ----------------------------------------------------------- anthropic

    def _chat_anthropic(
        self,
        user_message: Any,
        on_tool_call: Optional[Callable[[str, dict], None]],
        on_tool_result: Optional[Callable[[str, Any], None]],
        max_iterations: int,
    ) -> OrchestratorResult:
        if self.client is None:
            raise RuntimeError("Anthropic client is not initialized (set ANTHROPIC_API_KEY).")

        self.history.append(ChatMessage(role="user", content=user_message))
        tools = to_anthropic_format()
        if not get_all_tools():
            logger.warning("Tool registry bos - LLM tool cagiramayacak.")

        final_text = ""
        tool_calls_log: list[dict[str, Any]] = []

        for _ in range(max_iterations):
            self._trim_history()
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=self._build_anthropic_messages(),
            )
            self.history.append(ChatMessage(role="assistant", content=response.content))

            tool_use_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
            text_blocks = [b for b in response.content if getattr(b, "type", None) == "text"]
            for tb in text_blocks:
                final_text += tb.text + "\n"

            if response.stop_reason != "tool_use":
                return OrchestratorResult(
                    text=_guard_final_text(user_message, final_text.strip(), tool_calls_log),
                    tool_calls=tool_calls_log,
                    stop_reason=response.stop_reason or "end_turn",
                )

            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                tool_name = block.name
                tool_input = block.input or {}
                if on_tool_call:
                    try:
                        on_tool_call(tool_name, tool_input)
                    except Exception:
                        logger.exception("on_tool_call callback failed")
                try:
                    result = self._execute_tool(tool_name, tool_input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": _serialize_for_llm(result),
                        }
                    )
                    tool_calls_log.append(
                        {"name": tool_name, "input": tool_input, "result": result, "ok": True}
                    )
                    if on_tool_result:
                        try:
                            on_tool_result(tool_name, result)
                        except Exception:
                            logger.exception("on_tool_result callback failed")
                except Exception as exc:
                    logger.exception("Tool error: %s", tool_name)
                    err_payload = {
                        "ok": False,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": _serialize_for_llm(err_payload),
                            "is_error": True,
                        }
                    )
                    tool_calls_log.append(
                        {
                            "name": tool_name,
                            "input": tool_input,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                            "ok": False,
                        }
                    )
                    if on_tool_result:
                        try:
                            on_tool_result(tool_name, err_payload)
                        except Exception:
                            logger.exception("on_tool_result callback failed")

            self.history.append(ChatMessage(role="user", content=tool_results))

        return OrchestratorResult(
            text=_guard_final_text(user_message, (final_text + "\n[Warning: max iterations reached]").strip(), tool_calls_log),
            tool_calls=tool_calls_log,
            stop_reason="max_iterations",
        )

    # -------------------------------------------------------------- ollama

    def _chat_ollama(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]],
        on_tool_result: Optional[Callable[[str, Any], None]],
        max_iterations: int,
    ) -> OrchestratorResult:
        if not self.ollama_messages:
            self.ollama_messages.append({"role": "system", "content": SYSTEM_PROMPT})
        self.ollama_messages.append({"role": "user", "content": user_message})

        final_text = ""
        tool_calls_log: list[dict[str, Any]] = []
        tools = self._select_ollama_tools(user_message)
        if not tools:
            logger.warning("Tool registry bos - LLM tool cagiramayacak.")
        _last_calls_sig: str | None = None

        for _ in range(max_iterations):
            self._trim_ollama_history()
            response = self._ollama_chat(self.ollama_messages, tools=tools)
            message = response.get("message") or {}
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []
            synthetic_tool_calls = False
            if not tool_calls:
                tool_calls = _extract_text_tool_calls(content)
                synthetic_tool_calls = bool(tool_calls)

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": "" if synthetic_tool_calls else content,
            }
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            self.ollama_messages.append(assistant_message)

            if content and not synthetic_tool_calls:
                final_text += content + "\n"

            if not tool_calls:
                return OrchestratorResult(
                    text=_guard_final_text(user_message, final_text.strip(), tool_calls_log),
                    tool_calls=tool_calls_log,
                    stop_reason="stop",
                )

            # Over-creation / sonsuz dongu korumasi (P0): model ayni tool cagri
            # kumesini ardisik tekrar ederse (or. ayni nesneyi defalarca olusturma),
            # eylem yapildi say ve dur.
            _calls_sig = json.dumps(
                [
                    {
                        "n": (c.get("function") or {}).get("name") or c.get("name"),
                        "a": (c.get("function") or {}).get("arguments") or c.get("arguments"),
                    }
                    for c in tool_calls
                ],
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )
            if _calls_sig == _last_calls_sig:
                return OrchestratorResult(
                    text=_guard_final_text(
                        user_message,
                        (final_text + "\n(Ayni tool cagrilari tekrarlandi; durduruldu.)").strip(),
                        tool_calls_log,
                    ),
                    tool_calls=tool_calls_log,
                    stop_reason="repeated_tool_calls",
                )
            _last_calls_sig = _calls_sig

            for call in tool_calls:
                function = call.get("function") or {}
                tool_name = function.get("name") or call.get("name")
                tool_input = function.get("arguments") or call.get("arguments") or {}
                if isinstance(tool_input, str):
                    try:
                        tool_input = json.loads(tool_input) if tool_input.strip() else {}
                    except json.JSONDecodeError:
                        tool_input = {}
                if not isinstance(tool_input, dict):
                    tool_input = {}

                if on_tool_call:
                    try:
                        on_tool_call(tool_name, tool_input)
                    except Exception:
                        logger.exception("on_tool_call callback failed")

                try:
                    result = self._execute_tool(tool_name, tool_input)
                    ok = not (isinstance(result, dict) and result.get("ok") is False)
                    tool_calls_log.append(
                        {"name": tool_name, "input": tool_input, "result": result, "ok": ok}
                    )
                    if on_tool_result:
                        try:
                            on_tool_result(tool_name, result)
                        except Exception:
                            logger.exception("on_tool_result callback failed")
                except Exception as exc:
                    logger.exception("Tool error: %s", tool_name)
                    result = {
                        "ok": False,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                    tool_calls_log.append(
                        {
                            "name": tool_name,
                            "input": tool_input,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                            "ok": False,
                        }
                    )
                    if on_tool_result:
                        try:
                            on_tool_result(tool_name, result)
                        except Exception:
                            logger.exception("on_tool_result callback failed")

                self.ollama_messages.append(
                    {
                        "role": "tool",
                        "content": _serialize_for_llm(result),
                        "name": tool_name,
                    }
                )

        return OrchestratorResult(
            text=_guard_final_text(user_message, (final_text + "\n[Warning: max iterations reached]").strip(), tool_calls_log),
            tool_calls=tool_calls_log,
            stop_reason="max_iterations",
        )

    def _ollama_chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        host = self.config.ollama_host.rstrip("/")
        payload: dict[str, Any] = {
            "model": self.config.ollama_model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            # Ollama options: deterministic-ish + reasonable context.
            "options": {
                "temperature": 0.4,
                "num_ctx": 8192,
                "num_predict": max(256, int(self.max_tokens)),
            },
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama'ya baglanilamadi: {exc}. Ollama kurulu ve calisir durumda mi? "
                f"Beklenen adres: {host}"
            ) from exc

    # ----------------------------------------------------------- cloudflare

    def _chat_cloudflare(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]],
        on_tool_result: Optional[Callable[[str, Any], None]],
        max_iterations: int,
    ) -> OrchestratorResult:
        """Cloudflare Workers AI tool-calling dongusu.

        Yapisi _chat_ollama ile ayni; tek fark backend cagrisi (_cloudflare_chat).
        Ortak mesaj tamponu (self.ollama_messages) yeniden kullanilir — bir
        Orchestrator ornegi tek provider'a baglidir, cakisma olmaz.
        """
        if not self.ollama_messages:
            self.ollama_messages.append({"role": "system", "content": SYSTEM_PROMPT})
        self.ollama_messages.append({"role": "user", "content": user_message})

        final_text = ""
        tool_calls_log: list[dict[str, Any]] = []
        tools = self._select_ollama_tools(user_message)
        _last_calls_sig: str | None = None

        for _ in range(max_iterations):
            self._trim_ollama_history()
            response = self._cloudflare_chat(self.ollama_messages, tools=tools)
            message = response.get("message") or {}
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []
            synthetic_tool_calls = False
            if not tool_calls:
                tool_calls = _extract_text_tool_calls(content)
                synthetic_tool_calls = bool(tool_calls)

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": "" if synthetic_tool_calls else content,
            }
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            self.ollama_messages.append(assistant_message)

            if content and not synthetic_tool_calls:
                final_text += content + "\n"

            if not tool_calls:
                return OrchestratorResult(
                    text=_guard_final_text(user_message, final_text.strip(), tool_calls_log),
                    tool_calls=tool_calls_log,
                    stop_reason="stop",
                )

            # Over-creation / sonsuz dongu korumasi (P0): model ayni tool cagri
            # kumesini ardisik tekrar ederse (or. ayni nesneyi defalarca olusturma),
            # eylem yapildi say ve dur.
            _calls_sig = json.dumps(
                [
                    {
                        "n": (c.get("function") or {}).get("name") or c.get("name"),
                        "a": (c.get("function") or {}).get("arguments") or c.get("arguments"),
                    }
                    for c in tool_calls
                ],
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )
            if _calls_sig == _last_calls_sig:
                return OrchestratorResult(
                    text=_guard_final_text(
                        user_message,
                        (final_text + "\n(Ayni tool cagrilari tekrarlandi; durduruldu.)").strip(),
                        tool_calls_log,
                    ),
                    tool_calls=tool_calls_log,
                    stop_reason="repeated_tool_calls",
                )
            _last_calls_sig = _calls_sig

            for call in tool_calls:
                function = call.get("function") or {}
                tool_name = function.get("name") or call.get("name")
                tool_input = function.get("arguments") or call.get("arguments") or {}
                if isinstance(tool_input, str):
                    try:
                        tool_input = json.loads(tool_input) if tool_input.strip() else {}
                    except json.JSONDecodeError:
                        tool_input = {}
                if not isinstance(tool_input, dict):
                    tool_input = {}

                if on_tool_call:
                    try:
                        on_tool_call(tool_name, tool_input)
                    except Exception:
                        logger.exception("on_tool_call callback failed")

                try:
                    result = self._execute_tool(tool_name, tool_input)
                    ok = not (isinstance(result, dict) and result.get("ok") is False)
                    tool_calls_log.append(
                        {"name": tool_name, "input": tool_input, "result": result, "ok": ok}
                    )
                    if on_tool_result:
                        try:
                            on_tool_result(tool_name, result)
                        except Exception:
                            logger.exception("on_tool_result callback failed")
                except Exception as exc:
                    logger.exception("Tool error: %s", tool_name)
                    result = {
                        "ok": False,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                    tool_calls_log.append(
                        {
                            "name": tool_name,
                            "input": tool_input,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                            "ok": False,
                        }
                    )
                    if on_tool_result:
                        try:
                            on_tool_result(tool_name, result)
                        except Exception:
                            logger.exception("on_tool_result callback failed")

                self.ollama_messages.append(
                    {
                        "role": "tool",
                        "content": _serialize_for_llm(result),
                        "name": tool_name,
                    }
                )

        return OrchestratorResult(
            text=_guard_final_text(user_message, (final_text + "\n[Warning: max iterations reached]").strip(), tool_calls_log),
            tool_calls=tool_calls_log,
            stop_reason="max_iterations",
        )

    def _cloudflare_chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Cloudflare Workers AI native /ai/run endpoint cagrisi.

        Yaniti Ollama benzeri {"message": {"content", "tool_calls"}} sekline
        normalize eder; boylece _chat_cloudflare dongusu degismeden calisir.
        CF tool_calls formati: [{"name": ..., "arguments": {...}}].
        """
        account = (getattr(self.config, "cloudflare_account_id", "") or "").strip()
        token = (getattr(self.config, "cloudflare_api_token", "") or "").strip()
        model = (getattr(self.config, "cloudflare_model", "") or "@cf/meta/llama-3.3-70b-instruct-fp8-fast").strip()
        if not account or not token:
            raise RuntimeError(
                "Cloudflare ayarlari eksik: CLOUDFLARE_ACCOUNT_ID ve CLOUDFLARE_API_TOKEN .env'de olmali."
            )
        url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": max(256, int(self.max_tokens)),
            "temperature": 0.4,
        }
        if tools:
            payload["tools"] = tools
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            errbody = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Cloudflare AI HTTP {exc.code}: {errbody[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cloudflare AI'ya baglanilamadi: {exc}") from exc
        if not body.get("success", True):
            raise RuntimeError(f"Cloudflare AI hata: {body.get('errors')}")
        result = body.get("result") or {}
        return {
            "message": {
                "content": result.get("response") or "",
                "tool_calls": result.get("tool_calls") or [],
            }
        }

    def _complete_no_tools(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Provider-bagimsiz, arac-suz tek seferlik tamamlama.

        Donus sekli Ollama/Cloudflare ile ayni: {"message": {"content": ...}}.
        dual_agent.py'deki Master/Reader bunu kullanir; boylece provider'a gore
        (ollama / cloudflare / anthropic) dogru backend'e yonlenir, _ollama_chat'e
        sabit bagli kalmaz.
        """
        provider = (self.config.provider or "ollama").lower()
        if provider == "cloudflare":
            return self._cloudflare_chat(messages, tools=[])
        if provider == "anthropic":
            if self.client is None:
                raise RuntimeError("Anthropic client is not initialized (set ANTHROPIC_API_KEY).")
            system_parts = [str(m.get("content", "")) for m in messages if m.get("role") == "system"]
            convo = [m for m in messages if m.get("role") != "system"]
            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "max_tokens": self.max_tokens,
                "messages": convo,
            }
            sys_text = "\n\n".join(p for p in system_parts if p)
            if sys_text:
                kwargs["system"] = sys_text
            resp = self.client.messages.create(**kwargs)
            text = "".join(
                getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text"
            )
            return {"message": {"content": text, "tool_calls": []}}
        return self._ollama_chat(messages, tools=[])

    def _select_ollama_tools(self, user_message: str) -> list[dict[str, Any]]:
        """Send Ollama only the tools that are relevant to the current request.

        Local models slow down dramatically when every function schema is sent
        on every turn. A small intent-based subset keeps chat responsive while
        still giving Unity requests the right capabilities.
        """
        text = (user_message or "").lower()
        action_words = (
            "unity", "unreal", "ue", "ue5", "sahne", "scene", "asset", "prefab", "obje", "object",
            "level", "harita", "map",
            "agac", "ağaç", "tree", "rock", "kaya", "ground", "zemin",
            "terrain", "forest", "orman", "material", "renk", "color",
            "palette", "boya", "pink", "pembe", "magenta", "shader",
            "texture", "resim", "kayma", "bozuk", "repair", "fix", "onar",
            "qa", "visual", "screenshot", "gorsel", "görsel", "profil", "profile",
            "performance", "performans", "kasma", "kasiyor", "kasıyor", "timeout",
            "triangle", "poly", "polygon", "mesh", "lod", "decimation", "decimate",
            "lowpoly", "proxy", "optimizasyon",
            "snapshot", "backup", "yedek", "safety", "guvenlik", "güvenlik",
            "task", "queue", "plan", "preset", "quality", "kalite",
            "delete", "sil", "kaldir", "kaldır",
            "create", "olustur", "oluştur", "yerlestir", "yerleştir",
            "light", "isik", "ışık", "camera", "kamera", "fog", "sis",
            "blender", "fbx", "export", "import",
        )
        if not any(word in text for word in action_words):
            return []

        selected: set[str] = {
            "unity_ping",
            "unity_get_scene_catalog",
            "unity_find_scene_objects_semantic",
            "unity_export_scene_knowledge_base",
            "unity_optimize_editor_performance",
            "unity_get_autopilot_safety_mode",
            "unity_plan_scene_operation",
            "unity_list_scenes",
            "unity_save_scene",
        }
        if any(word in text for word in ("sahne", "scene", "level", "harita", "map", "aç", "ac", "open", "switch", "geç", "gec")):
            selected.update({"unity_list_scenes", "unity_open_scene", "unity_get_project_info", "unity_save_scene"})
        if any(word in text for word in ("asset", "prefab", "real", "realistic", "relis", "tree", "agac", "ağaç", "rock", "kaya", "prop", "character", "weapon", "material", "texture")):
            selected.update(
                {
                    "unity_search_assets_semantic",
                    "unity_find_tree_assets",
                    "unity_find_rock_assets",
                    "unity_find_prop_assets",
                    "unity_find_character_assets",
                    "unity_find_weapon_assets",
                    "unity_find_material_assets",
                    "unity_get_asset_catalog_summary",
                    "unity_instantiate_best_asset",
                    "unity_scatter_best_assets",
                    "unity_create_forest_from_assets",
                    "unity_create_rock_field_from_assets",
                    "unity_build_asset_knowledge_base",
                    "unity_rank_prefab_quality",
                }
            )
        if any(word in text for word in ("forest", "orman", "terrain", "zemin", "ground", "tree", "agac", "ağaç", "rock", "kaya", "fog", "sis")):
            selected.update(
                {
                    "unity_create_optimized_forest_scene",
                    "unity_create_scene_snapshot",
                    "unity_apply_material_palette",
                    "unity_create_primitive",
                    "unity_create_light",
                    "unity_set_camera",
                    "unity_create_empty",
                    "unity_set_parent",
                    "unity_set_position",
                    "unity_set_scale",
                }
            )
        if any(word in text for word in ("renk", "color", "palette", "material", "boya", "dark", "forest", "ground", "zemin", "rock", "kaya", "tree", "agac", "ağaç")):
            selected.update({"unity_apply_material_palette", "unity_set_material_color", "unity_run_visual_qa"})
        if any(word in text for word in ("pink", "pembe", "magenta", "shader", "material", "texture", "resim", "kayma", "bozuk", "repair", "fix", "onar")):
            selected.update(
                {
                    "unity_diagnose_material_issues",
                    "unity_repair_material_issues",
                    "unity_repair_texture_import_settings",
                    "unity_auto_convert_materials_to_pipeline",
                    "unity_apply_material_palette",
                    "unity_run_visual_qa",
                }
            )
        if any(word in text for word in ("delete", "sil", "kaldir", "kaldır", "remove", "clear", "temizle")):
            selected.update({"unity_create_scene_snapshot", "unity_delete_scene_objects_semantic", "unity_delete_object"})
        if any(word in text for word in ("list", "liste", "show", "goster", "göster", "find", "bul", "count", "say")):
            selected.update({"unity_list_scene_objects", "unity_find_scene_objects", "unity_find_scene_objects_semantic"})
        if any(word in text for word in ("cube", "kup", "küp", "sphere", "primitive", "plane", "quad", "capsule", "cylinder")):
            selected.update({"unity_create_primitive", "unity_set_position", "unity_set_scale", "unity_set_material_color"})
        if any(word in text for word in ("blender", "fbx", "blend", "export", "import")):
            selected.update({"blender_export_fbx", "blender_list_objects", "pipeline_blend_to_unity", "unity_import_asset"})
        if any(word in text for word in ("qa", "visual", "screenshot", "gorsel", "görsel", "kontrol", "bozuk", "pembe")):
            selected.update({"unity_run_visual_qa", "unity_diagnose_material_issues"})
        if any(word in text for word in ("performance", "performans", "profil", "profile", "kas", "kasma", "kasıyor", "kasiyor", "timeout", "optimize")):
            selected.update({"unity_profile_scene_performance", "unity_optimize_editor_performance", "unity_analyze_lod_decimation_candidates", "unity_create_lod_decimation_plan"})
        if any(word in text for word in ("triangle", "poly", "polygon", "mesh", "lod", "decimation", "decimate", "lowpoly", "proxy", "55m", "55 m")):
            selected.update({"unity_profile_scene_performance", "unity_analyze_lod_decimation_candidates", "unity_create_lod_decimation_plan", "unity_apply_lod_decimation_plan", "unity_create_scene_snapshot", "unity_run_visual_qa"})
        if any(word in text for word in ("snapshot", "backup", "yedek", "geri", "restore")):
            selected.update({"unity_create_scene_snapshot", "unity_restore_scene_snapshot"})
        if any(word in text for word in ("task", "queue", "gorev", "görev", "progress", "ilerleme")):
            selected.update({"unity_create_task_queue", "unity_get_task_queue", "unity_update_task_status"})
        if any(word in text for word in ("safety", "guvenlik", "güvenlik", "safe", "destructive")):
            selected.update({"unity_set_autopilot_safety_mode", "unity_get_autopilot_safety_mode"})

        if any(word in text for word in ("game studio", "studio", "oyun studyosu", "oyun stüdyosu", "gameplay", "ui", "hud", "multiplayer", "replication", "dedicated", "steam", "build")):
            selected.update(
                {
                    "gamestudio_get_evolution_architecture",
                    "gamestudio_list_templates",
                    "gamestudio_plan_unreal_fast_action",
                    "gamestudio_preflight_prompt",
                    "gamestudio_initialize_self_evolving_studio",
                    "gamestudio_record_game_experiment",
                    "gamestudio_create_iteration_plan",
                    "unreal_scan_project",
                    "unreal_open_level",
                    "unreal_create_basic_level",
                    "unreal_setup_studio_lighting",
                    "unreal_create_blockout_map",
                    "unreal_create_arena_survivor_prototype",
                    "unreal_apply_arena_survivor_runtime_scaffold",
                    "unreal_spawn_arena_survivor_player_pawn",
                    "unreal_spawn_arena_survivor_placeholder_enemies",
                    "unreal_reset_arena_survivor_runtime_state",
                    "unreal_simulate_arena_survivor_wave_clear",
                    "unreal_simulate_arena_survivor_pickup_collect",
                    "unreal_search_assets_semantic",
                    "unreal_get_asset_catalog_summary",
                    "unreal_save_dirty_packages",
                }
            )

        if any(word in text for word in ("evolve", "evolving", "self-evolving", "evrim", "evrimles", "evrimle", "transformens", "director ai", "liveops", "player data", "fun analysis", "agent roles")):
            selected.update(
                {
                    "gamestudio_get_evolution_architecture",
                    "gamestudio_list_templates",
                    "gamestudio_plan_unreal_fast_action",
                    "gamestudio_preflight_prompt",
                    "gamestudio_initialize_self_evolving_studio",
                    "gamestudio_record_game_experiment",
                    "gamestudio_create_iteration_plan",
                    "unreal_scan_project",
                    "unreal_open_level",
                    "unreal_get_project_info",
                    "unreal_get_asset_catalog_summary",
                    "unreal_create_arena_survivor_prototype",
                    "unreal_open_level",
                    "unreal_apply_arena_survivor_runtime_scaffold",
                    "unreal_spawn_arena_survivor_player_pawn",
                    "unreal_spawn_arena_survivor_placeholder_enemies",
                    "unreal_reset_arena_survivor_runtime_state",
                    "unreal_simulate_arena_survivor_wave_clear",
                    "unreal_simulate_arena_survivor_pickup_collect",
                }
            )

        if any(word in text for word in ("arena", "survivor", "wave", "prototype", "prototip", "playable slice", "seed game")):
            selected.update(
                {
                    "gamestudio_record_game_experiment",
                    "gamestudio_create_iteration_plan",
                    "unreal_create_arena_survivor_prototype",
                    "unreal_apply_arena_survivor_runtime_scaffold",
                    "unreal_spawn_arena_survivor_player_pawn",
                    "unreal_spawn_arena_survivor_placeholder_enemies",
                    "unreal_reset_arena_survivor_runtime_state",
                    "unreal_simulate_arena_survivor_wave_clear",
                    "unreal_simulate_arena_survivor_pickup_collect",
                    "unreal_scan_project",
                    "unreal_save_dirty_packages",
                }
            )

        if any(word in text for word in ("unreal", "ue", "ue5", "uproject", "level actor", "world")):
            selected.update(
                {
                    "unreal_ping",
                    "unreal_scan_project",
                    "unreal_get_project_info",
                    "unreal_open_level",
                    "unreal_list_level_actors",
                    "unreal_find_level_actors_semantic",
                    "unreal_search_assets_semantic",
                    "unreal_get_asset_catalog_summary",
                    "unreal_create_basic_level",
                    "unreal_setup_studio_lighting",
                    "unreal_create_blockout_map",
                    "unreal_create_arena_survivor_prototype",
                    "unreal_apply_arena_survivor_runtime_scaffold",
                    "unreal_spawn_arena_survivor_player_pawn",
                    "unreal_spawn_arena_survivor_placeholder_enemies",
                    "unreal_reset_arena_survivor_runtime_state",
                    "unreal_simulate_arena_survivor_wave_clear",
                    "unreal_simulate_arena_survivor_pickup_collect",
                    "unreal_spawn_basic_actor",
                    "unreal_set_actor_transform",
                    "unreal_import_asset",
                    "unreal_save_dirty_packages",
                    "unreal_stage_unity_assets_for_migration",
                }
            )
            if any(word in text for word in ("delete", "sil", "kaldir", "kaldır", "remove", "clear", "temizle")):
                selected.add("unreal_delete_actors_semantic")

        by_name = {tool.name: tool for tool in get_all_tools()}
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": by_name[name].description,
                    "parameters": by_name[name].input_schema,
                },
            }
            for name in sorted(selected)
            if name in by_name
        ]

    # ------------------------------------------------------------- helpers

    def _execute_tool(self, name: str, params: dict[str, Any]) -> Any:
        spec = get_tool(name)
        if spec is None:
            raise ValueError(f"Bilinmeyen tool: {name}")
        params = self._normalize_tool_params(name, params, spec.fn)
        return spec.fn(**params)

    def _normalize_tool_params(self, name: str, params: dict[str, Any], fn: Any) -> dict[str, Any]:
        """Accept common local-model argument aliases before calling Python tools.

        Ollama models sometimes infer natural names like `object`, `target`, or
        `color_palette` even when the schema says `query`, `category`, `palette`.
        We normalize those aliases here so a useful tool call does not fail just
        because one argument name was slightly off.
        """
        if not isinstance(params, dict):
            return {}

        normalized = dict(params)
        aliases: dict[str, dict[str, str]] = {
            "unity_apply_material_palette": {
                "object": "query",
                "objects": "query",
                "target": "query",
                "target_query": "query",
                "name": "query",
                "object_type": "category",
                "target_category": "category",
                "type": "category",
                "color_palette": "palette",
                "palette_name": "palette",
                "colors": "palette",
                "limit": "max",
                "count": "max",
                "max_results": "max",
            },
            "unity_find_scene_objects_semantic": {
                "object": "query",
                "objects": "query",
                "target": "query",
                "name": "query",
                "object_type": "category",
                "target_category": "category",
                "type": "category",
                "limit": "max_results",
                "count": "max_results",
                "max": "max_results",
            },
            "unity_delete_scene_objects_semantic": {
                "object": "query",
                "objects": "query",
                "target": "query",
                "name": "query",
                "object_type": "category",
                "target_category": "category",
                "type": "category",
                "limit": "max",
                "count": "max",
                "max_results": "max",
            },
            "unity_repair_material_issues": {
                "object": "query",
                "objects": "query",
                "target": "query",
                "name": "query",
                "object_type": "category",
                "target_category": "category",
                "type": "category",
                "color_palette": "palette",
                "palette_name": "palette",
                "colors": "palette",
                "recolor": "tint",
                "paint": "tint",
                "convert_all": "include_unsupported",
                "repair_all": "include_unsupported",
                "limit": "max",
                "count": "max",
                "max_results": "max",
            },
            "unity_diagnose_material_issues": {
                "object": "query",
                "objects": "query",
                "target": "query",
                "name": "query",
                "object_type": "category",
                "target_category": "category",
                "type": "category",
                "limit": "max",
                "count": "max",
                "max_results": "max",
            },
            "unity_repair_texture_import_settings": {
                "target": "query",
                "name": "query",
                "texture_query": "query",
                "limit": "max",
                "count": "max",
                "max_results": "max",
            },
            "unity_auto_convert_materials_to_pipeline": {
                "object": "query",
                "objects": "query",
                "target": "query",
                "name": "query",
                "object_type": "category",
                "target_category": "category",
                "type": "category",
                "limit": "max",
                "count": "max",
                "max_results": "max",
            },
            "unity_rank_prefab_quality": {
                "target": "query",
                "name": "query",
                "object": "query",
                "object_type": "category",
                "type": "category",
                "limit": "max_results",
                "count": "max_results",
                "max": "max_results",
            },
            "unity_run_visual_qa": {
                "screenshot": "capture_screenshot",
                "capture": "capture_screenshot",
            },
            "unity_create_scene_snapshot": {
                "name": "label",
                "title": "label",
            },
            "unity_restore_scene_snapshot": {
                "path": "snapshot_path",
                "snapshot": "snapshot_path",
            },
            "unity_update_task_status": {
                "id": "task_id",
                "task": "task_id",
                "state": "status",
            },
        }
        for source, target in aliases.get(name, {}).items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized[source]

        if name in {
            "unity_apply_material_palette",
            "unity_find_scene_objects_semantic",
            "unity_delete_scene_objects_semantic",
            "unity_diagnose_material_issues",
            "unity_repair_material_issues",
        }:
            category = str(normalized.get("category") or "").lower()
            query = str(normalized.get("query") or "").lower()
            combined = f"{category} {query}"
            if any(token in combined for token in ("tree", "trees", "agac", "ağaç", "forest", "orman")):
                normalized.setdefault("category", "tree")
            elif any(token in combined for token in ("rock", "stone", "boulder", "kaya", "tas", "taş")):
                normalized.setdefault("category", "rock")
            elif any(token in combined for token in ("ground", "terrain", "zemin", "grass", "dirt")):
                normalized.setdefault("category", "ground")
            elif any(token in combined for token in ("fire", "campfire", "ates", "ateş", "torch")):
                normalized.setdefault("category", "camp")

        if name == "unity_apply_material_palette":
            normalized.setdefault("palette", "forest")

        sig = inspect.signature(fn)
        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if accepts_kwargs:
            return normalized
        allowed = set(sig.parameters.keys())
        return {key: value for key, value in normalized.items() if key in allowed}

    def _build_anthropic_messages(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for msg in self.history:
            content = msg.content
            if msg.role == "assistant" and not isinstance(content, str):
                content = [self._block_to_dict(b) for b in content]
            out.append({"role": msg.role, "content": content})
        return out

    @staticmethod
    def _block_to_dict(block: Any) -> dict[str, Any]:
        if hasattr(block, "model_dump"):
            return block.model_dump()
        if hasattr(block, "dict"):
            return block.dict()
        btype = getattr(block, "type", None)
        if btype == "text":
            return {"type": "text", "text": block.text}
        if btype == "tool_use":
            return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
        return {"type": btype or "unknown"}

    @staticmethod
    def _flatten_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for b in content:
                if isinstance(b, dict) and b.get("type") == "text":
                    txt = str(b.get("text") or "")
                    if txt.strip():
                        parts.append(txt)
            if parts:
                return "\n".join(parts)
        return "[Non-text user content received]"

    def _trim_history(self) -> None:
        """Anthropic history'sini son N turn'a kirp.

        Bir 'turn' burada her bir ChatMessage demek (user, assistant ya da tool_results).
        Tool kullanimi sirasinda assistant + user(tool_results) ciftleri kalmali,
        bu yuzden kirpma noktasini orphan tool_result olusturmayacak sekilde ayarliyoruz.
        """
        if len(self.history) <= self.history_turn_limit:
            return
        excess = len(self.history) - self.history_turn_limit
        cut = excess
        while cut < len(self.history):
            first = self.history[cut]
            if first.role == "user" and not _is_tool_results(first.content):
                break
            cut += 1
        if 0 < cut < len(self.history):
            self.history = self.history[cut:]

    def _trim_ollama_history(self) -> None:
        """Ollama history'sini benzer sekilde kirp; system mesajini koru."""
        if len(self.ollama_messages) <= self.history_turn_limit + 1:
            return
        head = self.ollama_messages[:1]
        tail = self.ollama_messages[1:]
        excess = len(tail) - self.history_turn_limit
        if excess > 0:
            tail = tail[excess:]
            # tool mesajiyla baslamamali; basliyorsa onu da at
            while tail and tail[0].get("role") == "tool":
                tail.pop(0)
        self.ollama_messages = head + tail


def _guard_final_text(user_message: Any, text: str, tool_calls: list[dict[str, Any]]) -> str:
    """Prevent local models from claiming scene edits after search-only requests."""
    user_text = str(user_message).lower()
    no_place_terms = (
        "sahneye koyma",
        "sahneye yerlestirme",
        "sahneye yerleştirme",
        "yerlestirme",
        "yerleştirme",
        "sadece listele",
        "only list",
        "do not place",
        "don't place",
        "dont place",
    )
    if not any(term in user_text for term in no_place_terms):
        return text

    mutating_prefixes = (
        "unity_create_primitive",
        "unity_instantiate",
        "unity_scatter",
        "unity_create_asset_",
        "unity_place_asset_",
        "unity_create_forest",
        "unity_create_rock_field",
        "unity_create_prop_cluster",
        "unity_delete",
        "unity_duplicate",
        "unity_set_",
        "unity_add_",
        "unity_remove_",
    )
    if any(call.get("ok") and str(call.get("name", "")).startswith(mutating_prefixes) for call in tool_calls):
        return text

    for call in reversed(tool_calls):
        result = call.get("result")
        if not isinstance(result, dict):
            continue
        rows = result.get("results")
        if not isinstance(rows, list) or not rows:
            continue
        lines = ["Sahneye yerlestirme yapmadim; sadece bulunan assetleri listeliyorum:"]
        for index, row in enumerate(rows[:5], start=1):
            if not isinstance(row, dict):
                continue
            name = row.get("name") or str(row.get("path", "")).split("/")[-1]
            path = row.get("path", "")
            score = row.get("score")
            suffix = f" (score: {score})" if score is not None else ""
            lines.append(f"{index}. {name}{suffix} - {path}")
        return "\n".join(lines)

    lowered = text.lower()
    if "yerleştirdim" in lowered or "yerlestirdim" in lowered:
        return "Sahneye yerlestirme yapmadim; sadece arama/listeleme yaptim.\n\n" + text
    return text


def _extract_text_tool_calls(text: str) -> list[dict[str, Any]]:
    """Recover tool calls when a local model prints JSON instead of using tools.

    Some Ollama models occasionally output:
      {"tool": "unity_apply_material_palette", "input": {...}}
    as plain assistant text. Returning that to the Unity panel looks like "JSON
    spam" and no scene action happens. This parser only accepts JSON objects that
    name a registered tool, then converts them to Ollama tool_call shape.
    """
    if not text or "unity_" not in text and "blender_" not in text and "pipeline_" not in text:
        return []

    candidates: list[str] = []
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced)
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        candidates.append(stripped)
    candidates.extend(re.findall(r"(\{[^{}]*(?:\"tool\"|\"name\"|\"tool_calls\"|\"function\")[\s\S]*\})", text))

    recovered: list[dict[str, Any]] = []
    for raw in candidates:
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        recovered.extend(_tool_calls_from_json_payload(payload))
        if recovered:
            break
    return recovered


def _tool_calls_from_json_payload(payload: Any) -> list[dict[str, Any]]:
    rows: list[Any]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("tool_calls"), list):
        rows = payload["tool_calls"]
    else:
        rows = [payload]

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        function = row.get("function") if isinstance(row.get("function"), dict) else {}
        name = (
            function.get("name")
            or row.get("tool")
            or row.get("name")
            or row.get("tool_name")
        )
        if not isinstance(name, str) or get_tool(name) is None:
            continue
        args = (
            function.get("arguments")
            if "arguments" in function
            else row.get("input", row.get("arguments", row.get("params", {})))
        )
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except Exception:
                args = {}
        if not isinstance(args, dict):
            args = {}
        out.append({"function": {"name": name, "arguments": args}})
    return out


def _serialize_for_llm(value: Any) -> str:
    """LLM'e donecek tool result/error'u her zaman JSON string yap.
    str(dict) Python repr'i verir (tek tirnakli), bu da Ollama parser'larini
    bazen sasirtir. JSON cift tirnakli evrensel format.
    """
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _is_tool_results(content: Any) -> bool:
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "tool_result":
            return True
    return False
