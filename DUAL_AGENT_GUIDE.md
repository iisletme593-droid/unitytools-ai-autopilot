# Dual-Agent System Guide

## 🎯 Konsept

UnityTools artık **iki farklı AI modeli** kullanarak hiyerarşik bir sistem sunuyor:

```
┌─────────────────────────────────────────┐
│  MASTER AGENT (Qwen 2.5:14b - 9GB)        │
│  - Güçlü planlama (30-60 saniye)       │
│  - Derin analiz & strateji              │
│  - Edge case detection                  │
│  - Kalite kontrolü                      │
│  "Measure twice, cut once"             │
└──────────────┬──────────────────────────┘
               │ delegates
               â–¼
┌─────────────────────────────────────────┐
│  WORKER AGENT (Qwen 2.5:14b - 9GB)     │
│  - Hızlı tool execution                 │
│  - Master'ın planını takip eder         │
│  - Unity/Blender komutları              │
│  - Detaylı raporlama                    │
└─────────────────────────────────────────┘
```

### 💡 Felsefe

**"İyi planlama her şeyi kolaylaştırır"**

Master agent 30-60 saniye planlama yapar. Bu yavaş görünebilir ama:
- ✅ Daha az hata
- ✅ Daha iyi sonuçlar
- ✅ Edge case'leri yakalar
- ✅ Alternatif planlar hazırlar
- ✅ Worker'a net talimatlar verir

Sonuç: **Hızlı başarısız execution < Yavaş başarılı planlama**

## 📦 Kurulum

### 1. Modelleri İndirin

```powershell
# Worker model (hızlı, tool execution)
ollama pull qwen2.5:14b-instruct

# Master model (güçlü, planning)
ollama pull qwen2.5:14b-instruct

# Alternatif: Daha hafif kombinasyon
ollama pull qwen2.5:7b-instruct   # Worker
ollama pull qwen2.5:14b-instruct  # Master
```

### 2. Dual-Agent Modunu Aktifleştirin

`.env` dosyanızda:

```env
UNITYTOOLS_PROVIDER=ollama
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

## 🚀 Kullanım

### Terminal Chat (Dual-Agent)

```powershell
# Varsayılan modeller ile
unitytools dual-chat

# Özel modeller ile
unitytools dual-chat --master qwen2.5:14b-instruct --worker qwen2.5:7b-instruct
```

### Unity Editor'de Dual-Agent

Unity Editor'de chat panelini açın:
```
Window > UnityTools AI > Autopilot Chat
```

Panel otomatik olarak `.env` dosyasındaki `USE_DUAL_AGENT` ayarını okur.

## 💡 Ne Zaman Kullanmalı?

### Dual-Agent (Qwen 2.5:14b Master) İdeal:
- ✅ Karmaşık sahne oluşturma ("Create a medieval village with 50 buildings")
- ✅ Multi-step görevler ("Import models, setup materials, arrange in grid")
- ✅ Planlama gerektiren işler ("Design a level layout with proper flow")
- ✅ Büyük batch işlemler ("Place 100 trees with natural distribution")
- ✅ Edge case'lerin önemli olduğu durumlar
- ✅ İlk denemede doğru sonuç istediğinizde

### Single-Agent Yeterli:
- âš¡ Basit sorgular ("List scene objects")
- âš¡ Tek tool çağrısı ("Create a cube")
- âš¡ Hızlı yanıt gereken durumlar
- âš¡ Deneme-yanılma yapılabilecek işler

### Master'ın Değeri

30-60 saniye planlama süresi şunları sağlar:

1. **Derin Analiz**: "Forest oluştur" derken:
   - Hangi tree asset'leri var?
   - Sahne durumu ne?
   - Kaç ağaç uygun?
   - Nasıl dağıtılmalı?
   - Overlap olmaması için min spacing ne olmalı?

2. **Hata Önleme**: 
   - Asset yoksa fallback plan
   - Sahne doluysa alternatif konum
   - Tool başarısız olursa başka yöntem

3. **Optimizasyon**:
   - Gereksiz adımları çıkarır
   - Batch işlemleri birleştirir
   - En verimli tool'u seçer

**Sonuç**: 1 dakika planlama + 30 saniye execution = Başarı  
vs.  
5 saniye planlama + 2 dakika hata düzeltme = Hayal kırıklığı

## 🔧 Yapılandırma

### Model Kombinasyonları

| Master Model | Worker Model | Kullanım Senaryosu | Planlama Süresi |
|--------------|--------------|-------------------|-----------------|
| **qwen2.5:14b-instruct** | **qwen2.5:14b** | **En iyi kalite (ÖNERİLEN)** | **10-30s** |
| qwen2.5:14b | qwen2.5:7b | Hızlı ama daha az detaylı | 10-15s |
| qwen2.5:14b | qwen2.5:14b | Aynı model (fallback) | 10-15s |

**Önerilen**: Qwen 2.5:14b master kullanın. 30-60 saniye beklemeye değer çünkü:
- Daha az hata = daha az düzeltme = toplam daha hızlı
- İlk denemede doğru sonuç
- Edge case'leri yakalar
- Alternatif planlar hazırlar

### Performans Ayarları

`.env` dosyasında:

```env
# Master için daha az token (sadece planlama)
UNITYTOOLS_MAX_TOKENS=4096

