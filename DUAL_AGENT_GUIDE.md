# Dual-Agent System Guide

## ğŸ¯ Konsept

UnityTools artÄ±k **iki farklÄ± AI modeli** kullanarak hiyerarÅŸik bir sistem sunuyor:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  MASTER AGENT (Qwen 2.5:14b - 9GB)        â”‚
â”‚  - GÃ¼Ã§lÃ¼ planlama (30-60 saniye)       â”‚
â”‚  - Derin analiz & strateji              â”‚
â”‚  - Edge case detection                  â”‚
â”‚  - Kalite kontrolÃ¼                      â”‚
â”‚  "Measure twice, cut once"             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
               â”‚ delegates
               â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  WORKER AGENT (Qwen 2.5:14b - 9GB)     â”‚
â”‚  - HÄ±zlÄ± tool execution                 â”‚
â”‚  - Master'Ä±n planÄ±nÄ± takip eder         â”‚
â”‚  - Unity/Blender komutlarÄ±              â”‚
â”‚  - DetaylÄ± raporlama                    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### ğŸ’¡ Felsefe

**"Ä°yi planlama her ÅŸeyi kolaylaÅŸtÄ±rÄ±r"**

Master agent 30-60 saniye planlama yapar. Bu yavaÅŸ gÃ¶rÃ¼nebilir ama:
- âœ… Daha az hata
- âœ… Daha iyi sonuÃ§lar
- âœ… Edge case'leri yakalar
- âœ… Alternatif planlar hazÄ±rlar
- âœ… Worker'a net talimatlar verir

SonuÃ§: **HÄ±zlÄ± baÅŸarÄ±sÄ±z execution < YavaÅŸ baÅŸarÄ±lÄ± planlama**

## ğŸ“¦ Kurulum

### 1. Modelleri Ä°ndirin

```powershell
# Worker model (hÄ±zlÄ±, tool execution)
ollama pull qwen2.5:14b-instruct

# Master model (gÃ¼Ã§lÃ¼, planning)
ollama pull qwen2.5:14b-instruct

# Alternatif: Daha hafif kombinasyon
ollama pull qwen2.5:7b-instruct   # Worker
ollama pull qwen2.5:14b-instruct  # Master
```

### 2. Dual-Agent Modunu AktifleÅŸtirin

`.env` dosyanÄ±zda:

```env
UNITYTOOLS_PROVIDER=ollama
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

## ğŸš€ KullanÄ±m

### Terminal Chat (Dual-Agent)

```powershell
# VarsayÄ±lan modeller ile
unitytools dual-chat

