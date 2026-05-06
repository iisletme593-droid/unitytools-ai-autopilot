// TCP listener used by the Python UnityBridge.
// Protocol: newline-delimited JSON. One request line, one response line.

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
namespace UnityTools.Bridge
{
    [InitializeOnLoad]
    public static class BridgeServer
    {
        private const int DefaultPort = 7777;
        private const string PrefsKey = "UnityToolsBridgeEnabled";

        private static TcpListener _listener;
        private static Thread _acceptThread;
        private static readonly List<ClientConnection> _clients = new List<ClientConnection>();
        private static readonly ConcurrentQueue<PendingRequest> _mainThreadQueue = new ConcurrentQueue<PendingRequest>();

        public static int Port { get; private set; } = DefaultPort;
        public static bool IsRunning { get; private set; }

        static BridgeServer()
        {
            EditorApplication.update += OnEditorUpdate;
            AssemblyReloadEvents.beforeAssemblyReload += Stop;
            EditorApplication.quitting += Stop;
            if (EditorPrefs.GetBool(PrefsKey, true))
            {
                Start();
            }
        }

        public static void Start(int port = -1)
        {
            if (IsRunning) return;
            if (port <= 0) port = ResolveDefaultPort();
            Exception lastError = null;
            for (int candidate = port; candidate < port + 24; candidate++)
            {
                try
                {
                    Port = candidate;
                    _listener = new TcpListener(IPAddress.Loopback, candidate);
                    _listener.Start();
                    IsRunning = true;

                    _acceptThread = new Thread(AcceptLoop) { IsBackground = true, Name = "UnityToolsBridgeAccept" };
                    _acceptThread.Start();

                    if (candidate == port)
                        Debug.Log($"[UnityTools] BridgeServer listening on port {candidate}.");
                    else
                        Debug.LogWarning($"[UnityTools] BridgeServer preferred port {port} was busy; listening on fallback port {candidate}.");
                    return;
                }
                catch (Exception e)
                {
                    lastError = e;
                    try { _listener?.Stop(); } catch { }
                    _listener = null;
                    IsRunning = false;
                }
            }
            Debug.LogWarning($"[UnityTools] BridgeServer could not start on ports {port}-{port + 23}: {lastError?.Message}");
        }

        private static int ResolveDefaultPort()
        {
            string envPort = Environment.GetEnvironmentVariable("UNITY_BRIDGE_PORT");
            if (int.TryParse(envPort, out int fromEnv) && fromEnv > 0) return fromEnv;

            try
            {
                string projectRoot = Directory.GetParent(Application.dataPath)?.FullName ?? "";
                string envPath = Path.Combine(projectRoot, ".env");
                if (File.Exists(envPath))
                {
                    foreach (string raw in File.ReadAllLines(envPath))
                    {
                        string line = raw.Trim();
                        if (line.StartsWith("#") || !line.StartsWith("UNITY_BRIDGE_PORT=", StringComparison.Ordinal))
                            continue;
                        string value = line.Substring("UNITY_BRIDGE_PORT=".Length).Trim();
                        if (int.TryParse(value, out int fromFile) && fromFile > 0) return fromFile;
                    }
                }
            }
            catch { }

            return DefaultPort;
        }

        public static void Stop()
        {
            if (!IsRunning) return;
            IsRunning = false;
            try { _listener?.Stop(); } catch { }
            lock (_clients)
            {
                foreach (var c in _clients) c.Close();
                _clients.Clear();
            }
            Debug.Log("[UnityTools] BridgeServer stopped.");
        }

        private static void AcceptLoop()
        {
            while (IsRunning)
            {
                try
                {
                    TcpClient tcp = _listener.AcceptTcpClient();
                    var conn = new ClientConnection(tcp, OnRequestReceived);
                    lock (_clients) _clients.Add(conn);
                    conn.Start();
                }
                catch (SocketException) { }
                catch (ThreadAbortException) { break; }
                catch (ObjectDisposedException) { break; }
                catch (Exception e)
                {
                    if (IsRunning) Debug.LogWarning($"[UnityTools] Accept warning: {e.Message}");
                }
            }
        }

