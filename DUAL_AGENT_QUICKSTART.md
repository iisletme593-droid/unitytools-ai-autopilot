# 🚀 Dual-Agent Quick Start

## 5 Dakikada Başlangıç

### 1. Modelleri İndirin (İlk Kez)

```powershell
# Master: Güçlü planlayıcı (9GB, 10-30s planlama)
ollama pull qwen2.5:14b-instruct

# Worker: Hızlı executor (9GB, saniyeler içinde execution)
ollama pull qwen2.5:14b-instruct
```

**Bekleme süreleri**:
- Qwen 2.5:14b: ~30-45 dakika (9GB)
- Qwen 2.5:14b: ~10-15 dakika (9GB)

### 2. Dual-Agent Modunu Aktifleştirin

`.env` dosyanızda:

```env
UNITYTOOLS_PROVIDER=ollama
USE_DUAL_AGENT=true
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

### 3. Test Edin

```powershell
# Terminal chat başlat
unitytools dual-chat

# İlk komut (basit test)
> List all objects in the scene

# İkinci komut (karmaşık test)
> Create a small forest with 15 realistic trees
```

## 🎯 İlk Kullanımda Beklentiler

### Basit Komut: "List scene objects"

```
[Master] Analyzing request... (5-10 saniye)
  ↓ Plan: Single step, use unity_list_scene_objects
[Worker] Executing... (2-3 saniye)
  ↓ Tool: unity_list_scene_objects()
[Master] Summarizing... (3-5 saniye)
  ↓ Result: "Scene has 12 objects: Camera, Light, Cube..."

Toplam: ~15 saniye
```

### Karmaşık Komut: "Create a forest"

```
[Master] Analyzing request... (30-60 saniye)
  ↓ Deep analysis:
    - Check available tree assets
    - Analyze scene state
    - Calculate optimal placement
    - Prepare fallback plans
  ↓ Plan: 3 steps with detailed parameters

[Worker] Step 1: Search tree assets... (5 saniye)
  ↓ Found: 5 tree types

[Worker] Step 2: Analyze scene... (3 saniye)
  ↓ Found: Clear area at (0,0,0)

[Worker] Step 3: Create forest... (8 saniye)
  ↓ Created: 15 trees with natural scatter

[Master] Summarizing... (5 saniye)
  ↓ Result: "Created forest with 15 trees..."

Toplam: ~70 saniye
```

## 💡 İlk Deneme İpuçları

### ✅ İyi İlk Komutlar

1. **Basit sorgu** (master'ı tanıyın):
   ```
   List all objects in the scene
   ```

2. **Orta seviye** (planlama görmek için):
   ```
   Create 5 cubes in a line
   ```

3. **Karmaşık** (master'ın gücünü görmek için):
   ```
   Create a small village with houses and trees
   ```

### ❌ İlk Denemede Kaçının

1. **Çok karmaşık istekler**:
   ```
   Create a complete game level with enemies, items, and lighting
   ```
   → Daha küçük parçalara bölün

2. **Belirsiz istekler**:
   ```
   Make something cool
   ```
   → Spesifik olun

3. **Asset gerektiren ama asset olmayan**:
   ```
   Place 50 medieval buildings
   ```
   → Önce asset'lerinizi kontrol edin

## 📊 Performans Beklentileri

| Komut Tipi | Master Süresi | Worker Süresi | Toplam |
|------------|---------------|---------------|--------|
| Basit sorgu | 5-10s | 2-5s | ~15s |
| Orta karmaşık | 15-30s | 5-10s | ~40s |
| Çok karmaşık | 10-30s | 10-30s | ~90s |

**Önemli**: Master'ın süresi sabit değil, isteğin karmaşıklığına göre değişir.

## 🎓 Master'ın Düşünce Süreci

Master 30-60 saniye ne yapıyor?

```
[0-10s]  İsteği parse et, anahtar kelimeleri çıkar
[10-20s] Mevcut durumu analiz et (assets, scene, constraints)
[20-40s] Olası yaklaşımları değerlendir, en iyisini seç
[40-50s] Detaylı plan oluştur (steps, parameters, fallbacks)
[50-60s] Planı JSON'a çevir, worker'a hazırla
```

Bu süre **boşa gitmez**:
- Hata oranını %80 azaltır
- İlk denemede başarı şansını artırır
- Edge case'leri yakalar
- Alternatif planlar hazırlar

## 🔧 Sorun Giderme

### "Master çok yavaş"

**Normal**: 10-30s planlama beklenen davranış  
**Anormal**: >2 dakika

Çözüm:
```powershell
# Ollama'yı restart edin
taskkill /F /IM ollama.exe
ollama serve

# Yeni terminal'de
unitytools dual-chat
```

### "Worker hata veriyor"

Kontrol edin:
1. Unity Editor açık mı?
2. Bridge bağlı mı? → `unitytools unity-ping`
3. Asset'ler var mı? (asset gerektiren komutlarda)

### "Sonuç beklediğim gibi değil"

Master'ın planını görmek için:
```powershell
# Debug mode ile çalıştırın
$env:LOG_LEVEL="DEBUG"
unitytools dual-chat
```

## 📚 Sonraki Adımlar

1. ✅ Basit komutlarla alışın
2. ✅ Master'ın planlarını inceleyin (log'larda)
3. ✅ Karmaşık komutlar deneyin
4. ✅ Kendi workflow'unuzu oluşturun

## 🎯 Gerçek Dünya Örnekleri

### Örnek 1: Prototip Sahne

```
User: Create a prototype scene with ground, player spawn, and 3 enemy spawns

Master Plan (45s):
  1. Create ground plane (10x10)
  2. Create player spawn (green cube at origin)
  3. Create 3 enemy spawns (red cubes in triangle formation)
  4. Add directional light
  5. Position camera to see all

Worker Execution (15s):
  ✓ All steps completed

Result: Clean prototype scene ready for testing
```

### Örnek 2: Asset Placement

```
User: Place trees around the perimeter of the scene

Master Plan (60s):
  1. Find tree assets (search realistic trees)
  2. Get scene bounds (analyze existing objects)
  3. Calculate perimeter points (circle with radius)
  4. Place trees at perimeter (spacing 5 units)
  5. Randomize rotation and scale

Worker Execution (25s):
  ✓ Found 3 tree types
  ✓ Scene bounds: 20x20
  ✓ Placed 16 trees around perimeter

Result: Natural-looking tree border
```

## 💬 Topluluk

Deneyimlerinizi paylaşın:
- GitHub Issues: Sorunlar ve öneriler
- GitHub Discussions: Kullanım senaryoları
- Pull Requests: İyileştirmeler

---

**Hazır mısınız?**

```powershell
unitytools dual-chat
```

**İyi planlamalar!** 🎯

