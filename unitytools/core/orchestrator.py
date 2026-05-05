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
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from anthropic import Anthropic

from .config import Config
from .tool_registry import get_tool, to_anthropic_format, to_openai_tool_format

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

=== UNITY BILGISI ===
Primitive tipler: Cube, Sphere, Cylinder, Capsule, Plane, Quad
Light tipleri: Point, Directional, Spot, Area
Collider tipleri: Box, Sphere, Capsule, Mesh, Terrain
Rigidbody ayarlari: use_gravity, is_kinematic, mass, drag, angular_drag, interpolate, collision_detection
Camera ayarlari: fov, near_clip, far_clip, orthographic, orthographic_size, background_color
Transform: position (Vector3), rotation (Euler angles), scale (localScale)
Tag'ler: Untagged, MainCamera, Player, Respawn, Finish, EditorOnly, GameController
Layer'lar: 0=Default, 1=TransparentFX, 2=IgnoreRaycast, 4=Water, 5=UI, 8-31=Custom

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
        if not tools:
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
        tools = to_openai_tool_format()
        if not tools:
            logger.warning("Tool registry bos - LLM tool cagiramayacak.")

        for _ in range(max_iterations):
            self._trim_ollama_history()
            response = self._ollama_chat(self.ollama_messages, tools=tools)
            message = response.get("message") or {}
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            assistant_message: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            self.ollama_messages.append(assistant_message)

            if content:
                final_text += content + "\n"

            if not tool_calls:
                return OrchestratorResult(
                    text=_guard_final_text(user_message, final_text.strip(), tool_calls_log),
                    tool_calls=tool_calls_log,
                    stop_reason="stop",
                )

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

    # ------------------------------------------------------------- helpers

    def _execute_tool(self, name: str, params: dict[str, Any]) -> Any:
        spec = get_tool(name)
        if spec is None:
            raise ValueError(f"Bilinmeyen tool: {name}")
        return spec.fn(**params)

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
