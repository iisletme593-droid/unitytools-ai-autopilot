// Unity Editor command handlers. All methods run on the Unity main thread.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
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

