// TCP client used by the embedded Unity Editor chat window.

using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace UnityTools.Bridge
{
    public class ChatClient
    {
        public string Host { get; }
        public int Port { get; }
        public bool IsConnected => _tcp != null && _tcp.Connected;

        public readonly ConcurrentQueue<JObject> InboundMessages = new ConcurrentQueue<JObject>();

        private TcpClient _tcp;
        private NetworkStream _stream;
        private Thread _readThread;
        private volatile bool _running;

        public event Action OnDisconnected;
        public event Action<Exception> OnError;

        public ChatClient(string host = "127.0.0.1", int port = 7778)
        {
            Host = host;
            Port = port;
        }

        public bool Connect(int timeoutMs = 2000)
        {
            try
            {
                _tcp = new TcpClient();
                var asyncResult = _tcp.BeginConnect(Host, Port, null, null);
                bool ok = asyncResult.AsyncWaitHandle.WaitOne(timeoutMs);
                if (!ok || !_tcp.Connected)
                {
                    _tcp.Close();
                    _tcp = null;
                    return false;
                }

                _tcp.EndConnect(asyncResult);
                _stream = _tcp.GetStream();
                _running = true;

                _readThread = new Thread(ReadLoop) { IsBackground = true, Name = "UnityToolsChatClient" };
                _readThread.Start();
                return true;
            }
            catch (Exception e)
            {
                OnError?.Invoke(e);
                _tcp = null;
                _stream = null;
                return false;
            }
        }

        public void Disconnect()
        {
            _running = false;
            try { _stream?.Close(); } catch { }
            try { _tcp?.Close(); } catch { }
            _stream = null;
            _tcp = null;
        }

        public void Send(JObject message)
        {
            if (!IsConnected) throw new InvalidOperationException("Not connected");
            byte[] bytes = Encoding.UTF8.GetBytes(message.ToString(Newtonsoft.Json.Formatting.None) + "\n");
            try
            {
                _stream.Write(bytes, 0, bytes.Length);
                _stream.Flush();
            }
            catch (Exception e)
            {
                OnError?.Invoke(e);
                Disconnect();
                OnDisconnected?.Invoke();
            }
        }

        public void SendUserMessage(string content)
        {
            Send(new JObject
            {
                ["type"] = "user_message",
                ["content"] = content,
            });
        }

        public void SendReset()
        {
            Send(new JObject { ["type"] = "reset" });
        }

        public void SendPing()
        {
            Send(new JObject { ["type"] = "ping" });
        }

        private void ReadLoop()
        {
            byte[] buffer = new byte[8192];
            var pending = new MemoryStream();
            try
            {
                while (_running && _stream != null)
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
                            JObject obj = JObject.Parse(line);
                            InboundMessages.Enqueue(obj);
                        }
                        catch (Exception e)
                        {
                            Debug.LogWarning($"[UnityTools.ChatClient] Parse error: {e.Message}");
                        }
                    }

                    pending.Position = 0;
                    pending.SetLength(0);
                    if (start < data.Length) pending.Write(data, start, data.Length - start);
                }
            }
            catch (IOException) { }
            catch (Exception e) { OnError?.Invoke(e); }
            finally
            {
                _running = false;
                OnDisconnected?.Invoke();
            }
        }
    }
}
