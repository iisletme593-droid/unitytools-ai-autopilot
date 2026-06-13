using UnityEngine;

namespace Gameplay
{
    /// Oyun durumu: ölüm -> kamp ateşinden yeniden doğma döngüsü
    /// (GAME_DESIGN kararı 3: eşya düşmez).
    public class GameManager : MonoBehaviour
    {
        public float respawnDelay = 2.5f;

        CombatComponent _playerCombat;
        float _respawnAt = -1f;

        void Update()
        {
            if (_playerCombat == null)
            {
                var player = GameObject.FindGameObjectWithTag("Player");
                if (player == null) return;
                _playerCombat = player.GetComponent<CombatComponent>();
                if (_playerCombat != null)
                    _playerCombat.OnDied += () => _respawnAt = Time.time + respawnDelay;
            }
            if (_respawnAt > 0f && Time.time >= _respawnAt)
            {
                _respawnAt = -1f;
                Respawn();
            }
        }

        void Respawn()
        {
            var player = GameObject.FindGameObjectWithTag("Player");
            if (player == null || _playerCombat == null) return;
            Vector3 spawn = CampfireVfx.LastCheckpoint ?? player.transform.position;
            var cc = player.GetComponent<CharacterController>();
            if (cc != null) cc.enabled = false;
            player.transform.position = spawn + Vector3.up * 0.5f;
            if (cc != null) cc.enabled = true;
            _playerCombat.currentHealth = _playerCombat.maxHealth;
            _playerCombat.comboCount = 0;
        }
    }
}
