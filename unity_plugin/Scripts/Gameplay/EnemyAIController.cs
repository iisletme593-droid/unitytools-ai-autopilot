using UnityEngine;

namespace Gameplay
{
    /// Basit kovala-saldır düşman AI'ı. Autopilot enemyTier/enemyLevel atar;
    /// istatistikler bunlardan türetilir (Brute = tier 2+).
    public class EnemyAIController : MonoBehaviour
    {
        public int enemyTier = 1;
        public int enemyLevel = 1;
        public float aggroRange = 12f;
        public float attackRange = 1.9f;
        public float attackCooldown = 1.6f;
        public float moveSpeed = 3.2f;

        public CombatComponent Combat { get; private set; }

        Transform _player;
        CombatComponent _playerCombat;
        float _nextAttackTime;
        bool _statsApplied;

        void Awake()
        {
            Combat = GetComponent<CombatComponent>();
            if (Combat == null) Combat = gameObject.AddComponent<CombatComponent>();
        }

        void Start()
        {
            ApplyTierStats();
        }

        void ApplyTierStats()
        {
            if (_statsApplied) return;
            _statsApplied = true;
            float tierMul = 1f + (enemyTier - 1) * 0.65f;
            float levelMul = 1f + (enemyLevel - 1) * 0.12f;
            Combat.maxHealth = 40f * tierMul * levelMul;
            Combat.currentHealth = Combat.maxHealth;
            Combat.attackDamage = 8f * tierMul * levelMul;
            moveSpeed *= 1f + (enemyTier - 1) * 0.1f;
        }

        void Update()
        {
            if (Combat.IsDead) { enabled = false; return; }
            if (_player == null)
            {
                var p = GameObject.FindGameObjectWithTag("Player");
                if (p == null) return;
                _player = p.transform;
                _playerCombat = p.GetComponent<CombatComponent>();
            }
            if (_playerCombat != null && _playerCombat.IsDead) return;

            float dist = Vector3.Distance(transform.position, _player.position);
            if (dist > aggroRange) return;

            if (dist > attackRange)
            {
                Vector3 dir = (_player.position - transform.position); dir.y = 0f;
                dir.Normalize();
                transform.position += dir * moveSpeed * Time.deltaTime;
                if (dir.sqrMagnitude > 0.01f)
                    transform.rotation = Quaternion.RotateTowards(
                        transform.rotation, Quaternion.LookRotation(dir), 360f * Time.deltaTime);
            }
            else if (Time.time >= _nextAttackTime)
            {
                _nextAttackTime = Time.time + attackCooldown;
                if (_playerCombat != null) _playerCombat.TakeDamage(Combat.attackDamage);
            }
        }
    }
}
