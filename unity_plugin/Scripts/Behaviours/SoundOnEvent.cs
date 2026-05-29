// Runtime: plays a one-shot AudioSource clip when a GameSession
// state change matches a chosen event kind. Closes the "game
// happens but is silent" gap from Phase 27 (AudioEngineer attaches
// AudioSource but no behaviour fires them on game events).
//
// Pair pattern:
//   1. Audio Engineer imports the SFX clip + attaches AudioSource
//      to a hidden 'SFX_Coin' GameObject (playOnAwake=false).
//   2. Worker attaches SoundOnEvent here with
//      audioSourceName='SFX_Coin' + triggerKind='ScoreIncreased'.
//   3. Each Collectible.AddScore call fires
//      GameSession.OnStateChanged -> SoundOnEvent.PlayOneShot.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/SoundOnEvent")]
    public class SoundOnEvent : MonoBehaviour
    {
        public enum TriggerKind
        {
            ScoreIncreased,    // any score delta > 0
            LivesDecreased,    // any lives delta < 0
            GameWon,           // IsOver becomes true with Score >= winScore
            GameLost,          // IsOver becomes true without winning
            AnyStateChange,    // every OnStateChanged tick
        }

        [Tooltip("Name of a GameObject in the scene that has an AudioSource. Resolved once at Start; if missing, the sound silently no-ops.")]
        public string audioSourceName = "SFX_Coin";

        [Tooltip("Which GameSession signal triggers playback.")]
        public TriggerKind triggerKind = TriggerKind.ScoreIncreased;

        [Tooltip("Volume scale for the one-shot. 1.0 = the AudioSource's own volume.")]
        [Range(0f, 1f)]
        public float volumeScale = 1.0f;

        AudioSource _source;
        GameSession _session;
        int _lastScore;
        int _lastLives;
        bool _wasOver;

        void Start()
        {
            BindAudioSource();
            BindSession();
        }

        void BindAudioSource()
        {
            if (_source != null) return;
            if (string.IsNullOrEmpty(audioSourceName)) return;
            var go = GameObject.Find(audioSourceName);
            if (go == null) return;
            _source = go.GetComponent<AudioSource>();
        }

        void BindSession()
        {
            if (_session != null) return;
            _session = GameSession.Current;
            if (_session == null) return;
            _lastScore = _session.Score;
            _lastLives = _session.Lives;
            _wasOver = _session.IsOver;
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
                case TriggerKind.ScoreIncreased:
                    fire = _session.Score > _lastScore;
                    break;
                case TriggerKind.LivesDecreased:
                    fire = _session.Lives < _lastLives;
                    break;
                case TriggerKind.GameWon:
                    fire = !_wasOver && _session.IsOver && _session.Score >= _session.winScore;
                    break;
                case TriggerKind.GameLost:
                    fire = !_wasOver && _session.IsOver && _session.Score < _session.winScore;
                    break;
                case TriggerKind.AnyStateChange:
                    fire = true;
                    break;
            }
            if (fire) PlayOneShot();
            _lastScore = _session.Score;
            _lastLives = _session.Lives;
            _wasOver = _session.IsOver;
        }

        public void PlayOneShot()
        {
            if (_source == null) BindAudioSource();
            if (_source == null || _source.clip == null) return;
            _source.PlayOneShot(_source.clip, Mathf.Clamp01(volumeScale));
        }
    }
}
