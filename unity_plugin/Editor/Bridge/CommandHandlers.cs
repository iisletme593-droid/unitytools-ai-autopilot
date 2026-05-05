// Unity Editor command handlers. All methods run on the Unity main thread.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
namespace UnityTools.Bridge
{
    public static class CommandHandlers
    {
        public static object Dispatch(string method, JObject p)
        {
            switch (method)
            {
                case "ping": return Ping();
                case "get_project_info": return GetProjectInfo();
                case "list_scene_objects": return ListSceneObjects(p);
                case "find_scene_objects": return FindSceneObjects(p);
                case "create_primitive": return CreatePrimitive(p);
                case "set_transform": return SetTransform(p);
                case "set_material_color": return SetMaterialColor(p);
                case "import_asset": return ImportAsset(p);
                case "save_scene": return SaveScene();
                case "open_scene": return OpenScene(p);
                case "execute_menu_item": return ExecuteMenuItem(p);
                case "delete_object": return DeleteObject(p);
                case "duplicate_object": return DuplicateObject(p);
                case "create_empty": return CreateEmpty(p);
                case "set_parent": return SetParent(p);
                case "set_active": return SetActive(p);
                case "set_tag": return SetTag(p);
                case "set_layer": return SetLayer(p);
                case "add_component": return AddComponent(p);
                case "remove_component": return RemoveComponent(p);
                case "get_component_info": return GetComponentInfo(p);
                case "get_object_details": return GetObjectDetails(p);
                case "create_light": return CreateLight(p);
                case "set_camera": return SetCamera(p);
                case "play_mode": return PlayMode(p);
                case "instantiate_prefab": return InstantiatePrefab(p);
                case "instantiate_prefabs": return InstantiatePrefabs(p);
                case "add_collider": return AddCollider(p);
                case "set_rigidbody": return SetRigidbody(p);
                case "find_by_tag": return FindByTag(p);
                case "find_assets": return FindAssets(p);
                case "list_prefabs": return ListPrefabs(p);
                case "get_editor_state": return GetEditorState();
                case "get_scene_catalog": return GetSceneCatalog(p);
                case "find_scene_objects_semantic": return FindSceneObjectsSemantic(p);
                case "delete_scene_objects_semantic": return DeleteSceneObjectsSemantic(p);
                case "apply_material_palette": return ApplyMaterialPalette(p);
                case "create_optimized_forest_scene": return CreateOptimizedForestScene(p);
                case "optimize_editor_performance": return OptimizeEditorPerformance(p);
                default: throw new InvalidOperationException($"Unknown method: {method}");
            }
        }

        private static object Ping()
        {
            return new { pong = true, unity_version = Application.unityVersion, time = DateTime.UtcNow.ToString("o") };
        }

        private static object GetProjectInfo()
        {
            return new
            {
                project_name = Application.productName,
                unity_version = Application.unityVersion,
                data_path = Application.dataPath,
                active_scene = SceneManager.GetActiveScene().path,
                is_playing = EditorApplication.isPlaying,
            };
        }

        private static object ListSceneObjects(JObject p)
        {
            int maxCount = Mathf.Clamp(p["max_count"]?.ToObject<int>() ?? 200, 1, 5000);
            var scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects();
            var list = new List<object>();
            foreach (var root in roots)
            {
                AppendHierarchy(root, list, 0, maxCount);
                if (list.Count >= maxCount) break;
            }
            int totalCount = CountHierarchy(roots);
            return new { scene = scene.name, objects = list, count = totalCount, returned = list.Count, truncated = totalCount > list.Count };
        }

        private static object FindSceneObjects(JObject p)
        {
            string query = p["name_contains"]?.ToString() ?? "";
            int maxCount = Mathf.Clamp(p["max_count"]?.ToObject<int>() ?? 50, 1, 1000);
            var scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects();
            var list = new List<object>();
            int totalMatches = 0;
            foreach (var root in roots)
            {
                AppendMatches(root, query, list, ref totalMatches, 0, maxCount);
            }
            return new { scene = scene.name, query, objects = list, count = totalMatches, returned = list.Count, truncated = totalMatches > list.Count };
        }

        private static void AppendHierarchy(GameObject go, List<object> list, int depth, int maxCount)
        {
            if (list.Count >= maxCount) return;
            list.Add(new
            {
                name = go.name,
                depth = depth,
                active = go.activeSelf,
                position = new { x = go.transform.position.x, y = go.transform.position.y, z = go.transform.position.z },
                tag = go.tag,
            });
            foreach (Transform child in go.transform)
            {
                if (list.Count >= maxCount) break;
                AppendHierarchy(child.gameObject, list, depth + 1, maxCount);
            }
        }

        private static void AppendMatches(GameObject go, string query, List<object> list, ref int totalMatches, int depth, int maxCount)
        {
            if (string.IsNullOrEmpty(query) || go.name.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0)
            {
                totalMatches++;
                if (list.Count < maxCount)
                {
                    list.Add(new
                    {
                        name = go.name,
                        depth = depth,
                        active = go.activeSelf,
                        position = new { x = go.transform.position.x, y = go.transform.position.y, z = go.transform.position.z },
                        tag = go.tag,
                    });
                }
            }
            foreach (Transform child in go.transform)
            {
                AppendMatches(child.gameObject, query, list, ref totalMatches, depth + 1, maxCount);
            }
        }

        private static int CountHierarchy(GameObject[] roots)
        {
            int count = 0;
            foreach (var root in roots) count += CountHierarchy(root);
            return count;
        }

        private static int CountHierarchy(GameObject go)
        {
            int count = 1;
            foreach (Transform child in go.transform) count += CountHierarchy(child.gameObject);
            return count;
        }

