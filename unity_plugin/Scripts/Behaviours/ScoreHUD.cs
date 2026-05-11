// Runtime: subscribes to the active GameSession's state and renders
// score / lives into a UI.Text. Designed to be attached to a Text that
// the UI Builder created.
//
// Format string supports {score}, {lives}, {win}. Example:
//   "Coins: {score}/{win}  Lives: {lives}"
using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/ScoreHUD")]
    [RequireComponent(typeof(Text))]
    public class ScoreHUD : MonoBehaviour
    {
        [Tooltip("Format string. Tokens: {score}, {lives}, {win}.")]
        public string format = "Score: {score}";

        [Tooltip("Text shown while no GameSession exists yet (avoids 'null' flicker on first frame).")]
        public string placeholderWhileLoading = "Score: --";

        Text _text;
        GameSession _session;

        void Awake()
        {
            _text = GetComponent<Text>();
            if (_text != null) _text.text = placeholderWhileLoading;
        }

        IEnumerator Start()
        {
            // Wait one frame so a GameSession that was placed in the same
            // scene has a chance to Awake first regardless of script order.
            yield return null;
            BindToSession();
        }

        void OnEnable()
        {
            BindToSession();
        }

        void OnDisable()
        {
            UnbindFromSession();
        }

        void BindToSession()
        {
            if (_session != null) return;
            _session = GameSession.Current;
            if (_session == null) return;
            _session.OnStateChanged += Refresh;
            Refresh();
        }

        void UnbindFromSession()
        {
            if (_session == null) return;
            _session.OnStateChanged -= Refresh;
            _session = null;
        }

        public void Refresh()
        {
            if (_text == null) return;
            if (_session == null)
            {
                _text.text = placeholderWhileLoading;
                return;
            }
            string s = format ?? "";
            s = s.Replace("{score}", _session.Score.ToString());
            s = s.Replace("{lives}", _session.Lives.ToString());
            s = s.Replace("{win}", _session.winScore.ToString());
            _text.text = s;
        }
    }
}
