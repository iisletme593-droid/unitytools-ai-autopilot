using System;
using UnityEngine;

namespace Autopilot
{
    /// <summary>
    /// Static CLI entrypoint for headless/autopilot runs.
    /// Usage example (Windows):
    /// Unity.exe -batchmode -projectPath "C:/path/to/UnityProject" -executeMethod Autopilot.AutopilotCLI.RunAutopilot -quit
    /// </summary>
    public static class AutopilotCLI
    {
        public static void RunAutopilot()
        {
            Debug.Log("AutopilotCLI: invoked via -executeMethod (blocking)");
            try
            {
                var tasks = AutopilotStorage.LoadTasks();
                if (tasks == null || tasks.tasks == null || tasks.tasks.Length == 0)
                {
                    AutopilotLogger.Log("No tasks found for CLI run. Creating Unity reboot defaults.", "WARN");
                    tasks = UnityAutopilotTasks.CreateDefaultTaskList();
                    AutopilotStorage.SaveTasks(tasks);
                }

                AutopilotProcessor.RunTasksBlocking(tasks.tasks);

                // Capture screenshot for vision comparison pipeline.
                AutopilotLogger.Log("AutopilotCLI: capturing scene screenshot...", "INFO");
                AutopilotScreenshot.CaptureAfterBuild();

                AutopilotLogger.Flush();
                AutopilotLogger.Log("AutopilotCLI: finished (blocking)", "INFO");
            }
            catch (Exception ex)
            {
                AutopilotLogger.Log("AutopilotCLI error: " + ex, "ERROR");
            }
        }
    }
}
