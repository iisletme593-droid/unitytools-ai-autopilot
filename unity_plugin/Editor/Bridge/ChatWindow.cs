// Native-feeling Unity Editor AI panel for UnityTools Autopilot.
// The panel starts the Python chat core in the background and connects automatically.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Debug = UnityEngine.Debug;
namespace UnityTools.Bridge
{
    public class ChatWindow : EditorWindow
    {
        [MenuItem("Tools/UnityTools/Open AI Autopilot", false, 0)]
        [MenuItem("Window/UnityTools AI/Autopilot Chat", false, 0)]
        public static void Open()
        {
            var win = GetWindow<ChatWindow>("UnityTools AI");
            win.minSize = new Vector2(420, 520);
            win.Show();
        }
        [MenuItem("Tools/UnityTools/Bridge Status", false, 100)]
        public static void OpenBridgeStatus()
        {
            BridgeStatusWindow.Open();
        }
        [MenuItem("Tools/UnityTools/Start Embedded Chat Core", false, 200)]
        public static void StartEmbeddedCore()
        {
            ChatServerProcess.EnsureRunning("127.0.0.1", 7778, ProjectRoot);
        }
        [MenuItem("Tools/UnityTools/Stop Embedded Chat Core", false, 201)]
        public static void StopEmbeddedCore()
        {
            ChatServerProcess.StopOwnedProcess();
        }

        private static string ProjectRoot => Path.GetDirectoryName(Application.dataPath);

        private ChatClient _client;
        private string _input = "";
        private readonly List<SelectedImage> _selectedImages = new List<SelectedImage>();
        private Vector2 _scrollPos;
        private readonly List<ChatItem> _items = new List<ChatItem>();
        private bool _serverThinking;
        private bool _autoConnectEnabled = true;
        private double _nextConnectAttempt;
        private string _serverHost = "127.0.0.1";
        private int _serverPort = 7778;
        private string _providerLabel = "Local core";
        private string _agentMode = "single";
        private string _masterModel = "";
        private string _workerModel = "";
        private readonly List<SceneChoice> _sceneChoices = new List<SceneChoice>();
        private string[] _sceneLabels = new[] { "Sahneler yukleniyor..." };
        private int _selectedSceneIndex;
        private double _nextSceneRefresh;

        private const string PrefHostKey = "UnityTools.Chat.Host";
        private const string PrefPortKey = "UnityTools.Chat.Port";
        private const string PrefAutoConnectKey = "UnityTools.Chat.AutoConnect";

        private GUIStyle _headerStyle;
        private GUIStyle _subtleStyle;
        private GUIStyle _bubbleUserStyle;
        private GUIStyle _bubbleAiStyle;
        private GUIStyle _toolStyle;
        private GUIStyle _errorStyle;
        private GUIStyle _chipStyle;
        private bool _stylesReady;

        private void OnEnable()
        {
            _serverHost = EditorPrefs.GetString(PrefHostKey, "127.0.0.1");
            _serverPort = EditorPrefs.GetInt(PrefPortKey, 7778);
            _autoConnectEnabled = EditorPrefs.GetBool(PrefAutoConnectKey, true);
            _providerLabel = ReadEnvValue("UNITYTOOLS_PROVIDER", "ollama") + " / " + ReadEnvValue("OLLAMA_MODEL", "gemma4:latest");
            EditorApplication.update += OnEditorUpdate;
            RefreshScenes();
            AddSystemMessage("UnityTools AI hazir. Gomulu core otomatik baslar.");
            _nextConnectAttempt = EditorApplication.timeSinceStartup + 0.25f;
        }

        private void OnDisable()
        {
            EditorApplication.update -= OnEditorUpdate;
            _client?.Disconnect();
        }

        private void OnEditorUpdate()
        {
            if (_autoConnectEnabled && !IsConnected() && EditorApplication.timeSinceStartup >= _nextConnectAttempt)
            {
                _nextConnectAttempt = EditorApplication.timeSinceStartup + 2.5f;
                EnsureCoreAndConnect(silent: true);
            }
            if (_client == null) return;
            bool changed = false;
            while (_client.InboundMessages.TryDequeue(out var msg))
            {
                HandleInbound(msg);
                changed = true;
            }
            if (changed) Repaint();
        }

