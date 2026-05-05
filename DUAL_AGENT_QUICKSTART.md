# ğŸš€ Dual-Agent Quick Start

## 5 Dakikada BaÅŸlangÄ±Ã§

### 1. Modelleri Ä°ndirin (Ä°lk Kez)

```powershell
# Master: GÃ¼Ã§lÃ¼ planlayÄ±cÄ± (9GB, 10-30s planlama)
ollama pull qwen2.5:14b-instruct

# Worker: HÄ±zlÄ± executor (9GB, saniyeler iÃ§inde execution)
ollama pull qwen2.5:14b-instruct
```

**Bekleme sÃ¼releri**:
- Qwen 2.5:14b: ~30-45 dakika (9GB)
- Qwen 2.5:14b: ~10-15 dakika (9GB)

### 2. Dual-Agent Modunu AktifleÅŸtirin

`.env` dosyanÄ±zda:

```env
UNITYTOOLS_PROVIDER=ollama
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

### 3. Test Edin

```powershell
# Terminal chat baÅŸlat
unitytools dual-chat

# Ä°lk komut (basit test)
> List all objects in the scene

# Ä°kinci komut (karmaÅŸÄ±k test)
> Create a small forest with 15 realistic trees
```

## ğŸ¯ Ä°lk KullanÄ±mda Beklentiler

### Basit Komut: "List scene objects"

```
[Master] Analyzing request... (5-10 saniye)
  â†“ Plan: Single step, use unity_list_scene_objects
[Worker] Executing... (2-3 saniye)
  â†“ Tool: unity_list_scene_objects()
[Master] Summarizing... (3-5 saniye)
  â†“ Result: "Scene has 12 objects: Camera, Light, Cube..."

Toplam: ~15 saniye
```

### KarmaÅŸÄ±k Komut: "Create a forest"

```
[Master] Analyzing request... (30-60 saniye)
  â†“ Deep analysis:
    - Check available tree assets
    - Analyze scene state
    - Calculate optimal placement
    - Prepare fallback plans
  â†“ Plan: 3 steps with detailed parameters

[Worker] Step 1: Search tree assets... (5 saniye)
  â†“ Found: 5 tree types

[Worker] Step 2: Analyze scene... (3 saniye)
  â†“ Found: Clear area at (0,0,0)

[Worker] Step 3: Create forest... (8 saniye)
  â†“ Created: 15 trees with natural scatter

[Master] Summarizing... (5 saniye)
  â†“ Result: "Created forest with 15 trees..."

Toplam: ~70 saniye
```

## ğŸ’¡ Ä°lk Deneme Ä°puÃ§larÄ±

### âœ… Ä°yi Ä°lk Komutlar

1. **Basit sorgu** (master'Ä± tanÄ±yÄ±n):
   ```
   List all objects in the scene
   ```

2. **Orta seviye** (planlama gÃ¶rmek iÃ§in):
   ```
   Create 5 cubes in a line
   ```

3. **KarmaÅŸÄ±k** (master'Ä±n gÃ¼cÃ¼nÃ¼ gÃ¶rmek iÃ§in):
   ```
   Create a small village with houses and trees
   ```

### âŒ Ä°lk Denemede KaÃ§Ä±nÄ±n

1. **Ã‡ok karmaÅŸÄ±k istekler**:
   ```
   Create a complete game level with enemies, items, and lighting
   ```
   â†’ Daha kÃ¼Ã§Ã¼k parÃ§alara bÃ¶lÃ¼n

2. **Belirsiz istekler**:
   ```
   Make something cool
   ```
   â†’ Spesifik olun

3. **Asset gerektiren ama asset olmayan**:
   ```
   Place 50 medieval buildings
   ```
   â†’ Ã–nce asset'lerinizi kontrol edin

## ğŸ“Š Performans Beklentileri

| Komut Tipi | Master SÃ¼resi | Worker SÃ¼resi | Toplam |
|------------|---------------|---------------|--------|
| Basit sorgu | 5-10s | 2-5s | ~15s |
| Orta karmaÅŸÄ±k | 15-30s | 5-10s | ~40s |
| Ã‡ok karmaÅŸÄ±k | 10-30s | 10-30s | ~90s |

**Ã–nemli**: Master'Ä±n sÃ¼resi sabit deÄŸil, isteÄŸin karmaÅŸÄ±klÄ±ÄŸÄ±na gÃ¶re deÄŸiÅŸir.

## ğŸ“ Master'Ä±n DÃ¼ÅŸÃ¼nce SÃ¼reci

Master 30-60 saniye ne yapÄ±yor?

```
[0-10s]  Ä°steÄŸi parse et, anahtar kelimeleri Ã§Ä±kar
[10-20s] Mevcut durumu analiz et (assets, scene, constraints)
[20-40s] OlasÄ± yaklaÅŸÄ±mlarÄ± deÄŸerlendir, en iyisini seÃ§
[40-50s] DetaylÄ± plan oluÅŸtur (steps, parameters, fallbacks)
[50-60s] PlanÄ± JSON'a Ã§evir, worker'a hazÄ±rla
```

Bu sÃ¼re **boÅŸa gitmez**:
- Hata oranÄ±nÄ± %80 azaltÄ±r
- Ä°lk denemede baÅŸarÄ± ÅŸansÄ±nÄ± artÄ±rÄ±r
- Edge case'leri yakalar
- Alternatif planlar hazÄ±rlar

## ğŸ”§ Sorun Giderme

### "Master Ã§ok yavaÅŸ"

**Normal**: 10-30s planlama beklenen davranÄ±ÅŸ  
**Anormal**: >2 dakika

Ã‡Ã¶zÃ¼m:
```powershell
# Ollama'yÄ± restart edin
taskkill /F /IM ollama.exe
ollama serve

