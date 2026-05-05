using UnityEngine;

namespace Autopilot
{
    [CreateAssetMenu(menuName = "Autopilot/Config", fileName = "AutopilotConfig")]
    public class AutopilotConfig : ScriptableObject
    {
        [Tooltip("Max retries for a failing task")]
        public int maxRetries = 3;

        [Tooltip("Default estimated seconds when not provided")]
        public float defaultEstimatedSeconds = 2f;

        [Tooltip("If true, autopilot CLI should run in headless mode")]
        public bool headless = true;
    }
}