        private void HandleInbound(JObject msg)
        {
            string type = msg["type"]?.ToString();
            switch (type)
            {
                case "thinking":
                    _serverThinking = true;
                    break;
                case "tool_call":
                    _items.Add(new ChatItem
                    {
                        Kind = ItemKind.ToolCall,
                        Text = $"tool -> {msg["tool"]}({CompactParams(msg["input"] as JObject)})",
                    });
                    break;
                case "tool_result":
                    bool ok = msg["ok"]?.ToObject<bool>() ?? true;
                    string resultText = ok
                        ? $"tool <- OK {msg["tool"]}"
                        : $"tool <- ERR {msg["tool"]}: {msg["error"]}";
                    _items.Add(new ChatItem { Kind = ItemKind.ToolResult, Text = resultText, Ok = ok });
                    break;
                case "assistant_text":
                    _serverThinking = false;
                    _items.Add(new ChatItem
                    {
                        Kind = ItemKind.Assistant,
                        Text = msg["content"]?.ToString() ?? "",
                    });
                    break;
                case "assistant_done":
                    _serverThinking = false;
                    break;
                case "master_thinking":
                    _items.Add(new ChatItem
                    {
                        Kind = ItemKind.System,
                        Text = "🧠 Master: " + (msg["message"]?.ToString() ?? "Planning..."),
                    });
                    break;
                case "worker_executing":
                    _items.Add(new ChatItem
                    {
                        Kind = ItemKind.System,
                        Text = "⚙️ Worker: " + (msg["message"]?.ToString() ?? "Executing..."),
                    });
                    break;
                case "reader_brief":
                    _items.Add(new ChatItem
                    {
                        Kind = ItemKind.System,
                        Text = "Reader: " + (msg["brief"]?.ToString() ?? ""),
                    });
                    break;
                case "dual_agent_plan":
                    var plan = msg["plan"] as JObject;
                    if (plan != null)
                    {
                        string taskDesc = plan["task"]?.ToString() ?? "Unknown task";
                        int stepCount = (plan["steps"] as JArray)?.Count ?? 0;
                        _items.Add(new ChatItem
                        {
                            Kind = ItemKind.System,
                            Text = $"📋 Master Plan: {taskDesc} ({stepCount} steps)",
                        });
                    }
                    break;
                case "dual_agent_reports":
                    var reports = msg["reports"] as JArray;
                    if (reports != null && reports.Count > 0)
                    {
                        _items.Add(new ChatItem
                        {
                            Kind = ItemKind.System,
                            Text = $"✓ Worker completed {reports.Count} step(s)",
                        });
                    }
                    break;
                case "error":
                    _serverThinking = false;
                    _items.Add(new ChatItem
                    {
                        Kind = ItemKind.Error,
                        Text = "Error: " + (msg["message"]?.ToString() ?? "?"),
                    });
                    break;
                case "pong":
                    _items.Add(new ChatItem { Kind = ItemKind.System, Text = "Core responded." });
                    break;
                case "hello":
                    int toolsLoaded = msg["tools_loaded"]?.ToObject<int>() ?? 0;
                    string provider = msg["provider"]?.ToString() ?? "?";
                    string model = msg["model"]?.ToString() ?? "?";
                    _agentMode = msg["mode"]?.ToString() ?? "single-agent";
                    string readerModel = msg["reader_model"]?.ToString() ?? "";
                    _masterModel = msg["master_model"]?.ToString() ?? "";
                    _workerModel = msg["worker_model"]?.ToString() ?? "";
                    
                    bool isDualMode = _agentMode.StartsWith("dual-agent", StringComparison.OrdinalIgnoreCase);
                    string modeInfo = isDualMode
                        ? $"DUAL-AGENT: Reader={readerModel}, Master={_masterModel}, Worker={_workerModel}"
                        : $"Model: {model}";
                    
                    _items.Add(new ChatItem
                    {
                        Kind = ItemKind.System,
                        Text = $"Connected. Provider: {provider}, {modeInfo}, {toolsLoaded} tools loaded.",
                    });
                    
                    if (isDualMode)
                    {
                        _items.Add(new ChatItem
                        {
                            Kind = ItemKind.System,
                            Text = "Dual-agent mode: Master plans (30-60s), Worker executes. Good planning = better results!",
                        });
                    }
                    
                    if (toolsLoaded == 0)
                    {
                        _items.Add(new ChatItem
                        {
                            Kind = ItemKind.Error,
                            Text = "WARNING: No tools loaded! AI cannot make Unity changes. Check the chat-server log.",
                        });
                    }
                    break;
                default:
                    Debug.LogWarning($"[UnityTools.Chat] Unknown message type: {type}");
                    break;
            }
            _scrollPos.y = float.MaxValue;
        }

