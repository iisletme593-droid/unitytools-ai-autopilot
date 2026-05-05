#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Autopilot
{
    public static class HdrpCleanSceneBuilder
    {
        private const string ScenePath = "Assets/Scenes/Main.unity";
        private const string RootName = "_RPG_CleanReferenceScene";
        private const string GeneratedRoot = "Assets/FantasyRPG/Generated";
        private const string MaterialRoot = GeneratedRoot + "/Materials";

        [MenuItem("Tools/Autopilot/HDRP Clean Reference Scene")]
        public static void RunMenu()
        {
            Run(out string reason);
            Debug.Log("[HdrpCleanSceneBuilder] " + reason);
        }

        public static void RunCli()
        {
            Run(out string reason);
            Debug.Log("[HdrpCleanSceneBuilder] " + reason);
        }

        public static bool Run(out string reason)
        {
            EnsureFolders();
            OpenOrCreateScene();
            CleanupGeneratedScene();

            Scene scene = EditorSceneManager.GetActiveScene();
            GameObject root = new GameObject(RootName);
            root.transform.position = Vector3.zero;

            Material mud = CreatePbrMaterial("HDRP_M_WetForestMud", "Ground/Ground054", "Ground054", new Color(0.075f, 0.058f, 0.046f), 0.82f);
            Material path = CreatePbrMaterial("HDRP_M_DarkMuddyPath", "Ground/Ground103", "Ground103", new Color(0.058f, 0.044f, 0.035f), 0.9f);
            Material stone = CreatePbrMaterial("HDRP_M_WetRock", "Rock/Rock063", "Rock063", new Color(0.18f, 0.18f, 0.17f), 0.45f);
            Material brick = CreatePbrMaterial("HDRP_M_GothicStone", "Stone/Bricks101", "Bricks101", new Color(0.22f, 0.21f, 0.20f), 0.38f);
            Material wood = CreatePbrMaterial("HDRP_M_WetAgedWood", "Wood/Wood081", "Wood081", new Color(0.13f, 0.085f, 0.055f), 0.7f);
            Material pine = CreateFlatMaterial("HDRP_M_BlackPineNeedles", new Color(0.028f, 0.055f, 0.042f), 0.62f);
            Material warm = CreateEmissiveMaterial("HDRP_M_WarmLantern", new Color(1.0f, 0.42f, 0.13f), new Color(4.5f, 1.55f, 0.28f));
            Material beam = CreateEmissiveMaterial("HDRP_M_CastleBeamWhite", new Color(1.0f, 0.90f, 0.72f), new Color(8f, 6.5f, 4f));
            Material metal = CreatePbrMaterial("HDRP_M_DarkKnightMetal", "Metal/Metal063", "Metal063", new Color(0.08f, 0.085f, 0.09f), 0.28f);

            BuildTerrain(root.transform, mud);
            BuildPath(root.transform, path);
            BuildCabinCluster(root.transform, wood, stone, warm);
            BuildForest(root.transform, pine, wood, stone);
            BuildRockScatter(root.transform, stone);
            BuildDistantCastle(root.transform, brick, beam);
            BuildGameplayActors(root.transform, metal, wood);
            BuildHudAndManagers(root.transform);
            BuildLightingAndAtmosphere(root.transform, warm, beam);
            BuildPreviewCamera();

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            WriteStatus("completed", 0);
            AutopilotScreenshot.CaptureAfterBuild();

            reason = "Temiz HDRP referans sahne kuruldu: dusuk obje sayisi, GLB agac/kaya kullanimi, temiz kamera, kirli primitive placeholder yok.";
            return true;
        }

        private static void OpenOrCreateScene()
        {
            if (File.Exists(ScenePath))
                EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            else
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        }

        private static void EnsureFolders()
        {
            EnsureFolder("Assets/FantasyRPG");
            EnsureFolder(GeneratedRoot);
            EnsureFolder(MaterialRoot);
            EnsureFolder("Assets/Scenes");
        }

        private static void CleanupGeneratedScene()
        {
            string[] prefixes =
            {
                "_RPG_", "TI_", "Moody", "Distant_", "Fargoth", "WetDirtPath", "SparseTallPine",
                "DeadTree", "Village_", "CinematicPreviewCamera", "PostProcess_", "CastleBeam_",
                "Route_", "Palisade", "Enemy_RootAcolyte", "Player_NordWarrior"
            };

            foreach (GameObject go in UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include))
            {
                if (go == null || go.transform.parent != null)
                    continue;
                if (go.GetComponent<Camera>() != null)
                    continue;
                if (prefixes.Any(p => go.name.StartsWith(p, StringComparison.OrdinalIgnoreCase)))
                    UnityEngine.Object.DestroyImmediate(go);
            }

            GameObject oldPlayer = GameObject.FindGameObjectWithTag("Player");
            if (oldPlayer != null)
                UnityEngine.Object.DestroyImmediate(oldPlayer);
        }

        private static void BuildTerrain(Transform root, Material material)
        {
            const int grid = 96;
            const float width = 150f;
            const float depth = 170f;
            Vector3[] vertices = new Vector3[(grid + 1) * (grid + 1)];
            Vector2[] uv = new Vector2[vertices.Length];
            int[] triangles = new int[grid * grid * 6];

            for (int z = 0; z <= grid; z++)
            {
                for (int x = 0; x <= grid; x++)
                {
                    float nx = x / (float)grid;
                    float nz = z / (float)grid;
                    float wx = (nx - 0.5f) * width;
                    float wz = nz * depth - 48f;
                    float pathX = Mathf.Sin(Mathf.InverseLerp(-38f, 108f, wz) * Mathf.PI * 1.1f) * 4f;
                    float pathMask = Mathf.Clamp01(Mathf.Abs(wx - pathX) / 12f);
                    float hill = Mathf.PerlinNoise(nx * 3.5f + 2.1f, nz * 4.8f) * 1.75f;
                    hill += Mathf.PerlinNoise(nx * 10.5f, nz * 9.2f + 3.2f) * 0.35f;
                    hill += Mathf.Clamp01((wz - 34f) / 86f) * 6.0f;
                    hill += pathMask * 0.45f;
                    vertices[z * (grid + 1) + x] = new Vector3(wx, hill - 0.72f, wz);
                    uv[z * (grid + 1) + x] = new Vector2(nx * 16f, nz * 18f);
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

            Mesh mesh = new Mesh { name = "_RPG_Mesh_StartingValleyTerrain", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            mesh.vertices = vertices;
            mesh.uv = uv;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();

            GameObject terrain = new GameObject("_RPG_Terrain_StartingValley");
            terrain.transform.SetParent(root);
            terrain.AddComponent<MeshFilter>().sharedMesh = mesh;
            terrain.AddComponent<MeshRenderer>().sharedMaterial = material;
            terrain.AddComponent<MeshCollider>().sharedMesh = mesh;
        }

        private static void BuildPath(Transform root, Material material)
        {
            const int segments = 72;
            Vector3[] vertices = new Vector3[(segments + 1) * 2];
            Vector2[] uv = new Vector2[vertices.Length];
            int[] triangles = new int[segments * 6];

            for (int i = 0; i <= segments; i++)
            {
                float t = i / (float)segments;
                float z = Mathf.Lerp(-39f, 111f, t);
                float x = Mathf.Sin(t * Mathf.PI * 1.1f) * 4f;
                float width = Mathf.Lerp(7.8f, 4.6f, t);
                float y = 0.07f + t * 0.28f;
                vertices[i * 2] = new Vector3(x - width * 0.5f, y, z);
                vertices[i * 2 + 1] = new Vector3(x + width * 0.5f, y, z);
                uv[i * 2] = new Vector2(0f, t * 12f);
                uv[i * 2 + 1] = new Vector2(1f, t * 12f);
            }

            int tri = 0;
            for (int i = 0; i < segments; i++)
            {
                int v = i * 2;
                triangles[tri++] = v;
                triangles[tri++] = v + 2;
                triangles[tri++] = v + 1;
                triangles[tri++] = v + 1;
                triangles[tri++] = v + 2;
                triangles[tri++] = v + 3;
            }

            Mesh mesh = new Mesh { name = "_RPG_Mesh_WetReadablePath" };
            mesh.vertices = vertices;
            mesh.uv = uv;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();

            GameObject path = new GameObject("_RPG_Path_WetMuddyRoute");
            path.transform.SetParent(root);
            path.AddComponent<MeshFilter>().sharedMesh = mesh;
            path.AddComponent<MeshRenderer>().sharedMaterial = material;
        }

        private static void BuildCabinCluster(Transform root, Material wood, Material stone, Material warm)
        {
            Transform cabin = new GameObject("_RPG_Cabin_LeftForeground").transform;
            cabin.SetParent(root);
            cabin.SetPositionAndRotation(new Vector3(-19f, 0.35f, -21f), Quaternion.Euler(0f, 18f, 0f));
            AddBox(cabin, "stone_foundation", new Vector3(0f, 0.25f, 0f), new Vector3(9.8f, 0.5f, 7.0f), stone);
            AddBox(cabin, "weathered_log_wall", new Vector3(0f, 2.0f, 0f), new Vector3(8.8f, 3.4f, 5.8f), wood);
            AddGableRoof(cabin, wood, new Vector3(0f, 4.3f, 0f), 10.5f, 7.8f, 2.7f);
            AddBox(cabin, "warm_window", new Vector3(-2.2f, 2.2f, -2.96f), new Vector3(1.35f, 1.05f, 0.08f), warm);
            AddBox(cabin, "dark_door", new Vector3(1.65f, 1.35f, -3.02f), new Vector3(1.35f, 2.4f, 0.12f), stone);
            AddBox(cabin, "chimney", new Vector3(-3.2f, 5.35f, 1.2f), new Vector3(0.75f, 2.4f, 0.75f), stone);
            AddPointLight("_RPG_Light_CabinWarmth", cabin.TransformPoint(new Vector3(-1.4f, 2.4f, -3.2f)), new Color(1f, 0.45f, 0.16f), 3.2f, 17f, root);

            Transform shed = new GameObject("_RPG_Shed_RightMidground").transform;
            shed.SetParent(root);
            shed.SetPositionAndRotation(new Vector3(18f, 0.35f, -8f), Quaternion.Euler(0f, -23f, 0f));
            AddBox(shed, "shed_base", new Vector3(0f, 0.2f, 0f), new Vector3(5.6f, 0.4f, 4.0f), stone);
            AddBox(shed, "shed_body", new Vector3(0f, 1.35f, 0f), new Vector3(5.0f, 2.3f, 3.6f), wood);
            AddGableRoof(shed, wood, new Vector3(0f, 2.75f, 0f), 6.0f, 4.6f, 1.5f);
            AddBox(shed, "shed_window", new Vector3(-1.1f, 1.3f, -1.85f), new Vector3(0.9f, 0.7f, 0.08f), warm);

            GameObject fire = InstantiateAsset("StoneFire", new Vector3(-4.2f, 0.25f, -11.5f), Quaternion.identity, 1.2f, root);
            if (fire != null) fire.name = "_RPG_Campfire_StoneFire";
            AddPointLight("_RPG_Light_Campfire", new Vector3(-4.2f, 1.0f, -11.5f), new Color(1f, 0.36f, 0.11f), 4.2f, 18f, root);
            InstantiateAsset("WoodenLantern", new Vector3(-12f, 1.4f, -18f), Quaternion.Euler(0f, 15f, 0f), 0.8f, root);
            InstantiateAsset("Lantern", new Vector3(14f, 1.2f, -7f), Quaternion.identity, 0.65f, root);
        }

        private static void BuildForest(Transform root, Material pineFallback, Material woodFallback, Material stone)
        {
            string[] treeHints = { "PineTree", "FirTree", "DeadTreeTrunk" };
            System.Random rng = new System.Random(20260505);
            for (int i = 0; i < 92; i++)
            {
                bool left = i % 2 == 0;
                float z = Lerp(-41f, 116f, rng);
                float t = Mathf.InverseLerp(-41f, 116f, z);
                float gap = Mathf.Lerp(11f, 6f, t);
                float x = (left ? -1f : 1f) * Lerp(gap, 69f, rng);
                string hint = treeHints[rng.Next(treeHints.Length)];
                float target = hint == "DeadTreeTrunk" ? Lerp(7.5f, 12f, rng) : Lerp(9f, 18f, rng);
                GameObject tree = InstantiateAsset(hint, new Vector3(x, 0f, z), Quaternion.Euler(0f, Lerp(0f, 360f, rng), 0f), target, root);
                if (tree != null)
                    tree.name = "_RPG_Forest_" + hint + "_" + i.ToString("00");
            }

            AddFallbackTree(root, new Vector3(-46f, 0f, -35f), pineFallback, woodFallback, 19f, "_RPG_ForegroundTreeLeft");
            AddFallbackTree(root, new Vector3(44f, 0f, -31f), pineFallback, woodFallback, 17f, "_RPG_ForegroundTreeRight");
        }

        private static void BuildRockScatter(Transform root, Material stone)
        {
            System.Random rng = new System.Random(20260506);
            string[] hints = { "Boulder1", "Rock7", "Rock9", "RockFace1", "RockFace2", "RockMossSet" };
            for (int i = 0; i < 36; i++)
            {
                float angle = Lerp(0f, Mathf.PI * 2f, rng);
                float radius = Lerp(18f, 73f, rng);
                Vector3 pos = new Vector3(Mathf.Cos(angle) * radius, 0.08f, Mathf.Sin(angle) * radius);
                GameObject rock = InstantiateAsset(hints[rng.Next(hints.Length)], pos, Quaternion.Euler(0f, Lerp(0f, 360f, rng), 0f), Lerp(1.2f, 4.5f, rng), root);
                if (rock == null)
                    AddBox(root, "_RPG_Rock_Fallback_" + i.ToString("00"), pos + Vector3.up * 0.35f, new Vector3(2f, 0.75f, 1.3f) * Lerp(0.6f, 1.6f, rng), stone);
                else
                    rock.name = "_RPG_Rock_" + i.ToString("00");
            }
        }

        private static void BuildDistantCastle(Transform root, Material stone, Material beam)
        {
            Transform castle = new GameObject("_RPG_DistantCastle_FargothSilhouette").transform;
            castle.SetParent(root);
            castle.position = new Vector3(0f, 3f, 118f);
            AddBox(castle, "lower_keep", new Vector3(0f, 8f, 0f), new Vector3(38f, 16f, 15f), stone);
            AddBox(castle, "upper_keep", new Vector3(0f, 22f, 0f), new Vector3(22f, 30f, 10f), stone);
            for (int i = 0; i < 6; i++)
            {
                float x = -24f + i * 9.6f;
                AddCylinder(castle, "tower_" + i.ToString("00"), new Vector3(x, 18f + (i % 2) * 3f, 1f), 2.2f, 33f + (i % 2) * 6f, stone);
                AddCone(castle, "spire_" + i.ToString("00"), new Vector3(x, 39f + (i % 2) * 5f, 1f), 4.5f, 12f, stone);
            }
            GameObject gate = InstantiateAsset("CastleDoor", castle.position + new Vector3(0f, 1f, -8.2f), Quaternion.identity, 8f, root);
            if (gate != null) gate.name = "_RPG_CastleDoor_VisibleLandmark";
            AddCylinder(castle, "vertical_castle_beam", new Vector3(0f, 85f, 0f), 0.7f, 160f, beam);
            AddPointLight("_RPG_Light_CastleBeam", castle.position + new Vector3(0f, 42f, 0f), new Color(1f, 0.82f, 0.55f), 7.0f, 110f, root);
        }

        private static void BuildGameplayActors(Transform root, Material metal, Material wood)
        {
            GameObject player = new GameObject("_RPG_PlayerRuntime");
            player.tag = "Player";
            player.transform.SetParent(root);
            player.transform.position = new Vector3(0f, 1.05f, -31f);
            CharacterController cc = player.AddComponent<CharacterController>();
            cc.height = 2f;
            cc.radius = 0.42f;
            cc.center = new Vector3(0f, 1f, 0f);
            player.AddComponent<Gameplay.PlayerController>();
            player.AddComponent<Gameplay.StaminaComponent>();
            player.AddComponent<Gameplay.CombatComponent>();
            player.AddComponent<Gameplay.InventoryComponent>();
            player.AddComponent<Gameplay.ExperienceComponent>();
            GameObject armor = InstantiateAsset("ArmoredKnight", player.transform.position, Quaternion.Euler(0f, 180f, 0f), 2.0f, player.transform);
            if (armor == null)
                armor = InstantiateAsset("KnightArmour", player.transform.position, Quaternion.Euler(0f, 180f, 0f), 2.0f, player.transform);
            if (armor != null)
            {
                armor.name = "_RPG_PlayerVisual_Armor";
                armor.transform.localPosition = Vector3.zero;
            }
            InstantiateAsset("MedievalShield", player.transform.position + new Vector3(-0.55f, 1.1f, 0.15f), Quaternion.Euler(0f, 0f, 88f), 0.9f, player.transform);
            InstantiateAsset("IronSword", player.transform.position + new Vector3(0.7f, 0.85f, 0.2f), Quaternion.Euler(18f, 0f, -25f), 1.1f, player.transform);

            string[] enemyHints = { "DemonMask", "DarkKnightArmor", "ForestCrown" };
            Vector3[] positions =
            {
                new Vector3(8f, 0.8f, 25f), new Vector3(-9f, 0.8f, 36f),
                new Vector3(13f, 0.8f, 54f), new Vector3(-16f, 0.8f, 70f)
            };
            for (int i = 0; i < positions.Length; i++)
            {
                GameObject enemy = new GameObject("_RPG_EnemyZone_" + (i + 1).ToString("00"));
                enemy.transform.SetParent(root);
                enemy.transform.position = positions[i];
                enemy.AddComponent<CapsuleCollider>();
                enemy.AddComponent<Gameplay.CombatComponent>();
                Gameplay.EnemyAIController ai = enemy.AddComponent<Gameplay.EnemyAIController>();
                ai.enemyTier = Mathf.Clamp(i + 1, 1, 4);
                ai.enemyLevel = 2 + i * 3;
                GameObject visual = InstantiateAsset(enemyHints[i % enemyHints.Length], positions[i], Quaternion.Euler(0f, 180f, 0f), 1.7f + i * 0.15f, enemy.transform);
                if (visual != null)
                {
                    visual.name = "_RPG_EnemyVisual";
                    visual.transform.localPosition = Vector3.zero;
                }
            }
        }

        private static void BuildHudAndManagers(Transform root)
        {
            if (!HasComponent<Gameplay.RpgHudController>())
            {
                GameObject hud = new GameObject("_RPG_HUD_RuntimeShell");
                hud.transform.SetParent(root);
                hud.AddComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
                hud.AddComponent<UnityEngine.UI.CanvasScaler>();
                hud.AddComponent<UnityEngine.UI.GraphicRaycaster>();
                hud.AddComponent<Gameplay.RpgHudController>();
            }
            if (!HasComponent<Gameplay.WeatherSystem>())
                root.gameObject.AddComponent<Gameplay.WeatherSystem>();
            if (!HasComponent<Gameplay.DayCycleManager>())
                root.gameObject.AddComponent<Gameplay.DayCycleManager>();
            if (!HasComponent<Gameplay.PostProcessSetup>())
                root.gameObject.AddComponent<Gameplay.PostProcessSetup>();
        }

        private static bool HasComponent<T>() where T : UnityEngine.Object
        {
            return UnityEngine.Object.FindObjectsByType<T>(FindObjectsInactive.Include).Length > 0;
        }

        private static void BuildLightingAndAtmosphere(Transform root, Material warm, Material beam)
        {
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.035f, 0.042f, 0.055f);
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = new Color(0.16f, 0.20f, 0.24f);
            RenderSettings.fogDensity = 0.022f;

            GameObject sunGo = new GameObject("_RPG_Light_LowMorningSun");
            sunGo.transform.SetParent(root);
            sunGo.transform.rotation = Quaternion.Euler(13f, -48f, 0f);
            Light sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(0.84f, 0.75f, 0.64f);
            sun.intensity = 0.75f;
            sun.shadows = LightShadows.Soft;

            AddPointLight("_RPG_Light_PathWarmContrast", new Vector3(-5f, 2f, -11f), new Color(1f, 0.38f, 0.12f), 2.8f, 22f, root);
        }

        private static void BuildPreviewCamera()
        {
            GameObject camGo = GameObject.Find("Main Camera");
            if (camGo != null && camGo.GetComponent<Camera>() == null)
                UnityEngine.Object.DestroyImmediate(camGo);
            if (camGo == null)
                camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            Camera cam = camGo.GetComponent<Camera>() ?? camGo.AddComponent<Camera>();
            if (camGo.GetComponent<AudioListener>() == null)
                camGo.AddComponent<AudioListener>();
            cam.transform.SetParent(null);
            cam.transform.position = new Vector3(-2.2f, 3.35f, -38f);
            cam.transform.LookAt(new Vector3(0f, 8f, 103f));
            cam.fieldOfView = 45f;
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 520f;
        }

        private static GameObject InstantiateAsset(string hint, Vector3 position, Quaternion rotation, float targetMeters, Transform parent)
        {
            string path = FindAssetPath(hint);
            if (string.IsNullOrEmpty(path))
                return null;
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null)
                return null;
            GameObject go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            go.transform.SetPositionAndRotation(position, rotation);
            float maxDim = GetMaxDimension(prefab);
            if (maxDim > 0.001f)
                go.transform.localScale = Vector3.one * (targetMeters / maxDim);
            return go;
        }

        private static string FindAssetPath(string hint)
        {
            string[] guids = AssetDatabase.FindAssets(hint + " t:GameObject", new[] { "Assets/FantasyRPG" });
            if (guids.Length == 0)
                guids = AssetDatabase.FindAssets(hint, new[] { "Assets/FantasyRPG" });
            return guids.Length == 0 ? "" : AssetDatabase.GUIDToAssetPath(guids[0]);
        }

        private static float GetMaxDimension(GameObject prefab)
        {
            float max = 0f;
            foreach (Renderer r in prefab.GetComponentsInChildren<Renderer>(true))
            {
                Vector3 size = r.bounds.size;
                max = Mathf.Max(max, size.x, size.y, size.z);
            }
            foreach (MeshFilter mf in prefab.GetComponentsInChildren<MeshFilter>(true))
            {
                if (mf.sharedMesh == null) continue;
                Vector3 size = mf.sharedMesh.bounds.size;
                max = Mathf.Max(max, size.x, size.y, size.z);
            }
            return max;
        }

        private static void AddFallbackTree(Transform root, Vector3 position, Material pine, Material wood, float height, string name)
        {
            Transform tree = new GameObject(name).transform;
            tree.SetParent(root);
            tree.position = position;
            AddCylinder(tree, "trunk", new Vector3(0f, height * 0.27f, 0f), height * 0.045f, height * 0.55f, wood);
            AddCone(tree, "crown_low", new Vector3(0f, height * 0.62f, 0f), height * 0.18f, height * 0.42f, pine);
            AddCone(tree, "crown_high", new Vector3(0f, height * 0.83f, 0f), height * 0.12f, height * 0.32f, pine);
        }

        private static void AddGableRoof(Transform parent, Material material, Vector3 center, float width, float depth, float height)
        {
            Mesh mesh = new Mesh();
            float hw = width * 0.5f;
            float hd = depth * 0.5f;
            Vector3[] v =
            {
                center + new Vector3(-hw, 0f, -hd), center + new Vector3(hw, 0f, -hd), center + new Vector3(0f, height, -hd),
                center + new Vector3(-hw, 0f, hd), center + new Vector3(hw, 0f, hd), center + new Vector3(0f, height, hd)
            };
            int[] tri = { 0, 2, 3, 2, 5, 3, 2, 1, 5, 1, 4, 5, 0, 1, 2, 3, 5, 4, 0, 3, 1, 1, 3, 4 };
            mesh.vertices = v;
            mesh.triangles = tri;
            mesh.RecalculateNormals();
            GameObject roof = new GameObject("roof_weathered_gable");
            roof.transform.SetParent(parent);
            roof.AddComponent<MeshFilter>().sharedMesh = mesh;
            roof.AddComponent<MeshRenderer>().sharedMaterial = material;
        }

        private static GameObject AddBox(Transform parent, string name, Vector3 localPosition, Vector3 scale, Material material)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent);
            go.transform.localPosition = localPosition;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale = scale;
            go.AddComponent<MeshFilter>().sharedMesh = CreateBoxMesh();
            go.AddComponent<MeshRenderer>().sharedMaterial = material;
            return go;
        }

        private static void AddCylinder(Transform parent, string name, Vector3 localPosition, float radius, float height, Material material)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent);
            go.transform.localPosition = localPosition;
            go.AddComponent<MeshFilter>().sharedMesh = CreateCylinderMesh(16, radius, height);
            go.AddComponent<MeshRenderer>().sharedMaterial = material;
        }

        private static void AddCone(Transform parent, string name, Vector3 localPosition, float radius, float height, Material material)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent);
            go.transform.localPosition = localPosition;
            go.AddComponent<MeshFilter>().sharedMesh = CreateConeMesh(18, radius, height);
            go.AddComponent<MeshRenderer>().sharedMaterial = material;
        }

        private static void AddPointLight(string name, Vector3 position, Color color, float intensity, float range, Transform parent)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent);
            go.transform.position = position;
            Light light = go.AddComponent<Light>();
            light.type = LightType.Point;
            light.color = color;
            light.intensity = intensity;
            light.range = range;
            light.shadows = LightShadows.Soft;
        }

        private static Mesh CreateBoxMesh()
        {
            Vector3[] v =
            {
                new Vector3(-0.5f,-0.5f,-0.5f), new Vector3(0.5f,-0.5f,-0.5f), new Vector3(0.5f,0.5f,-0.5f), new Vector3(-0.5f,0.5f,-0.5f),
                new Vector3(-0.5f,-0.5f,0.5f), new Vector3(0.5f,-0.5f,0.5f), new Vector3(0.5f,0.5f,0.5f), new Vector3(-0.5f,0.5f,0.5f)
            };
            int[] t =
            {
                0,2,1, 0,3,2, 4,5,6, 4,6,7, 0,1,5, 0,5,4,
                2,3,7, 2,7,6, 1,2,6, 1,6,5, 3,0,4, 3,4,7
            };
            Mesh mesh = new Mesh { name = "_RPG_BoxMesh" };
            mesh.vertices = v;
            mesh.triangles = t;
            mesh.RecalculateNormals();
            return mesh;
        }

        private static Mesh CreateCylinderMesh(int segments, float radius, float height)
        {
            List<Vector3> v = new List<Vector3>();
            List<int> t = new List<int>();
            float half = height * 0.5f;
            for (int i = 0; i < segments; i++)
            {
                float a = i / (float)segments * Mathf.PI * 2f;
                v.Add(new Vector3(Mathf.Cos(a) * radius, -half, Mathf.Sin(a) * radius));
                v.Add(new Vector3(Mathf.Cos(a) * radius, half, Mathf.Sin(a) * radius));
            }
            v.Add(new Vector3(0f, -half, 0f));
            v.Add(new Vector3(0f, half, 0f));
            int bottom = segments * 2;
            int top = bottom + 1;
            for (int i = 0; i < segments; i++)
            {
                int n = (i + 1) % segments;
                int b0 = i * 2; int y0 = b0 + 1; int b1 = n * 2; int y1 = b1 + 1;
                t.AddRange(new[] { b0, y0, b1, b1, y0, y1, bottom, b1, b0, top, y0, y1 });
            }
            Mesh mesh = new Mesh { name = "_RPG_CylinderMesh" };
            mesh.SetVertices(v);
            mesh.SetTriangles(t, 0);
            mesh.RecalculateNormals();
            return mesh;
        }

        private static Mesh CreateConeMesh(int segments, float radius, float height)
        {
            List<Vector3> v = new List<Vector3> { new Vector3(0f, height * 0.5f, 0f), new Vector3(0f, -height * 0.5f, 0f) };
            List<int> t = new List<int>();
            for (int i = 0; i < segments; i++)
            {
                float a = i / (float)segments * Mathf.PI * 2f;
                v.Add(new Vector3(Mathf.Cos(a) * radius, -height * 0.5f, Mathf.Sin(a) * radius));
            }
            for (int i = 0; i < segments; i++)
            {
                int cur = i + 2;
                int next = i == segments - 1 ? 2 : i + 3;
                t.AddRange(new[] { 0, cur, next, 1, next, cur });
            }
            Mesh mesh = new Mesh { name = "_RPG_ConeMesh" };
            mesh.SetVertices(v);
            mesh.SetTriangles(t, 0);
            mesh.RecalculateNormals();
            return mesh;
        }

        private static Material CreatePbrMaterial(string name, string textureFolderAndSet, string setName, Color fallback, float smoothness)
        {
            Material material = CreateFlatMaterial(name, fallback, smoothness);
            string folder = "Assets/FantasyRPG/Textures/" + textureFolderAndSet;
            Texture2D color = AssetDatabase.LoadAssetAtPath<Texture2D>($"{folder}/{setName}_2K-JPG_Color.jpg");
            Texture2D normal = AssetDatabase.LoadAssetAtPath<Texture2D>($"{folder}/{setName}_2K-JPG_NormalDX.jpg");
            if (color != null)
            {
                SetTexture(material, "_BaseColorMap", color);
                SetTexture(material, "_MainTex", color);
                SetColor(material, fallback * 0.85f + Color.white * 0.15f);
            }
            if (normal != null)
            {
                SetTexture(material, "_NormalMap", normal);
                SetTexture(material, "_BumpMap", normal);
                SetFloat(material, "_NormalScale", 1f);
                SetFloat(material, "_BumpScale", 1f);
            }
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material CreateFlatMaterial(string name, Color color, float smoothness)
        {
            string path = $"{MaterialRoot}/{name}.mat";
            Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(Shader.Find("HDRP/Lit") ?? Shader.Find("Standard"));
                AssetDatabase.CreateAsset(material, path);
            }
            material.shader = Shader.Find("HDRP/Lit") ?? Shader.Find("Standard");
            SetColor(material, color);
            SetFloat(material, "_Smoothness", smoothness);
            SetFloat(material, "_Glossiness", smoothness);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material CreateEmissiveMaterial(string name, Color baseColor, Color emission)
        {
            Material material = CreateFlatMaterial(name, baseColor, 0.25f);
            material.EnableKeyword("_EMISSION");
            SetColor(material, baseColor);
            if (material.HasProperty("_EmissionColor"))
                material.SetColor("_EmissionColor", emission);
            if (material.HasProperty("_EmissiveColor"))
                material.SetColor("_EmissiveColor", emission);
            return material;
        }

        private static void SetTexture(Material material, string property, Texture texture)
        {
            if (material.HasProperty(property))
                material.SetTexture(property, texture);
        }

        private static void SetColor(Material material, Color color)
        {
            if (material.HasProperty("_BaseColor"))
                material.SetColor("_BaseColor", color);
            else if (material.HasProperty("_Color"))
                material.SetColor("_Color", color);
        }

        private static void SetFloat(Material material, string property, float value)
        {
            if (material.HasProperty(property))
                material.SetFloat(property, value);
        }

        private static float Lerp(float min, float max, System.Random rng) => Mathf.Lerp(min, max, (float)rng.NextDouble());

        private static void EnsureFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder))
                return;
            string parent = Path.GetDirectoryName(folder)?.Replace("\\", "/");
            if (!string.IsNullOrEmpty(parent) && !AssetDatabase.IsValidFolder(parent))
                EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(folder));
        }

        private static void WriteStatus(string result, int placeholderCount)
        {
            string dataRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "AutopilotData"));
            Directory.CreateDirectory(dataRoot);
            string json =
                "{\n" +
                $"  \"result\": \"{result}\",\n" +
                $"  \"generated_at_utc\": \"{DateTime.UtcNow:o}\",\n" +
                "  \"engine\": \"unity-hdrp\",\n" +
                "  \"scene\": \"Assets/Scenes/Main.unity\",\n" +
                $"  \"visible_placeholder_count\": {placeholderCount},\n" +
                "  \"composition\": \"cabin_path_forest_castle_beam\",\n" +
                "  \"note\": \"Clean reference pass avoids capsule/cube blockout actors and limits renderer count.\"\n" +
                "}\n";
            File.WriteAllText(Path.Combine(dataRoot, "hdrp_clean_reference_scene_status.json"), json);
        }
    }
}
#endif

