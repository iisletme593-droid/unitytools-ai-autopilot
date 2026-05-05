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
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  THORNY IVY â€” VISION LEARNER
    //
    //  Ã‡alÄ±ÅŸma prensibi:
    //    1. AutopilotData/reference_images/*.png dosyalarÄ±nÄ± yÃ¼kler
    //    2. Her birinden renk/parlaklÄ±k/sis metrikleri Ã§Ä±karÄ±r â†’ hedef belirler
    //    3. Unity kamerasÄ±ndan screenshot alÄ±r, aynÄ± metrikleri Ã¶lÃ§er
    //    4. FarkÄ± minimize edecek parametre ayarÄ± yapar (hill-climbing)
    //    5. Ã–lÃ§ek doÄŸrulamasÄ± â€” her nesne iÃ§in beklenen metre aralÄ±ÄŸÄ±
    //    6. Hedef skora (â‰¥78) ulaÅŸana veya 60 iterasyon bitene dek devam eder
    //
    //  MenÃ¼: Tools > Autopilot > â˜… Vision Learner
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    public static class AutopilotVisionLearner
    {
        const float ScoreThreshold   = 78f;
        const int   MaxIterations    = 60;
        const int   SnapW            = 320;
        const int   SnapH            = 180;
        const float StepDecay        = 0.92f; // iterasyon baÅŸÄ±na adÄ±m kÃ¼Ã§Ã¼lme oranÄ±

        static readonly string RefDir = Path.GetFullPath(
            Path.Combine(Application.dataPath, "..", "AutopilotData", "reference_images"));

        // â”€â”€ GÃ¶rsel metrik paketi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        struct VM
        {
            public float Lum;            // ortalama luminans
            public float R, G, B;        // kanal ortalamalarÄ±
            public float WarmFrac;       // turuncu-sÄ±cak piksel oranÄ± (kampfire/fener)
            public float DarkFrac;       // lum<0.35 oranÄ± (gotik karanlÄ±k)
            public float BlueFrac;       // mavi > kÄ±rmÄ±zÄ±*1.2 oranÄ± (sis soÄŸukluÄŸu)
            public float SkyLum;         // Ã¼st 1/3 luminans (gÃ¶kyÃ¼zÃ¼/sis)
            public float MidLum;         // orta 1/3 luminans (orman/yol)
            public float GroundLum;      // alt 1/3 luminans (zemin)
            public float Saturation;     // ortalama doygunluk
        }

        // VarsayÄ±lan hedef â€” tÃ¼m gÃ¶rseller analiz edilince Ã¼zerine yazÄ±lÄ±r
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

        // Her iterasyon sonrasÄ± kaydedilen en iyi parametre kÃ¼mesi
        static SceneParams _bestParams;

        struct SceneParams
        {
            public float FogDensity;
            public Color FogColor;
            public Color Ambient;
            public float SunIntensity;
        }

        // â”€â”€ MenÃ¼ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        [MenuItem("Tools/Autopilot/â˜… Vision Learner - BaÅŸlat")]
        public static void Start()
        {
            if (_running) { Debug.Log("[VisionLearner] Zaten Ã§alÄ±ÅŸÄ±yor."); return; }
            LoadTarget();
            _running   = true;
            _iter      = 0;
            _bestScore = 0f;
            _prevScore = 0f;
            _step      = 1.0f;
            _log.Clear();
            _log.Add($"Hedef skor â‰¥ {ScoreThreshold}/100. Referans: {RefDir}");
            Debug.Log("[VisionLearner] Ã–ÄŸrenme baÅŸlatÄ±ldÄ±.");
            EditorApplication.delayCall += Tick;
        }

        [MenuItem("Tools/Autopilot/â˜… Vision Learner - Durdur")]
        public static void Stop()
        {
            _running = false;
            SaveScene();
            Debug.Log($"[VisionLearner] Durduruldu. En iyi: {_bestScore:F1}/100  " +
                      $"({_iter} iterasyon)");
            foreach (var l in _log.TakeLast(25)) Debug.Log(l);
        }

        [MenuItem("Tools/Autopilot/â˜… Vision Learner - Tek Analiz")]
        public static void AnalyzeOnce()
        {
            LoadTarget();
            var tex = Snapshot();
            if (tex == null) { Debug.LogWarning("[VisionLearner] Screenshot alÄ±namadÄ±."); return; }
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

        [MenuItem("Tools/Autopilot/â˜… Vision Learner - Ã–lÃ§ek DoÄŸrula")]
        public static void ValidateScalesMenu() => ValidateScales(verbose: true);

        // â”€â”€ Ana Ã¶ÄŸrenme dÃ¶ngÃ¼sÃ¼ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static void Tick()
        {
            if (!_running) return;
            if (_iter >= MaxIterations) { Stop(); return; }

            // Screenshot & Ã¶lÃ§Ã¼m
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
            string arrow = score > _prevScore + 0.2f ? "â†‘" : score < _prevScore - 0.2f ? "â†“" : "â€”";
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
                _log.Add($"âœ“ Hedef aÅŸÄ±ldÄ±: {score:F1}/100 ({_iter} iter)");
                Debug.Log($"[VisionLearner] âœ“ TamamlandÄ±! {score:F1}/100");
                Stop();
                return;
            }

            // KÃ¶tÃ¼ durum â†’ tam yeniden kurulum (8. veya 20. iterasyonda)
            if ((_iter == 8 && score < 22f) || (_iter == 20 && score < 35f))
            {
                Debug.Log($"[VisionLearner] Skor Ã§ok dÃ¼ÅŸÃ¼k ({score:F1}) â€” sahne yeniden kuruluyor.");
                SceneBuilder.BuildScene();
                SceneMaterialPainter.PaintAll();
                IslandTreePainter.PaintAll();
            }

            Adjust(actual, score);
            _step *= StepDecay;
            _iter++;
            EditorApplication.delayCall += Tick;
        }

        // â”€â”€ Parametre ayarÄ± â€” hill-climbing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static void Adjust(VM a, float score)
        {
            float s = _step;

            // 1. PARLAKLK â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            float lumErr = a.Lum - _target.Lum;
            if (lumErr > 0.008f) // Ã§ok parlak
            {
                RenderSettings.ambientLight = ScaleColor(RenderSettings.ambientLight,
                    1f - 0.10f * s * Mathf.Clamp01(lumErr / 0.05f));
                AdjustSun(-0.04f * s);
            }
            else if (lumErr < -0.008f) // Ã§ok karanlÄ±k
            {
                RenderSettings.ambientLight = ScaleColor(RenderSettings.ambientLight,
                    1f + 0.06f * s * Mathf.Clamp01(-lumErr / 0.05f));
                AdjustSun(+0.025f * s);
            }

            // 2. SÄ°S YOÄUNLUÄU â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            // KaranlÄ±k piksel oranÄ± dÃ¼ÅŸÃ¼kse â†’ sis artÄ±r (nesneler daha az gÃ¶rÃ¼nÃ¼r olacak)
            float darkErr = a.DarkFrac - _target.DarkFrac;
            if (darkErr < -0.05f)
                RenderSettings.fogDensity = Mathf.Clamp(
                    RenderSettings.fogDensity + 0.003f * s, 0.012f, 0.080f);
            else if (darkErr > 0.06f)
                RenderSettings.fogDensity = Mathf.Clamp(
                    RenderSettings.fogDensity - 0.002f * s, 0.012f, 0.080f);

            // 3. SÄ°S RENGÄ° â€” hedef mavi-gri'ye yumuÅŸak yakÄ±nsama â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            Color fogTarget = new Color(0.28f, 0.30f, 0.38f);
            RenderSettings.fogColor = Color.Lerp(
                RenderSettings.fogColor, fogTarget, 0.08f * s);

            // 4. SICAK AKSAN (kampfire/fener) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            float warmErr = a.WarmFrac - _target.WarmFrac;
            if (warmErr < -0.02f)      // yetersiz sÄ±cak Ä±ÅŸÄ±k
                AdjustWarmLights(+0.6f * s, +2f * s);
            else if (warmErr > 0.03f)  // fazla sÄ±cak
                AdjustWarmLights(-0.3f * s, 0f);

            // 5. MOR/KALE IÅIK â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            // Sis Ã§ok soÄŸuk deÄŸilse kale bÃ¼yÃ¼sel Ä±ÅŸÄ±nÄ±nÄ± koru
            if (a.BlueFrac < _target.BlueFrac * 0.80f)
            {
                AdjustMagicLights(+0.4f * s);
                Color fc = RenderSettings.fogColor;
                RenderSettings.fogColor = new Color(fc.r, fc.g,
                    Mathf.Clamp(fc.b + 0.008f * s, 0f, 0.6f));
            }

            // 6. AMBÄ°ENT RENK â€” hedef: koyu mavi-gri â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            Color ambTarget = new Color(0.022f, 0.028f, 0.052f);
            RenderSettings.ambientLight = Color.Lerp(
                RenderSettings.ambientLight, ambTarget, 0.05f * s);

            // 7. Ã–LÃ‡EK DOÄRULAMA (her 8 iterasyonda) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if (_iter % 8 == 0) ValidateScales(verbose: false);

            // 8. MATERYAL YENÄ°DEN BOYAMA (her 18 iterasyonda, dÃ¼ÅŸÃ¼k skor) â”€â”€â”€â”€â”€
            if (_iter % 18 == 9 && score < 55f)
            {
                SceneMaterialPainter.RunAsTask(out _);
                IslandTreePainter.RunAsTask(out _);
            }

            SaveScene();
        }

        // â”€â”€ Referans gÃ¶rsellerden hedef metrikleri hesapla â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static void LoadTarget()
        {
            if (_targetReady) return;

            if (!Directory.Exists(RefDir))
            {
                Debug.LogWarning($"[VisionLearner] Referans klasÃ¶r yok: {RefDir}  VarsayÄ±lan hedef kullanÄ±lÄ±yor.");
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
            Debug.Log($"[VisionLearner] {n} gÃ¶rsel analiz edildi.\n" +
                      $"  Hedef: Lum={_target.Lum:F3}  Warm={_target.WarmFrac:F3}  " +
                      $"Dark={_target.DarkFrac:F3}  Sis={_target.SkyLum:F3}");
        }

        // â”€â”€ Screenshot (HDRP dahil) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                Debug.LogWarning($"[VisionLearner] Screenshot hatasÄ±: {ex.Message}");
                return null;
            }
        }

        // â”€â”€ Piksel analizi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

                // SÄ±cak turuncu tespiti (kampfire / fener)
                if (p.r > 0.38f && p.g > 0.12f && p.b < 0.14f &&
                    p.r > p.g * 1.4f && p.r > p.b * 2.2f) warm++;

                // KaranlÄ±k piksel
                if (lum < 0.35f) dark++;

                // SoÄŸuk mavi piksel (sis / atmosfer)
                if (p.b > p.r * 1.22f && p.b > 0.20f) blue++;

                // Dikey bÃ¶lge
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

        // â”€â”€ Ã‡ok metrikli skor (0â€“100) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static float Score(VM a)
        {
            float s = 100f;
            s -= Mathf.Abs(a.Lum      - _target.Lum)      * 240f; // aÄŸÄ±rlÄ±k 24
            s -= Mathf.Abs(a.WarmFrac - _target.WarmFrac)  * 220f; // aÄŸÄ±rlÄ±k 22 â€” kampfire kritik
            s -= Mathf.Abs(a.DarkFrac - _target.DarkFrac)  * 140f; // aÄŸÄ±rlÄ±k 14
            s -= Mathf.Abs(a.SkyLum   - _target.SkyLum)    * 100f; // aÄŸÄ±rlÄ±k 10
            s -= Mathf.Abs(a.GroundLum- _target.GroundLum) * 100f; // aÄŸÄ±rlÄ±k 10
            s -= Mathf.Abs(a.R        - _target.R)          * 70f;
            s -= Mathf.Abs(a.G        - _target.G)          * 70f;
            s -= Mathf.Abs(a.B        - _target.B)          * 70f;
            s -= Mathf.Abs(a.BlueFrac - _target.BlueFrac)   * 60f;
            s -= Mathf.Abs(a.Saturation-_target.Saturation) * 60f;
            return Mathf.Clamp(s, 0f, 100f);
        }

        // â”€â”€ IÅŸÄ±k yardÄ±mcÄ±larÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                if (l.color.r > 0.55f && l.color.b < 0.25f) // sÄ±cak ton filtresi
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
                // Mor/mavi ton â€” kale sihirli Ä±ÅŸÄ±n
                if (l.color.b > l.color.r * 1.1f && l.color.r > 0.20f)
                    l.intensity = Mathf.Clamp(l.intensity + intDelta, 0.5f, 14f);
            }
        }

        // â”€â”€ Ã–lÃ§ek doÄŸrulamasÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        // Her nesne tipi iÃ§in beklenen yÃ¼kseklik aralÄ±ÄŸÄ± (metre, world scale)
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

                    // Bounding box yÃ¼ksekliÄŸi kullan
                    var renderers = go.GetComponentsInChildren<MeshRenderer>(true);
                    if (renderers.Length == 0) break;

                    Bounds b = renderers[0].bounds;
                    foreach (var r in renderers.Skip(1)) b.Encapsulate(r.bounds);
                    float h = b.size.y;
                    if (h < 0.001f) break;

                    if (h < minM)
                    {
                        go.transform.localScale *= (minM / h);
                        if (verbose) Debug.Log($"[ScaleValidator] â†‘ {go.name} {h:F2}mâ†’{minM:F2}m");
                        fixed_++;
                    }
                    else if (h > maxM)
                    {
                        go.transform.localScale *= (maxM / h);
                        if (verbose) Debug.Log($"[ScaleValidator] â†“ {go.name} {h:F2}mâ†’{maxM:F2}m");
                        fixed_++;
                    }
                    else ok++;
                    break;
                }
            }

            if (fixed_ > 0 || verbose)
                Debug.Log($"[ScaleValidator] {fixed_} dÃ¼zeltildi, {ok} uygun.");
        }

        // â”€â”€ YardÄ±mcÄ±lar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        // â”€â”€ Autopilot Brain entegrasyonu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                    reason = $"Vision Learner baÅŸlatÄ±ldÄ±. Mevcut skor: {score:F1}/100";
                }
                else
                {
                    reason = $"GÃ¶rsel hedef zaten karÅŸÄ±lanmÄ±ÅŸ: {score:F1}/100";
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

