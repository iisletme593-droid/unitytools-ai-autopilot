// Runtime: takes damage from Projectile hits and dies after running out
// of health, broadcasting a score reward to the active GameSession.
// Designed for top-down / wave-survival genres. Combine with
// FollowTarget if the enemy should chase the player.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Enemy")]
    public class Enemy : MonoBehaviour
    {
        [Tooltip("Hit points. Each TakeDamage(n) call subtracts n. <=0 -> die.")]
        public int health = 1;

        [Tooltip("Score added to the active GameSession on death.")]
        public int scoreOnDeath = 1;

        [Tooltip("Damage this enemy deals to the player on contact. <= 0 disables contact damage.")]
        public int contactDamage = 0;

        [Tooltip("Player object name prefix used for contact damage. 'Player' matches Player + Player_2 etc.")]
        public string playerNamePrefix = "Player";

        bool _dead;

        public void TakeDamage(int delta)
        {
            if (_dead || delta <= 0) return;
            health -= delta;
            if (health <= 0) Die();
        }

        void Die()
        {
            _dead = true;
            var session = GameSession.Current;
            if (session != null && scoreOnDeath > 0) session.AddScore(scoreOnDeath);
            Destroy(gameObject);
        }

        void OnCollisionEnter(Collision collision)
        {
            HandleContact(collision.collider.gameObject);
        }

        void OnTriggerEnter(Collider other)
        {
            HandleContact(other.gameObject);
        }

        void OnCollisionEnter2D(Collision2D collision)
        {
            HandleContact(collision.collider.gameObject);
        }

        void OnTriggerEnter2D(Collider2D other)
        {
            HandleContact(other.gameObject);
        }

        void HandleContact(GameObject other)
        {
            if (_dead || contactDamage <= 0 || other == null) return;
            if (string.IsNullOrEmpty(playerNamePrefix)) return;
            if (!other.name.StartsWith(playerNamePrefix)) return;
            var session = GameSession.Current;
            if (session != null)
            {
                for (int i = 0; i < contactDamage; i++) session.LoseLife();
            }
        }
    }
}
