#if UNITY_EDITOR
using UnityEditor;

namespace UnityTools.Autopilot.Editor
{
    /// <summary>
    /// Applies safe import settings for generated/downloaded FBX models.
    /// These assets are often props or non-Unity humanoids; forcing Humanoid creates
    /// noisy Hips/Head rig errors, so default to Generic/NoAvatar.
    /// </summary>
    public class ModelImportPostprocessor : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            var importer = (ModelImporter)assetImporter;
            importer.globalScale = 1f;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.meshCompression = ModelImporterMeshCompression.Medium;
            importer.isReadable = false;
            importer.optimizeMeshPolygons = true;

            var path = assetPath.ToLowerInvariant();
            if (path.Contains("character") || path.Contains("characters") || path.Contains("rig") || path.Contains("skeleton") || path.Contains("player"))
            {
                importer.animationType = ModelImporterAnimationType.Generic;
                importer.avatarSetup = ModelImporterAvatarSetup.NoAvatar;
            }
        }
    }
}
#endif
