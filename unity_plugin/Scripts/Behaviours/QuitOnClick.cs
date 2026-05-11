// Runtime: wires a UI.Button click to Application.Quit (or exits play mode
// in the editor). Designed to be added to a Button GameObject.
using UnityEngine;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/QuitOnClick")]
    [RequireComponent(typeof(Button))]
    public class QuitOnClick : MonoBehaviour
    {
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
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }
    }
}
