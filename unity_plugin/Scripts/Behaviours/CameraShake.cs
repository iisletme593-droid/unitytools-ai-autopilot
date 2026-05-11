// Runtime: random translation noise on the camera (or any transform)
// for a configurable duration. Triggered by a GameSession event or a
// manual Shake() call (UnityEvent hook).
//
// Implementation: stores the original localPosition on Awake; each
// frame during a shake adds a Vector3 with magnitude * decay applied
// to localPosition; restores cleanly on stop. Decay is exponential
// so the shake feels punchy at the start and tapers.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/CameraShake")]
    public class CameraShake : MonoBehaviour
    {
        public enum TriggerKind
        {
            None,              // Manual only via Shake() method
            OnLivesDecreased,  // GameSession.Lives drops -> shake
            OnGameOver,        // GameSession.IsOver becomes true
        }

        [Tooltip("Peak shake magnitude in world units (or Canvas units if attached to a UI camera).")]
        [Range(0f, 5f)]
        public float magnitude = 0.3f;

        [Tooltip("Total shake duration in seconds. Magnitude decays exponentially to 0 over this window.")]
        public float duration = 0.35f;

        [Tooltip("Which GameSession signal auto-fires the shake.")]
        public TriggerKind triggerKind = TriggerKind.OnLivesDecreased;

        Vector3 _restPosition;
        float _shakeUntil;
        float _shakeStarted;
        GameSession _session;
        int _lastLives;
        bool _wasOver;

        void Awake()
        {
            _restPosition = transform.localPosition;
        }

        void Start()
        {
            BindSession();
        }

        void BindSession()
        {
            _session = GameSession.Current;
            if (_session == null) return;
            _lastLives = _session.Lives;
            _wasOver = _session.IsOver;
            _session.OnStateChanged += OnStateChanged;
        }

        void OnDestroy()
        {
            if (_session != null) _session.OnStateChanged -= OnStateChanged;
            // Defensive: never leave the camera offset from rest on destroy
            transform.localPosition = _restPosition;
        }

        void OnStateChanged()
        {
            if (_session == null) return;
            bool fire = false;
            switch (triggerKind)
            {
                case TriggerKind.OnLivesDecreased:
                    fire = _session.Lives < _lastLives;
                    break;
                case TriggerKind.OnGameOver:
                    fire = !_wasOver && _session.IsOver;
                    break;
                case TriggerKind.None:
                    fire = false;
                    break;
            }
            if (fire) Shake();
            _lastLives = _session.Lives;
            _wasOver = _session.IsOver;
        }

        /// <summary>Trigger a shake now. Restarts any in-progress shake.</summary>
        public void Shake()
        {
            _shakeStarted = Time.time;
            _shakeUntil = Time.time + Mathf.Max(0.01f, duration);
        }

        /// <summary>Trigger a shake with a custom magnitude + duration override.</summary>
        public void ShakeCustom(float overrideMagnitude, float overrideDuration)
        {
            magnitude = Mathf.Max(0f, overrideMagnitude);
            duration = Mathf.Max(0.01f, overrideDuration);
            Shake();
        }

        void LateUpdate()
        {
            // LateUpdate so this fires AFTER any camera follow behaviour
            // (e.g. FollowTarget) has set the base position. We add the
            // shake offset on top.
            if (Time.time >= _shakeUntil)
            {
                transform.localPosition = _restPosition;
                return;
            }
            float elapsed = Time.time - _shakeStarted;
            float window = _shakeUntil - _shakeStarted;
            float t = Mathf.Clamp01(elapsed / window);
            // Exponential decay: full strength at t=0, near-zero at t=1
            float decay = Mathf.Exp(-3f * t);
            float strength = magnitude * decay;
            Vector3 jitter = new Vector3(
                (Random.value - 0.5f) * 2f,
                (Random.value - 0.5f) * 2f,
                0f
            ) * strength;
            transform.localPosition = _restPosition + jitter;
        }
    }
}
