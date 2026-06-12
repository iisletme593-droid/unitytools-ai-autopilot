"""TCP chat server used by the embedded Unity Editor AI panel.

Unity connects to this process on port 7778, sends newline-delimited JSON
messages, and receives tool-call progress plus final assistant text.

İlk bağlantı kurulduğunda istemciye bir `hello` mesajı gönderilir; böylece
Unity tarafı süreç başarıyla ayağa kalkmış mı yoksa import sırasında ölmüş mü
olduğunu anlayabilir.

Supports both single-agent and dual-agent modes.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import socket
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .config import Config
from .orchestrator import Orchestrator
from .security import is_loopback_addr, is_loopback_host, tokens_match

logger = logging.getLogger(__name__)


def _compact_for_client(value: Any, *, list_limit: int = 40, string_limit: int = 3000, depth: int = 0) -> Any:
    """Keep the editor chat responsive by trimming very large tool payloads."""
    if depth > 4:
        return "<trimmed>"
    if isinstance(value, str):
        if len(value) > string_limit:
            return value[:string_limit] + f"... <trimmed {len(value) - string_limit} chars>"
        return value
    if isinstance(value, list):
        kept = [_compact_for_client(v, list_limit=list_limit, string_limit=string_limit, depth=depth + 1) for v in value[:list_limit]]
        if len(value) > list_limit:
            kept.append({"_trimmed_items": len(value) - list_limit})
        return kept
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, item in value.items():
            # Keep common huge collections short in the panel; the LLM still receives full tool results internally.
            local_limit = 20 if key in {"actors", "objects", "assets", "files", "samples", "results"} else list_limit
            compact[key] = _compact_for_client(item, list_limit=local_limit, string_limit=string_limit, depth=depth + 1)
        return compact
    return value


def _local_unreal_ui_plan(text: str) -> str | None:
    """Fast deterministic answer for plan-only UI/HUD requests.

    Local Ollama models can spend minutes planning when the request only needs a
    studio-ready architecture note. This keeps the embedded panel feeling native
    and responsive while heavier create/build requests still go through tools.
    """
    lower = (text or "").lower()
    ui_terms = ("ui", "hud", "menu", "inventory", "settings", "umg", "widget")
    plan_terms = ("plan", "tasarla", "hazirla", "hazırla", "uygulanabilir", "architecture", "mimari")
    execute_terms = ("hemen uygula", "simdi uygula", "şimdi uygula", "olustur", "oluştur", "create widget", "spawn", "sahneye koy", "map uret", "map üret")
    if not any(term in lower for term in ui_terms):
        return None
    if not any(term in lower for term in plan_terms):
        return None
    if any(term in lower for term in execute_terms):
        return None

    return """Unreal icin sade premium UI plani hazir:

Ana hedef:
- UI tek bir temiz tasarim dilinde olacak: koyu grafit zemin, sicak altin vurgu, mat cam paneller, az animasyon.
- UMG tarafinda her ekran ayri Widget Blueprint olacak; ortak buton, panel ve text stilleri tek yerde toplanacak.

Widget mimarisi:
- WBP_MainMenu: Continue, New Game, Settings, Exit butonlari; arka planda yavas kamera/scene blur hissi.
- WBP_HUD: health/stamina bar, mini objective text, interaction prompt, minimal notification stack.
- WBP_Settings: video, audio, controls, gameplay sekmeleri; apply/back akisi.
- WBP_Inventory: sol kategori listesi, orta item grid, sag item detail paneli; equip/use/drop aksiyonlari.
- WBP_PauseMenu: Resume, Save, Settings, Main Menu.
- WBP_CommonButton, WBP_CommonPanel, WBP_Toast: tekrar kullanilabilir premium atomlar.

Unreal implementation:
- UIManager veya PlayerController icinde aktif widget state tutulacak.
- Input: Escape pause, I inventory, Tab objective/HUD focus; Enhanced Input ile baglanacak.
- Inventory data: ItemData PrimaryDataAsset veya DataTable; icon, name, rarity, stack, description, gameplay tag.
- Save data: settings ve inventory state icin USaveGame sinifi.
- Styling: ortak renk paleti ve font ayarlari DataAsset olarak tutulacak.