        private void OnGUI()
        {
            EnsureStyles();
            DrawHero();
            DrawSceneSelector();
            DrawToolbar();
            DrawMessages();
            DrawInput();
        }

        private void DrawHero()
        {
            using (new EditorGUILayout.VerticalScope(EditorStyles.helpBox))
            {
                EditorGUILayout.LabelField("UnityTools AI Autopilot", _headerStyle);
                
                string subtitle = _agentMode.StartsWith("dual-agent", StringComparison.OrdinalIgnoreCase)
                    ? "Cift Agent: Master derin planlar, Worker hizli uygular."
                    : "Unity Editor icinde sohbet. Local Ollama veya cloud modeller Unity/Blender tool'larini cagirir.";
                
                EditorGUILayout.LabelField(subtitle, _subtleStyle);
                
                using (new EditorGUILayout.HorizontalScope())
                {
                    DrawChip(IsConnected() ? "AI Bagli" : "AI Kapali", IsConnected());
                    DrawChip(BridgeServer.IsRunning ? "Unity Bridge OK" : "Unity Bridge Kapali", BridgeServer.IsRunning);
                    DrawChip(ChatServerProcess.IsOwnedProcessRunning ? "Core Yonetiliyor" : "Core Local", ChatServerProcess.IsOwnedProcessRunning || ChatServerProcess.IsPortOpen(_serverHost, _serverPort));
                    
                    if (_agentMode == "dual-agent")
                    {
                        DrawChip("Dual-Agent", true);
                    }
                    else
                    {
                        DrawChip(_providerLabel, true);
                    }
                }
            }
        }

        private void DrawSceneSelector()
        {
            if (EditorApplication.timeSinceStartup >= _nextSceneRefresh && _sceneChoices.Count == 0)
            {
                RefreshScenes();
            }
            using (new EditorGUILayout.VerticalScope(EditorStyles.helpBox))
            {
                EditorGUILayout.LabelField("Calisilacak Sahne", EditorStyles.boldLabel);
                using (new EditorGUILayout.HorizontalScope())
                {
                    _selectedSceneIndex = Mathf.Clamp(_selectedSceneIndex, 0, Mathf.Max(0, _sceneLabels.Length - 1));
                    _selectedSceneIndex = EditorGUILayout.Popup(_selectedSceneIndex, _sceneLabels);
                    if (GUILayout.Button("Yenile", GUILayout.Width(70)))
                    {
                        RefreshScenes();
                    }
                    using (new EditorGUI.DisabledScope(_sceneChoices.Count == 0 || _selectedSceneIndex >= _sceneChoices.Count))
                    {
                        if (GUILayout.Button("Sahneyi Ac", GUILayout.Width(92)))
                        {
                            OpenSelectedScene();
                        }
                    }
                }
                string activePath = UnityEngine.SceneManagement.SceneManager.GetActiveScene().path;
                EditorGUILayout.LabelField("Aktif: " + (string.IsNullOrEmpty(activePath) ? "(kaydedilmemis sahne)" : activePath), _subtleStyle);
            }
        }

