// Runtime: loads an ordered array of strings from a JSON file in
// Resources and walks the player through them one line at a time.
// Drives a target UI.Text. Advances on key press; fires UnityEvent
// OnComplete when the last line is shown + advanced past.
//
// JSON format (flat string array):
//   ["Welcome to the cave.", "Watch your step.", "Coins await."]
//
// Pair pattern:
//   1. Storyteller writes studio/dialogs/<id>.json (mirrored into
//      Assets/Resources/Dialogs/<id>.json at sync time).
//   2. UI Builder creates a DialogCanvas with a Text + 'press
//      space' hint.
//   3. Worker attaches DialogText to the Text component, points
//      dialogId at the JSON's stem.
//   4. Player advances with Space until OnComplete fires; pair
//      it with a SceneManager.LoadScene or canvas.SetActive(false).
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/DialogText")]
    [RequireComponent(typeof(Text))]
    public class DialogText : MonoBehaviour
    {
        [Tooltip("Dialog file stem (no extension). Loads Resources/Dialogs/<dialogId>.json. Expected: a flat JSON string array.")]
        public string dialogId = "intro";

        [Tooltip("Key that advances to the next line. Default Space.")]
        public KeyCode advanceKey = KeyCode.Space;

        [Tooltip("Auto-advance if no input after this many seconds. <=0 disables (manual only).")]
        public float autoAdvanceSeconds = 0f;

        [Tooltip("Fires once when the player advances past the last line. Hook scene transition / canvas hide here.")]
        public UnityEvent OnComplete;

        public int CurrentIndex { get; private set; }
        public bool IsComplete { get; private set; }
        public int LineCount => _lines.Count;

        readonly List<string> _lines = new();
        Text _text;
        float _autoAdvanceAt;

        void Awake()
        {
            _text = GetComponent<Text>();
            LoadLines();
        }

        void Start()
        {
            ShowCurrent();
        }

        void LoadLines()
        {
            _lines.Clear();
            if (string.IsNullOrEmpty(dialogId)) return;
            var asset = Resources.Load<TextAsset>($"Dialogs/{dialogId}");
            if (asset == null)
            {
                Debug.LogWarning($"DialogText: Resources/Dialogs/{dialogId}.json not found.");
                return;
            }
            var parsed = SimpleJsonStringArrayParser.Parse(asset.text);
            _lines.AddRange(parsed);
        }

        void ShowCurrent()
        {
            if (_text == null) return;
            if (_lines.Count == 0)
            {
                _text.text = $"[dialog {dialogId} empty]";
                IsComplete = true;
                return;
            }
            if (CurrentIndex >= _lines.Count)
            {
                IsComplete = true;
                OnComplete?.Invoke();
                return;
            }
            _text.text = _lines[CurrentIndex];
            if (autoAdvanceSeconds > 0f) _autoAdvanceAt = Time.time + autoAdvanceSeconds;
        }

        void Update()
        {
            if (IsComplete) return;
            bool advance = Input.GetKeyDown(advanceKey)
                            || (autoAdvanceSeconds > 0f && Time.time >= _autoAdvanceAt);
            if (advance) Advance();
        }

        /// <summary>Move to the next line. At the last line, fires OnComplete.</summary>
        public void Advance()
        {
            if (IsComplete) return;
            CurrentIndex++;
            if (CurrentIndex >= _lines.Count)
            {
                IsComplete = true;
                if (_text != null) _text.text = "";
                OnComplete?.Invoke();
            }
            else
            {
                ShowCurrent();
            }
        }

        /// <summary>Rewind to the first line. Useful for replay / debug.</summary>
        public void Reset()
        {
            CurrentIndex = 0;
            IsComplete = false;
            ShowCurrent();
        }
    }

    // Minimal flat-JSON string-array parser. Mirrors the
    // SimpleJsonStringParser from LocalizedText so DialogText doesn't
    // need a JSON dependency at runtime.
    internal static class SimpleJsonStringArrayParser
    {
        public static List<string> Parse(string text)
        {
            var result = new List<string>();
            if (string.IsNullOrEmpty(text)) return result;
            int i = 0;
            Skip(text, ref i);
            if (i >= text.Length || text[i] != '[') return result;
            i++;
            while (i < text.Length)
            {
                Skip(text, ref i);
                if (i < text.Length && text[i] == ']') break;
                string s = ReadString(text, ref i);
                if (s == null) break;
                result.Add(s);
                Skip(text, ref i);
                if (i < text.Length && text[i] == ',') { i++; continue; }
                if (i < text.Length && text[i] == ']') break;
            }
            return result;
        }

        static void Skip(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        static string ReadString(string s, ref int i)
        {
            if (i >= s.Length || s[i] != '"') return null;
            i++;
            var sb = new System.Text.StringBuilder();
            while (i < s.Length)
            {
                char c = s[i];
                if (c == '"') { i++; return sb.ToString(); }
                if (c == '\\' && i + 1 < s.Length)
                {
                    char esc = s[i + 1];
                    switch (esc)
                    {
                        case '"': sb.Append('"'); i += 2; continue;
                        case '\\': sb.Append('\\'); i += 2; continue;
                        case 'n': sb.Append('\n'); i += 2; continue;
                        case 't': sb.Append('\t'); i += 2; continue;
                        case 'r': sb.Append('\r'); i += 2; continue;
                        default: sb.Append(esc); i += 2; continue;
                    }
                }
                sb.Append(c);
                i++;
            }
            return null;
        }
    }
}