        private static object CreatePrimitive(JObject p)
        {
            string typeStr = p["type"]?.ToString() ?? "Cube";
            string name = p["name"]?.ToString();
            JObject pos = p["position"] as JObject;
            if (!Enum.TryParse<PrimitiveType>(typeStr, true, out var type))
                throw new ArgumentException($"Invalid primitive type: {typeStr}");
            var go = GameObject.CreatePrimitive(type);
            if (!string.IsNullOrEmpty(name)) go.name = name;
            if (pos != null)
            {
                go.transform.position = new Vector3(
                    pos["x"]?.ToObject<float>() ?? 0f,
                    pos["y"]?.ToObject<float>() ?? 0f,
                    pos["z"]?.ToObject<float>() ?? 0f
                );
            }
            Undo.RegisterCreatedObjectUndo(go, $"Bridge: create {go.name}");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { name = go.name, instance_id = go.GetHashCode() };
        }

        private static object SetTransform(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            JObject pos = p["position"] as JObject;
            JObject rot = p["rotation"] as JObject;
            JObject scl = p["scale"] as JObject;
            Undo.RecordObject(go.transform, "Bridge: set transform");
            if (pos != null)
            {
                go.transform.position = new Vector3(
                    pos["x"]?.ToObject<float>() ?? go.transform.position.x,
                    pos["y"]?.ToObject<float>() ?? go.transform.position.y,
                    pos["z"]?.ToObject<float>() ?? go.transform.position.z
                );
            }
            if (rot != null)
            {
                go.transform.eulerAngles = new Vector3(
                    rot["x"]?.ToObject<float>() ?? 0f,
                    rot["y"]?.ToObject<float>() ?? 0f,
                    rot["z"]?.ToObject<float>() ?? 0f
                );
            }
            if (scl != null)
            {
                go.transform.localScale = new Vector3(
                    scl["x"]?.ToObject<float>() ?? 1f,
                    scl["y"]?.ToObject<float>() ?? 1f,
                    scl["z"]?.ToObject<float>() ?? 1f
                );
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true };
        }

        private static object SetMaterialColor(JObject p)
        {
            string name = p["name"]?.ToString();
            float r = p["r"]?.ToObject<float>() ?? 1f;
            float g = p["g"]?.ToObject<float>() ?? 1f;
            float b = p["b"]?.ToObject<float>() ?? 1f;
            float a = p["a"]?.ToObject<float>() ?? 1f;
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var rend = go.GetComponent<Renderer>();
            if (rend == null) throw new InvalidOperationException($"Renderer not found: {name}");
            Undo.RecordObject(rend, "Bridge: material color");
            var mat = rend.material;
            mat.color = new Color(r, g, b, a);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true };
        }

        private static object ImportAsset(JObject p)
        {
            string srcPath = p["src_path"]?.ToString();
            string dstRel = p["dst_relative"]?.ToString();
            if (string.IsNullOrEmpty(srcPath) || string.IsNullOrEmpty(dstRel))
                throw new ArgumentException("src_path and dst_relative are required");
            if (!File.Exists(srcPath))
                throw new FileNotFoundException($"Source file not found: {srcPath}");
            string fullDst = Path.Combine(Application.dataPath, dstRel);
            Directory.CreateDirectory(Path.GetDirectoryName(fullDst));
            File.Copy(srcPath, fullDst, overwrite: true);
            string assetPath = "Assets/" + dstRel.Replace("\\", "/");
            AssetDatabase.Refresh();
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
            return new { dst_path = assetPath, size_bytes = new FileInfo(fullDst).Length };
        }

        private static object SaveScene()
        {
            var scene = SceneManager.GetActiveScene();
            bool ok = EditorSceneManager.SaveScene(scene);
            return new { ok = ok, path = scene.path };
        }

        private static object OpenScene(JObject p)
        {
            string path = p["path"]?.ToString();
            if (string.IsNullOrEmpty(path)) throw new ArgumentException("path is required");
            var scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
            return new { name = scene.name, path = scene.path };
        }

        private static object ExecuteMenuItem(JObject p)
        {
            string menu = p["path"]?.ToString();
            if (string.IsNullOrEmpty(menu)) throw new ArgumentException("path is required");
            bool ok = EditorApplication.ExecuteMenuItem(menu);
            return new { ok = ok };
        }

