using UnityEditor;

namespace UnityTools.Autopilot.Editor
{
    public sealed class AutopilotAssetImportCleaner : AssetPostprocessor
    {
        private void OnPreprocessModel()
        {
            if (!assetPath.StartsWith("Assets/Art/Characters/") &&
                !assetPath.StartsWith("Assets/FantasyRPG/Models/") &&
                !assetPath.StartsWith("Assets/Models/Sketchfab/"))
            {
                return;
            }

            if (assetImporter is not ModelImporter importer)
                return;

            // Many downloaded props/enemies are marked Humanoid but do not contain a
            // valid Unity humanoid skeleton. Generic avoids noisy Hips/Head rig errors.
            if (importer.animationType == ModelImporterAnimationType.Human)
            {
                importer.animationType = ModelImporterAnimationType.Generic;
                importer.avatarSetup = ModelImporterAvatarSetup.NoAvatar;
            }
        }
    }
}