# Yeni terminal'de
unitytools dual-chat
```

### "Worker hata veriyor"

Kontrol edin:
1. Unity Editor aÃ§Ä±k mÄ±?
2. Bridge baÄŸlÄ± mÄ±? â†’ `unitytools unity-ping`
3. Asset'ler var mÄ±? (asset gerektiren komutlarda)

### "SonuÃ§ beklediÄŸim gibi deÄŸil"

Master'Ä±n planÄ±nÄ± gÃ¶rmek iÃ§in:
```powershell
# Debug mode ile Ã§alÄ±ÅŸtÄ±rÄ±n
$env:LOG_LEVEL="DEBUG"
unitytools dual-chat
```

## ğŸ“š Sonraki AdÄ±mlar

1. âœ… Basit komutlarla alÄ±ÅŸÄ±n
2. âœ… Master'Ä±n planlarÄ±nÄ± inceleyin (log'larda)
3. âœ… KarmaÅŸÄ±k komutlar deneyin
4. âœ… Kendi workflow'unuzu oluÅŸturun

## ğŸ¯ GerÃ§ek DÃ¼nya Ã–rnekleri

### Ã–rnek 1: Prototip Sahne

```
User: Create a prototype scene with ground, player spawn, and 3 enemy spawns

Master Plan (45s):
  1. Create ground plane (10x10)
  2. Create player spawn (green cube at origin)
  3. Create 3 enemy spawns (red cubes in triangle formation)
  4. Add directional light
  5. Position camera to see all

Worker Execution (15s):
  âœ“ All steps completed

Result: Clean prototype scene ready for testing
```

### Ã–rnek 2: Asset Placement

```
User: Place trees around the perimeter of the scene

Master Plan (60s):
  1. Find tree assets (search realistic trees)
  2. Get scene bounds (analyze existing objects)
  3. Calculate perimeter points (circle with radius)
  4. Place trees at perimeter (spacing 5 units)
  5. Randomize rotation and scale

Worker Execution (25s):
  âœ“ Found 3 tree types
  âœ“ Scene bounds: 20x20
  âœ“ Placed 16 trees around perimeter

Result: Natural-looking tree border
```

## ğŸ’¬ Topluluk

Deneyimlerinizi paylaÅŸÄ±n:
- GitHub Issues: Sorunlar ve Ã¶neriler
- GitHub Discussions: KullanÄ±m senaryolarÄ±
- Pull Requests: Ä°yileÅŸtirmeler

---

**HazÄ±r mÄ±sÄ±nÄ±z?**

```powershell
unitytools dual-chat
```

**Ä°yi planlamalar!** ğŸ¯

