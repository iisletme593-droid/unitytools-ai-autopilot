// Runtime: adds a jump arc on a key press. Single-axis (vertical
// only) — pair with KeyboardMover for horizontal movement.
//
// Implementation: standalone vertical-velocity simulator that adds
// to transform.position.y each frame. NO CharacterController.Move
// (which would conflict with KeyboardMover's own Move call). Ground
// check is a downward raycast.
//
// IMPORTANT: when this behaviour is attached, set
// KeyboardMover.applyGravity=false so the two don't compete on
// vertical motion. The platformer scaffolder enforces this.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Jumper")]
    public class Jumper : MonoBehaviour
    {
        [Tooltip("Peak jump height in world units.")]
        public float jumpHeight = 2.0f;

        [Tooltip("Downward acceleration in m/s^2.")]
        public float gravity = 20f;

        [Tooltip("Key to fire a jump. Default Space.")]
        public KeyCode jumpKey = KeyCode.Space;

        [Tooltip("Ground check ray length from object pivot. Should be slightly more than the visual half-height (e.g. 1.05 for a 2-unit-tall capsule with pivot at center).")]
        public float groundCheckDistance = 1.05f;

        [Tooltip("Layers treated as ground for the downward raycast. Default 'Everything' (~0).")]
        public LayerMask groundMask = ~0;

        [Tooltip("Coyote time — seconds after leaving ground where jump still works. Forgiving for casual players.")]
        public float coyoteTime = 0.1f;

        [Tooltip("Jump-buffer — seconds before landing where a queued jump still fires on touchdown.")]
        public float jumpBuffer = 0.1f;

        public bool IsGrounded { get; private set; }
        public float VerticalVelocity => _yVel;

        float _yVel;
        float _lastGroundedTime = -999f;
        float _lastJumpPressTime = -999f;

        void Update()
        {
            // 1. Ground check (raycast down from pivot)
            IsGrounded = Physics.Raycast(transform.position, Vector3.down,
                                          groundCheckDistance, groundMask,
                                          QueryTriggerInteraction.Ignore);
            if (IsGrounded) _lastGroundedTime = Time.time;

            // 2. Input
            if (Input.GetKeyDown(jumpKey)) _lastJumpPressTime = Time.time;

            // 3. Resolve jump (coyote + buffer)
            bool wantJump = (Time.time - _lastJumpPressTime) <= jumpBuffer;
            bool canJump = (Time.time - _lastGroundedTime) <= coyoteTime;
            if (wantJump && canJump)
            {
                _yVel = Mathf.Sqrt(2f * gravity * Mathf.Max(0.01f, jumpHeight));
                _lastJumpPressTime = -999f;   // consume the buffer
                _lastGroundedTime = -999f;    // consume the coyote
            }

            // 4. Gravity / falling
            if (!IsGrounded)
            {
                _yVel -= gravity * Time.deltaTime;
            }
            else if (_yVel < 0f)
            {
                _yVel = -0.5f;   // keep slight downward velocity so isGrounded stays true
            }

            // 5. Apply
            transform.position += Vector3.up * _yVel * Time.deltaTime;
        }
    }
}
