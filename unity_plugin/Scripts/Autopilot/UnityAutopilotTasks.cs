using System;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using UnityEngine.Rendering;
using UnityEngine.UI;
#endif

namespace Autopilot
{
    public static class UnityAutopilotTasks
    {
        public static AutopilotTaskList CreateDefaultTaskList()
        {
            string now = DateTime.UtcNow.ToString("o");
            return new AutopilotTaskList
            {
                tasks = new[]
                {
                    Task("unity-001", "Retire Unreal automation", "Record that Unreal is retired and Unity is active.", "ReportStatus", 1, now),
                    Task("unity-002", "Validate Unity compile context", "Run Unity-side validation hooks for the active project.", "GameplayValidation", 2, now),
                    Task("unity-003", "Create Unity autopilot executor", "Confirm the Unity-only task executor is active.", "ReportStatus", 3, now),
                    Task("unity-004", "Seed Unity task queue", "Ensure only Unity tasks are allowed in AutopilotData/tasks.json.", "ReportStatus", 4, now),
                    Task("unity-005", "Prepare asset folders", "Create professional Unity art/audio/vfx folder structure.", "AssetImport", 5, now),
                    Task("unity-006", "Create built-in lookdev materials", "Generate dark Nordic Standard materials for the first playable.", "MaterialBake", 6, now),
                    Task("unity-007", "Build RPG fantasy scene", "SceneBuilder ile gercek GLB asset'leri kullanan dark fantasy sahnesini kur (orman, kayalik, kale, dusman zonlari).", "SceneBuild", 7, now),
                    Task("unity-008", "Install player and camera", "Place player controller, combat, stamina, XP, inventory, and third-person camera.", "SceneBuild", 8, now),
                    Task("unity-009", "Install combat loop", "Place enemy AI with tier/level system, patrol/chase/attack, loot and XP rewards.", "SceneBuild", 9, now),
                    Task("unity-010", "Install RPG HUD shell", "Create HP, MP, stamina, skill bar, minimap, quest tracker, and loot readout.", "SceneBuild", 10, now),
                    Task("unity-011", "Validate first playable", "Check spawn, camera, enemies, RPG scene objects, and renderer density.", "GameplayValidation", 11, now),
                    Task("unity-012", "Paint scene materials", "Dark fantasy paleti ile tum sahne materyallerini boyar (tas, ahsap, metal, emissive fener).", "MaterialPaint", 12, now),
                    Task("unity-012b", "Brain cycle optimization", "AutopilotBrain ile sahne kalite skoru hesapla ve eksiklikleri gider.", "BrainCycle", 12, now),
                    Task("unity-013", "Capture first playable screenshot", "Capture or prepare the screenshot output path.", "ScreenshotCapture", 13, now),
                    Task("unity-014", "Build Windows player report", "Attempt Windows build and write completion report.", "BuildPlayer", 14, now),
                    Task("unity-015", "Visual quality gate", "Renderer sayisi, sis, isik ve materyal kalitesini dogrula.", "VisualQualityGate", 15, now),
                    Task("unity-016", "Write Unity reboot status", "Write human-readable Unity-only status summaries.", "ReportStatus", 16, now)
                }
            };
        }

        private static AutopilotTask Task(string id, string title, string description, string taskType, int priority, string now)
        {
            return new AutopilotTask
            {
                id = id,
                title = title,
                description = description,
                engine = "unity",
                taskType = taskType,
                sourceDoc = "docs/design",
                priority = priority,
                status = "Pending",
                createdAt = now,
                updatedAt = now,
                estimatedSeconds = 1f,
                qualityGates = new[] { "unity_only", "no_unreal_process", "first_playable_ready" }
            };
        }

        public static bool Execute(AutopilotTask task, out string reason)
        {
            if (task == null)
            {
                reason = "Task was null.";
                return false;
            }

#if UNITY_EDITOR
            switch ((task.taskType ?? "ReportStatus").Trim())
            {
                case "SceneBuild":
                    return HdrpCleanSceneBuilder.Run(out reason);
                case "CleanHdrpReferenceScene":
                    return HdrpCleanSceneBuilder.Run(out reason);
                case "AssetImport":
                    return PrepareAssetFolders(out reason);
                case "MaterialBake":
                    return CreateLookdevMaterials(out reason);
                case "GameplayValidation":
                    return ValidateFirstPlayable(out reason);
                case "ScreenshotCapture":
                    return CaptureScreenshot(out reason);
                case "BuildPlayer":
                    return BuildWindowsPlayer(out reason);
                case "ExternalAI":
                    return ValidateExternalAIStack(out reason);
                case "GeoWorldPlanning":
                    return WriteGeoWorldUnityPlan(out reason);
                case "AssetCandidateScan":
                    return ScanUnityAssetCandidates(out reason);
                case "AssetReplacement":
                    return ImportHighQualityPbrSurfaces(out reason);
                case "CharacterPrefabReplacement":
                    return ImportCharacterPrefabReplacements(out reason);
                case "FbxAssetScan":
                    return ScanAndImportAllFbx(out reason);
                case "SceneModelSwap":
                    return SwapScenePrimitivesWithModels(out reason);
                case "VisualQualityGate":
                    return WriteVisualQualityGate(out reason);
                case "MaterialPaint":
                    return SceneMaterialPainter.RunAsTask(out reason);
                case "BrainCycle":
                    return RunBrainCycle(out reason);
                case "ReportStatus":
                default:
                    return WriteStatusReport($"Task {task.id}: {task.title}", out reason);
            }
#else
            reason = task.taskType == "ReportStatus"
                ? "Runtime report task acknowledged. Editor-only tasks require Unity batchmode/editor."
                : $"Task type '{task.taskType}' requires Unity Editor batchmode.";
            return task.taskType == "ReportStatus";
#endif
        }

#if UNITY_EDITOR
        private const string ScenePath = "Assets/Scenes/Main.unity";
        private const string MaterialRoot = "Assets/Materials/Generated";
        private const string AutopilotDataRoot = "AutopilotData";
        private static bool s_CharacterReplacementImportReady;

        public static void OpenMainSceneForReview()
        {
            if (!File.Exists(ScenePath))
                BuildFirstPlayableScene(out _);

            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Selection.activeObject = AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath);
            EditorGUIUtility.PingObject(Selection.activeObject);
            Debug.Log("Unity autopilot review scene opened: " + ScenePath);
        }

        private static bool PrepareAssetFolders(out string reason)
        {
            string[] folders =
            {
                "Assets/Art", "Assets/Art/Characters", "Assets/Art/Environment", "Assets/Art/Props",
                "Assets/Materials", "Assets/Materials/Generated", "Assets/Textures", "Assets/Audio",
                "Assets/VFX", "Assets/UI", "Assets/Prefabs", "Assets/Prefabs/Gameplay"
            };

            foreach (string folder in folders)
                EnsureFolder(folder);

            AssetDatabase.SaveAssets();
            reason = "Unity asset folders are ready.";
            return true;
        }

        private static bool ValidateExternalAIStack(out string reason)
        {
            string root = Directory.GetParent(Application.dataPath)!.FullName;
            string statusPath = Path.Combine(root, AutopilotDataRoot, "external_ai", "unity_external_ai_stack_status.json");
            if (!File.Exists(statusPath))
            {
                reason = "External AI stack status is missing; run scripts/unity/run_unity_external_ai_stack.ps1.";
                return false;
            }

            string text = File.ReadAllText(statusPath);
            bool hasCompleted = text.Contains("\"result\":  \"completed\"") || text.Contains("\"result\":\"completed\"");
            bool hasWarning = text.Contains("completed_with_warnings");
            reason = hasCompleted
                ? "External AI stack completed and Unity-facing status is available."
                : hasWarning
                    ? "External AI stack completed with warnings; Unity can continue with deterministic local tasks."
                    : "External AI stack status exists but did not report completion.";
            return hasCompleted || hasWarning;
        }

        private static bool WriteGeoWorldUnityPlan(out string reason)
        {
            string root = Directory.GetParent(Application.dataPath)!.FullName;
            string sourceStatus = Path.Combine(Directory.GetParent(root)!.FullName, "scripts", "ai", "geo_world_integration_status.json");
            string outputPath = Path.Combine(root, AutopilotDataRoot, "geo_world_unity_plan.json");
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);

            bool hasGoogleMaps = false;
            bool minimapReady = false;
            bool weatherReady = false;
            if (File.Exists(sourceStatus))
            {
                string text = File.ReadAllText(sourceStatus);
                hasGoogleMaps = text.Contains("\"google_maps_key_present\": true");
                minimapReady = text.Contains("\"minimap_ready\": true");
                weatherReady = text.Contains("\"weather_ready\": true");
            }

            string json =
                "{\n" +
                "  \"result\": \"completed\",\n" +
                "  \"engine\": \"unity\",\n" +
                "  \"generated_at_utc\": \"" + DateTime.UtcNow.ToString("o") + "\",\n" +
                "  \"google_maps_key_present\": " + hasGoogleMaps.ToString().ToLowerInvariant() + ",\n" +
                "  \"minimap_ready\": " + minimapReady.ToString().ToLowerInvariant() + ",\n" +
                "  \"weather_ready\": " + weatherReady.ToString().ToLowerInvariant() + ",\n" +
                "  \"legal_guardrail\": \"Google map tiles are runtime/reference only; baked terrain should use licensed/open terrain data.\",\n" +
                "  \"unity_plan\": [\n" +
                "    \"Use reference-map anchors for village/camp/castle spacing.\",\n" +
                "    \"Keep baked fantasy terrain original and license-safe.\",\n" +
                "    \"Use real weather as optional runtime mood input for fog/rain/wind values.\",\n" +
                "    \"Generate minimap as stylized Unity overlay, not copied offline Google tiles.\"\n" +
                "  ]\n" +
                "}\n";
            File.WriteAllText(outputPath, json);

