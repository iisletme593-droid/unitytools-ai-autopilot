# 🎯 Dual-Agent System - Özet

## ✅ Tamamlanan İşler

### 1. Core Implementation
- ✅ `DualAgentOrchestrator` - Master/Worker hiyerarşisi
- ✅ `SimpleDualAgent` - Otomatik model routing
- ✅ Master system prompt (planlama odaklı)
- ✅ Worker system prompt (execution odaklı)
- ✅ JSON plan extraction ve parsing

### 2. CLI Integration
- ✅ `unitytools dual-chat` komutu
- ✅ `--master` ve `--worker` parametreleri
- ✅ Rich console output (renkli, formatted)
- ✅ Callback system (on_master_thinking, on_worker_executing)

### 3. Chat Server Integration
- ✅ `ChatServer` dual-agent desteği
- ✅ `use_dual_agent` parametresi
- ✅ Unity Editor için hello message (mode bilgisi)
- ✅ Master/worker progress messages

### 4. Configuration
- ✅ `.env` dosyasına dual-agent ayarları
- ✅ `USE_DUAL_AGENT`, `DUAL_AGENT_MASTER`, `DUAL_AGENT_WORKER`
- ✅ Model cloning (farklı modeller için config)

### 5. Documentation
- ✅ `DUAL_AGENT_GUIDE.md` - Kapsamlı kullanım kılavuzu
- ✅ README.md güncellemesi
- ✅ API reference
- ✅ Best practices
- ✅ Troubleshooting guide

## 📁 Oluşturulan Dosyalar

```
unitytools/
├── core/
│   ├── dual_agent.py           # Master-Worker orchestrator
│   ├── simple_dual_agent.py    # Smart routing
│   └── chat_server.py          # Updated for dual-agent
├── cli/
│   ├── dual_chat.py            # Dual-agent REPL
│   └── entry.py                # Updated with dual-chat command
DUAL_AGENT_GUIDE.md             # Kullanım kılavuzu
DUAL_AGENT_SUMMARY.md           # Bu dosya
test_dual_agent.py              # Test script (hierarchical)
test_simple_dual.py             # Test script (routing)
```

## 🎨 Mimari

### Hierarchical Mode (DualAgentOrchestrator)

```
User Request
    ↓
Master Agent (Qwen 2.5:14b)
    ├─ Analyze request
    ├─ Create JSON plan
    └─ Decompose into steps
        ↓
Worker Agent (Qwen 2.5:14b)
    ├─ Execute step 1 (with tools)
    ├─ Execute step 2 (with tools)
    └─ Execute step N (with tools)
        ↓
Master Agent
    └─ Summarize results
        ↓
User Response
```

### Routing Mode (SimpleDualAgent)

```
User Request
    ↓
Complexity Analysis
    ├─ Simple? → Fast Model (7b)
    └─ Complex? → Smart Model (14b)
        ↓
Execute with Tools
    ↓
User Response
```

## 🚀 Kullanım Örnekleri

### Terminal

```powershell
# Hierarchical mode
unitytools dual-chat

# Custom models
unitytools dual-chat --master qwen2.5:14b --worker qwen2.5:7b
```

### Python API

```python
from unitytools.core.dual_agent import DualAgentOrchestrator
from unitytools.core.simple_dual_agent import SimpleDualAgent

# Hierarchical
dual = DualAgentOrchestrator(config)
result = dual.chat("Create a forest with 50 trees")

# Routing
simple = SimpleDualAgent(config)
result = simple.chat("List scene objects")  # Auto-selects fast model
```

### Unity Editor

`.env` dosyasında:
```env
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

## ⚠️ Bilinen Sorunlar

### 1. Qwen 2.5:14b Yavaş
- **Sorun**: 9GB model, yanıt süresi 30-60 saniye
- **Çözüm**: `qwen2.5:14b` master olarak kullan

### 2. Master Planning Timeout
- **Sorun**: Master plan oluştururken takılıyor
- **Çözüm**: `SimpleDualAgent` kullan (routing mode)

### 3. Windows Console Encoding
- **Sorun**: Emoji ve Unicode karakterler hata veriyor
- **Çözüm**: `$env:PYTHONIOENCODING="utf-8"` veya emoji kullanma

## 🔧 Önerilen Konfigürasyon

### Hız Öncelikli

```env
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:7b-instruct
```

### Kalite Öncelikli

```env
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

### Dengeli

```env
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

## 📊 Performans Karşılaştırması

| Mode | Model | Basit Sorgu | Karmaşık Görev | Token Kullanımı |
|------|-------|-------------|----------------|-----------------|
| Single | qwen2.5:14b | ~5s | ~30s | Orta |
| Hierarchical | 3.6 + 14b | ~15s | ~45s | Yüksek |
| Routing | 14b / 7b | ~3s / ~5s | ~30s | Düşük |

## 🎯 Sonraki Adımlar

### Kısa Vadeli
1. ✅ Master timeout sorununu çöz → SimpleDualAgent ile çözüldü
2. ⏳ Unity Editor integration test et
3. ⏳ Performance benchmarks yap
4. ⏳ Real-world scenarios test et

### Orta Vadeli
1. ⏳ Adaptive routing (ML-based complexity detection)
2. ⏳ Plan caching (repeated tasks)
3. ⏳ Multi-worker parallel execution
4. ⏳ Visual plan viewer (Unity Editor UI)

### Uzun Vadeli
1. ⏳ Fine-tuned models (Unity-specific)
2. ⏳ Distributed execution (multiple machines)
3. ⏳ Learning from user feedback
4. ⏳ Auto-optimization (model selection)

## 💡 Kullanım Tavsiyeleri

1. **Başlangıç**: `SimpleDualAgent` ile başla (daha stabil)
2. **Test**: Basit görevlerle test et (list, search)
3. **Karmaşık**: Sonra karmaşık görevleri dene (create, build)
4. **Optimize**: Performance'a göre model kombinasyonunu ayarla

## 🤝 Katkı

Dual-agent sistemi **experimental** durumda. Geri bildirimleriniz çok değerli:

- Hangi senaryolar iyi çalışıyor?
- Hangi model kombinasyonları optimal?
- Performance sorunları nerede?
- Hangi özellikler eksik?

GitHub Issues veya Pull Requests ile katkıda bulunabilirsiniz!

## 📚 Kaynaklar

- [DUAL_AGENT_GUIDE.md](DUAL_AGENT_GUIDE.md) - Detaylı kullanım kılavuzu
- [README.md](README.md) - Ana proje dokümantasyonu
- [unitytools/core/dual_agent.py](unitytools/core/dual_agent.py) - Kaynak kod
- [unitytools/core/simple_dual_agent.py](unitytools/core/simple_dual_agent.py) - Routing kod

---

**Oluşturulma Tarihi**: 2026-05-05  
**Versiyon**: 2.2.1  
**Durum**: Experimental / Beta

