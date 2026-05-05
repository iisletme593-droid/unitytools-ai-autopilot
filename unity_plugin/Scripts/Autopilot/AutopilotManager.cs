using System.Collections;
using UnityEngine;

namespace Autopilot
{
    /// <summary>
    /// Runtime-visible autopilot manager. In editor/batchmode it can execute Unity tasks;
    /// in player builds it remains a lightweight status/log runner.
    /// </summary>
    public class AutopilotManager : MonoBehaviour
    {
        [Tooltip("Run autopilot automatically when scene starts.")]
        public bool runOnStart = false;

        [Tooltip("Delay in seconds between finishing a task and starting the next.")]
        public float taskProcessingDelay = 0.25f;

        private AutopilotTaskList tasks;

        void Start()
        {
            if (runOnStart)
                StartCoroutine(RunCoroutine());
        }

        public void StartAutopilotCycle()
        {
            StartCoroutine(RunCoroutine());
        }

        private IEnumerator RunCoroutine()
        {
            AutopilotLogger.Log("AutopilotManager: loading Unity-only tasks", "INFO");
            tasks = AutopilotStorage.LoadTasks();

            if (tasks == null || tasks.tasks == null || tasks.tasks.Length == 0)
            {
                AutopilotLogger.Log("No tasks found - creating Unity reboot defaults", "WARN");
                tasks = UnityAutopilotTasks.CreateDefaultTaskList();
                AutopilotStorage.SaveTasks(tasks);
            }

            foreach (AutopilotTask task in tasks.tasks)
            {
                // Tamamlanmis / birakilan gorevleri atla — dongu olusturma
                if (task.status == "Completed" || task.status == "Abandoned" || task.status == "Skipped")
                {
                    AutopilotLogger.Log($"Runtime skip {task.status} task {task.id}", "INFO");
                    continue;
                }

                // Max 3 deneme
                if (task.status == "Failed" && task.retryCount >= 3)
                {
                    task.status    = "Abandoned";
                    task.statusReason = "Max retries reached.";
                    task.updatedAt = System.DateTime.UtcNow.ToString("o");
                    AutopilotStorage.SaveTasks(tasks);
                    continue;
                }

                if (!string.Equals(task.engine, "unity", System.StringComparison.OrdinalIgnoreCase))
                {
                    task.status = "Skipped";
                    task.statusReason = "Non-Unity task ignored by Unity autopilot.";
                    AutopilotStorage.SaveTasks(tasks);
                    continue;
                }

                task.status = "InProgress";
                task.updatedAt = System.DateTime.UtcNow.ToString("o");
                AutopilotStorage.SaveTasks(tasks);

                bool success = UnityAutopilotTasks.Execute(task, out string reason);
                if (!success) task.retryCount++;
                task.status = success ? "Completed" : "Failed";
                task.statusReason = reason;
                task.updatedAt = System.DateTime.UtcNow.ToString("o");
                AutopilotStorage.SaveTasks(tasks);

                AutopilotLogger.Log($"Runtime task {task.id} {task.status}: {reason}", success ? "INFO" : "ERROR");
                yield return new WaitForSeconds(taskProcessingDelay);
            }

            AutopilotLogger.Flush();
            AutopilotLogger.Log("AutopilotManager: Unity task cycle finished", "INFO");
        }
    }
}