        private void DrawToolbar()
        {
            using (new EditorGUILayout.HorizontalScope(EditorStyles.toolbar))
            {
                bool connected = IsConnected();
                if (GUILayout.Button(connected ? "Baglantiyi Kes" : "Baglan", EditorStyles.toolbarButton, GUILayout.Width(100)))
                {
                    if (connected) Disconnect();
                    else EnsureCoreAndConnect(silent: false);
                }
                if (GUILayout.Button("Core Yenile", EditorStyles.toolbarButton, GUILayout.Width(90)))
                {
                    RestartCore();
                }
                _autoConnectEnabled = GUILayout.Toggle(_autoConnectEnabled, "Auto", EditorStyles.toolbarButton, GUILayout.Width(52));
                EditorPrefs.SetBool(PrefAutoConnectKey, _autoConnectEnabled);
                GUILayout.FlexibleSpace();
                if (GUILayout.Button("Temizle", EditorStyles.toolbarButton, GUILayout.Width(65)))
                {
                    _items.Clear();
                    if (connected) _client.SendReset();
                    AddSystemMessage("Sohbet gecmisi temizlendi.");
                }
                if (GUILayout.Button("Log", EditorStyles.toolbarButton, GUILayout.Width(40)))
                {
                    OpenLog();
                }
                if (GUILayout.Button("Ayarlar", EditorStyles.toolbarButton, GUILayout.Width(70)))
                {
                    ShowSettingsPopup();
                }
            }
        }

        private void DrawMessages()
        {
            _scrollPos = EditorGUILayout.BeginScrollView(_scrollPos, GUILayout.ExpandHeight(true));
            if (_items.Count == 0)
            {
                GUILayout.Space(12);
                EditorGUILayout.HelpBox("Dene: 'Bu sahnede 5 kup olustur' veya 'aktif sahnedeki objeleri listele'.", MessageType.Info);
            }
            foreach (var item in _items)
            {
                DrawItem(item);
                EditorGUILayout.Space(5);
            }
            if (_serverThinking)
            {
                GUILayout.Label("AI is thinking and may call tools...", _toolStyle);
            }
            EditorGUILayout.EndScrollView();
        }

        private void DrawItem(ChatItem item)
        {
            switch (item.Kind)
            {
                case ItemKind.User:
                    EditorGUILayout.LabelField("Sen", EditorStyles.miniBoldLabel);
                    EditorGUILayout.SelectableLabel(item.Text, _bubbleUserStyle, GUILayout.Height(GetTextHeight(item.Text, _bubbleUserStyle)));
                    break;
                case ItemKind.Assistant:
                    EditorGUILayout.LabelField("UnityTools AI", EditorStyles.miniBoldLabel);
                    EditorGUILayout.SelectableLabel(item.Text, _bubbleAiStyle, GUILayout.Height(GetTextHeight(item.Text, _bubbleAiStyle)));
                    break;
                case ItemKind.ToolCall:
                case ItemKind.ToolResult:
                    GUILayout.Label(item.Text, _toolStyle);
                    break;
                case ItemKind.Error:
                    GUILayout.Label(item.Text, _errorStyle);
                    break;
                case ItemKind.System:
                    GUILayout.Label(item.Text, _subtleStyle);
                    break;
            }
        }

