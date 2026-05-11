// Runtime: wires a UI.Button click to SceneManager.LoadScene. Designed to
// be added to a Button GameObject.
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/LoadSceneOnClick")]
    [RequireComponent(typeof(Button))]
    public class LoadSceneOnClick : MonoBehaviour
    {
        [Tooltip("Name of the scene to load (must be enabled in EditorBuildSettings).")]
        public string sceneName = "";

        void OnEnable()
        {
            var btn = GetComponent<Button>();
            if (btn != null) btn.onClick.AddListener(OnClick);
        }

        void OnDisable()
        {
            var btn = GetComponent<Button>();
            if (btn != null) btn.onClick.RemoveListener(OnClick);
        }

        public void OnClick()
        {
            if (string.IsNullOrEmpty(sceneName))
            {
                Debug.LogWarning("LoadSceneOnClick: sceneName is empty.");
                return;
            }
            SceneManager.LoadScene(sceneName);
        }
    }
}
