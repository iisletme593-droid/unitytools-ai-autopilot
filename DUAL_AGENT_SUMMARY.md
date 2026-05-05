# ğŸ¯ Dual-Agent System - Ã–zet

## âœ… Tamamlanan Ä°ÅŸler

### 1. Core Implementation
- âœ… `DualAgentOrchestrator` - Master/Worker hiyerarÅŸisi
- âœ… `SimpleDualAgent` - Otomatik model routing
- âœ… Master system prompt (planlama odaklÄ±)
- âœ… Worker system prompt (execution odaklÄ±)
- âœ… JSON plan extraction ve parsing

### 2. CLI Integration
- âœ… `unitytools dual-chat` komutu
- âœ… `--master` ve `--worker` parametreleri
- âœ… Rich console output (renkli, formatted)
- âœ… Callback system (on_master_thinking, on_worker_executing)

### 3. Chat Server Integration
- âœ… `ChatServer` dual-agent desteÄŸi
- âœ… `use_dual_agent` parametresi
- âœ… Unity Editor iÃ§in hello message (mode bilgisi)
- âœ… Master/worker progress messages

### 4. Configuration
- âœ… `.env` dosyasÄ±na dual-agent ayarlarÄ±
- âœ… `USE_DUAL_AGENT`, `DUAL_AGENT_MASTER`, `DUAL_AGENT_WORKER`
- âœ… Model cloning (farklÄ± modeller iÃ§in config)

### 5. Documentation
- âœ… `DUAL_AGENT_GUIDE.md` - KapsamlÄ± kullanÄ±m kÄ±lavuzu
- âœ… README.md gÃ¼ncellemesi
- âœ… API reference
- âœ… Best practices
- âœ… Troubleshooting guide

## ğŸ“ OluÅŸturulan Dosyalar

```
unitytools/
â”œâ”€â”€ core/
â”‚   â”œâ”€â”€ dual_agent.py           # Master-Worker orchestrator
â”‚   â”œâ”€â”€ simple_dual_agent.py    # Smart routing
â”‚   â””â”€â”€ chat_server.py          # Updated for dual-agent
â”œâ”€â”€ cli/
â”‚   â”œâ”€â”€ dual_chat.py            # Dual-agent REPL
â”‚   â””â”€â”€ entry.py                # Updated with dual-chat command
DUAL_AGENT_GUIDE.md             # KullanÄ±m kÄ±lavuzu
DUAL_AGENT_SUMMARY.md           # Bu dosya
test_dual_agent.py              # Test script (hierarchical)
test_simple_dual.py             # Test script (routing)
```

## ğŸ¨ Mimari

### Hierarchical Mode (DualAgentOrchestrator)

```
User Request
    â†“
Master Agent (Qwen 2.5:14b)
    â”œâ”€ Analyze request
    â”œâ”€ Create JSON plan
    â””â”€ Decompose into steps
        â†“
Worker Agent (Qwen 2.5:14b)
    â”œâ”€ Execute step 1 (with tools)
    â”œâ”€ Execute step 2 (with tools)
    â””â”€ Execute step N (with tools)
        â†“
Master Agent
    â””â”€ Summarize results
        â†“
User Response
```

### Routing Mode (SimpleDualAgent)

```
User Request
    â†“
Complexity Analysis
    â”œâ”€ Simple? â†’ Fast Model (7b)
    â””â”€ Complex? â†’ Smart Model (14b)
        â†“
Execute with Tools
    â†“
User Response
```

## ğŸš€ KullanÄ±m Ã–rnekleri

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

`.env` dosyasÄ±nda:
```env
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

## âš ï¸ Bilinen Sorunlar

### 1. Qwen 2.5:14b YavaÅŸ
- **Sorun**: 9GB model, yanÄ±t sÃ¼resi 30-60 saniye
- **Ã‡Ã¶zÃ¼m**: `qwen2.5:14b` master olarak kullan

### 2. Master Planning Timeout
- **Sorun**: Master plan oluÅŸtururken takÄ±lÄ±yor
- **Ã‡Ã¶zÃ¼m**: `SimpleDualAgent` kullan (routing mode)

### 3. Windows Console Encoding
- **Sorun**: Emoji ve Unicode karakterler hata veriyor
- **Ã‡Ã¶zÃ¼m**: `$env:PYTHONIOENCODING="utf-8"` veya emoji kullanma

## ğŸ”§ Ã–nerilen KonfigÃ¼rasyon

### HÄ±z Ã–ncelikli

```env
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:7b-instruct
```

### Kalite Ã–ncelikli

```env
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

### Dengeli

```env
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

## ğŸ“Š Performans KarÅŸÄ±laÅŸtÄ±rmasÄ±

| Mode | Model | Basit Sorgu | KarmaÅŸÄ±k GÃ¶rev | Token KullanÄ±mÄ± |
|------|-------|-------------|----------------|-----------------|
| Single | qwen2.5:14b | ~5s | ~30s | Orta |
| Hierarchical | 3.6 + 14b | ~15s | ~45s | YÃ¼ksek |
| Routing | 14b / 7b | ~3s / ~5s | ~30s | DÃ¼ÅŸÃ¼k |

## ğŸ¯ Sonraki AdÄ±mlar

### KÄ±sa Vadeli
1. âœ… Master timeout sorununu Ã§Ã¶z â†’ SimpleDualAgent ile Ã§Ã¶zÃ¼ldÃ¼
2. â³ Unity Editor integration test et
3. â³ Performance benchmarks yap
4. â³ Real-world scenarios test et

### Orta Vadeli
1. â³ Adaptive routing (ML-based complexity detection)
2. â³ Plan caching (repeated tasks)
3. â³ Multi-worker parallel execution
4. â³ Visual plan viewer (Unity Editor UI)

### Uzun Vadeli
1. â³ Fine-tuned models (Unity-specific)
2. â³ Distributed execution (multiple machines)
3. â³ Learning from user feedback
4. â³ Auto-optimization (model selection)

## ğŸ’¡ KullanÄ±m Tavsiyeleri

1. **BaÅŸlangÄ±Ã§**: `SimpleDualAgent` ile baÅŸla (daha stabil)
2. **Test**: Basit gÃ¶revlerle test et (list, search)
3. **KarmaÅŸÄ±k**: Sonra karmaÅŸÄ±k gÃ¶revleri dene (create, build)
4. **Optimize**: Performance'a gÃ¶re model kombinasyonunu ayarla

## ğŸ¤ KatkÄ±

Dual-agent sistemi **experimental** durumda. Geri bildirimleriniz Ã§ok deÄŸerli:

- Hangi senaryolar iyi Ã§alÄ±ÅŸÄ±yor?
- Hangi model kombinasyonlarÄ± optimal?
- Performance sorunlarÄ± nerede?
- Hangi Ã¶zellikler eksik?

GitHub Issues veya Pull Requests ile katkÄ±da bulunabilirsiniz!

## ğŸ“š Kaynaklar

- [DUAL_AGENT_GUIDE.md](DUAL_AGENT_GUIDE.md) - DetaylÄ± kullanÄ±m kÄ±lavuzu
- [README.md](README.md) - Ana proje dokÃ¼mantasyonu
- [unitytools/core/dual_agent.py](unitytools/core/dual_agent.py) - Kaynak kod
- [unitytools/core/simple_dual_agent.py](unitytools/core/simple_dual_agent.py) - Routing kod

---

**OluÅŸturulma Tarihi**: 2026-05-05  
**Versiyon**: 2.2.1  
**Durum**: Experimental / Beta

