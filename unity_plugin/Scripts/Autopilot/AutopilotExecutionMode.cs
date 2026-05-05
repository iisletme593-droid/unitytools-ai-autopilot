#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
#endif

namespace Autopilot
{
    public static class AutopilotExecutionMode
    {
#if UNITY_EDITOR
        private const string AllowAutomaticKey = "UnityTools.Autopilot.AllowAutomaticLoops";

        public static bool AllowAutomaticLoops => EditorPrefs.GetBool(AllowAutomaticKey, false);

        public static bool ShouldRunAutomatic(string feature)
        {
            if (AllowAutomaticLoops)
                return true;

            Debug.Log($"[UnityTools Autopilot] Automatic '{feature}' skipped. Autopilot is manual/chat-controlled.");
            return false;
        }

        [MenuItem("Tools/Autopilot/Mode/Enable Automatic Loops", false, 910)]
        public static void EnableAutomaticLoops()
        {
            EditorPrefs.SetBool(AllowAutomaticKey, true);
            Debug.Log("[UnityTools Autopilot] Automatic loops enabled.");
        }

        [MenuItem("Tools/Autopilot/Mode/Disable Automatic Loops (Chat Controlled)", false, 911)]
        public static void DisableAutomaticLoops()
        {
            EditorPrefs.SetBool(AllowAutomaticKey, false);
            Debug.Log("[UnityTools Autopilot] Automatic loops disabled. Chat/menu commands still work.");
        }
#else
        public static bool AllowAutomaticLoops => false;
        public static bool ShouldRunAutomatic(string feature) => false;
#endif
    }
}
