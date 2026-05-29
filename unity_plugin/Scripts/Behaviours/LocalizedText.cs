// Runtime: pulls a localized string by key from a JSON file under
// Resources/Strings/<locale>.json and assigns it to a UI.Text component.
//
// File format (UTF-8 JSON):
//   { "title.main": "Project Xenon", "btn.start": "Start", ... }
//
// Locale is chosen at runtime: defaultLocale is the fallback; the
// studio can set ActiveLocale at any time via LocalizedText.SetLocale.
// On change, every active LocalizedText re-resolves its key.
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/LocalizedText")]
    [RequireComponent(typeof(Text))]
    public class LocalizedText : MonoBehaviour
    {
        [Tooltip("Lookup key in the locale JSON, e.g. 'btn.start'.")]
        public string key = "";

        [Tooltip("Default locale code if ActiveLocale hasn't been set, e.g. 'en'.")]
        public string defaultLocale = "en";

        [Tooltip("If the key is missing, show this string instead. Empty = show the key in brackets.")]
        public string fallback = "";

        static string _activeLocale = "";
        static readonly Dictionary<string, Dictionary<string, string>> _cache = new();
        static readonly List<LocalizedText> _alive = new();

        public static string ActiveLocale => string.IsNullOrEmpty(_activeLocale) ? "en" : _activeLocale;

        public static void SetLocale(string locale)
        {
            if (string.IsNullOrEmpty(locale) || locale == _activeLocale) return;
            _activeLocale = locale;
            // Refresh every live LocalizedText
            for (int i = _alive.Count - 1; i >= 0; i--)
            {
                if (_alive[i] == null) { _alive.RemoveAt(i); continue; }
                _alive[i].Refresh();
            }
        }

        void OnEnable()
        {
            if (!_alive.Contains(this)) _alive.Add(this);
            Refresh();
        }

        void OnDisable()
        {
            _alive.Remove(this);
        }

        public void Refresh()
        {
            string locale = string.IsNullOrEmpty(_activeLocale) ? defaultLocale : _activeLocale;
            string value = Lookup(locale, key);
            if (string.IsNullOrEmpty(value))
            {
                value = string.IsNullOrEmpty(fallback) ? $"[{key}]" : fallback;
            }
            var t = GetComponent<Text>();
            if (t != null) t.text = value;
        }

        static string Lookup(string locale, string lookupKey)
        {
            if (string.IsNullOrEmpty(lookupKey)) return "";
            var table = LoadTable(locale);
            if (table != null && table.TryGetValue(lookupKey, out var v)) return v;
            return "";
        }

        static Dictionary<string, string> LoadTable(string locale)
        {
            if (_cache.TryGetValue(locale, out var existing)) return existing;
            var asset = Resources.Load<TextAsset>($"Strings/{locale}");
            if (asset == null)
            {
                _cache[locale] = null;
                return null;
            }
            var parsed = SimpleJsonStringParser.ParseFlat(asset.text);
            _cache[locale] = parsed;
            return parsed;
        }
    }

    // Minimal flat-JSON object parser (string -> string only). Avoids
    // pulling in a JSON dependency at runtime. Handles standard
    // escapes (\n, \t, \", \\, \uXXXX).
    internal static class SimpleJsonStringParser
    {
        public static Dictionary<string, string> ParseFlat(string text)
        {
            var result = new Dictionary<string, string>();
            if (string.IsNullOrEmpty(text)) return result;
            int i = 0;
            SkipWhitespace(text, ref i);
            if (i >= text.Length || text[i] != '{') return result;
            i++;
            while (i < text.Length)
            {
                SkipWhitespace(text, ref i);
                if (i < text.Length && text[i] == '}') break;
                string key = ReadString(text, ref i);
                if (key == null) break;
                SkipWhitespace(text, ref i);
                if (i >= text.Length || text[i] != ':') break;
                i++;
                SkipWhitespace(text, ref i);
                string value = ReadString(text, ref i);
                if (value == null) break;
                result[key] = value;
                SkipWhitespace(text, ref i);
                if (i < text.Length && text[i] == ',') { i++; continue; }
                if (i < text.Length && text[i] == '}') break;
            }
            return result;
        }

        static void SkipWhitespace(string s, ref int i)
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
                        case '"':  sb.Append('"');  i += 2; continue;
                        case '\\': sb.Append('\\'); i += 2; continue;
                        case '/':  sb.Append('/');  i += 2; continue;
                        case 'n':  sb.Append('\n'); i += 2; continue;
                        case 't':  sb.Append('\t'); i += 2; continue;
                        case 'r':  sb.Append('\r'); i += 2; continue;
                        case 'b':  sb.Append('\b'); i += 2; continue;
                        case 'f':  sb.Append('\f'); i += 2; continue;
                        case 'u':
                            if (i + 5 < s.Length)
                            {
                                string hex = s.Substring(i + 2, 4);
                                if (int.TryParse(hex, System.Globalization.NumberStyles.HexNumber, null, out int code))
                                {
                                    sb.Append((char)code);
                                    i += 6;
                                    continue;
                                }
                            }
                            i += 2;
                            continue;
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
