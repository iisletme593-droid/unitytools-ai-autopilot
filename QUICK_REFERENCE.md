# 🚀 UnityTools AI - Hızlı Referans

## 📋 Hızlı Başlangıç

### 1. Modelleri İndir
```powershell
ollama pull qwen2.5:14b-instruct          # Master (9GB)
ollama pull qwen2.5:14b-instruct    # Worker (9GB)
```

### 2. Konfigürasyon (.env)
```env
UNITYTOOLS_PROVIDER=ollama
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

### 3. Unity'de Başlat
```
Window > UnityTools AI > Autopilot Chat
```

---

## 🎯 Komutlar

### CLI Komutları

```powershell
# Dual-agent chat (terminal)
unitytools dual-chat

# Chat server (Unity için)
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

### Unity Menü

```
Window > UnityTools AI > Autopilot Chat
Tools > UnityTools > Bridge Status
Tools > UnityTools > Start Embedded Chat Core
Tools > UnityTools > Stop Embedded Chat Core
```

---

## 💬 Örnek Promptlar

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

### Karmaşık Komutlar
```
Create a small forest with 20 realistic trees
Build a medieval village with houses and trees
Place rocks around the scene perimeter with natural spacing
Create a procedural island with terrain, trees, and rocks
```

---

## 📊 Sistem Durumu

### Kontrol Komutları

```powershell
# Memory istatistikleri
python -c "from unitytools.core.memory_system import MemorySystem; m = MemorySystem(); print(m.get_statistics())"

# Pattern'leri görüntüle
cat ~/.unitytools/memory/patterns.json

# Long-term memory
cat ~/.unitytools/memory/long_term_memory.jsonl

# Test çalıştır
python test_full_integration.py
```

### Unity'de Kontrol

```
Tools > UnityTools > Bridge Status
```

Görmeli:
- ✅ AI Connected
- ✅ Unity Bridge OK
- ✅ Core Managed
- ✅ Dual-Agent (eğer aktifse)

---

## 🔧 Sorun Giderme

### "Master çok yavaş"

**Normal**: 10-30s planlama beklenen davranış  
**Anormal**: >2 dakika

```powershell
# Ollama'yı restart et
taskkill /F /IM ollama.exe
ollama serve
```

### "Worker hata veriyor"

```powershell
# Unity bridge kontrolü
unitytools unity-ping

# Unity Editor açık mı kontrol et
# Bridge Server çalışıyor mu kontrol et
```

### "Memory çalışmıyor"

```powershell
# Memory path kontrolü
ls ~/.unitytools/memory/

# Permissions kontrolü
# Manuel test
python test_full_integration.py
```

### "Context güncellenmiyor"

```python
# Python'da manuel test
from unitytools.core.context_manager import ContextManager
ctx = ContextManager()
ctx.update_scene([{"name": "Test", "position": {"x": 0, "y": 0, "z": 0}}])
print(ctx.get_context_summary())
```

---

## 📈 Performans İpuçları

### Model Seçimi

| Senaryo | Master | Worker | Süre |
|---------|--------|--------|------|
| **En iyi kalite** | qwen2.5:14b-instruct | qwen2.5:14b | 10-30s |
| Hızlı | qwen2.5:14b | qwen2.5:7b | 10-15s |
| Dengeli | qwen2.5:14b | qwen2.5:14b | 10-15s |

### Optimizasyon

```env
# Master için daha az token
UNITYTOOLS_MAX_TOKENS=4096

# History limit
UNITYTOOLS_HISTORY_LIMIT=40

# Timeout ayarları
UNITY_RPC_TIMEOUT=180
```

---

## 🎓 Best Practices

### İlk Kullanım

1. ✅ Basit komutlarla başla
2. ✅ Master'ın planlarını incele
3. ✅ Karmaşık görevleri dene
4. ✅ Öğrenme sürecini gözlemle

### Karmaşık Görevler

1. ✅ Spesifik ol
2. ✅ Context bilgisi ver
3. ✅ Master'a zaman tanı (10-30s)
4. ✅ Sonuçları kontrol et

### Öğrenme

1. ✅ Benzer görevleri tekrarla
2. ✅ Pattern'leri kontrol et
3. ✅ İstatistikleri takip et
4. ✅ Memory'yi temizle (gerekirse)

---

## 📚 Dokümantasyon Linkleri

### Başlangıç
- [README.md](README.md) - Ana dokümantasyon
- [DUAL_AGENT_QUICKSTART.md](DUAL_AGENT_QUICKSTART.md) - 5 dakikada başlangıç

### Detaylı Kılavuzlar
- [DUAL_AGENT_GUIDE.md](DUAL_AGENT_GUIDE.md) - Kapsamlı kullanım
- [DUAL_AGENT_PHILOSOPHY.md](DUAL_AGENT_PHILOSOPHY.md) - Felsefe ve ROI
- [ENHANCED_FEATURES.md](ENHANCED_FEATURES.md) - Yeni özellikler

### Teknik
- [DUAL_AGENT_SUMMARY.md](DUAL_AGENT_SUMMARY.md) - Teknik özet
- [FINAL_INTEGRATION_REPORT.md](FINAL_INTEGRATION_REPORT.md) - Test sonuçları
- [SYSTEM_STATUS.md](SYSTEM_STATUS.md) - Sistem durumu

---

## 🔑 Önemli Dosyalar

### Konfigürasyon
```
.env                              # Ana konfigürasyon
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

## 💡 Hızlı Notlar

### Master Agent
- Qwen 2.5:14b (9GB)
- 10-30s planlama
- Derin analiz
- Edge case detection

### Worker Agent
- Qwen 2.5:14b (9GB)
- Saniyeler içinde execution
- Tool calling
- Detaylı raporlama

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

## 🎯 Hızlı Test

```powershell
# 1. Test çalıştır
python test_full_integration.py

# 2. Unity'de test et
# Window > UnityTools AI > Autopilot Chat
# Komut: "List all objects in the scene"

# 3. Memory kontrol et
cat ~/.unitytools/memory/patterns.json

# 4. Karmaşık test
# Komut: "Create a small forest with 15 trees"
```

---

**Hazır mısınız?**

```powershell
unitytools dual-chat
```

veya

```
Unity > Window > UnityTools AI > Autopilot Chat
```

**İyi çalışmalar!** 🚀

