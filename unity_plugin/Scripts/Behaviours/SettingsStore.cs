// Runtime: PlayerPrefs-backed persistent key/value store. Stores high
// score, music volume, language, last-checkpoint scene, etc. — anything
// the autonomous studio needs to persist between play sessions without
// generating new C# code.
//
// Design: one SettingsStore is enough per game. It exposes static
// helpers so other behaviours (LocalizedText, ScoreHUD, etc.) can read
// + write without holding a reference. All keys are namespaced under
// 'unitytools.' to keep the PlayerPrefs store clean.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/SettingsStore")]
    public class SettingsStore : MonoBehaviour
    {
        public const string KeyPrefix = "unitytools.";

        [Tooltip("If true, also persists when this GO is destroyed (PlayerPrefs.Save on OnDisable).")]
        public bool saveOnDisable = true;

        [Tooltip("Default values applied at first run. Each entry should look like 'volume=0.8' or 'locale=en'. Numbers stored as floats; non-numeric as strings.")]
        public string[] defaults = new string[] { "volume=1.0", "locale=en" };

        void Awake()
        {
            ApplyDefaultsIfMissing();
        }

        void OnDisable()
        {
            if (saveOnDisable) PlayerPrefs.Save();
        }

        void ApplyDefaultsIfMissing()
        {
            if (defaults == null) return;
            foreach (var entry in defaults)
            {
                if (string.IsNullOrEmpty(entry)) continue;
                int eq = entry.IndexOf('=');
                if (eq <= 0 || eq >= entry.Length - 1) continue;
                string key = entry.Substring(0, eq).Trim();
                string val = entry.Substring(eq + 1).Trim();
                if (string.IsNullOrEmpty(key)) continue;
                string fullKey = KeyPrefix + key;
                if (PlayerPrefs.HasKey(fullKey)) continue;
                if (float.TryParse(val, System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out float f))
                {
                    PlayerPrefs.SetFloat(fullKey, f);
                }
                else
                {
                    PlayerPrefs.SetString(fullKey, val);
                }
            }
            PlayerPrefs.Save();
        }

        // ─── Static convenience API ────────────────────────────────────

        static string FullKey(string key) => KeyPrefix + (key ?? "");

        public static void SetFloat(string key, float value)
        {
            PlayerPrefs.SetFloat(FullKey(key), value);
        }

        public static float GetFloat(string key, float defaultValue = 0f)
        {
            return PlayerPrefs.GetFloat(FullKey(key), defaultValue);
        }

        public static void SetInt(string key, int value)
        {
            PlayerPrefs.SetInt(FullKey(key), value);
        }

        public static int GetInt(string key, int defaultValue = 0)
        {
            return PlayerPrefs.GetInt(FullKey(key), defaultValue);
        }

        public static void SetString(string key, string value)
        {
            PlayerPrefs.SetString(FullKey(key), value ?? "");
        }

        public static string GetString(string key, string defaultValue = "")
        {
            return PlayerPrefs.GetString(FullKey(key), defaultValue ?? "");
        }

        public static bool HasKey(string key)
        {
            return PlayerPrefs.HasKey(FullKey(key));
        }

        public static void DeleteKey(string key)
        {
            PlayerPrefs.DeleteKey(FullKey(key));
        }

        public static void Save()
        {
            PlayerPrefs.Save();
        }
    }
}
