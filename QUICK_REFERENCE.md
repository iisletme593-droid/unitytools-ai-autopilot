# ğŸš€ UnityTools AI - HÄ±zlÄ± Referans

## ğŸ“‹ HÄ±zlÄ± BaÅŸlangÄ±Ã§

### 1. Modelleri Ä°ndir
```powershell
ollama pull qwen2.5:14b-instruct          # Master (9GB)
ollama pull qwen2.5:14b-instruct    # Worker (9GB)
```

### 2. KonfigÃ¼rasyon (.env)
```env
UNITYTOOLS_PROVIDER=ollama
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

### 3. Unity'de BaÅŸlat
```
Window > UnityTools AI > Autopilot Chat
```

---

## ğŸ¯ Komutlar

### CLI KomutlarÄ±

```powershell
# Dual-agent chat (terminal)
unitytools dual-chat

# Chat server (Unity iÃ§in)
unitytools chat-server

# Memory olmadan
unitytools chat-server --no-memory

# Context olmadan
unitytools chat-server --no-context

# Diagnostics
unitytools doctor
unitytools status
unitytools unity-ping
```

### Unity MenÃ¼

```
Window > UnityTools AI > Autopilot Chat
Tools > UnityTools > Bridge Status
Tools > UnityTools > Start Embedded Chat Core
Tools > UnityTools > Stop Embedded Chat Core
```

---

## ğŸ’¬ Ã–rnek Promptlar

### Basit Komutlar
```
List all objects in the scene
Create a cube at position (0, 0, 0)
Move Cube to x=5 y=1 z=0
Delete all cubes
```

### Orta Seviye
```
Create 5 cubes in a line along X axis
Find all tree assets in the project
Place 10 trees around the scene
Create a grid of 3x3 spheres
```

### KarmaÅŸÄ±k Komutlar
```
Create a small forest with 20 realistic trees
Build a medieval village with houses and trees
Place rocks around the scene perimeter with natural spacing
Create a procedural island with terrain, trees, and rocks
```

---

## ğŸ“Š Sistem Durumu

### Kontrol KomutlarÄ±

```powershell
# Memory istatistikleri
python -c "from unitytools.core.memory_system import MemorySystem; m = MemorySystem(); print(m.get_statistics())"

# Pattern'leri gÃ¶rÃ¼ntÃ¼le
cat ~/.unitytools/memory/patterns.json

# Long-term memory
cat ~/.unitytools/memory/long_term_memory.jsonl

# Test Ã§alÄ±ÅŸtÄ±r
python test_full_integration.py
```

### Unity'de Kontrol

```
Tools > UnityTools > Bridge Status
```

GÃ¶rmeli:
- âœ… AI Connected
- âœ… Unity Bridge OK
- âœ… Core Managed
- âœ… Dual-Agent (eÄŸer aktifse)

---

## ğŸ”§ Sorun Giderme

### "Master Ã§ok yavaÅŸ"

**Normal**: 10-30s planlama beklenen davranÄ±ÅŸ  
**Anormal**: >2 dakika

```powershell
# Ollama'yÄ± restart et
taskkill /F /IM ollama.exe
ollama serve
```

### "Worker hata veriyor"

```powershell
# Unity bridge kontrolÃ¼
unitytools unity-ping

# Unity Editor aÃ§Ä±k mÄ± kontrol et
# Bridge Server Ã§alÄ±ÅŸÄ±yor mu kontrol et
```

### "Memory Ã§alÄ±ÅŸmÄ±yor"

```powershell
# Memory path kontrolÃ¼
ls ~/.unitytools/memory/

# Permissions kontrolÃ¼
# Manuel test
python test_full_integration.py
```

### "Context gÃ¼ncellenmiyor"

```python
# Python'da manuel test
from unitytools.core.context_manager import ContextManager
ctx = ContextManager()
ctx.update_scene([{"name": "Test", "position": {"x": 0, "y": 0, "z": 0}}])
print(ctx.get_context_summary())
```

---

## ğŸ“ˆ Performans Ä°puÃ§larÄ±

### Model SeÃ§imi

| Senaryo | Master | Worker | SÃ¼re |
|---------|--------|--------|------|
| **En iyi kalite** | qwen2.5:14b-instruct | qwen2.5:14b | 10-30s |
| HÄ±zlÄ± | qwen2.5:14b | qwen2.5:7b | 10-15s |
| Dengeli | qwen2.5:14b | qwen2.5:14b | 10-15s |

### Optimizasyon

```env
# Master iÃ§in daha az token
UNITYTOOLS_MAX_TOKENS=4096

