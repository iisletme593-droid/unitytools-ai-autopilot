// Runtime: tracks one achievement unlock condition against the active
// GameSession. On first satisfaction, writes a flag via SettingsStore
// (so it survives play sessions) and fires UnityEvent OnUnlock so a
// UI / SFX behaviour can react.
//
// Design intent: zero-code-generation achievement support. The
// Achievement Designer's doc lists each achievement; the Worker
// attaches one Achievement component per row to a hidden GO with the
// right achievementKey + triggerKind + threshold.
using UnityEngine;
using UnityEngine.Events;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Achievement")]
    public class Achievement : MonoBehaviour
    {
        public enum TriggerKind
        {
            ScoreAtLeast,         // GameSession.Score >= threshold
            LivesRemainingAtMost, // GameSession.Lives <= threshold
            GameOver,             // GameSession.IsOver becomes true
        }

        [Tooltip("PlayerPrefs key (under 'unitytools.' namespace) that stores the unlock flag.")]
        public string achievementKey = "first_blood";

        [Tooltip("Human-readable label, shown by HUD / toast UI when unlocked.")]
        public string unlockMessage = "Achievement unlocked!";

        [Tooltip("Which GameSession signal triggers the unlock check.")]
        public TriggerKind triggerKind = TriggerKind.ScoreAtLeast;

        [Tooltip("Numeric threshold for the trigger. ScoreAtLeast: score >= threshold. LivesRemainingAtMost: lives <= threshold. GameOver: ignored.")]
        public int threshold = 10;

        [Tooltip("Fires once on first unlock. UI / SFX hookups here.")]
        public UnityEvent OnUnlock;

        public bool IsUnlocked { get; private set; }

        GameSession _session;

        void Start()
        {
            // If we were unlocked in a prior play session, restore state
            // so OnUnlock doesn't fire twice across sessions.
            if (SettingsStore.GetInt(StoreKey(), 0) == 1)
            {
                IsUnlocked = true;
            }
            // Bind to GameSession lazily — it might not Awake before us.
            BindSession();
        }

        void Update()
        {
            if (IsUnlocked) return;
            if (_session == null) BindSession();
            if (_session == null) return;
            if (Evaluate(_session)) Unlock();
        }

        void BindSession()
        {
            _session = GameSession.Current;
            if (_session != null) _session.OnStateChanged += OnStateChanged;
        }

        void OnDestroy()
        {
            if (_session != null) _session.OnStateChanged -= OnStateChanged;
        }

        void OnStateChanged()
        {
            if (IsUnlocked || _session == null) return;
            if (Evaluate(_session)) Unlock();
        }

        bool Evaluate(GameSession s)
        {
            switch (triggerKind)
            {
                case TriggerKind.ScoreAtLeast:
                    return s.Score >= threshold;
                case TriggerKind.LivesRemainingAtMost:
                    return s.Lives <= threshold;
                case TriggerKind.GameOver:
                    return s.IsOver;
                default:
                    return false;
            }
        }

        public void Unlock()
        {
            if (IsUnlocked) return;
            IsUnlocked = true;
            SettingsStore.SetInt(StoreKey(), 1);
            SettingsStore.Save();
            Debug.Log($"[Achievement] Unlocked: {achievementKey} - {unlockMessage}");
            OnUnlock?.Invoke();
        }

        /// <summary>Clear the unlock flag (debug / new-game-plus). Does NOT fire OnUnlock.</summary>
        public void ResetUnlock()
        {
            IsUnlocked = false;
            SettingsStore.DeleteKey(StoreKey());
        }

        string StoreKey() => $"achievement.{achievementKey}";
    }
}