# Ã–zel modeller ile
unitytools dual-chat --master qwen2.5:14b-instruct --worker qwen2.5:7b-instruct
```

### Unity Editor'de Dual-Agent

Unity Editor'de chat panelini aÃ§Ä±n:
```
Window > UnityTools AI > Autopilot Chat
```

Panel otomatik olarak `.env` dosyasÄ±ndaki `USE_DUAL_AGENT` ayarÄ±nÄ± okur.

## ğŸ’¡ Ne Zaman KullanmalÄ±?

### Dual-Agent (Qwen 2.5:14b Master) Ä°deal:
- âœ… KarmaÅŸÄ±k sahne oluÅŸturma ("Create a medieval village with 50 buildings")
- âœ… Multi-step gÃ¶revler ("Import models, setup materials, arrange in grid")
- âœ… Planlama gerektiren iÅŸler ("Design a level layout with proper flow")
- âœ… BÃ¼yÃ¼k batch iÅŸlemler ("Place 100 trees with natural distribution")
- âœ… Edge case'lerin Ã¶nemli olduÄŸu durumlar
- âœ… Ä°lk denemede doÄŸru sonuÃ§ istediÄŸinizde

### Single-Agent Yeterli:
- âš¡ Basit sorgular ("List scene objects")
- âš¡ Tek tool Ã§aÄŸrÄ±sÄ± ("Create a cube")
- âš¡ HÄ±zlÄ± yanÄ±t gereken durumlar
- âš¡ Deneme-yanÄ±lma yapÄ±labilecek iÅŸler

### Master'Ä±n DeÄŸeri

30-60 saniye planlama sÃ¼resi ÅŸunlarÄ± saÄŸlar:

1. **Derin Analiz**: "Forest oluÅŸtur" derken:
   - Hangi tree asset'leri var?
   - Sahne durumu ne?
   - KaÃ§ aÄŸaÃ§ uygun?
   - NasÄ±l daÄŸÄ±tÄ±lmalÄ±?
   - Overlap olmamasÄ± iÃ§in min spacing ne olmalÄ±?

2. **Hata Ã–nleme**: 
   - Asset yoksa fallback plan
   - Sahne doluysa alternatif konum
   - Tool baÅŸarÄ±sÄ±z olursa baÅŸka yÃ¶ntem

3. **Optimizasyon**:
   - Gereksiz adÄ±mlarÄ± Ã§Ä±karÄ±r
   - Batch iÅŸlemleri birleÅŸtirir
   - En verimli tool'u seÃ§er

**SonuÃ§**: 1 dakika planlama + 30 saniye execution = BaÅŸarÄ±  
vs.  
5 saniye planlama + 2 dakika hata dÃ¼zeltme = Hayal kÄ±rÄ±klÄ±ÄŸÄ±

## ğŸ”§ YapÄ±landÄ±rma

### Model KombinasyonlarÄ±

| Master Model | Worker Model | KullanÄ±m Senaryosu | Planlama SÃ¼resi |
|--------------|--------------|-------------------|-----------------|
| **qwen2.5:14b-instruct** | **qwen2.5:14b** | **En iyi kalite (Ã–NERÄ°LEN)** | **10-30s** |
| qwen2.5:14b | qwen2.5:7b | HÄ±zlÄ± ama daha az detaylÄ± | 10-15s |
| qwen2.5:14b | qwen2.5:14b | AynÄ± model (fallback) | 10-15s |

**Ã–nerilen**: Qwen 2.5:14b master kullanÄ±n. 30-60 saniye beklemeye deÄŸer Ã§Ã¼nkÃ¼:
- Daha az hata = daha az dÃ¼zeltme = toplam daha hÄ±zlÄ±
- Ä°lk denemede doÄŸru sonuÃ§
- Edge case'leri yakalar
- Alternatif planlar hazÄ±rlar

### Performans AyarlarÄ±

`.env` dosyasÄ±nda:

```env
# Master iÃ§in daha az token (sadece planlama)
UNITYTOOLS_MAX_TOKENS=4096

# History limit (dual-agent daha fazla mesaj Ã¼retir)
UNITYTOOLS_HISTORY_LIMIT=60
```

## ğŸ“Š Avantajlar

1. **Daha Ä°yi Planlama**: BÃ¼yÃ¼k model karmaÅŸÄ±k gÃ¶revleri daha iyi analiz eder
2. **HÄ±zlÄ± Execution**: KÃ¼Ã§Ã¼k model tool'larÄ± hÄ±zlÄ± Ã§alÄ±ÅŸtÄ±rÄ±r
3. **Token VerimliliÄŸi**: Master sadece plan yapar, worker Ã§alÄ±ÅŸtÄ±rÄ±r
4. **AÃ§Ä±k Separation**: Planlama ve execution ayrÄ±, debug kolay

## ğŸ› Sorun Giderme

### "Master agent takes too long"
- Bu NORMAL! Master 30-60 saniye planlama yapar
- Bu sÃ¼re iyi planlama iÃ§in gerekli
- SabÄ±rlÄ± olun - sonuÃ§ daha iyi olacak
- EÄŸer gerÃ§ekten Ã§ok uzun sÃ¼rÃ¼yorsa (>2 dakika), Ollama'yÄ± restart edin

### "Master agent timeout" (>2 dakika)
- Ollama restart: `ollama serve` (yeni terminal)
- Model yeniden yÃ¼kle: `ollama run qwen2.5:14b-instruct` sonra Ctrl+D
- RAM yetersizse: 32GB+ RAM Ã¶nerilir Qwen 2.5:14b iÃ§in

### "Worker fails to execute"
- Worker model tool-calling desteklemiyor olabilir
- Minimum `qwen2.5:7b-instruct` kullanÄ±n
- `qwen2.5:14b-instruct` Ã¶nerilir

### "Results not as expected"
- Master'Ä±n planÄ±nÄ± kontrol edin (log'larda)
- Worker'Ä±n raporlarÄ±nÄ± inceleyin
- Daha spesifik istek yapÄ±n
- Master'a daha fazla context verin

## ğŸ”¬ GeliÅŸmiÅŸ: Simple Routing

Otomatik model seÃ§imi iÃ§in:

```python
from unitytools.core.simple_dual_agent import SimpleDualAgent

