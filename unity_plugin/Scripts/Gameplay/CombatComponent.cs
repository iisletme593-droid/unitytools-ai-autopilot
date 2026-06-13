using System;
using UnityEngine;

namespace Gameplay
{
    /// Can/mana/hasar durumu + combo sayacı (GAME_DESIGN.md combo sistemi v1).
    /// Hem oyuncu hem düşman kullanır; Autopilot alan adlarına bağımlıdır:
    /// maxHealth, currentHealth, maxMana, currentMana, attackDamage.
    public class CombatComponent : MonoBehaviour
    {
        public float maxHealth = 100f;
        public float currentHealth = 100f;
        public float maxMana = 50f;
        public float currentMana = 50f;
        public float attackDamage = 15f;

        [Header("Combo")]
        public int comboCount;
        public float comboResetSeconds = 3f;
        public float comboDamageBonusPerHit = 0.04f;
        public float comboDamageBonusCap = 0.6f;

        public event Action<float> OnDamaged;
        public event Action OnDied;

        float _lastHitTime;

        public bool IsDead => currentHealth <= 0f;
        public float ComboMultiplier =>
            1f + Mathf.Min(comboDamageBonusCap, comboCount * comboDamageBonusPerHit);

        public void RegisterHitLanded()
        {
            comboCount++;
            _lastHitTime = Time.time;
        }

        public void TakeDamage(float amount)
        {
            if (IsDead) return;
            currentHealth = Mathf.Max(0f, currentHealth - amount);
            comboCount = 0; // hasar yiyince combo sıfırlanır
            OnDamaged?.Invoke(amount);
            if (IsDead) OnDied?.Invoke();
        }

        void Update()
        {
            if (comboCount > 0 && Time.time - _lastHitTime > comboResetSeconds)
                comboCount = 0;
        }
    }
}
