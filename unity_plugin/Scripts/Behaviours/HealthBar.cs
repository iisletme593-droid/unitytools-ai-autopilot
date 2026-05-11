// Runtime: UI.Image whose fillAmount mirrors the active GameSession's
// Lives ratio. Pair pattern:
//   1. UI Builder creates a Canvas with a horizontal Image filled
//      with a bright red sprite. Image.type = Filled, Image.fillMethod
//      = Horizontal, fillOrigin = Left.
//   2. Worker attaches HealthBar to that Image GameObject.
//   3. GameSession.LoseLife() drops fillAmount via OnStateChanged.
//
// HealthBar reads GameSession.startingLives as the denominator so
// the bar starts full regardless of how many lives the designer
// configured.
using UnityEngine;
using UnityEngine.UI;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/HealthBar")]
    [RequireComponent(typeof(Image))]
    public class HealthBar : MonoBehaviour
    {
        [Tooltip("Seconds to lerp toward the new fill value. 0 = instant snap.")]
        public float smoothDuration = 0.25f;

        [Tooltip("If true, also tints the bar from green (full) to red (low). Uses the Image's color channel; works on any sprite.")]
        public bool tintWithHealth = true;

        [Tooltip("Color at 100% health.")]
        public Color fullColor = new Color(0.30f, 0.85f, 0.30f);

        [Tooltip("Color at 0% health.")]
        public Color emptyColor = new Color(0.85f, 0.25f, 0.20f);

        Image _image;
        GameSession _session;
        float _targetFill = 1f;
        float _currentFill = 1f;

        void Awake()
        {
            _image = GetComponent<Image>();
            if (_image != null && _image.type != Image.Type.Filled)
            {
                // Auto-correct: a HealthBar on an Image that isn't filled
                // would render the whole sprite regardless of value. Force
                // the correct mode but log so the designer sees it.
                _image.type = Image.Type.Filled;
                _image.fillMethod = Image.FillMethod.Horizontal;
                _image.fillOrigin = (int)Image.OriginHorizontal.Left;
            }
        }

        void Start()
        {
            BindSession();
            // Snap to full on the first frame
            _currentFill = _targetFill;
            ApplyFill();
        }

        void BindSession()
        {
            _session = GameSession.Current;
            if (_session == null) return;
            _session.OnStateChanged += Recompute;
            Recompute();
        }

        void OnDestroy()
        {
            if (_session != null) _session.OnStateChanged -= Recompute;
        }

        void Recompute()
        {
            if (_session == null) return;
            float denom = Mathf.Max(1, _session.startingLives);
            _targetFill = Mathf.Clamp01(_session.Lives / denom);
        }

        void Update()
        {
            if (_image == null) return;
            if (smoothDuration <= 0f)
            {
                _currentFill = _targetFill;
            }
            else
            {
                _currentFill = Mathf.MoveTowards(_currentFill, _targetFill,
                                                  (1f / smoothDuration) * Time.deltaTime);
            }
            ApplyFill();
        }

        void ApplyFill()
        {
            _image.fillAmount = _currentFill;
            if (tintWithHealth)
            {
                _image.color = Color.Lerp(emptyColor, fullColor, _currentFill);
            }
        }
    }
}
