using System;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

namespace Autopilot
{
    // Batch mode screenshot: Unity -batchmode -executeMethod Autopilot.AutopilotScreenshot.Capture
    // Also called automatically at the end of AutopilotCLI.RunAutopilot().
    public static class AutopilotScreenshot
    {
        private const int Width  = 1920;
        private const int Height = 1080;

#if UNITY_EDITOR
        // Standalone entry point: builds scene then captures.
        public static void Capture()
        {
            try
            {
                UnityAutopilotTasks.BuildDefaultScene();
                string path = GetOutputPath();
                RenderToFile(path);
                AutopilotLogger.Log($"Screenshot kaydedildi: {path}", "INFO");
                AutopilotLogger.Flush();
            }
            catch (Exception ex)
            {
                AutopilotLogger.Log("Screenshot hatasi: " + ex, "ERROR");
            }
            finally
            {
                EditorApplication.Exit(0);
            }
        }
#endif

        // Called from AutopilotCLI after tasks complete — no Exit() here.
        public static void CaptureAfterBuild()
        {
            try
            {
                string path = GetOutputPath();
                RenderToFile(path);
                AutopilotLogger.Log($"[screenshot] Kaydedildi: {path}", "INFO");
            }
            catch (Exception ex)
            {
                AutopilotLogger.Log("[screenshot] Hata: " + ex.Message, "WARN");
            }
        }

        public static void RenderToFile(string filePath)
        {
            Camera cam = Camera.main;
            if (cam == null)
                cam = UnityEngine.Object.FindAnyObjectByType<Camera>();
            if (cam == null)
            {
                AutopilotLogger.Log("[screenshot] Kamera bulunamadi — atlanıyor.", "WARN");
                return;
            }

            Directory.CreateDirectory(Path.GetDirectoryName(filePath)!);

            var rt = new RenderTexture(Width, Height, 24, RenderTextureFormat.ARGB32);
            Camera prevCam = cam;
            prevCam.targetTexture = rt;
            prevCam.Render();

            RenderTexture.active = rt;
            var tex = new Texture2D(Width, Height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, Width, Height), 0, 0);
            tex.Apply();

            prevCam.targetTexture = null;
            RenderTexture.active = null;
            UnityEngine.Object.DestroyImmediate(rt);

            File.WriteAllBytes(filePath, tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
        }

        public static string GetOutputPath()
        {
            // dataPath = {RepoRoot}/UnityProject/Assets  →  ../.. = RepoRoot
            string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
            return Path.Combine(repoRoot, "output", "unity", "unity_first_playable_preview.png");
        }
    }
}
