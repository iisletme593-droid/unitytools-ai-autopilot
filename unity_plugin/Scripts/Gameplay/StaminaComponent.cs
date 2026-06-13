using UnityEngine;

namespace Gameplay
{
    /// Dayanıklılık: dodge ve saldırılar tüketir, beklemede yenilenir.
    public class StaminaComponent : MonoBehaviour
    {
        public float maxStamina = 100f;
        public float currentStamina = 100f;
        public float regenPerSecond = 18f;
        public float regenDelayAfterUse = 0.8f;

        float _lastUseTime;

        public bool TryConsume(float amount)
        {
            if (currentStamina < amount) return false;
            currentStamina -= amount;
            _lastUseTime = Time.time;
            return true;
        }

        void Update()
        {
            if (Time.time - _lastUseTime < regenDelayAfterUse) return;
            currentStamina = Mathf.Min(maxStamina, currentStamina + regenPerSecond * Time.deltaTime);
        }
    }
}