        private void DrawInput()
        {
            using (new EditorGUILayout.VerticalScope(EditorStyles.helpBox))
            {
                DrawPresetBar();
                using (new EditorGUILayout.HorizontalScope())
                {
                    GUI.SetNextControlName("UnityToolsAIInput");
                    _input = EditorGUILayout.TextArea(_input, GUILayout.MinHeight(48), GUILayout.MaxHeight(140));
                    using (new EditorGUI.DisabledScope(!CanSend()))
                    {
                        if (GUILayout.Button("Send", GUILayout.Width(86), GUILayout.Height(48)))
                        {
                            SendCurrent();
                        }
                    }
                }
                using (new EditorGUILayout.HorizontalScope())
                {
                    if (GUILayout.Button("Upload Image", GUILayout.Width(110)))
                    {
                        PickImage();
                    }
                    if (_selectedImages.Count > 0)
                    {
                        GUILayout.Label($"{_selectedImages.Count} image(s) attached", _subtleStyle);
                        GUILayout.FlexibleSpace();
                        if (GUILayout.Button("Clear Images", GUILayout.Width(100)))
                        {
                            _selectedImages.Clear();
                        }
                    }
                }
                Event e = Event.current;
                if (e.type == EventType.KeyDown && e.keyCode == KeyCode.Return && (e.control || e.command))
                {
                    if (CanSend())
                    {
                        SendCurrent();
                        e.Use();
                    }
                }
                EditorGUILayout.LabelField("Ctrl+Enter gonderir. Tool'lar Undo destekli Unity Editor komutlariyla calisir.", _subtleStyle);
            }
        }

        private void DrawPresetBar()
        {
            EditorGUILayout.LabelField("Hizli Autopilot Komutlari", _subtleStyle);
            using (new EditorGUILayout.HorizontalScope())
            {
                PresetButton("Snapshot", "Aktif sahne icin riskli islerden once scene snapshot al ve snapshot path'ini raporla.");
                PresetButton("Asset DB", "Asset knowledge base olustur; tree/rock/prop/material/texture assetlerini grupla ve en iyi realistic assetleri ozetle.");
                PresetButton("Pembe Duzelt", "Pink/magenta/bozuk material sorunlarini diagnose et, texturelari koruyarak aktif render pipeline'a cevir, sonra visual QA calistir.");
            }
            using (new EditorGUILayout.HorizontalScope())
            {
                PresetButton("Optimize", "Aktif sahnede performans profili al; agir renderer/light/shadow/material risklerini bul, sonra guvenli editor optimizasyonu uygula.");
                PresetButton("Visual QA", "Screenshot ile visual QA calistir; material, isik, kamera, texture ve performans risklerini raporla.");
                PresetButton("Orman Plani", "Secili/aktif sahnede snapshot, terrain, agaclar, kayalar, fog, isik, kamera, performans profili ve visual QA iceren guvenli orman workflow'u planla ve uygula.");
            }
        }

        private void PresetButton(string label, string prompt)
        {
            if (GUILayout.Button(label, GUILayout.Height(22)))
            {
                _input = prompt;
                GUI.FocusControl("UnityToolsAIInput");
            }
        }

        private bool CanSend()
        {
            return IsConnected() && !string.IsNullOrWhiteSpace(_input) && !_serverThinking;
        }

        private bool IsConnected()
        {
            return _client != null && _client.IsConnected;
        }

        private void SendCurrent()
        {
            string text = _input.Trim();
            if (string.IsNullOrEmpty(text) && _selectedImages.Count == 0) return;
            _items.Add(new ChatItem { Kind = ItemKind.User, Text = text });
            try
            {
                if (_selectedImages.Count > 0)
                {
                    var images = new JArray();
                    foreach (var img in _selectedImages)
                    {
                        images.Add(new JObject
                        {
                            ["mime"] = img.Mime,
                            ["data_base64"] = img.Base64,
                            ["name"] = img.Name,
                        });
                    }
                    _client.SendUserMessageWithImages(text, images);
                    _selectedImages.Clear();
                }
                else
                {
                    _client.SendUserMessage(text);
                }
                _input = "";
                _serverThinking = true;
                _scrollPos.y = float.MaxValue;
                GUI.FocusControl(null);
            }
            catch (Exception ex)
            {
                AddErrorMessage("Send failed: " + ex.Message);
            }
        }

        private void EnsureCoreAndConnect(bool silent)
        {
            ChatServerProcess.EnsureRunning(_serverHost, _serverPort, ProjectRoot);
            if (ChatServerProcess.IsPortOpen(_serverHost, _serverPort, 500))
            {
                Connect(silent);
            }
            else if (!silent)
            {
                AddSystemMessage("Starting embedded AI core. It may take a few seconds...");
            }
        }

