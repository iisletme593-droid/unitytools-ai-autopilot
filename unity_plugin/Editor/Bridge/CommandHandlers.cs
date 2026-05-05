// Unity Editor command handlers. All methods run on the Unity main thread.

using System;
using System.Collections.Generic;
using System.IO;
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
                case "list_scene_objects": return ListSceneObjects();
                case "create_primitive": return CreatePrimitive(p);
                case "set_transform": return SetTransform(p);
                case "set_material_color": return SetMaterialColor(p);
                case "import_asset": return ImportAsset(p);
                case "save_scene": return SaveScene();
                case "open_scene": return OpenScene(p);
                case "execute_menu_item": return ExecuteMenuItem(p);
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

        private static object ListSceneObjects()
        {
            var scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects();
            var list = new List<object>();
            foreach (var root in roots)
            {
                AppendHierarchy(root, list, 0);
            }
            return new { scene = scene.name, objects = list, count = list.Count };
        }

        private static void AppendHierarchy(GameObject go, List<object> list, int depth)
        {
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
                AppendHierarchy(child.gameObject, list, depth + 1);
            }
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
            return new { name = go.name, instance_id = go.GetInstanceID() };
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
    }
}
