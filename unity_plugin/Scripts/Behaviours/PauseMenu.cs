// Runtime: toggles a target panel + Time.timeScale on a key press
// (default Escape). Designed for the UI Builder + Worker pattern:
//   - UI Builder creates a "PauseCanvas" with a "PausePanel" child
//   - Worker disables PausePanel by default
//   - Worker attaches PauseMenu to the canvas (or any persistent GO)
//     with pausePanel = the PausePanel reference
// Survives across scene loads when persistAcrossScenes = true (uses
// DontDestroyOnLoad, but only when set in the first scene).
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/PauseMenu")]
    public class PauseMenu : MonoBehaviour
    {
        [Tooltip("GameObject (usually a Panel under a Canvas) toggled visible while paused.")]
        public GameObject pausePanel;

        [Tooltip("Key that toggles pause. Default Escape.")]
        public KeyCode toggleKey = KeyCode.Escape;

        [Tooltip("When true, Time.timeScale is set to 0 while paused (gameplay freezes).")]
        public bool freezeTime = true;

        [Tooltip("DontDestroyOnLoad — keeps the pause menu alive across scene transitions.")]
        public bool persistAcrossScenes = false;

        public bool IsPaused { get; private set; }

        float _previousTimeScale = 1f;

        void Awake()
        {
            if (persistAcrossScenes)
            {
                DontDestroyOnLoad(gameObject);
            }
            if (pausePanel != null) pausePanel.SetActive(false);
            IsPaused = false;
        }

        void Update()
        {
            if (Input.GetKeyDown(toggleKey))
            {
                Toggle();
            }
        }

        public void Toggle()
        {
            if (IsPaused) Resume();
            else Pause();
        }

        public void Pause()
        {
            if (IsPaused) return;
            IsPaused = true;
            if (pausePanel != null) pausePanel.SetActive(true);
            if (freezeTime)
            {
                _previousTimeScale = Time.timeScale;
                Time.timeScale = 0f;
            }
        }

        public void Resume()
        {
            if (!IsPaused) return;
            IsPaused = false;
            if (pausePanel != null) pausePanel.SetActive(false);
            if (freezeTime)
            {
                Time.timeScale = _previousTimeScale > 0f ? _previousTimeScale : 1f;
            }
        }

        void OnDisable()
        {
            // Defensive: never leave the game frozen if this component is
            // removed mid-pause.
            if (IsPaused && freezeTime)
            {
                Time.timeScale = _previousTimeScale > 0f ? _previousTimeScale : 1f;
            }
        }
    }
}