# History limit
UNITYTOOLS_HISTORY_LIMIT=40

# Timeout ayarlarÄ±
UNITY_RPC_TIMEOUT=180
```

---

## ğŸ“ Best Practices

### Ä°lk KullanÄ±m

1. âœ… Basit komutlarla baÅŸla
2. âœ… Master'Ä±n planlarÄ±nÄ± incele
3. âœ… KarmaÅŸÄ±k gÃ¶revleri dene
4. âœ… Ã–ÄŸrenme sÃ¼recini gÃ¶zlemle

### KarmaÅŸÄ±k GÃ¶revler

1. âœ… Spesifik ol
2. âœ… Context bilgisi ver
3. âœ… Master'a zaman tanÄ± (10-30s)
4. âœ… SonuÃ§larÄ± kontrol et

### Ã–ÄŸrenme

1. âœ… Benzer gÃ¶revleri tekrarla
2. âœ… Pattern'leri kontrol et
3. âœ… Ä°statistikleri takip et
4. âœ… Memory'yi temizle (gerekirse)

---

## ğŸ“š DokÃ¼mantasyon Linkleri

### BaÅŸlangÄ±Ã§
- [README.md](README.md) - Ana dokÃ¼mantasyon
- [DUAL_AGENT_QUICKSTART.md](DUAL_AGENT_QUICKSTART.md) - 5 dakikada baÅŸlangÄ±Ã§

### DetaylÄ± KÄ±lavuzlar
- [DUAL_AGENT_GUIDE.md](DUAL_AGENT_GUIDE.md) - KapsamlÄ± kullanÄ±m
- [DUAL_AGENT_PHILOSOPHY.md](DUAL_AGENT_PHILOSOPHY.md) - Felsefe ve ROI
- [ENHANCED_FEATURES.md](ENHANCED_FEATURES.md) - Yeni Ã¶zellikler

### Teknik
- [DUAL_AGENT_SUMMARY.md](DUAL_AGENT_SUMMARY.md) - Teknik Ã¶zet
- [FINAL_INTEGRATION_REPORT.md](FINAL_INTEGRATION_REPORT.md) - Test sonuÃ§larÄ±
- [SYSTEM_STATUS.md](SYSTEM_STATUS.md) - Sistem durumu

---

## ğŸ”‘ Ã–nemli Dosyalar

### KonfigÃ¼rasyon
```
.env                              # Ana konfigÃ¼rasyon
~/.unitytools/memory/             # Memory storage
```

### Kod
```
unitytools/core/dual_agent.py     # Dual-agent orchestrator
unitytools/core/memory_system.py  # Memory & learning
unitytools/core/context_manager.py # Context management
unitytools/core/chat_server.py    # Chat server
```

### Unity
```
unity_plugin/Editor/Bridge/ChatWindow.cs  # Unity chat panel
unity_plugin/Editor/Bridge/BridgeServer.cs # Unity bridge
```

### Tests
```
test_full_integration.py          # Full integration test
test_enhanced_dual.py             # Enhanced dual-agent test
test_dual_agent.py                # Dual-agent test
```

---

## ğŸ’¡ HÄ±zlÄ± Notlar

### Master Agent
- Qwen 2.5:14b (9GB)
- 10-30s planlama
- Derin analiz
- Edge case detection

### Worker Agent
- Qwen 2.5:14b (9GB)
- Saniyeler iÃ§inde execution
- Tool calling
- DetaylÄ± raporlama

### Memory System
- Long-term memory
- Pattern recognition
- Learning from mistakes
- Success rate tracking

### Context Manager
- Scene state tracking
- Asset inventory
- Action history
- Smart suggestions

---

## ğŸ¯ HÄ±zlÄ± Test

```powershell
# 1. Test Ã§alÄ±ÅŸtÄ±r
python test_full_integration.py

# 2. Unity'de test et
# Window > UnityTools AI > Autopilot Chat
# Komut: "List all objects in the scene"

# 3. Memory kontrol et
cat ~/.unitytools/memory/patterns.json

# 4. KarmaÅŸÄ±k test
# Komut: "Create a small forest with 15 trees"
```

---

**HazÄ±r mÄ±sÄ±nÄ±z?**

```powershell
unitytools dual-chat
```

veya

```
Unity > Window > UnityTools AI > Autopilot Chat
```

**Ä°yi Ã§alÄ±ÅŸmalar!** ğŸš€