        private void Connect(bool silent)
        {
            if (IsConnected()) return;
            _client?.Disconnect();
            _client = new ChatClient(_serverHost, _serverPort);
            _client.OnDisconnected += () =>
            {
                EditorApplication.delayCall += () =>
                {
                    if (!IsConnected()) AddSystemMessage("AI core connection closed.");
                    _serverThinking = false;
                    Repaint();
                };
            };
            _client.OnError += (ex) =>
            {
                EditorApplication.delayCall += () =>
                {
                    AddErrorMessage("Connection error: " + ex.Message);
                    Repaint();
                };
            };
            bool ok = _client.Connect();
            if (!ok)
            {
                _client = null;
                if (!silent) AddErrorMessage($"Could not connect to {_serverHost}:{_serverPort}. Check the embedded core log.");
            }
            else if (!silent)
            {
                AddSystemMessage($"Gomulu AI core'a baglandi: {_serverHost}:{_serverPort}.");
            }
        }

        private void Disconnect()
        {
            _client?.Disconnect();
            _client = null;
            AddSystemMessage("AI core baglantisi kesildi.");
        }

        private void RestartCore()
        {
            Disconnect();
            ChatServerProcess.StopOwnedProcess();
            ChatServerProcess.StartHidden(ProjectRoot);
            _nextConnectAttempt = EditorApplication.timeSinceStartup + 1.0f;
            AddSystemMessage("Gomulu AI core yeniden baslatildi.");
        }

        private void OpenLog()
        {
            string path = ChatServerProcess.LastLogPath;
            if (!string.IsNullOrEmpty(path) && File.Exists(path))
            {
                EditorUtility.RevealInFinder(path);
            }
            else
            {
                EditorUtility.DisplayDialog("UnityTools AI", "No embedded core log exists yet.", "OK");
            }
        }

        private void ShowSettingsPopup()
        {
            var w = GetWindow<ChatSettingsWindow>(true, "UnityTools AI Settings");
            w.Init(_serverHost, _serverPort, (host, port) =>
            {
                _serverHost = host;
                _serverPort = port;
                EditorPrefs.SetString(PrefHostKey, host);
                EditorPrefs.SetInt(PrefPortKey, port);
                AddSystemMessage($"Settings saved: {host}:{port}");
            });
        }

        private void AddSystemMessage(string text) =>
            _items.Add(new ChatItem { Kind = ItemKind.System, Text = text });

        private void AddErrorMessage(string text) =>
            _items.Add(new ChatItem { Kind = ItemKind.Error, Text = text });

