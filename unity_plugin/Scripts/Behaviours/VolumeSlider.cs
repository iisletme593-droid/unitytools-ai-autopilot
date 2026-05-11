// Runtime: UI.Slider that controls AudioListener.volume + persists via
// SettingsStore. Pair pattern:
//   1. UI Builder creates a Slider on the PauseCanvas / SettingsCanvas
//   2. Worker attaches VolumeSlider with settingsKey='volume'
//   3. Slider.value -> AudioListener.volume + SettingsStore.SetFloat
//   On scene load, the slider reads back from SettingsStore so the
//   player's choice survives play sessions.
using UnityEngine;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/VolumeSlider")]
    [RequireComponent(typeof(Slider))]
    public class VolumeSlider : MonoBehaviour
    {
        [Tooltip("SettingsStore key (under 'unitytools.' namespace) for this volume control.")]
        public string settingsKey = "volume";

        [Tooltip("Default value when the SettingsStore key is missing. Used on first ever launch.")]
        [Range(0f, 1f)]
        public float defaultValue = 1.0f;

        [Tooltip("If true, AudioListener.volume is updated each time the slider moves. Disable to let an external mixer override.")]
        public bool driveAudioListener = true;

        Slider _slider;

        void Awake()
        {
            _slider = GetComponent<Slider>();
            if (_slider != null)
            {
                _slider.minValue = 0f;
                _slider.maxValue = 1f;
                _slider.wholeNumbers = false;
            }
        }

        void Start()
        {
            // Read persisted value, fall back to defaultValue on first launch
            float v = SettingsStore.GetFloat(settingsKey, Mathf.Clamp01(defaultValue));
            ApplyValue(v);
            if (_slider != null)
            {
                _slider.SetValueWithoutNotify(v);
                _slider.onValueChanged.AddListener(OnSliderChanged);
            }
        }

        void OnDestroy()
        {
            if (_slider != null) _slider.onValueChanged.RemoveListener(OnSliderChanged);
        }

        void OnSliderChanged(float v)
        {
            v = Mathf.Clamp01(v);
            ApplyValue(v);
            SettingsStore.SetFloat(settingsKey, v);
        }

        void ApplyValue(float v)
        {
            if (driveAudioListener) AudioListener.volume = Mathf.Clamp01(v);
        }
    }
}
