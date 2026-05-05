using UnityEditor;

namespace UnityTools.Autopilot.Editor
{
    public sealed class AutopilotImportedFbxPostprocessor : AssetPostprocessor
    {
        private void OnPreprocessModel()
        {
            if (!assetPath.StartsWith("Assets/Art/Characters/Imported/"))
                return;

            if (!assetPath.EndsWith(".fbx", System.StringComparison.OrdinalIgnoreCase))
                return;

            ModelImporter importer = (ModelImporter)assetImporter;
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.NoAvatar;
            importer.importAnimation = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
        }
    }
}
