using System;
using System.IO;
using UnityEngine;
using System.Collections.Generic;
using System.Text;

namespace Autopilot
{
    public static class AutopilotStorage
    {
        public static string DataRoot
        {
            get
            {
                var root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "AutopilotData"));
                if (!Directory.Exists(root)) Directory.CreateDirectory(root);
                return root;
            }
        }

        public static string TasksPath => Path.Combine(DataRoot, "tasks.json");
        public static string LogPath => Path.Combine(DataRoot, "autopilot_logs.jsonl");

        public static AutopilotTaskList LoadTasks()
        {
            try
            {
                if (!File.Exists(TasksPath))
                    return new AutopilotTaskList { tasks = new AutopilotTask[0] };

                var json = File.ReadAllText(TasksPath);
                if (string.IsNullOrWhiteSpace(json))
                    return new AutopilotTaskList { tasks = new AutopilotTask[0] };

                var wrapper = JsonUtility.FromJson<AutopilotTaskList>(json);
                return wrapper ?? new AutopilotTaskList { tasks = new AutopilotTask[0] };
            }
            catch (Exception ex)
            {
                Debug.LogError($"AutopilotStorage.LoadTasks: {ex}");
                return new AutopilotTaskList { tasks = new AutopilotTask[0] };
            }
        }

        public static void SaveTasks(AutopilotTaskList tasks)
        {
            try
            {
                var json = JsonUtility.ToJson(tasks, true);
                File.WriteAllText(TasksPath, json);
            }
            catch (Exception ex)
            {
                Debug.LogError($"AutopilotStorage.SaveTasks: {ex}");
            }
        }

        public static readonly object _logLock = new object();
        public static long MaxLogFileSizeBytes { get; set; } = 10 * 1024 * 1024; // 10 MB default

        public static void AppendLog(AutopilotLogEntry entry)
        {
            AppendLogs(new[] { entry });
        }

        public static void AppendLogs(IEnumerable<AutopilotLogEntry> entries)
        {
            try
            {
                lock (_logLock)
                {
                    var sb = new StringBuilder();
                    foreach (var e in entries)
                    {
                        sb.AppendLine(JsonUtility.ToJson(e));
                    }

                    var content = sb.ToString();
                    if (File.Exists(LogPath))
                    {
                        var fi = new FileInfo(LogPath);
                        if (fi.Length + Encoding.UTF8.GetByteCount(content) > MaxLogFileSizeBytes)
                        {
                            var archive = Path.Combine(DataRoot, $"autopilot_logs_{DateTime.UtcNow:yyyyMMdd_HHmmss}.jsonl");
                            File.Move(LogPath, archive);
                        }
                    }

                    File.AppendAllText(LogPath, content);
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"AutopilotStorage.AppendLogs: {ex}");
            }
        }
    }
}
