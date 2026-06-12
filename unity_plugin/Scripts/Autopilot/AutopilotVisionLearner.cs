#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    // ─────────────────────────────────────────────────────────────────────────
    //  THORNY IVY — VISION LEARNER
    //
    //  Çalışma prensibi:
    //    1. AutopilotData/reference_images/*.png dosyalarını yükler
    //    2. Her birinden renk/parlaklık/sis metrikleri çıkarır → hedef belirler
    //    3. Unity kamerasından screenshot alır, aynı metrikleri ölçer
    //    4. Farkı minimize edecek parametre ayarı yapar (hill-climbing)
    //    5. Ölçek doğrulaması — her nesne için beklenen metre aralığı
    //    6. Hedef skora (≥78) ulaşana veya 60 iterasyon bitene dek devam eder
    //
    //  Menü: Tools > Autopilot > ★ Vision Learner
    // ─────────────────────────────────────────────────────────────────────────
    public static class AutopilotVisionLearner
    {
        const float ScoreThreshold   = 78f;
        const int   MaxIterations    = 60;
        const int   SnapW            = 320;
        const int   SnapH            = 180;
        const float StepDecay        = 0.92f; // iterasyon başına adım küçülme oranı

        static readonly string RefDir = Path.GetFullPath(
            Path.Combine(Application.dataPath, "..", "AutopilotData", "reference_images"));

        // ── Görsel metrik paketi ──────────────────────────────────────────────
        struct VM
        {
            public float Lum;            // ortalama luminans
            public float R, G, B;        // kanal ortalamaları
            public float WarmFrac;       // turuncu-sıcak piksel oranı (kampfire/fener)
            public float DarkFrac;       // lum<0.35 oranı (gotik karanlık)
            public float BlueFrac;       // mavi > kırmızı*1.2 oranı (sis soğukluğu)
            public float SkyLum;         // üst 1/3 luminans (gökyüzü/sis)
            public float MidLum;         // orta 1/3 luminans (orman/yol)
            public float GroundLum;      // alt 1/3 luminans (zemin)
            public float Saturation;     // ortalama doygunluk
        }

        // Varsayılan hedef — tüm görseller analiz edilince üzerine yazılır
        static VM _target = new VM
        {
            Lum = 0.112f, R = 0.202f, G = 0.222f, B = 0.305f,
            WarmFrac = 0.078f, DarkFrac = 0.748f, BlueFrac = 0.362f,
            SkyLum = 0.148f, MidLum = 0.105f, GroundLum = 0.058f,
            Saturation = 0.255f,
        };

        static bool _targetReady;
        static bool _running;
        static int  _iter;
        static float _bestScore;
        static float _prevScore;
        static float _step = 1.0f;
        static readonly List<string> _log = new();

        // Her iterasyon sonrası kaydedilen en iyi parametre kümesi
        static SceneParams _bestParams;

        struct SceneParams
        {
            public float FogDensity;
            public Color FogColor;
            public Color Ambient;
            public float SunIntensity;
        }

        // ── Menü ─────────────────────────────────────────────────────────────
        [MenuItem("Tools/Autopilot/★ Vision Learner - Başlat")]
        public static void Start()
        {
            if (_running) { Debug.Log("[VisionLearner] Zaten çalışıyor."); return; }
            LoadTarget();
            _running   = true;
            _iter      = 0;
            _bestScore = 0f;
            _prevScore = 0f;
            _step      = 1.0f;
            _log.Clear();
            _log.Add($"Hedef skor ≥ {ScoreThreshold}/100. Referans: {RefDir}");
            Debug.Log("[VisionLearner] Öğrenme başlatıldı.");
            EditorApplication.delayCall += Tick;
        }

        [MenuItem("Tools/Autopilot/★ Vision Learner - Durdur")]
        public static void Stop()
        {
            _running = false;
            SaveScene();
            Debug.Log($"[VisionLearner] Durduruldu. En iyi: {_bestScore:F1}/100  " +
                      $"({_iter} iterasyon)");
            foreach (var l in _log.TakeLast(25)) Debug.Log(l);
        }

        [MenuItem("Tools/Autopilot/★ Vision Learner - Tek Analiz")]
        public static void AnalyzeOnce()
        {
            LoadTarget();
            var tex = Snapshot();
            if (tex == null) { Debug.LogWarning("[VisionLearner] Screenshot alınamadı."); return; }
            var m = Measure(tex);
            UnityEngine.Object.DestroyImmediate(tex);
            float s = Score(m);
            Debug.Log($"[VisionLearner] Skor: {s:F1}/100\n" +
                      $"  Lum={m.Lum:F3} (hedef {_target.Lum:F3}) | " +
                      $"Warm={m.WarmFrac:F3} (h:{_target.WarmFrac:F3}) | " +
                      $"Dark={m.DarkFrac:F3} (h:{_target.DarkFrac:F3})\n" +
                      $"  RGB=({m.R:F3},{m.G:F3},{m.B:F3}) " +
                      $"h=({_target.R:F3},{_target.G:F3},{_target.B:F3})\n" +
                      $"  Sky={m.SkyLum:F3} | Mid={m.MidLum:F3} | Ground={m.GroundLum:F3}");
        }

        [MenuItem("Tools/Autopilot/★ Vision Learner - Ölçek Doğrula")]
        public static void ValidateScalesMenu() => ValidateScales(verbose: true);

        // ── Ana öğrenme döngüsü ───────────────────────────────────────────────
        static void Tick()
        {
            if (!_running) return;
            if (_iter >= MaxIterations) { Stop(); return; }

            // Screenshot & ölçüm
            var tex = Snapshot();
            VM actual = default;
            float score = 0f;
            if (tex != null)
            {
                actual = Measure(tex);
                score  = Score(actual);
                UnityEngine.Object.DestroyImmediate(tex);
            }

            // Loglama
            string arrow = score > _prevScore + 0.2f ? "↑" : score < _prevScore - 0.2f ? "↓" : "—";
            string line  = $"[{_iter:D3}] {arrow} {score:F1}/100  " +
                           $"Lum:{actual.Lum:F3} Warm:{actual.WarmFrac:F3} " +
                           $"Dark:{actual.DarkFrac:F3} Fog:{RenderSettings.fogDensity:F3} " +
                           $"Amb:{RenderSettings.ambientIntensity:F2}";
            _log.Add(line);
            Debug.Log("[VisionLearner] " + line);

            if (score > _bestScore)
            {
                _bestScore = score;
                _bestParams = ReadParams();
            }
            _prevScore = score;

            if (score >= ScoreThreshold)
            {
                _log.Add($"✓ Hedef aşıldı: {score:F1}/100 ({_iter} iter)");
                Debug.Log($"[VisionLearner] ✓ Tamamlandı! {score:F1}/100");
                Stop();
                return;
            }

            // Kötü durum → tam yeniden kurulum (8. veya 20. iterasyonda)
            if ((_iter == 8 && score < 22f) || (_iter == 20 && score < 35f))
            {
                Debug.Log($"[VisionLearner] Skor çok düşük ({score:F1}) — sahne yeniden kuruluyor.");
                SceneBuilder.BuildScene();
                SceneMaterialPainter.PaintAll();
                IslandTreePainter.PaintAll();
            }

            Adjust(actual, score);
            _step *= StepDecay;
            _iter++;
            EditorApplication.delayCall += Tick;
        }

        // ── Parametre ayarı — hill-climbing ───────────────────────────────────
        static void Adjust(VM a, float score)
        {
            float s = _step;

            // 1. PARLAKLK ─────────────────────────────────────────────────────
            float lumErr = a.Lum - _target.Lum;
            if (lumErr > 0.008f) // çok parlak
            {
                RenderSettings.ambientLight = ScaleColor(RenderSettings.ambientLight,
                    1f - 0.10f * s * Mathf.Clamp01(lumErr / 0.05f));
                AdjustSun(-0.04f * s);
            }
            else if (lumErr < -0.008f) // çok karanlık
            {
                RenderSettings.ambientLight = ScaleColor(RenderSettings.ambientLight,
                    1f + 0.06f * s * Mathf.Clamp01(-lumErr / 0.05f));
                AdjustSun(+0.025f * s);
            }

            // 2. SİS YOĞUNLUĞU ───────────────────────────────────────────────
            // Karanlık piksel oranı düşükse → sis artır (nesneler daha az görünür olacak)
            float darkErr = a.DarkFrac - _target.DarkFrac;
            if (darkErr < -0.05f)
                RenderSettings.fogDensity = Mathf.Clamp(
                    RenderSettings.fogDensity + 0.003f * s, 0.012f, 0.080f);
            else if (darkErr > 0.06f)
                RenderSettings.fogDensity = Mathf.Clamp(
                    RenderSettings.fogDensity - 0.002f * s, 0.012f, 0.080f);

            // 3. SİS RENGİ — hedef mavi-gri'ye yumuşak yakınsama ────────────
            Color fogTarget = new Color(0.28f, 0.30f, 0.38f);
            RenderSettings.fogColor = Color.Lerp(
                RenderSettings.fogColor, fogTarget, 0.08f * s);

            // 4. SICAK AKSAN (kampfire/fener) ─────────────────────────────────
            float warmErr = a.WarmFrac - _target.WarmFrac;
            if (warmErr < -0.02f)      // yetersiz sıcak ışık
                AdjustWarmLights(+0.6f * s, +2f * s);
            else if (warmErr > 0.03f)  // fazla sıcak
                AdjustWarmLights(-0.3f * s, 0f);

            // 5. MOR/KALE IŞIK ────────────────────────────────────────────────
            // Sis çok soğuk değilse kale büyüsel ışınını koru
            if (a.BlueFrac < _target.BlueFrac * 0.80f)
            {
                AdjustMagicLights(+0.4f * s);
                Color fc = RenderSettings.fogColor;
                RenderSettings.fogColor = new Color(fc.r, fc.g,
                    Mathf.Clamp(fc.b + 0.008f * s, 0f, 0.6f));
            }

            // 6. AMBİENT RENK — hedef: koyu mavi-gri ────────────────────────
            Color ambTarget = new Color(0.022f, 0.028f, 0.052f);
            RenderSettings.ambientLight = Color.Lerp(
                RenderSettings.ambientLight, ambTarget, 0.05f * s);

            // 7. ÖLÇEK DOĞRULAMA (her 8 iterasyonda) ─────────────────────────
            if (_iter % 8 == 0) ValidateScales(verbose: false);

            // 8. MATERYAL YENİDEN BOYAMA (her 18 iterasyonda, düşük skor) ─────
            if (_iter % 18 == 9 && score < 55f)
            {
                SceneMaterialPainter.RunAsTask(out _);
                IslandTreePainter.RunAsTask(out _);
            }

            SaveScene();
        }

        // ── Referans görsellerden hedef metrikleri hesapla ────────────────────
        static void LoadTarget()
        {
            if (_targetReady) return;

            if (!Directory.Exists(RefDir))
            {
                Debug.LogWarning($"[VisionLearner] Referans klasör yok: {RefDir}  Varsayılan hedef kullanılıyor.");
                _targetReady = true;
                return;
            }

            string[] pngs = Directory.GetFiles(RefDir, "*.png");
            if (pngs.Length == 0) { _targetReady = true; return; }

            var acc = new VM();
            int n = 0;
            foreach (string p in pngs)
            {
                byte[] data = File.ReadAllBytes(p);
                var t = new Texture2D(2, 2, TextureFormat.RGB24, false);
                if (!ImageConversion.LoadImage(t, data)) { UnityEngine.Object.DestroyImmediate(t); continue; }
                var m = Measure(t);
                UnityEngine.Object.DestroyImmediate(t);
                acc.Lum        += m.Lum;
                acc.R          += m.R;
                acc.G          += m.G;
                acc.B          += m.B;
                acc.WarmFrac   += m.WarmFrac;
                acc.DarkFrac   += m.DarkFrac;
                acc.BlueFrac   += m.BlueFrac;
                acc.SkyLum     += m.SkyLum;
                acc.MidLum     += m.MidLum;
                acc.GroundLum  += m.GroundLum;
                acc.Saturation += m.Saturation;
                n++;
            }

            if (n == 0) { _targetReady = true; return; }
            float inv = 1f / n;
            _target = new VM
            {
                Lum        = acc.Lum       * inv,
                R          = acc.R         * inv,
                G          = acc.G         * inv,
                B          = acc.B         * inv,
                WarmFrac   = acc.WarmFrac  * inv,
                DarkFrac   = acc.DarkFrac  * inv,
                BlueFrac   = acc.BlueFrac  * inv,
                SkyLum     = acc.SkyLum    * inv,
                MidLum     = acc.MidLum    * inv,
                GroundLum  = acc.GroundLum * inv,
                Saturation = acc.Saturation* inv,
            };
            _targetReady = true;
            Debug.Log($"[VisionLearner] {n} görsel analiz edildi.\n" +
                      $"  Hedef: Lum={_target.Lum:F3}  Warm={_target.WarmFrac:F3}  " +
                      $"Dark={_target.DarkFrac:F3}  Sis={_target.SkyLum:F3}");
        }

        // ── Screenshot (HDRP dahil) ───────────────────────────────────────────
        static Texture2D Snapshot()
        {
            var cam = Camera.main;
            if (cam == null) return null;
            try
            {
                var rt = new RenderTexture(SnapW, SnapH, 24, RenderTextureFormat.ARGB32);
                var prev = cam.targetTexture;
                cam.targetTexture = rt;
                cam.Render();
                cam.targetTexture = prev;

                var prevActive = RenderTexture.active;
                RenderTexture.active = rt;
                var tex = new Texture2D(SnapW, SnapH, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, SnapW, SnapH), 0, 0);
                tex.Apply();
                RenderTexture.active = prevActive;
                rt.Release();
                UnityEngine.Object.DestroyImmediate(rt);
                return tex;
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[VisionLearner] Screenshot hatası: {ex.Message}");
                return null;
            }
        }

        // ── Piksel analizi ────────────────────────────────────────────────────
        static VM Measure(Texture2D tex)
        {
            var pixels = tex.GetPixels();
            int total  = pixels.Length;
            int w = tex.width, h = tex.height;
            int topThird    = h * 2 / 3;
            int bottomThird = h / 3;

            float sumLum=0, sumR=0, sumG=0, sumB=0, sumSat=0;
            float warm=0, dark=0, blue=0;
            float skySum=0, skyN=0, midSum=0, midN=0, groundSum=0, groundN=0;

            for (int i = 0; i < total; i++)
            {
                Color p   = pixels[i];
                float lum = 0.299f * p.r + 0.587f * p.g + 0.114f * p.b;
                sumLum += lum; sumR += p.r; sumG += p.g; sumB += p.b;

                // Doygunluk
                float mx = Mathf.Max(p.r, p.g, p.b);
                float mn = Mathf.Min(p.r, p.g, p.b);
                sumSat += mx > 0.001f ? (mx - mn) / mx : 0f;

                // Sıcak turuncu tespiti (kampfire / fener)
                if (p.r > 0.38f && p.g > 0.12f && p.b < 0.14f &&
                    p.r > p.g * 1.4f && p.r > p.b * 2.2f) warm++;

                // Karanlık piksel
                if (lum < 0.35f) dark++;

                // Soğuk mavi piksel (sis / atmosfer)
                if (p.b > p.r * 1.22f && p.b > 0.20f) blue++;

                // Dikey bölge
                int row = i / w;
                if (row >= topThird)         { skySum    += lum; skyN++;    }
                else if (row >= bottomThird) { midSum    += lum; midN++;    }
                else                         { groundSum += lum; groundN++; }
            }

            float inv = 1f / total;
            return new VM
            {
                Lum        = sumLum  * inv,
                R          = sumR    * inv,
                G          = sumG    * inv,
                B          = sumB    * inv,
                WarmFrac   = warm    * inv,
                DarkFrac   = dark    * inv,
                BlueFrac   = blue    * inv,
                SkyLum     = skyN    > 0 ? skySum    / skyN    : 0f,
                MidLum     = midN    > 0 ? midSum    / midN    : 0f,
                GroundLum  = groundN > 0 ? groundSum / groundN : 0f,
                Saturation = sumSat  * inv,
            };
        }

        // ── Çok metrikli skor (0–100) ─────────────────────────────────────────
        static float Score(VM a)
        {
            float s = 100f;
            s -= Mathf.Abs(a.Lum      - _target.Lum)      * 240f; // ağırlık 24
            s -= Mathf.Abs(a.WarmFrac - _target.WarmFrac)  * 220f; // ağırlık 22 — kampfire kritik
            s -= Mathf.Abs(a.DarkFrac - _target.DarkFrac)  * 140f; // ağırlık 14
            s -= Mathf.Abs(a.SkyLum   - _target.SkyLum)    * 100f; // ağırlık 10
            s -= Mathf.Abs(a.GroundLum- _target.GroundLum) * 100f; // ağırlık 10
            s -= Mathf.Abs(a.R        - _target.R)          * 70f;
            s -= Mathf.Abs(a.G        - _target.G)          * 70f;
            s -= Mathf.Abs(a.B        - _target.B)          * 70f;
            s -= Mathf.Abs(a.BlueFrac - _target.BlueFrac)   * 60f;
            s -= Mathf.Abs(a.Saturation-_target.Saturation) * 60f;
            return Mathf.Clamp(s, 0f, 100f);
        }

        // ── Işık yardımcıları ─────────────────────────────────────────────────
        static void AdjustSun(float delta)
        {
            foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(
                FindObjectsInactive.Include))
            {
                if (l.type != LightType.Directional) continue;
                l.intensity = Mathf.Clamp(l.intensity + delta, 0.05f, 1.5f);
                break;
            }
        }

        static void AdjustWarmLights(float intDelta, float rangeDelta)
        {
            foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(
                FindObjectsInactive.Include))
            {
                if (l.type != LightType.Point) continue;
                if (l.color.r > 0.55f && l.color.b < 0.25f) // sıcak ton filtresi
                {
                    l.intensity = Mathf.Clamp(l.intensity + intDelta, 0.5f, 12f);
                    l.range     = Mathf.Clamp(l.range + rangeDelta,    5f, 40f);
                }
            }
        }

        static void AdjustMagicLights(float intDelta)
        {
            foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(
                FindObjectsInactive.Include))
            {
                if (l.type != LightType.Point) continue;
                // Mor/mavi ton — kale sihirli ışın
                if (l.color.b > l.color.r * 1.1f && l.color.r > 0.20f)
                    l.intensity = Mathf.Clamp(l.intensity + intDelta, 0.5f, 14f);
            }
        }

        // ── Ölçek doğrulaması ─────────────────────────────────────────────────
        // Her nesne tipi için beklenen yükseklik aralığı (metre, world scale)
        static readonly (string kw, float min, float max)[] SizeTable =
        {
            ("PineTree",      7f,  18f),
            ("FirTree",       7f,  18f),
            ("IslandTree",    5f,  16f),
            ("DeadTreeTrunk", 4f,  14f),
            ("TreeStump",     0.3f, 1.2f),
            ("Boulder1",      0.6f, 3.0f),
            ("Rock7",         0.25f,1.5f),
            ("Rock9",         0.25f,1.5f),
            ("RockFace",      1.0f, 5.0f),
            ("RockMossSet",   0.4f, 2.0f),
            ("StoneFire",     0.4f, 1.2f),
            ("Lantern",       0.18f,0.55f),
            ("WoodenLantern", 0.18f,0.55f),
            ("BrassDiya",     0.15f,0.45f),
            ("Barrel",        0.55f,1.10f),
            ("WoodenCrate",   0.35f,0.90f),
            ("WickerBasket",  0.25f,0.65f),
            ("WoodenBucket",  0.22f,0.55f),
            ("TreasureChest", 0.35f,0.80f),
            ("WineBarrel",    0.55f,1.10f),
            ("ModularFort",  15.0f,38.0f),
            ("GothicBed",     1.8f, 2.6f),
            ("GothicCabinet", 1.8f, 2.8f),
            ("WornBookshelf", 1.6f, 2.4f),
            ("GothicTable",   0.7f, 1.0f),
            ("WoodenTable",   0.7f, 1.0f),
            ("WoodenStool",   0.4f, 0.7f),
            ("WoodenPier",    3.0f,12.0f),
        };

        public static void ValidateScales(bool verbose = false)
        {
            int fixed_ = 0, ok = 0;
            var allGo = UnityEngine.Object.FindObjectsByType<GameObject>(
                FindObjectsInactive.Include);

            foreach (var go in allGo)
            {
                if (go == null || !go.name.StartsWith("_RPG_")) continue;

                foreach (var (kw, minM, maxM) in SizeTable)
                {
                    if (!go.name.Contains(kw, StringComparison.OrdinalIgnoreCase)) continue;

                    // Bounding box yüksekliği kullan
                    var renderers = go.GetComponentsInChildren<MeshRenderer>(true);
                    if (renderers.Length == 0) break;

                    Bounds b = renderers[0].bounds;
                    foreach (var r in renderers.Skip(1)) b.Encapsulate(r.bounds);
                    float h = b.size.y;
                    if (h < 0.001f) break;

                    if (h < minM)
                    {
                        go.transform.localScale *= (minM / h);
                        if (verbose) Debug.Log($"[ScaleValidator] ↑ {go.name} {h:F2}m→{minM:F2}m");
                        fixed_++;
                    }
                    else if (h > maxM)
                    {
                        go.transform.localScale *= (maxM / h);
                        if (verbose) Debug.Log($"[ScaleValidator] ↓ {go.name} {h:F2}m→{maxM:F2}m");
                        fixed_++;
                    }
                    else ok++;
                    break;
                }
            }

            if (fixed_ > 0 || verbose)
                Debug.Log($"[ScaleValidator] {fixed_} düzeltildi, {ok} uygun.");
        }

        // ── Yardımcılar ───────────────────────────────────────────────────────
        static Color ScaleColor(Color c, float factor) =>
            new Color(
                Mathf.Clamp(c.r * factor, 0f, 0.35f),
                Mathf.Clamp(c.g * factor, 0f, 0.35f),
                Mathf.Clamp(c.b * factor, 0f, 0.35f), c.a);

        static SceneParams ReadParams() => new SceneParams
        {
            FogDensity   = RenderSettings.fogDensity,
            FogColor     = RenderSettings.fogColor,
            Ambient      = RenderSettings.ambientLight,
            SunIntensity = GetSunIntensity(),
        };

        static float GetSunIntensity()
        {
            foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(
                FindObjectsInactive.Include))
                if (l.type == LightType.Directional) return l.intensity;
            return 0f;
        }

        static void SaveScene()
        {
            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        }

        // ── Autopilot Brain entegrasyonu ──────────────────────────────────────
        public static float GetCurrentScore()
        {
            LoadTarget();
            var tex = Snapshot();
            if (tex == null) return -1f;
            var m = Measure(tex);
            UnityEngine.Object.DestroyImmediate(tex);
            return Score(m);
        }

        public static bool RunAsTask(out string reason)
        {
            try
            {
                LoadTarget();
                var tex = Snapshot();
                float score = 0f;
                if (tex != null)
                {
                    score = Score(Measure(tex));
                    UnityEngine.Object.DestroyImmediate(tex);
                }
                if (score < ScoreThreshold)
                {
                    Start();
                    reason = $"Vision Learner başlatıldı. Mevcut skor: {score:F1}/100";
                }
                else
                {
                    reason = $"Görsel hedef zaten karşılanmış: {score:F1}/100";
                }
                return true;
            }
            catch (Exception ex)
            {
                reason = $"VisionLearner hata: {ex.Message}";
                return false;
            }
        }
    }
}
#endif

