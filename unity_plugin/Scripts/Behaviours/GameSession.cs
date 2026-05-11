// Runtime: scene-level score keeper + win/lose state machine + scene
// transitions. Singleton-style — exactly one GameSession per scene; the
// first one to Awake claims the static instance. Collectibles +
// HUDs find it through GameSession.Current.
//
// Design intent: the autonomous studio's Worker can attach Collectible
// + GameSession + ScoreHUD to build a complete "collect N coins to
// win" loop without touching this code.
using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/GameSession")]
    public class GameSession : MonoBehaviour
    {
        public static GameSession Current { get; private set; }

        [Tooltip("Score required to trigger the win transition. <= 0 disables auto-win.")]
        public int winScore = 10;

        [Tooltip("Scene to load when winScore is reached. Empty = no scene change (broadcasts only).")]
        public string winSceneName = "";

        [Tooltip("Scene to load when LoseGame() is invoked. Empty = no scene change.")]
        public string loseSceneName = "";

        [Tooltip("Maximum lives. <= 0 means lives are disabled (single-life only).")]
        public int startingLives = 3;

        public int Score { get; private set; }
        public int Lives { get; private set; }
        public bool IsOver { get; private set; }

        // Event fires whenever score or lives change. Subscribers (ScoreHUD)
        // pull current values via the properties above.
        public event Action OnStateChanged;

        void Awake()
        {
            if (Current != null && Current != this)
            {
                Debug.LogWarning($"GameSession: a second instance was added on {gameObject.name}; ignoring.", this);
                enabled = false;
                return;
            }
            Current = this;
            Lives = Mathf.Max(0, startingLives);
            Score = 0;
            IsOver = false;
        }

        void OnDestroy()
        {
            if (Current == this) Current = null;
        }

        /// <summary>Increment the score by `delta` and check the win condition.</summary>
        public void AddScore(int delta)
        {
            if (IsOver) return;
            Score += delta;
            OnStateChanged?.Invoke();
            if (winScore > 0 && Score >= winScore)
            {
                WinGame();
            }
        }

        /// <summary>Decrement remaining lives and fire lose if we run out.</summary>
        public void LoseLife()
        {
            if (IsOver || startingLives <= 0) return;
            Lives = Mathf.Max(0, Lives - 1);
            OnStateChanged?.Invoke();
            if (Lives == 0) LoseGame();
        }

        public void WinGame()
        {
            if (IsOver) return;
            IsOver = true;
            OnStateChanged?.Invoke();
            if (!string.IsNullOrEmpty(winSceneName))
            {
                SceneManager.LoadScene(winSceneName);
            }
        }

        public void LoseGame()
        {
            if (IsOver) return;
            IsOver = true;
            OnStateChanged?.Invoke();
            if (!string.IsNullOrEmpty(loseSceneName))
            {
                SceneManager.LoadScene(loseSceneName);
            }
        }

        public void Reset()
        {
            Score = 0;
            Lives = Mathf.Max(0, startingLives);
            IsOver = false;
            OnStateChanged?.Invoke();
        }
    }
}