        private static void OnRequestReceived(ClientConnection client, JObject request)
        {
            _mainThreadQueue.Enqueue(new PendingRequest { Client = client, Request = request });
        }

        private static void OnEditorUpdate()
        {
            while (_mainThreadQueue.TryDequeue(out var pending))
            {
                ProcessRequest(pending.Client, pending.Request);
            }

            lock (_clients)
            {
                _clients.RemoveAll(c => !c.IsAlive);
            }
        }

        private static void ProcessRequest(ClientConnection client, JObject request)
        {
            string id = request["id"]?.ToString() ?? "";
            string method = request["method"]?.ToString() ?? "";
            JObject parameters = request["params"] as JObject ?? new JObject();
            JObject response = new JObject { ["id"] = id };

            try
            {
                object result = CommandHandlers.Dispatch(method, parameters);
                response["result"] = result == null ? JValue.CreateNull() : JToken.FromObject(result);
            }
            catch (Exception e)
            {
                response["error"] = new JObject
                {
                    ["code"] = 1,
                    ["message"] = e.Message,
                };
                Debug.LogError($"[UnityTools] {method} error: {e}");
            }

            client.Send(response.ToString(Formatting.None));
        }

        private struct PendingRequest
        {
            public ClientConnection Client;
            public JObject Request;
        }
    }

    internal class ClientConnection
    {
        private readonly TcpClient _tcp;
        private readonly NetworkStream _stream;
        private readonly Action<ClientConnection, JObject> _onRequest;
        private Thread _readThread;
        public bool IsAlive { get; private set; }

        public ClientConnection(TcpClient tcp, Action<ClientConnection, JObject> onRequest)
        {
            _tcp = tcp;
            _stream = tcp.GetStream();
            _onRequest = onRequest;
            IsAlive = true;
        }

        public void Start()
        {
            _readThread = new Thread(ReadLoop) { IsBackground = true, Name = "UnityToolsBridgeClient" };
            _readThread.Start();
        }

        private void ReadLoop()
        {
            var buffer = new byte[8192];
            var pending = new MemoryStream();
            try
            {
                while (IsAlive)
                {
                    int n = _stream.Read(buffer, 0, buffer.Length);
                    if (n <= 0) break;
                    pending.Write(buffer, 0, n);

                    byte[] data = pending.ToArray();
                    int start = 0;
                    for (int i = 0; i < data.Length; i++)
                    {
                        if (data[i] != (byte)'\n') continue;
                        string line = Encoding.UTF8.GetString(data, start, i - start);
                        start = i + 1;
                        if (string.IsNullOrWhiteSpace(line)) continue;
                        try
                        {
                            JObject req = JObject.Parse(line);
                            _onRequest(this, req);
                        }
                        catch (Exception e)
                        {
                            Debug.LogWarning($"[UnityTools] Invalid JSON: {e.Message}");
                        }
                    }

                    pending = new MemoryStream();
                    if (start < data.Length) pending.Write(data, start, data.Length - start);
                }
            }
            catch (IOException) { }
            catch (Exception e) { Debug.LogError($"[UnityTools] Read error: {e.Message}"); }
            finally { Close(); }
        }

        public void Send(string jsonLine)
        {
            try
            {
                byte[] bytes = Encoding.UTF8.GetBytes(jsonLine + "\n");
                _stream.Write(bytes, 0, bytes.Length);
                _stream.Flush();
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[UnityTools] Send error: {e.Message}");
                Close();
            }
        }

        public void Close()
        {
            IsAlive = false;
            try { _stream?.Close(); } catch { }
            try { _tcp?.Close(); } catch { }
        }
    }
}
