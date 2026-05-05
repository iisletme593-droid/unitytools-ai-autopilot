// Starts and monitors the Python chat server without opening a terminal window.

using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using UnityEditor;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace UnityTools.Bridge
{
    public static class ChatServerProcess
    {
        private const string PrefCommandKey = "UnityTools.Chat.Command";
        private const string PrefArgsKey = "UnityTools.Chat.Args";

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
            get => EditorPrefs.GetString(PrefArgsKey, "chat-server");
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
            StartHidden(workingDirectory);
            return true;
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
            if (!IsOwnedProcessRunning) return;
            try
            {
                _process.Kill();
                _process.Dispose();
            }
            catch { }
            finally
            {
                _process = null;
            }
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

        private static string ResolveDefaultCommand()
        {
#if UNITY_EDITOR_WIN
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string programs = Path.Combine(localAppData, "Programs", "Python");
            if (Directory.Exists(programs))
            {
                foreach (string candidate in Directory.GetFiles(programs, "unitytools.exe", SearchOption.AllDirectories))
                {
                    if (candidate.Contains("Scripts")) return candidate;
                }
            }
            return "unitytools";
#else
            return "unitytools";
#endif
        }
    }
}
