// Runtime: UI.Button that cycles through configured locale codes,
// calling LocalizedText.SetLocale and persisting via SettingsStore.
// On scene load, restores the last-selected locale from
// SettingsStore (defaulting to defaultLocale on first launch).
//
// Pair pattern:
//   1. Localization Lead seeds en + tr (etc.) string tables.
//   2. UI Builder creates a Button with a child Text labeled
//      "Language: English".
//   3. Worker attaches LocaleSelector with locales=["en","tr"] +
//      a Text reference name for the label.
using UnityEngine;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/LocaleSelector")]
    [RequireComponent(typeof(Button))]
    public class LocaleSelector : MonoBehaviour
    {
        [Tooltip("Ordered list of locale codes (e.g. 'en', 'tr', 'pt-BR'). Click cycles through them.")]
        public string[] locales = new string[] { "en", "tr" };

        [Tooltip("Default locale on first launch (must be in the locales list).")]
        public string defaultLocale = "en";

        [Tooltip("Optional: name of a UI Text in the scene that shows the current locale. Empty = no label updates.")]
        public string labelTextName = "";

        [Tooltip("SettingsStore key (under 'unitytools.') used to persist the active locale.")]
        public string settingsKey = "locale";

        [Tooltip("Label template. {locale} is replaced with the active code. e.g. 'Language: {locale}'.")]
        public string labelFormat = "Lang: {locale}";

        Button _button;
        Text _labelText;
        int _index;

        void Awake()
        {
            _button = GetComponent<Button>();
        }

        void Start()
        {
            // Try to resolve the label
            if (!string.IsNullOrEmpty(labelTextName))
            {
                var labelGo = GameObject.Find(labelTextName);
                if (labelGo != null) _labelText = labelGo.GetComponent<Text>();
            }
            // Restore the last-selected locale, falling back to defaultLocale
            string saved = SettingsStore.GetString(settingsKey, defaultLocale ?? "");
            _index = FindLocaleIndex(saved);
            if (_index < 0) _index = FindLocaleIndex(defaultLocale);
            if (_index < 0) _index = 0;
            ApplyCurrentLocale();
            if (_button != null) _button.onClick.AddListener(OnClick);
        }

        void OnDestroy()
        {
            if (_button != null) _button.onClick.RemoveListener(OnClick);
        }

        public void OnClick()
        {
            if (locales == null || locales.Length == 0) return;
            _index = (_index + 1) % locales.Length;
            ApplyCurrentLocale();
        }

        void ApplyCurrentLocale()
        {
            if (locales == null || locales.Length == 0) return;
            string code = locales[Mathf.Clamp(_index, 0, locales.Length - 1)];
            LocalizedText.SetLocale(code);
            SettingsStore.SetString(settingsKey, code);
            if (_labelText != null)
            {
                _labelText.text = (labelFormat ?? "").Replace("{locale}", code);
            }
        }

        int FindLocaleIndex(string code)
        {
            if (locales == null || string.IsNullOrEmpty(code)) return -1;
            for (int i = 0; i < locales.Length; i++)
            {
                if (locales[i] == code) return i;
            }
            return -1;
        }
    }
}
