# Scene Intelligence / Sahne Zekasi

UnityTools AI Autopilot v2.3 adds a scene-intelligence layer so the assistant does not depend on Unity tags. This is important because many imported assets stay `Untagged`, even when their names/materials clearly describe trees, rocks, terrain, campfires, buildings, and characters.

UnityTools AI Autopilot v2.3, modelin Unity tag'lerine bagimli kalmamasi icin scene-intelligence katmani ekler. Bu onemli cunku import edilen assetlerin cogu `Untagged` kalir; ama isimleri, hiyerarsileri ve materiallari agac, kaya, terrain, kamp atesi, bina veya karakter bilgisini tasir.

## New Tools / Yeni Tool'lar

- `unity_get_scene_catalog`: Reads the active scene and groups objects by semantic category.
- `unity_find_scene_objects_semantic`: Finds objects by name, hierarchy path, material, component, and category.
- `unity_delete_scene_objects_semantic`: Deletes matching scene objects without requiring tags.
- `unity_apply_material_palette`: Applies coherent palettes to trees, rocks, ground, campfires, buildings, and other objects.
- `unity_create_optimized_forest_scene`: Builds terrain, trees, rocks, fog, light, camera, names, and materials in one high-level RPC.
- `unity_optimize_editor_performance`: Lowers heavy editor/render settings for large scenes.
- `unity_export_scene_knowledge_base`: Exports `AutopilotData/scene_knowledge.md` and `.json` for deep scene memory.

## Why This Fixes The Tree Problem / Agac Sorununu Nasil Cozer

Old behavior:

```text
User: Remove all trees.
Assistant: Searches tag == tree.
Unity: Everything is Untagged.
Result: No objects found.
```

New behavior:

```text
User: Remove all trees.
Assistant: Calls unity_find_scene_objects_semantic or unity_delete_scene_objects_semantic.
Unity: Matches SparseTallPine_01, DeadTree_Silhouette_01, pine_tree_01_branch_g, etc.
Result: Trees are found even when tags are Untagged.
```

Eski davranis tag aradigi icin bos donuyordu. Yeni davranis isim, hierarchy, material, component ve kategori okudugu icin `SparseTallPine_01`, `DeadTree_Silhouette_01`, `pine_tree_01_branch_g` gibi objeleri bulur.

## Recommended Local Model / Onerilen Lokal Model

```env
UNITYTOOLS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:14b-instruct
USE_DUAL_AGENT=false
DUAL_AGENT_MASTER=qwen2.5:14b-instruct
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

Single-agent is the default because it is faster for Unity editing. Dual-agent is still available for complex planning, but the embedded Unity panel starts the fast single-agent core by default.

Single-agent varsayilan; Unity duzenlemelerinde daha hizlidir. Dual-agent kompleks planlama icin durur, fakat gomulu Unity paneli varsayilan olarak hizli single-agent core ile baslar.

## Performance Notes / Performans Notlari

For large prompts like `create 100 trees, terrain, fog, camera`, the assistant should prefer `unity_create_optimized_forest_scene` instead of creating every object through many separate calls. This reduces timeouts and avoids excessive editor overhead.

`100 agac, terrain, sis, kamera olustur` gibi buyuk promptlarda asistan tek tek obje olusturmak yerine `unity_create_optimized_forest_scene` kullanmalidir. Bu timeout riskini ve editor yukunu azaltir.

Use `unity_optimize_editor_performance` when the scene becomes heavy. It lowers anti-aliasing, LOD bias, shadow distance, and disables expensive renderer shadows where possible.

Sahne agirlasinca `unity_optimize_editor_performance` kullan. Anti-aliasing, LOD bias, shadow distance ve pahali shadow ayarlarini dusurur.

## Tool Argument Tolerance / Tool Arguman Toleransi

Local models sometimes call tools with natural argument names such as `object`, `target`, `object_type`, `color_palette`, or `max_results`. UnityTools normalizes these aliases before execution, so a call like this:

Lokal modeller bazen `object`, `target`, `object_type`, `color_palette` veya `max_results` gibi dogal arguman isimleri kullanir. UnityTools bunlari calistirmadan once normalize eder; yani su cagri:

```json
{"object": "trees", "color_palette": "forest", "max_results": 50}
```

is executed as:

su sekilde calisir:

```json
{"query": "trees", "category": "tree", "palette": "forest", "max": 50}
```

This prevents useful scene operations from failing just because one argument name was slightly different.

Bu sayede faydali sahne islemleri sadece bir arguman adi farkli geldi diye hata vermez.

## Pink Materials and Broken Textures / Pembe Material ve Bozuk Texture

In HDRP/URP projects, magenta or pink objects usually mean the material shader is missing or incompatible with the active render pipeline. UnityTools can now diagnose and repair these materials without throwing away the original texture links.

HDRP/URP projelerinde magenta/pembe objeler genelde material shader'inin eksik veya aktif render pipeline ile uyumsuz oldugunu gosterir. UnityTools artik bu materiallari orijinal texture baglantilarini atmadan diagnose/repair edebilir.

Use:

Kullan:

```text
unity_diagnose_material_issues
unity_repair_material_issues
unity_repair_texture_import_settings
```

The repair flow preserves common maps such as base color/albedo, normal, mask, metallic, occlusion, and emission maps when converting to an HDRP/URP/Built-in safe Lit shader.

Repair akisi HDRP/URP/Built-in uyumlu Lit shader'a donustururken base color/albedo, normal, mask, metallic, occlusion ve emission map gibi yaygin texture baglarini korur.