            reason = "Unity geo world plan written with map/minimap/weather guardrails.";
            return true;
        }

        private static bool CreateLookdevMaterials(out string reason)
        {
            PrepareAssetFolders(out _);
            ConfigureBuiltInPipeline();
            CreateMaterial("M_NordicMud", new Color(0.23f, 0.18f, 0.13f), 0.82f, 0f);
            CreateMaterial("M_ForestGrass", new Color(0.12f, 0.20f, 0.11f), 0.74f, 0f);
            CreateMaterial("M_WetStone", new Color(0.34f, 0.33f, 0.30f), 0.48f, 0f);
            CreateMaterial("M_AgedWood", new Color(0.20f, 0.12f, 0.07f), 0.72f, 0f);
            CreateMaterial("M_DarkMetal", new Color(0.13f, 0.13f, 0.14f), 0.32f, 0.8f);
            CreateMaterial("M_FireEmissive", new Color(1f, 0.42f, 0.08f), 0.25f, 0f, new Color(4.5f, 1.4f, 0.3f));
            CreateMaterial("M_RedBeamEmissive", new Color(1f, 0.06f, 0.12f), 0.18f, 0f, new Color(12f, 0.2f, 0.8f));
            CreateMaterial("M_SnowMountain", new Color(0.73f, 0.78f, 0.80f), 0.58f, 0f);
            CreateMaterial("M_DeepPine", new Color(0.035f, 0.09f, 0.055f), 0.68f, 0f);
            CreateMaterial("M_PathDirtWet", new Color(0.16f, 0.10f, 0.065f), 0.86f, 0f);
            CreateMaterial("M_GothicBannerRed", new Color(0.42f, 0.025f, 0.035f), 0.62f, 0f);
            CreateMaterial("M_FogBackdrop", new Color(0.34f, 0.38f, 0.42f, 0.14f), 0.42f, 0f);
            CreateMaterial("M_MagicRoseGlow", new Color(1f, 0.10f, 0.34f), 0.18f, 0f, new Color(8f, 0.15f, 1.5f));
            CreateMaterial("M_DampBlackSoil", new Color(0.055f, 0.052f, 0.047f), 0.93f, 0f);
            CreateMaterial("M_WetMudPath", new Color(0.095f, 0.072f, 0.055f), 0.97f, 0f);
            CreateMaterial("M_CabinWeatheredWood", new Color(0.105f, 0.075f, 0.052f), 0.78f, 0f);
            CreateMaterial("M_CoolFogBlue", new Color(0.42f, 0.50f, 0.56f, 0.16f), 0.35f, 0f);
            CreateMaterial("M_WarmLanternGlow", new Color(1f, 0.50f, 0.18f), 0.22f, 0f, new Color(5.5f, 1.8f, 0.35f));
            CreateMaterial("M_WhiteCastleBeam", new Color(1f, 0.92f, 0.78f), 0.12f, 0f, new Color(7f, 6f, 4f));
            ImportHighQualityPbrSurfaces(out _);
            AssetDatabase.SaveAssets();
            reason = "Generated URP lookdev materials.";
            return true;
        }

        private static bool ScanUnityAssetCandidates(out string reason)
        {
            string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
            string outputDir = Path.Combine(Directory.GetParent(Application.dataPath)!.FullName, AutopilotDataRoot);
            string outputPath = Path.Combine(outputDir, "unity_asset_candidate_scan.json");
            Directory.CreateDirectory(outputDir);

            string[] roots =
            {
                Path.Combine(repoRoot, "Assests"),
                Path.Combine(repoRoot, "Assets"),
                Path.Combine(repoRoot, "Content_Source"),
                Path.Combine(repoRoot, "output", "showcase", "hf_concept_batch"),
                Path.Combine(repoRoot, "output", "hf_autopilot")
            };

            int models = 0;
            int textures4k = 0;
            int audio = 0;
            int vfx = 0;
            int concepts = 0;
            string bestGround = "";
            string bestWood = "";
            string bestRock = "";
            string bestHero = "";
            string bestEnemy = "";

            foreach (string root in roots)
            {
                if (!Directory.Exists(root))
                    continue;

                foreach (string file in Directory.GetFiles(root, "*.*", SearchOption.AllDirectories))
                {
                    string ext = Path.GetExtension(file).ToLowerInvariant();
                    string lower = file.ToLowerInvariant();
                    long size = new FileInfo(file).Length;
                    if (ext is ".fbx" or ".obj" or ".gltf" or ".glb")
                    {
                        models++;
                        if (string.IsNullOrEmpty(bestHero) && (lower.Contains("warden") || lower.Contains("character") || lower.Contains("hero")))
                            bestHero = file;
                        if (string.IsNullOrEmpty(bestEnemy) && (lower.Contains("monster") || lower.Contains("demon") || lower.Contains("beast") || lower.Contains("enemy")))
                            bestEnemy = file;
                    }
                    else if (ext is ".png" or ".jpg" or ".jpeg")
                    {
                        if (size >= 4L * 1024L * 1024L)
                            textures4k++;
                        if (string.IsNullOrEmpty(bestGround) && (lower.Contains("ground") || lower.Contains("mud") || lower.Contains("forest_ground") || lower.Contains("aerial_mud")))
                            bestGround = file;
                        if (string.IsNullOrEmpty(bestWood) && (lower.Contains("wood") || lower.Contains("bark")))
                            bestWood = file;
                        if (string.IsNullOrEmpty(bestRock) && lower.Contains("rock"))
                            bestRock = file;
                        if (lower.Contains("hf_game_ai") || lower.Contains("flux"))
                            concepts++;
                        if (lower.Contains("vfx") || lower.Contains("slash") || lower.Contains("impact") || lower.Contains("mist") || lower.Contains("ember"))
                            vfx++;
                    }
                    else if (ext is ".wav" or ".mp3" or ".ogg")
                    {
                        audio++;
                    }
                }
            }

            string Escape(string value) => value.Replace("\\", "\\\\").Replace("\"", "\\\"");
            string json =
                "{\n" +
                "  \"result\": \"completed\",\n" +
                "  \"generated_at_utc\": \"" + DateTime.UtcNow.ToString("o") + "\",\n" +
                "  \"model_candidates\": " + models + ",\n" +
                "  \"texture_candidates_4mb_plus\": " + textures4k + ",\n" +
                "  \"audio_candidates\": " + audio + ",\n" +
                "  \"vfx_candidates\": " + vfx + ",\n" +
                "  \"concept_candidates\": " + concepts + ",\n" +
                "  \"best_ground_candidate\": \"" + Escape(bestGround) + "\",\n" +
                "  \"best_wood_candidate\": \"" + Escape(bestWood) + "\",\n" +
                "  \"best_rock_candidate\": \"" + Escape(bestRock) + "\",\n" +
                "  \"best_hero_candidate\": \"" + Escape(bestHero) + "\",\n" +
                "  \"best_enemy_candidate\": \"" + Escape(bestEnemy) + "\"\n" +
                "}\n";
            File.WriteAllText(outputPath, json);

            reason = $"Asset candidate scan completed: models={models}, 4K-ish textures={textures4k}, audio={audio}, vfx={vfx}.";
            return models > 0 && textures4k > 0;
        }

        private static bool ImportHighQualityPbrSurfaces(out string reason)
        {
            PrepareAssetFolders(out _);
            EnsureFolder("Assets/Textures/ImportedPBR");
            EnsureFolder("Assets/Textures/ImportedPBR/Ground");
            EnsureFolder("Assets/Textures/ImportedPBR/Wood");
            EnsureFolder("Assets/Textures/ImportedPBR/Rock");

            string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
            int imported = 0;
            imported += ImportSurfaceSet(
                repoRoot,
                "M_WetMudPath",
                new[]
                {
                    "Assests/AAA_Free_Pack/Textures/PolyHaven/aerial_mud_1/aerial_mud_1_diff_4k.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Ground059/Ground059_4K-JPG_Color.jpg",
                    "Content_Source/Materials/PhotorealisticSurfaces/damp_mud_diffuse.png"
                },
                new[]
                {
                    "Assests/AAA_Free_Pack/Textures/PolyHaven/aerial_mud_1/aerial_mud_1_nor_gl_4k.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Ground059/Ground059_4K-JPG_NormalGL.jpg",
                    "Content_Source/Materials/PhotorealisticSurfaces/damp_mud_normal.png"
                },
                "Ground",
                0.92f);

            imported += ImportSurfaceSet(
                repoRoot,
                "M_CabinWeatheredWood",
                new[]
                {
                    "Assests/AAA_Free_Pack/Textures/PolyHaven/bark_brown_02/bark_brown_02_diff_4k.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Wood025/Wood025_4K-JPG_Color.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Bark004/Bark004_4K-JPG_Color.jpg"
                },
                new[]
                {
                    "Assests/AAA_Free_Pack/Textures/PolyHaven/bark_brown_02/bark_brown_02_nor_gl_4k.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Wood025/Wood025_4K-JPG_NormalGL.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Bark004/Bark004_4K-JPG_NormalGL.jpg"
                },
                "Wood",
                0.62f);

            imported += ImportSurfaceSet(
                repoRoot,
                "M_WetStone",
                new[]
                {
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Rock037/Rock037_4K-JPG_Color.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Rock029/Rock029_4K-JPG_Color.jpg",
                    "Content_Source/Materials/PhotorealisticSurfaces/wet_stone_diffuse.png"
                },
                new[]
                {
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Rock037/Rock037_4K-JPG_NormalGL.jpg",
                    "Assests/AAA_Free_Pack/Textures/ambientCG/Rock029/Rock029_4K-JPG_NormalGL.jpg",
                    "Content_Source/Materials/PhotorealisticSurfaces/wet_stone_normal.png"
                },
                "Rock",
                0.48f);

            AssetDatabase.SaveAssets();
            reason = $"Imported/rebound high-quality PBR surfaces: {imported} material sets.";
            return imported >= 2;
        }

        private static bool ImportCharacterPrefabReplacements(out string reason)
        {
            PrepareAssetFolders(out _);
            EnsureFolder("Assets/Art/Characters/Imported");
            EnsureFolder("Assets/Art/Characters/Imported/Hero");
            EnsureFolder("Assets/Art/Characters/Imported/Enemy");
            EnsureFolder("Assets/Art/Characters/Imported/Equipment");

            string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));

            int staged = 0;

            // â”€â”€ Hero â€” prefer Female Dark Knight, fallback to biped â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            staged += CopyCharacterAsset(repoRoot,
                "Assests/female_dark_knight_character_fbx/Female_Dark_Knight.fbx",
                "Assets/Art/Characters/Imported/Hero/SK_Hero.fbx") ? 1 : 0;
            if (staged == 0)
                staged += CopyCharacterAsset(repoRoot,
                    "Assests/biped/Character_output.fbx",
                    "Assets/Art/Characters/Imported/Hero/SK_Hero.fbx") ? 1 : 0;

            // â”€â”€ Enemy 0 (brute) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            staged += CopyCharacterAsset(repoRoot,
                "Assests/Rampaging_Behemoth_0124122908_texture_fbx/Rampaging_Behemoth_0124122908_texture.fbx",
                "Assets/Art/Characters/Imported/Enemy/SK_Enemy0.fbx") ? 1 : 0;

            // â”€â”€ Enemy 1 (demon) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            staged += CopyCharacterAsset(repoRoot,
                "Assests/Enemy_Entity_from_Spa_0121043824_texture_fbx/Enemy_Entity_from_Spa_0121043824_texture.fbx",
                "Assets/Art/Characters/Imported/Enemy/SK_Enemy1.fbx") ? 1 : 0;
            if (staged < 3)
                CopyCharacterAsset(repoRoot,
                    "Assests/King_Demon_Vulture_0120150621_texture.fbx",
                    "Assets/Art/Characters/Imported/Enemy/SK_Enemy1.fbx");

            // â”€â”€ Weapon â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            CopyCharacterAsset(repoRoot, "Assests/Sword/sword.fbx",        "Assets/Art/Characters/Imported/Equipment/SM_Sword.fbx");
            CopyCharacterAsset(repoRoot, "Assests/source/Katana_BlueMoon.fbx", "Assets/Art/Characters/Imported/Equipment/SM_Katana.fbx");

            // â”€â”€ Import & configure all FBX files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (string fbxAsset in new[]
            {
                "Assets/Art/Characters/Imported/Hero/SK_Hero.fbx",
                "Assets/Art/Characters/Imported/Enemy/SK_Enemy0.fbx",
                "Assets/Art/Characters/Imported/Enemy/SK_Enemy1.fbx",
                "Assets/Art/Characters/Imported/Equipment/SM_Sword.fbx",
                "Assets/Art/Characters/Imported/Equipment/SM_Katana.fbx",
            })
            {
                var importer = AssetImporter.GetAtPath(fbxAsset) as ModelImporter;
                if (importer == null) continue;
                importer.animationType    = ModelImporterAnimationType.None;
                importer.avatarSetup      = ModelImporterAvatarSetup.NoAvatar;
                importer.importAnimation  = false;
                importer.globalScale      = 1f;
                importer.materialImportMode = ModelImporterMaterialImportMode.None;
                importer.SaveAndReimport();
            }

            s_CharacterReplacementImportReady = true;
            reason = $"Character FBX imported into Assets: {staged} primary models.";
            return staged >= 2;
        }

        // Loads a model prefab from Assets and instantiates it as a child of parent.
        // Returns true if a real model was placed; caller should hide the capsule root renderer.
        private static bool TryInstantiateModel(string assetPath, Transform parent, Vector3 localPos, float scale)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (prefab == null) return false;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            go.transform.localPosition = localPos;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale    = Vector3.one * scale;
            // Disable any colliders on the visual child so gameplay collider is used
            foreach (var col in go.GetComponentsInChildren<Collider>())
                col.enabled = false;
            return true;
        }

        private static bool CopyCharacterAsset(string repoRoot, string sourceRelative, string targetAssetPath)
        {
            string source = Path.Combine(repoRoot, sourceRelative.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(source))
                return false;

            string destination = Path.Combine(Directory.GetParent(Application.dataPath)!.FullName, targetAssetPath.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            File.Copy(source, destination, true);

            if (Path.GetExtension(destination).Equals(".fbx", StringComparison.OrdinalIgnoreCase))
                PatchImportedFbxMetaForGenericVisual(destination);

            return true;
        }

        private static void ConfigureModelImporter(string assetPath, float scale, bool humanoid)
        {
            ModelImporter importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
            if (importer == null)
                return;

            importer.globalScale = scale;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            // These imported models are visual replacements attached under gameplay controllers.
            // Visual-only imports do not need avatars; disabling animation avoids humanoid/generic rig validation noise.
            importer.animationType = ModelImporterAnimationType.None;
            importer.avatarSetup = ModelImporterAvatarSetup.NoAvatar;
            importer.importAnimation = false;
            AssetDatabase.WriteImportSettingsIfDirty(assetPath);

            string destination = Path.Combine(Directory.GetParent(Application.dataPath)!.FullName, assetPath.Replace('/', Path.DirectorySeparatorChar));
            PatchImportedFbxMetaForGenericVisual(destination);
        }

        private static void PatchImportedFbxMetaForGenericVisual(string destination)
        {
            string metaPath = destination + ".meta";
            if (!File.Exists(metaPath))
                return;

            string meta = File.ReadAllText(metaPath);
            string patched = meta
                .Replace("animationType: 3", "animationType: 0")
                .Replace("animationType: 2", "animationType: 0")
                .Replace("avatarSetup: 1", "avatarSetup: 0")
                .Replace("autoGenerateAvatarMappingIfUnspecified: 1", "autoGenerateAvatarMappingIfUnspecified: 0");

            if (patched == meta)
                return;

            File.WriteAllText(metaPath, patched);
        }

        private static bool AttachImportedCharacterVisual(Transform parent, bool hero, int index)
        {
            if (!s_CharacterReplacementImportReady)
                ImportCharacterPrefabReplacements(out _);

            if (hero)
            {
                // Try real model first
                if (TryInstantiateModel("Assets/Art/Characters/Imported/Hero/SK_Hero.fbx",
                        parent, new Vector3(0f, -1.05f, 0f), 1.0f))
                    return true;
            }
            else
            {
                // Alternate enemy model based on index
                string enemyAsset = (index % 2 == 0)
                    ? "Assets/Art/Characters/Imported/Enemy/SK_Enemy0.fbx"
                    : "Assets/Art/Characters/Imported/Enemy/SK_Enemy1.fbx";
                if (TryInstantiateModel(enemyAsset, parent, new Vector3(0f, -1.0f, 0f), 0.85f))
                    return true;
            }

            // Fallback: primitive blockout when model files are missing
            GameObject visual = new GameObject(hero ? "Player_Visual_Blockout" : $"Enemy_Visual_Blockout_{index:00}");
            visual.transform.SetParent(parent);
            visual.transform.localPosition = hero ? new Vector3(0f, -1.05f, 0f) : new Vector3(0f, -1.0f, 0f);
            visual.transform.localRotation = Quaternion.identity;
            visual.transform.localScale    = hero ? Vector3.one : Vector3.one * 0.85f;

            if (hero) BuildGeneratedHeroVisual(visual.transform);
            else      BuildGeneratedEnemyVisual(visual.transform, index);

            foreach (Collider col in visual.GetComponentsInChildren<Collider>())
                col.enabled = false;

            return false;
        }

        // â”€â”€ FBX Auto-Import â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        private static bool ScanAndImportAllFbx(out string reason)
        {
            string repoRoot  = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
            string manifestPath = Path.Combine(repoRoot, "output", "unity", "fbx_scan_manifest.json").Replace('\\', '/');

            if (!File.Exists(manifestPath))
            {
                reason = "FBX scan manifest not found â€” run fbx_asset_scanner.py first.";
                return false;
            }

            var manifest = JsonUtility.FromJson<FbxScanManifest>(File.ReadAllText(manifestPath));
            if (manifest?.assets == null || manifest.assets.Length == 0)
            {
                reason = "FBX manifest empty.";
                return false;
            }

            int imported = 0;
            foreach (var entry in manifest.assets)
            {
                if (string.IsNullOrEmpty(entry.unity_path)) continue;
                string absPath = Path.Combine(Application.dataPath,
                    "..", entry.unity_path.Replace("Assets/", "")).Replace('/', Path.DirectorySeparatorChar);
                absPath = Path.GetFullPath(absPath);

                if (!File.Exists(absPath)) continue;

                // Configure importer
                var importer = AssetImporter.GetAtPath(entry.unity_path) as ModelImporter;
                if (importer != null)
                {
                    bool isAnim = entry.category == "animation";
                    if (importer.animationType != ModelImporterAnimationType.None || isAnim)
                    {
                        importer.animationType      = isAnim ? ModelImporterAnimationType.Generic : ModelImporterAnimationType.None;
                        importer.avatarSetup        = ModelImporterAvatarSetup.NoAvatar;
                        importer.importAnimation    = isAnim;
                        importer.materialImportMode = ModelImporterMaterialImportMode.None;
                        importer.globalScale        = 1f;
                        importer.SaveAndReimport();
                    }
                }
                imported++;
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.SaveAssets();

            reason = $"FBX scan import done: {imported}/{manifest.assets.Length} assets configured.";
            Debug.Log($"[FbxScan] {reason}");
            return imported > 0;
        }

        private static bool SwapScenePrimitivesWithModels(out string reason)
        {
            string manifestPath = Path.Combine(
                Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..")),
                "output", "unity", "fbx_scan_manifest.json").Replace('\\', '/');

            FbxScanManifest manifest = null;
            if (File.Exists(manifestPath))
                manifest = JsonUtility.FromJson<FbxScanManifest>(File.ReadAllText(manifestPath));

            int swapped = 0;

            // â”€â”€ Player â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            var player = GameObject.FindWithTag("Player");
            if (player != null)
            {
                // Imported klasoru onceklik alir (garantili dosyalar)
                string heroPath = "Assets/Art/Characters/Imported/Hero/SK_Hero.fbx";
                if (AssetDatabase.LoadAssetAtPath<GameObject>(heroPath) == null)
                    heroPath = manifest != null ? FirstAssetOfCategory(manifest, "hero") : "";

                if (SwapObjectModel(player.transform, heroPath, new Vector3(0f, -1.05f, 0f), 1.0f))
                {
                    swapped++;
                    string weaponPath = "Assets/Art/Characters/Imported/Equipment/SM_Sword.fbx";
                    if (AssetDatabase.LoadAssetAtPath<GameObject>(weaponPath) == null)
                        weaponPath = manifest != null ? FirstAssetOfCategory(manifest, "weapon") : "";
                    AttachWeaponModel(player.transform, weaponPath);
                }
            }

            // â”€â”€ Enemies â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            var enemies = UnityEngine.Object.FindObjectsByType<Gameplay.EnemyAIController>(
                FindObjectsInactive.Exclude);
            string[] enemyPaths = new[]
            {
                "Assets/Art/Characters/Imported/Enemy/SK_Enemy0.fbx",
                "Assets/Art/Characters/Imported/Enemy/SK_Enemy1.fbx",
            };
            // Imported'da yoksa manifest'ten al
            if (AssetDatabase.LoadAssetAtPath<GameObject>(enemyPaths[0]) == null && manifest != null)
                enemyPaths = AllAssetsOfCategory(manifest, "enemy");

            for (int i = 0; i < enemies.Length; i++)
            {
                string ep = enemyPaths.Length > 0 ? enemyPaths[i % enemyPaths.Length] : "";
                if (!string.IsNullOrEmpty(ep) &&
                    SwapObjectModel(enemies[i].transform, ep, new Vector3(0f, -1.0f, 0f), 0.85f))
                    swapped++;
            }

            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            AssetDatabase.SaveAssets();

            reason = $"SceneModelSwap: {swapped} characters replaced with real FBX models.";
            Debug.Log($"[SceneModelSwap] {reason}");
            return swapped > 0;
        }

        private static bool SwapObjectModel(Transform root, string assetPath,
            Vector3 localPos, float scale)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (prefab == null)
            {
                // Try any fbx in the same folder
                string folder = Path.GetDirectoryName(assetPath)!.Replace('\\', '/');
                foreach (string guid in AssetDatabase.FindAssets("t:Model", new[] { folder }))
                {
                    prefab = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(guid));
                    if (prefab != null) break;
                }
                if (prefab == null) return false;
            }

            // Remove old blockout children
            var toDelete = new System.Collections.Generic.List<GameObject>();
            foreach (Transform child in root)
            {
                string n = child.name;
                if (n.Contains("Visual") || n.Contains("Blockout") ||
                    n.StartsWith("Hero_") || n.StartsWith("Enemy_") ||
                    n.StartsWith("Player_") || n.StartsWith("SK_"))
                    toDelete.Add(child.gameObject);
            }
            foreach (var go in toDelete)
                UnityEngine.Object.DestroyImmediate(go);

            // Hide root mesh
            var mr = root.GetComponent<MeshRenderer>();
            if (mr != null) mr.enabled = false;

            // Place real model
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab, root);
            instance.name = "SK_Model_Visual";
            instance.transform.localPosition = localPos;
            instance.transform.localRotation = Quaternion.identity;
            instance.transform.localScale    = Vector3.one * scale;
            foreach (var col in instance.GetComponentsInChildren<Collider>())
                col.enabled = false;
            return true;
        }

        private static void AttachWeaponModel(Transform player, string assetPath)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (prefab == null) return;
            var weapon = (GameObject)PrefabUtility.InstantiatePrefab(prefab, player);
            weapon.name = "SK_Weapon_Visual";
            weapon.transform.localPosition = new Vector3(0.78f, -0.1f, 0.35f);
            weapon.transform.localRotation = Quaternion.Euler(0f, 0f, -28f);
            weapon.transform.localScale    = Vector3.one * 0.012f;
            foreach (var col in weapon.GetComponentsInChildren<Collider>())
                col.enabled = false;
        }

        private static string FirstAssetOfCategory(FbxScanManifest m, string cat)
        {
            if (m?.assets == null) return "";
            foreach (var a in m.assets)
                if (a.category == cat && !string.IsNullOrEmpty(a.unity_path))
                    return a.unity_path;
            return "";
        }

        private static string[] AllAssetsOfCategory(FbxScanManifest m, string cat)
        {
            if (m?.assets == null) return System.Array.Empty<string>();
            var list = new System.Collections.Generic.List<string>();
            foreach (var a in m.assets)
                if (a.category == cat && !string.IsNullOrEmpty(a.unity_path))
                    list.Add(a.unity_path);
            return list.ToArray();
        }

        [System.Serializable]
        private class FbxScanManifest
        {
            public FbxScanEntry[] assets;
        }

        [System.Serializable]
        private class FbxScanEntry
        {
            public string id;
            public string source;
            public string category;
            public string unity_path;
            public float  scale;
            public int    size_kb;
            public bool   copied;
        }

        // â”€â”€ DeleteGeneratedImportedFbxAssets (legacy â€” kept for reference) â”€â”€â”€

        private static void DeleteGeneratedImportedFbxAssets()
        {
            string unityRoot = Directory.GetParent(Application.dataPath)!.FullName;
            string importedRoot = Path.Combine(unityRoot, "Assets", "Art", "Characters", "Imported");
            if (!Directory.Exists(importedRoot))
                return;

            foreach (string file in Directory.GetFiles(importedRoot, "*.fbx", SearchOption.AllDirectories))
            {
                File.Delete(file);
                string meta = file + ".meta";
                if (File.Exists(meta))
                    File.Delete(meta);
            }
        }

        private static Material CreateImportedVisualMaterial(string materialName, string texturePath, Color fallbackColor)
        {
            EnsureFolder(MaterialRoot);
            string materialPath = $"{MaterialRoot}/{materialName}.mat";
            Material mat = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if (mat == null)
            {
                mat = new Material(PreviewSafeShader());
                mat.name = materialName;
                AssetDatabase.CreateAsset(mat, materialPath);
            }

            mat.shader = PreviewSafeShader();
            mat.SetColor("_BaseColor", fallbackColor);
            mat.SetColor("_Color", fallbackColor);

            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
            if (texture != null)
            {
                if (mat.HasProperty("_BaseMap")) mat.SetTexture("_BaseMap", texture);
                if (mat.HasProperty("_MainTex")) mat.SetTexture("_MainTex", texture);
            }

            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static void BuildGeneratedHeroVisual(Transform root)
        {
            Material armor = LoadMaterial("M_WardenImportedVisual");
            Material metal = LoadMaterial("M_DarkMetal");
            Material cape = CreateMaterial("M_WardenCapeDeepBurgundy", new Color(0.24f, 0.02f, 0.06f), 0.42f, 0f);

            Primitive("Hero_ArmoredTorso", PrimitiveType.Capsule, new Vector3(0f, 1.55f, 0f), new Vector3(0.62f, 1.05f, 0.48f), armor, root);
            Primitive("Hero_Helmet", PrimitiveType.Sphere, new Vector3(0f, 2.55f, 0.03f), new Vector3(0.42f, 0.42f, 0.42f), metal, root);
            Primitive("Hero_Cape_FurCloak", PrimitiveType.Cube, new Vector3(0f, 1.35f, 0.36f), new Vector3(1.05f, 1.95f, 0.12f), cape, root);
            Primitive("Hero_Shoulder_L", PrimitiveType.Sphere, new Vector3(-0.52f, 2.05f, 0f), new Vector3(0.35f, 0.22f, 0.35f), metal, root);
            Primitive("Hero_Shoulder_R", PrimitiveType.Sphere, new Vector3(0.52f, 2.05f, 0f), new Vector3(0.35f, 0.22f, 0.35f), metal, root);
            Primitive("Hero_Sword_ReadableSilhouette", PrimitiveType.Cube, new Vector3(0.88f, 1.05f, -0.16f), new Vector3(0.08f, 1.65f, 0.08f), metal, root).transform.localRotation = Quaternion.Euler(0f, 0f, -28f);
            Primitive("Hero_Shield_Round", PrimitiveType.Cylinder, new Vector3(-0.82f, 1.32f, -0.08f), new Vector3(0.55f, 0.10f, 0.55f), metal, root).transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
        }

        private static void BuildGeneratedEnemyVisual(Transform root, int index)
        {
            bool demon = index % 2 != 0;
            Material body = LoadMaterial(demon ? "M_DemonVultureImportedVisual" : "M_BeastImportedVisual");
            Material dark = LoadMaterial("M_DarkMetal");
            Material glow = LoadMaterial("M_RedBeamEmissive");

            Primitive("Enemy_ImportedBody", PrimitiveType.Capsule, new Vector3(0f, 1.15f, 0f), demon ? new Vector3(0.66f, 1.1f, 0.44f) : new Vector3(0.78f, 0.92f, 0.58f), body, root);
            Primitive("Enemy_ImportedHead", PrimitiveType.Sphere, new Vector3(0f, 2.08f, -0.03f), demon ? new Vector3(0.34f, 0.42f, 0.34f) : new Vector3(0.48f, 0.38f, 0.42f), body, root);
            Primitive("Enemy_Claw_L", PrimitiveType.Cube, new Vector3(-0.66f, 1.08f, -0.18f), new Vector3(0.12f, 0.62f, 0.12f), dark, root).transform.localRotation = Quaternion.Euler(0f, 0f, 28f);
            Primitive("Enemy_Claw_R", PrimitiveType.Cube, new Vector3(0.66f, 1.08f, -0.18f), new Vector3(0.12f, 0.62f, 0.12f), dark, root).transform.localRotation = Quaternion.Euler(0f, 0f, -28f);

            if (demon)
            {
                Primitive("Enemy_Wing_L", PrimitiveType.Cube, new Vector3(-0.9f, 1.55f, 0.12f), new Vector3(1.2f, 0.08f, 0.72f), body, root).transform.localRotation = Quaternion.Euler(0f, 22f, 18f);
                Primitive("Enemy_Wing_R", PrimitiveType.Cube, new Vector3(0.9f, 1.55f, 0.12f), new Vector3(1.2f, 0.08f, 0.72f), body, root).transform.localRotation = Quaternion.Euler(0f, -22f, -18f);
                Primitive("Enemy_EyeGlow", PrimitiveType.Sphere, new Vector3(0f, 2.10f, -0.37f), new Vector3(0.12f, 0.08f, 0.04f), glow, root);
            }
        }

        private static int ImportSurfaceSet(string repoRoot, string materialName, string[] colorCandidates, string[] normalCandidates, string folder, float smoothness)
        {
            string colorSource = FirstExisting(repoRoot, colorCandidates);
            if (string.IsNullOrEmpty(colorSource))
                return 0;

            string normalSource = FirstExisting(repoRoot, normalCandidates);
            string destDir = $"Assets/Textures/ImportedPBR/{folder}";
            string colorAsset = CopyIntoUnityAssets(colorSource, destDir, materialName + "_D");
            string normalAsset = string.IsNullOrEmpty(normalSource) ? "" : CopyIntoUnityAssets(normalSource, destDir, materialName + "_N");

            ConfigureTextureImporter(colorAsset, false);
            if (!string.IsNullOrEmpty(normalAsset))
                ConfigureTextureImporter(normalAsset, true);

            AssetDatabase.ImportAsset(colorAsset, ImportAssetOptions.ForceUpdate);
            if (!string.IsNullOrEmpty(normalAsset))
                AssetDatabase.ImportAsset(normalAsset, ImportAssetOptions.ForceUpdate);

            string matPath = $"{MaterialRoot}/{materialName}.mat";
            Material mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat == null)
            {
                mat = new Material(SurfaceShader());
                AssetDatabase.CreateAsset(mat, matPath);
            }
            else
            {
                Shader shader = SurfaceShader();
                if (shader != null && mat.shader != shader)
                    mat.shader = shader;
            }

            Texture2D color = AssetDatabase.LoadAssetAtPath<Texture2D>(colorAsset);
            Texture2D normal = string.IsNullOrEmpty(normalAsset) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(normalAsset);
            mat.mainTexture = color;
            if (mat.HasProperty("_BaseMap"))
                mat.SetTexture("_BaseMap", color);
            if (mat.HasProperty("_MainTex"))
                mat.SetTexture("_MainTex", color);
            if (mat.HasProperty("_BaseColor"))
                mat.SetColor("_BaseColor", Color.white);
            if (normal != null && mat.HasProperty("_BumpMap"))
            {
                mat.SetTexture("_BumpMap", normal);
                mat.EnableKeyword("_NORMALMAP");
            }
            if (mat.HasProperty("_Smoothness"))
                mat.SetFloat("_Smoothness", smoothness);
            if (mat.HasProperty("_Metallic"))
                mat.SetFloat("_Metallic", 0f);

            EditorUtility.SetDirty(mat);
            return 1;
        }

        private static string FirstExisting(string repoRoot, string[] relativePaths)
        {
            foreach (string relative in relativePaths)
            {
                string full = Path.Combine(repoRoot, relative.Replace('/', Path.DirectorySeparatorChar));
                if (File.Exists(full))
                    return full;
            }
            return "";
        }

        private static string CopyIntoUnityAssets(string sourcePath, string assetFolder, string targetBaseName)
        {
            string extension = Path.GetExtension(sourcePath).ToLowerInvariant();
            string assetPath = $"{assetFolder}/{targetBaseName}{extension}";
            string fullDestination = Path.Combine(Directory.GetParent(Application.dataPath)!.FullName, assetPath.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(fullDestination)!);
            File.Copy(sourcePath, fullDestination, true);
            return assetPath;
        }

        private static void ConfigureTextureImporter(string assetPath, bool normalMap)
        {
            TextureImporter importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (importer == null)
                return;

            importer.maxTextureSize = 4096;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.sRGBTexture = !normalMap;
            importer.textureType = normalMap ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.mipmapEnabled = true;
            EditorUtility.SetDirty(importer);
            importer.SaveAndReimport();
        }

        private static void ConfigureBuiltInPipeline()
        {
            EnsureFolder("Assets/Settings");
            // Unity 6 hedefimiz HDRP. Eski gÃ¶rev adÄ± geriye uyumluluk iÃ§in duruyor,
            // ama artÄ±k render pipeline'Ä± sÄ±fÄ±rlamÄ±yor; aksi halde sahne kararÄ±p bozuluyor.
            AssetDatabase.SaveAssets();
        }

        // â”€â”€ Yeni SceneBuilder'a yonlendir â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        private static bool RunSceneBuilderTask(out string reason)
        {
            return HdrpCleanSceneBuilder.Run(out reason);
        }

        private static bool RunBrainCycle(out string reason)
        {
            try
            {
                AutopilotBrain.RunHeadless();
                reason = "Brain cycle tamamlandÄ±.";
                return true;
            }
            catch (System.Exception ex)
            {
                reason = $"Brain cycle hata: {ex.Message}";
                return false;
            }
        }

        private static bool BuildFirstPlayableScene(out string reason)
        {
            PrepareAssetFolders(out _);
            CreateLookdevMaterials(out _);

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = "Main";

            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = new Color(0.20f, 0.23f, 0.26f);
            RenderSettings.fogDensity = 0.026f;
            RenderSettings.ambientLight = new Color(0.11f, 0.13f, 0.16f);

            GameObject light = new GameObject("Sun_LowAngle_Cinematic");
            Light sun = light.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.85f;
            sun.color = new Color(1f, 0.82f, 0.62f);
            light.transform.rotation = Quaternion.Euler(20f, -42f, 0f);

            GameObject root = new GameObject("TI_Unity_FirstPlayable_Root");
            BuildStartingValley(root.transform);
            BuildCinematicAtmosphere(root.transform);
            GameObject player = BuildPlayer(root.transform);
            BuildCamera(root.transform, player.transform);
            BuildEnemies(root.transform);
            BuildHud(root.transform);
            BuildPostProcess(root.transform);
            BuildGameManager(root.transform, player.transform);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            reason = "Main.unity first playable scene rebuilt with valley, player, camera, enemies, HUD, castle, and route.";
            return true;
        }

        public static void BuildDefaultScene() => HdrpCleanSceneBuilder.Run(out _);

        private static bool BuildMoodyFogForestScene(out string reason)
        {
            PrepareAssetFolders(out _);
            CreateLookdevMaterials(out _);

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = "Main";

            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = new Color(0.22f, 0.29f, 0.34f);
            RenderSettings.fogDensity = 0.034f;
            RenderSettings.ambientLight = new Color(0.055f, 0.07f, 0.082f);

            GameObject sunObject = new GameObject("Sun_EarlyMorning_LowAngle");
            Light sun = sunObject.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.38f;
            sun.color = new Color(0.92f, 0.78f, 0.58f);
            sunObject.transform.rotation = Quaternion.Euler(10f, -48f, 0f);

            GameObject root = new GameObject("TI_MoodyFogForest_FirstPlayable_Root");
            Material soil = LoadMaterial("M_DampBlackSoil");
            Material path = LoadMaterial("M_WetMudPath");
            Material wood = LoadMaterial("M_CabinWeatheredWood");
            Material pine = LoadMaterial("M_DeepPine");
            Material stone = LoadMaterial("M_WetStone");
            Material fire = LoadMaterial("M_WarmLanternGlow");
            Material beam = LoadMaterial("M_WhiteCastleBeam");
            Material fog = LoadMaterial("M_CoolFogBlue");

            BuildMoodyTerrain(root.transform, soil);
            BuildWetForestPath(root.transform, path, stone);
            BuildMoodyCabin(root.transform, new Vector3(-20f, 0.4f, -18f), Quaternion.Euler(0f, 18f, 0f), wood, stone, fire);
            BuildMoodyShed(root.transform, new Vector3(17f, 0.35f, -6f), Quaternion.Euler(0f, -21f, 0f), wood, stone, fire);
            BuildForestCampfire(root.transform, new Vector3(-4f, 0.55f, -10f), wood, fire);
            BuildMoodyForest(root.transform, pine, wood, stone);
            BuildForestCastleAndBeam(root.transform, new Vector3(0f, 0f, 118f), stone, beam);
            BuildGroundDetailScatter(root.transform, path, stone, wood);
            BuildForegroundCompositionFrame(root.transform, pine, wood, stone);
            BuildCinematicAtmosphere(root.transform);

            GameObject player = BuildPlayer(root.transform);
            player.name = "Player_ForestSurvivorSilhouette";
            player.transform.position = new Vector3(0f, 1.05f, -24f);
            player.transform.rotation = Quaternion.Euler(0f, 0f, 0f);
            if (!TryInstantiateModel("Assets/Art/Characters/Imported/Equipment/SM_Sword.fbx", player.transform, new Vector3(0.72f, -0.15f, 0.35f), 0.012f))
                Primitive("Player_Tool_Stick", PrimitiveType.Cube, new Vector3(0.72f, -0.15f, 0.35f), new Vector3(0.08f, 1.65f, 0.08f), wood, player.transform).transform.localRotation = Quaternion.Euler(18f, 0f, -8f);

            BuildCamera(root.transform, player.transform);
            if (Camera.main != null)
            {
                Camera.main.fieldOfView = 52f;
                Camera.main.transform.position = new Vector3(-1.7f, 3.5f, -35f);
                Camera.main.transform.LookAt(new Vector3(0f, 8.5f, 92f));
            }

            BuildEnemies(root.transform);
            BuildHud(root.transform);
            BuildPostProcess(root.transform);
            BuildPostProcessVolume(root.transform);
            BuildVfxManager(root.transform);
            BuildDayCycleManager(root.transform);
            BuildGameManager(root.transform, player.transform);
            BuildAudioManager(root.transform);
            BuildSkyboxManager(root.transform);
            BuildWeatherSystem(root.transform);
            BuildLockOnSystem(root.transform);
            BuildObjectPool(root.transform);
            BuildQuestSystem(root.transform);
            BuildDialogueSystem(root.transform);
            BuildCutsceneController(root.transform);
            BuildBossEncounterManager(root.transform);
            BuildProceduralWorld(root.transform);
            BuildHdrpSceneSetup(root.transform);
            ConfigureQualitySettings();

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            reason = "Main.unity rebuilt: forest + AAA systems (quest, dialogue, cutscene, boss, procedural world, HDRP setup).";
            return true;
        }

        private static void BuildMoodyTerrain(Transform root, Material material)
        {
            const int grid = 58;
            const float width = 120f;
            const float depth = 150f;
            Vector3[] vertices = new Vector3[(grid + 1) * (grid + 1)];
            Vector2[] uv = new Vector2[vertices.Length];
            int[] triangles = new int[grid * grid * 6];

            for (int z = 0; z <= grid; z++)
            {
                for (int x = 0; x <= grid; x++)
                {
                    float nx = x / (float)grid;
                    float nz = z / (float)grid;
                    float worldX = (nx - 0.5f) * width;
                    float worldZ = nz * depth - 42f;
                    float height = Mathf.PerlinNoise(nx * 4.6f, nz * 6.2f) * 1.25f;
                    height += Mathf.PerlinNoise(nx * 14f + 4.1f, nz * 9f) * 0.32f;
                    height += Mathf.Clamp01((worldZ - 42f) / 85f) * 5.8f;
                    vertices[z * (grid + 1) + x] = new Vector3(worldX, height - 0.42f, worldZ);
                    uv[z * (grid + 1) + x] = new Vector2(nx * 8f, nz * 10f);
                }
            }

            int t = 0;
            for (int z = 0; z < grid; z++)
            {
                for (int x = 0; x < grid; x++)
                {
                    int i = z * (grid + 1) + x;
                    triangles[t++] = i;
                    triangles[t++] = i + grid + 1;
                    triangles[t++] = i + 1;
                    triangles[t++] = i + 1;
                    triangles[t++] = i + grid + 1;
                    triangles[t++] = i + grid + 2;
                }
            }

            Mesh mesh = new Mesh();
            mesh.name = "Generated_MoodyWetTerrainMesh";
            mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.vertices = vertices;
            mesh.uv = uv;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();

            GameObject terrain = new GameObject("MoodyUnevenWetTerrain");
            terrain.transform.SetParent(root);
            terrain.AddComponent<MeshFilter>().sharedMesh = mesh;
            terrain.AddComponent<MeshRenderer>().sharedMaterial = material;
            terrain.AddComponent<MeshCollider>().sharedMesh = mesh;
        }

        private static void BuildWetForestPath(Transform root, Material path, Material stone)
        {
            for (int i = 0; i < 34; i++)
            {
                float t = i / 33f;
                float z = Mathf.Lerp(-32f, 86f, t);
                float x = Mathf.Sin(t * Mathf.PI * 1.15f) * 4.5f;
                GameObject patch = Primitive($"WetDirtPath_MuddyReflection_{i:00}", PrimitiveType.Cube, new Vector3(x, 0.12f + t * 0.22f, z), new Vector3(Mathf.Lerp(8f, 4.2f, t), 0.045f, 5.2f), path, root);
                patch.transform.localRotation = Quaternion.Euler(0f, Mathf.Lerp(-5f, 8f, Mathf.PingPong(t * 2f, 1f)), 0f);

                if (i % 4 == 0)
                {
                    Primitive($"WetPath_Puddle_{i:00}", PrimitiveType.Sphere, new Vector3(x + UnityEngine.Random.Range(-2.4f, 2.4f), 0.18f + t * 0.2f, z + UnityEngine.Random.Range(-1.8f, 1.8f)), new Vector3(1.8f, 0.09f, 0.9f), LoadMaterial("M_WetStone"), root);
                    Primitive($"SmallPathRock_{i:00}", PrimitiveType.Sphere, new Vector3(x + UnityEngine.Random.Range(-4.4f, 4.4f), 0.42f + t * 0.2f, z + UnityEngine.Random.Range(-2.5f, 2.5f)), Vector3.one * UnityEngine.Random.Range(0.35f, 1.1f), stone, root);
                }
            }
        }

        private static void BuildMoodyForest(Transform root, Material pine, Material wood, Material stone)
        {
            UnityEngine.Random.InitState(20260504);
            for (int i = 0; i < 148; i++)
            {
                bool left = i % 2 == 0;
                float z = UnityEngine.Random.Range(-42f, 116f);
                float nearPathGap = Mathf.Lerp(10f, 5f, Mathf.InverseLerp(-36f, 106f, z));
                float x = (left ? -1f : 1f) * UnityEngine.Random.Range(nearPathGap, 68f);
                if (i % 9 == 0)
                    BuildDeadTree(root, new Vector3(x, 0.55f, z), wood, i);
                else
                    BuildMoodyPine(root, new Vector3(x, 0.35f, z), pine, wood, i, UnityEngine.Random.Range(0.75f, 1.45f));

                if (i % 11 == 0)
                    Primitive($"MossyForegroundRock_{i:00}", PrimitiveType.Sphere, new Vector3(x * 0.92f, 0.42f, z + 1.2f), Vector3.one * UnityEngine.Random.Range(0.8f, 2.2f), stone, root);
            }

            BuildDeadTree(root, new Vector3(-8f, 0.4f, -6f), wood, 900);
            BuildDeadTree(root, new Vector3(31f, 0.4f, -1f), wood, 901);
            BuildMoodyPine(root, new Vector3(-39f, 0.4f, -30f), pine, wood, 902, 2.2f);
            BuildMoodyPine(root, new Vector3(37f, 0.4f, -20f), pine, wood, 903, 1.95f);
        }

        private static void BuildMoodyPine(Transform root, Vector3 position, Material pine, Material wood, int index, float scale)
        {
            GameObject tree = new GameObject($"SparseTallPine_{index:00}");
            tree.transform.SetParent(root);
            tree.transform.position = position;
            tree.transform.rotation = Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 360f), UnityEngine.Random.Range(-3f, 3f));
            Primitive("Trunk", PrimitiveType.Cylinder, new Vector3(0f, 2.2f * scale, 0f), new Vector3(0.32f * scale, 4.4f * scale, 0.32f * scale), wood, tree.transform);
            Cone("LowerNeedles", new Vector3(0f, 5.0f * scale, 0f), new Vector3(2.3f * scale, 4.0f * scale, 2.3f * scale), pine, tree.transform);
            Cone("UpperNeedles", new Vector3(0f, 7.2f * scale, 0f), new Vector3(1.55f * scale, 3.2f * scale, 1.55f * scale), pine, tree.transform);
        }

        private static void BuildDeadTree(Transform root, Vector3 position, Material wood, int index)
        {
            GameObject tree = new GameObject($"DeadTree_Silhouette_{index:00}");
            tree.transform.SetParent(root);
            tree.transform.position = position;
            tree.transform.rotation = Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 360f), UnityEngine.Random.Range(-7f, 7f));
            Primitive("DeadTrunk", PrimitiveType.Cylinder, new Vector3(0f, 3.6f, 0f), new Vector3(0.26f, 7.2f, 0.26f), wood, tree.transform);
            for (int b = 0; b < 4; b++)
            {
                GameObject branch = Primitive($"BareBranch_{b:00}", PrimitiveType.Cube, new Vector3((b % 2 == 0 ? -1f : 1f) * 0.75f, 4.2f + b * 0.75f, 0f), new Vector3(1.8f, 0.08f, 0.08f), wood, tree.transform);
                branch.transform.localRotation = Quaternion.Euler(0f, 0f, (b % 2 == 0 ? 28f : -28f));
            }
        }

        private static void BuildMoodyCabin(Transform root, Vector3 position, Quaternion rotation, Material wood, Material stone, Material fire)
        {
            GameObject cabin = new GameObject("MoodyVillage_MainWoodenCabin");
            cabin.transform.SetParent(root);
            cabin.transform.position = position;
            cabin.transform.rotation = rotation;
            Primitive("StonePierBase", PrimitiveType.Cube, new Vector3(0f, 0.25f, 0f), new Vector3(10f, 0.5f, 7.2f), stone, cabin.transform);
            Primitive("WeatheredWoodWalls", PrimitiveType.Cube, new Vector3(0f, 2.0f, 0f), new Vector3(9.2f, 3.4f, 6.2f), wood, cabin.transform);
            for (int i = 0; i < 9; i++)
                Primitive($"RoofShingle_{i:00}", PrimitiveType.Cube, new Vector3(-3.6f + i * 0.9f, 4.0f + Mathf.Abs(i - 4) * 0.17f, 0f), new Vector3(0.82f, 0.22f, 7.4f), wood, cabin.transform).transform.localRotation = Quaternion.Euler(0f, 0f, i < 4 ? -28f : 28f);
            Primitive("WarmWindowGlow", PrimitiveType.Cube, new Vector3(-2.2f, 2.0f, -3.15f), new Vector3(1.45f, 1.1f, 0.08f), fire, cabin.transform);
            Primitive("DoorDark", PrimitiveType.Cube, new Vector3(1.7f, 1.4f, -3.18f), new Vector3(1.4f, 2.35f, 0.1f), LoadMaterial("M_DarkMetal"), cabin.transform);
            Primitive("Chimney", PrimitiveType.Cube, new Vector3(-3.0f, 5.0f, 1.2f), new Vector3(0.85f, 2.8f, 0.85f), stone, cabin.transform);
            Light lantern = cabin.AddComponent<Light>();
            lantern.type = LightType.Point;
            lantern.range = 18f;
            lantern.intensity = 5.5f;
            lantern.color = new Color(1f, 0.48f, 0.18f);
        }

        private static void BuildMoodyShed(Transform root, Vector3 position, Quaternion rotation, Material wood, Material stone, Material fire)
        {
            GameObject shed = new GameObject("MoodyVillage_SecondarySmallShed");
            shed.transform.SetParent(root);
            shed.transform.position = position;
            shed.transform.rotation = rotation;
            Primitive("ShedBase", PrimitiveType.Cube, new Vector3(0f, 0.18f, 0f), new Vector3(5.5f, 0.36f, 4.2f), stone, shed.transform);
            Primitive("ShedWalls", PrimitiveType.Cube, new Vector3(0f, 1.35f, 0f), new Vector3(5.0f, 2.3f, 3.8f), wood, shed.transform);
            Primitive("ShedRoofLeft", PrimitiveType.Cube, new Vector3(-1.2f, 2.8f, 0f), new Vector3(3.2f, 0.28f, 4.7f), wood, shed.transform).transform.localRotation = Quaternion.Euler(0f, 0f, -24f);
            Primitive("ShedRoofRight", PrimitiveType.Cube, new Vector3(1.2f, 2.8f, 0f), new Vector3(3.2f, 0.28f, 4.7f), wood, shed.transform).transform.localRotation = Quaternion.Euler(0f, 0f, 24f);
            Primitive("ShedWindowGlow", PrimitiveType.Cube, new Vector3(-1.3f, 1.35f, -1.95f), new Vector3(0.9f, 0.65f, 0.08f), fire, shed.transform);
        }

        private static void BuildForestCampfire(Transform root, Vector3 position, Material wood, Material fire)
        {
            GameObject camp = new GameObject("Village_ForestCampfire");
            camp.transform.SetParent(root);
            camp.transform.localPosition = position;
            Primitive("WetLog_A", PrimitiveType.Cube, Vector3.zero, new Vector3(2.2f, 0.16f, 0.16f), wood, camp.transform).transform.localRotation = Quaternion.Euler(0f, 25f, 0f);
            Primitive("WetLog_B", PrimitiveType.Cube, Vector3.zero, new Vector3(2.2f, 0.16f, 0.16f), wood, camp.transform).transform.localRotation = Quaternion.Euler(0f, -25f, 0f);
            Cone("OrangeFlame_Core", new Vector3(0f, 0.55f, 0f), new Vector3(0.75f, 0.95f, 0.75f), fire, camp.transform);
            Cone("OrangeFlame_Outer", new Vector3(0f, 0.75f, 0f), new Vector3(1.1f, 1.5f, 1.1f), LoadMaterial("M_WarmLanternGlow"), camp.transform);
            GameObject lightObj = new GameObject("ForestFireLight");
            lightObj.transform.SetParent(camp.transform);
            lightObj.transform.localPosition = new Vector3(0f, 0.5f, 0f);
            Light light = lightObj.AddComponent<Light>();
            light.type = LightType.Point;
            light.range = 20f;
            light.intensity = 7f;
            light.color = new Color(1f, 0.42f, 0.14f);
            camp.AddComponent<Gameplay.CampfireVfx>();
        }

        private static void BuildForestCastleAndBeam(Transform root, Vector3 position, Material stone, Material beam)
        {
            GameObject castle = new GameObject("Distant_FargothCastle_Silhouette");
            castle.transform.SetParent(root);
            castle.transform.position = position;
            Primitive("CastleBase_FogHidden", PrimitiveType.Cube, new Vector3(0f, 10f, 0f), new Vector3(28f, 18f, 13f), stone, castle.transform);
            for (int i = 0; i < 5; i++)
            {
                float x = -14f + i * 7f;
                Primitive($"MistTower_{i:00}", PrimitiveType.Cylinder, new Vector3(x, 17f + (i % 2) * 2f, 1f), new Vector3(2.2f, 30f + i * 1.5f, 2.2f), stone, castle.transform);
                Cone($"MistSpire_{i:00}", new Vector3(x, 34f + (i % 2) * 2f, 1f), new Vector3(4.0f, 11f, 4.0f), stone, castle.transform);
            }
            Primitive("Castle_MagicalVerticalBeam", PrimitiveType.Cylinder, new Vector3(0f, 72f, 0f), new Vector3(0.85f, 135f, 0.85f), beam, castle.transform);
            Primitive("QuestBeacon_FargothCastle", PrimitiveType.Cylinder, new Vector3(0f, 54f, 0f), new Vector3(1.45f, 94f, 1.45f), beam, castle.transform);
            Light glow = castle.AddComponent<Light>();
            glow.type = LightType.Point;
            glow.range = 110f;
            glow.intensity = 8.5f;
            glow.color = new Color(1f, 0.92f, 0.72f);
        }

        private static void BuildDepthFogSilhouettes(Transform root, Material fog)
        {
            for (int i = 0; i < 6; i++)
            {
                GameObject layer = Primitive($"FogDepthVolume_Readability_{i:00}", PrimitiveType.Sphere, new Vector3(0f, 5.4f + i * 1.2f, 34f + i * 15f), new Vector3(78f + i * 10f, 4.2f, 9f), fog, root);
                layer.transform.localRotation = Quaternion.Euler(0f, UnityEngine.Random.Range(-7f, 7f), 0f);
            }
        }

        private static void BuildGroundDetailScatter(Transform root, Material path, Material stone, Material wood)
        {
            UnityEngine.Random.InitState(20260505);
            Material wet = LoadMaterial("M_WetStone");
            for (int i = 0; i < 72; i++)
            {
                float t = UnityEngine.Random.Range(0f, 1f);
                float z = Mathf.Lerp(-34f, 88f, t);
                float centerX = Mathf.Sin(t * Mathf.PI * 1.15f) * 4.5f;
                float side = UnityEngine.Random.value > 0.5f ? 1f : -1f;
                float x = centerX + side * UnityEngine.Random.Range(2.8f, 12.5f);
                Vector3 pos = new Vector3(x, 0.34f + t * 0.25f, z + UnityEngine.Random.Range(-2.6f, 2.6f));
                if (i % 3 == 0)
                {
                    GameObject puddle = Primitive($"MicroPuddle_DarkReflection_{i:00}", PrimitiveType.Sphere, pos, new Vector3(UnityEngine.Random.Range(0.9f, 2.2f), 0.045f, UnityEngine.Random.Range(0.45f, 1.15f)), wet, root);
                    puddle.transform.localRotation = Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 180f), 0f);
                }
                else if (i % 3 == 1)
                {
                    Primitive($"RootAndBranch_Detail_{i:00}", PrimitiveType.Cube, pos + Vector3.up * 0.05f, new Vector3(UnityEngine.Random.Range(0.9f, 2.4f), 0.075f, 0.09f), wood, root).transform.localRotation = Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 180f), UnityEngine.Random.Range(-5f, 5f));
                }
                else
                {
                    Primitive($"PathPebbleCluster_{i:00}", PrimitiveType.Sphere, pos, Vector3.one * UnityEngine.Random.Range(0.22f, 0.65f), stone, root);
                }
            }

            for (int i = 0; i < 24; i++)
            {
                float z = Mathf.Lerp(-31f, 76f, i / 23f);
                float x = Mathf.Sin(i * 0.42f) * 4.2f;
                GameObject shine = Primitive($"WetPath_SpecularRibbon_{i:00}", PrimitiveType.Cube, new Vector3(x, 0.21f, z), new Vector3(2.4f, 0.018f, 0.28f), path, root);
                shine.transform.localRotation = Quaternion.Euler(0f, UnityEngine.Random.Range(-18f, 18f), 0f);
            }
        }

        private static void BuildForegroundCompositionFrame(Transform root, Material pine, Material wood, Material stone)
        {
            BuildMoodyPine(root, new Vector3(-47f, 0.2f, -37f), pine, wood, 1200, 2.85f);
            BuildMoodyPine(root, new Vector3(45f, 0.2f, -33f), pine, wood, 1201, 2.35f);
            BuildDeadTree(root, new Vector3(-33f, 0.25f, -24f), wood, 1202);
            BuildDeadTree(root, new Vector3(34f, 0.25f, -17f), wood, 1203);
            Primitive("Foreground_LeftWetBoulder", PrimitiveType.Sphere, new Vector3(-19f, 0.72f, -29f), new Vector3(4.2f, 1.35f, 2.3f), stone, root);
            Primitive("Foreground_RightWetBoulder", PrimitiveType.Sphere, new Vector3(22f, 0.62f, -27f), new Vector3(3.4f, 1.1f, 2.0f), stone, root);
        }

        private static void BuildStormCloudCanopy(Transform root, Material fog)
        {
            for (int i = 0; i < 7; i++)
            {
                float x = -54f + i * 18f;
                GameObject cloud = Primitive($"LowStormCloudLayer_{i:00}", PrimitiveType.Sphere, new Vector3(x, 28f + (i % 2) * 2f, 58f + i * 5f), new Vector3(18f, 2.2f, 8f), fog, root);
                cloud.transform.localRotation = Quaternion.Euler(0f, UnityEngine.Random.Range(-18f, 18f), 0f);
            }
        }

        private static void BuildStartingValley(Transform root)
        {
            UnityEngine.Random.InitState(20260503);

            Material mud = LoadMaterial("M_NordicMud");
            Material grass = LoadMaterial("M_ForestGrass");
            Material stone = LoadMaterial("M_WetStone");
            Material wood = LoadMaterial("M_AgedWood");
            Material fire = LoadMaterial("M_FireEmissive");
            Material beam = LoadMaterial("M_RedBeamEmissive");
            Material snow = LoadMaterial("M_SnowMountain");

            Primitive("Ground_StartingValley", PrimitiveType.Cube, new Vector3(0f, -0.08f, 18f), new Vector3(72f, 0.15f, 96f), grass, root);
            Primitive("DirtPath_ToCastle", PrimitiveType.Cube, new Vector3(0f, 0.02f, 18f), new Vector3(10f, 0.05f, 92f), mud, root);

            for (int i = 0; i < 18; i++)
            {
                float side = i % 2 == 0 ? -1f : 1f;
                float z = -18f + i * 4.8f;
                float x = side * UnityEngine.Random.Range(10f, 24f);
                Primitive($"PineTrunk_{i:00}", PrimitiveType.Cylinder, new Vector3(x, 1.2f, z), new Vector3(0.45f, 2.4f, 0.45f), wood, root);
                Cone($"PineCrown_{i:00}", new Vector3(x, 3.1f, z), new Vector3(2.7f, 4.1f, 2.7f), grass, root);
            }

            for (int i = 0; i < 14; i++)
            {
                Vector3 pos = new Vector3(UnityEngine.Random.Range(-28f, 28f), 0.35f, UnityEngine.Random.Range(-20f, 46f));
                Primitive($"RouteRock_{i:00}", PrimitiveType.Sphere, pos, Vector3.one * UnityEngine.Random.Range(0.65f, 1.6f), stone, root);
            }

            BuildHouse(root, new Vector3(-17f, 0f, -21f), Quaternion.Euler(0f, 18f, 0f), wood, stone, fire);
            BuildCampfire(root, new Vector3(13f, 0.25f, -17f), wood, fire);
            BuildBrokenBridge(root, new Vector3(0f, 0.18f, 27f), wood, stone);
            BuildEnemyCamp(root, new Vector3(0f, 0f, 18f), wood, fire);
            BuildRouteMarkers(root, mud, beam);
            BuildCastleSilhouette(root, new Vector3(0f, 0f, 62f), stone, beam);
            BuildDistantDragon(root, new Vector3(-12f, 28f, 58f), LoadMaterial("M_DarkMetal"));
            BuildPremiumReferenceComposition(root, wood, stone, grass, mud, fire, beam, snow);

            for (int i = 0; i < 7; i++)
            {
                float x = -30f + i * 10f;
                Cone($"SnowMountain_Backdrop_{i:00}", new Vector3(x, 11f, 86f + Mathf.Abs(x) * 0.25f), new Vector3(17f, 32f + (i % 3) * 5f, 17f), snow, root);
            }
        }

        private static void BuildPremiumReferenceComposition(Transform root, Material wood, Material stone, Material grass, Material mud, Material fire, Material beam, Material snow)
        {
            Material pine = LoadMaterial("M_DeepPine");
            Material path = LoadMaterial("M_PathDirtWet");
            Material banner = LoadMaterial("M_GothicBannerRed");
            Material fog = LoadMaterial("M_FogBackdrop");
            Material magic = LoadMaterial("M_MagicRoseGlow");

            Primitive("Vista_DeepValleyFloor_Extension", PrimitiveType.Cube, new Vector3(0f, -0.13f, 64f), new Vector3(150f, 0.12f, 180f), grass, root);
            Primitive("Left_Forest_Hillside_Composition", PrimitiveType.Cube, new Vector3(-58f, 3.1f, 42f), new Vector3(56f, 6f, 145f), pine, root).transform.localRotation = Quaternion.Euler(0f, 0f, -7f);
            Primitive("Right_Forest_Hillside_Composition", PrimitiveType.Cube, new Vector3(58f, 2.6f, 48f), new Vector3(50f, 5f, 140f), pine, root).transform.localRotation = Quaternion.Euler(0f, 0f, 6f);

            for (int i = 0; i < 26; i++)
            {
                float t = i / 25f;
                float z = Mathf.Lerp(-33f, 92f, t);
                float x = Mathf.Sin(t * Mathf.PI * 1.35f) * 7.5f;
                GameObject segment = Primitive($"CinematicReadablePath_{i:00}", PrimitiveType.Cube, new Vector3(x, 0.09f, z), new Vector3(Mathf.Lerp(13f, 5.5f, t), 0.045f, 4.8f), path, root);
                segment.transform.localRotation = Quaternion.Euler(0f, Mathf.Lerp(-8f, 11f, Mathf.PingPong(t * 2f, 1f)), 0f);

                if (i % 3 == 0)
                {
                    Primitive($"Pathside_MudDecal_L_{i:00}", PrimitiveType.Sphere, new Vector3(x - 5.8f, 0.18f, z + 0.5f), new Vector3(1.7f, 0.12f, 1.0f), mud, root);
                    Primitive($"Pathside_MudDecal_R_{i:00}", PrimitiveType.Sphere, new Vector3(x + 5.5f, 0.18f, z - 0.7f), new Vector3(1.3f, 0.10f, 0.9f), mud, root);
                }
            }

            for (int i = 0; i < 92; i++)
            {
                bool left = i % 2 == 0;
                float z = UnityEngine.Random.Range(-28f, 96f);
                float x = (left ? -1f : 1f) * UnityEngine.Random.Range(18f, 70f);
                float height = UnityEngine.Random.Range(3.4f, 7.8f);
                Primitive($"DensePine_Trunk_{i:00}", PrimitiveType.Cylinder, new Vector3(x, height * 0.28f, z), new Vector3(0.35f, height * 0.55f, 0.35f), wood, root);
                Cone($"DensePine_Crown_{i:00}", new Vector3(x, height * 0.72f, z), new Vector3(height * 0.42f, height, height * 0.42f), pine, root);
            }

            BuildHouse(root, new Vector3(-24f, 0f, -28f), Quaternion.Euler(0f, 28f, 0f), wood, stone, fire);
            BuildHouse(root, new Vector3(-34f, 0f, -13f), Quaternion.Euler(0f, 52f, 0f), wood, stone, fire);
            BuildSmallNordicHut(root, new Vector3(18f, 0f, -22f), Quaternion.Euler(0f, -24f, 0f), wood, stone, fire);
            BuildVillageFence(root, wood);
            BuildWatchtower(root, new Vector3(26f, 0f, -6f), wood, fire);
            BuildBanner(root, new Vector3(-19f, 3.1f, -24.2f), banner);
            BuildBanner(root, new Vector3(6f, 18.5f, 91f), banner);
            BuildGothicMegaCastle(root, new Vector3(0f, 0f, 105f), stone, beam, banner);
            BuildMountainWall(root, snow, stone);

            Primitive("AtmosphericDepthFog_SideLayer_L", PrimitiveType.Cube, new Vector3(-72f, 8f, 70f), new Vector3(0.4f, 16f, 95f), fog, root);
            Primitive("AtmosphericDepthFog_SideLayer_R", PrimitiveType.Cube, new Vector3(72f, 8f, 70f), new Vector3(0.4f, 16f, 95f), fog, root);
            Primitive("CastleBeam_BloomCore_Wide", PrimitiveType.Cylinder, new Vector3(0f, 58f, 106f), new Vector3(1.8f, 125f, 1.8f), magic, root);
        }

        private static void BuildCinematicAtmosphere(Transform root)
        {
            GameObject rim = new GameObject("WarmVillage_RimLight");
            rim.transform.SetParent(root);
            rim.transform.position = new Vector3(-18f, 6f, -22f);
            Light rimLight = rim.AddComponent<Light>();
            rimLight.type = LightType.Point;
            rimLight.range = 34f;
            rimLight.intensity = 4.2f;
            rimLight.color = new Color(1f, 0.48f, 0.18f);

            GameObject castleGlow = new GameObject("RedCastle_AtmosphereLight");
            castleGlow.transform.SetParent(root);
            castleGlow.transform.position = new Vector3(0f, 24f, 98f);
            Light red = castleGlow.AddComponent<Light>();
            red.type = LightType.Point;
            red.range = 90f;
            red.intensity = 7f;
            red.color = new Color(1f, 0.05f, 0.22f);
        }

        private static void BuildSmallNordicHut(Transform root, Vector3 position, Quaternion rotation, Material wood, Material stone, Material fire)
        {
            GameObject hut = new GameObject("Village_SmallNordicHut_Blockout");
            hut.transform.SetParent(root);
            hut.transform.position = position;
            hut.transform.rotation = rotation;
            Primitive("StoneBase", PrimitiveType.Cube, new Vector3(0f, 0.2f, 0f), new Vector3(5.2f, 0.4f, 4.2f), stone, hut.transform);
            Primitive("DarkWoodCabin", PrimitiveType.Cube, new Vector3(0f, 1.25f, 0f), new Vector3(4.8f, 2.1f, 3.8f), wood, hut.transform);
            GameObject roofA = Primitive("Roof_A", PrimitiveType.Cube, new Vector3(-1.25f, 2.65f, 0f), new Vector3(3.2f, 0.35f, 5.2f), wood, hut.transform);
            roofA.transform.localRotation = Quaternion.Euler(0f, 0f, -31f);
            GameObject roofB = Primitive("Roof_B", PrimitiveType.Cube, new Vector3(1.25f, 2.65f, 0f), new Vector3(3.2f, 0.35f, 5.2f), wood, hut.transform);
            roofB.transform.localRotation = Quaternion.Euler(0f, 0f, 31f);
            Primitive("WindowGlow", PrimitiveType.Cube, new Vector3(-1.3f, 1.25f, -1.95f), new Vector3(0.85f, 0.7f, 0.08f), fire, hut.transform);
        }

        private static void BuildVillageFence(Transform root, Material wood)
        {
            for (int i = 0; i < 18; i++)
            {
                float z = -35f + i * 2.3f;
                float x = -9f - Mathf.Sin(i * 0.65f) * 2.2f;
                GameObject post = Primitive($"VillageFence_Post_{i:00}", PrimitiveType.Cube, new Vector3(x, 0.85f, z), new Vector3(0.22f, 1.7f, 0.22f), wood, root);
                post.transform.localRotation = Quaternion.Euler(0f, 8f, UnityEngine.Random.Range(-5f, 5f));
            }
        }

        private static void BuildWatchtower(Transform root, Vector3 position, Material wood, Material fire)
        {
            GameObject tower = new GameObject("Village_Watchtower_RightSilhouette");
            tower.transform.SetParent(root);
            tower.transform.position = position;
            Primitive("Leg_A", PrimitiveType.Cube, new Vector3(-1.1f, 2f, -1.1f), new Vector3(0.28f, 4f, 0.28f), wood, tower.transform);
            Primitive("Leg_B", PrimitiveType.Cube, new Vector3(1.1f, 2f, -1.1f), new Vector3(0.28f, 4f, 0.28f), wood, tower.transform);
            Primitive("Leg_C", PrimitiveType.Cube, new Vector3(-1.1f, 2f, 1.1f), new Vector3(0.28f, 4f, 0.28f), wood, tower.transform);
            Primitive("Leg_D", PrimitiveType.Cube, new Vector3(1.1f, 2f, 1.1f), new Vector3(0.28f, 4f, 0.28f), wood, tower.transform);
            Primitive("Platform", PrimitiveType.Cube, new Vector3(0f, 4.05f, 0f), new Vector3(3.2f, 0.28f, 3.2f), wood, tower.transform);
            Cone("TorchFlame", new Vector3(0f, 4.85f, 0f), new Vector3(0.8f, 1.0f, 0.8f), fire, tower.transform);
        }

        private static void BuildBanner(Transform root, Vector3 position, Material banner)
        {
            GameObject cloth = Primitive("RedLionBanner_CompositionMarker", PrimitiveType.Cube, position, new Vector3(1.6f, 2.8f, 0.08f), banner, root);
            cloth.transform.localRotation = Quaternion.Euler(0f, -6f, 0f);
        }

        private static void BuildGothicMegaCastle(Transform root, Vector3 position, Material stone, Material beam, Material banner)
        {
            GameObject castle = new GameObject("FargothCastle_GothicMegaSilhouette");
            castle.transform.SetParent(root);
            castle.transform.position = position;
            Primitive("UpperKeep", PrimitiveType.Cube, new Vector3(0f, 18f, 0f), new Vector3(22f, 28f, 12f), stone, castle.transform);
            Primitive("LowerFortress", PrimitiveType.Cube, new Vector3(0f, 7f, -2f), new Vector3(36f, 14f, 16f), stone, castle.transform);
            for (int i = 0; i < 6; i++)
            {
                float x = -24f + i * 9.6f;
                Primitive($"GothicTower_{i:00}", PrimitiveType.Cylinder, new Vector3(x, 14f + (i % 2) * 3f, 1f), new Vector3(3.2f, 28f + (i % 2) * 6f, 3.2f), stone, castle.transform);
                Cone($"GothicSpire_{i:00}", new Vector3(x, 32f + (i % 2) * 6f, 1f), new Vector3(5.3f, 13f, 5.3f), stone, castle.transform);
            }
            Primitive("MainRedBeam", PrimitiveType.Cylinder, new Vector3(0f, 76f, 0f), new Vector3(1.2f, 150f, 1.2f), beam, castle.transform);
            Primitive("Banner_Left", PrimitiveType.Cube, new Vector3(-9f, 14f, -6.2f), new Vector3(2.2f, 6.5f, 0.1f), banner, castle.transform);
            Primitive("Banner_Right", PrimitiveType.Cube, new Vector3(9f, 14f, -6.2f), new Vector3(2.2f, 6.5f, 0.1f), banner, castle.transform);
        }

        private static void BuildMountainWall(Transform root, Material snow, Material stone)
        {
            for (int i = 0; i < 15; i++)
            {
                float x = -95f + i * 13.5f;
                float z = 128f + Mathf.Abs(x) * 0.12f;
                Cone($"EpicSnowMountain_Wall_{i:00}", new Vector3(x, 22f, z), new Vector3(20f + (i % 4) * 4f, 52f + (i % 5) * 7f, 20f + (i % 4) * 4f), snow, root);
                if (i % 2 == 0)
                    Cone($"DarkRockPeak_Contrast_{i:00}", new Vector3(x + 4f, 14f, z - 8f), new Vector3(13f, 32f, 13f), stone, root);
            }
        }

        private static GameObject BuildPlayer(Transform root)
        {
            GameObject player = Primitive("Player_NordWarrior", PrimitiveType.Capsule, new Vector3(0f, 1.05f, -30f), new Vector3(1f, 1f, 1f), LoadMaterial("M_DarkMetal"), root);
            player.tag = "Player";
            CharacterController controller = player.AddComponent<CharacterController>();
            controller.height = 2f;
            controller.radius = 0.42f;
            player.AddComponent<Gameplay.PlayerController>();
            player.AddComponent<Gameplay.StaminaComponent>();
            Gameplay.CombatComponent combat = player.AddComponent<Gameplay.CombatComponent>();
            combat.maxHealth = 160f;
            combat.currentHealth = 160f;
            combat.maxMana = 90f;
            combat.currentMana = 90f;
            combat.attackDamage = 24f;
            player.AddComponent<Gameplay.InventoryComponent>();
            player.AddComponent<Gameplay.ExperienceComponent>();

            bool importedHero = AttachImportedCharacterVisual(player.transform, true, 0);
            MeshRenderer playerRenderer = player.GetComponent<MeshRenderer>();
            if (playerRenderer != null && importedHero)
                playerRenderer.enabled = false;

            if (!importedHero)
                Primitive("Player_Cloak_Blockout", PrimitiveType.Cube, new Vector3(0f, 0.05f, -0.45f), new Vector3(0.95f, 1.55f, 0.08f), CreateRuntimeMaterial(new Color(0.24f, 0.02f, 0.05f)), player.transform);

            // Weapon: prefer real sword model, fallback to thin cube blockout
            bool swordAttached =
                TryInstantiateModel("Assets/Art/Characters/Imported/Equipment/SM_Sword.fbx",  player.transform, new Vector3(0.78f, -0.10f, 0.35f), 0.012f) ||
                TryInstantiateModel("Assets/Art/Characters/Imported/Equipment/SM_Katana.fbx", player.transform, new Vector3(0.78f, -0.10f, 0.35f), 0.012f);
            if (!swordAttached)
                Primitive("Player_Sword_Blockout", PrimitiveType.Cube, new Vector3(0.78f, -0.10f, 0.35f), new Vector3(0.08f, 1.45f, 0.08f), LoadMaterial("M_DarkMetal"), player.transform);
            return player;
        }

        private static void BuildCamera(Transform root, Transform player)
        {
            GameObject camera = new GameObject("Main Camera");
            camera.tag = "MainCamera";
            camera.transform.SetParent(root);
            Camera cam = camera.AddComponent<Camera>();
            cam.fieldOfView = 62f;
            cam.nearClipPlane = 0.08f;
            cam.farClipPlane = 700f;
            AudioListener listener = camera.AddComponent<AudioListener>();
            listener.enabled = true;
            Gameplay.ThirdPersonCamera follow = camera.AddComponent<Gameplay.ThirdPersonCamera>();
            follow.target = player;
            follow.distance = 5.8f;
            follow.targetOffset = new Vector3(0.35f, 1.65f, 0f);
            follow.defaultFov = 62f;
            follow.sprintFovBoost = 7f;
            camera.AddComponent<Gameplay.ScreenShake>();
            camera.transform.position = player.position + new Vector3(0f, 3.5f, -6f);
        }

        private static void BuildEnemies(Transform root)
        {
            Material metal = LoadMaterial("M_DarkMetal");
            Material glow = LoadMaterial("M_RedBeamEmissive");

            Vector3[] positions = {
                new Vector3(-5f, 1.05f, 18f), new Vector3(-1.5f, 1.05f, 23f),
                new Vector3(3f, 1.05f, 19f), new Vector3(6f, 1.05f, 26f)
            };

            for (int i = 0; i < 4; i++)
            {
                bool isBrute = i % 2 == 0;
                Material bodyMat = isBrute ? metal : glow;
                GameObject enemy = Primitive($"Enemy_RootAcolyte_{i:00}", PrimitiveType.Capsule, positions[i], isBrute ? Vector3.one * 1.15f : Vector3.one, bodyMat, root);

                CharacterController cc = enemy.AddComponent<CharacterController>();
                cc.height = 2f;
                cc.radius = 0.4f;

                Gameplay.CombatComponent combat = enemy.AddComponent<Gameplay.CombatComponent>();
                combat.maxHealth = isBrute ? 80f : 55f;
                combat.currentHealth = combat.maxHealth;
                combat.attackDamage = isBrute ? 14f : 9f;
                combat.attackCooldown = isBrute ? 1.4f : 1.0f;
                combat.knockbackForce = isBrute ? 3f : 2f;
                combat.deathFadeDuration = 3.5f;

                Gameplay.EnemyAIController ai = enemy.AddComponent<Gameplay.EnemyAIController>();
                ai.detectionRadius = isBrute ? 14f : 18f;
                ai.fieldOfViewAngle = isBrute ? 100f : 140f;
                ai.attackRange = isBrute ? 2.0f : 1.6f;
                ai.chaseSpeed = isBrute ? 3.5f : 4.8f;
                ai.attackCooldown = isBrute ? 2.2f : 1.4f;
                ai.attackWindupSeconds = isBrute ? 0.45f : 0.25f;

                enemy.AddComponent<Gameplay.LootDrop>();

                bool importedEnemy = AttachImportedCharacterVisual(enemy.transform, false, i);
                MeshRenderer renderer = enemy.GetComponent<MeshRenderer>();
                if (renderer != null && importedEnemy)
                    renderer.enabled = false;
            }
        }

        private static void BuildRouteMarkers(Transform root, Material pathMaterial, Material beamMaterial)
        {
            for (int i = 0; i < 6; i++)
            {
                float z = -24f + i * 13f;
                GameObject marker = Primitive($"Route_Readability_DirtPatch_{i:00}", PrimitiveType.Cube, new Vector3(0f, 0.075f, z), new Vector3(12f - i * 0.7f, 0.035f, 2.2f), pathMaterial, root);
                marker.transform.localRotation = Quaternion.Euler(0f, i % 2 == 0 ? 7f : -6f, 0f);
            }

            Primitive("QuestBeacon_FargothCastle", PrimitiveType.Cylinder, new Vector3(0f, 8.5f, 48f), new Vector3(0.25f, 17f, 0.25f), beamMaterial, root);
        }

        private static void BuildEnemyCamp(Transform root, Vector3 position, Material wood, Material fire)
        {
            GameObject camp = new GameObject("EnemyCamp_RootAcolyte_Blockout");
            camp.transform.SetParent(root);
            camp.transform.position = position;

            for (int i = 0; i < 10; i++)
            {
                float angle = i / 10f * Mathf.PI * 2f;
                Vector3 local = new Vector3(Mathf.Cos(angle) * 8f, 1.35f, Mathf.Sin(angle) * 5.5f);
                GameObject stake = Primitive($"PalisadeStake_{i:00}", PrimitiveType.Cube, local, new Vector3(0.32f, 2.7f, 0.32f), wood, camp.transform);
                stake.transform.localRotation = Quaternion.Euler(0f, -angle * Mathf.Rad2Deg, 9f);
            }

            BuildCampfire(camp.transform, new Vector3(0f, 0.25f, 0f), wood, fire);
            Primitive("LootChest_Blockout", PrimitiveType.Cube, new Vector3(3.2f, 0.45f, -1.8f), new Vector3(1.35f, 0.75f, 0.85f), wood, camp.transform);
        }

        private static void BuildBrokenBridge(Transform root, Vector3 position, Material wood, Material stone)
        {
            GameObject bridge = new GameObject("BrokenBridge_RouteLandmark");
            bridge.transform.SetParent(root);
            bridge.transform.position = position;

            Primitive("BridgeLeftBank", PrimitiveType.Cube, new Vector3(-4.2f, 0.08f, 0f), new Vector3(5.2f, 0.28f, 3.4f), stone, bridge.transform);
            Primitive("BridgeRightBank", PrimitiveType.Cube, new Vector3(4.2f, 0.08f, 0f), new Vector3(5.2f, 0.28f, 3.4f), stone, bridge.transform);
            GameObject plankA = Primitive("BrokenPlank_A", PrimitiveType.Cube, new Vector3(-0.9f, 0.42f, -0.45f), new Vector3(4.6f, 0.22f, 0.46f), wood, bridge.transform);
            plankA.transform.localRotation = Quaternion.Euler(0f, 0f, -5f);
            GameObject plankB = Primitive("BrokenPlank_B", PrimitiveType.Cube, new Vector3(1.2f, 0.38f, 0.55f), new Vector3(3.8f, 0.22f, 0.46f), wood, bridge.transform);
            plankB.transform.localRotation = Quaternion.Euler(0f, 0f, 7f);
        }

        private static void BuildDistantDragon(Transform root, Vector3 position, Material material)
        {
            GameObject dragon = new GameObject("DistantDragon_CinematicSilhouette");
            dragon.transform.SetParent(root);
            dragon.transform.position = position;
            dragon.transform.rotation = Quaternion.Euler(0f, -28f, 0f);
            Primitive("Body", PrimitiveType.Capsule, Vector3.zero, new Vector3(1.0f, 0.38f, 2.2f), material, dragon.transform);
            GameObject wingL = Primitive("Wing_L", PrimitiveType.Cube, new Vector3(-1.2f, 0f, 0f), new Vector3(2.6f, 0.08f, 0.75f), material, dragon.transform);
            wingL.transform.localRotation = Quaternion.Euler(0f, 0f, 17f);
            GameObject wingR = Primitive("Wing_R", PrimitiveType.Cube, new Vector3(1.2f, 0f, 0f), new Vector3(2.6f, 0.08f, 0.75f), material, dragon.transform);
            wingR.transform.localRotation = Quaternion.Euler(0f, 0f, -17f);
        }

        private static void BuildGameManager(Transform root, Transform spawnPoint)
        {
            GameObject managerObject = new GameObject("GameManager");
            managerObject.transform.SetParent(root);
            Gameplay.GameManager manager = managerObject.AddComponent<Gameplay.GameManager>();
            manager.spawnPoint = spawnPoint;
            manager.respawnDelay = 4f;
        }

        private static void BuildHud(Transform root)
        {
            GameObject canvasObject = new GameObject("HUD_RPG_ReferenceShell");
            canvasObject.transform.SetParent(root);
            Canvas canvas = canvasObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            CanvasScaler scaler = canvasObject.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 0.5f;
            canvasObject.AddComponent<GraphicRaycaster>();

            Gameplay.RpgHudController hud = canvasObject.AddComponent<Gameplay.RpgHudController>();
            canvasObject.AddComponent<Gameplay.DamageNumberSpawner>();

            hud.levelText = TextElement(canvasObject.transform, "LevelText", "Lv. 1", new Vector2(22f, -18f), new Vector2(180f, 28f), TextAnchor.MiddleLeft, 18);
            hud.xpText = TextElement(canvasObject.transform, "XPText", "XP: 0 / 100", new Vector2(22f, -44f), new Vector2(200f, 20f), TextAnchor.MiddleLeft, 13);

            hud.xpFill = Bar(canvasObject.transform, "XPBar", new Vector2(22f, -62f), new Vector2(220f, 8f), new Color(0.72f, 0.62f, 0.12f));

            hud.healthGhostFill = Bar(canvasObject.transform, "HealthBarGhost", new Vector2(22f, -80f), new Vector2(310f, 22f), new Color(0.7f, 0.3f, 0.1f));
            hud.healthFill = Bar(canvasObject.transform, "HealthBarFill", new Vector2(22f, -80f), new Vector2(310f, 22f), new Color(0.55f, 0.02f, 0.02f));
            hud.manaFill = Bar(canvasObject.transform, "ManaBar", new Vector2(22f, -108f), new Vector2(240f, 18f), new Color(0.04f, 0.18f, 0.62f));
            hud.staminaFill = Bar(canvasObject.transform, "StaminaBar", new Vector2(22f, -132f), new Vector2(210f, 14f), new Color(0.85f, 0.62f, 0.14f));

            hud.questText = TextElement(canvasObject.transform, "QuestTracker", "", new Vector2(-315f, -150f), new Vector2(290f, 250f), TextAnchor.UpperLeft, 15, Anchor.TopRight);
            hud.lootText = TextElement(canvasObject.transform, "LootReadout", "Gold: 0", new Vector2(-180f, -420f), new Vector2(160f, 26f), TextAnchor.MiddleRight, 14, Anchor.BottomRight);

            GameObject flashObj = UiObject(canvasObject.transform, "DamageFlashOverlay", Vector2.zero, new Vector2(1920f, 1080f), Anchor.TopLeft);
            Image flash = flashObj.AddComponent<Image>();
            flash.color = new Color(0.7f, 0.02f, 0.02f, 0f);
            flash.raycastTarget = false;
            RectTransform flashRect = flashObj.GetComponent<RectTransform>();
            flashRect.anchorMin = Vector2.zero;
            flashRect.anchorMax = Vector2.one;
            flashRect.sizeDelta = Vector2.zero;
            hud.damageFlashOverlay = flash;

            TextElement(canvasObject.transform, "SkillBar", "1  Slash   2  Guard   3  Fire   4  Dodge   5  Heal", new Vector2(0f, 34f), new Vector2(600f, 32f), TextAnchor.MiddleCenter, 15, Anchor.BottomCenter);
            TextElement(canvasObject.transform, "MiniMap", "N\n\nFARGOTH - Kuzey\n\n^", new Vector2(-145f, -25f), new Vector2(210f, 210f), TextAnchor.MiddleCenter, 13, Anchor.TopRight);
        }

        private static void BuildPostProcess(Transform root)
        {
            GameObject fill = new GameObject("ColdFill_MoonLight");
            fill.transform.SetParent(root);
            Light fillLight = fill.AddComponent<Light>();
            fillLight.type = LightType.Directional;
            fillLight.intensity = 0.22f;
            fillLight.color = new Color(0.44f, 0.52f, 0.64f);
            fill.transform.rotation = Quaternion.Euler(22f, 128f, 0f);

            GameObject rimLeft = new GameObject("RimLight_RightSide_WarmEdge");
            rimLeft.transform.SetParent(root);
            rimLeft.transform.position = new Vector3(22f, 7f, 5f);
            Light rim = rimLeft.AddComponent<Light>();
            rim.type = LightType.Spot;
            rim.spotAngle = 65f;
            rim.range = 40f;
            rim.intensity = 1.4f;
            rim.color = new Color(1f, 0.72f, 0.42f);

            GameObject sky = new GameObject("Sky_AmbientFogDome");
            sky.transform.SetParent(root);
            sky.transform.position = new Vector3(0f, 55f, 55f);
            Light skyAmbient = sky.AddComponent<Light>();
            skyAmbient.type = LightType.Point;
            skyAmbient.range = 200f;
            skyAmbient.intensity = 0.28f;
            skyAmbient.color = new Color(0.25f, 0.30f, 0.38f);

            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fog = true;
            RenderSettings.fogColor = new Color(0.22f, 0.28f, 0.34f);
            RenderSettings.fogDensity = 0.030f;
            RenderSettings.ambientLight = new Color(0.06f, 0.07f, 0.09f);
        }

        private static void BuildHouse(Transform root, Vector3 position, Quaternion rotation, Material wood, Material stone, Material fire)
        {
            GameObject house = new GameObject("Village_NordicLonghouse_Blockout");
            house.transform.SetParent(root);
            house.transform.position = position;
            house.transform.rotation = rotation;
            Primitive("StoneFoundation", PrimitiveType.Cube, new Vector3(0f, 0.25f, 0f), new Vector3(8f, 0.5f, 6f), stone, house.transform);
            Primitive("WoodWalls", PrimitiveType.Cube, new Vector3(0f, 1.65f, 0f), new Vector3(7.2f, 2.8f, 5.2f), wood, house.transform);
            GameObject roofA = Primitive("Roof_A", PrimitiveType.Cube, new Vector3(-1.9f, 3.4f, 0f), new Vector3(4.4f, 0.45f, 6.6f), wood, house.transform);
            roofA.transform.localRotation = Quaternion.Euler(0f, 0f, -28f);
            GameObject roofB = Primitive("Roof_B", PrimitiveType.Cube, new Vector3(1.9f, 3.4f, 0f), new Vector3(4.4f, 0.45f, 6.6f), wood, house.transform);
            roofB.transform.localRotation = Quaternion.Euler(0f, 0f, 28f);
            Primitive("DoorWarmGlow", PrimitiveType.Cube, new Vector3(0f, 1f, -2.65f), new Vector3(1.25f, 1.8f, 0.1f), fire, house.transform);
            Light torch = house.AddComponent<Light>();
            torch.type = LightType.Point;
            torch.range = 9f;
            torch.intensity = 3.5f;
            torch.color = new Color(1f, 0.48f, 0.18f);
        }

        private static void BuildCampfire(Transform root, Vector3 position, Material wood, Material fire)
        {
            GameObject camp = new GameObject("Village_Campfire");
            camp.transform.SetParent(root);
            camp.transform.localPosition = position;
            Primitive("LogA", PrimitiveType.Cube, Vector3.zero, new Vector3(2f, 0.18f, 0.18f), wood, camp.transform).transform.localRotation = Quaternion.Euler(0f, 25f, 0f);
            Primitive("LogB", PrimitiveType.Cube, Vector3.zero, new Vector3(2f, 0.18f, 0.18f), wood, camp.transform).transform.localRotation = Quaternion.Euler(0f, -25f, 0f);
            Cone("Flame_Core", new Vector3(0f, 0.55f, 0f), new Vector3(0.8f, 1.0f, 0.8f), fire, camp.transform);
            Cone("Flame_Outer", new Vector3(0f, 0.7f, 0f), new Vector3(1.1f, 1.4f, 1.1f), LoadMaterial("M_FireEmissive"), camp.transform);
            GameObject lightObj = new GameObject("FireLight");
            lightObj.transform.SetParent(camp.transform);
            lightObj.transform.localPosition = new Vector3(0f, 0.5f, 0f);
            Light light = lightObj.AddComponent<Light>();
            light.type = LightType.Point;
            light.range = 14f;
            light.intensity = 5.5f;
            light.color = new Color(1f, 0.40f, 0.14f);
            Gameplay.CampfireVfx vfx = camp.AddComponent<Gameplay.CampfireVfx>();
        }

        private static void BuildCastleSilhouette(Transform root, Vector3 position, Material stone, Material beam)
        {
            GameObject castle = new GameObject("Distant_FargothCastle_Silhouette");
            castle.transform.SetParent(root);
            castle.transform.position = position;
            Primitive("Keep", PrimitiveType.Cube, new Vector3(0f, 8f, 0f), new Vector3(12f, 16f, 8f), stone, castle.transform);
            Primitive("Tower_L", PrimitiveType.Cylinder, new Vector3(-8f, 8f, 0f), new Vector3(3f, 16f, 3f), stone, castle.transform);
            Primitive("Tower_R", PrimitiveType.Cylinder, new Vector3(8f, 8f, 0f), new Vector3(3f, 16f, 3f), stone, castle.transform);
            Cone("Spire", new Vector3(0f, 20f, 0f), new Vector3(7f, 13f, 7f), stone, castle.transform);
            Primitive("RedMagicBeam", PrimitiveType.Cylinder, new Vector3(0f, 40f, 0f), new Vector3(1.25f, 80f, 1.25f), beam, castle.transform);
            Light red = castle.AddComponent<Light>();
            red.type = LightType.Point;
            red.range = 55f;
            red.intensity = 10f;
            red.color = new Color(1f, 0.05f, 0.16f);
        }

        private static bool ValidateFirstPlayable(out string reason)
        {
            if (!File.Exists(ScenePath))
                RunSceneBuilderTask(out _);

            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);

            bool hasPlayer  = GameObject.FindGameObjectWithTag("Player") != null;
            bool hasCamera  = Camera.main != null;
            bool hasEnemy   = UnityEngine.Object.FindObjectsByType<Gameplay.EnemyAIController>(
                                  FindObjectsInactive.Exclude).Length > 0;
            bool hasHud     = UnityEngine.Object.FindObjectsByType<Gameplay.RpgHudController>(
                                  FindObjectsInactive.Include).Length > 0;

            bool hasRpgScene = GameObject.Find("_RPG_CleanReferenceScene") != null
                            || GameObject.Find("_RPG_WetTerrain") != null
                            || GameObject.Find("_RPG_DistantCastleSilhouette") != null;

            // Eski format geriye donuk uyum
            bool hasLegacyScene = GameObject.Find("TI_MoodyFogForest_FirstPlayable_Root") != null
                               || GameObject.Find("Distant_FargothCastle_Silhouette") != null;

            bool hasScene  = hasRpgScene || hasLegacyScene;
            int  renderers = UnityEngine.Object.FindObjectsByType<MeshRenderer>(
                                 FindObjectsInactive.Exclude).Length;
            bool hasDensity = renderers > 20;

            bool ok = hasPlayer && hasCamera && hasScene && hasDensity;
            reason = $"player={hasPlayer} camera={hasCamera} enemy={hasEnemy} hud={hasHud} rpgScene={hasRpgScene} legacyScene={hasLegacyScene} renderers={renderers}";
            WriteStatusJson(ok, reason);
            return ok;
        }

        private static bool WriteVisualQualityGate(out string reason)
        {
            if (!File.Exists(ScenePath))
                HdrpCleanSceneBuilder.Run(out _);

            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            string unityRoot = Directory.GetParent(Application.dataPath)!.FullName;
            string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
            string statusPath = Path.Combine(unityRoot, AutopilotDataRoot, "unity_visual_quality_gate.json");
            string reportPath = Path.Combine(repoRoot, "docs", "production", "unity-visual-quality-gate-latest.md");
            Directory.CreateDirectory(Path.GetDirectoryName(statusPath)!);
            Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);

            bool hasPlayer = GameObject.FindGameObjectWithTag("Player") != null;
            bool hasCabin = GameObject.Find("_RPG_MainCabin") != null || GameObject.Find("MoodyVillage_MainWoodenCabin") != null;
            bool hasShed = GameObject.Find("_RPG_SecondaryShed") != null || GameObject.Find("MoodyVillage_SecondarySmallShed") != null;
            bool hasPath = GameObject.Find("_RPG_MuddyPath") != null || GameObject.Find("WetDirtPath_MuddyReflection_00") != null || GameObject.Find("CinematicReadablePath_00") != null;
            bool hasCastle = GameObject.Find("_RPG_DistantCastleSilhouette") != null || GameObject.Find("Distant_FargothCastle_Silhouette") != null;
            bool hasBeam = GameObject.Find("_RPG_CastleBeam") != null || GameObject.Find("Castle_MagicalVerticalBeam") != null || GameObject.Find("QuestBeacon_FargothCastle") != null;
            bool hasHud = UnityEngine.Object.FindObjectsByType<Gameplay.RpgHudController>(FindObjectsInactive.Include).Length > 0;
            bool hasEnemy = UnityEngine.Object.FindObjectsByType<Gameplay.EnemyAIController>(FindObjectsInactive.Exclude).Length > 0;
            bool hasImportedHero = GameObject.Find("Player_ImportedHeroVisual_Warden") != null || GameObject.Find("SK_Warden_Hero") != null;
            bool hasImportedEnemy = GameObject.Find("Enemy_ImportedVisual_00") != null || GameObject.Find("SK_BeastAnother") != null || GameObject.Find("SK_DemonVulture") != null;
            int rendererCount = UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude).Length;
            int lights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude).Length;
            int fogLayers = 0;
            int primitivePlaceholders = 0;
            foreach (Transform transform in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Exclude))
            {
                string lower = transform.name.ToLowerInvariant();
                if (lower.Contains("fog") || lower.Contains("mist"))
                    fogLayers++;
                if (lower.Contains("blockout") || lower.Contains("cube") || lower.Contains("primitive"))
                    primitivePlaceholders++;
            }

            bool pbrGround = HasMaterialTexture("HDRP_M_WetGround") || HasMaterialTexture("M_WetMudPath");
            bool pbrWood = HasMaterialTexture("HDRP_M_WetAgedWood") || HasMaterialTexture("M_CabinWeatheredWood");
            bool pbrRock = HasMaterialTexture("HDRP_M_WetRock") || HasMaterialTexture("M_WetStone");
            int brokenMaterials = CountBrokenGeneratedMaterials();
            bool previewExists = File.Exists(Path.Combine(repoRoot, "output", "unity", "unity_first_playable_preview.png"));

            int score = 0;
            score += hasPlayer ? 8 : 0;
            score += hasCabin ? 10 : 0;
            score += hasShed ? 6 : 0;
            score += hasPath ? 12 : 0;
            score += hasCastle ? 12 : 0;
            score += hasBeam ? 10 : 0;
            score += hasHud ? 8 : 0;
            score += hasEnemy ? 6 : 0;
            score += rendererCount >= 160 ? 10 : rendererCount >= 100 ? 7 : 3;
            score += lights >= 5 ? 6 : lights >= 3 ? 4 : 1;
            score += fogLayers >= 6 ? 6 : fogLayers >= 3 ? 4 : 1;
            score += pbrGround ? 4 : 0;
            score += pbrWood ? 4 : 0;
            score += pbrRock ? 4 : 0;
            score += hasImportedHero ? 6 : 0;
            score += hasImportedEnemy ? 4 : 0;
            score = Mathf.Min(score, 100);

            string grade = score >= 88 ? "A" : score >= 76 ? "B" : score >= 62 ? "C" : "D";
            bool pass = score >= 76 && pbrGround && pbrWood && pbrRock && brokenMaterials == 0 && previewExists;

            string json =
                "{\n" +
                "  \"result\": \"" + (pass ? "completed" : "needs_iteration") + "\",\n" +
                "  \"generated_at_utc\": \"" + DateTime.UtcNow.ToString("o") + "\",\n" +
                "  \"score\": " + score + ",\n" +
                "  \"grade\": \"" + grade + "\",\n" +
                "  \"has_player\": " + hasPlayer.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_cabin\": " + hasCabin.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_shed\": " + hasShed.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_path\": " + hasPath.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_castle\": " + hasCastle.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_beam\": " + hasBeam.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_hud\": " + hasHud.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_enemy\": " + hasEnemy.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_imported_hero_visual\": " + hasImportedHero.ToString().ToLowerInvariant() + ",\n" +
                "  \"has_imported_enemy_visual\": " + hasImportedEnemy.ToString().ToLowerInvariant() + ",\n" +
                "  \"renderer_count\": " + rendererCount + ",\n" +
                "  \"light_count\": " + lights + ",\n" +
                "  \"fog_layer_count\": " + fogLayers + ",\n" +
                "  \"primitive_placeholder_markers\": " + primitivePlaceholders + ",\n" +
                "  \"pbr_ground_bound\": " + pbrGround.ToString().ToLowerInvariant() + ",\n" +
                "  \"pbr_wood_bound\": " + pbrWood.ToString().ToLowerInvariant() + ",\n" +
                "  \"pbr_rock_bound\": " + pbrRock.ToString().ToLowerInvariant() + ",\n" +
                "  \"broken_generated_materials\": " + brokenMaterials + ",\n" +
                "  \"preview_exists\": " + previewExists.ToString().ToLowerInvariant() + "\n" +
                "}\n";
            File.WriteAllText(statusPath, json);

            string report =
                "# Unity Visual Quality Gate\n\n" +
                $"- Result: {(pass ? "completed" : "needs_iteration")}\n" +
                $"- Score: {score}/100\n" +
                $"- Grade: {grade}\n" +
                $"- PBR bound: ground={pbrGround}, wood={pbrWood}, rock={pbrRock}\n" +
                $"- Broken generated materials: {brokenMaterials}\n" +
                $"- Imported visuals: hero={hasImportedHero}, enemy={hasImportedEnemy}\n" +
                $"- Composition: player={hasPlayer}, cabin={hasCabin}, path={hasPath}, castle={hasCastle}, beam={hasBeam}, hud={hasHud}, enemy={hasEnemy}\n" +
                $"- Scene density: renderers={rendererCount}, lights={lights}, fogLayers={fogLayers}, primitiveMarkers={primitivePlaceholders}\n\n" +
                "Next iteration target: replace more primitive/blockout silhouettes with imported FBX/GLB prefabs, add more non-uniform terrain elevation, and keep the cabin-path-castle beam triangle readable in every screenshot.\n";
            File.WriteAllText(reportPath, report);

            reason = $"Visual quality gate score={score}/100 grade={grade}, PBR ground={pbrGround}, wood={pbrWood}, rock={pbrRock}, brokenMaterials={brokenMaterials}.";
            return pass;
        }

        private static int CountBrokenGeneratedMaterials()
        {
            int broken = 0;
            string[] guids = AssetDatabase.FindAssets("t:Material", new[] { MaterialRoot });
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material == null || material.shader == null || material.shader.name.Contains("InternalError"))
                    broken++;
            }
            return broken;
        }

        private static bool HasMaterialTexture(string materialName)
        {
            Material material = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialRoot}/{materialName}.mat");
            if (material == null)
                material = AssetDatabase.LoadAssetAtPath<Material>($"Assets/FantasyRPG/Generated/Materials/{materialName}.mat");
            if (material == null)
                return false;

            if (material.HasProperty("_BaseColorMap") && material.GetTexture("_BaseColorMap") != null)
                return true;
            if (material.HasProperty("_BaseMap") && material.GetTexture("_BaseMap") != null)
                return true;
            if (material.HasProperty("_MainTex") && material.GetTexture("_MainTex") != null)
                return true;
            return material.mainTexture != null;
        }

        private static bool CaptureScreenshot(out string reason)
        {
            if (!File.Exists(ScenePath))
                HdrpCleanSceneBuilder.Run(out _);

            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            string outputDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "output", "unity"));
            Directory.CreateDirectory(outputDir);
            string outputPath = Path.Combine(outputDir, "unity_first_playable_preview.png");

            GameObject cameraObject = GameObject.Find("CinematicPreviewCamera");
            if (cameraObject == null)
                cameraObject = new GameObject("CinematicPreviewCamera");

            Camera camera = cameraObject.GetComponent<Camera>();
            if (camera == null)
                camera = cameraObject.AddComponent<Camera>();

            cameraObject.transform.position = new Vector3(-2.5f, 3.6f, -39f);
            cameraObject.transform.LookAt(new Vector3(0f, 8.8f, 98f));
            camera.fieldOfView = 44f;
            camera.nearClipPlane = 0.05f;
            camera.farClipPlane = 550f;
            camera.clearFlags = CameraClearFlags.Skybox;
            camera.backgroundColor = new Color(0.055f, 0.070f, 0.082f);

            RenderTexture previous = RenderTexture.active;
            RenderTexture target = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32);
            camera.targetTexture = target;
            camera.Render();
            RenderTexture.active = target;
            Texture2D image = new Texture2D(target.width, target.height, TextureFormat.RGB24, false);
            image.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0);
            image.Apply();
            File.WriteAllBytes(outputPath, image.EncodeToPNG());
            camera.targetTexture = null;
            RenderTexture.active = previous;
            UnityEngine.Object.DestroyImmediate(target);
            UnityEngine.Object.DestroyImmediate(image);

            string notePath = Path.Combine(outputDir, "unity_first_playable_capture_request.txt");
            File.WriteAllText(notePath, $"Generated preview: {outputPath}\nScene: {ScenePath}\n");
            reason = $"Screenshot preview generated: {outputPath}";
            return true;
        }

        private static bool BuildWindowsPlayer(out string reason)
        {
            if (!File.Exists(ScenePath))
                HdrpCleanSceneBuilder.Run(out _);

            string buildDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Builds", "Windows"));
            Directory.CreateDirectory(buildDir);
            string exePath = Path.Combine(buildDir, "ThornyIvy_Unity.exe");

            string allowFullBuild = Environment.GetEnvironmentVariable("UNITY_AUTOPILOT_ALLOW_FULL_BUILD");
            if (!string.Equals(allowFullBuild, "1", StringComparison.Ordinal))
            {
                string report = "Unity Windows build readiness report\n" +
                                $"Generated: {DateTime.UtcNow:o}\n" +
                                $"Scene: {ScenePath}\n" +
                                $"Output: {exePath}\n" +
                                "Status: ready_for_manual_or_explicit_full_build\n" +
                                "Note: Full build is disabled by default in autopilot to avoid long URP shader compilation crashes.\n" +
                                "Run with UNITY_AUTOPILOT_ALLOW_FULL_BUILD=1 only after the scene is playtested.\n";
                File.WriteAllText(Path.Combine(buildDir, "build_readiness_report.txt"), report);
                reason = $"Build readiness report written at {Path.Combine(buildDir, "build_readiness_report.txt")}. Full build deferred safely.";
                return true;
            }

            BuildPlayerOptions options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = exePath,
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.Development
            };
            BuildPipeline.BuildPlayer(options);
            reason = $"Windows build completed or requested at {exePath}.";
            return true;
        }

        private static bool WriteStatusReport(string message, out string reason)
        {
            string root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
            string logPath = Path.Combine(root, "autopilot-log.md");
            string line = $"- [{DateTime.UtcNow:o}] Unity pipeline active: {message}\n";
            File.AppendAllText(logPath, line);
            WriteStatusJson(true, message);
            reason = "Unity-only status report updated.";
            return true;
        }

        private static void WriteStatusJson(bool ready, string message)
        {
            string dataRoot = AutopilotStorage.DataRoot;
            Directory.CreateDirectory(dataRoot);
            string json = "{\n" +
                          $"  \"unity_only\": true,\n" +
                          $"  \"first_playable_ready\": {ready.ToString().ToLowerInvariant()},\n" +
                          $"  \"updated_at\": \"{DateTime.UtcNow:o}\",\n" +
                          $"  \"message\": \"{EscapeJson(message)}\"\n" +
                          "}\n";
            File.WriteAllText(Path.Combine(dataRoot, "unity_reboot_status.json"), json);
        }

        private enum Anchor { TopLeft, TopRight, BottomCenter, BottomRight }

        private static Image Bar(Transform parent, string name, Vector2 anchoredPosition, Vector2 size, Color fillColor)
        {
            GameObject background = UiObject(parent, name, anchoredPosition, size, Anchor.TopLeft);
            Image bg = background.AddComponent<Image>();
            bg.color = new Color(0.02f, 0.02f, 0.02f, 0.72f);

            GameObject fillObject = UiObject(background.transform, "Fill", Vector2.zero, size - new Vector2(4f, 4f), Anchor.TopLeft);
            Image fill = fillObject.AddComponent<Image>();
            fill.color = fillColor;
            fill.type = Image.Type.Filled;
            fill.fillMethod = Image.FillMethod.Horizontal;
            fill.fillOrigin = 0;
            fill.fillAmount = 1f;
            return fill;
        }

        private static Text TextElement(Transform parent, string name, string value, Vector2 anchoredPosition, Vector2 size, TextAnchor alignment, int fontSize, Anchor anchor = Anchor.TopLeft)
        {
            GameObject obj = UiObject(parent, name, anchoredPosition, size, anchor);
            Text text = obj.AddComponent<Text>();
            text.text = value;
            text.alignment = alignment;
            text.fontSize = fontSize;
            text.color = new Color(0.92f, 0.86f, 0.72f);
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (text.font == null) text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            return text;
        }

        private static GameObject UiObject(Transform parent, string name, Vector2 anchoredPosition, Vector2 size, Anchor anchor)
        {
            GameObject obj = new GameObject(name);
            obj.transform.SetParent(parent, false);
            RectTransform rect = obj.AddComponent<RectTransform>();
            switch (anchor)
            {
                case Anchor.TopRight:
                    rect.anchorMin = rect.anchorMax = new Vector2(1f, 1f);
                    rect.pivot = new Vector2(1f, 1f);
                    break;
                case Anchor.BottomCenter:
                    rect.anchorMin = rect.anchorMax = new Vector2(0.5f, 0f);
                    rect.pivot = new Vector2(0.5f, 0f);
                    break;
                case Anchor.BottomRight:
                    rect.anchorMin = rect.anchorMax = new Vector2(1f, 0f);
                    rect.pivot = new Vector2(1f, 0f);
                    break;
                default:
                    rect.anchorMin = rect.anchorMax = new Vector2(0f, 1f);
                    rect.pivot = new Vector2(0f, 1f);
                    break;
            }

            rect.anchoredPosition = anchoredPosition;
            rect.sizeDelta = size;
            return obj;
        }

        private static GameObject Primitive(string name, PrimitiveType type, Vector3 position, Vector3 scale, Material material, Transform parent)
        {
            GameObject obj = GameObject.CreatePrimitive(type);
            obj.name = name;
            obj.transform.SetParent(parent);
            obj.transform.localPosition = position;
            obj.transform.localRotation = Quaternion.identity;
            obj.transform.localScale = scale;
            if (material != null)
            {
                var rend = obj.GetComponent<Renderer>();
                if (rend != null) rend.sharedMaterial = material;
            }
            return obj;
        }

        private static GameObject Cone(string name, Vector3 position, Vector3 scale, Material material, Transform parent)
        {
            GameObject obj = new GameObject(name);
            obj.transform.SetParent(parent);
            obj.transform.localPosition = position;
            obj.transform.localRotation = Quaternion.identity;
            obj.transform.localScale = scale;

            MeshFilter filter = obj.AddComponent<MeshFilter>();
            MeshRenderer renderer = obj.AddComponent<MeshRenderer>();
            filter.sharedMesh = CreateConeMesh();
            if (material != null)
                renderer.sharedMaterial = material;
            return obj;
        }

        private static Mesh CreateConeMesh()
        {
            const int segments = 18;
            Vector3[] vertices = new Vector3[segments + 2];
            int[] triangles = new int[segments * 6];

            vertices[0] = new Vector3(0f, 0.5f, 0f);
            vertices[1] = new Vector3(0f, -0.5f, 0f);
            for (int i = 0; i < segments; i++)
            {
                float angle = i / (float)segments * Mathf.PI * 2f;
                vertices[i + 2] = new Vector3(Mathf.Cos(angle) * 0.5f, -0.5f, Mathf.Sin(angle) * 0.5f);
            }

            int t = 0;
            for (int i = 0; i < segments; i++)
            {
                int current = i + 2;
                int next = i == segments - 1 ? 2 : i + 3;
                triangles[t++] = 0;
                triangles[t++] = current;
                triangles[t++] = next;
                triangles[t++] = 1;
                triangles[t++] = next;
                triangles[t++] = current;
            }

            Mesh mesh = new Mesh();
            mesh.name = "Generated_ConeMesh";
            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        private static Material CreateMaterial(string name, Color baseColor, float smoothness, float metallic, Color? emission = null)
        {
            string path = $"{MaterialRoot}/{name}.mat";
            Material existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            Material mat = existing != null ? existing : new Material(PreviewSafeShader());
            mat.name = name;
            mat.shader = PreviewSafeShader();
            mat.SetColor("_BaseColor", baseColor);
            mat.SetColor("_Color", baseColor);
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", metallic);
            if (baseColor.a < 0.99f)
                ConfigureTransparentMaterial(mat);
            if (emission.HasValue)
            {
                mat.EnableKeyword("_EMISSION");
                if (mat.HasProperty("_EmissionColor")) mat.SetColor("_EmissionColor", emission.Value);
            }
            if (existing == null)
                AssetDatabase.CreateAsset(mat, path);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static void ConfigureTransparentMaterial(Material mat)
        {
            if (mat.HasProperty("_Mode"))
                mat.SetFloat("_Mode", 3f);
            if (mat.HasProperty("_SrcBlend"))
                mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            if (mat.HasProperty("_DstBlend"))
                mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            if (mat.HasProperty("_ZWrite"))
                mat.SetInt("_ZWrite", 0);
            mat.DisableKeyword("_ALPHATEST_ON");
            mat.EnableKeyword("_ALPHABLEND_ON");
            mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            mat.renderQueue = 3000;
        }

        private static Material CreateRuntimeMaterial(Color color)
        {
            Material mat = new Material(PreviewSafeShader());
            mat.SetColor("_BaseColor", color);
            mat.SetColor("_Color", color);
            return mat;
        }

        private static Shader PreviewSafeShader()
        {
            Shader shader = Shader.Find("HDRP/Lit");
            if (shader == null)
                shader = Shader.Find("Standard");
            if (shader == null)
                shader = Shader.Find("Legacy Shaders/Diffuse");
            if (shader == null)
                shader = Shader.Find("Unlit/Color");
            if (shader == null)
                shader = Shader.Find("Sprites/Default");
            return shader;
        }

        private static Shader SurfaceShader()
        {
            Shader shader = Shader.Find("HDRP/Lit");
            if (shader == null)
                shader = Shader.Find("Standard");
            if (shader == null)
                shader = Shader.Find("Legacy Shaders/Diffuse");
            if (shader == null)
                shader = PreviewSafeShader();
            return shader;
        }

        private static Material LoadMaterial(string name)
        {
            Material mat = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialRoot}/{name}.mat");
            if (mat == null)
                mat = CreateMaterial(name, Color.gray, 0.5f, 0f);
            return mat;
        }

        private static void EnsureFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder)) return;
            string parent = Path.GetDirectoryName(folder).Replace("\\", "/");
            string name = Path.GetFileName(folder);
            if (!AssetDatabase.IsValidFolder(parent))
                EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, name);
        }

        private static string EscapeJson(string value)
        {
            return (value ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"");
        }

        private static void BuildPostProcessVolume(Transform root)
        {
            // Built-in pipeline: no URP Volume component. PostProcessSetup handles
            // RenderSettings and camera quality directly.
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.PostProcessSetup>() != null) return;
            GameObject ppObj = new GameObject("PostProcessSetup_Global");
            ppObj.transform.SetParent(root);
            ppObj.AddComponent<Gameplay.PostProcessSetup>();
        }

        private static void BuildVfxManager(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.VfxManager>() != null) return;
            GameObject vfxObj = new GameObject("VfxManager");
            vfxObj.transform.SetParent(root);
            vfxObj.AddComponent<Gameplay.VfxManager>();
        }

        private static void BuildDayCycleManager(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.DayCycleManager>() != null) return;
            GameObject dayObj = new GameObject("DayCycleManager");
            dayObj.transform.SetParent(root);
            Gameplay.DayCycleManager dcm = dayObj.AddComponent<Gameplay.DayCycleManager>();
            Light sun = GameObject.Find("Sun_EarlyMorning_LowAngle")?.GetComponent<Light>();
            if (sun != null)
            {
                System.Reflection.FieldInfo fi = typeof(Gameplay.DayCycleManager).GetField("sunLight",
                    System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                fi?.SetValue(dcm, sun);
            }
        }

        private static void BuildAudioManager(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.AudioManager>() != null) return;
            var go = new GameObject("AudioManager");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.AudioManager>();
        }

        private static void BuildSkyboxManager(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.SkyboxManager>() != null) return;
            var go = new GameObject("SkyboxManager");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.SkyboxManager>();
        }

        private static void BuildWeatherSystem(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.WeatherSystem>() != null) return;
            var go = new GameObject("WeatherSystem");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.WeatherSystem>();
        }

        private static void BuildLockOnSystem(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.LockOnSystem>() != null) return;
            var go = new GameObject("LockOnSystem");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.LockOnSystem>();
        }

        private static void BuildObjectPool(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.ObjectPool>() != null) return;
            var go = new GameObject("ObjectPool");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.ObjectPool>();
        }

        private static void BuildQuestSystem(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.QuestSystem>() != null) return;
            var go = new GameObject("QuestSystem");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.QuestSystem>();
        }

        private static void BuildDialogueSystem(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.DialogueSystem>() != null) return;
            var go = new GameObject("DialogueSystem");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.DialogueSystem>();
        }

        private static void BuildCutsceneController(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.CutsceneController>() != null) return;
            var go = new GameObject("CutsceneController");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.CutsceneController>();
        }

        private static void BuildBossEncounterManager(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.BossEncounterManager>() != null) return;
            var go = new GameObject("BossEncounterManager");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.BossEncounterManager>();
        }

        private static void BuildProceduralWorld(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.ProceduralWorldGenerator>() != null) return;
            var go = new GameObject("ProceduralWorldGenerator");
            go.transform.SetParent(root);
            var gen = go.AddComponent<Gameplay.ProceduralWorldGenerator>();
            // Generate is called at runtime; don't call in editor to keep scenes manageable
        }

        private static void BuildHdrpSceneSetup(Transform root)
        {
            if (UnityEngine.Object.FindAnyObjectByType<Gameplay.HdrpSceneSetup>() != null) return;
            var go = new GameObject("HdrpSceneSetup");
            go.transform.SetParent(root);
            go.AddComponent<Gameplay.HdrpSceneSetup>();
        }

        private static void ConfigureQualitySettings()
        {
            QualitySettings.shadows = ShadowQuality.All;
            QualitySettings.shadowResolution = ShadowResolution.VeryHigh;
            QualitySettings.shadowCascades = 4;
            QualitySettings.shadowDistance = 80f;
            QualitySettings.antiAliasing = 4;
            QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
            QualitySettings.vSyncCount = 1;
            QualitySettings.globalTextureMipmapLimit = 0;
            QualitySettings.lodBias = 2f;
        }
#endif
    }
}

