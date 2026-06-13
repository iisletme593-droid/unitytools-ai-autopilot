using UnityEngine;

namespace Gameplay
{
    /// Tepeden bakışlı oyuncu kontrolü (GAME_DESIGN.md: V-Rising hissi).
    /// WASD = dünya eksenli hareket, Space/Sağ-tık = dodge-roll (stamina harcar).
    [RequireComponent(typeof(CharacterController))]
    public class PlayerController : MonoBehaviour
    {
        public float moveSpeed = 5.5f;
        public float rotationSpeedDeg = 720f;
        public float dodgeSpeed = 11f;
        public float dodgeDuration = 0.35f;
        public float dodgeStaminaCost = 22f;
        public float gravity = -20f;

        CharacterController _cc;
        StaminaComponent _stamina;
        CombatComponent _combat;
        Vector3 _dodgeDir;
        float _dodgeUntil;
        float _verticalVel;

        public bool IsDodging => Time.time < _dodgeUntil;

        void Awake()
        {
            _cc = GetComponent<CharacterController>();
            _stamina = GetComponent<StaminaComponent>();
            _combat = GetComponent<CombatComponent>();
        }

        void Update()
        {
            if (_combat != null && _combat.IsDead) return;

            Vector3 input = new Vector3(Input.GetAxisRaw("Horizontal"), 0f, Input.GetAxisRaw("Vertical"));
            input = Vector3.ClampMagnitude(input, 1f);

            bool wantsDodge = Input.GetKeyDown(KeyCode.Space) || Input.GetMouseButtonDown(1);
            if (wantsDodge && !IsDodging && input.sqrMagnitude > 0.01f &&
                (_stamina == null || _stamina.TryConsume(dodgeStaminaCost)))
            {
                _dodgeDir = input.normalized;
                _dodgeUntil = Time.time + dodgeDuration;
            }

            Vector3 planar = IsDodging ? _dodgeDir * dodgeSpeed : input * moveSpeed;

            if (_cc.isGrounded) _verticalVel = -1f;
            else _verticalVel += gravity * Time.deltaTime;

            _cc.Move((planar + Vector3.up * _verticalVel) * Time.deltaTime);

            Vector3 face = planar; face.y = 0f;
            if (face.sqrMagnitude > 0.01f)
            {
                Quaternion target = Quaternion.LookRotation(face);
                transform.rotation = Quaternion.RotateTowards(transform.rotation, target, rotationSpeedDeg * Time.deltaTime);
            }
        }
    }
}
