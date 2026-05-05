#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Autopilot
{
    // Reads Assests/Animations/Mixamo/{CharType}/*.fbx
    // and imports them into Assets/Art/Animations/{CharType}/
    // Run via: Tools > Autopilot > Import Mixamo Animations
    public static class MixamoAnimationImporter
    {
        private static readonly string SourceRoot = Path.GetFullPath(
            Path.Combine(Application.dataPath, "..", "..", "Assests", "Animations", "Mixamo"));

        private static readonly string DestRoot = "Assets/Art/Animations";

        [MenuItem("Tools/Autopilot/Import Mixamo Animations")]
        public static void ImportAll()
        {
            if (!Directory.Exists(SourceRoot))
            {
                Debug.LogWarning($"[MixamoImporter] Kaynak klasör bulunamadı: {SourceRoot}\n" +
                                 "Önce mixamo_downloader.py çalıştırın.");
                return;
            }

            EnsureFolder(DestRoot);

            int total = 0, imported = 0;

            foreach (string charDir in Directory.GetDirectories(SourceRoot))
            {
                string charType = Path.GetFileName(charDir);
                string destDir  = $"{DestRoot}/{charType}";
                EnsureFolder(destDir);

                foreach (string fbxPath in Directory.GetFiles(charDir, "*.fbx"))
                {
                    total++;
                    string fileName   = Path.GetFileName(fbxPath);
                    string destAsset  = $"{destDir}/{fileName}";
                    string destAbs    = Path.Combine(Application.dataPath,
                        "..", destAsset.Replace('/', Path.DirectorySeparatorChar));

                    File.Copy(fbxPath, destAbs, overwrite: false);
                    imported++;
                }
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            // Configure each FBX: Humanoid rig, import animations, no mesh
            int configured = 0;
            foreach (string charDir in Directory.GetDirectories(SourceRoot))
            {
                string charType = Path.GetFileName(charDir);
                string destDir  = $"{DestRoot}/{charType}";

                foreach (string fbxPath in Directory.GetFiles(charDir, "*.fbx"))
                {
                    string assetPath = $"{destDir}/{Path.GetFileName(fbxPath)}";
                    var importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
                    if (importer == null) continue;

                    importer.animationType      = ModelImporterAnimationType.Human;
                    importer.avatarSetup        = ModelImporterAvatarSetup.CopyFromOther;
                    importer.importAnimation    = true;
                    importer.materialImportMode = ModelImporterMaterialImportMode.None;
                    importer.globalScale        = 1f;

                    // Clean up clip name (Mixamo prefix)
                    var clips = importer.clipAnimations;
                    if (clips != null && clips.Length > 0)
                    {
                        foreach (var clip in clips)
                            clip.name = SanitizeClipName(clip.name);
                        importer.clipAnimations = clips;
                    }

                    importer.SaveAndReimport();
                    configured++;
                }
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            Debug.Log($"[MixamoImporter] Tamamlandı: {imported}/{total} FBX kopyalandı, " +
                      $"{configured} configure edildi.\nHedef: {DestRoot}");

            // Write AnimatorController stubs for each character type
            BuildAnimatorControllers();
        }

        // ── Animator Controllers ──────────────────────────────────────────────

        [MenuItem("Tools/Autopilot/Build Mixamo Animator Controllers")]
        public static void BuildAnimatorControllers()
        {
            EnsureFolder("Assets/Art/Animations/Controllers");

            var charTypes = new[] { "Female_Hero", "Archer", "Mage", "Shaman" };
            foreach (string charType in charTypes)
            {
                string controllerPath = $"Assets/Art/Animations/Controllers/AC_{charType}.controller";
                if (AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(controllerPath) != null)
                    continue;

                var controller = UnityEditor.Animations.AnimatorController.CreateAnimatorControllerAtPath(controllerPath);
                var root = controller.layers[0].stateMachine;

                // Add parameters
                controller.AddParameter("Speed",       AnimatorControllerParameterType.Float);
                controller.AddParameter("IsSprinting", AnimatorControllerParameterType.Bool);
                controller.AddParameter("IsGrounded",  AnimatorControllerParameterType.Bool);
                controller.AddParameter("Attack",      AnimatorControllerParameterType.Trigger);
                controller.AddParameter("Die",         AnimatorControllerParameterType.Trigger);
                controller.AddParameter("Hit",         AnimatorControllerParameterType.Trigger);
                controller.AddParameter("Roll",        AnimatorControllerParameterType.Trigger);

                // Map clip names to states
                var clipMap = GetClipMapForType(charType);
                string destDir = $"Assets/Art/Animations/{charType}";

                var stateMap = new Dictionary<string, UnityEditor.Animations.AnimatorState>();

                foreach (var (stateName, clipHint) in clipMap)
                {
                    var clip = FindClip(destDir, clipHint);
                    var state = root.AddState(stateName);
                    if (clip != null) state.motion = clip;
                    stateMap[stateName] = state;
                }

                // Basic transitions: Idle <-> Walk/Run by Speed
                WireSpeedTransitions(controller, root, stateMap);

                AssetDatabase.SaveAssets();
                Debug.Log($"[MixamoImporter] AnimatorController: {controllerPath}");
            }
        }

        // ── Helpers ───────────────────────────────────────────────────────────

        private static List<(string state, string clipHint)> GetClipMapForType(string charType)
        {
            return charType switch
            {
                "Female_Hero" => new List<(string, string)>
                {
                    ("Idle",        "Sword_And_Shield_Idle"),
                    ("Walk",        "Sword_And_Shield_Walk"),
                    ("Run",         "Sword_And_Shield_Run"),
                    ("Attack1",     "Sword_And_Shield_Slash"),
                    ("Attack2",     "Sword_And_Shield_Thrust"),
                    ("Jump",        "Sword_And_Shield_Jump"),
                    ("Roll",        "Standing_Dive_Roll"),
                    ("Block",       "Block"),
                    ("Hit",         "Getting_Hit"),
                    ("Die",         "Falling_Back_Death"),
                },
                "Archer" => new List<(string, string)>
                {
                    ("Idle",        "Arrow_Aim_Idle"),
                    ("Walk",        "Arrow_Aim_Walk"),
                    ("Run",         "Run_Forward"),
                    ("Attack1",     "Arrow_Shoot"),
                    ("Attack2",     "Arrow_Shoot_Roll"),
                    ("CrouchIdle",  "Crouching_Idle"),
                    ("CrouchWalk",  "Crouching_Walk"),
                    ("Hit",         "Getting_Hit"),
                    ("Die",         "Falling_Back_Death"),
                },
                "Mage" => new List<(string, string)>
                {
                    ("Idle",        "Spellcasting_Idle"),
                    ("Walk",        "Walking"),
                    ("Run",         "Running"),
                    ("Attack1",     "Magic_Attack_01"),
                    ("Attack2",     "Magic_Attack_02"),
                    ("Cast",        "Casting"),
                    ("Levitate",    "Levitate"),
                    ("Hit",         "Getting_Hit"),
                    ("Die",         "Falling_Back_Death"),
                },
                "Shaman" => new List<(string, string)>
                {
                    ("Idle",        "Idle"),
                    ("Walk",        "Walking"),
                    ("Run",         "Running"),
                    ("Dance",       "Tribal_Dance"),
                    ("Summon",      "Summoning"),
                    ("Attack1",     "Magic_Attack_01"),
                    ("WarCry",      "War_Cry"),
                    ("Hit",         "Getting_Hit"),
                    ("Die",         "Falling_Back_Death"),
                },
                _ => new List<(string, string)>()
            };
        }

        private static AnimationClip FindClip(string dir, string hint)
        {
            if (!AssetDatabase.IsValidFolder(dir)) return null;
            foreach (string guid in AssetDatabase.FindAssets("t:AnimationClip", new[] { dir }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.Contains(hint, System.StringComparison.OrdinalIgnoreCase))
                    return AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
            }
            return null;
        }

        private static void WireSpeedTransitions(
            UnityEditor.Animations.AnimatorController ctrl,
            UnityEditor.Animations.AnimatorStateMachine sm,
            Dictionary<string, UnityEditor.Animations.AnimatorState> states)
        {
            if (!states.TryGetValue("Idle", out var idle)) return;
            sm.defaultState = idle;

            if (states.TryGetValue("Walk", out var walk))
            {
                var t = idle.AddTransition(walk);
                t.AddCondition(UnityEditor.Animations.AnimatorConditionMode.Greater, 0.1f, "Speed");
                t.duration = 0.2f;
                var t2 = walk.AddTransition(idle);
                t2.AddCondition(UnityEditor.Animations.AnimatorConditionMode.Less, 0.1f, "Speed");
                t2.duration = 0.2f;
            }
            if (states.TryGetValue("Walk", out var w) && states.TryGetValue("Run", out var run))
            {
                var t = w.AddTransition(run);
                t.AddCondition(UnityEditor.Animations.AnimatorConditionMode.Greater, 0.6f, "Speed");
                t.AddCondition(UnityEditor.Animations.AnimatorConditionMode.If, 0f, "IsSprinting");
                t.duration = 0.15f;
                var t2 = run.AddTransition(w);
                t2.AddCondition(UnityEditor.Animations.AnimatorConditionMode.IfNot, 0f, "IsSprinting");
                t2.duration = 0.15f;
            }
        }

        private static string SanitizeClipName(string name)
        {
            // Strip "mixamo.com" prefix that Mixamo embeds in clip names
            int pipe = name.IndexOf('|');
            return pipe >= 0 ? name[(pipe + 1)..].Trim() : name.Trim();
        }

        private static void EnsureFolder(string assetPath)
        {
            if (AssetDatabase.IsValidFolder(assetPath)) return;
            string parent = Path.GetDirectoryName(assetPath)!.Replace('\\', '/');
            string leaf   = Path.GetFileName(assetPath);
            if (!AssetDatabase.IsValidFolder(parent)) EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }
    }
}
#endif
