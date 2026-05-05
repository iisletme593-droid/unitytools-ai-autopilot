using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

public static class AutopilotProjectMaintenance
{
    [MenuItem("Tools/Autopilot/Maintenance/Clean Model Import Settings")]
    public static void CleanModelImportSettings()
    {
        string[] roots =
        {
            "Assets/Art/Characters",
            "Assets/FantasyRPG/Models",
            "Assets/Models/Sketchfab"
        };

        int changed = 0;
        foreach (string guid in AssetDatabase.FindAssets("t:Model", roots.Where(AssetDatabase.IsValidFolder).ToArray()))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) continue;

            bool dirty = false;
            if (importer.animationType == ModelImporterAnimationType.Human)
            {
                importer.animationType = ModelImporterAnimationType.Generic;
                dirty = true;
            }
            if (importer.avatarSetup != ModelImporterAvatarSetup.NoAvatar)
            {
                importer.avatarSetup = ModelImporterAvatarSetup.NoAvatar;
                dirty = true;
            }

            if (dirty)
            {
                importer.SaveAndReimport();
                changed++;
            }
        }

        Debug.Log($"[Autopilot] Model import settings cleaned. Changed: {changed}");
    }

    [MenuItem("Tools/Autopilot/Maintenance/Quarantine Broken GLB Imports")]
    public static void QuarantineBrokenGlbImports()
    {
        string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        string logPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Unity", "Editor", "Editor.log");
        if (!File.Exists(logPath))
        {
            Debug.LogWarning("[Autopilot] Editor.log not found; no GLB quarantine performed.");
            return;
        }

        string quarantineRoot = Path.Combine(projectRoot, "AutopilotData", "QuarantinedBrokenImports");
        Directory.CreateDirectory(quarantineRoot);

        int moved = 0;
        foreach (string line in File.ReadLines(logPath))
        {
            int marker = line.IndexOf("Failed to import Assets/", StringComparison.Ordinal);
            if (marker < 0) continue;
            int start = line.IndexOf("Assets/", marker, StringComparison.Ordinal);
            int end = line.IndexOf(".glb", start, StringComparison.OrdinalIgnoreCase);
            if (start < 0 || end < 0) continue;

            string assetPath = line.Substring(start, end - start + 4).Replace('\\', '/');
            string fullPath = Path.Combine(projectRoot, assetPath.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(fullPath)) continue;

            string safeName = assetPath.Replace("Assets/", "").Replace('/', '_').Replace('\\', '_');
            string dst = Path.Combine(quarantineRoot, safeName);
            if (File.Exists(dst)) continue;

            File.Move(fullPath, dst);
            string meta = fullPath + ".meta";
            if (File.Exists(meta)) File.Move(meta, dst + ".meta");
            moved++;
        }

        AssetDatabase.Refresh();
        Debug.Log($"[Autopilot] Quarantined broken GLB imports: {moved}. Folder: {quarantineRoot}");
    }

    [MenuItem("Tools/Autopilot/Maintenance/Clear Console")]
    public static void ClearConsole()
    {
        Assembly assembly = Assembly.GetAssembly(typeof(SceneView));
        Type logEntries = assembly.GetType("UnityEditor.LogEntries");
        MethodInfo clear = logEntries?.GetMethod("Clear", BindingFlags.Static | BindingFlags.Public);
        clear?.Invoke(null, null);
    }

    [MenuItem("Tools/Autopilot/Maintenance/Run Full Console Cleanup")]
    public static void RunFullConsoleCleanup()
    {
        CleanModelImportSettings();
        QuarantineBrokenGlbImports();
        ClearConsole();
        Debug.Log("[Autopilot] Console cleanup finished.");
    }
}
