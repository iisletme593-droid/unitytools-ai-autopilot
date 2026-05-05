using System.Collections.Generic;
using UnityEngine;

namespace Autopilot
{
    /// <summary>
    /// Simple in-memory priority queue for AutopilotTask (lower priority value = higher priority).
    /// </summary>
    public class AutopilotQueue
    {
        private readonly List<AutopilotTask> queue = new List<AutopilotTask>();

        public void Enqueue(AutopilotTask task)
        {
            queue.Add(task);
            queue.Sort((a, b) => a.priority.CompareTo(b.priority));
        }

        public AutopilotTask Dequeue()
        {
            if (queue.Count == 0) return null;
            var t = queue[0];
            queue.RemoveAt(0);
            return t;
        }

        public int Count => queue.Count;
        public AutopilotTask[] ToArray() => queue.ToArray();
    }
}