dual = SimpleDualAgent(
    config,
    complex_model="qwen2.5:14b-instruct",
    simple_model="qwen2.5:7b-instruct",
)

# Otomatik olarak uygun modeli seÃ§er
result = dual.chat("List scene objects")  # -> 7b model
result = dual.chat("Create a forest with 50 trees")  # -> 14b model
```

## ğŸ“ Ã–rnek Senaryolar

### Senaryo 1: KarmaÅŸÄ±k Sahne OluÅŸturma

```
User: Create a medieval village with houses, trees, and a central plaza

Master: 
  1. Search for medieval building assets
  2. Search for tree assets
  3. Create plaza (flat plane)
  4. Arrange buildings in circle around plaza
  5. Scatter trees between buildings
  6. Add lighting

Worker: [Executes each step with tools]
```

### Senaryo 2: Basit Sorgu

```
User: How many objects in the scene?

Master: Simple query, single tool call needed

Worker: unity_list_scene_objects() -> 15 objects
```

## ğŸ“ Best Practices

1. **Model SeÃ§imi**: BÃ¼yÃ¼k master = daha iyi plan, ama yavaÅŸ
2. **Timeout AyarlarÄ±**: Master iÃ§in 60s, worker iÃ§in 180s
3. **History Management**: Dual-agent daha fazla mesaj Ã¼retir, limit ayarlayÄ±n
4. **Error Handling**: Master plan baÅŸarÄ±sÄ±z olursa fallback to single-agent

## ğŸ”® Gelecek GeliÅŸtirmeler

- [ ] Adaptive routing (otomatik complexity detection)
- [ ] Multi-worker support (parallel execution)
- [ ] Plan caching (aynÄ± gÃ¶revler iÃ§in)
- [ ] Visual plan viewer (Unity Editor'de)
- [ ] Performance metrics (master vs worker timing)

## ğŸ“š API Reference

### DualAgentOrchestrator

```python
class DualAgentOrchestrator:
    def __init__(
        self,
        config: Config,
        master_model: str = "qwen2.5:14b-instruct",
        worker_model: str = "qwen2.5:14b-instruct",
    )
    
    def chat(
        self,
        user_message: str,
        on_master_thinking: Optional[Callable] = None,
        on_worker_executing: Optional[Callable] = None,
        on_tool_call: Optional[Callable] = None,
        on_tool_result: Optional[Callable] = None,
        max_iterations: int = 5,
    ) -> DualAgentResult
    
    def reset(self) -> None
```

### SimpleDualAgent

```python
class SimpleDualAgent:
    def __init__(
        self,
        config: Config,
        complex_model: str = "qwen2.5:14b-instruct",
        simple_model: str = "qwen2.5:14b-instruct",
    )
    
    def chat(
        self,
        user_message: str,
        on_tool_call: Optional[Callable] = None,
        on_tool_result: Optional[Callable] = None,
        on_model_selected: Optional[Callable] = None,
        max_iterations: int = 10,
    ) -> OrchestratorResult
```

## ğŸ¤ KatkÄ±da Bulunma

Dual-agent sistemi deneyseldir. Geri bildirimleriniz Ã§ok deÄŸerli:

- Hangi model kombinasyonlarÄ± iyi Ã§alÄ±ÅŸÄ±yor?
- Hangi gÃ¶revler iÃ§in dual-agent gerÃ§ekten faydalÄ±?
- Performance sorunlarÄ±?

GitHub Issues'da paylaÅŸÄ±n!

## ğŸ“„ Lisans

MIT License - Ana proje ile aynÄ±

