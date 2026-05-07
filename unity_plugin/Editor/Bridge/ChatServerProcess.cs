// Starts and monitors the Python chat server without opening a terminal window.

using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Debug = UnityEngine.Debug;
namespace UnityTools.Bridge
{
    [InitializeOnLoad]
    internal static class ChatServerProcessLifecycle
    {
        static ChatServerProcessLifecycle()
        {
            EditorApplication.quitting += ChatServerProcess.StopKnownProcesses;
        }
    }

    public static class ChatServerProcess
    {
        private const string PrefCommandKey = "UnityTools.Chat.Command";
        private const string PrefArgsKey = "UnityTools.Chat.Args";
        private static readonly string PidPath = Path.Combine(Path.GetTempPath(), "unitytools-editor-chat.pid");

        private static Process _process;
        private static string _lastLogPath;

        public static bool IsOwnedProcessRunning => _process != null && !_process.HasExited;
        public static string LastLogPath => _lastLogPath;

        public static string Command
        {
            get => EditorPrefs.GetString(PrefCommandKey, ResolveDefaultCommand());
            set => EditorPrefs.SetString(PrefCommandKey, value);
        }

        public static string Arguments
        {
            get
            {
                string value = EditorPrefs.GetString(PrefArgsKey, ResolveDefaultArguments());
                if (value.Contains("--no-dual-agent"))
                {
                    value = ResolveDefaultArguments();
                    EditorPrefs.SetString(PrefArgsKey, value);
                }
                return value;
            }
            set => EditorPrefs.SetString(PrefArgsKey, value);
        }

        public static bool IsPortOpen(string host, int port, int timeoutMs = 250)
        {
            try
            {
                using (var tcp = new TcpClient())
                {
                    var async = tcp.BeginConnect(host, port, null, null);
                    bool ok = async.AsyncWaitHandle.WaitOne(timeoutMs);
                    if (!ok) return false;
                    tcp.EndConnect(async);
                    return tcp.Connected;
                }
            }
            catch
            {
                return false;
            }
        }

        public static bool EnsureRunning(string host, int port, string workingDirectory)
        {
            if (IsPortOpen(host, port)) return true;
            if (IsOwnedProcessRunning) return false;
            StopKnownProcesses();
            StartHidden(workingDirectory);
            return true;
        }

        /// <summary>
        /// Process'i başlat ve `timeoutMs` içinde port açılana kadar bekle.
        /// Açılmazsa Editor Console'a hata mesajı bas.
        /// </summary>
        public static bool EnsureRunningAndWait(string host, int port, string workingDirectory, int timeoutMs = 8000)
        {
            if (IsPortOpen(host, port)) return true;
            if (!IsOwnedProcessRunning)
            {
                StopKnownProcesses();
                StartHidden(workingDirectory);
            }
            // Port'u poll et
            int elapsed = 0;
            const int step = 200;
            while (elapsed < timeoutMs)
            {
                if (IsPortOpen(host, port, 100)) return true;
                if (_process != null && _process.HasExited)
                {
                    Debug.LogError(
                        $"[UnityTools] chat-server crashed during startup (exit {_process.ExitCode}). " +
                        $"Log: {_lastLogPath}"
                    );
                    return false;
                }
                System.Threading.Thread.Sleep(step);
                elapsed += step;
            }
            Debug.LogError(
                $"[UnityTools] chat-server did not open port {host}:{port} within {timeoutMs}ms. " +
                $"Log: {_lastLogPath}"
            );
            return false;
        }

        public static void StartHidden(string workingDirectory)
        {
            string command = Command;
            string args = Arguments;
            _lastLogPath = Path.Combine(Path.GetTempPath(), "unitytools-editor-chat.log");

            var psi = new ProcessStartInfo
            {
                FileName = command,
                Arguments = args,
                WorkingDirectory = workingDirectory,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };

            try
            {
                _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
                _process.OutputDataReceived += (_, e) => AppendLog(e.Data);
                _process.ErrorDataReceived += (_, e) => AppendLog(e.Data);
                _process.Exited += (_, __) => AppendLog($"[UnityTools] chat-server exited with code {_process.ExitCode}");
                _process.Start();
                WritePidFile(_process.Id);
                _process.BeginOutputReadLine();
                _process.BeginErrorReadLine();
                AppendLog($"[UnityTools] started: {command} {args}");
            }
            catch (Exception ex)
            {
                _process = null;
                AppendLog($"[UnityTools] failed to start chat-server: {ex}");
                Debug.LogError($"[UnityTools] Could not start embedded chat server: {ex.Message}");
            }
        }

        public static void StopOwnedProcess()
        {
            if (!IsOwnedProcessRunning)
            {
                StopKnownProcesses();
                return;
            }
            try
            {
                _process.Kill();
                _process.Dispose();
            }
            catch { }
            finally
            {
                _process = null;
                DeletePidFile();
            }
        }

        public static void StopKnownProcesses()
        {
            var ids = ReadPidFile();
            foreach (int id in ids)
            {
                try
                {
                    var p = Process.GetProcessById(id);
                    if (!p.HasExited) p.Kill();
                    p.Dispose();
                }
                catch { }
            }
            DeletePidFile();
        }

        private static void AppendLog(string line)
        {
            if (string.IsNullOrEmpty(line)) return;
            try
            {
                File.AppendAllText(_lastLogPath ?? Path.Combine(Path.GetTempPath(), "unitytools-editor-chat.log"), line + Environment.NewLine);
            }
            catch { }
        }

        private static void WritePidFile(int pid)
        {
            try
            {
                File.WriteAllLines(PidPath, new[] { pid.ToString() });
            }
            catch { }
        }

        private static int[] ReadPidFile()
        {
            try
            {
                if (!File.Exists(PidPath)) return Array.Empty<int>();
                return File.ReadAllLines(PidPath)
                    .Select(line => int.TryParse(line.Trim(), out int id) ? id : -1)
                    .Where(id => id > 0)
                    .Distinct()
                    .ToArray();
            }
            catch
            {
                return Array.Empty<int>();
            }
        }

        private static void DeletePidFile()
        {
            try
            {
                if (File.Exists(PidPath)) File.Delete(PidPath);
            }
            catch { }
        }

        private static string ResolveDefaultCommand()
        {
#if UNITY_EDITOR_WIN
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string programs = Path.Combine(localAppData, "Programs", "Python");
            if (Directory.Exists(programs))
            {
                foreach (string candidate in Directory.GetFiles(programs, "python.exe", SearchOption.AllDirectories))
                {
                    return candidate;
                }
            }
            return "python";
#else
            return "python";
#endif
        }

        private static string ResolveDefaultArguments()
        {
            return "-m unitytools.cli.entry chat-server --use-dual-agent --engine unity";
        }
    }
}