        private static object DeleteObject(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            Undo.DestroyObjectImmediate(go);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, deleted = name };
        }

        private static object DuplicateObject(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var clone = UnityEngine.Object.Instantiate(go);
            clone.name = go.name + "_Clone";
            Undo.RegisterCreatedObjectUndo(clone, $"Bridge: duplicate {go.name}");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { name = clone.name, instance_id = clone.GetHashCode() };
        }

        private static object CreateEmpty(JObject p)
        {
            string name = p["name"]?.ToString() ?? "Empty";
            var go = new GameObject(name);
            JObject pos = p["position"] as JObject;
            if (pos != null)
            {
                go.transform.position = new Vector3(
                    pos["x"]?.ToObject<float>() ?? 0f,
                    pos["y"]?.ToObject<float>() ?? 0f,
                    pos["z"]?.ToObject<float>() ?? 0f
                );
            }
            Undo.RegisterCreatedObjectUndo(go, $"Bridge: create empty {name}");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { name = go.name, instance_id = go.GetHashCode() };
        }

        private static object SetParent(JObject p)
        {
            string childName = p["child"]?.ToString();
            string parentName = p["parent"]?.ToString();
            if (string.IsNullOrEmpty(childName)) throw new ArgumentException("child is required");
            var child = GameObject.Find(childName);
            if (child == null) throw new InvalidOperationException($"Child not found: {childName}");
            Transform parent = null;
            if (!string.IsNullOrEmpty(parentName))
            {
                var pGo = GameObject.Find(parentName);
                if (pGo == null) throw new InvalidOperationException($"Parent not found: {parentName}");
                parent = pGo.transform;
            }
            Undo.SetTransformParent(child.transform, parent, "Bridge: set parent");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true };
        }

        private static object SetActive(JObject p)
        {
            string name = p["name"]?.ToString();
            bool active = p["active"]?.ToObject<bool>() ?? true;
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            Undo.RecordObject(go, "Bridge: set active");
            go.SetActive(active);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, active = active };
        }

        private static object SetTag(JObject p)
        {
            string name = p["name"]?.ToString();
            string tag = p["tag"]?.ToString();
            if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(tag))
                throw new ArgumentException("name and tag are required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            Undo.RecordObject(go, "Bridge: set tag");
            go.tag = tag;
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, tag = tag };
        }

        private static object SetLayer(JObject p)
        {
            string name = p["name"]?.ToString();
            int layer = p["layer"]?.ToObject<int>() ?? 0;
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            Undo.RecordObject(go, "Bridge: set layer");
            go.layer = layer;
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, layer = layer };
        }

        private static object AddComponent(JObject p)
        {
            string name = p["name"]?.ToString();
            string typeName = p["type"]?.ToString();
            if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(typeName))
                throw new ArgumentException("name and type are required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var compType = System.Type.GetType(typeName) ?? System.Type.GetType("UnityEngine." + typeName + ",UnityEngine");
            if (compType == null)
                compType = System.AppDomain.CurrentDomain.GetAssemblies()
                    .SelectMany(a => a.GetTypes())
                    .FirstOrDefault(t => t.Name == typeName || t.FullName == typeName);
            if (compType == null) throw new InvalidOperationException($"Component type not found: {typeName}");
            var comp = go.AddComponent(compType);
            Undo.RegisterCreatedObjectUndo(comp, $"Bridge: add {typeName}");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, component = compType.Name };
        }

        private static object RemoveComponent(JObject p)
        {
            string name = p["name"]?.ToString();
            string typeName = p["type"]?.ToString();
            if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(typeName))
                throw new ArgumentException("name and type are required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var comp = go.GetComponents<Component>().FirstOrDefault(c => c.GetType().Name == typeName || c.GetType().FullName == typeName);
            if (comp == null) throw new InvalidOperationException($"Component {typeName} not found on {name}");
            Undo.DestroyObjectImmediate(comp);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, removed = typeName };
        }

        private static object GetComponentInfo(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var comps = go.GetComponents<Component>();
            var list = new List<object>();
            foreach (var c in comps)
            {
                if (c == null) continue;
                list.Add(new { type = c.GetType().Name, full = c.GetType().FullName });
            }
            return new { name = go.name, components = list, count = list.Count };
        }

        private static object GetObjectDetails(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var t = go.transform;
            var comps = go.GetComponents<Component>().Where(c => c != null).Select(c => c.GetType().Name).ToList();
            return new
            {
                name = go.name,
                active = go.activeSelf,
                active_in_hierarchy = go.activeInHierarchy,
                tag = go.tag,
                layer = go.layer,
                position = new { x = t.position.x, y = t.position.y, z = t.position.z },
                rotation = new { x = t.eulerAngles.x, y = t.eulerAngles.y, z = t.eulerAngles.z },
                scale = new { x = t.localScale.x, y = t.localScale.y, z = t.localScale.z },
                parent = t.parent?.name,
                child_count = t.childCount,
                components = comps,
            };
        }

        private static object CreateLight(JObject p)
        {
            string name = p["name"]?.ToString() ?? "Light";
            string typeStr = p["light_type"]?.ToString() ?? "Point";
            if (!Enum.TryParse<LightType>(typeStr, true, out var lightType))
                throw new ArgumentException($"Invalid light type: {typeStr}");
            var go = new GameObject(name);
            var light = go.AddComponent<Light>();
            light.type = lightType;
            JObject pos = p["position"] as JObject;
            if (pos != null)
                go.transform.position = new Vector3(
                    pos["x"]?.ToObject<float>() ?? 0f,
                    pos["y"]?.ToObject<float>() ?? 0f,
                    pos["z"]?.ToObject<float>() ?? 0f
                );
            JObject col = p["color"] as JObject;
            if (col != null)
                light.color = new Color(
                    col["r"]?.ToObject<float>() ?? 1f,
                    col["g"]?.ToObject<float>() ?? 1f,
                    col["b"]?.ToObject<float>() ?? 1f,
                    col["a"]?.ToObject<float>() ?? 1f
                );
            light.intensity = p["intensity"]?.ToObject<float>() ?? 1f;
            light.range = p["range"]?.ToObject<float>() ?? 10f;
            Undo.RegisterCreatedObjectUndo(go, $"Bridge: create light {name}");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { name = go.name, instance_id = go.GetHashCode(), light_type = lightType.ToString() };
        }

        private static object SetCamera(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var cam = go.GetComponent<Camera>();
            if (cam == null) throw new InvalidOperationException($"Camera component not found on {name}");
            Undo.RecordObject(cam, "Bridge: set camera");
            JObject bg = p["background_color"] as JObject;
            if (bg != null)
                cam.backgroundColor = new Color(
                    bg["r"]?.ToObject<float>() ?? cam.backgroundColor.r,
                    bg["g"]?.ToObject<float>() ?? cam.backgroundColor.g,
                    bg["b"]?.ToObject<float>() ?? cam.backgroundColor.b,
                    bg["a"]?.ToObject<float>() ?? cam.backgroundColor.a
                );
            if (p["fov"] != null) cam.fieldOfView = p["fov"].ToObject<float>();
            if (p["near_clip"] != null) cam.nearClipPlane = p["near_clip"].ToObject<float>();
            if (p["far_clip"] != null) cam.farClipPlane = p["far_clip"].ToObject<float>();
            if (p["orthographic"] != null) cam.orthographic = p["orthographic"].ToObject<bool>();
            if (p["orthographic_size"] != null) cam.orthographicSize = p["orthographic_size"].ToObject<float>();
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true };
        }

        private static object PlayMode(JObject p)
        {
            bool play = p["play"]?.ToObject<bool>() ?? true;
            if (EditorApplication.isPlaying == play)
                return new { ok = true, is_playing = play };
            EditorApplication.isPlaying = play;
            return new { ok = true, is_playing = play };
        }

        private static object GetEditorState()
        {
            return new
            {
                is_compiling = EditorApplication.isCompiling,
                is_updating = EditorApplication.isUpdating,
                is_playing = EditorApplication.isPlaying,
                is_playing_or_will_change = EditorApplication.isPlayingOrWillChangePlaymode,
            };
        }

        private static object InstantiatePrefab(JObject p)
        {
            string path = p["path"]?.ToString();
            if (string.IsNullOrEmpty(path)) throw new ArgumentException("path is required");
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) throw new InvalidOperationException($"Prefab not found: {path}");
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            JObject pos = p["position"] as JObject;
            if (pos != null)
                go.transform.position = new Vector3(
                    pos["x"]?.ToObject<float>() ?? 0f,
                    pos["y"]?.ToObject<float>() ?? 0f,
                    pos["z"]?.ToObject<float>() ?? 0f
                );
            Undo.RegisterCreatedObjectUndo(go, $"Bridge: instantiate {path}");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { name = go.name, instance_id = go.GetHashCode(), path = path };
        }

        private static object InstantiatePrefabs(JObject p)
        {
            JArray items = p["items"] as JArray;
            if (items == null || items.Count == 0) throw new ArgumentException("items array is required");
            int max = p["max"]?.ToObject<int>() ?? 200;
            if (max <= 0) max = 200;
            var created = new List<object>();
            var errors = new List<object>();
            int count = 0;
            foreach (var token in items)
            {
                if (count >= max) break;
                var obj = token as JObject;
                if (obj == null) continue;
                string path = obj["path"]?.ToString();
                if (string.IsNullOrEmpty(path)) continue;
                try
                {
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                    if (prefab == null) throw new InvalidOperationException($"Prefab not found: {path}");
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    string name = obj["name"]?.ToString();
                    if (!string.IsNullOrEmpty(name)) go.name = name;
                    JObject pos = obj["position"] as JObject;
                    if (pos != null)
                        go.transform.position = new Vector3(
                            pos["x"]?.ToObject<float>() ?? 0f,
                            pos["y"]?.ToObject<float>() ?? 0f,
                            pos["z"]?.ToObject<float>() ?? 0f
                        );
                    JObject rot = obj["rotation"] as JObject;
                    if (rot != null)
                        go.transform.eulerAngles = new Vector3(
                            rot["x"]?.ToObject<float>() ?? 0f,
                            rot["y"]?.ToObject<float>() ?? 0f,
                            rot["z"]?.ToObject<float>() ?? 0f
                        );
                    JObject scale = obj["scale"] as JObject;
                    if (scale != null)
                        go.transform.localScale = new Vector3(
                            scale["x"]?.ToObject<float>() ?? 1f,
                            scale["y"]?.ToObject<float>() ?? 1f,
                            scale["z"]?.ToObject<float>() ?? 1f
                        );
                    Undo.RegisterCreatedObjectUndo(go, $"Bridge: instantiate {path}");
                    created.Add(new { path = path, name = go.name, instance_id = go.GetHashCode() });
                    count++;
                }
                catch (Exception e)
                {
                    errors.Add(new { path = path, error = e.Message });
                }
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = errors.Count == 0, created_count = created.Count, error_count = errors.Count, created = created, errors = errors };
        }

        private static object AddCollider(JObject p)
        {
            string name = p["name"]?.ToString();
            string typeStr = p["collider_type"]?.ToString() ?? "Box";
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            System.Type colliderType = typeStr.ToLower() switch
            {
                "box" => typeof(BoxCollider),
                "sphere" => typeof(SphereCollider),
                "capsule" => typeof(CapsuleCollider),
                "mesh" => typeof(MeshCollider),
                "terrain" => typeof(TerrainCollider),
                _ => throw new ArgumentException($"Unknown collider type: {typeStr}")
            };
            var comp = go.AddComponent(colliderType);
            Undo.RegisterCreatedObjectUndo(comp, $"Bridge: add {typeStr} collider");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, collider_type = typeStr };
        }

        private static object SetRigidbody(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var rb = go.GetComponent<Rigidbody>();
            if (rb == null)
            {
                rb = go.AddComponent<Rigidbody>();
                Undo.RegisterCreatedObjectUndo(rb, "Bridge: add Rigidbody");
            }
            else
            {
                Undo.RecordObject(rb, "Bridge: set Rigidbody");
            }
            if (p["use_gravity"] != null) rb.useGravity = p["use_gravity"].ToObject<bool>();
            if (p["is_kinematic"] != null) rb.isKinematic = p["is_kinematic"].ToObject<bool>();
            if (p["mass"] != null) rb.mass = p["mass"].ToObject<float>();
            if (p["drag"] != null) rb.linearDamping = p["drag"].ToObject<float>();
            if (p["angular_drag"] != null) rb.angularDamping = p["angular_drag"].ToObject<float>();
            if (p["interpolate"] != null)
            {
                string interp = p["interpolate"].ToString();
                rb.interpolation = interp.ToLower() switch
                {
                    "none" => RigidbodyInterpolation.None,
                    "interpolate" => RigidbodyInterpolation.Interpolate,
                    "extrapolate" => RigidbodyInterpolation.Extrapolate,
                    _ => rb.interpolation
                };
            }
            if (p["collision_detection"] != null)
            {
                string cd = p["collision_detection"].ToString();
                rb.collisionDetectionMode = cd.ToLower() switch
                {
                    "discrete" => CollisionDetectionMode.Discrete,
                    "continuous" => CollisionDetectionMode.Continuous,
                    "continuous_dynamic" => CollisionDetectionMode.ContinuousDynamic,
                    _ => rb.collisionDetectionMode
                };
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true };
        }

        private static object FindByTag(JObject p)
        {
            string tag = p["tag"]?.ToString();
            if (string.IsNullOrEmpty(tag)) throw new ArgumentException("tag is required");
            var gos = GameObject.FindGameObjectsWithTag(tag);
            var list = new List<object>();
            foreach (var go in gos)
            {
                list.Add(new { name = go.name, instance_id = go.GetHashCode() });
            }
            return new { tag = tag, count = list.Count, objects = list };
        }

        private static object GetSceneCatalog(JObject p)
        {
            int max = Mathf.Clamp(p["max_results"]?.ToObject<int>() ?? 1000, 1, 10000);
            var all = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include);
            var rows = new List<object>();
            var groups = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            foreach (var go in all.Take(max))
            {
                if (!go.scene.IsValid()) continue;
                string category = GuessCategory(go);
                groups[category] = groups.TryGetValue(category, out int n) ? n + 1 : 1;
                var renderers = go.GetComponentsInChildren<Renderer>(true);
                rows.Add(new
                {
                    name = go.name,
                    path = GetHierarchyPath(go.transform),
                    category,
                    active = go.activeSelf,
                    tag = go.tag,
                    layer = LayerMask.LayerToName(go.layer),
                    position = new { x = go.transform.position.x, y = go.transform.position.y, z = go.transform.position.z },
                    renderer_count = renderers.Length,
                    materials = renderers.SelectMany(r => r.sharedMaterials)
                        .Where(m => m != null)
                        .Select(m => m.name)
                        .Distinct()
                        .Take(8)
                        .ToArray(),
                    components = go.GetComponents<Component>().Where(c => c != null).Select(c => c.GetType().Name).Take(12).ToArray()
                });
            }
            return new
            {
                ok = true,
                scene = SceneManager.GetActiveScene().name,
                total_objects = all.Length,
                returned = rows.Count,
                groups = groups.OrderByDescending(kv => kv.Value).ToDictionary(kv => kv.Key, kv => kv.Value),
                objects = rows
            };
        }

        private static object FindSceneObjectsSemantic(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string category = p["category"]?.ToString() ?? "";
            int max = Mathf.Clamp(p["max_results"]?.ToObject<int>() ?? 100, 1, 2000);
            var matches = FindSemanticObjects(query, category).Take(max).ToList();
            return new
            {
                ok = true,
                query,
                category,
                count = matches.Count,
                objects = matches.Select(go => new
                {
                    name = go.name,
                    path = GetHierarchyPath(go.transform),
                    category = GuessCategory(go),
                    position = new { x = go.transform.position.x, y = go.transform.position.y, z = go.transform.position.z },
                    renderer_count = go.GetComponentsInChildren<Renderer>(true).Length
                }).ToArray()
            };
        }

        private static object DeleteSceneObjectsSemantic(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string category = p["category"]?.ToString() ?? "";
            int max = Mathf.Clamp(p["max"]?.ToObject<int>() ?? 500, 1, 5000);
            var matches = FindSemanticObjects(query, category)
                .Where(go => go != null)
                .Take(max)
                .ToList();
            matches = matches
                .Where(go => !matches.Any(other => other != go && go.transform.IsChildOf(other.transform)))
                .ToList();
            var deleted = new List<string>();
            foreach (var go in matches)
            {
                if (go == null) continue;
                deleted.Add(go.name);
                Undo.DestroyObjectImmediate(go);
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, query, category, deleted_count = deleted.Count, deleted };
        }

        private static object ApplyMaterialPalette(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string category = p["category"]?.ToString() ?? "";
            string palette = p["palette"]?.ToString() ?? "forest";
            int max = Mathf.Clamp(p["max"]?.ToObject<int>() ?? 2000, 1, 10000);
            var colors = PaletteColors(palette);
            var targets = string.IsNullOrWhiteSpace(query) && string.IsNullOrWhiteSpace(category)
                ? UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include).AsEnumerable()
                : FindSemanticObjects(query, category);
            int changed = 0;
            foreach (var go in targets.Take(max))
            {
                string cat = GuessCategory(go);
                Color color = colors.TryGetValue(cat, out var c) ? c : colors["default"];
                foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                {
                    if (renderer == null) continue;
                    var shader = Shader.Find("Standard") ?? renderer.sharedMaterial?.shader ?? Shader.Find("Universal Render Pipeline/Lit");
                    var mat = new Material(shader);
                    mat.name = $"UnityTools_{palette}_{cat}";
                    mat.color = color;
                    mat.SetFloat("_Glossiness", cat == "water" ? 0.65f : 0.15f);
                    renderer.sharedMaterial = mat;
                    changed++;
                }
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, query, category, palette, changed_renderers = changed };
        }

        private static object CreateOptimizedForestScene(JObject p)
        {
            bool clear = p["clear_scene"]?.ToObject<bool>() ?? true;
            int treeCount = Mathf.Clamp(p["tree_count"]?.ToObject<int>() ?? 100, 1, 300);
            int rockCount = Mathf.Clamp(p["rock_count"]?.ToObject<int>() ?? 18, 0, 120);
            float size = Mathf.Clamp(p["terrain_size"]?.ToObject<float>() ?? 120f, 20f, 500f);
            int seed = p["seed"]?.ToObject<int>() ?? 12345;
            var rng = new System.Random(seed);

            if (clear)
            {
                foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects().ToList())
                {
                    Undo.DestroyObjectImmediate(root);
                }
            }

            OptimizeEditorPerformance(new JObject());

            var rootGo = new GameObject("UnityTools_ForestScene");
            Undo.RegisterCreatedObjectUndo(rootGo, "UnityTools: forest scene root");

            var groundMat = MakeMaterial("ForestGround_DarkGrassDirt", new Color(0.16f, 0.20f, 0.10f), 0.05f);
            var pineMat = MakeMaterial("PineNeedles_DeepGreen", new Color(0.05f, 0.27f, 0.09f), 0.12f);
            var trunkMat = MakeMaterial("TreeTrunk_WarmBrown", new Color(0.28f, 0.16f, 0.08f), 0.10f);
            var deadMat = MakeMaterial("DeadTree_DryGreyBrown", new Color(0.20f, 0.17f, 0.14f), 0.08f);
            var rockMat = MakeMaterial("Rock_CoolGrey", new Color(0.28f, 0.29f, 0.27f), 0.18f);

            var terrain = BuildTerrain(size, rootGo.transform, groundMat, rng);
            var terrainData = terrain.GetComponent<Terrain>()?.terrainData;
            int pineCount = Mathf.RoundToInt(treeCount * 0.68f);
            int deadCount = treeCount - pineCount;
            var created = new List<string>();

            for (int i = 0; i < pineCount; i++)
            {
                Vector3 pos = RandomGroundPosition(size, terrainData, rng);
                string name = $"SparseTallPine_{i + 1:00}";
                CreateSimplePine(name, pos, RandomRange(rng, 0.75f, 1.45f), rootGo.transform, trunkMat, pineMat, rng);
                created.Add(name);
            }
            for (int i = 0; i < deadCount; i++)
            {
                Vector3 pos = RandomGroundPosition(size, terrainData, rng);
                string name = $"DeadTree_Silhouette_{i + 1:00}";
                CreateDeadTree(name, pos, RandomRange(rng, 0.8f, 1.35f), rootGo.transform, deadMat, rng);
                created.Add(name);
            }
            for (int i = 0; i < rockCount; i++)
            {
                Vector3 pos = RandomGroundPosition(size, terrainData, rng);
                string name = $"Rock_{i + 1:00}";
                CreateRock(name, pos, RandomRange(rng, 0.6f, 1.8f), rootGo.transform, rockMat, rng);
                created.Add(name);
            }

            RenderSettings.fog = true;
            RenderSettings.fogColor = new Color(0.38f, 0.42f, 0.38f);
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = 0.018f;
            RenderSettings.ambientLight = new Color(0.22f, 0.24f, 0.20f);

            var lightGo = new GameObject("DirectionalLight_ForestMorning");
            lightGo.transform.rotation = Quaternion.Euler(42f, -35f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.15f;
            light.color = new Color(1.0f, 0.92f, 0.78f);
            light.shadows = LightShadows.None;
            lightGo.transform.SetParent(rootGo.transform);

            var cameraGo = new GameObject("Camera_ForestOverview");
            var cam = cameraGo.AddComponent<Camera>();
            cam.fieldOfView = 50f;
            cam.farClipPlane = 350f;
            cam.transform.position = new Vector3(0f, 32f, -72f);
            cam.transform.rotation = Quaternion.Euler(24f, 0f, 0f);
            cameraGo.tag = "MainCamera";
            cameraGo.transform.SetParent(rootGo.transform);

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                root = rootGo.name,
                terrain = terrain.name,
                tree_count = treeCount,
                pine_count = pineCount,
                dead_tree_count = deadCount,
                rock_count = rockCount,
                created_count = created.Count,
                sample_names = created.Take(20).ToArray(),
                performance = "Editor quality lowered, shadows disabled for generated forest objects."
            };
        }

        private static object OptimizeEditorPerformance(JObject p)
        {
            QualitySettings.vSyncCount = 0;
            QualitySettings.antiAliasing = 0;
            QualitySettings.shadowDistance = p["shadow_distance"]?.ToObject<float>() ?? 25f;
            QualitySettings.lodBias = p["lod_bias"]?.ToObject<float>() ?? 0.55f;
            QualitySettings.maximumLODLevel = 1;
            foreach (var light in UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Include))
            {
                light.shadows = LightShadows.None;
                if (light.type == LightType.Directional && light.intensity > 1.25f) light.intensity = 1.0f;
            }
            foreach (var renderer in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include))
            {
                renderer.shadowCastingMode = ShadowCastingMode.Off;
                renderer.receiveShadows = false;
            }
            return new { ok = true, anti_aliasing = QualitySettings.antiAliasing, shadow_distance = QualitySettings.shadowDistance, lod_bias = QualitySettings.lodBias };
        }

        private static IEnumerable<GameObject> FindSemanticObjects(string query, string category)
        {
            var queryTokens = Tokenize(query);
            string wantedCategory = Normalize(category);
            foreach (var go in UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include))
            {
                if (!go.scene.IsValid()) continue;
                string cat = GuessCategory(go);
                if (!string.IsNullOrWhiteSpace(wantedCategory) && !CategoryMatches(cat, wantedCategory))
                    continue;
                if (queryTokens.Count == 0)
                {
                    yield return go;
                    continue;
                }
                string hay = Normalize($"{go.name} {go.tag} {LayerMask.LayerToName(go.layer)} {cat} {RendererWords(go)} {ComponentWords(go)}");
                bool any = queryTokens.Any(t => hay.Contains(t) || SynonymsFor(t).Any(s => hay.Contains(s)));
                if (any) yield return go;
            }
        }

        private static List<string> Tokenize(string value)
        {
            return Normalize(value)
                .Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries)
                .Where(t => t.Length > 1)
                .Distinct()
                .ToList();
        }

        private static string Normalize(string value)
        {
            if (string.IsNullOrWhiteSpace(value)) return "";
            value = value.ToLowerInvariant()
                .Replace("ı", "i").Replace("ğ", "g").Replace("ü", "u")
                .Replace("ş", "s").Replace("ö", "o").Replace("ç", "c");
            var chars = value.Select(ch => char.IsLetterOrDigit(ch) ? ch : ' ').ToArray();
            return new string(chars);
        }

        private static IEnumerable<string> SynonymsFor(string token)
        {
            switch (token)
            {
                case "forest":
                case "orman":
                case "agac":
                case "tree":
                case "trees":
                    return new[] { "tree", "pine", "fir", "forest", "trunk", "stump", "deadtree", "sparse", "silhouette" };
                case "kaya":
                case "tas":
                case "rock":
                    return new[] { "rock", "stone", "boulder", "cliff" };
                case "zemin":
                case "terrain":
                case "ground":
                case "ova":
                    return new[] { "terrain", "ground", "grass", "dirt", "floor", "plane" };
                case "koy":
                case "village":
                    return new[] { "village", "house", "hut", "camp", "cabin" };
                case "ates":
                case "campfire":
                    return new[] { "fire", "campfire", "torch", "flame" };
                default:
                    return Array.Empty<string>();
            }
        }

        private static bool CategoryMatches(string actualCategory, string wantedCategory)
        {
            string actual = Normalize(actualCategory);
            string wanted = Normalize(wantedCategory);
            if (string.IsNullOrWhiteSpace(wanted) || actual == wanted) return true;
            if ((wanted == "forest" || wanted == "orman" || wanted == "agac" || wanted == "trees") && actual == "tree") return true;
            if ((wanted == "tas" || wanted == "kaya" || wanted == "stone" || wanted == "boulder") && actual == "rock") return true;
            if ((wanted == "terrain" || wanted == "zemin" || wanted == "floor" || wanted == "grass" || wanted == "dirt") && actual == "ground") return true;
            if ((wanted == "campfire" || wanted == "ates" || wanted == "fire" || wanted == "flame") && actual == "camp") return true;
            if ((wanted == "village" || wanted == "koy" || wanted == "house" || wanted == "hut") && actual == "building") return true;
            return false;
        }

        private static string GuessCategory(GameObject go)
        {
            string hay = Normalize($"{go.name} {RendererWords(go)} {ComponentWords(go)}");
            if (hay.Contains("tree") || hay.Contains("pine") || hay.Contains("fir") || hay.Contains("trunk") || hay.Contains("stump") || hay.Contains("forest")) return "tree";
            if (hay.Contains("rock") || hay.Contains("stone") || hay.Contains("boulder") || hay.Contains("cliff")) return "rock";
            if (hay.Contains("terrain") || hay.Contains("ground") || hay.Contains("grass") || hay.Contains("dirt") || hay.Contains("floor")) return "ground";
            if (hay.Contains("camera")) return "camera";
            if (hay.Contains("light") || hay.Contains("sun")) return "light";
            if (hay.Contains("fire") || hay.Contains("torch") || hay.Contains("camp")) return "camp";
            if (hay.Contains("house") || hay.Contains("village") || hay.Contains("hut") || hay.Contains("castle")) return "building";
            if (hay.Contains("enemy") || hay.Contains("player") || hay.Contains("hero") || hay.Contains("character")) return "character";
            if (hay.Contains("water")) return "water";
            return "other";
        }

        private static string RendererWords(GameObject go)
        {
            var renderers = go.GetComponentsInChildren<Renderer>(true);
            return string.Join(" ", renderers.SelectMany(r => r.sharedMaterials)
                .Where(m => m != null)
                .Select(m => m.name)
                .Concat(renderers.Select(r => r.GetType().Name)));
        }

        private static string ComponentWords(GameObject go)
        {
            return string.Join(" ", go.GetComponents<Component>().Where(c => c != null).Select(c => c.GetType().Name));
        }

        private static string GetHierarchyPath(Transform t)
        {
            var names = new List<string>();
            while (t != null)
            {
                names.Add(t.name);
                t = t.parent;
            }
            names.Reverse();
            return string.Join("/", names);
        }

        private static Dictionary<string, Color> PaletteColors(string palette)
        {
            palette = Normalize(palette);
            if (palette.Contains("village") || palette.Contains("koy"))
            {
                return new Dictionary<string, Color>
                {
                    ["tree"] = new Color(0.07f, 0.25f, 0.08f),
                    ["rock"] = new Color(0.36f, 0.34f, 0.30f),
                    ["ground"] = new Color(0.24f, 0.18f, 0.10f),
                    ["building"] = new Color(0.42f, 0.28f, 0.16f),
                    ["camp"] = new Color(0.95f, 0.32f, 0.08f),
                    ["default"] = new Color(0.32f, 0.28f, 0.22f),
                };
            }
            return new Dictionary<string, Color>
            {
                ["tree"] = new Color(0.05f, 0.24f, 0.08f),
                ["rock"] = new Color(0.30f, 0.31f, 0.29f),
                ["ground"] = new Color(0.16f, 0.20f, 0.10f),
                ["building"] = new Color(0.25f, 0.18f, 0.12f),
                ["camp"] = new Color(0.9f, 0.28f, 0.06f),
                ["character"] = new Color(0.32f, 0.25f, 0.20f),
                ["water"] = new Color(0.08f, 0.20f, 0.26f),
                ["default"] = new Color(0.22f, 0.22f, 0.18f),
            };
        }

        private static Material MakeMaterial(string name, Color color, float smoothness)
        {
            var shader = Shader.Find("Standard") ?? Shader.Find("Universal Render Pipeline/Lit");
            var mat = new Material(shader);
            mat.name = name;
            mat.color = color;
            mat.SetFloat("_Glossiness", smoothness);
            return mat;
        }

        private static GameObject BuildTerrain(float size, Transform parent, Material material, System.Random rng)
        {
            int resolution = 129;
            float maxHeight = 4.0f;
            var data = new TerrainData
            {
                heightmapResolution = resolution,
                size = new Vector3(size, maxHeight, size)
            };
            float[,] heights = new float[resolution, resolution];
            for (int z = 0; z < resolution; z++)
            {
                for (int x = 0; x < resolution; x++)
                {
                    float nx = x / (float)(resolution - 1);
                    float nz = z / (float)(resolution - 1);
                    float h = Mathf.PerlinNoise(nx * 5.1f + 17.3f, nz * 5.1f + 9.7f) * 0.055f;
                    h += Mathf.PerlinNoise(nx * 13.0f, nz * 13.0f) * 0.018f;
                    heights[z, x] = h;
                }
            }
            data.SetHeights(0, 0, heights);
            var go = Terrain.CreateTerrainGameObject(data);
            go.name = $"Terrain_ForestGround_{Mathf.RoundToInt(size)}x{Mathf.RoundToInt(size)}";
            go.transform.position = new Vector3(-size * 0.5f, 0f, -size * 0.5f);
            go.transform.SetParent(parent);
            var terrain = go.GetComponent<Terrain>();
            terrain.materialTemplate = material;
            terrain.drawInstanced = false;
            var collider = go.GetComponent<TerrainCollider>();
            if (collider != null) collider.terrainData = data;
            return go;
        }

        private static Vector3 RandomGroundPosition(float size, TerrainData terrainData, System.Random rng)
        {
            float x = RandomRange(rng, -size * 0.46f, size * 0.46f);
            float z = RandomRange(rng, -size * 0.46f, size * 0.46f);
            float y = terrainData != null ? terrainData.GetInterpolatedHeight((x + size * 0.5f) / size, (z + size * 0.5f) / size) : 0f;
            return new Vector3(x, y, z);
        }

        private static float RandomRange(System.Random rng, float min, float max)
        {
            return min + (float)rng.NextDouble() * (max - min);
        }

        private static void CreateSimplePine(string name, Vector3 pos, float scale, Transform parent, Material trunkMat, Material foliageMat, System.Random rng)
        {
            var root = new GameObject(name);
            root.transform.SetParent(parent);
            root.transform.position = pos;
            root.transform.rotation = Quaternion.Euler(0f, RandomRange(rng, 0f, 360f), 0f);
            var trunk = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            trunk.name = "Trunk";
            trunk.transform.SetParent(root.transform);
            trunk.transform.localPosition = new Vector3(0f, 1.15f * scale, 0f);
            trunk.transform.localScale = new Vector3(0.18f * scale, 1.15f * scale, 0.18f * scale);
            trunk.GetComponent<Renderer>().sharedMaterial = trunkMat;
            var crown = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            crown.name = "PineNeedles";
            crown.transform.SetParent(root.transform);
            crown.transform.localPosition = new Vector3(0f, 2.65f * scale, 0f);
            crown.transform.localScale = new Vector3(1.05f * scale, 1.55f * scale, 1.05f * scale);
            crown.GetComponent<Renderer>().sharedMaterial = foliageMat;
            DisableExpensiveRendererFeatures(root);
        }

        private static void CreateDeadTree(string name, Vector3 pos, float scale, Transform parent, Material deadMat, System.Random rng)
        {
            var root = new GameObject(name);
            root.transform.SetParent(parent);
            root.transform.position = pos;
            root.transform.rotation = Quaternion.Euler(0f, RandomRange(rng, 0f, 360f), RandomRange(rng, -4f, 4f));
            var trunk = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            trunk.name = "DryTrunk";
            trunk.transform.SetParent(root.transform);
            trunk.transform.localPosition = new Vector3(0f, 1.55f * scale, 0f);
            trunk.transform.localScale = new Vector3(0.16f * scale, 1.55f * scale, 0.16f * scale);
            trunk.GetComponent<Renderer>().sharedMaterial = deadMat;
            for (int i = 0; i < 2; i++)
            {
                var branch = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                branch.name = $"DryBranch_{i + 1}";
                branch.transform.SetParent(root.transform);
                branch.transform.localPosition = new Vector3((i == 0 ? 0.22f : -0.20f) * scale, (2.15f + i * 0.25f) * scale, 0f);
                branch.transform.localRotation = Quaternion.Euler(0f, 0f, i == 0 ? -45f : 40f);
                branch.transform.localScale = new Vector3(0.055f * scale, 0.62f * scale, 0.055f * scale);
                branch.GetComponent<Renderer>().sharedMaterial = deadMat;
            }
            DisableExpensiveRendererFeatures(root);
        }

        private static void CreateRock(string name, Vector3 pos, float scale, Transform parent, Material rockMat, System.Random rng)
        {
            var rock = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            rock.name = name;
            rock.transform.SetParent(parent);
            rock.transform.position = pos + new Vector3(0f, 0.18f * scale, 0f);
            rock.transform.rotation = Quaternion.Euler(RandomRange(rng, 0f, 20f), RandomRange(rng, 0f, 360f), RandomRange(rng, 0f, 20f));
            rock.transform.localScale = new Vector3(RandomRange(rng, 0.8f, 1.8f) * scale, RandomRange(rng, 0.25f, 0.75f) * scale, RandomRange(rng, 0.7f, 1.6f) * scale);
            rock.GetComponent<Renderer>().sharedMaterial = rockMat;
            DisableExpensiveRendererFeatures(rock);
        }

        private static void DisableExpensiveRendererFeatures(GameObject root)
        {
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
            {
                renderer.shadowCastingMode = ShadowCastingMode.Off;
                renderer.receiveShadows = false;
            }
        }

        private static object FindAssets(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string type = p["type"]?.ToString() ?? "";
            int max = p["max_results"]?.ToObject<int>() ?? 50;
            JArray foldersArray = p["folders"] as JArray;
            if (max <= 0) max = 50;
            string filter = string.IsNullOrWhiteSpace(type) ? query : $"{query} t:{type}";
            string[] folders = null;
            if (foldersArray != null)
            {
                folders = foldersArray.Select(f => f.ToString()).Where(s => !string.IsNullOrWhiteSpace(s)).ToArray();
                if (folders.Length == 0) folders = null;
            }
            string[] guids = folders == null ? AssetDatabase.FindAssets(filter) : AssetDatabase.FindAssets(filter, folders);
            var results = new List<object>();
            foreach (var guid in guids.Take(max))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var mainType = AssetDatabase.GetMainAssetTypeAtPath(path);
                results.Add(new { guid = guid, path = path, main_type = mainType != null ? mainType.Name : "" });
            }
            return new { ok = true, query = query, type = type, filter = filter, count = guids.Length, results = results };
        }

        private static object ListPrefabs(JObject p)
        {
            string folder = p["folder"]?.ToString() ?? "Assets";
            int max = p["max_results"]?.ToObject<int>() ?? 200;
            if (max <= 0) max = 200;
            string[] guids = AssetDatabase.FindAssets("t:Prefab", new[] { folder });
            var results = new List<object>();
            foreach (var guid in guids.Take(max))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                results.Add(new { guid = guid, path = path });
            }
            return new { ok = true, folder = folder, count = guids.Length, results = results };
        }
    }
}

