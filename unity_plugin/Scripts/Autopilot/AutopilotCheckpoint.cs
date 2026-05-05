using System.IO;
using UnityEngine;

namespace Autopilot
{
    public static class AutopilotCheckpoint
    {
        public static string CheckpointPath => Path.Combine(AutopilotStorage.DataRoot, "checkpoint.json");

        public static void Save(AutopilotTaskList tasks)
        {
            try
            {
                var json = JsonUtility.ToJson(tasks, true);
                File.WriteAllText(CheckpointPath, json);
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"AutopilotCheckpoint.Save failed: {ex}");
            }
        }

        public static AutopilotTaskList Load()
        {
            try
            {
                if (!File.Exists(CheckpointPath)) return null;
                var json = File.ReadAllText(CheckpointPath);
                return JsonUtility.FromJson<AutopilotTaskList>(json);
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"AutopilotCheckpoint.Load failed: {ex}");
                return null;
            }
        }
    }
}