# History limit (dual-agent daha fazla mesaj üretir)
UNITYTOOLS_HISTORY_LIMIT=60
```

## 📊 Avantajlar

1. **Daha İyi Planlama**: Büyük model karmaşık görevleri daha iyi analiz eder
2. **Hızlı Execution**: Küçük model tool'ları hızlı çalıştırır
3. **Token Verimliliği**: Master sadece plan yapar, worker çalıştırır
4. **Açık Separation**: Planlama ve execution ayrı, debug kolay

## 🐛 Sorun Giderme

### "Master agent takes too long"
- Bu NORMAL! Master 30-60 saniye planlama yapar
- Bu süre iyi planlama için gerekli
- Sabırlı olun - sonuç daha iyi olacak
- Eğer gerçekten çok uzun sürüyorsa (>2 dakika), Ollama'yı restart edin

### "Master agent timeout" (>2 dakika)
- Ollama restart: `ollama serve` (yeni terminal)
- Model yeniden yükle: `ollama run qwen2.5:14b-instruct` sonra Ctrl+D
- RAM yetersizse: 32GB+ RAM önerilir Qwen 2.5:14b için

### "Worker fails to execute"
- Worker model tool-calling desteklemiyor olabilir
- Minimum `qwen2.5:7b-instruct` kullanın
- `qwen2.5:14b-instruct` önerilir

### "Results not as expected"
- Master'ın planını kontrol edin (log'larda)
- Worker'ın raporlarını inceleyin
- Daha spesifik istek yapın
- Master'a daha fazla context verin

## 🔬 Gelişmiş: Simple Routing

Otomatik model seçimi için:

```python
from unitytools.core.simple_dual_agent import SimpleDualAgent

dual = SimpleDualAgent(
    config,
    complex_model="qwen2.5:14b-instruct",
    simple_model="qwen2.5:7b-instruct",
)

# Otomatik olarak uygun modeli seçer
result = dual.chat("List scene objects")  # -> 7b model
result = dual.chat("Create a forest with 50 trees")  # -> 14b model
```

## 📝 Örnek Senaryolar

### Senaryo 1: Karmaşık Sahne Oluşturma

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

## 🎓 Best Practices

1. **Model Seçimi**: Büyük master = daha iyi plan, ama yavaş
2. **Timeout Ayarları**: Master için 60s, worker için 180s
3. **History Management**: Dual-agent daha fazla mesaj üretir, limit ayarlayın
4. **Error Handling**: Master plan başarısız olursa fallback to single-agent

## 🔮 Gelecek Geliştirmeler

- [ ] Adaptive routing (otomatik complexity detection)
- [ ] Multi-worker support (parallel execution)
- [ ] Plan caching (aynı görevler için)
- [ ] Visual plan viewer (Unity Editor'de)
- [ ] Performance metrics (master vs worker timing)

## 📚 API Reference

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

## 🤝 Katkıda Bulunma

Dual-agent sistemi deneyseldir. Geri bildirimleriniz çok değerli:

- Hangi model kombinasyonları iyi çalışıyor?
- Hangi görevler için dual-agent gerçekten faydalı?
- Performance sorunları?

GitHub Issues'da paylaşın!

## 📄 Lisans

MIT License - Ana proje ile aynı

