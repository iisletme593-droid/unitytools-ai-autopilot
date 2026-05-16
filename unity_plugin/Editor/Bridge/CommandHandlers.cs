// Unity Editor command handlers. All methods run on the Unity main thread.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
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
                case "set_scale": return SetScale(p);
                case "set_position": return SetPosition(p);
                case "set_rotation": return SetRotation(p);
                case "set_material_color": return SetMaterialColor(p);
                case "import_asset": return ImportAsset(p);
                case "save_scene": return SaveScene();
                case "list_scenes": return ListScenes(p);
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
                case "set_audio_source": return SetAudioSource(p);
                case "set_light_properties": return SetLightProperties(p);
                case "set_ambient_light": return SetAmbientLight(p);
                case "list_lights": return ListLights(p);
                case "set_camera_transform": return SetCameraTransform(p);
                case "frame_object": return FrameObject(p);
                case "set_scene_view": return SetSceneView(p);
                case "list_cameras": return ListCameras(p);
                case "add_particle_system": return AddParticleSystem(p);
                case "set_particle_properties": return SetParticleProperties(p);
                case "list_particle_systems": return ListParticleSystems(p);
                case "create_ui_canvas": return CreateUICanvas(p);
                case "create_ui_text": return CreateUIText(p);
                case "create_ui_button": return CreateUIButton(p);
                case "list_ui_elements": return ListUIElements(p);
                case "build_player": return BuildPlayer(p);
                case "list_build_scenes": return ListBuildScenes(p);
                case "add_scene_to_build": return AddSceneToBuild(p);
                case "attach_behaviour": return AttachBehaviour(p);
                case "list_behaviour_library": return ListBehaviourLibrary(p);
                case "list_attached_behaviours": return ListAttachedBehaviours(p);
                case "set_skybox": return SetSkybox(p);
                case "set_fog": return SetFog(p);
                case "get_atmosphere_state": return GetAtmosphereState(p);
                case "set_material_pbr": return SetMaterialPbr(p);
                case "get_material_properties": return GetMaterialProperties(p);
                case "set_player_settings": return SetPlayerSettings(p);
                case "get_player_settings": return GetPlayerSettings(p);
                case "find_by_tag": return FindByTag(p);
                case "find_assets": return FindAssets(p);
                case "list_prefabs": return ListPrefabs(p);
                case "get_editor_state": return GetEditorState();
                case "get_scene_catalog": return GetSceneCatalog(p);
                case "find_scene_objects_semantic": return FindSceneObjectsSemantic(p);
                case "delete_scene_objects_semantic": return DeleteSceneObjectsSemantic(p);
                case "apply_material_palette": return ApplyMaterialPalette(p);
                case "diagnose_material_issues": return DiagnoseMaterialIssues(p);
                case "repair_material_issues": return RepairMaterialIssues(p);
                case "repair_texture_import_settings": return RepairTextureImportSettings(p);
                case "create_optimized_forest_scene": return CreateOptimizedForestScene(p);
                case "optimize_editor_performance": return OptimizeEditorPerformance(p);
                case "run_visual_qa": return RunVisualQA(p);
                case "profile_scene_performance": return ProfileScenePerformance(p);
                case "analyze_lod_decimation_candidates": return AnalyzeLodDecimationCandidates(p);
                case "apply_lod_decimation_plan": return ApplyLodDecimationPlan(p);
                case "create_scene_snapshot": return CreateSceneSnapshot(p);
                case "restore_scene_snapshot": return RestoreSceneSnapshot(p);
                case "setup_hdrp_volume": return SetupHdrpVolume(p);
                case "list_root_objects": return ListRootObjects(p);
                case "assign_material_asset": return AssignMaterialAsset(p);
                case "build_terrain_from_heightmap": return BuildTerrainFromHeightmap(p);
                case "fix_terrain_material": return FixTerrainMaterial(p);
                case "scatter_terrain_trees": return ScatterTerrainTrees(p);
                case "scatter_terrain_grass": return ScatterTerrainGrass(p);
                case "scatter_terrain_glb_trees": return ScatterTerrainGlbTrees(p);
                case "place_asset_on_terrain": return PlaceAssetOnTerrain(p);
                case "repaint_terrain_biomes": return RepaintTerrainBiomes(p);
                case "apply_terrain_pbr_layers": return ApplyTerrainPbrLayers(p);
                case "fix_terrain_hdrp_material": return FixTerrainHdrpMaterial(p);
                case "list_terrains": return ListTerrains(p);
                case "setup_smart_camera": return SetupSmartCamera(p);
                case "make_terrain_playable": return MakeTerrainPlayable(p);
                case "wire_playable_slice": return WirePlayableSlice(p);
                default: throw new InvalidOperationException($"Unknown method: {method}");
            }
        }

        // ── Phase 91: real-world terrain. Python fetches a heightmap
        // from a free elevation API (Open-Meteo) and posts it here as
        // a flat float list (res*res, row-major, normalized 0..1).
        // We sculpt a Unity Terrain + paint biome ground by elevation
        // band (plains / forest-floor / rock) using procedural
        // TerrainLayers — bypasses the broken GLB-material pipeline
        // entirely (terrain layers are independent of mesh materials).
        private static Texture2D SolidTex(Color c, string name)
        {
            var t = new Texture2D(8, 8) { name = name };
            var px = new Color[64];
            for (int i = 0; i < 64; i++) px[i] = c;
            t.SetPixels(px); t.Apply();
            return t;
        }

        // HDRP terrains render invisible/grey without an HDRP terrain
        // material. Try the pipeline-correct shader; degrade silently
        // on built-in/URP (default terrain material is fine there).
        // Phase 111 ROOT CAUSE: the scene has >1 Terrain (the big playable
        // "WorldTerrain" plus a small leftover "Terrain_ForestGround_
        // 500x500"). Every handler used FindObjectsByType<Terrain>()
        // .FirstOrDefault(), which grabbed the WRONG (small/invisible)
        // one — so all the real PBR ground/biome work landed on a
        // terrain nobody sees, and WorldTerrain stayed pale. Resolve the
        // intended terrain deterministically: explicit terrain_name ->
        // "WorldTerrain" -> the LARGEST by area -> first.
        private static Terrain ResolveSceneTerrain(JObject p)
        {
            var all = UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsInactive.Exclude);
            if (all == null || all.Length == 0) return null;
            string wanted = p?["terrain_name"]?.ToString();
            if (!string.IsNullOrEmpty(wanted))
            {
                var named = all.FirstOrDefault(t => t.name == wanted);
                if (named != null) return named;
            }
            var world = all.FirstOrDefault(t => t.name == "WorldTerrain");
            if (world != null && TerrainRelief(world) > 0.001f) return world;
            // Score: strongly prefer terrains that actually have relief
            // (the visible playable one) over the many flat [0,0] tiles,
            // then by area. This is why earlier PBR kept landing on a
            // flat invisible tile.
            Terrain best = all[0];
            float bestScore = -1f;
            foreach (var t in all)
            {
                if (t.terrainData == null) continue;
                float area = t.terrainData.size.x * t.terrainData.size.z;
                float relief = TerrainRelief(t);
                float score = area * (relief > 0.001f ? 1000f : 1f) + relief * 1e6f;
                if (score > bestScore) { bestScore = score; best = t; }
            }
            return best;
        }

        private static float TerrainRelief(Terrain t)
        {
            if (t == null || t.terrainData == null) return 0f;
            var td = t.terrainData;
            int r = Mathf.Min(33, td.heightmapResolution);
            float[,] hs = td.GetHeights(0, 0, r, r);
            float mn = float.MaxValue, mx = float.MinValue;
            for (int y = 0; y < r; y++)
                for (int x = 0; x < r; x++)
                { float v = hs[y, x]; if (v < mn) mn = v; if (v > mx) mx = v; }
            return (mx - mn) * td.size.y;
        }

        private static object ListTerrains(JObject p)
        {
            var all = UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsInactive.Include);
            var rows = new List<object>();
            foreach (var t in all)
            {
                var td = t.terrainData;
                rows.Add(new
                {
                    name = t.name,
                    active = t.gameObject.activeInHierarchy,
                    pos = new[] { t.transform.position.x, t.transform.position.y, t.transform.position.z },
                    size = td != null ? new[] { td.size.x, td.size.y, td.size.z } : new[] { 0f, 0f, 0f },
                    relief_m = TerrainRelief(t),
                    layers = td != null ? td.terrainLayers.Length : 0,
                    shader = t.materialTemplate != null && t.materialTemplate.shader != null
                             ? t.materialTemplate.shader.name : "(none)",
                });
            }
            var chosen = ResolveSceneTerrain(p);
            return new { ok = true, count = rows.Count, terrains = rows,
                         resolved = chosen != null ? chosen.name : "(none)" };
        }

        private static string ApplyTerrainPipelineMaterial(Terrain terrain)
        {
            if (terrain == null) return "no-terrain";

            // 1) HDRP/URP's OWN default terrain material via reflection on
            //    the active RenderPipelineAsset. This is the reliable path
            //    — Shader.Find("HDRP/TerrainLit") returns null on a fresh
            //    boot because the shader isn't in Always-Included, so the
            //    old code silently fell back to the broken built-in shader
            //    (the pale-desert look).
            var rpAsset = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline
                          ?? UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline;
            if (rpAsset != null)
            {
                var t = rpAsset.GetType();
                foreach (var member in new[] { "defaultTerrainMaterial", "GetDefaultTerrainMaterial" })
                {
                    try
                    {
                        Material dm = null;
                        var prop = t.GetProperty(member,
                            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                        if (prop != null) dm = prop.GetValue(rpAsset) as Material;
                        if (dm == null)
                        {
                            var meth = t.GetMethod(member,
                                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic,
                                null, System.Type.EmptyTypes, null);
                            if (meth != null) dm = meth.Invoke(rpAsset, null) as Material;
                        }
                        if (dm != null && dm.shader != null)
                        {
                            terrain.materialTemplate = new Material(dm) { name = "UnityTools_TerrainMat" };
                            return "rp-default:" + dm.shader.name;
                        }
                    }
                    catch { /* try next */ }
                }
            }

            // 2) Any existing project material that uses an SRP terrain shader.
            foreach (var guid in AssetDatabase.FindAssets("t:Material"))
            {
                var mp = AssetDatabase.GUIDToAssetPath(guid);
                var mm = AssetDatabase.LoadAssetAtPath<Material>(mp);
                var sn = mm?.shader != null ? mm.shader.name : "";
                if (sn.IndexOf("TerrainLit", StringComparison.OrdinalIgnoreCase) >= 0
                    || sn.IndexOf("Terrain/Lit", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    terrain.materialTemplate = new Material(mm) { name = "UnityTools_TerrainMat" };
                    return "asset:" + sn;
                }
            }

            // 3) Shader.Find as a last resort (works once a layer/material
            //    has loaded the shader into memory).
            foreach (var shn in new[] { "HDRP/TerrainLit", "Universal Render Pipeline/Terrain/Lit" })
            {
                var sh = Shader.Find(shn);
                if (sh != null)
                {
                    terrain.materialTemplate = new Material(sh) { name = "UnityTools_TerrainMat" };
                    return "shaderfind:" + shn;
                }
            }
            return "builtin-default";
        }

        // Phase 111: standalone diagnose+fix for the terrain HDRP material
        // (returns the resolved material/shader so QA can confirm).
        private static object FixTerrainHdrpMaterial(JObject p)
        {
            var terrain = ResolveSceneTerrain(p);
            if (terrain == null)
                return new { ok = false, error = "No Terrain in scene" };
            string before = terrain.materialTemplate != null && terrain.materialTemplate.shader != null
                ? terrain.materialTemplate.shader.name : "(none)";
            string resolved = ApplyTerrainPipelineMaterial(terrain);
            terrain.basemapDistance = 20000f;
            terrain.heightmapPixelError = 2f;
            try { if (terrain.terrainData != null) terrain.terrainData.SetBaseMapDirty(); } catch { }
            terrain.Flush();
            string after = terrain.materialTemplate != null && terrain.materialTemplate.shader != null
                ? terrain.materialTemplate.shader.name : "(none)";
            int layerCount = terrain.terrainData != null ? terrain.terrainData.terrainLayers.Length : 0;
            string firstTex = "(none)";
            if (layerCount > 0 && terrain.terrainData.terrainLayers[0] != null
                && terrain.terrainData.terrainLayers[0].diffuseTexture != null)
                firstTex = terrain.terrainData.terrainLayers[0].diffuseTexture.name;
            if (terrain.terrainData != null) EditorUtility.SetDirty(terrain.terrainData);
            EditorUtility.SetDirty(terrain);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                resolved,
                shader_before = before,
                shader_after = after,
                terrain_layer_count = layerCount,
                first_layer_diffuse = firstTex,
                rp = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null
                     ? UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline.GetType().Name : "(builtin)",
            };
        }

        // ── Phase 95: the SMART playability layer. A 16 km real-world
        // terrain is geographically true but unplayable — a 1.8 m human
        // is a speck. This reasons about scale: shrinks the terrain to
        // a human-explorable footprint (heightmap SHAPE preserved),
        // recenters it, finds a good valley/meadow spawn (mid-low
        // elevation + low slope) by scanning the heightmap, drops the
        // character ON the surface there, and frames a third-person
        // human-scale camera behind it. One intelligent call.
        private static object MakeTerrainPlayable(JObject p)
        {
            float footprint = p["footprint_m"]?.ToObject<float>() ?? 1200f; // playable XZ
            float reliefScale = p["relief_scale"]?.ToObject<float>() ?? 0.16f; // y = footprint*this
            string charName = p["character"]?.ToString() ?? "SK_Hero";
            float charScale = p["character_scale"]?.ToObject<float>() ?? 1.0f;

            var terrain = ResolveSceneTerrain(p);
            if (terrain == null)
                return new { ok = false, error = "No Terrain in scene" };
            var td = terrain.terrainData;

            // 1) Rescale to a human-explorable footprint, keep heightmap.
            float yH = footprint * reliefScale;
            td.size = new Vector3(footprint, yH, footprint);
            // recenter so terrain centre = world origin
            terrain.transform.position = new Vector3(-footprint / 2f, 0f, -footprint / 2f);

            // 2) Scan heightmap for a good spawn: mid-low elevation +
            // low local slope, biased toward the centre (a meadow).
            int hr = td.heightmapResolution;
            float[,] hs = td.GetHeights(0, 0, hr, hr);
            float hMin = float.MaxValue, hMax = float.MinValue;
            for (int y = 0; y < hr; y++)
                for (int x = 0; x < hr; x++)
                { float hv = hs[y, x]; if (hv < hMin) hMin = hv; if (hv > hMax) hMax = hv; }
            float span = Mathf.Max(1e-5f, hMax - hMin);

            int bestX = hr / 2, bestY = hr / 2; float bestScore = -1f;
            for (int gy = 4; gy < hr - 4; gy += 2)
            {
                for (int gx = 4; gx < hr - 4; gx += 2)
                {
                    float hn = (hs[gy, gx] - hMin) / span;
                    // local slope from neighbour delta
                    float slope = Mathf.Abs(hs[gy, gx] - hs[gy, gx + 2])
                                + Mathf.Abs(hs[gy, gx] - hs[gy + 2, gx]);
                    // want hn ~0.30 (low valley meadow), flat, near centre
                    float fEle = 1f - Mathf.Abs(hn - 0.30f) / 0.30f;
                    float fFlat = 1f - Mathf.Clamp01(slope * 40f);
                    float cx = (gx / (float)hr - 0.5f), cy = (gy / (float)hr - 0.5f);
                    float fCen = 1f - Mathf.Clamp01(Mathf.Sqrt(cx * cx + cy * cy) * 1.6f);
                    float score = fEle * 0.4f + fFlat * 0.45f + fCen * 0.15f;
                    if (score > bestScore) { bestScore = score; bestX = gx; bestY = gy; }
                }
            }
            float u = bestX / (float)(hr - 1), v = bestY / (float)(hr - 1);
            float wx = terrain.transform.position.x + u * footprint;
            float wz = terrain.transform.position.z + v * footprint;
            float wy = terrain.transform.position.y + td.GetInterpolatedHeight(u, v);

            // 3) Place the character ON the surface there.
            string placed = "not-found";
            var ch = GameObject.Find(charName);
            if (ch != null)
            {
                ch.transform.position = new Vector3(wx, wy, wz);
                ch.transform.localScale = Vector3.one * charScale;
                ch.transform.rotation = Quaternion.Euler(0f, 135f, 0f);
                placed = $"{wx:0},{wy:0},{wz:0}";
            }

            // 4) Third-person human-scale camera behind + above.
            var camGo = GameObject.Find("Main Camera")
                        ?? new GameObject("Main Camera");
            var cam = camGo.GetComponent<Camera>() ?? camGo.AddComponent<Camera>();
            try { camGo.tag = "MainCamera"; } catch { }
            cam.nearClipPlane = 0.2f;
            cam.farClipPlane = Mathf.Max(2500f, footprint * 2.2f);
            cam.fieldOfView = 60f;
            Vector3 charPos = new Vector3(wx, wy, wz);
            Vector3 back = Quaternion.Euler(0f, 135f, 0f) * Vector3.back;
            camGo.transform.position = charPos + back * 9f + Vector3.up * 4f;
            camGo.transform.rotation = Quaternion.LookRotation(
                ((charPos + Vector3.up * 1.4f) - camGo.transform.position).normalized, Vector3.up);
            var hdCamType = FindType("UnityEngine.Rendering.HighDefinition.HDAdditionalCameraData");
            if (hdCamType != null && camGo.GetComponent(hdCamType) == null)
                camGo.AddComponent(hdCamType);

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                footprint_m = footprint,
                relief_m = yH,
                spawn = placed,
                spawn_score = bestScore,
                character = charName,
                note = "terrain rescaled to playable footprint; character on surface; third-person cam",
            };
        }

        // ── Phase 94: a SMART inspection camera. Auto-frames a target
        // (default: the terrain) with clip planes correct for huge
        // worlds (the "view disappears when you zoom" bug = far-clip
        // too small for a 16 km terrain). Also attaches HDRP camera
        // data via reflection so the SRP render path (and screenshots)
        // actually work. This is the system getting smarter about
        // seeing the scene instead of blind hand-tuning.
        private static object SetupSmartCamera(JObject p)
        {
            string targetName = p["target"]?.ToString() ?? "WorldTerrain";
            float pitch = p["pitch"]?.ToObject<float>() ?? 28f;
            float yaw = p["yaw"]?.ToObject<float>() ?? 35f;
            float distFactor = p["distance_factor"]?.ToObject<float>() ?? 0.62f;

            var go = GameObject.Find("Main Camera");
            if (go == null)
            {
                go = new GameObject("Main Camera");
                Undo.RegisterCreatedObjectUndo(go, "UnityTools: smart camera");
            }
            var cam = go.GetComponent<Camera>() ?? go.AddComponent<Camera>();
            try { go.tag = "MainCamera"; } catch { }

            // Bounds of the target (terrain or any renderered object).
            Bounds b = new Bounds(Vector3.zero, new Vector3(200, 50, 200));
            var tgt = GameObject.Find(targetName);
            var terr = ResolveSceneTerrain(p);
            if (tgt != null && tgt.GetComponent<Terrain>() != null) terr = tgt.GetComponent<Terrain>();
            if (terr != null)
            {
                var td = terr.terrainData;
                b = new Bounds(terr.transform.position + td.size * 0.5f, td.size);
            }
            else if (tgt != null)
            {
                var rs = tgt.GetComponentsInChildren<Renderer>();
                if (rs.Length > 0)
                {
                    b = rs[0].bounds;
                    foreach (var r in rs) b.Encapsulate(r.bounds);
                }
            }

            float radius = b.extents.magnitude;
            // clip planes scaled to the world so nothing vanishes:
            cam.nearClipPlane = Mathf.Max(0.05f, radius * 0.0002f);
            cam.farClipPlane = Mathf.Max(5000f, radius * 6f);
            cam.fieldOfView = 60f;

            float dist = radius * Mathf.Max(0.15f, distFactor) * 2f;
            var rot = Quaternion.Euler(pitch, yaw, 0f);
            Vector3 dir = rot * Vector3.forward;
            go.transform.position = b.center - dir * dist + Vector3.up * (radius * 0.35f);
            go.transform.rotation = Quaternion.LookRotation((b.center - go.transform.position).normalized, Vector3.up);

            // HDRP camera data (reflection — no asmdef dep). Without it
            // the SRP render path / screenshots can produce nothing.
            var hdCamType = FindType("UnityEngine.Rendering.HighDefinition.HDAdditionalCameraData");
            string hdNote = "none";
            if (hdCamType != null)
            {
                var hd = go.GetComponent(hdCamType) ?? go.AddComponent(hdCamType);
                hdNote = hd != null ? "HDAdditionalCameraData attached" : "failed";
            }

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                camera = go.name,
                target = targetName,
                world_radius = radius,
                near = cam.nearClipPlane,
                far = cam.farClipPlane,
                position = new[] { go.transform.position.x, go.transform.position.y, go.transform.position.z },
                hdrp_camera = hdNote,
                note = "auto-framed; clip planes scaled to world (no more zoom-vanish)",
            };
        }

        // ── Phase 93: repaint terrain biome bands from the EXISTING
        // terrain (no elevation re-fetch). Normalizes by the terrain's
        // OWN min/max height so the bands adapt to the real relief
        // distribution — fixes "Alpine data is all high -> all white
        // rock/snow". Tunable band cutoffs (as 0..1 percentiles of the
        // terrain's own height range) + colours. Deterministic + live.
        private static object RepaintTerrainBiomes(JObject p)
        {
            float plainsTo = p["plains_to"]?.ToObject<float>() ?? 0.30f;
            float forestTo = p["forest_to"]?.ToObject<float>() ?? 0.64f;
            float rockTo   = p["rock_to"]?.ToObject<float>() ?? 0.88f;

            Color cPlain  = ReadColor(p["plains_color"], new Color(0.27f, 0.42f, 0.18f));
            Color cForest = ReadColor(p["forest_color"], new Color(0.14f, 0.27f, 0.13f));
            Color cRock   = ReadColor(p["rock_color"],   new Color(0.40f, 0.39f, 0.37f));
            Color cSnow   = ReadColor(p["snow_color"],   new Color(0.90f, 0.92f, 0.95f));

            var terrain = ResolveSceneTerrain(p);
            if (terrain == null)
                return new { ok = false, error = "No Terrain in scene" };
            var td = terrain.terrainData;

            int hr = td.heightmapResolution;
            float[,] hs = td.GetHeights(0, 0, hr, hr);
            float hMin = float.MaxValue, hMax = float.MinValue;
            for (int y = 0; y < hr; y++)
                for (int x = 0; x < hr; x++)
                {
                    float v = hs[y, x];
                    if (v < hMin) hMin = v;
                    if (v > hMax) hMax = v;
                }
            float span = Mathf.Max(1e-5f, hMax - hMin);

            td.terrainLayers = new[]
            {
                new TerrainLayer { diffuseTexture = SolidTex(cPlain,  "Plains"),      tileSize = new Vector2(20, 20) },
                new TerrainLayer { diffuseTexture = SolidTex(cForest, "ForestFloor"), tileSize = new Vector2(20, 20) },
                new TerrainLayer { diffuseTexture = SolidTex(cRock,   "Rock"),        tileSize = new Vector2(20, 20) },
                new TerrainLayer { diffuseTexture = SolidTex(cSnow,   "Snow"),        tileSize = new Vector2(20, 20) },
            };

            int aw = td.alphamapWidth, ah = td.alphamapHeight;
            var a = new float[ah, aw, 4];
            for (int y = 0; y < ah; y++)
            {
                for (int x = 0; x < aw; x++)
                {
                    int hy = Mathf.Clamp(Mathf.RoundToInt((float)y / (ah - 1) * (hr - 1)), 0, hr - 1);
                    int hx = Mathf.Clamp(Mathf.RoundToInt((float)x / (aw - 1) * (hr - 1)), 0, hr - 1);
                    float hn = (hs[hy, hx] - hMin) / span;     // 0..1 over real range
                    // soft band membership centred in each percentile slice
                    float wP = Band(hn, 0f, plainsTo);
                    float wF = Band(hn, plainsTo, forestTo);
                    float wR = Band(hn, forestTo, rockTo);
                    float wS = Band(hn, rockTo, 1.001f);
                    float s = wP + wF + wR + wS + 1e-4f;
                    a[y, x, 0] = wP / s; a[y, x, 1] = wF / s;
                    a[y, x, 2] = wR / s; a[y, x, 3] = wS / s;
                }
            }
            td.SetAlphamaps(0, 0, a);
            ApplyTerrainPipelineMaterial(terrain);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                terrain = terrain.name,
                height_range_norm = new[] { hMin, hMax },
                cutoffs = new[] { plainsTo, forestTo, rockTo },
                note = "repainted by terrain's own relief percentile (no re-fetch)",
            };
        }

        // Phase 107: paint the terrain with REAL PBR ground/rock textures
        // (diffuse + normal) instead of flat solid-colour splats. Same
        // relief-percentile band logic as RepaintTerrainBiomes, but each
        // band is a proper TerrainLayer asset built from the project's
        // 2K AmbientCG-style sets. layers = ordered low->high array of
        // { name, diffuse, normal, tile }. cutoffs = (len-1) norm splits.
        private static object ApplyTerrainPbrLayers(JObject p)
        {
            var layersIn = p["layers"] as JArray;
            if (layersIn == null || layersIn.Count < 2)
                return new { ok = false, error = "layers[] (>=2) required: {name,diffuse,normal,tile}" };
            int n = Mathf.Clamp(layersIn.Count, 2, 8);

            var cutoffsIn = p["cutoffs"] as JArray;
            var cutoffs = new List<float>();
            if (cutoffsIn != null)
                foreach (var c in cutoffsIn) cutoffs.Add(c.ToObject<float>());
            // default = even percentile splits
            while (cutoffs.Count < n - 1)
                cutoffs.Add((cutoffs.Count + 1) / (float)n);

            var terrain = ResolveSceneTerrain(p);
            if (terrain == null)
                return new { ok = false, error = "No Terrain in scene" };
            var td = terrain.terrainData;

            const string layerDir = "Assets/FantasyRPG/Generated/TerrainLayers";
            Directory.CreateDirectory(Path.Combine(ProjectRootPath(), layerDir.Replace("/", Path.DirectorySeparatorChar.ToString())));

            // Force normal-map textures to be imported as NormalMap so the
            // terrain shader reads them correctly (not as colour data).
            void EnsureNormalImport(string ap)
            {
                if (string.IsNullOrEmpty(ap)) return;
                var ti = AssetImporter.GetAtPath(ap) as TextureImporter;
                if (ti != null && ti.textureType != TextureImporterType.NormalMap)
                {
                    ti.textureType = TextureImporterType.NormalMap;
                    ti.SaveAndReimport();
                }
            }

            var built = new List<string>();
            var tlayers = new TerrainLayer[n];
            for (int i = 0; i < n; i++)
            {
                var lo = layersIn[i] as JObject;
                string nm = lo?["name"]?.ToString() ?? $"Layer{i}";
                string diff = lo?["diffuse"]?.ToString();
                string nrm = lo?["normal"]?.ToString();
                float tile = lo?["tile"]?.ToObject<float>() ?? 12f;

                var dTex = string.IsNullOrEmpty(diff) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(diff);
                if (dTex == null)
                    return new { ok = false, error = $"Diffuse not found for {nm}: {diff}" };
                EnsureNormalImport(nrm);
                var nTex = string.IsNullOrEmpty(nrm) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(nrm);

                var tl = new TerrainLayer
                {
                    diffuseTexture = dTex,
                    normalMapTexture = nTex,
                    tileSize = new Vector2(tile, tile),
                    normalScale = 0.8f,
                    smoothness = 0.10f,
                    metallic = 0.0f,
                };
                string tlPath = $"{layerDir}/TL_{nm}.terrainlayer";
                if (AssetDatabase.LoadAssetAtPath<TerrainLayer>(tlPath) != null)
                    AssetDatabase.DeleteAsset(tlPath);
                AssetDatabase.CreateAsset(tl, tlPath);
                tlayers[i] = AssetDatabase.LoadAssetAtPath<TerrainLayer>(tlPath);
                built.Add($"{nm}<-{Path.GetFileName(diff)}{(nTex != null ? "+N" : "")}");
            }
            td.terrainLayers = tlayers;

            // Relief-percentile alphamap (real height range, soft bands).
            int hr = td.heightmapResolution;
            float[,] hs = td.GetHeights(0, 0, hr, hr);
            float hMin = float.MaxValue, hMax = float.MinValue;
            for (int y = 0; y < hr; y++)
                for (int x = 0; x < hr; x++)
                {
                    float hv = hs[y, x];
                    if (hv < hMin) hMin = hv;
                    if (hv > hMax) hMax = hv;
                }
            float span = Mathf.Max(1e-5f, hMax - hMin);

            int aw = td.alphamapWidth, ah = td.alphamapHeight;
            var a = new float[ah, aw, n];
            var edges = new float[n + 1];
            edges[0] = 0f; edges[n] = 1.001f;
            for (int i = 0; i < n - 1; i++) edges[i + 1] = Mathf.Clamp01(cutoffs[i]);
            for (int y = 0; y < ah; y++)
            {
                for (int x = 0; x < aw; x++)
                {
                    int hy = Mathf.Clamp(Mathf.RoundToInt((float)y / (ah - 1) * (hr - 1)), 0, hr - 1);
                    int hx = Mathf.Clamp(Mathf.RoundToInt((float)x / (aw - 1) * (hr - 1)), 0, hr - 1);
                    float hn = (hs[hy, hx] - hMin) / span;
                    float s = 1e-4f;
                    for (int i = 0; i < n; i++)
                    {
                        float w = Band(hn, edges[i], edges[i + 1]);
                        a[y, x, i] = w; s += w;
                    }
                    for (int i = 0; i < n; i++) a[y, x, i] /= s;
                }
            }
            td.SetAlphamaps(0, 0, a);
            string matResolved = ApplyTerrainPipelineMaterial(terrain);
            // Push the splat through: regenerate the basemap and Flush,
            // and render the detailed splat at any distance (the pale
            // far-view was the stale/blank low-res basemap showing).
            terrain.basemapDistance = 20000f;
            terrain.heightmapPixelError = 2f;
            try { td.SetBaseMapDirty(); } catch { }
            terrain.Flush();
            // CRITICAL: terrainData is an ASSET. Without SetDirty the
            // terrainLayers/alphamap assignment is NOT written by
            // SaveAssets and reverts to 0 layers on scene/domain reload
            // (the real reason the ground kept going pale).
            EditorUtility.SetDirty(td);
            EditorUtility.SetDirty(terrain);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                terrain = terrain.name,
                terrain_material = matResolved,
                layers = built,
                cutoffs = edges.Skip(1).Take(n - 1).ToArray(),
                height_range = new[] { hMin, hMax },
                note = "real PBR ground/rock layers (diffuse+normal), relief-percentile bands",
            };
        }

        private static float Band(float v, float lo, float hi)
        {
            // 1 inside [lo,hi], soft 12%-of-span feather at each edge
            float feather = Mathf.Max(0.02f, (hi - lo) * 0.30f);
            if (v < lo) return Mathf.Clamp01(1f - (lo - v) / feather);
            if (v > hi) return Mathf.Clamp01(1f - (v - hi) / feather);
            return 1f;
        }

        private static Color ReadColor(JToken t, Color def)
        {
            if (t is JArray ja && ja.Count >= 3)
                return new Color(ja[0].ToObject<float>(), ja[1].ToObject<float>(),
                                 ja[2].ToObject<float>());
            return def;
        }

        // ── Phase 92: scatter sparse procedural pines on the real-world
        // terrain, only in a mid-elevation "forest" band and off steep
        // slopes. Procedural + HDRP-correct materials (PipelineLitShader)
        // so it sidesteps the broken GLB-material pipeline entirely.
        private static object ScatterTerrainTrees(JObject p)
        {
            int attempts = Mathf.Clamp(p["tree_count"]?.ToObject<int>() ?? 220, 1, 5000);
            float bandMin = p["forest_min"]?.ToObject<float>() ?? 0.16f; // norm height
            float bandMax = p["forest_max"]?.ToObject<float>() ?? 0.52f;
            float maxSlope = p["max_slope_deg"]?.ToObject<float>() ?? 32f;
            float sMin = p["scale_min"]?.ToObject<float>() ?? 8f;
            float sMax = p["scale_max"]?.ToObject<float>() ?? 16f;
            int seed = p["seed"]?.ToObject<int>() ?? 9090;

            var terrain = ResolveSceneTerrain(p);
            if (terrain == null)
                return new { ok = false, error = "No Terrain in scene (build it first)" };
            var td = terrain.terrainData;
            Vector3 tp = terrain.transform.position;
            float sizeX = td.size.x, sizeZ = td.size.z, sizeY = td.size.y;

            var existing = GameObject.Find("WorldForest");
            if (existing != null) Undo.DestroyObjectImmediate(existing);
            // Also nuke any leftover WorldForestGLB from abandoned FBX
            // tree experiments (broken white-speckle / huge-dark clusters)
            // so the procedural forest is the ONLY forest in the scene.
            var glbJunk = GameObject.Find("WorldForestGLB");
            if (glbJunk != null) Undo.DestroyObjectImmediate(glbJunk);
            var forestRoot = new GameObject("WorldForest");
            Undo.RegisterCreatedObjectUndo(forestRoot, "UnityTools: world forest");

            // Colours sampled from the user's real Tree1 download
            // (free3d): mean of the opaque conifer-needle pixels and of
            // the bark photo. Real-derived palette on the proven solid
            // geometry (reliable; runtime alpha-card path failed in HDRP).
            var trunkMat = MakeMaterial("Pine_Trunk_RealColor_HDRP",
                new Color(0.363f, 0.326f, 0.244f), 0.10f);
            var foliageMat = MakeMaterial("Pine_Foliage_RealColor_HDRP",
                new Color(0.330f, 0.366f, 0.162f), 0.12f);

            var rng = new System.Random(seed);
            int placed = 0, bandFail = 0, slopeFail = 0;
            string placeNote = "requested band/slope";
            // Two-pass like the GLB scatter: real-world heightmaps are
            // steep per-sample, so if the requested band/slope rejects
            // everything, retry wide-open so a forest still appears.
            for (int pass = 0; pass < 2; pass++)
            {
                if (pass == 1)
                {
                    if (placed > 0) break;
                    bandMin = 0f; bandMax = 1.01f; maxSlope = 89f;
                    rng = new System.Random(seed);
                    placeNote = "fallback: band/slope too strict, used full range";
                }
            for (int i = 0; i < attempts; i++)
            {
                float u = (float)rng.NextDouble();
                float v = (float)rng.NextDouble();
                float hn = td.GetInterpolatedHeight(u, v) / Mathf.Max(0.001f, sizeY);
                if (hn < bandMin || hn > bandMax) { bandFail++; continue; }
                float steep = td.GetSteepness(u, v);
                if (steep > maxSlope) { slopeFail++; continue; }

                float wx = tp.x + u * sizeX;
                float wz = tp.z + v * sizeZ;
                float wy = tp.y + td.GetInterpolatedHeight(u, v);
                float scl = (float)(sMin + rng.NextDouble() * (sMax - sMin));
                string nm = $"Pine_{placed:000}";
                CreateSimplePine(nm, new Vector3(wx, wy, wz), scl,
                                  forestRoot.transform, trunkMat, foliageMat, rng);
                placed++;
            }
            }  // end pass loop

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                placed,
                attempts,
                band_fail = bandFail,
                slope_fail = slopeFail,
                terrain = terrain.name,
                terrain_relief_m = TerrainRelief(terrain),
                forest_band = new[] { bandMin, bandMax },
                max_slope_deg = maxSlope,
                note = "procedural pines (cylinder trunk + green crown, HDRP-coloured, "
                       + "pivot-at-base so never sunk); " + placeNote,
            };
        }

        // Cached ultra-cheap grass-clump mesh: 3 crossed vertical quads
        // (the classic billboard-grass trick) -> 12 tris, shared by
        // every clump + GPU-instanced. Reliable in-engine (the proven
        // strategy) instead of the 1.5M-tri free3d grass import.
        private static Mesh _grassMesh;
        private static Mesh GrassMesh()
        {
            if (_grassMesh != null) return _grassMesh;
            var verts = new System.Collections.Generic.List<Vector3>();
            var tris = new System.Collections.Generic.List<int>();
            for (int q = 0; q < 3; q++)
            {
                float ang = q * (Mathf.PI / 3f);
                Vector3 d = new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang)) * 0.5f;
                int b = verts.Count;
                verts.Add(-d); verts.Add(d);
                verts.Add(d + Vector3.up); verts.Add(-d + Vector3.up);
                tris.Add(b); tris.Add(b + 2); tris.Add(b + 1);
                tris.Add(b); tris.Add(b + 3); tris.Add(b + 2);
                tris.Add(b); tris.Add(b + 1); tris.Add(b + 2);   // back
                tris.Add(b); tris.Add(b + 2); tris.Add(b + 3);
            }
            _grassMesh = new Mesh { name = "UT_GrassMesh" };
            _grassMesh.SetVertices(verts);
            _grassMesh.SetTriangles(tris, 0);
            _grassMesh.RecalculateNormals();
            _grassMesh.RecalculateBounds();
            return _grassMesh;
        }

        // Cheap procedural ground-cover grass: dense small clumps in the
        // low/valley band, ground-snapped, HDRP-green, shared mesh +
        // instancing + expensive features off. ~12 tris/clump.
        private static object ScatterTerrainGrass(JObject p)
        {
            int count = Mathf.Clamp(p["clump_count"]?.ToObject<int>() ?? 900, 1, 8000);
            float bandMin = p["band_min"]?.ToObject<float>() ?? 0.0f;
            float bandMax = p["band_max"]?.ToObject<float>() ?? 0.55f;
            float maxSlope = p["max_slope_deg"]?.ToObject<float>() ?? 38f;
            float sMin = p["scale_min"]?.ToObject<float>() ?? 1.4f;
            float sMax = p["scale_max"]?.ToObject<float>() ?? 3.2f;
            int seed = p["seed"]?.ToObject<int>() ?? 4242;

            var terrain = ResolveSceneTerrain(p);
            if (terrain == null)
                return new { ok = false, error = "No Terrain in scene" };
            var td = terrain.terrainData;
            Vector3 tp = terrain.transform.position;
            float sx = td.size.x, sz = td.size.z, sy = td.size.y;

            var old = GameObject.Find("WorldGrass");
            if (old != null) Undo.DestroyObjectImmediate(old);
            var root = new GameObject("WorldGrass");
            Undo.RegisterCreatedObjectUndo(root, "UnityTools: grass");
            var grassMat = MakeMaterial("Grass_HDRP",
                new Color(0.17f, 0.30f, 0.13f), 0.18f);
            grassMat.enableInstancing = true;

            var rng = new System.Random(seed);
            int placed = 0;
            for (int i = 0; i < count; i++)
            {
                float u = (float)rng.NextDouble(), v = (float)rng.NextDouble();
                float hn = td.GetInterpolatedHeight(u, v) / Mathf.Max(0.001f, sy);
                if (hn < bandMin || hn > bandMax) continue;
                if (td.GetSteepness(u, v) > maxSlope) continue;
                float wy = tp.y + td.GetInterpolatedHeight(u, v);
                var go = new GameObject($"Grass_{placed:0000}",
                    typeof(MeshFilter), typeof(MeshRenderer));
                go.transform.SetParent(root.transform);
                go.transform.position = new Vector3(tp.x + u * sx, wy, tp.z + v * sz);
                go.transform.rotation = Quaternion.Euler(0f,
                    (float)(rng.NextDouble() * 360.0), 0f);
                float s = (float)(sMin + rng.NextDouble() * (sMax - sMin));
                go.transform.localScale = new Vector3(s, s * 1.3f, s);
                go.GetComponent<MeshFilter>().sharedMesh = GrassMesh();
                go.GetComponent<MeshRenderer>().sharedMaterial = grassMat;
                placed++;
            }
            foreach (Transform t in root.transform)
                DisableExpensiveRendererFeatures(t.gameObject);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true, placed, count,
                terrain = terrain.name,
                note = "cheap procedural ground-cover grass (12 tris/clump, "
                       + "shared mesh, instanced, ground-snapped, HDRP-green)",
            };
        }

        // Phase 106: scatter REAL glTF/GLB tree models onto the terrain surface
        // (replaces the procedural cube/cylinder pines). Keeps good PBR materials,
        // but auto-repairs any white/magenta (non-pipeline / broken) renderer with
        // a known-good HDRP foliage material so trees never render white.
        private static object ScatterTerrainGlbTrees(JObject p)
        {
            int attempts = Mathf.Clamp(p["tree_count"]?.ToObject<int>() ?? 200, 1, 5000);
            float bandMin = p["forest_min"]?.ToObject<float>() ?? 0.16f;  // norm height
            float bandMax = p["forest_max"]?.ToObject<float>() ?? 0.52f;
            float maxSlope = p["max_slope_deg"]?.ToObject<float>() ?? 32f;
            float sMin = p["scale_min"]?.ToObject<float>() ?? 0.6f;
            float sMax = p["scale_max"]?.ToObject<float>() ?? 1.5f;
            float yOffset = p["y_offset"]?.ToObject<float>() ?? 0f;
            float deadRatio = Mathf.Clamp01(p["dead_ratio"]?.ToObject<float>() ?? 0.12f);
            int seed = p["seed"]?.ToObject<int>() ?? 9090;
            bool clearPrimitive = p["clear_primitive_forest"]?.ToObject<bool>() ?? true;

            // Curated default tree set (PolyHaven, present in this project).
            var liveModels = new List<string>();
            var deadModels = new List<string>();
            var modelsParam = p["models"] as JArray;
            if (modelsParam != null && modelsParam.Count > 0)
            {
                foreach (var m in modelsParam) liveModels.Add(m.ToString());
            }
            else
            {
                liveModels.Add("Assets/FantasyRPG/Models/PolyHaven/Nature/Trees/Nature_Trees_04_PineTree.glb");
                liveModels.Add("Assets/FantasyRPG/Models/PolyHaven/Nature/Trees/Nature_Trees_05_FirTree.glb");
                liveModels.Add("Assets/FantasyRPG/Models/PolyHaven/Nature/Trees/Nature_Trees_06_IslandTree.glb");
                deadModels.Add("Assets/FantasyRPG/Models/PolyHaven/Nature/Trees/Nature_Trees_01_DeadTreeTrunk.glb");
            }
            var deadParam = p["dead_models"] as JArray;
            if (deadParam != null)
            {
                deadModels.Clear();
                foreach (var m in deadParam) deadModels.Add(m.ToString());
            }

            string foliageMatPath = p["foliage_material_path"]?.ToString()
                ?? "Assets/FantasyRPG/Generated/Materials/HDRP_M_BlackPineNeedles.mat";
            var foliageMat = AssetDatabase.LoadAssetAtPath<Material>(foliageMatPath);
            // Optional trunk material: when set, a renderer with >=2
            // material slots gets slot 0 = trunk, slots 1+ = foliage
            // (the low-poly Blender conifers are 1 mesh / 2 slots).
            string trunkMatPath = p["trunk_material_path"]?.ToString();
            var trunkMat = string.IsNullOrEmpty(trunkMatPath) ? null
                : AssetDatabase.LoadAssetAtPath<Material>(trunkMatPath);
            // GUARANTEE colour: if the HDRP material assets are missing
            // or broken, build cheap HDRP-correct coloured materials so
            // trees are NEVER white/grey/uncoloured (user feedback).
            if (foliageMat == null || IsBrokenMaterial(foliageMat)
                || !IsPipelineCompatible(foliageMat.shader))
                foliageMat = MakeMaterial("LP_Needle_HDRP",
                    new Color(0.12f, 0.24f, 0.13f), 0.10f); // sickly pine green
            if (trunkMat == null || IsBrokenMaterial(trunkMat)
                || !IsPipelineCompatible(trunkMat.shader))
                trunkMat = MakeMaterial("LP_Bark_HDRP",
                    new Color(0.17f, 0.11f, 0.07f), 0.10f);  // dark bark brown
            bool gpuInstance = p["gpu_instancing"]?.ToObject<bool>() ?? true;
            if (gpuInstance)
            {
                if (foliageMat != null) foliageMat.enableInstancing = true;
                if (trunkMat != null) trunkMat.enableInstancing = true;
            }

            // Resolve prefabs (skip any missing path so a partial set still works).
            GameObject LoadModel(string ap)
            {
                var g = AssetDatabase.LoadAssetAtPath<GameObject>(ap);
                return g;
            }
            var live = liveModels.Select(LoadModel).Where(g => g != null).ToList();
            var dead = deadModels.Select(LoadModel).Where(g => g != null).ToList();
            if (live.Count == 0 && dead.Count == 0)
                return new { ok = false, error = "No tree GLB models could be loaded", tried_live = liveModels, tried_dead = deadModels };

            var terrain = ResolveSceneTerrain(p);
            if (terrain == null)
                return new { ok = false, error = "No Terrain in scene (build it first)" };
            var td = terrain.terrainData;
            Vector3 tp = terrain.transform.position;
            float sizeX = td.size.x, sizeZ = td.size.z, sizeY = td.size.y;

            if (clearPrimitive)
            {
                var oldProc = GameObject.Find("WorldForest");
                if (oldProc != null) Undo.DestroyObjectImmediate(oldProc);
            }
            var oldGlb = GameObject.Find("WorldForestGLB");
            if (oldGlb != null) Undo.DestroyObjectImmediate(oldGlb);
            var forestRoot = new GameObject("WorldForestGLB");
            Undo.RegisterCreatedObjectUndo(forestRoot, "UnityTools: GLB world forest");

            var rng = new System.Random(seed);
            int placed = 0, deadPlaced = 0, renderersFixed = 0, renderersKept = 0;
            int bandFail = 0, slopeFail = 0;
            string placementNote = "requested band/slope";
            // Two-pass: if the requested band/slope rejects everything
            // (real-world heightmaps are often steep per-sample), retry
            // wide-open so a forest still appears (then report why).
            for (int pass = 0; pass < 2; pass++)
            {
                if (pass == 1)
                {
                    if (placed > 0) break;
                    bandMin = 0f; bandMax = 1.01f; maxSlope = 89f;
                    rng = new System.Random(seed);
                    placementNote = "fallback: band/slope too strict for this terrain, used full range";
                }
            for (int i = 0; i < attempts; i++)
            {
                float u = (float)rng.NextDouble();
                float v = (float)rng.NextDouble();
                float hn = td.GetInterpolatedHeight(u, v) / Mathf.Max(0.001f, sizeY);
                if (hn < bandMin || hn > bandMax) { bandFail++; continue; }
                float steep = td.GetSteepness(u, v);
                if (steep > maxSlope) { slopeFail++; continue; }

                bool useDead = dead.Count > 0 && rng.NextDouble() < deadRatio;
                var pool = useDead ? dead : (live.Count > 0 ? live : dead);
                var prefab = pool[rng.Next(pool.Count)];

                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                if (go == null) go = UnityEngine.Object.Instantiate(prefab);
                if (go == null) continue;

                float wx = tp.x + u * sizeX;
                float wz = tp.z + v * sizeZ;
                float wy = tp.y + td.GetInterpolatedHeight(u, v) + yOffset;
                float scl = (float)(sMin + rng.NextDouble() * (sMax - sMin));
                go.transform.SetParent(forestRoot.transform, true);
                go.transform.position = new Vector3(wx, wy, wz);
                go.transform.rotation = Quaternion.Euler(
                    (float)(rng.NextDouble() * 4.0 - 2.0),     // slight lean
                    (float)(rng.NextDouble() * 360.0),          // random facing
                    (float)(rng.NextDouble() * 4.0 - 2.0));
                go.transform.localScale = Vector3.one * scl;
                go.name = (useDead ? "DeadTree_" : "Tree_") + placed.ToString("000");

                // Material safety: keep working PBR, repair broken/white ones.
                var rends = go.GetComponentsInChildren<Renderer>(true);
                foreach (var rend in rends)
                {
                    var shared = rend.sharedMaterials;
                    bool anyBroken = shared == null || shared.Length == 0;
                    if (!anyBroken)
                        foreach (var m in shared)
                            if (m == null || IsBrokenMaterial(m) || !IsPipelineCompatible(m.shader))
                            { anyBroken = true; break; }
                    // Per-slot mode: low-poly conifers are 1 mesh / 2
                    // slots (trunk + needles). Always remap so they get
                    // cheap correct HDRP materials (not the FBX import's).
                    if (trunkMat != null && shared != null && shared.Length >= 2)
                    {
                        var arr = new Material[shared.Length];
                        arr[0] = trunkMat;
                        for (int k = 1; k < arr.Length; k++)
                            arr[k] = foliageMat ?? trunkMat;
                        rend.sharedMaterials = arr;
                        renderersFixed++;
                    }
                    else if ((anyBroken || trunkMat != null) && foliageMat != null)
                    {
                        var arr = new Material[Mathf.Max(1, shared?.Length ?? 1)];
                        for (int k = 0; k < arr.Length; k++) arr[k] = foliageMat;
                        rend.sharedMaterials = arr;
                        renderersFixed++;
                    }
                    else renderersKept++;
                }

                // GROUND SNAP (pivot-agnostic): the imported FBX pivot is
                // NOT at the mesh base, so setting position.y = surface
                // sank trees under the terrain (user feedback). Recompute
                // combined world renderer bounds and lift the tree so its
                // lowest rendered point sits exactly on the surface (wy),
                // sunk slightly (0.15 m) so the trunk isn't floating.
                if (rends != null && rends.Length > 0)
                {
                    Bounds bb = rends[0].bounds;
                    for (int rb = 1; rb < rends.Length; rb++)
                        bb.Encapsulate(rends[rb].bounds);
                    float delta = wy - bb.min.y - 0.15f;
                    go.transform.position += new Vector3(0f, delta, 0f);
                }

                placed++;
                if (useDead) deadPlaced++;
            }
            }  // end pass loop

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                placed,
                dead_placed = deadPlaced,
                attempts,
                band_fail = bandFail,
                slope_fail = slopeFail,
                terrain = terrain.name,
                terrain_relief_m = TerrainRelief(terrain),
                live_models = live.Select(g => g.name).ToArray(),
                dead_models = dead.Select(g => g.name).ToArray(),
                renderers_fixed = renderersFixed,
                renderers_kept = renderersKept,
                foliage_material = foliageMat != null ? foliageMat.name : "(missing)",
                forest_band = new[] { bandMin, bandMax },
                note = placementNote,
            };
        }

        // Phase 108: place a generated/imported asset ON the terrain
        // surface at (x,z). Used by the AI Blender asset layer to drop
        // its own props (shrine/gate/totem...) at level-instance-links
        // anchors so they sit on the ground, not float.
        // Phase 136: make the slice genuinely PLAYABLE — attach the
        // (compiled, spec-aligned) Gameplay.* scripts to scene objects
        // in ForgottenValley_VS: hero gets controller/combat/stamina/
        // inventory + "Player" tag, camera gets ThirdPersonCamera, HUD/
        // streaming objects, camp racks/banner/loot, and a couple of
        // enemies. Idempotent (reuse existing). Reflection type-resolve
        // so the editor assembly needs no asmdef ref to Assembly-CSharp.
        private static System.Type ResolveGameType(string n)
        {
            var t = System.Type.GetType(n);
            if (t != null) return t;
            return System.AppDomain.CurrentDomain.GetAssemblies()
                .SelectMany(a => { try { return a.GetTypes(); } catch { return new System.Type[0]; } })
                .FirstOrDefault(x => x.FullName == n || x.Name == n);
        }

        private static object WirePlayableSlice(JObject p)
        {
            string heroName = p["hero"]?.ToString() ?? "SK_Hero";
            var wired = new List<string>();
            var missing = new List<string>();

            void Ensure(GameObject go, string typeName)
            {
                if (go == null) return;
                var ty = ResolveGameType(typeName);
                if (ty == null) { missing.Add(typeName); return; }
                var has = go.GetComponent(ty);
                if (has == null)
                {
                    go.AddComponent(ty);
                    wired.Add($"{go.name}+{ty.Name}");
                }
            }
            GameObject FindOrCube(string nm, Vector3 pos, PrimitiveType prim, Transform parent)
            {
                var g = GameObject.Find(nm);
                if (g == null)
                {
                    g = GameObject.CreatePrimitive(prim);
                    g.name = nm;
                    Undo.RegisterCreatedObjectUndo(g, "Bridge: playable slice");
                }
                g.transform.position = pos;
                if (parent != null) g.transform.SetParent(parent, true);
                return g;
            }

            var hero = GameObject.Find(heroName);
            if (hero == null)
                return new { ok = false, error = $"Hero '{heroName}' not in scene" };
            try { hero.tag = "Player"; } catch { /* builtin tag always exists */ }
            Vector3 hp = hero.transform.position;

            // Player component stack (CharacterController first for the
            // PlayerController [RequireComponent]).
            Ensure(hero, "UnityEngine.CharacterController");
            Ensure(hero, "Gameplay.StaminaComponent");
            Ensure(hero, "Gameplay.InventoryComponent");
            Ensure(hero, "Gameplay.ExperienceComponent");
            Ensure(hero, "Gameplay.CombatComponent");
            Ensure(hero, "Gameplay.StatusEffectComponent");
            Ensure(hero, "Gameplay.PlayerController");

            var cam = GameObject.Find("Main Camera") ?? (Camera.main ? Camera.main.gameObject : null);
            if (cam != null) Ensure(cam, "Gameplay.ThirdPersonCamera");

            var root = GameObject.Find("TI_Playable") ?? new GameObject("TI_Playable");
            Undo.RegisterCreatedObjectUndo(root, "Bridge: playable slice root");

            var hud = GameObject.Find("TI_HUD") ?? new GameObject("TI_HUD");
            hud.transform.SetParent(root.transform, true);
            Ensure(hud, "Gameplay.RpgHudController");
            Ensure(hud, "Gameplay.HudShells");

            var stream = GameObject.Find("TI_WorldStreaming") ?? new GameObject("TI_WorldStreaming");
            stream.transform.SetParent(root.transform, true);
            Ensure(stream, "Gameplay.RegionStreamer");

            // Night-peril director (core-pillars.md #3 "Dunya guzel VE
            // tehlikeli"): reads DayCycleManager, flags enemies harder +
            // wider-aggro after dark, fully reverts at dawn.
            var night = GameObject.Find("TI_NightDanger") ?? new GameObject("TI_NightDanger");
            night.transform.SetParent(root.transform, true);
            Ensure(night, "Gameplay.NightDanger");

            // Adaptive music: AudioManager is the two-layer ENGINE
            // (exploration bed + auto-ducking tension overlay); it lives
            // alone on its own object because its singleton guard
            // Destroy()s a duplicate gameObject. MusicDirector is the
            // brain that feeds it (core-pillars #2/#3) and sits on its
            // own object so a pre-existing scene AudioManager never
            // takes it down with it.
            var audioEng = GameObject.Find("TI_Audio") ?? new GameObject("TI_Audio");
            audioEng.transform.SetParent(root.transform, true);
            Ensure(audioEng, "Gameplay.AudioManager");
            var music = GameObject.Find("TI_MusicDirector") ?? new GameObject("TI_MusicDirector");
            music.transform.SetParent(root.transform, true);
            Ensure(music, "Gameplay.MusicDirector");

            // Diegetic positional encounter SFX (snarls/rustles at the
            // enemies) — the audible counterpart to MusicDirector; uses
            // the TI_Audio AudioManager engine.
            var amb = GameObject.Find("TI_EncounterAmbience") ?? new GameObject("TI_EncounterAmbience");
            amb.transform.SetParent(root.transform, true);
            Ensure(amb, "Gameplay.EncounterAmbience");

            // Camp progression backbone (core-pillars #4): ties the camp
            // stations into one escalating loop (craft -> camp tier up ->
            // better loadout/aura/recipes). Wired after the camp objects
            // below exist on re-runs; it finds them itself at runtime.
            var camp = GameObject.Find("TI_CampProgression") ?? new GameObject("TI_CampProgression");
            camp.transform.SetParent(root.transform, true);
            Ensure(camp, "Gameplay.CampProgression");

            // Camp loadout + offering near the hero/spawn.
            var rack = FindOrCube("WeaponRack_BarbarCamp", hp + new Vector3(3f, 0f, 2f), PrimitiveType.Cube, root.transform);
            Ensure(rack, "Gameplay.WeaponRack");
            var banner = FindOrCube("WarBanner_Camp", hp + new Vector3(-3f, 0f, 2f), PrimitiveType.Cube, root.transform);
            Ensure(banner, "Gameplay.WarBanner");
            var chest = FindOrCube("LootChest_Bridge", hp + new Vector3(0f, 0f, 5f), PrimitiveType.Cube, root.transform);
            Ensure(chest, "Gameplay.LootPickup");
            // Camp crafting station (core-pillars #4 progression node).
            var craft = FindOrCube("CraftingBench_Camp", hp + new Vector3(5f, 0f, -2f), PrimitiveType.Cube, root.transform);
            Ensure(craft, "Gameplay.CraftingStation");
            // Second-class prototype altar (P2). Default ClassPrototype
            // profile = Skirmisher = the new second class; Barbarian
            // stays the implicit default, so one altar is enough.
            var classAltar = FindOrCube("ClassAltar_Skirmisher", hp + new Vector3(-5f, 0f, -2f), PrimitiveType.Cube, root.transform);
            Ensure(classAltar, "Gameplay.ClassPrototype");
            // Lore pickups along the spine (camp + path). Default mode =
            // content-independent lore note; setting dialogueId in-editor
            // turns either into a DialogueSystem trigger (content).
            var loreCamp = FindOrCube("LoreNote_BriarCamp", hp + new Vector3(2f, 0f, -4f), PrimitiveType.Cube, root.transform);
            Ensure(loreCamp, "Gameplay.LorePickup");
            var lorePath = FindOrCube("LoreNote_Path", hp + new Vector3(12f, 0f, 8f), PrimitiveType.Cube, root.transform);
            Ensure(lorePath, "Gameplay.LorePickup");

            // A couple of readable enemies near the route.
            var enemies = new List<string>();
            for (int i = 0; i < 2; i++)
            {
                var e = FindOrCube($"Enemy_Briarbound_{i + 1:00}",
                    hp + new Vector3(8f + i * 3f, 0f, 10f + i * 4f),
                    PrimitiveType.Capsule, root.transform);
                Ensure(e, "Gameplay.CombatComponent");
                Ensure(e, "Gameplay.StatusEffectComponent");
                Ensure(e, "Gameplay.EnemyAIController");
                Ensure(e, "Gameplay.EliteAffix");   // may roll an elite
                enemies.Add(e.name);
            }
            // One GUARANTEED elite for the slice (name contains "Elite"
            // -> EliteAffix forces promotion + rolls an affix).
            var champ = FindOrCube("EliteBriarbound_Champion",
                hp + new Vector3(14f, 0f, 16f), PrimitiveType.Capsule, root.transform);
            Ensure(champ, "Gameplay.CombatComponent");
            Ensure(champ, "Gameplay.StatusEffectComponent");
            Ensure(champ, "Gameplay.EnemyAIController");
            Ensure(champ, "Gameplay.EliteAffix");
            enemies.Add(champ.name);

            var scene = SceneManager.GetActiveScene();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);

            return new
            {
                ok = true,
                hero = heroName,
                hero_tag = hero.tag,
                wired,
                wired_count = wired.Count,
                missing_types = missing,
                camp = new[] { "WeaponRack_BarbarCamp", "WarBanner_Camp", "LootChest_Bridge" },
                enemies,
                scene = scene.name,
                note = "Gameplay scripts attached to ForgottenValley_VS objects; scene saved",
            };
        }

        private static object PlaceAssetOnTerrain(JObject p)
        {
            string assetPath = p["asset_path"]?.ToString();
            if (string.IsNullOrEmpty(assetPath))
                return new { ok = false, error = "asset_path required" };
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (prefab == null)
                return new { ok = false, error = $"Asset not found: {assetPath}" };

            float x = p["x"]?.ToObject<float>() ?? 0f;
            float z = p["z"]?.ToObject<float>() ?? 0f;
            float rotY = p["rot_y"]?.ToObject<float>() ?? 0f;
            float scl = p["scale"]?.ToObject<float>() ?? 1f;
            float yOff = p["y_offset"]?.ToObject<float>() ?? 0f;
            string nm = p["name"]?.ToString();
            string parentName = p["parent"]?.ToString();
            string foliageMatPath = p["material_path"]?.ToString();

            // Snap-to-good-ground: blind anchor offsets often land in the
            // valley floor / underwater. If the sampled point is below
            // min_surface_y (or far from a reference elevation), spiral-
            // search nearby for a point that is above water, low-slope,
            // and (if ref_y given) near the playable elevation band.
            float minSurfaceY = p["min_surface_y"]?.ToObject<float>() ?? float.NaN;
            float refY = p["ref_y"]?.ToObject<float>() ?? float.NaN;
            float searchR = p["search_radius"]?.ToObject<float>() ?? 140f;
            float maxSlopeP = p["max_slope_deg"]?.ToObject<float>() ?? 32f;

            var terrain = ResolveSceneTerrain(p);
            float surfaceY = 0f;
            if (terrain != null)
            {
                var td = terrain.terrainData;
                Vector3 tp = terrain.transform.position;
                float HeightAt(float wx, float wz, out float steep)
                {
                    float uu = Mathf.Clamp01((wx - tp.x) / Mathf.Max(0.001f, td.size.x));
                    float vv = Mathf.Clamp01((wz - tp.z) / Mathf.Max(0.001f, td.size.z));
                    steep = td.GetSteepness(uu, vv);
                    return tp.y + td.GetInterpolatedHeight(uu, vv);
                }
                float s0;
                surfaceY = HeightAt(x, z, out s0);
                bool needBetter =
                    (!float.IsNaN(minSurfaceY) && surfaceY < minSurfaceY)
                    || s0 > maxSlopeP
                    || (!float.IsNaN(refY) && Mathf.Abs(surfaceY - refY) > 35f);
                if (needBetter)
                {
                    float bestX = x, bestZ = z, bestY = surfaceY, bestScore = float.MaxValue;
                    var rng = new System.Random((int)(x * 31 + z * 17));
                    for (int ring = 1; ring <= 8; ring++)
                    {
                        float rad = searchR * ring / 8f;
                        for (int a = 0; a < 12; a++)
                        {
                            double ang = a * (Math.PI / 6.0) + rng.NextDouble();
                            float cx = x + (float)Math.Cos(ang) * rad;
                            float cz = z + (float)Math.Sin(ang) * rad;
                            float st;
                            float hy = HeightAt(cx, cz, out st);
                            if (!float.IsNaN(minSurfaceY) && hy < minSurfaceY) continue;
                            if (st > maxSlopeP) continue;
                            float score = st
                                + (!float.IsNaN(refY) ? Mathf.Abs(hy - refY) : 0f)
                                + rad * 0.02f;
                            if (score < bestScore)
                            { bestScore = score; bestX = cx; bestZ = cz; bestY = hy; }
                        }
                    }
                    x = bestX; z = bestZ; surfaceY = bestY;
                }
            }

            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            if (go == null) go = UnityEngine.Object.Instantiate(prefab);
            if (go == null) return new { ok = false, error = "Instantiate failed" };

            GameObject parent = string.IsNullOrEmpty(parentName) ? null : GameObject.Find(parentName);
            if (!string.IsNullOrEmpty(parentName) && parent == null)
            {
                parent = new GameObject(parentName);
                Undo.RegisterCreatedObjectUndo(parent, "UnityTools: asset group");
            }
            if (parent != null) go.transform.SetParent(parent.transform, true);

            go.transform.position = new Vector3(x, surfaceY + yOff, z);
            go.transform.rotation = Quaternion.Euler(0f, rotY, 0f);
            go.transform.localScale = Vector3.one * scl;
            if (!string.IsNullOrEmpty(nm)) go.name = nm;

            // Optional: force a known-good material if the import is white.
            if (!string.IsNullOrEmpty(foliageMatPath))
            {
                var fm = AssetDatabase.LoadAssetAtPath<Material>(foliageMatPath);
                if (fm != null)
                    foreach (var rend in go.GetComponentsInChildren<Renderer>(true))
                    {
                        var arr = new Material[Mathf.Max(1, rend.sharedMaterials.Length)];
                        for (int i = 0; i < arr.Length; i++) arr[i] = fm;
                        rend.sharedMaterials = arr;
                    }
            }

            Undo.RegisterCreatedObjectUndo(go, "UnityTools: place asset on terrain");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                name = go.name,
                asset = assetPath,
                position = new { x, y = surfaceY + yOff, z },
                surface_y = surfaceY,
            };
        }

        private static object FixTerrainMaterial(JObject p)
        {
            bool clearClutter = p["clear_clutter"]?.ToObject<bool>() ?? true;
            var terrains = UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsInactive.Exclude);
            var fixedList = new List<string>();
            foreach (var t in terrains)
                fixedList.Add(t.name + ":" + ApplyTerrainPipelineMaterial(t));

            int removed = 0;
            if (clearClutter)
            {
                foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
                {
                    string n = root.name;
                    if (n.StartsWith("Nature_Trees") || n.StartsWith("Nature_Rocks")
                        || n == "UnityTools_ForestScene")
                    {
                        Undo.DestroyObjectImmediate(root);
                        removed++;
                    }
                }
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                terrains_fixed = fixedList.ToArray(),
                clutter_removed = removed,
            };
        }

        private static object BuildTerrainFromHeightmap(JObject p)
        {
            int res = p["resolution"]?.ToObject<int>() ?? 65;       // 2^k+1
            float sizeXZ = p["size_xz"]?.ToObject<float>() ?? 1000f; // metres
            float sizeY = p["size_y"]?.ToObject<float>() ?? 280f;    // relief
            var arr = p["heights"] as JArray;
            if (arr == null || arr.Count < res * res)
                return new { ok = false, error = $"heights needs {res*res} floats, got {arr?.Count ?? 0}" };

            // clear previous terrain(s)
            foreach (var t in UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsInactive.Exclude))
                Undo.DestroyObjectImmediate(t.gameObject);

            var td = new TerrainData
            {
                heightmapResolution = res,
                size = new Vector3(sizeXZ, sizeY, sizeXZ),
                alphamapResolution = res,
                baseMapResolution = Mathf.Min(1024, res * 4),
            };

            var h = new float[res, res];
            for (int y = 0; y < res; y++)
                for (int x = 0; x < res; x++)
                    h[y, x] = Mathf.Clamp01(arr[y * res + x].ToObject<float>());
            td.SetHeights(0, 0, h);

            // Biome ground layers — solid procedural colours by band.
            var plains = new TerrainLayer { diffuseTexture = SolidTex(new Color(0.30f, 0.42f, 0.20f), "Plains"), tileSize = new Vector2(15, 15) };
            var forest = new TerrainLayer { diffuseTexture = SolidTex(new Color(0.18f, 0.27f, 0.14f), "ForestFloor"), tileSize = new Vector2(15, 15) };
            var rock   = new TerrainLayer { diffuseTexture = SolidTex(new Color(0.42f, 0.40f, 0.38f), "Rock"),  tileSize = new Vector2(15, 15) };
            var snow   = new TerrainLayer { diffuseTexture = SolidTex(new Color(0.86f, 0.88f, 0.92f), "Snow"),  tileSize = new Vector2(15, 15) };
            td.terrainLayers = new[] { plains, forest, rock, snow };

            int aw = td.alphamapWidth, ah = td.alphamapHeight;
            var alpha = new float[ah, aw, 4];
            for (int y = 0; y < ah; y++)
            {
                for (int x = 0; x < aw; x++)
                {
                    float hn = h[
                        Mathf.Clamp(Mathf.RoundToInt((float)y / ah * (res - 1)), 0, res - 1),
                        Mathf.Clamp(Mathf.RoundToInt((float)x / aw * (res - 1)), 0, res - 1)];
                    float wPlain = Mathf.Clamp01(1f - Mathf.Abs(hn - 0.10f) / 0.22f);
                    float wForest = Mathf.Clamp01(1f - Mathf.Abs(hn - 0.42f) / 0.26f);
                    float wRock = Mathf.Clamp01(1f - Mathf.Abs(hn - 0.74f) / 0.26f);
                    float wSnow = Mathf.Clamp01((hn - 0.85f) / 0.15f);
                    float s = wPlain + wForest + wRock + wSnow + 1e-4f;
                    alpha[y, x, 0] = wPlain / s;
                    alpha[y, x, 1] = wForest / s;
                    alpha[y, x, 2] = wRock / s;
                    alpha[y, x, 3] = wSnow / s;
                }
            }
            td.SetAlphamaps(0, 0, alpha);

            var go = Terrain.CreateTerrainGameObject(td);
            go.name = "WorldTerrain";
            go.transform.position = new Vector3(-sizeXZ / 2f, 0f, -sizeXZ / 2f);
            ApplyTerrainPipelineMaterial(go.GetComponent<Terrain>());
            Undo.RegisterCreatedObjectUndo(go, "UnityTools: world terrain");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                terrain = go.name,
                resolution = res,
                size_xz = sizeXZ,
                size_y = sizeY,
                layers = new[] { "plains", "forest", "rock", "snow" },
            };
        }

        // ── Phase 90: whole-scene read (no 200 cap; roots are few even
        // with heavy GLB hierarchies) + premium material assignment.
        private static object ListRootObjects(JObject p)
        {
            var scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects();
            var list = new List<object>();
            foreach (var r in roots)
            {
                var rends = r.GetComponentsInChildren<Renderer>(true);
                int childCount = r.GetComponentsInChildren<Transform>(true).Length - 1;
                list.Add(new
                {
                    name = r.name,
                    active = r.activeSelf,
                    children = childCount,
                    renderers = rends.Length,
                    pos = new[] { r.transform.position.x, r.transform.position.y, r.transform.position.z },
                });
            }
            return new { ok = true, scene = scene.name, root_count = roots.Length, roots = list };
        }

        private static object AssignMaterialAsset(JObject p)
        {
            string matPath = p["material_path"]?.ToString();
            string nameContains = p["name_contains"]?.ToString() ?? "";
            bool recurse = p["recurse"]?.ToObject<bool>() ?? true;
            int maxObjects = Mathf.Clamp(p["max_objects"]?.ToObject<int>() ?? 5000, 1, 50000);
            if (string.IsNullOrEmpty(matPath))
                return new { ok = false, error = "material_path required" };

            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat == null)
                return new { ok = false, error = $"Material not found at {matPath}" };

            var scene = SceneManager.GetActiveScene();
            int matchedObjects = 0, assignedRenderers = 0;
            var sample = new List<string>();

            void Apply(GameObject go)
            {
                if (matchedObjects >= maxObjects) return;
                bool match = string.IsNullOrEmpty(nameContains)
                    || go.name.IndexOf(nameContains, StringComparison.OrdinalIgnoreCase) >= 0;
                if (match)
                {
                    matchedObjects++;
                    var rends = recurse
                        ? go.GetComponentsInChildren<Renderer>(true)
                        : go.GetComponents<Renderer>();
                    foreach (var rend in rends)
                    {
                        Undo.RecordObject(rend, "Bridge: assign material asset");
                        var arr = new Material[rend.sharedMaterials.Length];
                        for (int i = 0; i < arr.Length; i++) arr[i] = mat;
                        rend.sharedMaterials = arr;
                        assignedRenderers++;
                        if (sample.Count < 8) sample.Add(rend.gameObject.name);
                    }
                }
            }

            foreach (var root in scene.GetRootGameObjects())
            {
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    Apply(t.gameObject);
                    if (matchedObjects >= maxObjects) break;
                }
            }

            EditorSceneManager.MarkSceneDirty(scene);
            return new
            {
                ok = true,
                material = mat.name,
                material_path = matPath,
                name_contains = nameContains,
                matched_objects = matchedObjects,
                assigned_renderers = assignedRenderers,
                sample = sample.ToArray(),
            };
        }

        // ── Phase 89: HDRP Global Volume (Exposure+Tonemapping+Fog).
        // Reflection-only so the bridge asmdef needs NO HDRP reference
        // and degrades gracefully when HDRP is absent. Fixes the
        // HDRP white-out (physical auto-exposure with no Exposure
        // override blows every frame to white).
        private static Type FindType(string fullName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(fullName, false);
                if (t != null) return t;
            }
            return null;
        }

        private static void VpOverride(object param, object val)
        {
            if (param == null) return;
            var osF = param.GetType().GetField("overrideState");
            if (osF != null) osF.SetValue(param, true);
            var vProp = param.GetType().GetProperty("value");
            if (vProp == null) return;
            var pt = vProp.PropertyType;
            object conv;
            if (pt.IsEnum)
                conv = (val is string es) ? Enum.Parse(pt, es, true)
                                          : Enum.ToObject(pt, Convert.ToInt32(val));
            else if (pt == typeof(Color)) conv = val;
            else conv = Convert.ChangeType(val, pt);
            vProp.SetValue(param, conv);
        }

        private static bool SetVc(object vc, string field, object val, List<string> applied)
        {
            if (vc == null) return false;
            var f = vc.GetType().GetField(field);
            if (f == null) return false;
            var param = f.GetValue(vc);
            if (param == null) return false;
            VpOverride(param, val);
            applied.Add(field + "=" + val);
            return true;
        }

        private static object SetupHdrpVolume(JObject p)
        {
            float exposure = p["fixed_exposure"]?.ToObject<float>() ?? 12.5f;
            // "Automatic" = HDRP adaptive eye — never blows pure white
            // or pitch black again. The smart default.
            string expMode = (p["exposure_mode"]?.ToString() ?? "Automatic");
            bool fog = p["fog"]?.ToObject<bool>() ?? true;
            float meanFreePath = p["fog_distance"]?.ToObject<float>() ?? 260f;

            var profType = FindType("UnityEngine.Rendering.VolumeProfile");
            var volType = FindType("UnityEngine.Rendering.Volume");
            if (profType == null || volType == null)
                return new { ok = false, error = "Volume/VolumeProfile types not found (SRP core missing)" };

            var expType  = FindType("UnityEngine.Rendering.HighDefinition.Exposure");
            var toneType = FindType("UnityEngine.Rendering.HighDefinition.Tonemapping");
            var fogType  = FindType("UnityEngine.Rendering.HighDefinition.Fog");
            if (expType == null && toneType == null)
                return new { ok = false, error = "HDRP volume types not found — project is not HDRP?" };

            var go = GameObject.Find("UnityTools_HDRPVolume")
                     ?? new GameObject("UnityTools_HDRPVolume");
            Undo.RegisterCreatedObjectUndo(go, "UnityTools: HDRP volume");
            var vol = go.GetComponent(volType) ?? go.AddComponent(volType);
            volType.GetProperty("isGlobal")?.SetValue(vol, true);
            volType.GetProperty("priority")?.SetValue(vol, 10f);

            var profile = ScriptableObject.CreateInstance(profType);
            profile.name = "UnityTools_HDRP_Profile";
            var sharedProp = volType.GetProperty("sharedProfile") ?? volType.GetProperty("profile");
            sharedProp?.SetValue(vol, profile);

            var addM = profType.GetMethod("Add", new[] { typeof(Type), typeof(bool) });
            object AddComp(Type t) => (t != null && addM != null)
                ? addM.Invoke(profile, new object[] { t, true }) : null;

            var applied = new List<string>();

            if (expType != null)
            {
                var exp = AddComp(expType);
                if (expMode.Equals("Automatic", StringComparison.OrdinalIgnoreCase))
                {
                    // Adaptive: meters the scene and self-corrects.
                    SetVc(exp, "mode", "Automatic", applied);
                    SetVc(exp, "meteringMode", "CenterWeighted", applied);
                    SetVc(exp, "luminanceSource", "ColorBuffer", applied);
                    SetVc(exp, "limitMin", -4f, applied);
                    SetVc(exp, "limitMax", 14f, applied);
                    SetVc(exp, "adaptationSpeedDarkToLight", 3f, applied);
                    SetVc(exp, "adaptationSpeedLightToDark", 1f, applied);
                }
                else
                {
                    SetVc(exp, "mode", "Fixed", applied);
                    SetVc(exp, "fixedExposure", exposure, applied);
                }
            }
            if (toneType != null)
            {
                var tone = AddComp(toneType);
                SetVc(tone, "mode", "ACES", applied);
            }
            if (fog && fogType != null)
            {
                var fg = AddComp(fogType);
                SetVc(fg, "enabled", true, applied);
                SetVc(fg, "meanFreePath", meanFreePath, applied);
                SetVc(fg, "baseHeight", 0f, applied);
                SetVc(fg, "maximumHeight", 60f, applied);
                SetVc(fg, "enableVolumetricFog", true, applied);
            }

            EditorUtility.SetDirty(go);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                volume_object = go.name,
                pipeline = "HDRP",
                fixed_exposure = exposure,
                fog,
                applied = applied.ToArray(),
                note = "HDRP Global Volume: Exposure(Fixed)+Tonemapping(ACES)"
                       + (fog ? "+Fog" : "")
            };
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

        // Phase 104: flat {name,x,y,z} convenience aliases. Raw bridge
        // callers (scripts, studio_realize_world) used set_scale/
        // set_position/set_rotation with a flat shape — these were
        // never dispatch cases (only set_transform with nested
        // position/rotation/scale), so every raw transform call
        // silently failed. These 3 handlers make the intuitive flat
        // form work and retroactively fix the orchestrator + blockouts.
        private static GameObject ReqGo(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            return go;
        }

        private static object SetScale(JObject p)
        {
            var go = ReqGo(p);
            Undo.RecordObject(go.transform, "Bridge: set scale");
            var s = go.transform.localScale;
            go.transform.localScale = new Vector3(
                p["x"]?.ToObject<float>() ?? s.x,
                p["y"]?.ToObject<float>() ?? s.y,
                p["z"]?.ToObject<float>() ?? s.z);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, scale = new[] { go.transform.localScale.x,
                go.transform.localScale.y, go.transform.localScale.z } };
        }

        private static object SetPosition(JObject p)
        {
            var go = ReqGo(p);
            Undo.RecordObject(go.transform, "Bridge: set position");
            var v = go.transform.position;
            go.transform.position = new Vector3(
                p["x"]?.ToObject<float>() ?? v.x,
                p["y"]?.ToObject<float>() ?? v.y,
                p["z"]?.ToObject<float>() ?? v.z);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, position = new[] { go.transform.position.x,
                go.transform.position.y, go.transform.position.z } };
        }

        private static object SetRotation(JObject p)
        {
            var go = ReqGo(p);
            Undo.RecordObject(go.transform, "Bridge: set rotation");
            var e = go.transform.eulerAngles;
            go.transform.eulerAngles = new Vector3(
                p["x"]?.ToObject<float>() ?? e.x,
                p["y"]?.ToObject<float>() ?? e.y,
                p["z"]?.ToObject<float>() ?? e.z);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, euler = new[] { go.transform.eulerAngles.x,
                go.transform.eulerAngles.y, go.transform.eulerAngles.z } };
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
            // Phase 104: edit-mode must use sharedMaterial — rend.material
            // instantiates a leaked per-renderer copy every call (the
            // 'Instantiating material...will leak' console spam). Give
            // each object its OWN material once (so recolour is isolated)
            // then mutate sharedMaterial in place — no leak.
            if (rend.sharedMaterial != null && !rend.sharedMaterial.name.StartsWith("UT_"))
            {
                var owned = new Material(rend.sharedMaterial)
                { name = "UT_" + go.name };
                rend.sharedMaterial = owned;
            }
            SetMaterialBaseColor(rend.sharedMaterial, new Color(r, g, b, a));
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

        private static object ListScenes(JObject p)
        {
            int max = Mathf.Clamp(p["max_results"]?.ToObject<int>() ?? 200, 1, 1000);
            bool includePackages = p["include_packages"]?.ToObject<bool>() ?? false;
            string[] guids = AssetDatabase.FindAssets("t:Scene");
            var scenes = new List<object>();
            foreach (string guid in guids.Take(max))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (!includePackages && !path.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase))
                    continue;
                scenes.Add(new
                {
                    name = Path.GetFileNameWithoutExtension(path),
                    path = path,
                    folder = Path.GetDirectoryName(path)?.Replace("\\", "/") ?? "",
                    editable = path.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase),
                    active = string.Equals(path, SceneManager.GetActiveScene().path, StringComparison.OrdinalIgnoreCase),
                });
            }
            return new
            {
                ok = true,
                active_scene = SceneManager.GetActiveScene().path,
                count = guids.Length,
                returned = scenes.Count,
                scenes = scenes,
            };
        }

        private static object OpenScene(JObject p)
        {
            string path = p["path"]?.ToString();
            if (string.IsNullOrEmpty(path)) throw new ArgumentException("path is required");
            if (!path.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("path must be a Unity asset path under Assets/");
            if (!File.Exists(Path.Combine(ProjectRootPath(), path)))
                throw new FileNotFoundException($"Scene not found: {path}");
            if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            {
                var scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
                return new { ok = true, name = scene.name, path = scene.path };
            }
            return new { ok = false, cancelled = true, path = path };
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

        private static Camera ResolveCamera(string name)
        {
            if (string.IsNullOrEmpty(name))
            {
                var main = Camera.main;
                if (main != null) return main;
                throw new InvalidOperationException("No camera name given and no MainCamera in scene.");
            }
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var cam = go.GetComponent<Camera>();
            if (cam == null) throw new InvalidOperationException($"Camera component not found on {name}");
            return cam;
        }

        private static object SetCameraTransform(JObject p)
        {
            Camera cam = ResolveCamera(p["name"]?.ToString());
            Undo.RecordObject(cam.transform, "Bridge: set camera transform");
            JObject pos = p["position"] as JObject;
            if (pos != null)
                cam.transform.position = new Vector3(
                    pos["x"]?.ToObject<float>() ?? cam.transform.position.x,
                    pos["y"]?.ToObject<float>() ?? cam.transform.position.y,
                    pos["z"]?.ToObject<float>() ?? cam.transform.position.z
                );
            JObject rot = p["rotation_euler"] as JObject;
            if (rot != null)
                cam.transform.eulerAngles = new Vector3(
                    rot["x"]?.ToObject<float>() ?? cam.transform.eulerAngles.x,
                    rot["y"]?.ToObject<float>() ?? cam.transform.eulerAngles.y,
                    rot["z"]?.ToObject<float>() ?? cam.transform.eulerAngles.z
                );
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                name = cam.gameObject.name,
                position_x = cam.transform.position.x,
                position_y = cam.transform.position.y,
                position_z = cam.transform.position.z,
                rotation_x = cam.transform.eulerAngles.x,
                rotation_y = cam.transform.eulerAngles.y,
                rotation_z = cam.transform.eulerAngles.z,
            };
        }

        private static object FrameObject(JObject p)
        {
            string targetName = p["target_name"]?.ToString();
            if (string.IsNullOrEmpty(targetName)) throw new ArgumentException("target_name is required");
            var target = GameObject.Find(targetName);
            if (target == null) throw new InvalidOperationException($"Target object not found: {targetName}");
            Camera cam = ResolveCamera(p["camera_name"]?.ToString());

            // Compute target world-space center: use renderer bounds if any, else transform.position.
            Vector3 center = target.transform.position;
            float radius = 1.0f;
            var renderers = target.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length > 0)
            {
                var bounds = renderers[0].bounds;
                for (int i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
                center = bounds.center;
                radius = Mathf.Max(0.5f, bounds.extents.magnitude);
            }

            float distance = p["distance"]?.ToObject<float>() ?? (radius * 3f);
            float yaw = p["yaw_degrees"]?.ToObject<float>() ?? -30f;        // around Y
            float pitch = p["pitch_degrees"]?.ToObject<float>() ?? 20f;      // tilt down
            float heightOffset = p["height_offset"]?.ToObject<float>() ?? 0f;

            // Place the camera on a sphere around `center` and look at it.
            float yawRad = yaw * Mathf.Deg2Rad;
            float pitchRad = pitch * Mathf.Deg2Rad;
            Vector3 offset = new Vector3(
                Mathf.Sin(yawRad) * Mathf.Cos(pitchRad),
                Mathf.Sin(pitchRad),
                -Mathf.Cos(yawRad) * Mathf.Cos(pitchRad)
            ) * distance;
            Vector3 newPos = center + offset + new Vector3(0f, heightOffset, 0f);

            Undo.RecordObject(cam.transform, "Bridge: frame object");
            cam.transform.position = newPos;
            cam.transform.LookAt(center);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());

            return new
            {
                ok = true,
                camera = cam.gameObject.name,
                target = targetName,
                center_x = center.x,
                center_y = center.y,
                center_z = center.z,
                distance = distance,
                yaw = yaw,
                pitch = pitch,
                camera_position_x = cam.transform.position.x,
                camera_position_y = cam.transform.position.y,
                camera_position_z = cam.transform.position.z,
                target_radius = radius,
            };
        }

        // Phase 106: position the SCENE VIEW camera (the one run_visual_qa /
        // studio_capture_screenshot actually renders from). All session the
        // QA shot framed the whole terrain because nothing could move the
        // SceneView. This gives deterministic close-ups: pass a target
        // object (frames its renderer bounds) or an explicit pivot, plus
        // pitch/yaw/size. size = orbit distance (small = close-up).
        private static object SetSceneView(JObject p)
        {
            var sv = SceneView.lastActiveSceneView;
            if (sv == null)
            {
                // Try to grab/instantiate any SceneView so headless-ish
                // editors still capture something sensible.
                if (SceneView.sceneViews != null && SceneView.sceneViews.Count > 0)
                    sv = SceneView.sceneViews[0] as SceneView;
            }
            if (sv == null)
                return new { ok = false, error = "No SceneView available (open a Scene window)" };

            Vector3 pivot = new Vector3(
                p["pivot_x"]?.ToObject<float>() ?? 0f,
                p["pivot_y"]?.ToObject<float>() ?? 0f,
                p["pivot_z"]?.ToObject<float>() ?? 0f);
            float size = p["size"]?.ToObject<float>() ?? 14f;
            string targetName = p["target"]?.ToString();
            string framedBy = "explicit_pivot";

            if (!string.IsNullOrEmpty(targetName))
            {
                var target = GameObject.Find(targetName);
                if (target == null)
                    return new { ok = false, error = $"Target not found: {targetName}" };
                pivot = target.transform.position;
                var rends = target.GetComponentsInChildren<Renderer>(true);
                if (rends.Length > 0)
                {
                    var b = rends[0].bounds;
                    for (int i = 1; i < rends.Length; i++) b.Encapsulate(rends[i].bounds);
                    pivot = b.center;
                    if (p["size"] == null)
                        size = Mathf.Max(2f, b.extents.magnitude * 1.6f);
                    framedBy = "renderer_bounds";
                }
                else framedBy = "transform_position";
            }

            float pitch = p["pitch"]?.ToObject<float>() ?? 12f;   // tilt down
            float yaw = p["yaw"]?.ToObject<float>() ?? 45f;       // around Y
            var rot = Quaternion.Euler(pitch, yaw, 0f);

            sv.orthographic = false;
            // instant=true so the camera is THERE immediately (a follow-up
            // screenshot RPC must not catch a mid-animation pose).
            sv.LookAt(pivot, rot, size, false, true);
            sv.Repaint();

            return new
            {
                ok = true,
                framed_by = framedBy,
                target = targetName ?? "",
                pivot_x = pivot.x,
                pivot_y = pivot.y,
                pivot_z = pivot.z,
                size,
                pitch,
                yaw,
            };
        }

        private static object ListCameras(JObject p)
        {
            var all = UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include);
            var rows = new List<object>();
            foreach (var cam in all)
            {
                if (!cam.gameObject.scene.IsValid()) continue;
                rows.Add(new
                {
                    name = cam.gameObject.name,
                    is_main = (cam == Camera.main),
                    fov = cam.fieldOfView,
                    orthographic = cam.orthographic,
                    orthographic_size = cam.orthographicSize,
                    near_clip = cam.nearClipPlane,
                    far_clip = cam.farClipPlane,
                    position_x = cam.transform.position.x,
                    position_y = cam.transform.position.y,
                    position_z = cam.transform.position.z,
                    rotation_x = cam.transform.eulerAngles.x,
                    rotation_y = cam.transform.eulerAngles.y,
                    rotation_z = cam.transform.eulerAngles.z,
                    active = cam.gameObject.activeInHierarchy,
                });
            }
            return new { ok = true, count = rows.Count, cameras = rows };
        }

        private static (Color start, float lifetime, float speed, float rate, float size) ParticlePreset(string preset)
        {
            // (startColor, startLifetime, startSpeed, emissionRate, startSize)
            switch ((preset ?? "").ToLowerInvariant())
            {
                case "fire":  return (new Color(1.0f, 0.45f, 0.10f, 0.85f), 1.5f, 1.6f, 60f, 0.35f);
                case "smoke": return (new Color(0.60f, 0.60f, 0.60f, 0.60f), 3.0f, 0.7f, 25f, 0.80f);
                case "magic": return (new Color(0.55f, 0.30f, 0.95f, 0.95f), 2.0f, 1.0f, 35f, 0.20f);
                case "dust":
                default:      return (new Color(0.85f, 0.78f, 0.55f, 0.45f), 4.0f, 0.4f, 12f, 0.45f);
            }
        }

        private static object AddParticleSystem(JObject p)
        {
            string targetName = p["target_name"]?.ToString();
            if (string.IsNullOrEmpty(targetName)) throw new ArgumentException("target_name is required");
            var go = GameObject.Find(targetName);
            if (go == null) throw new InvalidOperationException($"Object not found: {targetName}");

            string preset = p["preset"]?.ToString() ?? "dust";
            var ps = go.GetComponent<ParticleSystem>();
            bool created = false;
            if (ps == null)
            {
                ps = go.AddComponent<ParticleSystem>();
                Undo.RegisterCreatedObjectUndo(ps, "Bridge: add ParticleSystem");
                created = true;
            }
            else
            {
                Undo.RecordObject(ps, "Bridge: configure ParticleSystem");
            }

            var (color, lifetime, speed, rate, size) = ParticlePreset(preset);
            var main = ps.main;
            main.startColor = color;
            main.startLifetime = lifetime;
            main.startSpeed = speed;
            main.startSize = size;
            main.loop = true;
            main.playOnAwake = true;
            main.maxParticles = 1000;

            var emission = ps.emission;
            emission.enabled = true;
            emission.rateOverTime = rate;

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                target = targetName,
                preset = preset,
                created = created,
                emission_rate = rate,
                start_lifetime = lifetime,
                start_color_r = color.r,
                start_color_g = color.g,
                start_color_b = color.b,
            };
        }

        private static object SetParticleProperties(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var ps = go.GetComponent<ParticleSystem>();
            if (ps == null) throw new InvalidOperationException($"ParticleSystem not found on {name}");
            Undo.RecordObject(ps, "Bridge: set ParticleSystem properties");

            var main = ps.main;
            if (p["start_lifetime"] != null) main.startLifetime = Mathf.Max(0.01f, p["start_lifetime"].ToObject<float>());
            if (p["start_speed"] != null) main.startSpeed = p["start_speed"].ToObject<float>();
            if (p["start_size"] != null) main.startSize = Mathf.Max(0.001f, p["start_size"].ToObject<float>());
            if (p["max_particles"] != null) main.maxParticles = Mathf.Clamp(p["max_particles"].ToObject<int>(), 1, 10000);
            if (p["loop"] != null) main.loop = p["loop"].ToObject<bool>();
            JObject col = p["color"] as JObject;
            if (col != null)
                main.startColor = new Color(
                    col["r"]?.ToObject<float>() ?? 1f,
                    col["g"]?.ToObject<float>() ?? 1f,
                    col["b"]?.ToObject<float>() ?? 1f,
                    col["a"]?.ToObject<float>() ?? 1f
                );

            var emission = ps.emission;
            if (p["emission_rate"] != null) emission.rateOverTime = Mathf.Max(0f, p["emission_rate"].ToObject<float>());

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                name = name,
                start_lifetime = main.startLifetime.constant,
                start_speed = main.startSpeed.constant,
                emission_rate = emission.rateOverTime.constant,
                max_particles = main.maxParticles,
            };
        }

        private static object ListParticleSystems(JObject p)
        {
            var all = UnityEngine.Object.FindObjectsByType<ParticleSystem>(FindObjectsInactive.Include);
            var rows = new List<object>();
            float totalEmission = 0f;
            int totalMax = 0;
            foreach (var ps in all)
            {
                if (!ps.gameObject.scene.IsValid()) continue;
                var main = ps.main;
                var emission = ps.emission;
                float rate = emission.rateOverTime.constant;
                totalEmission += rate;
                totalMax += main.maxParticles;
                rows.Add(new
                {
                    name = ps.gameObject.name,
                    emission_rate = rate,
                    start_lifetime = main.startLifetime.constant,
                    start_speed = main.startSpeed.constant,
                    max_particles = main.maxParticles,
                    loop = main.loop,
                    play_on_awake = main.playOnAwake,
                    color_r = main.startColor.color.r,
                    color_g = main.startColor.color.g,
                    color_b = main.startColor.color.b,
                    active = ps.gameObject.activeInHierarchy,
                });
            }
            return new
            {
                ok = true,
                count = rows.Count,
                total_emission_rate = totalEmission,
                total_max_particles = totalMax,
                systems = rows,
            };
        }

        private static Color ColorFromJson(JObject c, Color fallback)
        {
            if (c == null) return fallback;
            return new Color(
                c["r"]?.ToObject<float>() ?? fallback.r,
                c["g"]?.ToObject<float>() ?? fallback.g,
                c["b"]?.ToObject<float>() ?? fallback.b,
                c["a"]?.ToObject<float>() ?? fallback.a
            );
        }

        private static void EnsureEventSystem()
        {
            if (UnityEngine.Object.FindAnyObjectByType<EventSystem>() != null) return;
            var es = new GameObject("EventSystem");
            es.AddComponent<EventSystem>();
            es.AddComponent<StandaloneInputModule>();
            Undo.RegisterCreatedObjectUndo(es, "Bridge: add EventSystem");
        }

        private static object CreateUICanvas(JObject p)
        {
            string name = p["name"]?.ToString() ?? "UICanvas";
            // Re-use an existing canvas with that name if present
            var existing = GameObject.Find(name);
            if (existing != null)
            {
                var existingCanvas = existing.GetComponent<Canvas>();
                if (existingCanvas != null)
                {
                    return new { ok = true, name = name, created = false, instance_id = existing.GetHashCode() };
                }
            }
            var go = new GameObject(name);
            var canvas = go.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            go.AddComponent<CanvasScaler>();
            go.AddComponent<GraphicRaycaster>();
            EnsureEventSystem();
            Undo.RegisterCreatedObjectUndo(go, "Bridge: create UI Canvas");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, name = name, created = true, instance_id = go.GetHashCode() };
        }

        private static Transform ResolveCanvasTransform(string canvasName)
        {
            if (string.IsNullOrEmpty(canvasName))
            {
                var canvas = UnityEngine.Object.FindAnyObjectByType<Canvas>();
                if (canvas == null) throw new InvalidOperationException("No Canvas in scene. Call create_ui_canvas first.");
                return canvas.transform;
            }
            var go = GameObject.Find(canvasName);
            if (go == null) throw new InvalidOperationException($"Canvas not found: {canvasName}");
            if (go.GetComponent<Canvas>() == null) throw new InvalidOperationException($"Object {canvasName} is not a Canvas.");
            return go.transform;
        }

        private static object CreateUIText(JObject p)
        {
            string canvasName = p["canvas_name"]?.ToString() ?? "";
            string name = p["name"]?.ToString() ?? "UIText";
            string text = p["text"]?.ToString() ?? "";
            float x = p["position_x"]?.ToObject<float>() ?? 0f;
            float y = p["position_y"]?.ToObject<float>() ?? 0f;
            float width = p["width"]?.ToObject<float>() ?? 400f;
            float height = p["height"]?.ToObject<float>() ?? 80f;
            int fontSize = p["font_size"]?.ToObject<int>() ?? 36;
            Color color = ColorFromJson(p["color"] as JObject, Color.white);

            Transform parent = ResolveCanvasTransform(canvasName);
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var rect = go.AddComponent<RectTransform>();
            rect.anchoredPosition = new Vector2(x, y);
            rect.sizeDelta = new Vector2(width, height);
            var t = go.AddComponent<Text>();
            t.text = text;
            t.color = color;
            t.alignment = TextAnchor.MiddleCenter;
            t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            t.fontSize = fontSize;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            Undo.RegisterCreatedObjectUndo(go, "Bridge: create UI Text");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                name = name,
                canvas = parent.name,
                text = text,
                position_x = x,
                position_y = y,
                width = width,
                height = height,
                font_size = fontSize,
            };
        }

        private static object CreateUIButton(JObject p)
        {
            string canvasName = p["canvas_name"]?.ToString() ?? "";
            string name = p["name"]?.ToString() ?? "UIButton";
            string label = p["label"]?.ToString() ?? "Button";
            float x = p["position_x"]?.ToObject<float>() ?? 0f;
            float y = p["position_y"]?.ToObject<float>() ?? 0f;
            float width = p["width"]?.ToObject<float>() ?? 200f;
            float height = p["height"]?.ToObject<float>() ?? 60f;
            int fontSize = p["font_size"]?.ToObject<int>() ?? 24;
            Color bg = ColorFromJson(p["background_color"] as JObject, new Color(0.2f, 0.2f, 0.25f, 1f));
            Color labelColor = ColorFromJson(p["label_color"] as JObject, Color.white);

            Transform parent = ResolveCanvasTransform(canvasName);
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var rect = go.AddComponent<RectTransform>();
            rect.anchoredPosition = new Vector2(x, y);
            rect.sizeDelta = new Vector2(width, height);
            var image = go.AddComponent<Image>();
            image.color = bg;
            var button = go.AddComponent<Button>();
            button.targetGraphic = image;

            // Label child
            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(go.transform, false);
            var labelRect = labelGo.AddComponent<RectTransform>();
            labelRect.anchorMin = Vector2.zero;
            labelRect.anchorMax = Vector2.one;
            labelRect.sizeDelta = Vector2.zero;
            labelRect.anchoredPosition = Vector2.zero;
            var labelText = labelGo.AddComponent<Text>();
            labelText.text = label;
            labelText.color = labelColor;
            labelText.alignment = TextAnchor.MiddleCenter;
            labelText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            labelText.fontSize = fontSize;

            Undo.RegisterCreatedObjectUndo(go, "Bridge: create UI Button");
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                name = name,
                canvas = parent.name,
                label = label,
                position_x = x,
                position_y = y,
                width = width,
                height = height,
            };
        }

        private static object ListUIElements(JObject p)
        {
            var canvases = UnityEngine.Object.FindObjectsByType<Canvas>(FindObjectsInactive.Include);
            var canvasRows = new List<object>();
            int totalTexts = 0;
            int totalButtons = 0;
            foreach (var canvas in canvases)
            {
                if (!canvas.gameObject.scene.IsValid()) continue;
                var texts = canvas.GetComponentsInChildren<Text>(true);
                var buttons = canvas.GetComponentsInChildren<Button>(true);
                totalTexts += texts.Length;
                totalButtons += buttons.Length;
                var textRows = new List<object>();
                foreach (var t in texts)
                {
                    // Skip the labels-inside-buttons by parent check
                    if (t.GetComponentInParent<Button>() != null && t.transform.parent != canvas.transform) continue;
                    textRows.Add(new
                    {
                        name = t.gameObject.name,
                        text = t.text,
                        font_size = t.fontSize,
                    });
                }
                var buttonRows = new List<object>();
                foreach (var b in buttons)
                {
                    var lbl = b.GetComponentInChildren<Text>(true);
                    buttonRows.Add(new
                    {
                        name = b.gameObject.name,
                        label = lbl != null ? lbl.text : "",
                    });
                }
                canvasRows.Add(new
                {
                    name = canvas.gameObject.name,
                    render_mode = canvas.renderMode.ToString(),
                    active = canvas.gameObject.activeInHierarchy,
                    text_count = textRows.Count,
                    button_count = buttonRows.Count,
                    texts = textRows,
                    buttons = buttonRows,
                });
            }
            bool hasEventSystem = UnityEngine.Object.FindAnyObjectByType<EventSystem>() != null;
            return new
            {
                ok = true,
                canvas_count = canvasRows.Count,
                total_texts = totalTexts,
                total_buttons = totalButtons,
                has_event_system = hasEventSystem,
                canvases = canvasRows,
            };
        }

        private static BuildTarget ParseBuildTarget(string targetName)
        {
            if (string.IsNullOrEmpty(targetName)) return EditorUserBuildSettings.activeBuildTarget;
            switch (targetName.ToLowerInvariant())
            {
                case "windows":
                case "windows64":
                case "win64":
                case "standalonewindows64":
                    return BuildTarget.StandaloneWindows64;
                case "windows32":
                case "win32":
                case "standalonewindows":
                    return BuildTarget.StandaloneWindows;
                case "mac":
                case "osx":
                case "standaloneosx":
                    return BuildTarget.StandaloneOSX;
                case "linux":
                case "linux64":
                case "standalonelinux64":
                    return BuildTarget.StandaloneLinux64;
                case "webgl":
                    return BuildTarget.WebGL;
                case "android":
                    return BuildTarget.Android;
                case "ios":
                case "iphone":
                    return BuildTarget.iOS;
            }
            throw new ArgumentException($"Unknown build target: {targetName}. Use windows / mac / linux / webgl / android / ios.");
        }

        private static object ListBuildScenes(JObject p)
        {
            var scenes = EditorBuildSettings.scenes;
            var rows = new List<object>();
            int enabledCount = 0;
            for (int i = 0; i < scenes.Length; i++)
            {
                var s = scenes[i];
                if (s.enabled) enabledCount++;
                rows.Add(new
                {
                    index = i,
                    path = s.path,
                    enabled = s.enabled,
                });
            }
            return new
            {
                ok = true,
                count = scenes.Length,
                enabled_count = enabledCount,
                active_target = EditorUserBuildSettings.activeBuildTarget.ToString(),
                scenes = rows,
            };
        }

        private static object AddSceneToBuild(JObject p)
        {
            string scenePath = p["scene_path"]?.ToString();
            if (string.IsNullOrEmpty(scenePath)) throw new ArgumentException("scene_path is required");
            bool enabled = p["enabled"]?.ToObject<bool>() ?? true;

            // Validate scene file exists in the AssetDatabase
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) == null)
                throw new InvalidOperationException($"Scene asset not found at {scenePath}");

            var existing = EditorBuildSettings.scenes.ToList();
            int existingIdx = existing.FindIndex(s => s.path == scenePath);
            bool created;
            if (existingIdx >= 0)
            {
                existing[existingIdx] = new EditorBuildSettingsScene(scenePath, enabled);
                created = false;
            }
            else
            {
                existing.Add(new EditorBuildSettingsScene(scenePath, enabled));
                created = true;
            }
            EditorBuildSettings.scenes = existing.ToArray();
            return new
            {
                ok = true,
                scene_path = scenePath,
                enabled = enabled,
                added = created,
                total_scenes = existing.Count,
            };
        }

        private static object BuildPlayer(JObject p)
        {
            string targetName = p["target"]?.ToString() ?? "";
            string outputPath = p["output_path"]?.ToString();
            if (string.IsNullOrEmpty(outputPath)) throw new ArgumentException("output_path is required");
            bool developmentBuild = p["development_build"]?.ToObject<bool>() ?? false;

            BuildTarget target = ParseBuildTarget(targetName);

            // Collect scenes — explicit list, or fall back to enabled-in-EditorBuildSettings
            List<string> scenePaths = new List<string>();
            JArray sceneArr = p["scenes"] as JArray;
            if (sceneArr != null && sceneArr.Count > 0)
            {
                foreach (var t in sceneArr)
                {
                    var sp = t.ToString();
                    if (!string.IsNullOrEmpty(sp)) scenePaths.Add(sp);
                }
            }
            else
            {
                foreach (var s in EditorBuildSettings.scenes)
                {
                    if (s.enabled) scenePaths.Add(s.path);
                }
            }
            if (scenePaths.Count == 0)
                throw new InvalidOperationException("No scenes to build. Add at least one via add_scene_to_build or EditorBuildSettings.");

            // Ensure output dir exists
            var outFile = new FileInfo(outputPath);
            if (outFile.Directory != null && !outFile.Directory.Exists)
                outFile.Directory.Create();

            var options = new BuildPlayerOptions
            {
                scenes = scenePaths.ToArray(),
                locationPathName = outputPath,
                target = target,
                options = developmentBuild ? BuildOptions.Development : BuildOptions.None,
            };

            var report = BuildPipeline.BuildPlayer(options);
            var summary = report.summary;
            bool success = summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded;
            return new
            {
                ok = success,
                result = summary.result.ToString(),
                target = target.ToString(),
                output_path = outputPath,
                total_size_bytes = (long)summary.totalSize,
                total_errors = summary.totalErrors,
                total_warnings = summary.totalWarnings,
                total_time_seconds = summary.totalTime.TotalSeconds,
                scene_count = scenePaths.Count,
                development_build = developmentBuild,
            };
        }

        // ─── Phase 34: Behaviour Library ────────────────────────────────
        // The autonomous studio ships a small library of runtime
        // MonoBehaviour scripts (Rotator, Bobber, FollowTarget, ...) in
        // unity_plugin/Scripts/Behaviours/. They live in Assembly-CSharp;
        // we look them up by name from the UnityTools.Behaviours namespace
        // and AddComponent + set serialized fields via reflection.

        private static readonly string[] _BehaviourLibrary = new string[]
        {
            "Rotator", "Bobber", "PulseScale", "LookAtCamera",
            "DestroyAfter", "FollowTarget", "LoadSceneOnClick",
            "QuitOnClick", "KeyboardMover", "LocalizedText",
            // Phase 40: game-loop primitives
            "GameSession", "Collectible", "ScoreHUD",
            // Phase 41: pause + persistent settings
            "PauseMenu", "SettingsStore",
            // Phase 43: combat primitives
            "Projectile", "Shooter", "Spawner", "Enemy",
            // Phase 46: endless-runner primitives
            "AutoScroller", "LanePositioner",
            // Phase 50: platformer primitive
            "Jumper",
            // Phase 51: achievement primitive
            "Achievement",
            // Phase 52: audio + visual feedback primitives
            "SoundOnEvent", "HitFlash",
            // Phase 53: HUD + camera feel
            "HealthBar", "CameraShake",
            // Phase 54: settings menu primitives
            "VolumeSlider", "LocaleSelector",
            // Phase 55: narrative primitive
            "DialogText",
        };

        private static Type ResolveBehaviourType(string name)
        {
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("behaviour_name is required");
            // Try fully-qualified first
            var candidates = new[]
            {
                "UnityTools.Behaviours." + name,
                name,
            };
            foreach (var qn in candidates)
            {
                foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    var t = asm.GetType(qn, false, false);
                    if (t != null && typeof(MonoBehaviour).IsAssignableFrom(t)) return t;
                }
            }
            throw new InvalidOperationException(
                $"Behaviour type not found: {name}. Available: {string.Join(",", _BehaviourLibrary)}");
        }

        private static bool TryConvertJTokenToFieldValue(JToken token, Type targetType, out object result)
        {
            result = null;
            try
            {
                if (targetType == typeof(string))
                {
                    result = token.ToString(); return true;
                }
                if (targetType == typeof(int))
                {
                    result = token.ToObject<int>(); return true;
                }
                if (targetType == typeof(float))
                {
                    result = token.ToObject<float>(); return true;
                }
                if (targetType == typeof(double))
                {
                    result = token.ToObject<double>(); return true;
                }
                if (targetType == typeof(bool))
                {
                    result = token.ToObject<bool>(); return true;
                }
                if (targetType == typeof(Vector3))
                {
                    var jo = token as JObject;
                    if (jo == null) return false;
                    result = new Vector3(
                        jo["x"]?.ToObject<float>() ?? 0f,
                        jo["y"]?.ToObject<float>() ?? 0f,
                        jo["z"]?.ToObject<float>() ?? 0f
                    );
                    return true;
                }
                if (targetType == typeof(Vector2))
                {
                    var jo = token as JObject;
                    if (jo == null) return false;
                    result = new Vector2(
                        jo["x"]?.ToObject<float>() ?? 0f,
                        jo["y"]?.ToObject<float>() ?? 0f
                    );
                    return true;
                }
                if (targetType.IsEnum)
                {
                    result = Enum.Parse(targetType, token.ToString(), true);
                    return true;
                }
            }
            catch { }
            return false;
        }

        private static object AttachBehaviour(JObject p)
        {
            string targetName = p["target_name"]?.ToString();
            if (string.IsNullOrEmpty(targetName)) throw new ArgumentException("target_name is required");
            string behaviourName = p["behaviour_name"]?.ToString();
            if (string.IsNullOrEmpty(behaviourName)) throw new ArgumentException("behaviour_name is required");
            var go = GameObject.Find(targetName);
            if (go == null) throw new InvalidOperationException($"Object not found: {targetName}");

            Type type = ResolveBehaviourType(behaviourName);
            // Re-use existing component if present
            Component component = go.GetComponent(type);
            bool created = false;
            if (component == null)
            {
                component = go.AddComponent(type);
                Undo.RegisterCreatedObjectUndo(component, $"Bridge: attach {type.Name}");
                created = true;
            }
            else
            {
                Undo.RecordObject(component, $"Bridge: configure {type.Name}");
            }

            // Set serialized public fields from the params dict
            var applied = new List<string>();
            var skipped = new List<string>();
            JObject paramObj = p["params"] as JObject;
            if (paramObj != null)
            {
                foreach (var pair in paramObj)
                {
                    string fieldName = pair.Key;
                    JToken value = pair.Value;
                    FieldInfo field = type.GetField(fieldName, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
                    if (field == null)
                    {
                        skipped.Add(fieldName + ":not_found");
                        continue;
                    }
                    if (TryConvertJTokenToFieldValue(value, field.FieldType, out object converted))
                    {
                        field.SetValue(component, converted);
                        applied.Add(fieldName);
                    }
                    else
                    {
                        skipped.Add(fieldName + ":wrong_type");
                    }
                }
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                target = targetName,
                behaviour = type.Name,
                full_type = type.FullName,
                created = created,
                applied_fields = applied,
                skipped_fields = skipped,
            };
        }

        private static object ListBehaviourLibrary(JObject p)
        {
            var rows = new List<object>();
            foreach (var name in _BehaviourLibrary)
            {
                Type t;
                try { t = ResolveBehaviourType(name); }
                catch { t = null; }
                if (t == null)
                {
                    rows.Add(new { name = name, found = false, fields = new object[0] });
                    continue;
                }
                var fieldRows = new List<object>();
                foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.Instance))
                {
                    fieldRows.Add(new { name = f.Name, type = f.FieldType.Name });
                }
                rows.Add(new { name = name, found = true, full_type = t.FullName, fields = fieldRows });
            }
            return new { ok = true, count = rows.Count, library = rows };
        }

        private static object ListAttachedBehaviours(JObject p)
        {
            string targetName = p["target_name"]?.ToString();
            GameObject[] roots;
            if (!string.IsNullOrEmpty(targetName))
            {
                var go = GameObject.Find(targetName);
                if (go == null) throw new InvalidOperationException($"Object not found: {targetName}");
                roots = new[] { go };
            }
            else
            {
                roots = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include);
            }
            var rows = new List<object>();
            foreach (var go in roots)
            {
                if (!go.scene.IsValid()) continue;
                foreach (var c in go.GetComponents<MonoBehaviour>())
                {
                    if (c == null) continue;
                    Type t = c.GetType();
                    if (t.Namespace == "UnityTools.Behaviours")
                    {
                        rows.Add(new
                        {
                            game_object = go.name,
                            behaviour = t.Name,
                            full_type = t.FullName,
                        });
                    }
                }
            }
            return new { ok = true, count = rows.Count, attached = rows };
        }

        // ─── Phase 37: Marketing / project metadata ─────────────────────

        private static object SetPlayerSettings(JObject p)
        {
            string productName = p["product_name"]?.ToString();
            string companyName = p["company_name"]?.ToString();
            string version = p["version"]?.ToString();
            string bundleId = p["bundle_id"]?.ToString();
            int? defaultWidth = p["default_width"]?.ToObject<int?>();
            int? defaultHeight = p["default_height"]?.ToObject<int?>();

            if (!string.IsNullOrEmpty(productName)) PlayerSettings.productName = productName;
            if (!string.IsNullOrEmpty(companyName)) PlayerSettings.companyName = companyName;
            if (!string.IsNullOrEmpty(version)) PlayerSettings.bundleVersion = version;
            if (!string.IsNullOrEmpty(bundleId))
            {
                try
                {
                    PlayerSettings.SetApplicationIdentifier(
                        UnityEditor.Build.NamedBuildTarget.Standalone, bundleId);
                    PlayerSettings.SetApplicationIdentifier(
                        UnityEditor.Build.NamedBuildTarget.WebGL, bundleId);
                }
                catch
                {
                    // Older Unity: fall back to the universal setter
                    PlayerSettings.applicationIdentifier = bundleId;
                }
            }
            if (defaultWidth.HasValue && defaultWidth.Value > 0) PlayerSettings.defaultScreenWidth = defaultWidth.Value;
            if (defaultHeight.HasValue && defaultHeight.Value > 0) PlayerSettings.defaultScreenHeight = defaultHeight.Value;
            AssetDatabase.SaveAssets();
            return new
            {
                ok = true,
                product_name = PlayerSettings.productName,
                company_name = PlayerSettings.companyName,
                version = PlayerSettings.bundleVersion,
                bundle_id = PlayerSettings.applicationIdentifier,
                default_width = PlayerSettings.defaultScreenWidth,
                default_height = PlayerSettings.defaultScreenHeight,
            };
        }

        private static object GetPlayerSettings(JObject p)
        {
            return new
            {
                ok = true,
                product_name = PlayerSettings.productName,
                company_name = PlayerSettings.companyName,
                version = PlayerSettings.bundleVersion,
                bundle_id = PlayerSettings.applicationIdentifier,
                default_width = PlayerSettings.defaultScreenWidth,
                default_height = PlayerSettings.defaultScreenHeight,
                active_build_target = EditorUserBuildSettings.activeBuildTarget.ToString(),
                unity_version = Application.unityVersion,
            };
        }

        // ─── Phase 36: Material PBR (metallic + smoothness + emission) ──

        private static Material ResolveSharedMaterial(string targetName)
        {
            var go = GameObject.Find(targetName);
            if (go == null) throw new InvalidOperationException($"Object not found: {targetName}");
            var rend = go.GetComponent<Renderer>();
            if (rend == null) throw new InvalidOperationException($"Renderer not found on {targetName}");
            // Use sharedMaterial to avoid spawning a per-instance copy in editor —
            // we want the change to persist on the asset / shared material.
            var mat = rend.sharedMaterial;
            if (mat == null) throw new InvalidOperationException($"No material on {targetName}");
            return mat;
        }

        private static object SetMaterialPbr(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            Material mat = ResolveSharedMaterial(name);
            Undo.RecordObject(mat, "Bridge: set PBR properties");

            // Metallic (0..1)
            if (p["metallic"] != null && mat.HasProperty("_Metallic"))
            {
                mat.SetFloat("_Metallic", Mathf.Clamp01(p["metallic"].ToObject<float>()));
            }
            // Smoothness (0..1) — propagates to both _Smoothness and _Glossiness
            if (p["smoothness"] != null)
            {
                SetMaterialSmoothness(mat, Mathf.Clamp01(p["smoothness"].ToObject<float>()));
            }
            // Emission: enable keyword + set color + intensity
            bool emissionTouched = false;
            JObject ecol = p["emission_color"] as JObject;
            float emissionIntensity = p["emission_intensity"]?.ToObject<float>() ?? -1f;
            if (p["emission_enabled"] != null)
            {
                bool en = p["emission_enabled"].ToObject<bool>();
                if (en) mat.EnableKeyword("_EMISSION");
                else mat.DisableKeyword("_EMISSION");
                emissionTouched = true;
            }
            if (ecol != null || emissionIntensity >= 0f)
            {
                Color baseE = mat.HasProperty("_EmissionColor") ? mat.GetColor("_EmissionColor") : Color.black;
                Color targetE = baseE;
                if (ecol != null)
                {
                    targetE = new Color(
                        ecol["r"]?.ToObject<float>() ?? baseE.r,
                        ecol["g"]?.ToObject<float>() ?? baseE.g,
                        ecol["b"]?.ToObject<float>() ?? baseE.b,
                        ecol["a"]?.ToObject<float>() ?? baseE.a
                    );
                }
                if (emissionIntensity >= 0f)
                {
                    // Treat the color as normalised hue/sat/val and scale by intensity
                    targetE *= Mathf.Max(0f, emissionIntensity);
                }
                if (mat.HasProperty("_EmissionColor"))
                {
                    mat.SetColor("_EmissionColor", targetE);
                }
                if (!emissionTouched)
                {
                    // Setting an emission color implies enabling emission
                    mat.EnableKeyword("_EMISSION");
                }
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            EditorUtility.SetDirty(mat);

            return new
            {
                ok = true,
                target = name,
                material = mat.name,
                shader = mat.shader != null ? mat.shader.name : "",
                metallic = mat.HasProperty("_Metallic") ? mat.GetFloat("_Metallic") : 0f,
                smoothness = mat.HasProperty("_Smoothness")
                    ? mat.GetFloat("_Smoothness")
                    : (mat.HasProperty("_Glossiness") ? mat.GetFloat("_Glossiness") : 0f),
                emission_enabled = mat.IsKeywordEnabled("_EMISSION"),
                emission_color_r = mat.HasProperty("_EmissionColor") ? mat.GetColor("_EmissionColor").r : 0f,
                emission_color_g = mat.HasProperty("_EmissionColor") ? mat.GetColor("_EmissionColor").g : 0f,
                emission_color_b = mat.HasProperty("_EmissionColor") ? mat.GetColor("_EmissionColor").b : 0f,
            };
        }

        private static object GetMaterialProperties(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            Material mat = ResolveSharedMaterial(name);
            Color baseColor = mat.HasProperty("_BaseColor")
                ? mat.GetColor("_BaseColor")
                : (mat.HasProperty("_Color") ? mat.GetColor("_Color") : Color.white);
            Color emissionColor = mat.HasProperty("_EmissionColor") ? mat.GetColor("_EmissionColor") : Color.black;
            return new
            {
                ok = true,
                target = name,
                material = mat.name,
                shader = mat.shader != null ? mat.shader.name : "",
                base_color_r = baseColor.r,
                base_color_g = baseColor.g,
                base_color_b = baseColor.b,
                base_color_a = baseColor.a,
                metallic = mat.HasProperty("_Metallic") ? mat.GetFloat("_Metallic") : 0f,
                smoothness = mat.HasProperty("_Smoothness")
                    ? mat.GetFloat("_Smoothness")
                    : (mat.HasProperty("_Glossiness") ? mat.GetFloat("_Glossiness") : 0f),
                emission_enabled = mat.IsKeywordEnabled("_EMISSION"),
                emission_color_r = emissionColor.r,
                emission_color_g = emissionColor.g,
                emission_color_b = emissionColor.b,
            };
        }

        // ─── Phase 35: Atmosphere (skybox + fog) ────────────────────────

        private static object SetSkybox(JObject p)
        {
            string materialPath = p["material_path"]?.ToString();
            if (!string.IsNullOrEmpty(materialPath))
            {
                var mat = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
                if (mat == null) throw new InvalidOperationException($"Skybox material not found: {materialPath}");
                RenderSettings.skybox = mat;
                DynamicGI.UpdateEnvironment();
                EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
                return new
                {
                    ok = true,
                    mode = "asset",
                    material = materialPath,
                };
            }

            // Procedural path: tune the existing skybox if it's the Procedural shader,
            // or build a fresh procedural material in memory if not.
            float sunSize = p["sun_size"]?.ToObject<float>() ?? 0.04f;
            float atmosphereThickness = p["atmosphere_thickness"]?.ToObject<float>() ?? 1.0f;
            float exposure = p["exposure"]?.ToObject<float>() ?? 1.3f;
            Color skyTint = ColorFromJson(p["sky_tint"] as JObject, new Color(0.5f, 0.5f, 0.5f, 1f));
            Color groundColor = ColorFromJson(p["ground_color"] as JObject, new Color(0.37f, 0.34f, 0.31f, 1f));

            var sky = RenderSettings.skybox;
            if (sky == null || sky.shader == null || sky.shader.name != "Skybox/Procedural")
            {
                var shader = Shader.Find("Skybox/Procedural");
                if (shader == null) throw new InvalidOperationException("Skybox/Procedural shader not available on this URP/HDRP project. Provide material_path explicitly.");
                sky = new Material(shader) { name = "Procedural Skybox (UnityTools)" };
            }
            else
            {
                Undo.RecordObject(sky, "Bridge: tune procedural skybox");
            }
            if (sky.HasProperty("_SunSize"))             sky.SetFloat("_SunSize", Mathf.Clamp(sunSize, 0f, 1f));
            if (sky.HasProperty("_AtmosphereThickness")) sky.SetFloat("_AtmosphereThickness", Mathf.Clamp(atmosphereThickness, 0f, 5f));
            if (sky.HasProperty("_Exposure"))            sky.SetFloat("_Exposure", Mathf.Clamp(exposure, 0f, 8f));
            if (sky.HasProperty("_SkyTint"))             sky.SetColor("_SkyTint", skyTint);
            if (sky.HasProperty("_GroundColor"))         sky.SetColor("_GroundColor", groundColor);
            RenderSettings.skybox = sky;
            DynamicGI.UpdateEnvironment();
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                mode = "procedural",
                shader = sky.shader.name,
                sun_size = sunSize,
                atmosphere_thickness = atmosphereThickness,
                exposure = exposure,
                sky_tint_r = skyTint.r,
                sky_tint_g = skyTint.g,
                sky_tint_b = skyTint.b,
                ground_color_r = groundColor.r,
                ground_color_g = groundColor.g,
                ground_color_b = groundColor.b,
            };
        }

        private static object SetFog(JObject p)
        {
            if (p["enabled"] != null) RenderSettings.fog = p["enabled"].ToObject<bool>();
            JObject col = p["color"] as JObject;
            if (col != null)
                RenderSettings.fogColor = new Color(
                    col["r"]?.ToObject<float>() ?? RenderSettings.fogColor.r,
                    col["g"]?.ToObject<float>() ?? RenderSettings.fogColor.g,
                    col["b"]?.ToObject<float>() ?? RenderSettings.fogColor.b,
                    col["a"]?.ToObject<float>() ?? RenderSettings.fogColor.a
                );
            string modeStr = p["mode"]?.ToString();
            if (!string.IsNullOrEmpty(modeStr) && Enum.TryParse<FogMode>(modeStr, true, out var mode))
                RenderSettings.fogMode = mode;
            if (p["density"] != null) RenderSettings.fogDensity = Mathf.Max(0f, p["density"].ToObject<float>());
            if (p["start_distance"] != null) RenderSettings.fogStartDistance = Mathf.Max(0f, p["start_distance"].ToObject<float>());
            if (p["end_distance"] != null) RenderSettings.fogEndDistance = Mathf.Max(0.001f, p["end_distance"].ToObject<float>());
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                enabled = RenderSettings.fog,
                mode = RenderSettings.fogMode.ToString(),
                density = RenderSettings.fogDensity,
                start_distance = RenderSettings.fogStartDistance,
                end_distance = RenderSettings.fogEndDistance,
                color_r = RenderSettings.fogColor.r,
                color_g = RenderSettings.fogColor.g,
                color_b = RenderSettings.fogColor.b,
            };
        }

        private static object GetAtmosphereState(JObject p)
        {
            var sky = RenderSettings.skybox;
            string shaderName = (sky != null && sky.shader != null) ? sky.shader.name : "";
            bool procedural = shaderName == "Skybox/Procedural";
            return new
            {
                ok = true,
                skybox_present = sky != null,
                skybox_shader = shaderName,
                skybox_procedural = procedural,
                skybox_sun_size = (procedural && sky.HasProperty("_SunSize")) ? sky.GetFloat("_SunSize") : 0f,
                skybox_exposure = (procedural && sky.HasProperty("_Exposure")) ? sky.GetFloat("_Exposure") : 0f,
                fog_enabled = RenderSettings.fog,
                fog_mode = RenderSettings.fogMode.ToString(),
                fog_density = RenderSettings.fogDensity,
                fog_start_distance = RenderSettings.fogStartDistance,
                fog_end_distance = RenderSettings.fogEndDistance,
                fog_color_r = RenderSettings.fogColor.r,
                fog_color_g = RenderSettings.fogColor.g,
                fog_color_b = RenderSettings.fogColor.b,
                ambient_intensity = RenderSettings.ambientIntensity,
                ambient_mode = RenderSettings.ambientMode.ToString(),
            };
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

        private static object SetAudioSource(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var src = go.GetComponent<AudioSource>();
            if (src == null)
            {
                src = go.AddComponent<AudioSource>();
                Undo.RegisterCreatedObjectUndo(src, "Bridge: add AudioSource");
            }
            else
            {
                Undo.RecordObject(src, "Bridge: set AudioSource");
            }
            string clipResult = "";
            if (p["clip_path"] != null)
            {
                string clipPath = p["clip_path"].ToString();
                if (!string.IsNullOrEmpty(clipPath))
                {
                    var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(clipPath);
                    if (clip == null)
                    {
                        clipResult = $"clip not found at {clipPath}";
                    }
                    else
                    {
                        src.clip = clip;
                        clipResult = clipPath;
                    }
                }
            }
            if (p["loop"] != null) src.loop = p["loop"].ToObject<bool>();
            if (p["play_on_awake"] != null) src.playOnAwake = p["play_on_awake"].ToObject<bool>();
            if (p["volume"] != null) src.volume = Mathf.Clamp01(p["volume"].ToObject<float>());
            if (p["pitch"] != null) src.pitch = p["pitch"].ToObject<float>();
            if (p["spatial_blend"] != null) src.spatialBlend = Mathf.Clamp01(p["spatial_blend"].ToObject<float>());
            if (p["min_distance"] != null) src.minDistance = Mathf.Max(0f, p["min_distance"].ToObject<float>());
            if (p["max_distance"] != null) src.maxDistance = Mathf.Max(0.001f, p["max_distance"].ToObject<float>());
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                name = name,
                clip = clipResult,
                loop = src.loop,
                volume = src.volume,
                spatial_blend = src.spatialBlend,
            };
        }

        private static object SetLightProperties(JObject p)
        {
            string name = p["name"]?.ToString();
            if (string.IsNullOrEmpty(name)) throw new ArgumentException("name is required");
            var go = GameObject.Find(name);
            if (go == null) throw new InvalidOperationException($"Object not found: {name}");
            var light = go.GetComponent<Light>();
            if (light == null) throw new InvalidOperationException($"Light component not found on {name}");
            Undo.RecordObject(light, "Bridge: set light properties");
            JObject col = p["color"] as JObject;
            if (col != null)
                light.color = new Color(
                    col["r"]?.ToObject<float>() ?? light.color.r,
                    col["g"]?.ToObject<float>() ?? light.color.g,
                    col["b"]?.ToObject<float>() ?? light.color.b,
                    col["a"]?.ToObject<float>() ?? light.color.a
                );
            if (p["intensity"] != null) light.intensity = Mathf.Max(0f, p["intensity"].ToObject<float>());
            if (p["range"] != null) light.range = Mathf.Max(0f, p["range"].ToObject<float>());
            if (p["spot_angle"] != null) light.spotAngle = Mathf.Clamp(p["spot_angle"].ToObject<float>(), 1f, 179f);
            if (p["shadows_enabled"] != null)
                light.shadows = p["shadows_enabled"].ToObject<bool>() ? LightShadows.Soft : LightShadows.None;
            if (p["shadow_strength"] != null) light.shadowStrength = Mathf.Clamp01(p["shadow_strength"].ToObject<float>());
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                name = name,
                light_type = light.type.ToString(),
                intensity = light.intensity,
                range = light.range,
                shadows = light.shadows.ToString(),
                color_r = light.color.r,
                color_g = light.color.g,
                color_b = light.color.b,
            };
        }

        private static object SetAmbientLight(JObject p)
        {
            JObject col = p["color"] as JObject;
            if (col != null)
                RenderSettings.ambientLight = new Color(
                    col["r"]?.ToObject<float>() ?? RenderSettings.ambientLight.r,
                    col["g"]?.ToObject<float>() ?? RenderSettings.ambientLight.g,
                    col["b"]?.ToObject<float>() ?? RenderSettings.ambientLight.b,
                    col["a"]?.ToObject<float>() ?? RenderSettings.ambientLight.a
                );
            if (p["intensity"] != null) RenderSettings.ambientIntensity = Mathf.Max(0f, p["intensity"].ToObject<float>());
            string modeStr = p["mode"]?.ToString();
            if (!string.IsNullOrEmpty(modeStr))
            {
                if (Enum.TryParse<UnityEngine.Rendering.AmbientMode>(modeStr, true, out var mode))
                    RenderSettings.ambientMode = mode;
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                color_r = RenderSettings.ambientLight.r,
                color_g = RenderSettings.ambientLight.g,
                color_b = RenderSettings.ambientLight.b,
                intensity = RenderSettings.ambientIntensity,
                mode = RenderSettings.ambientMode.ToString(),
            };
        }

        private static object ListLights(JObject p)
        {
            var all = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Include);
            var rows = new List<object>();
            float totalIntensity = 0f;
            int shadowCount = 0;
            foreach (var light in all)
            {
                if (!light.gameObject.scene.IsValid()) continue;
                totalIntensity += light.intensity;
                if (light.shadows != LightShadows.None) shadowCount++;
                rows.Add(new
                {
                    name = light.gameObject.name,
                    light_type = light.type.ToString(),
                    intensity = light.intensity,
                    range = light.range,
                    color_r = light.color.r,
                    color_g = light.color.g,
                    color_b = light.color.b,
                    shadows = light.shadows.ToString(),
                    active = light.gameObject.activeInHierarchy,
                });
            }
            return new
            {
                ok = true,
                count = rows.Count,
                total_intensity = totalIntensity,
                shadow_casting_count = shadowCount,
                ambient_intensity = RenderSettings.ambientIntensity,
                ambient_mode = RenderSettings.ambientMode.ToString(),
                ambient_color_r = RenderSettings.ambientLight.r,
                ambient_color_g = RenderSettings.ambientLight.g,
                ambient_color_b = RenderSettings.ambientLight.b,
                lights = rows,
            };
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
            int repaired = 0;
            int preservedTextures = 0;
            foreach (var go in targets.Take(max))
            {
                if (go == null || !go.scene.IsValid()) continue;
                string cat = GuessCategory(go);
                Color color = colors.TryGetValue(cat, out var c) ? c : colors["default"];
                foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                {
                    if (renderer == null) continue;
                    Material source = renderer.sharedMaterial;
                    bool hadTexture = HasAnyTexture(source);
                    bool wasBroken = IsBrokenMaterial(source);
                    var mat = CreatePaletteMaterial(source, $"UnityTools_{palette}_{cat}", color, cat == "water" ? 0.65f : 0.15f);
                    Undo.RecordObject(renderer, "UnityTools: apply material palette");
                    renderer.sharedMaterial = mat;
                    if (wasBroken) repaired++;
                    if (hadTexture && HasAnyTexture(mat)) preservedTextures++;
                    changed++;
                }
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new { ok = true, query, category, palette, changed_renderers = changed, repaired_materials = repaired, preserved_texture_materials = preservedTextures, pipeline = ActivePipelineName() };
        }

        private static object DiagnoseMaterialIssues(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string category = p["category"]?.ToString() ?? "";
            int max = Mathf.Clamp(p["max"]?.ToObject<int>() ?? 2000, 1, 10000);
            var targets = string.IsNullOrWhiteSpace(query) && string.IsNullOrWhiteSpace(category)
                ? UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include).AsEnumerable()
                : FindSemanticObjects(query, category);

            int renderers = 0;
            int missingMaterials = 0;
            int brokenMaterials = 0;
            int textureMaterials = 0;
            var samples = new List<object>();

            foreach (var go in targets.Take(max))
            {
                if (go == null || !go.scene.IsValid()) continue;
                foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                {
                    if (renderer == null) continue;
                    renderers++;
                    foreach (var mat in renderer.sharedMaterials)
                    {
                        if (mat == null)
                        {
                            missingMaterials++;
                            if (samples.Count < 20) samples.Add(new { object_name = go.name, issue = "missing_material", path = GetHierarchyPath(go.transform) });
                            continue;
                        }
                        if (HasAnyTexture(mat)) textureMaterials++;
                        if (IsBrokenMaterial(mat))
                        {
                            brokenMaterials++;
                            if (samples.Count < 20)
                            {
                                samples.Add(new
                                {
                                    object_name = go.name,
                                    material = mat.name,
                                    shader = mat.shader != null ? mat.shader.name : "(null)",
                                    issue = "broken_or_unsupported_shader",
                                    path = GetHierarchyPath(go.transform)
                                });
                            }
                        }
                    }
                }
            }

            return new
            {
                ok = true,
                query,
                category,
                pipeline = ActivePipelineName(),
                renderers,
                missing_materials = missingMaterials,
                broken_materials = brokenMaterials,
                materials_with_textures = textureMaterials,
                samples
            };
        }

        private static object RepairMaterialIssues(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string category = p["category"]?.ToString() ?? "";
            bool tint = p["tint"]?.ToObject<bool>() ?? false;
            string palette = p["palette"]?.ToString() ?? "forest";
            bool includeUnsupported = p["include_unsupported"]?.ToObject<bool>() ?? false;
            int max = Mathf.Clamp(p["max"]?.ToObject<int>() ?? 2000, 1, 10000);
            var colors = PaletteColors(palette);
            var targets = string.IsNullOrWhiteSpace(query) && string.IsNullOrWhiteSpace(category)
                ? UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include).AsEnumerable()
                : FindSemanticObjects(query, category);

            int scanned = 0;
            int repaired = 0;
            int created = 0;
            int preservedTextures = 0;
            var samples = new List<object>();

            foreach (var go in targets.Take(max))
            {
                if (go == null || !go.scene.IsValid()) continue;
                string cat = GuessCategory(go);
                Color color = colors.TryGetValue(cat, out var c) ? c : colors["default"];
                foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                {
                    if (renderer == null) continue;
                    scanned++;
                    var materials = renderer.sharedMaterials;
                    bool changedRenderer = false;
                    for (int i = 0; i < materials.Length; i++)
                    {
                        Material source = materials[i];
                        bool needsRepair = source == null || IsBrokenMaterial(source) || (includeUnsupported && !IsPipelineCompatible(source.shader));
                        if (!needsRepair && !tint) continue;

                        bool hadTexture = HasAnyTexture(source);
                        Material mat = needsRepair
                            ? CreatePipelineMaterialFrom(source, $"UnityTools_Repaired_{cat}")
                            : new Material(source) { name = $"UnityTools_Tinted_{cat}" };
                        if (tint) SetMaterialBaseColor(mat, color);
                        SetMaterialSmoothness(mat, cat == "water" ? 0.65f : 0.15f);
                        materials[i] = mat;
                        changedRenderer = true;
                        if (needsRepair) repaired++;
                        if (source == null) created++;
                        if (hadTexture && HasAnyTexture(mat)) preservedTextures++;
                        if (samples.Count < 20)
                        {
                            samples.Add(new
                            {
                                object_name = go.name,
                                material = mat.name,
                                shader = mat.shader != null ? mat.shader.name : "(null)",
                                path = GetHierarchyPath(go.transform)
                            });
                        }
                    }
                    if (changedRenderer)
                    {
                        Undo.RecordObject(renderer, "UnityTools: repair materials");
                        renderer.sharedMaterials = materials;
                    }
                }
            }

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                query,
                category,
                palette,
                pipeline = ActivePipelineName(),
                scanned_renderers = scanned,
                repaired_materials = repaired,
                created_materials = created,
                preserved_texture_materials = preservedTextures,
                samples
            };
        }

        private static object RepairTextureImportSettings(JObject p)
        {
            string query = p["query"]?.ToString() ?? "texture";
            int max = Mathf.Clamp(p["max"]?.ToObject<int>() ?? 500, 1, 5000);
            string[] guids = AssetDatabase.FindAssets(query);
            int changed = 0;
            var samples = new List<object>();
            foreach (string guid in guids.Take(max))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var importer = AssetImporter.GetAtPath(path) as TextureImporter;
                if (importer == null) continue;
                bool isNormal = LooksLikeNormalMap(path);
                bool isLinear = isNormal || LooksLikeLinearMap(path);
                bool dirty = false;
                if (importer.textureType != (isNormal ? TextureImporterType.NormalMap : TextureImporterType.Default))
                {
                    importer.textureType = isNormal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                    dirty = true;
                }
                if (importer.sRGBTexture == isLinear)
                {
                    importer.sRGBTexture = !isLinear;
                    dirty = true;
                }
                if (!importer.mipmapEnabled)
                {
                    importer.mipmapEnabled = true;
                    dirty = true;
                }
                if (importer.maxTextureSize < 2048)
                {
                    importer.maxTextureSize = 2048;
                    dirty = true;
                }
                if (importer.textureCompression == TextureImporterCompression.Uncompressed)
                {
                    importer.textureCompression = TextureImporterCompression.CompressedHQ;
                    dirty = true;
                }
                if (!dirty) continue;
                importer.SaveAndReimport();
                changed++;
                if (samples.Count < 20) samples.Add(new { path, normal_map = isNormal, linear_map = isLinear });
            }
            AssetDatabase.Refresh();
            return new { ok = true, query, scanned = Math.Min(guids.Length, max), changed_textures = changed, samples };
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
            // Real Tree1-sampled conifer + bark palette (see scatter).
            var pineMat = MakeMaterial("PineNeedles_RealColor", new Color(0.330f, 0.366f, 0.162f), 0.12f);
            var trunkMat = MakeMaterial("TreeTrunk_RealColor", new Color(0.363f, 0.326f, 0.244f), 0.10f);
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

        private static object RunVisualQA(JObject p)
        {
            bool captureScreenshot = p["capture_screenshot"]?.ToObject<bool>() ?? true;
            var scene = SceneManager.GetActiveScene();
            var objects = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include)
                .Where(go => go.scene.IsValid())
                .ToArray();
            var renderers = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include)
                .Where(r => r.gameObject.scene.IsValid())
                .ToArray();
            var lights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Include)
                .Where(l => l.gameObject.scene.IsValid())
                .ToArray();
            var cameras = UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include)
                .Where(c => c.gameObject.scene.IsValid())
                .ToArray();

            int missingMaterials = 0;
            int brokenMaterials = 0;
            int unsupportedMaterials = 0;
            foreach (var renderer in renderers)
            {
                foreach (var mat in renderer.sharedMaterials)
                {
                    if (mat == null)
                    {
                        missingMaterials++;
                        continue;
                    }
                    if (IsBrokenMaterial(mat)) brokenMaterials++;
                    else if (!IsPipelineCompatible(mat.shader)) unsupportedMaterials++;
                }
            }

            string screenshotPath = "";
            string screenshotError = "";
            if (captureScreenshot)
            {
                try
                {
                    screenshotPath = CaptureSceneViewScreenshot("AutopilotData/screenshots");
                }
                catch (Exception ex)
                {
                    screenshotError = ex.Message;
                }
            }

            var issues = new List<string>();
            if (missingMaterials > 0) issues.Add($"{missingMaterials} renderer material slots are missing materials.");
            if (brokenMaterials > 0) issues.Add($"{brokenMaterials} materials use broken/pink shaders.");
            if (unsupportedMaterials > 0) issues.Add($"{unsupportedMaterials} materials are not compatible with the active render pipeline.");
            if (cameras.Length == 0) issues.Add("No camera found in the active scene.");
            if (lights.Length == 0) issues.Add("No light found in the active scene.");
            if (renderers.Length > 1500) issues.Add("High renderer count; consider batching, LODs, or reducing scatter density.");

            return new
            {
                ok = true,
                scene = scene.name,
                screenshot_path = screenshotPath,
                screenshot_error = screenshotError,
                counts = new
                {
                    objects = objects.Length,
                    renderers = renderers.Length,
                    lights = lights.Length,
                    cameras = cameras.Length,
                    missing_materials = missingMaterials,
                    broken_materials = brokenMaterials,
                    unsupported_materials = unsupportedMaterials,
                },
                issues = issues,
                verdict = issues.Count == 0 ? "Scene QA passed." : "Scene QA found issues to review."
            };
        }

        private static object ProfileScenePerformance(JObject p)
        {
            int maxObjects = Mathf.Clamp(p["max_objects"]?.ToObject<int>() ?? 10000, 1, 100000);
            var objects = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include)
                .Where(go => go.scene.IsValid())
                .Take(maxObjects)
                .ToArray();
            var renderers = objects.SelectMany(go => go.GetComponents<Renderer>()).ToArray();
            var meshFilters = objects.SelectMany(go => go.GetComponents<MeshFilter>()).ToArray();
            var skinned = objects.SelectMany(go => go.GetComponents<SkinnedMeshRenderer>()).ToArray();
            var lights = objects.SelectMany(go => go.GetComponents<Light>()).ToArray();
            var terrains = objects.SelectMany(go => go.GetComponents<Terrain>()).ToArray();

            long vertices = 0;
            long triangles = 0;
            var meshNames = new HashSet<string>();
            foreach (var mf in meshFilters)
            {
                AccumulateMeshStats(mf.sharedMesh, meshNames, ref vertices, ref triangles);
            }
            foreach (var smr in skinned)
            {
                AccumulateMeshStats(smr.sharedMesh, meshNames, ref vertices, ref triangles);
            }

            int shadowCasters = renderers.Count(r => r.shadowCastingMode != ShadowCastingMode.Off);
            int receiveShadows = renderers.Count(r => r.receiveShadows);
            int materialSlots = renderers.Sum(r => r.sharedMaterials.Length);
            int uniqueMaterials = renderers
                .SelectMany(r => r.sharedMaterials)
                .Where(m => m != null)
                .Select(m => AssetDatabase.GetAssetPath(m).Length > 0 ? AssetDatabase.GetAssetPath(m) : RuntimeHelpers.GetHashCode(m).ToString())
                .Distinct()
                .Count();

            var suggestions = new List<string>();
            if (renderers.Length > 1000) suggestions.Add("Renderer count is high; prefer GPU instancing, batching, LOD groups, or fewer scatter objects.");
            if (triangles > 1000000) suggestions.Add("Triangle count is high; add LODs or use lower-poly assets for distant forest/rocks.");
            if (shadowCasters > 200) suggestions.Add("Too many shadow casters; disable shadows on dense trees/rocks and keep shadows for hero assets.");
            if (lights.Count(l => l.shadows != LightShadows.None) > 2) suggestions.Add("Multiple shadow-casting lights can be expensive in HDRP.");
            if (uniqueMaterials > 250) suggestions.Add("Many unique materials; merge/reuse materials to improve batching.");
            if (QualitySettings.antiAliasing > 0) suggestions.Add("Disable MSAA in editor while building heavy scenes.");

            return new
            {
                ok = true,
                sampled_objects = objects.Length,
                total_scene_objects = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include).Count(go => go.scene.IsValid()),
                renderers = renderers.Length,
                mesh_filters = meshFilters.Length,
                skinned_mesh_renderers = skinned.Length,
                terrains = terrains.Length,
                lights = lights.Length,
                shadow_casters = shadowCasters,
                receive_shadows = receiveShadows,
                vertices = vertices,
                triangles = triangles,
                unique_meshes = meshNames.Count,
                material_slots = materialSlots,
                unique_materials = uniqueMaterials,
                quality = new
                {
                    anti_aliasing = QualitySettings.antiAliasing,
                    shadow_distance = QualitySettings.shadowDistance,
                    lod_bias = QualitySettings.lodBias,
                    maximum_lod_level = QualitySettings.maximumLODLevel
                },
                suggestions = suggestions
            };
        }

        private static object AnalyzeLodDecimationCandidates(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string category = p["category"]?.ToString() ?? "";
            int max = Mathf.Clamp(p["max_results"]?.ToObject<int>() ?? 25, 1, 200);
            int minTriangles = Mathf.Max(0, p["min_triangles"]?.ToObject<int>() ?? 10000);

            var uses = CollectMeshUses(query, category)
                .Where(u => u.Triangles >= minTriangles)
                .ToList();

            long totalTriangles = uses.Sum(u => (long)u.Triangles);
            long totalVertices = uses.Sum(u => (long)u.Vertices);
            var groups = uses
                .GroupBy(u => u.MeshKey)
                .Select(g => new
                {
                    mesh = g.First().MeshName,
                    mesh_path = g.First().MeshPath,
                    category = MostCommon(g.Select(x => x.Category)),
                    instances = g.Count(),
                    vertices_per_instance = g.First().Vertices,
                    triangles_per_instance = g.First().Triangles,
                    total_vertices = g.Sum(x => (long)x.Vertices),
                    total_triangles = g.Sum(x => (long)x.Triangles),
                    sample_objects = g.Select(x => GetHierarchyPath(x.Owner.transform)).Distinct().Take(8).ToArray(),
                    has_lod_group = g.Any(x => x.Owner.GetComponentInParent<LODGroup>() != null),
                    has_lod_named_children = g.Any(x => HasLodNamedRenderer(x.Owner.transform.root.gameObject)),
                    recommendation = BuildLodRecommendation(g.First().Category, g.First().Triangles, g.Count())
                })
                .OrderByDescending(g => g.total_triangles)
                .Take(max)
                .ToList();

            var suggestions = new List<string>();
            if (totalTriangles > 1000000) suggestions.Add("High total triangle load detected; add LODGroup/proxy LODs to repeated tree/rock meshes.");
            if (groups.Any(g => g.instances > 20)) suggestions.Add("Repeated meshes dominate the cost; optimize repeated prefabs before individual hero objects.");
            if (groups.Any(g => !g.has_lod_group)) suggestions.Add("Some heavy meshes have no LODGroup; use apply_lod_decimation_plan with create_proxy_lods=true.");

            return new
            {
                ok = true,
                query = query,
                category = category,
                min_triangles = minTriangles,
                mesh_use_count = uses.Count,
                total_vertices = totalVertices,
                total_triangles = totalTriangles,
                groups = groups,
                suggestions = suggestions
            };
        }

        private static object ApplyLodDecimationPlan(JObject p)
        {
            string query = p["query"]?.ToString() ?? "";
            string category = p["category"]?.ToString() ?? "tree";
            int maxObjects = Mathf.Clamp(p["max_objects"]?.ToObject<int>() ?? 150, 1, 1000);
            int minTriangles = Mathf.Max(0, p["min_triangles_per_object"]?.ToObject<int>() ?? 25000);
            bool createProxyLods = p["create_proxy_lods"]?.ToObject<bool>() ?? true;
            bool replaceWithProxy = p["replace_with_proxy"]?.ToObject<bool>() ?? false;
            bool disableShadows = p["disable_shadows"]?.ToObject<bool>() ?? true;
            bool markStatic = p["mark_static"]?.ToObject<bool>() ?? true;
            float lod0 = Mathf.Clamp01(p["lod0_screen_relative_height"]?.ToObject<float>() ?? 0.38f);
            float lod1 = Mathf.Clamp01(p["lod1_screen_relative_height"]?.ToObject<float>() ?? 0.08f);

            var uses = CollectMeshUses(query, category)
                .Where(u => u.Triangles >= minTriangles)
                .OrderByDescending(u => u.Triangles)
                .ToList();
            var roots = CollapseToOptimizationRoots(uses.Select(u => u.Owner).ToList())
                .Take(maxObjects)
                .ToList();

            int lodGroupsAdded = 0;
            int proxyObjectsCreated = 0;
            int renderersOptimized = 0;
            int originalRenderersDisabled = 0;
            var samples = new List<object>();

            foreach (var root in roots)
            {
                if (root == null || !root.scene.IsValid()) continue;
                var highRenderers = root.GetComponentsInChildren<Renderer>(true)
                    .Where(r => r != null && !r.name.StartsWith("UnityTools_LODProxy_", StringComparison.OrdinalIgnoreCase))
                    .ToArray();
                if (highRenderers.Length == 0) continue;

                if (disableShadows)
                {
                    foreach (var renderer in highRenderers)
                    {
                        Undo.RecordObject(renderer, "UnityTools: LOD optimize renderer");
                        renderer.shadowCastingMode = ShadowCastingMode.Off;
                        renderer.receiveShadows = false;
                        renderersOptimized++;
                    }
                }
                if (markStatic)
                {
                    GameObjectUtility.SetStaticEditorFlags(root, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                }

                Renderer proxyRenderer = null;
                if (createProxyLods)
                {
                    proxyRenderer = CreateLodProxy(root, GuessCategory(root));
                    proxyObjectsCreated++;

                    var group = root.GetComponent<LODGroup>();
                    if (group == null)
                    {
                        group = Undo.AddComponent<LODGroup>(root);
                        lodGroupsAdded++;
                    }
                    Undo.RecordObject(group, "UnityTools: configure proxy LOD");
                    group.SetLODs(new[]
                    {
                        new LOD(Mathf.Max(lod0, lod1 + 0.01f), highRenderers),
                        new LOD(lod1, new[] { proxyRenderer }),
                    });
                    group.RecalculateBounds();
                }

                if (replaceWithProxy && proxyRenderer != null)
                {
                    foreach (var renderer in highRenderers)
                    {
                        Undo.RecordObject(renderer, "UnityTools: replace with proxy");
                        renderer.enabled = false;
                        originalRenderersDisabled++;
                    }
                    proxyRenderer.enabled = true;
                }

                samples.Add(new
                {
                    root = GetHierarchyPath(root.transform),
                    category = GuessCategory(root),
                    renderers = highRenderers.Length,
                    proxy = proxyRenderer != null ? proxyRenderer.gameObject.name : "",
                    replaced = replaceWithProxy
                });
            }

            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return new
            {
                ok = true,
                query = query,
                category = category,
                min_triangles_per_object = minTriangles,
                candidates = uses.Count,
                optimized_roots = roots.Count,
                lod_groups_added = lodGroupsAdded,
                proxy_objects_created = proxyObjectsCreated,
                renderers_optimized = renderersOptimized,
                original_renderers_disabled = originalRenderersDisabled,
                mode = replaceWithProxy ? "aggressive_proxy_replace" : "safe_lod_proxy",
                samples = samples.Take(20).ToArray()
            };
        }

        private static object CreateSceneSnapshot(JObject p)
        {
            var scene = SceneManager.GetActiveScene();
            string label = SanitizeFileName(p["label"]?.ToString() ?? "manual");
            if (string.IsNullOrEmpty(scene.path))
            {
                string newPath = "Assets/AutopilotSnapshots/UnsavedScene_Source.unity";
                Directory.CreateDirectory(Path.Combine(Application.dataPath, "AutopilotSnapshots"));
                if (!EditorSceneManager.SaveScene(scene, newPath))
                    throw new InvalidOperationException("Could not save unsaved scene before snapshot.");
            }
            else
            {
                EditorSceneManager.SaveScene(scene);
            }

            Directory.CreateDirectory(Path.Combine(Application.dataPath, "AutopilotSnapshots"));
            string sceneName = SanitizeFileName(scene.name);
            string assetPath = $"Assets/AutopilotSnapshots/{sceneName}_{DateTime.Now:yyyyMMdd_HHmmss}_{label}.unity";
            assetPath = AssetDatabase.GenerateUniqueAssetPath(assetPath);
            bool ok = EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), assetPath, true);
            AssetDatabase.Refresh();
            return new { ok = ok, snapshot_path = assetPath, active_scene = SceneManager.GetActiveScene().path };
        }

        private static object RestoreSceneSnapshot(JObject p)
        {
            string path = p["path"]?.ToString() ?? p["snapshot_path"]?.ToString();
            if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("path is required");
            path = path.Replace("\\", "/");
            if (!path.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Snapshot path must be a Unity asset path under Assets/.");
            if (!File.Exists(Path.Combine(ProjectRootPath(), path)))
                throw new FileNotFoundException($"Snapshot not found: {path}");
            var scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
            return new { ok = true, scene = scene.name, path = scene.path };
        }

        private static void AccumulateMeshStats(Mesh mesh, HashSet<string> meshNames, ref long vertices, ref long triangles)
        {
            if (mesh == null) return;
            vertices += mesh.vertexCount;
            meshNames.Add(AssetDatabase.GetAssetPath(mesh).Length > 0 ? AssetDatabase.GetAssetPath(mesh) : RuntimeHelpers.GetHashCode(mesh).ToString());
            for (int i = 0; i < mesh.subMeshCount; i++)
            {
                triangles += (long)mesh.GetIndexCount(i) / 3L;
            }
        }

        private static byte[] RenderCameraToPng(Camera cam, int width, int height)
        {
            var rt = new RenderTexture(width, height, 24);
            var prevActive = RenderTexture.active;
            var prevTarget = cam.targetTexture;
            try
            {
                cam.targetTexture = rt;
                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(width, height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                tex.Apply();
                byte[] bytes = tex.EncodeToPNG();
                UnityEngine.Object.DestroyImmediate(tex);
                return bytes;
            }
            finally
            {
                cam.targetTexture = prevTarget;
                RenderTexture.active = prevActive;
                rt.Release();
                UnityEngine.Object.DestroyImmediate(rt);
            }
        }

        private static string CaptureSceneViewScreenshot(string relativeFolder)
        {
            // Source viewpoint: the SceneView camera (or Main). The
            // SceneView camera has no HDAdditionalCameraData, so a bare
            // cam.Render() in HDRP can produce a degraded image. Try a
            // throwaway camera WITH HDRP camera data first; if anything
            // throws, FALL BACK to rendering the source directly so we
            // ALWAYS return an image (never "no screenshot path").
            Camera src = null;
            var sceneView = SceneView.lastActiveSceneView;
            if (sceneView != null) { sceneView.Repaint(); src = sceneView.camera; }
            if (src == null) src = Camera.main;
            if (src == null) throw new InvalidOperationException("No SceneView or MainCamera available for screenshot capture.");

            int width = 1280, height = 720;
            byte[] bytes = null;
            GameObject capGo = null;
            try
            {
                capGo = new GameObject("__UT_CaptureCam");
                capGo.hideFlags = HideFlags.HideAndDontSave;
                var cam = capGo.AddComponent<Camera>();
                cam.CopyFrom(src);
                cam.transform.position = src.transform.position;
                cam.transform.rotation = src.transform.rotation;
                cam.clearFlags = CameraClearFlags.Skybox;
                cam.enabled = false;
                var hdCamType = FindType("UnityEngine.Rendering.HighDefinition.HDAdditionalCameraData");
                if (hdCamType != null && capGo.GetComponent(hdCamType) == null)
                    capGo.AddComponent(hdCamType);
                bytes = RenderCameraToPng(cam, width, height);
            }
            catch (Exception)
            {
                bytes = null; // fall through to direct render
            }
            finally
            {
                if (capGo != null) UnityEngine.Object.DestroyImmediate(capGo);
            }

            if (bytes == null || bytes.Length < 256)
            {
                // robust fallback: render the source camera directly
                bytes = RenderCameraToPng(src, width, height);
            }

            string folder = Path.Combine(ProjectRootPath(), relativeFolder.Replace("/", Path.DirectorySeparatorChar.ToString()));
            Directory.CreateDirectory(folder);
            string path = Path.Combine(folder, $"visual_qa_{DateTime.Now:yyyyMMdd_HHmmss}.png");
            File.WriteAllBytes(path, bytes);
            AssetDatabase.Refresh();
            return path;
        }

        private static string ProjectRootPath()
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        }

        private static string SanitizeFileName(string value)
        {
            if (string.IsNullOrWhiteSpace(value)) return "snapshot";
            var invalid = Path.GetInvalidFileNameChars();
            var chars = value.Select(ch => invalid.Contains(ch) ? '_' : ch).ToArray();
            string cleaned = new string(chars).Trim('_', ' ');
            return string.IsNullOrWhiteSpace(cleaned) ? "snapshot" : cleaned;
        }

        private class MeshUse
        {
            public GameObject Owner;
            public Mesh Mesh;
            public int Vertices;
            public int Triangles;
            public string Category;
            public string MeshName;
            public string MeshPath;
            public string MeshKey;
        }

        private static List<MeshUse> CollectMeshUses(string query, string category)
        {
            var uses = new List<MeshUse>();
            string wantedCategory = Normalize(category);
            var queryTokens = Tokenize(query);

            foreach (var mf in UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include))
            {
                if (mf == null || mf.sharedMesh == null || !mf.gameObject.scene.IsValid()) continue;
                TryAddMeshUse(uses, mf.gameObject, mf.sharedMesh, wantedCategory, queryTokens);
            }
            foreach (var smr in UnityEngine.Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include))
            {
                if (smr == null || smr.sharedMesh == null || !smr.gameObject.scene.IsValid()) continue;
                TryAddMeshUse(uses, smr.gameObject, smr.sharedMesh, wantedCategory, queryTokens);
            }
            return uses;
        }

        private static void TryAddMeshUse(List<MeshUse> uses, GameObject go, Mesh mesh, string wantedCategory, List<string> queryTokens)
        {
            string cat = GuessCategory(go);
            if (!string.IsNullOrWhiteSpace(wantedCategory) && !CategoryMatches(cat, wantedCategory))
                return;
            if (queryTokens.Count > 0)
            {
                string hay = Normalize($"{go.name} {cat} {RendererWords(go)} {ComponentWords(go)} {AssetDatabase.GetAssetPath(mesh)} {mesh.name}");
                bool any = queryTokens.Any(t => hay.Contains(t) || SynonymsFor(t).Any(s => hay.Contains(s)));
                if (!any) return;
            }
            int triangles = MeshTriangleCount(mesh);
            string path = AssetDatabase.GetAssetPath(mesh);
            string key = StableMeshKey(mesh, path);
            uses.Add(new MeshUse
            {
                Owner = go,
                Mesh = mesh,
                Vertices = mesh.vertexCount,
                Triangles = triangles,
                Category = cat,
                MeshName = mesh.name,
                MeshPath = path,
                MeshKey = key
            });
        }

        private static string StableMeshKey(Mesh mesh, string path)
        {
            if (mesh == null) return "(null)";
            if (AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string guid, out long localId))
                return $"{guid}:{localId}";
            string runtimeId = RuntimeHelpers.GetHashCode(mesh).ToString();
            return !string.IsNullOrEmpty(path) ? $"{path}::{mesh.name}::{runtimeId}" : runtimeId;
        }

        private static int MeshTriangleCount(Mesh mesh)
        {
            if (mesh == null) return 0;
            long triangles = 0;
            for (int i = 0; i < mesh.subMeshCount; i++)
                triangles += (long)mesh.GetIndexCount(i) / 3L;
            return triangles > int.MaxValue ? int.MaxValue : (int)triangles;
        }

        private static string MostCommon(IEnumerable<string> values)
        {
            return values
                .Where(v => !string.IsNullOrWhiteSpace(v))
                .GroupBy(v => v)
                .OrderByDescending(g => g.Count())
                .Select(g => g.Key)
                .FirstOrDefault() ?? "other";
        }

        private static string BuildLodRecommendation(string category, int triangles, int instances)
        {
            if (instances > 20 && triangles > 50000)
                return "Repeated high-poly mesh: add proxy LODs or replace distant instances with low-poly variants first.";
            if (category == "tree" || category == "rock")
                return "Nature prop: safe proxy LOD is recommended; keep original as LOD0.";
            return "Heavy mesh: inspect manually, then add LODGroup or lower-poly replacement.";
        }

        private static bool HasLodNamedRenderer(GameObject root)
        {
            if (root == null) return false;
            return root.GetComponentsInChildren<Renderer>(true)
                .Any(r => Normalize(r.name).Contains("lod1") || Normalize(r.name).Contains("lod2") || Normalize(r.name).Contains("low"));
        }

        private static List<GameObject> CollapseToOptimizationRoots(List<GameObject> owners)
        {
            var roots = new List<GameObject>();
            foreach (var owner in owners.Where(o => o != null && o.scene.IsValid()))
            {
                GameObject root = FindSemanticOptimizationRoot(owner);
                if (roots.Any(existing => existing == root)) continue;
                if (roots.Any(existing => root.transform.IsChildOf(existing.transform))) continue;
                roots.RemoveAll(existing => existing.transform.IsChildOf(root.transform));
                roots.Add(root);
            }
            return roots;
        }

        private static GameObject FindSemanticOptimizationRoot(GameObject go)
        {
            Transform current = go.transform;
            string cat = GuessCategory(go);
            while (current.parent != null && current.parent.gameObject.scene.IsValid())
            {
                string parentCat = GuessCategory(current.parent.gameObject);
                if (!CategoryMatches(parentCat, cat)) break;
                if (current.parent.GetComponentsInChildren<Renderer>(true).Length > 24) break;
                current = current.parent;
            }
            return current.gameObject;
        }

        private static Renderer CreateLodProxy(GameObject root, string category)
        {
            var renderers = root.GetComponentsInChildren<Renderer>(true)
                .Where(r => r != null && !r.name.StartsWith("UnityTools_LODProxy_", StringComparison.OrdinalIgnoreCase))
                .ToArray();
            Bounds bounds = new Bounds(root.transform.position, Vector3.one);
            bool hasBounds = false;
            foreach (var sourceRenderer in renderers)
            {
                if (!hasBounds)
                {
                    bounds = sourceRenderer.bounds;
                    hasBounds = true;
                }
                else bounds.Encapsulate(sourceRenderer.bounds);
            }

            PrimitiveType primitive = category == "tree" ? PrimitiveType.Capsule : PrimitiveType.Cube;
            var proxy = GameObject.CreatePrimitive(primitive);
            proxy.name = $"UnityTools_LODProxy_{SanitizeFileName(root.name)}";
            Undo.RegisterCreatedObjectUndo(proxy, "UnityTools: create LOD proxy");
            proxy.transform.position = bounds.center;
            proxy.transform.rotation = root.transform.rotation;
            Vector3 size = bounds.size;
            if (category == "tree")
                proxy.transform.localScale = new Vector3(Mathf.Max(0.35f, size.x * 0.45f), Mathf.Max(0.8f, size.y * 0.5f), Mathf.Max(0.35f, size.z * 0.45f));
            else
                proxy.transform.localScale = new Vector3(Mathf.Max(0.35f, size.x), Mathf.Max(0.2f, size.y), Mathf.Max(0.35f, size.z));
            proxy.transform.SetParent(root.transform, true);

            var collider = proxy.GetComponent<Collider>();
            if (collider != null) UnityEngine.Object.DestroyImmediate(collider);

            var proxyRendererComponent = proxy.GetComponent<Renderer>();
            proxyRendererComponent.sharedMaterial = ProxyMaterialFor(category);
            proxyRendererComponent.shadowCastingMode = ShadowCastingMode.Off;
            proxyRendererComponent.receiveShadows = false;
            return proxyRendererComponent;
        }

        private static Material ProxyMaterialFor(string category)
        {
            string folder = "Assets/UnityToolsGenerated/Materials";
            Directory.CreateDirectory(Path.Combine(Application.dataPath, "UnityToolsGenerated/Materials"));
            string path = $"{folder}/UnityTools_LODProxy_{category}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat != null) return mat;
            Color color = category == "tree" ? new Color(0.06f, 0.22f, 0.08f)
                : category == "rock" ? new Color(0.30f, 0.30f, 0.28f)
                : new Color(0.25f, 0.24f, 0.20f);
            mat = MakeMaterial($"UnityTools_LODProxy_{category}", color, 0.12f);
            AssetDatabase.CreateAsset(mat, path);
            AssetDatabase.SaveAssets();
            return mat;
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
            var shader = PipelineLitShader();
            var mat = new Material(shader);
            mat.name = name;
            SetMaterialBaseColor(mat, color);
            SetMaterialSmoothness(mat, smoothness);
            return mat;
        }

        // Real conifer foliage + bark harvested from the user's Tree1
        // download (free3d "Tree1ByTyroSmith"). Cards use the alpha
        // needle-sprig PNG, trunk uses the bark JPG. If Unity hasn't
        // imported the texture yet we keep the proven solid colour ->
        // never white, never a hard dependency (same fallback discipline
        // as the rest of the procedural forest).
        private const string ConiferFoliageTex =
            "Assets/FantasyRPG/Textures/Foliage/Leaves0142_4_S.png";
        private const string ConiferBarkTex =
            "Assets/FantasyRPG/Textures/Foliage/BarkDecidious0143_5_S.jpg";

        private static Material MakeTexturedMaterial(
            string name, string assetPath, Color fallback,
            float smoothness, bool foliageAlpha)
        {
            var mat = MakeMaterial(name, fallback, smoothness);
            Texture2D tex = null;
            try { tex = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath); }
            catch { tex = null; }
            if (tex != null)
            {
                foreach (var p in new[] { "_BaseColorMap", "_BaseMap", "_MainTex" })
                    if (mat.HasProperty(p)) mat.SetTexture(p, tex);
                // Textured -> let the photo show at (near) full colour
                // instead of multiplying it down with the fallback tint.
                SetMaterialBaseColor(mat, foliageAlpha
                    ? Color.white : new Color(0.82f, 0.82f, 0.82f));
            }
            if (foliageAlpha)
            {
                // HDRP/Lit alpha-clipped + double-sided foliage card.
                foreach (var kv in new System.Collections.Generic.KeyValuePair<string, float>[]{
                    new System.Collections.Generic.KeyValuePair<string,float>("_AlphaCutoffEnable", 1f),
                    new System.Collections.Generic.KeyValuePair<string,float>("_AlphaCutoff", 0.42f),
                    new System.Collections.Generic.KeyValuePair<string,float>("_AlphaClip", 1f),
                    new System.Collections.Generic.KeyValuePair<string,float>("_Cutoff", 0.42f),
                    new System.Collections.Generic.KeyValuePair<string,float>("_DoubleSidedEnable", 1f),
                    new System.Collections.Generic.KeyValuePair<string,float>("_CullMode", 0f),
                    new System.Collections.Generic.KeyValuePair<string,float>("_CullModeForward", 0f),
                    new System.Collections.Generic.KeyValuePair<string,float>("_Cull", 0f) })
                    if (mat.HasProperty(kv.Key)) mat.SetFloat(kv.Key, kv.Value);
                mat.EnableKeyword("_ALPHATEST_ON");
                mat.EnableKeyword("_DOUBLESIDED_ON");
                mat.renderQueue = 2450; // AlphaTest
            }
            return mat;
        }

        // Cached, lazily built so all trees in a scatter share ONE
        // instanced card material. ScatterTerrainTrees nulls this at the
        // start of each run so a freshly imported texture is picked up.
        private static Material _coniferCardMat;
        private static Material ConiferCardMat()
        {
            if (_coniferCardMat == null)
                _coniferCardMat = MakeTexturedMaterial(
                    "Pine_FoliageCard_Real_HDRP", ConiferFoliageTex,
                    new Color(0.09f, 0.22f, 0.11f), 0.12f, true);
            return _coniferCardMat;
        }

        // 3 vertical quads crossed at 60deg, full 0..1 UVs so the whole
        // needle sprig shows on each card; double-sided tris as a safety
        // even if the material's cull-off doesn't take. ~12 tris, shared.
        private static Mesh _foliageCard;
        private static Mesh FoliageCardMesh()
        {
            if (_foliageCard != null) return _foliageCard;
            var v = new System.Collections.Generic.List<Vector3>();
            var uv = new System.Collections.Generic.List<Vector2>();
            var t = new System.Collections.Generic.List<int>();
            for (int q = 0; q < 3; q++)
            {
                float ang = q * (Mathf.PI / 3f);
                Vector3 d = new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang)) * 0.5f;
                int b = v.Count;
                v.Add(-d);             uv.Add(new Vector2(0f, 0f));
                v.Add(d);              uv.Add(new Vector2(1f, 0f));
                v.Add(d + Vector3.up); uv.Add(new Vector2(1f, 1f));
                v.Add(-d + Vector3.up);uv.Add(new Vector2(0f, 1f));
                t.Add(b); t.Add(b + 2); t.Add(b + 1);
                t.Add(b); t.Add(b + 3); t.Add(b + 2);
                t.Add(b); t.Add(b + 1); t.Add(b + 2);
                t.Add(b); t.Add(b + 2); t.Add(b + 3);
            }
            _foliageCard = new Mesh { name = "UT_FoliageCard" };
            _foliageCard.SetVertices(v);
            _foliageCard.SetUVs(0, uv);
            _foliageCard.SetTriangles(t, 0);
            _foliageCard.RecalculateNormals();
            _foliageCard.RecalculateBounds();
            return _foliageCard;
        }

        private static GameObject CardPart(string n, Transform parent,
            Vector3 lpos, float w, float h, float yaw, Material mat)
        {
            var go = new GameObject(n, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(parent);
            go.transform.localPosition = lpos;
            go.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);
            go.transform.localScale = new Vector3(w, h, w);
            go.GetComponent<MeshFilter>().sharedMesh = FoliageCardMesh();
            go.GetComponent<MeshRenderer>().sharedMaterial = mat;
            return go;
        }

        private static Material CreatePaletteMaterial(Material source, string name, Color color, float smoothness)
        {
            Material mat;
            if (source != null && !IsBrokenMaterial(source) && IsPipelineCompatible(source.shader))
            {
                mat = new Material(source);
                mat.name = name;
            }
            else
            {
                mat = CreatePipelineMaterialFrom(source, name);
            }
            SetMaterialBaseColor(mat, color);
            SetMaterialSmoothness(mat, smoothness);
            return mat;
        }

        private static Material CreatePipelineMaterialFrom(Material source, string name)
        {
            var shader = PipelineLitShader();
            var mat = new Material(shader);
            mat.name = name;
            if (source != null)
            {
                CopyKnownMaterialTextures(source, mat);
                Color baseColor = GetMaterialBaseColor(source);
                SetMaterialBaseColor(mat, baseColor);
            }
            return mat;
        }

        private static Shader PipelineLitShader()
        {
            string pipeline = ActivePipelineName();
            if (pipeline == "HDRP")
                return Shader.Find("HDRP/Lit") ?? Shader.Find("Hidden/HDRP/Lit") ?? Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard") ?? Shader.Find("Legacy Shaders/Diffuse") ?? Shader.Find("Unlit/Color");
            if (pipeline == "URP")
                return Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("HDRP/Lit") ?? Shader.Find("Standard") ?? Shader.Find("Legacy Shaders/Diffuse") ?? Shader.Find("Unlit/Color");
            return Shader.Find("Standard") ?? Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("HDRP/Lit") ?? Shader.Find("Legacy Shaders/Diffuse") ?? Shader.Find("Unlit/Color");
        }

        private static string ActivePipelineName()
        {
            var pipeline = GraphicsSettings.currentRenderPipeline;
            if (pipeline == null) return "BuiltIn";
            string type = pipeline.GetType().FullName ?? "";
            if (type.Contains("HighDefinition")) return "HDRP";
            if (type.Contains("Universal")) return "URP";
            return pipeline.GetType().Name;
        }

        private static bool IsPipelineCompatible(Shader shader)
        {
            if (shader == null) return false;
            if (IsBrokenShader(shader)) return false;
            string pipeline = ActivePipelineName();
            string name = shader.name ?? "";
            if (pipeline == "HDRP")
                return name.StartsWith("HDRP/", StringComparison.OrdinalIgnoreCase) || name.IndexOf("High Definition", StringComparison.OrdinalIgnoreCase) >= 0;
            if (pipeline == "URP")
                return name.StartsWith("Universal Render Pipeline/", StringComparison.OrdinalIgnoreCase) || name.StartsWith("Shader Graphs/", StringComparison.OrdinalIgnoreCase);
            return true;
        }

        private static bool IsBrokenMaterial(Material mat)
        {
            if (mat == null || mat.shader == null) return true;
            return IsBrokenShader(mat.shader);
        }

        private static bool IsBrokenShader(Shader shader)
        {
            if (shader == null) return true;
            string name = shader.name ?? "";
            return name.IndexOf("InternalError", StringComparison.OrdinalIgnoreCase) >= 0
                || name.IndexOf("Hidden/InternalError", StringComparison.OrdinalIgnoreCase) >= 0
                || name.IndexOf("Error", StringComparison.OrdinalIgnoreCase) >= 0
                || name.IndexOf("pink", StringComparison.OrdinalIgnoreCase) >= 0
                || !shader.isSupported;
        }

        private static bool HasAnyTexture(Material mat)
        {
            if (mat == null) return false;
            try
            {
                return mat.GetTexturePropertyNames().Any(prop => mat.GetTexture(prop) != null);
            }
            catch
            {
                return false;
            }
        }

        private static Color GetMaterialBaseColor(Material mat)
        {
            if (mat == null) return Color.white;
            if (mat.HasProperty("_BaseColor")) return mat.GetColor("_BaseColor");
            if (mat.HasProperty("_Color")) return mat.GetColor("_Color");
            return Color.white;
        }

        private static void SetMaterialBaseColor(Material mat, Color color)
        {
            if (mat == null) return;
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            if (mat.HasProperty("_Color")) mat.SetColor("_Color", color);
        }

        private static void SetMaterialSmoothness(Material mat, float smoothness)
        {
            if (mat == null) return;
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
            if (mat.HasProperty("_Glossiness")) mat.SetFloat("_Glossiness", smoothness);
        }

        private static void CopyKnownMaterialTextures(Material source, Material target)
        {
            if (source == null || target == null) return;
            CopyTexture(source, target, new[] { "_BaseColorMap", "_BaseMap", "_MainTex", "_Albedo", "_DiffuseMap" }, new[] { "_BaseColorMap", "_BaseMap", "_MainTex" });
            CopyTexture(source, target, new[] { "_NormalMap", "_BumpMap", "_Normal" }, new[] { "_NormalMap", "_BumpMap" });
            CopyTexture(source, target, new[] { "_MaskMap", "_MetallicGlossMap", "_MetallicMap", "_OcclusionMap" }, new[] { "_MaskMap", "_MetallicGlossMap", "_OcclusionMap" });
            CopyTexture(source, target, new[] { "_EmissionMap" }, new[] { "_EmissionMap" });
        }

        private static void CopyTexture(Material source, Material target, string[] sourceProps, string[] targetProps)
        {
            Texture texture = null;
            Vector2 scale = Vector2.one;
            Vector2 offset = Vector2.zero;
            foreach (string prop in sourceProps)
            {
                if (!source.HasProperty(prop)) continue;
                texture = source.GetTexture(prop);
                if (texture == null) continue;
                scale = source.GetTextureScale(prop);
                offset = source.GetTextureOffset(prop);
                break;
            }
            if (texture == null) return;
            foreach (string prop in targetProps)
            {
                if (!target.HasProperty(prop)) continue;
                target.SetTexture(prop, texture);
                target.SetTextureScale(prop, scale);
                target.SetTextureOffset(prop, offset);
            }
        }

        private static bool LooksLikeNormalMap(string path)
        {
            string n = Normalize(Path.GetFileNameWithoutExtension(path));
            return n.EndsWith(" n") || n.Contains(" normal") || n.Contains(" normalmap") || n.Contains(" norm") || n.Contains(" bump");
        }

        private static bool LooksLikeLinearMap(string path)
        {
            string n = Normalize(Path.GetFileNameWithoutExtension(path));
            return n.EndsWith(" r") || n.EndsWith(" m") || n.Contains(" rough") || n.Contains(" roughness")
                || n.Contains(" metallic") || n.Contains(" metalness") || n.Contains(" mask")
                || n.Contains(" occlusion") || n.Contains(" ambientocclusion") || n.Contains(" ao")
                || n.Contains(" height") || n.Contains(" displacement");
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

        // Cached unit cone mesh (radius 1 at y=0 base, apex at y=1),
        // built once and shared by every tier of every tree -> cheap +
        // GPU-instanceable. ~12 sides = 24 tris.
        private static Mesh _coneMesh;
        private static Mesh ConeMesh()
        {
            if (_coneMesh != null) return _coneMesh;
            const int N = 12;
            var verts = new Vector3[N + 2];
            var tris = new System.Collections.Generic.List<int>();
            verts[0] = new Vector3(0f, 1f, 0f);            // apex
            verts[1] = Vector3.zero;                       // base centre
            for (int i = 0; i < N; i++)
            {
                float a = (i / (float)N) * Mathf.PI * 2f;
                verts[2 + i] = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
            }
            for (int i = 0; i < N; i++)
            {
                int a = 2 + i, b = 2 + (i + 1) % N;
                tris.Add(0); tris.Add(b); tris.Add(a);     // side
                tris.Add(1); tris.Add(a); tris.Add(b);     // bottom cap
            }
            _coneMesh = new Mesh { name = "UT_ConeMesh" };
            _coneMesh.SetVertices(new System.Collections.Generic.List<Vector3>(verts));
            _coneMesh.SetTriangles(tris, 0);
            _coneMesh.RecalculateNormals();
            _coneMesh.RecalculateBounds();
            return _coneMesh;
        }

        private static GameObject ConePart(string n, Transform parent,
            Vector3 lpos, float radius, float height, Material mat)
        {
            var go = new GameObject(n, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(parent);
            go.transform.localPosition = lpos;
            go.transform.localScale = new Vector3(radius, height, radius);
            go.GetComponent<MeshFilter>().sharedMesh = ConeMesh();
            go.GetComponent<MeshRenderer>().sharedMaterial = mat;
            return go;
        }

        // Real conifer silhouette: thin tapered brown trunk + 3 stacked
        // green cone tiers (wide low -> narrow top). Pivot at base
        // (y=0) so the ground-snap keeps it on the surface. ~80 tris,
        // shared cone mesh -> cheap & instanceable. No FBX = reliable.
        private static void CreateSimplePine(string name, Vector3 pos, float scale, Transform parent, Material trunkMat, Material foliageMat, System.Random rng)
        {
            var root = new GameObject(name);
            root.transform.SetParent(parent);
            root.transform.position = pos;
            root.transform.rotation = Quaternion.Euler(
                RandomRange(rng, -2f, 2f),
                RandomRange(rng, 0f, 360f),
                RandomRange(rng, -2f, 2f));

            float h = RandomRange(rng, 0.9f, 1.15f);   // per-tree height jitter
            // trunk: thin tapered cone, coloured with the REAL bark
            // colour sampled from the user's Tree1 download.
            ConePart("Trunk", root.transform, Vector3.zero,
                0.10f * scale, 1.25f * scale * h, trunkMat);

            // 3 solid foliage tiers (wide low -> narrow top), the proven
            // Phase-146/147 conifer silhouette — now tinted with the REAL
            // conifer-needle colour sampled from the downloaded asset.
            // Solid = no alpha/UV => bulletproof in HDRP (the runtime
            // alpha-card path failed = the whole tree-saga failure mode;
            // this keeps the reliable geometry, real-derived colour).
            float baseY = 0.55f * scale * h;
            for (int t = 0; t < 3; t++)
            {
                float r = (1.15f - t * 0.32f) * scale;
                float th = (1.7f - t * 0.25f) * scale * h;
                ConePart($"Foliage{t}", root.transform,
                    new Vector3(0f, baseY, 0f), r, th, foliageMat);
                baseY += th * 0.55f;
            }
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

