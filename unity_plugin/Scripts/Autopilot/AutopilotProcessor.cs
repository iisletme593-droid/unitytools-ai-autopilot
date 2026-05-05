using System;
using UnityEngine;

namespace Autopilot
{
    public static class AutopilotProcessor
    {
        public static void RunTasksBlocking(AutopilotTask[] tasks)
        {
            if (tasks == null || tasks.Length == 0)
            {
                AutopilotLogger.Log("No tasks to process (blocking)", "WARN");
                return;
            }

            foreach (var t in tasks)
            {
                try
                {
                    // Tamamlanmis veya birakilan gorevleri atla
                    if (t.status == "Completed" || t.status == "Abandoned" || t.status == "Skipped")
                    {
                        AutopilotLogger.Log($"[Blocking] Skip {t.status} task {t.id}: {t.title}", "INFO");
                        continue;
                    }

                    // Max retry: 3 denemeden sonra birak
                    if (t.status == "Failed" && t.retryCount >= 3)
                    {
                        t.status    = "Abandoned";
                        t.statusReason = $"Max {t.retryCount} retries reached. Skipping permanently.";
                        t.updatedAt = DateTime.UtcNow.ToString("o");
                        AutopilotStorage.SaveTasks(new AutopilotTaskList { tasks = tasks });
                        AutopilotLogger.Log($"[Blocking] Abandoned task {t.id} after {t.retryCount} retries", "WARN");
                        continue;
                    }

                    // Dispatch task to appropriate processor based on engine
                    string engine = (t.engine ?? "unity").Trim().ToLowerInvariant();
                    if (!IsEngineSupported(engine))
                    {
                        t.status = "Skipped";
                        t.statusReason = $"Unsupported engine '{t.engine}'. Supported: unity, blender, hf, validate.";
                        t.updatedAt = DateTime.UtcNow.ToString("o");
                        AutopilotLogger.Log($"[Blocking] Skipped task {t.id} with unsupported engine '{t.engine}'", "WARN");
                        AutopilotStorage.SaveTasks(new AutopilotTaskList { tasks = tasks });
                        continue;
                    }

                    AutopilotLogger.Log($"[Blocking] Starting task {t.id} (engine={engine}, retry={t.retryCount}): {t.title}", "INFO");
                    t.status = "InProgress";
                    t.statusReason = "";
                    t.updatedAt = DateTime.UtcNow.ToString("o");
                    AutopilotStorage.SaveTasks(new AutopilotTaskList { tasks = tasks });

                    bool success;
                    string reason;

                    // Route to appropriate executor by engine
                    if (engine == "unity")
                    {
                        success = UnityAutopilotTasks.Execute(t, out reason);
                    }
                    else if (engine == "blender")
                    {
                        success = BlenderTaskProcessor.Execute(t, out reason);
                    }
                    else if (engine == "hf")
                    {
                        success = HfTaskProcessor.Execute(t, out reason);
                    }
                    else if (engine == "validate")
                    {
                        success = ValidateTaskProcessor.Execute(t, out reason);
                    }
                    else
                    {
                        success = false;
                        reason = $"No executor for engine '{engine}'.";
                    }

                    if (!success) t.retryCount++;
                    t.status = success ? "Completed" : "Failed";
                    t.statusReason = reason;
                    t.updatedAt = DateTime.UtcNow.ToString("o");

                    AutopilotStorage.SaveTasks(new AutopilotTaskList { tasks = tasks });
                    AutopilotLogger.Log($"[Blocking] {t.status} task {t.id}: {reason}", success ? "INFO" : "ERROR");
                }
                catch (Exception ex)
                {
                    t.status = "Failed";
                    t.statusReason = ex.Message;
                    t.updatedAt = DateTime.UtcNow.ToString("o");
                    AutopilotStorage.SaveTasks(new AutopilotTaskList { tasks = tasks });
                    AutopilotLogger.Log($"[Blocking] Task {t.id} error: {ex}", "ERROR");
                }
            }
            AutopilotLogger.Log("[Blocking] All tasks processed", "INFO");
        }

        private static bool IsEngineSupported(string engine)
        {
            return engine == "unity" || engine == "blender" || engine == "hf" || engine == "validate";
        }
    }
}
