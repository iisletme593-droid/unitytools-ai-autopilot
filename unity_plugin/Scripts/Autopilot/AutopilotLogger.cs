using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace Autopilot
{
    [Serializable]
    public class AutopilotLogEntry
    {
        public string timestamp;
        public string level;
        public string message;
        public string source;
        public long frame;
    }

    public enum LogLevel { Trace = 0, Debug = 1, Info = 2, Warn = 3, Error = 4, Fatal = 5 }

    public static class AutopilotLogger
    {
        private static readonly ConcurrentQueue<AutopilotLogEntry> _queue = new ConcurrentQueue<AutopilotLogEntry>();
        private static readonly int _batchSize;
        private static readonly int _flushIntervalMs;
        private static readonly LogLevel _minLevel;
        private static readonly Timer _flushTimer;
        private static readonly CancellationTokenSource _cts = new CancellationTokenSource();

        static AutopilotLogger()
        {
            int cpu = Math.Max(1, Environment.ProcessorCount);
            _batchSize = Math.Max(50, cpu * 16);
            _flushIntervalMs = 2000; // 2s
            _minLevel = LogLevel.Info;

            // Tune storage max size via AutopilotStorage property if needed
            AutopilotStorage.MaxLogFileSizeBytes = 10 * 1024 * 1024; // 10 MB

            _flushTimer = new Timer(_ => FlushInternal(), null, _flushIntervalMs, _flushIntervalMs);
            try { Application.quitting += OnApplicationQuitting; } catch { }
        }

        private static void OnApplicationQuitting()
        {
            try
            {
                _cts.Cancel();
                _flushTimer?.Change(Timeout.Infinite, Timeout.Infinite);
                FlushInternal();
            }
            catch { }
        }

        public static void Log(string message, string level = "INFO")
        {
            if (!Enum.TryParse<LogLevel>(level, true, out var lvl))
                lvl = LogLevel.Info;
            Log(message, lvl);
        }

        public static void Log(string message, LogLevel level)
        {
            if (level < _minLevel) return;
            var entry = new AutopilotLogEntry
            {
                timestamp = DateTime.UtcNow.ToString("o"),
                level = level.ToString().ToUpperInvariant(),
                message = message,
                source = "Autopilot",
                frame = Time.frameCount
            };

            try
            {
                // Keep quick visibility on console for warnings/errors
                if (level >= LogLevel.Warn)
                    Debug.LogWarning($"[Autopilot/{entry.level}] {message}");
                else
                    Debug.Log($"[Autopilot/{entry.level}] {message}");

                _queue.Enqueue(entry);

                if (_queue.Count >= _batchSize)
                    Task.Run(() => FlushInternal());
            }
            catch (Exception ex)
            {
                Debug.LogError($"AutopilotLogger.Log: {ex}");
            }
        }

        public static void Flush()
        {
            FlushInternal();
        }

        private static void FlushInternal()
        {
            try
            {
                if (_queue.IsEmpty) return;

                var batch = new List<AutopilotLogEntry>();
                while (batch.Count < _batchSize && _queue.TryDequeue(out var e))
                    batch.Add(e);

                if (batch.Count > 0)
                    AutopilotStorage.AppendLogs(batch);
            }
            catch (Exception ex)
            {
                Debug.LogError($"AutopilotLogger.FlushInternal: {ex}");
            }
        }
    }
}
