#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    // Sahnedeki primitive blockout karakterleri gercek FBX modellerle degistirir.
    // Derleme sonrasi otomatik calisir. El ile: Tools > Autopilot > Swap Characters to Real Models
    [InitializeOnLoad]
    public static class CharacterModelSwapper
    {
        private const string DoneKey = "ThornyIvy_CharSwap_v3";

        private const string HeroAsset   = "Assets/Art/Characters/Imported/Hero/SK_Hero.fbx";
        private const string Enemy0Asset = "Assets/Art/Characters/Imported/Enemy/SK_Enemy0.fbx";
        private const string Enemy1Asset = "Assets/Art/Characters/Imported/Enemy/SK_Enemy1.fbx";
        private const string SwordAsset  = "Assets/Art/Characters/Imported/Equipment/SM_Sword.fbx";
        private const string KatanaAsset = "Assets/Art/Characters/Imported/Equipment/SM_Katana.fbx";

        static CharacterModelSwapper()
        {
            // Zaten bu session'da yapildiysa tekrar calisma
            if (SessionState.GetBool(DoneKey, false)) return;
            // Modeller mevcutsa otomatik calistir
            EditorApplication.delayCall += AutoSwap;
        }

        private static void AutoSwap()
        {
            if (SessionState.GetBool(DoneKey, false)) return;
            // Sahnede zaten gercek model varsa atla
            if (SceneHasRealModels()) { SessionState.SetBool(DoneKey, true); return; }
            // Hero FBX mevcut degilse bekle
            if (AssetDatabase.LoadAssetAtPath<GameObject>(HeroAsset) == null) return;

            SessionState.SetBool(DoneKey, true);
            Debug.Log("[CharacterSwapper] Otomatik model swap baslatiliyor...");
            SwapAll();
        }

        [MenuItem("Tools/Autopilot/Swap Characters to Real Models")]
        public static void SwapAll()
        {
            ConfigureImporters();
            int swapped = 0;

            // â”€â”€ Player â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            var player = GameObject.FindWithTag("Player");
            if (player != null)
            {
                swapped += SwapCharacter(player.transform, HeroAsset,
                    new Vector3(0f, -1.05f, 0f), 1.0f, isHero: true);
                AttachWeapon(player.transform, SwordAsset, KatanaAsset);
            }

            // â”€â”€ Enemies â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            var enemies = UnityEngine.Object.FindObjectsByType<Gameplay.EnemyAIController>(
                FindObjectsInactive.Exclude);
            for (int i = 0; i < enemies.Length; i++)
            {
                string asset = (i % 2 == 0) ? Enemy0Asset : Enemy1Asset;
                swapped += SwapCharacter(enemies[i].transform, asset,
                    new Vector3(0f, -1.0f, 0f), 0.85f, isHero: false);
            }

            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            AssetDatabase.SaveAssets();

            string msg = $"{swapped} karakter gercek FBX modeline guncellendi.";
            Debug.Log($"[CharacterSwapper] {msg}");
            if (swapped > 0)
                EditorUtility.DisplayDialog("Karakter Swap Tamam", msg + "\nSahne kaydedildi.", "OK");
        }

        private static bool SceneHasRealModels()
        {
            var player = GameObject.FindWithTag("Player");
            if (player == null) return false;
            foreach (Transform child in player.transform)
                if (child.name == "SK_Hero_Visual" || child.name == "SK_Model_Visual")
                    return true;
            return false;
        }

        private static int SwapCharacter(Transform root, string assetPath,
            Vector3 localPos, float scale, bool isHero)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (prefab == null)
            {
                Debug.LogWarning($"[CharacterSwapper] Model bulunamadi: {assetPath}");
                return 0;
            }

            // Zaten yerlestirilmis mi?
            string targetName = isHero ? "SK_Hero_Visual" : "SK_Enemy_Visual";
            foreach (Transform child in root)
                if (child.name == targetName) return 1; // zaten var

            // Blockout ve primitive alt objeleri kaldir
            RemoveBlockoutChildren(root);

            // Root mesh'i gizle
            var mr = root.GetComponent<MeshRenderer>();
            if (mr != null) mr.enabled = false;
            var smr = root.GetComponent<SkinnedMeshRenderer>();
            if (smr != null) smr.enabled = false;

            // Gercek modeli yerlesyir
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, root);
            go.name = targetName;
            go.transform.localPosition = localPos;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale    = Vector3.one * scale;

            foreach (var col in go.GetComponentsInChildren<Collider>())
                col.enabled = false;

            Undo.RegisterCreatedObjectUndo(go, "SwapCharacter");
            return 1;
        }

        private static void RemoveBlockoutChildren(Transform root)
        {
            var toDelete = new List<Transform>();
            foreach (Transform child in root)
            {
                string n = child.name;
                bool isBlockout =
                    n.Contains("Blockout") || n.Contains("Visual") ||
                    n.Contains("Cloak")    || n.Contains("Tool_Stick") ||
                    n.StartsWith("Hero_")  || n.StartsWith("Enemy_")   ||
                    n.StartsWith("Player_")|| n.StartsWith("SK_")      ||
                    n.StartsWith("SM_")    || IsPrimitiveMesh(child);
                if (isBlockout) toDelete.Add(child);
            }
            foreach (var t in toDelete)
                Undo.DestroyObjectImmediate(t.gameObject);
        }

        private static bool IsPrimitiveMesh(Transform t)
        {
            var mf = t.GetComponent<MeshFilter>();
            if (mf == null || mf.sharedMesh == null) return false;
            string meshName = mf.sharedMesh.name;
            return meshName == "Cube"    || meshName == "Sphere"   ||
                   meshName == "Capsule" || meshName == "Cylinder" ||
                   meshName == "Plane"   || meshName == "Quad";
        }

        private static void AttachWeapon(Transform player, string sword, string katana)
        {
            var toDelete = new List<Transform>();
            foreach (Transform child in player.transform)
                if (child.name.Contains("Sword")  || child.name.Contains("Katana") ||
                    child.name.Contains("Weapon")  || child.name.Contains("Tool_Stick") ||
                    child.name == "SM_Weapon_Visual")
                    toDelete.Add(child);
            foreach (var t in toDelete)
                Undo.DestroyObjectImmediate(t.gameObject);

            var weaponPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(sword)
                            ?? AssetDatabase.LoadAssetAtPath<GameObject>(katana);
            if (weaponPrefab == null) return;

            // El kemigini bul (animator riginden)
            Transform handBone = FindBone(player, "RightHand", "Bip01_R_Hand", "Hand_R", "R_Hand", "RHand");

            var w = (GameObject)PrefabUtility.InstantiatePrefab(weaponPrefab, handBone != null ? handBone : player);
            w.name = "SM_Weapon_Visual";

            if (handBone != null)
            {
                // Kemige dogrudan bagla â€” kucuk offset
                w.transform.localPosition = new Vector3(0f, 0.05f, 0f);
                w.transform.localRotation = Quaternion.Euler(0f, 0f, 0f);
            }
            else
            {
                // Kemik yok: tahmini el pozisyonu
                w.transform.localPosition = new Vector3(0.78f, -0.10f, 0.35f);
                w.transform.localRotation = Quaternion.Euler(0f, 0f, -28f);
            }

            // Silah tipine gore fiziksel boyut
            string assetName = System.IO.Path.GetFileNameWithoutExtension(sword.Length > 0 ? sword : katana);
            float targetLengthM = WeaponTargetLength(assetName);
            float naturalSize   = GetMeshMaxDim(weaponPrefab);
            float sc = naturalSize > 0.001f ? targetLengthM / naturalSize : 0.012f;
            w.transform.localScale = Vector3.one * sc;

            foreach (var col in w.GetComponentsInChildren<Collider>())
                col.enabled = false;
            Undo.RegisterCreatedObjectUndo(w, "AttachWeapon");
        }

        // Rig'deki el kemigini isimle bul
        private static Transform FindBone(Transform root, params string[] names)
        {
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                foreach (var n in names)
                    if (t.name.Equals(n, System.StringComparison.OrdinalIgnoreCase) ||
                        t.name.IndexOf(n, System.StringComparison.OrdinalIgnoreCase) >= 0)
                        return t;
            return null;
        }

        // Silah turune gore hedef fiziksel uzunluk (metre)
        private static float WeaponTargetLength(string name)
        {
            name = name.ToLower();
            if (name.Contains("katana"))                          return 1.05f;
            if (name.Contains("tanto") || name.Contains("kunai") || name.Contains("dagger")) return 0.38f;
            if (name.Contains("shuriken") || name.Contains("throwing"))                      return 0.18f;
            if (name.Contains("staff")   || name.Contains("rod") || name.Contains("bone_staff")) return 1.80f;
            if (name.Contains("wand"))                            return 0.55f;
            if (name.Contains("bow"))                             return 1.15f;
            if (name.Contains("spear")   || name.Contains("lance"))                          return 1.90f;
            if (name.Contains("axe")     || name.Contains("hatchet"))                        return 0.72f;
            if (name.Contains("mace")    || name.Contains("club") || name.Contains("hammer")) return 0.78f;
            if (name.Contains("shield"))                          return 0.80f;
            if (name.Contains("sword")   || name.Contains("blade"))                          return 1.00f;
            return 0.90f; // varsayilan
        }

        // Prefabin en buyuk mesh boyutu (local space, scale=1 kabul)
        private static float GetMeshMaxDim(GameObject prefab)
        {
            float max = 0f;
            foreach (var mf in prefab.GetComponentsInChildren<MeshFilter>(true))
                if (mf.sharedMesh != null)
                {
                    var s = mf.sharedMesh.bounds.size;
                    max = Mathf.Max(max, s.x, s.y, s.z);
                }
            foreach (var smr in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (smr.sharedMesh != null)
                {
                    var s = smr.sharedMesh.bounds.size;
                    max = Mathf.Max(max, s.x, s.y, s.z);
                }
            return max;
        }

        private static void ConfigureImporters()
        {
            bool reimport = false;
            foreach (string path in new[] { HeroAsset, Enemy0Asset, Enemy1Asset, SwordAsset, KatanaAsset })
            {
                var importer = AssetImporter.GetAtPath(path) as ModelImporter;
                if (importer == null) continue;
                if (importer.animationType != ModelImporterAnimationType.None || importer.importAnimation)
                {
                    importer.animationType      = ModelImporterAnimationType.None;
                    importer.avatarSetup        = ModelImporterAvatarSetup.NoAvatar;
                    importer.importAnimation    = false;
                    importer.materialImportMode = ModelImporterMaterialImportMode.None;
                    importer.globalScale        = 1f;
                    importer.SaveAndReimport();
                    reimport = true;
                }
            }
            if (reimport)
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }
    }
}
#endif