        private void RefreshScenes()
        {
            _nextSceneRefresh = EditorApplication.timeSinceStartup + 10.0f;
            _sceneChoices.Clear();
            try
            {
                string activePath = UnityEngine.SceneManagement.SceneManager.GetActiveScene().path;
                string[] guids = AssetDatabase.FindAssets("t:Scene");
                foreach (string guid in guids)
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    if (string.IsNullOrWhiteSpace(path)) continue;
                    if (!path.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase)) continue;
                    _sceneChoices.Add(new SceneChoice
                    {
                        Name = Path.GetFileNameWithoutExtension(path),
                        Path = path,
                        Active = string.Equals(path, activePath, StringComparison.OrdinalIgnoreCase),
                    });
                }
                _sceneChoices.Sort((a, b) => string.Compare(a.Path, b.Path, StringComparison.OrdinalIgnoreCase));
                _sceneLabels = _sceneChoices.Count == 0
                    ? new[] { "Sahne bulunamadi" }
                    : _sceneChoices.Select(s => (s.Active ? "* " : "  ") + s.Name + "  -  " + s.Path).ToArray();
                int activeIndex = _sceneChoices.FindIndex(s => s.Active);
                if (activeIndex >= 0) _selectedSceneIndex = activeIndex;
            }
            catch (Exception ex)
            {
                _sceneLabels = new[] { "Sahne listesi alinamadi" };
                AddErrorMessage("Sahne yenileme hatasi: " + ex.Message);
            }
        }

        private void OpenSelectedScene()
        {
            if (_selectedSceneIndex < 0 || _selectedSceneIndex >= _sceneChoices.Count) return;
            var choice = _sceneChoices[_selectedSceneIndex];
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            {
                AddSystemMessage("Sahne gecisi iptal edildi.");
                return;
            }
            try
            {
                var scene = EditorSceneManager.OpenScene(choice.Path, OpenSceneMode.Single);
                AddSystemMessage($"Sahne acildi: {scene.name} ({scene.path})");
                RefreshScenes();
            }
            catch (Exception ex)
            {
                AddErrorMessage("Sahne acilamadi: " + ex.Message);
            }
        }

        private static string CompactParams(JObject obj)
        {
            if (obj == null) return "";
            var props = obj.Properties().ToList();
            var parts = props.Take(3).Select(p => $"{p.Name}={Truncate(p.Value.ToString(), 20)}");
            string s = string.Join(", ", parts);
            if (props.Count > 3) s += ", ...";
            return s;
        }

        private static string Truncate(string s, int max) =>
            s.Length <= max ? s : s.Substring(0, max - 3) + "...";

        private float GetTextHeight(string text, GUIStyle style)
        {
            if (string.IsNullOrEmpty(text)) return 22f;
            float w = EditorGUIUtility.currentViewWidth - 34f;
            return Mathf.Max(24f, style.CalcHeight(new GUIContent(text), w));
        }

        private void DrawChip(string text, bool ok)
        {
            Color old = GUI.color;
            GUI.color = ok ? new Color(0.64f, 0.95f, 0.72f) : new Color(1f, 0.72f, 0.55f);
            GUILayout.Label(text, _chipStyle, GUILayout.ExpandWidth(false));
            GUI.color = old;
        }

        private static string ReadEnvValue(string key, string fallback)
        {
            string envPath = Path.Combine(ProjectRoot, ".env");
            if (!File.Exists(envPath)) return fallback;
            foreach (string line in File.ReadAllLines(envPath))
            {
                if (line.StartsWith(key + "=", StringComparison.OrdinalIgnoreCase))
                {
                    string value = line.Substring(key.Length + 1).Trim();
                    return string.IsNullOrEmpty(value) ? fallback : value;
                }
            }
            return fallback;
        }

        private void EnsureStyles()
        {
            if (_stylesReady) return;
            _headerStyle = new GUIStyle(EditorStyles.boldLabel)
            {
                fontSize = 18,
                padding = new RectOffset(4, 4, 3, 0),
            };
            _subtleStyle = new GUIStyle(EditorStyles.miniLabel)
            {
                wordWrap = true,
                normal = { textColor = new Color(0.62f, 0.67f, 0.72f) },
            };
            _bubbleUserStyle = new GUIStyle(EditorStyles.textArea)
            {
                wordWrap = true,
                fontSize = 12,
                padding = new RectOffset(10, 10, 8, 8),
            };
            _bubbleAiStyle = new GUIStyle(EditorStyles.textArea)
            {
                wordWrap = true,
                fontSize = 12,
                padding = new RectOffset(10, 10, 8, 8),
            };
            _toolStyle = new GUIStyle(EditorStyles.miniLabel)
            {
                fontSize = 11,
                normal = { textColor = new Color(0.55f, 0.75f, 0.95f) },
                padding = new RectOffset(12, 4, 2, 2),
            };
            _errorStyle = new GUIStyle(EditorStyles.miniLabel)
            {
                fontSize = 11,
                wordWrap = true,
                normal = { textColor = new Color(1f, 0.45f, 0.45f) },
                padding = new RectOffset(12, 4, 2, 2),
            };
            _chipStyle = new GUIStyle(EditorStyles.toolbarButton)
            {
                fontSize = 10,
                padding = new RectOffset(8, 8, 2, 2),
                margin = new RectOffset(2, 2, 2, 2),
            };
            _stylesReady = true;
        }

        private enum ItemKind { User, Assistant, ToolCall, ToolResult, Error, System }

        private class ChatItem
        {
            public ItemKind Kind;
            public string Text;
            public bool Ok;
        }

        private struct SelectedImage
        {
            public string Name;
            public string Mime;
            public string Base64;
        }

        private struct SceneChoice
        {
            public string Name;
            public string Path;
            public bool Active;
        }

        private void PickImage()
        {
            string path = EditorUtility.OpenFilePanel("Select reference image", ProjectRoot, "png,jpg,jpeg,webp");
            if (string.IsNullOrEmpty(path) || !File.Exists(path)) return;
            try
            {
                byte[] bytes = File.ReadAllBytes(path);
                string ext = Path.GetExtension(path).ToLowerInvariant();
                string mime = "image/png";
                if (ext == ".jpg" || ext == ".jpeg") mime = "image/jpeg";
                else if (ext == ".webp") mime = "image/webp";
                string b64 = Convert.ToBase64String(bytes);
                _selectedImages.Add(new SelectedImage
                {
                    Name = Path.GetFileName(path),
                    Mime = mime,
                    Base64 = b64,
                });
            }
            catch (Exception ex)
            {
                AddErrorMessage("Image load failed: " + ex.Message);
            }
        }
    }

    public class ChatSettingsWindow : EditorWindow
    {
        private string _host;
        private int _port;
        private string _command;
        private string _arguments;
        private Action<string, int> _onSave;

        public void Init(string host, int port, Action<string, int> onSave)
        {
            _host = host;
            _port = port;
            _command = ChatServerProcess.Command;
            _arguments = ChatServerProcess.Arguments;
            _onSave = onSave;
            minSize = new Vector2(430, 170);
            maxSize = new Vector2(430, 170);
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Connection", EditorStyles.boldLabel);
            _host = EditorGUILayout.TextField("Host", _host);
            _port = EditorGUILayout.IntField("Port", _port);
            EditorGUILayout.Space(6);
            EditorGUILayout.LabelField("Embedded Python Core", EditorStyles.boldLabel);
            _command = EditorGUILayout.TextField("Command", _command);
            _arguments = EditorGUILayout.TextField("Arguments", _arguments);
            EditorGUILayout.Space(10);
            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("Cancel")) Close();
                if (GUILayout.Button("Save"))
                {
                    ChatServerProcess.Command = _command;
                    ChatServerProcess.Arguments = _arguments;
                    _onSave?.Invoke(_host, _port);
                    Close();
                }
            }
        }
    }

    public class BridgeStatusWindow : EditorWindow
    {
        public static void Open()
        {
            var w = GetWindow<BridgeStatusWindow>("UnityTools Status");
            w.minSize = new Vector2(340, 190);
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("UnityTools Runtime", EditorStyles.boldLabel);
            EditorGUILayout.LabelField("Unity command bridge:", BridgeServer.IsRunning ? "OK Running" : "ERR Stopped");
            EditorGUILayout.LabelField("Command bridge port:", BridgeServer.Port.ToString());
            EditorGUILayout.LabelField("Embedded chat core:", ChatServerProcess.IsPortOpen("127.0.0.1", 7778) ? "OK Listening" : "ERR Offline");
            EditorGUILayout.LabelField("Chat core port:", "7778");
            EditorGUILayout.Space();
            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button(BridgeServer.IsRunning ? "Stop Unity Bridge" : "Start Unity Bridge"))
                {
                    if (BridgeServer.IsRunning) BridgeServer.Stop();
                    else BridgeServer.Start();
                }
                if (GUILayout.Button("Restart Chat Core"))
                {
                    ChatServerProcess.StopOwnedProcess();
                    ChatServerProcess.StartHidden(Path.GetDirectoryName(Application.dataPath));
                }
            }
            EditorGUILayout.Space();
            EditorGUILayout.HelpBox("The AI panel starts the Python core silently. No terminal window is required.", MessageType.Info);
        }
    }
}
