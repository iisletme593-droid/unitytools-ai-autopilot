using UnityEngine;

namespace Autopilot
{
    /// <summary>
    /// Safe placeholders for non-Unity autopilot engines. The Python UnityTools
    /// pipeline owns Blender/HF execution; Unity should not fail compilation if
    /// those processors are not installed as editor scripts.
    /// </summary>
    public static class BlenderTaskProcessor
    {
        public static bool Execute(AutopilotTask task, out string reason)
        {
            reason = "Blender tasks are handled by the external UnityTools Python pipeline. No Unity-side Blender executor is installed.";
            Debug.LogWarning("[Autopilot] " + reason);
            return false;
        }
    }

    public static class HfTaskProcessor
    {
        public static bool Execute(AutopilotTask task, out string reason)
        {
            reason = "Hugging Face tasks are handled by the external UnityTools Python pipeline. No Unity-side HF executor is installed.";
            Debug.LogWarning("[Autopilot] " + reason);
            return false;
        }
    }

    public static class ValidateTaskProcessor
    {
        public static bool Execute(AutopilotTask task, out string reason)
        {
            reason = $"Validation acknowledged for task '{task?.id ?? "unknown"}'.";
            return true;
        }
    }
}
