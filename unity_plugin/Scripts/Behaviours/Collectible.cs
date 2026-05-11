// Runtime: a pickup that destroys itself on trigger enter and adds its
// score value to the active GameSession. Requires a trigger Collider —
// Worker should attach a SphereCollider with isTrigger=true on the
// target. Optional filter: only counts the player (tagged by name).
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Collectible")]
    public class Collectible : MonoBehaviour
    {
        [Tooltip("Score points added to the active GameSession when collected.")]
        public int scoreValue = 1;

        [Tooltip("If set, only objects with this name (or tag, if it starts with #) trigger the pickup. Empty = any collider.")]
        public string playerFilter = "Player";

        [Tooltip("Destroy self after collecting. If false, the component just disables itself (useful for respawning pickups).")]
        public bool destroyOnPickup = true;

        bool _collected;

        void OnTriggerEnter(Collider other)
        {
            if (_collected) return;
            if (!MatchesFilter(other.gameObject)) return;
            _collected = true;
            var session = GameSession.Current;
            if (session != null) session.AddScore(scoreValue);
            else Debug.LogWarning($"Collectible: no GameSession in scene for {gameObject.name}; score lost.", this);
            if (destroyOnPickup) Destroy(gameObject);
            else gameObject.SetActive(false);
        }

        // Also support 2D physics for top-down / side-scroller games.
        void OnTriggerEnter2D(Collider2D other)
        {
            if (_collected) return;
            if (!MatchesFilter(other.gameObject)) return;
            _collected = true;
            var session = GameSession.Current;
            if (session != null) session.AddScore(scoreValue);
            if (destroyOnPickup) Destroy(gameObject);
            else gameObject.SetActive(false);
        }

        bool MatchesFilter(GameObject other)
        {
            if (string.IsNullOrEmpty(playerFilter)) return true;
            if (playerFilter.StartsWith("#"))
            {
                string tag = playerFilter.Substring(1);
                try { return other.CompareTag(tag); }
                catch { return false; }   // unknown tag
            }
            return other.name == playerFilter || other.name.StartsWith(playerFilter);
        }
    }
}