Renk paleti:
- Background: #111418 / #171B20
- Panel: #20262D, opacity 0.88
- Accent: #C9A45C
- Success: #78B86B
- Danger: #C65E58
- Text primary: #F1EDE4
- Text secondary: #A8B0B8

Uygulama sirasi:
1. WBP_CommonButton ve WBP_CommonPanel olustur.
2. WBP_MainMenu ile ana navigasyonu kur.
3. WBP_HUD icin health/stamina/objective alanlarini bagla.
4. WBP_Inventory icin ItemData yapisini ve grid binding'i hazirla.
5. WBP_Settings icin audio/video/control ayarlarini SaveGame'e bagla.
6. UIManager ile ekranlar arasi gecisi tek yerden yonet.
7. Son pass: hover/click animasyonlari, focus states, gamepad navigation.

Benim onerim:
- Once MainMenu + Pause + Settings temelini kuralim.
- Sonra HUD ve Inventory'yi gameplay loop'a baglayalim.
- En sonda premium polish: animasyon, sound cue, blur, renk tutarliligi."""


def _try_local_unreal_action(text: str, send: Callable[[dict], None]) -> bool:
    """Run common Unreal actions directly instead of letting a small local LLM ramble.

    This is intentionally conservative: only obvious imperative prompts are
    handled here. Rich creative requests still go through the orchestrator.
    """
    try:
        from .game_studio_actions import plan_unreal_fast_action
        from unitytools.tools.unreal_tools import (
            unreal_apply_arena_survivor_runtime_scaffold,
            unreal_apply_actor_material_palette,
            unreal_create_blockout_map,
            unreal_get_project_info,
            unreal_get_scene_workbench_status,
            unreal_list_levels,
            unreal_list_level_actors,
            unreal_list_selected_actors,
            unreal_list_ai_placed_actors,
            unreal_open_level,
            unreal_open_level_by_name,
            unreal_remember_active_level,
            unreal_plan_scene_lod_decimation,
            unreal_place_semantic_assets,
            unreal_prepare_open_world_ground,
            unreal_cleanup_ai_placed_actors,
            unreal_reset_arena_survivor_runtime_state,
            unreal_scan_project,
            unreal_simulate_arena_survivor_pickup_collect,
            unreal_simulate_arena_survivor_wave_clear,
            unreal_setup_studio_lighting,
            unreal_spawn_basic_actor,
            unreal_spawn_arena_survivor_player_pawn,
            unreal_spawn_arena_survivor_placeholder_enemies,
        )
    except Exception:
        return False

    plan = plan_unreal_fast_action(text)
    planned_steps = plan.get("steps", []) if isinstance(plan, dict) else []
    if not planned_steps:
        return False

    tool_map: dict[str, Callable[..., dict[str, Any]]] = {
        "unreal_open_level": unreal_open_level,
        "unreal_open_level_by_name": unreal_open_level_by_name,
        "unreal_remember_active_level": unreal_remember_active_level,
        "unreal_get_project_info": unreal_get_project_info,
        "unreal_get_scene_workbench_status": unreal_get_scene_workbench_status,
        "unreal_list_levels": unreal_list_levels,
        "unreal_scan_project": unreal_scan_project,
        "unreal_list_level_actors": unreal_list_level_actors,
        "unreal_list_selected_actors": unreal_list_selected_actors,
        "unreal_list_ai_placed_actors": unreal_list_ai_placed_actors,
        "unreal_apply_actor_material_palette": unreal_apply_actor_material_palette,
        "unreal_plan_scene_lod_decimation": unreal_plan_scene_lod_decimation,
        "unreal_place_semantic_assets": unreal_place_semantic_assets,
        "unreal_prepare_open_world_ground": unreal_prepare_open_world_ground,
        "unreal_cleanup_ai_placed_actors": unreal_cleanup_ai_placed_actors,
        "unreal_setup_studio_lighting": unreal_setup_studio_lighting,
        "unreal_create_blockout_map": unreal_create_blockout_map,
        "unreal_spawn_basic_actor": unreal_spawn_basic_actor,
        "unreal_apply_arena_survivor_runtime_scaffold": unreal_apply_arena_survivor_runtime_scaffold,
        "unreal_reset_arena_survivor_runtime_state": unreal_reset_arena_survivor_runtime_state,
        "unreal_spawn_arena_survivor_player_pawn": unreal_spawn_arena_survivor_player_pawn,
        "unreal_spawn_arena_survivor_placeholder_enemies": unreal_spawn_arena_survivor_placeholder_enemies,
        "unreal_simulate_arena_survivor_pickup_collect": unreal_simulate_arena_survivor_pickup_collect,
        "unreal_simulate_arena_survivor_wave_clear": unreal_simulate_arena_survivor_wave_clear,
    }
    send({"type": "thinking"})
    summaries = []
    results_by_tool: dict[str, Any] = {}
    for step in planned_steps:
        name = str(step.get("tool", ""))
        kwargs = step.get("kwargs", {}) if isinstance(step.get("kwargs", {}), dict) else {}
        fn = tool_map.get(name)
        if fn is None:
            continue
        send({"type": "tool_call", "tool": name, "input": {"mode": "local_unreal_fast_path", **kwargs}})
        try:
            result = fn(**kwargs)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        send(
            {
                "type": "tool_result",
                "tool": name,
                "ok": bool(result.get("ok", False)) if isinstance(result, dict) else True,
                "result": _compact_for_client(result),
                "error": result.get("error") if isinstance(result, dict) else None,
            }
        )
        results_by_tool[name] = result
        if isinstance(result, dict):
            detail_keys = (
                "created_count",
                "placed_count",
                "changed_count",
                "deleted_count",
                "matched_count",
                "count",
                "aligned_count",
                "bottom_settled_count",
                "estimated_total_triangles",
                "actors_with_static_mesh",
                "existing_ground_count",
                "material_applied_count",
                "existing_count",
                "target_scene_mismatch",
            )
            details = [f"{key}={result.get(key)}" for key in detail_keys if key in result]
            detail_text = ", ".join(details) if details else "done"
            summaries.append(f"- {name}: ok={result.get('ok')} {detail_text}")
        else:
            summaries.append(f"- {name}: tamam")

    scan = results_by_tool.get("unreal_scan_project")
    any_success = any(isinstance(result, dict) and result.get("ok") for result in results_by_tool.values())
    if any_success and (not isinstance(scan, dict) or not scan.get("ok")):
        scan = unreal_scan_project(max_assets=1000, max_actors=300)
    map_name = scan.get("project", {}).get("map_name", "?") if isinstance(scan, dict) else "?"
    actor_counts = scan.get("actors", {}).get("by_category", {}) if isinstance(scan, dict) else {}
    template = plan.get("display_name") or plan.get("template") or "Unreal"
    reply = f"{template} aksiyon modu calisti; sadece yazi basmadim, sahneye tool uyguladim.\n\n"
    reply += "\n".join(summaries)
    reply += f"\n\nAktif map: {map_name}\nActor kategorileri: {actor_counts}"
    send({"type": "assistant_text", "content": reply, "done": True})
    send({"type": "assistant_done", "stop_reason": "local_unreal_action"})
    return True


@dataclass
class ClientHandle:
    sock: socket.socket
    addr: tuple
    alive: bool = True


class ChatServer:
    """Small newline-delimited JSON chat server.

    Each client gets an isolated orchestrator instance so chat history does not
    leak between Unity windows or test clients.
    
    Supports dual-agent mode when use_dual_agent=True.
    """

    SERVER_VERSION = "2.1.5"

    def __init__(
        self,
        config: Config,
        host: str = "127.0.0.1",
        port: int = 7778,
        use_dual_agent: bool = False,
        master_model: str = "qwen3.6:latest",
        worker_model: str = "qwen2.5:14b-instruct",
        reader_model: str = "qwen2.5:14b-instruct",
        enable_memory: bool = True,
        enable_context: bool = True,
        engine_context: str = "auto",
        auth_token: str = "",
        allow_remote: bool = False,
    ) -> None:
        self.config = config
        self.host = host
        self.port = port
        self.auth_token = auth_token or ""
        self.allow_remote = bool(allow_remote)
        self.use_dual_agent = use_dual_agent
        self.master_model = master_model
        self.worker_model = worker_model
        self.reader_model = reader_model
        self.enable_memory = enable_memory
        self.enable_context = enable_context
        self.engine_context = (engine_context or "auto").lower()
        self._listen_sock: Optional[socket.socket] = None
        self._running = False
        self._client_threads: list[threading.Thread] = []

    def start_blocking(self) -> None:
        # Guvenlik: loopback disi bir arayuze yalnizca acik izinle baglan.
        if not is_loopback_host(self.host) and not self.allow_remote:
            raise RuntimeError(
                f"ChatServer host {self.host!r} loopback degil. Loopback disi dinlemek icin "
                "UNITYTOOLS_ALLOW_REMOTE=1 ve bir UNITYTOOLS_SECRET/BRIDGE_TOKEN gerekir."
            )
        if not is_loopback_host(self.host) and self.allow_remote and not self.auth_token:
            raise RuntimeError(
                "ChatServer loopback disi dinleyecek ama token yok: bu kimlik dogrulamasiz "
                "uzaktan kod calistirma demektir. Once UNITYTOOLS_SECRET/BRIDGE_TOKEN ayarla."
            )
        self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._listen_sock.bind((self.host, self.port))
        except OSError as e:
            logger.error("ChatServer port'u acilamadi %s:%d -> %s", self.host, self.port, e)
            raise
        self._listen_sock.listen(5)
        self._running = True
        logger.info(
            "ChatServer listening: %s:%d (auth=%s)",
            self.host,
            self.port,
            "on" if self.auth_token else "off",
        )

        try:
            while self._running:
                try:
                    conn, addr = self._listen_sock.accept()
                except OSError:
                    break
                # Guvenlik: loopback disi peer'leri acik izin olmadan reddet.
                if not self.allow_remote and not is_loopback_addr(addr[0] if addr else None):
                    logger.warning("Loopback disi chat istemcisi reddedildi: %s", addr)
                    try:
                        conn.close()
                    except Exception:
                        pass
                    continue
                logger.info("New chat client: %s", addr)
                t = threading.Thread(
                    target=self._serve_client,
                    args=(ClientHandle(conn, addr),),
                    daemon=True,
                    name=f"chat-{addr[1]}",
                )
                t.start()
                self._client_threads.append(t)
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        if self._listen_sock is not None:
            try:
                self._listen_sock.close()
            except Exception:
                pass
        self._listen_sock = None

    def _serve_client(self, client: ClientHandle) -> None:
        # Create orchestrator based on mode
        if self.use_dual_agent:
            from .dual_agent import DualAgentOrchestrator
            orch = DualAgentOrchestrator(
                self.config,
                self.master_model,
                self.worker_model,
                reader_model=self.reader_model,
                enable_memory=self.enable_memory,
                enable_context=self.enable_context,
                engine_context=self.engine_context,
            )
            mode = "dual-agent"
            if self.enable_memory or self.enable_context:
                mode += " (enhanced)"
        else:
            orch = Orchestrator(self.config)
            mode = "single-agent"
        
        send = self._make_sender(client)

        # İlk handshake: Unity tarafı süreç sağlığını bundan anlar.
        try:
            tool_count = 0
            try:
                from .tool_registry import get_all_tools

                tool_count = len(get_all_tools())
            except Exception:
                pass
            send(
                {
                    "type": "hello",
                    "version": self.SERVER_VERSION,
                    "mode": mode,
                    "provider": self.config.provider,
                    "model": self.config.model if self.config.provider == "anthropic" else self.config.ollama_model,
                    "master_model": self.master_model if self.use_dual_agent else None,
                    "worker_model": self.worker_model if self.use_dual_agent else None,
                    "reader_model": self.reader_model if self.use_dual_agent else None,
                    "engine_context": self.engine_context,
                    "tools_loaded": tool_count,
                    "auth_required": bool(self.auth_token),
                }
            )
        except Exception:
            logger.exception("hello sent failed")

        buffer = b""
        try:
            while client.alive and self._running:
                try:
                    chunk = client.sock.recv(4096)
                except (ConnectionResetError, OSError):
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, _, buffer = buffer.partition(b"\n")
                    if not line.strip():
                        continue
                    self._handle_line(line, orch, send)
        except Exception as e:
            logger.exception("Client error: %s", client.addr)
            try:
                send({"type": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            try:
                client.sock.close()
            except Exception:
                pass
            logger.info("Chat client closed: %s", client.addr)

    def _handle_line(
        self,
        line: bytes,
        orch: Orchestrator,
        send: Callable[[dict], None],
    ) -> None:
        try:
            msg = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as e:
            send({"type": "error", "message": f"Invalid JSON: {e}"})
            return

        msg_type = msg.get("type")

        if msg_type == "ping":
            send({"type": "pong"})
            return

        # Guvenlik: ping disindaki her mesaj (reset / user_message / images) icin
        # yapilandirilmis token zorunlu. Bu, deterministik Unreal fast-path dahil
        # tum tool calistirma yollarini kimlik dogrulamasi arkasina alir.
        if not tokens_match(self.auth_token, msg.get("token")):
            send(
                {
                    "type": "error",
                    "message": (
                        "Unauthorized: gecersiz veya eksik token. Editor paneli ile "
                        "Python tarafinda ayni UNITYTOOLS_BRIDGE_TOKEN/UNITYTOOLS_SECRET "
                        "degeri ayarli olmali."
                    ),
                    "error_type": "AuthError",
                }
            )
            return

        if msg_type == "reset":
            orch.reset()
            send({"type": "assistant_text", "content": "History cleared.", "done": True})
            send({"type": "assistant_done", "stop_reason": "reset"})
            return

        if msg_type == "user_message":
            content = (msg.get("content") or msg.get("text") or "").strip()
            if not content:
                send({"type": "error", "message": "Empty message"})
                return
            unreal_project = str(msg.get("unreal_project") or "").strip()
            if unreal_project:
                os.environ["UNREALTOOLS_ACTIVE_PROJECT"] = unreal_project
            if self.engine_context == "unreal":
                if _try_local_unreal_action(content, send):
                    return
                local_reply = _local_unreal_ui_plan(content)
                if local_reply:
                    send({"type": "thinking"})
                    send({"type": "assistant_text", "content": local_reply, "done": True})
                    send({"type": "assistant_done", "stop_reason": "local_studio_plan"})
                    return
            content = self._apply_engine_context(content)
            self._process_user_message(content, orch, send)
            return

        if msg_type == "user_message_with_images":
            content = (msg.get("content") or "").strip()
            images = msg.get("images") or []
            if not content and not images:
                send({"type": "error", "message": "Empty message"})
                return
            if self.config.provider != "anthropic":
                send(
                    {
                        "type": "error",
                        "message": "Image input requires UNITYTOOLS_PROVIDER=anthropic (Claude vision).",
                    }
                )
                return
            blocks: list[dict[str, Any]] = []
            if content:
                blocks.append({"type": "text", "text": content})
            blocks = self._apply_engine_context(blocks)
            skipped_oversize = 0
            attached = 0
            for img in images:
                try:
                    mime = str(img.get("mime") or "image/png")
                    data_b64 = str(img.get("data_base64") or "")
                    if not data_b64.strip():
                        continue
                    # Anthropic görsel limiti 5MB; aşan görsel isteğin tamamını
                    # 400 ile düşürür. Burada eleyip kalanıyla devam ediyoruz.
                    if len(data_b64) > 6_800_000:  # base64 ~ 5MB ham veri
                        skipped_oversize += 1
                        continue
                    base64.b64decode(data_b64, validate=False)
                    blocks.append(
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime, "data": data_b64},
                        }
                    )
                    attached += 1
                except Exception:
                    continue
            if skipped_oversize:
                send(
                    {
                        "type": "assistant_text",
                        "content": f"[{skipped_oversize} görsel 5MB limitini aştığı için atlandı]",
                        "done": False,
                    }
                )
            if not content and not attached:
                # Engine-context ipucu bloğu tek başına anlamlı içerik değil.
                send({"type": "error", "message": "No usable content (all images skipped/invalid)."})
                return
            self._process_user_message(blocks, orch, send)
            return

        send({"type": "error", "message": f"Unknown message type: {msg_type}"})

    def _apply_engine_context(self, content: Any) -> Any:
        if self.engine_context not in {"unity", "unreal"}:
            return content
        if self.engine_context == "unreal":
            hint = (
                "ENGINE_CONTEXT: Unreal Editor. Prefer unreal_* tools for scene, asset, "
                "actor, import, and migration work. Do not use Unity tools unless the "
                "user explicitly asks for Unity.\n\n"
            )
        else:
            hint = (
                "ENGINE_CONTEXT: Unity Editor. Prefer unity_* tools for scene, asset, "
                "GameObject, material, and Autopilot work. Do not use Unreal tools unless "
                "the user explicitly asks for Unreal.\n\n"
            )
        if isinstance(content, str):
            return hint + content
        if isinstance(content, list):
            return [{"type": "text", "text": hint}] + content
        return content

    def _process_user_message(
        self,
        content: Any,
        orch: Any,  # Can be Orchestrator or DualAgentOrchestrator
        send: Callable[[dict], None],
    ) -> None:
        send({"type": "thinking"})

        def on_tool_call(name: str, params: dict) -> None:
            send({"type": "tool_call", "tool": name, "input": params})

        def on_tool_result(name: str, result: Any) -> None:
            ok = isinstance(result, dict) and result.get("ok", True)
            error = None
            payload = _compact_for_client(result)
            if isinstance(result, dict) and "error" in result and not ok:
                error = result.get("error")
            send(
                {
                    "type": "tool_result",
                    "tool": name,
                    "ok": ok,
                    "result": payload,
                    "error": error,
                }
            )

        def on_master_thinking(msg: str) -> None:
            send({"type": "master_thinking", "message": msg})

        def on_worker_executing(msg: str) -> None:
            send({"type": "worker_executing", "message": msg})

        try:
            # Check if dual-agent
            if hasattr(orch, 'master') and hasattr(orch, 'worker'):
                # Dual-agent mode
                result = orch.chat(
                    content,
                    on_master_thinking=on_master_thinking,
                    on_worker_executing=on_worker_executing,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                )
            else:
                # Single-agent mode
                result = orch.chat(
                    content,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                )
        except Exception as e:
            logger.exception("Orchestrator error")
            send({"type": "error", "message": str(e), "error_type": type(e).__name__})
            return

        if result.text:
            send({"type": "assistant_text", "content": result.text, "done": True})

        if hasattr(result, "reader_brief") and result.reader_brief:
            send({"type": "reader_brief", "brief": result.reader_brief})
        
        # Send additional dual-agent info if available
        if hasattr(result, 'master_plan') and result.master_plan:
            send({"type": "dual_agent_plan", "plan": result.master_plan})
        if hasattr(result, 'worker_reports') and result.worker_reports:
            send({"type": "dual_agent_reports", "reports": result.worker_reports})
        
        stop_reason = getattr(result, 'stop_reason', 'end_turn')
        send({"type": "assistant_done", "stop_reason": stop_reason})

    @staticmethod
    def _make_sender(client: ClientHandle) -> Callable[[dict], None]:
        lock = threading.Lock()

        def send(payload: dict) -> None:
            if not client.alive:
                return
            try:
                data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
                with lock:
                    client.sock.sendall(data)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                logger.debug("send failed (%s), marking client dead", e)
                client.alive = False

        return send
