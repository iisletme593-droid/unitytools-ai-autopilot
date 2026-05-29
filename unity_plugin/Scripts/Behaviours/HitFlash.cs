// Runtime: briefly tints the target Renderer's material color when
// the GameSession loses a life (or via a manual Flash() call from
// the inspector). Provides screen-feedback ("I got hit") without
// requiring a particle / shader system.
//
// Pair pattern: attach to the Player. When Enemy.contactDamage fires
// GameSession.LoseLife, HitFlash sees the OnStateChanged event and
// flashes the player white for `duration` seconds.
using System.Collections;
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/HitFlash")]
    public class HitFlash : MonoBehaviour
    {
        public enum TriggerKind
        {
            None,              // Never auto-fire; only manual Flash() works
            OnLivesDecreased,  // GameSession.Lives drops
            OnScoreIncreased,  // GameSession.Score rises (useful for coin pop)
        }

        [Tooltip("Flash color. Default white = damage feedback; gold = coin pickup.")]
        public Color flashColor = Color.white;

        [Tooltip("Seconds the flash stays at peak before fading back.")]
        public float duration = 0.15f;

        [Tooltip("Which GameSession signal auto-fires the flash.")]
        public TriggerKind triggerKind = TriggerKind.OnLivesDecreased;

        Renderer _renderer;
        Material _runtimeMaterial;
        Color _baseColor;
        Coroutine _active;
        GameSession _session;
        int _lastScore;
        int _lastLives;

        void Awake()
        {
            _renderer = GetComponent<Renderer>();
            if (_renderer != null)
            {
                // Avoid mutating the shared material — sharedMaterial would
                // leak into other GOs using the same material.
                _runtimeMaterial = _renderer.material;
                _baseColor = GetMatColor(_runtimeMaterial);
            }
        }

        void Start()
        {
            BindSession();
        }

        void BindSession()
        {
            _session = GameSession.Current;
            if (_session == null) return;
            _lastScore = _session.Score;
            _lastLives = _session.Lives;
            _session.OnStateChanged += OnStateChanged;
        }

        void OnDestroy()
        {
            if (_session != null) _session.OnStateChanged -= OnStateChanged;
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
                case TriggerKind.OnScoreIncreased:
                    fire = _session.Score > _lastScore;
                    break;
                case TriggerKind.None:
                    fire = false;
                    break;
            }
            if (fire) Flash();
            _lastScore = _session.Score;
            _lastLives = _session.Lives;
        }

        /// <summary>Trigger a flash now. Safe to call repeatedly; restarts.</summary>
        public void Flash()
        {
            if (_runtimeMaterial == null) return;
            if (_active != null) StopCoroutine(_active);
            _active = StartCoroutine(FlashRoutine());
        }

        IEnumerator FlashRoutine()
        {
            SetMatColor(_runtimeMaterial, flashColor);
            yield return new WaitForSeconds(Mathf.Max(0.01f, duration));
            // Linear fade back across half the duration so the cue is felt, not seen
            float fade = Mathf.Max(0.01f, duration);
            float t = 0f;
            while (t < fade)
            {
                t += Time.deltaTime;
                Color c = Color.Lerp(flashColor, _baseColor, Mathf.Clamp01(t / fade));
                SetMatColor(_runtimeMaterial, c);
                yield return null;
            }
            SetMatColor(_runtimeMaterial, _baseColor);
            _active = null;
        }

        static Color GetMatColor(Material m)
        {
            if (m == null) return Color.white;
            if (m.HasProperty("_BaseColor")) return m.GetColor("_BaseColor");
            if (m.HasProperty("_Color")) return m.GetColor("_Color");
            return Color.white;
        }

        static void SetMatColor(Material m, Color c)
        {
            if (m == null) return;
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (m.HasProperty("_Color")) m.SetColor("_Color", c);
        }
    }
}
