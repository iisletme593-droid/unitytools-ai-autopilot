// Runtime: simple WASD / arrow-key mover. Drops a CharacterController if
// one isn't already on the GameObject; otherwise uses it. Provides the
// minimal "player can walk" capability the autonomous studio needs to
// make a scene feel like a game instead of a diorama.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/KeyboardMover")]
    public class KeyboardMover : MonoBehaviour
    {
        [Tooltip("World units per second at full input.")]
        public float speed = 5f;

        [Tooltip("Apply gravity each frame (CharacterController only).")]
        public bool applyGravity = true;

        [Tooltip("World-up gravity magnitude.")]
        public float gravity = 9.81f;

        CharacterController _cc;
        float _yVel;

        void Awake()
        {
            _cc = GetComponent<CharacterController>();
        }

        void Update()
        {
            float h = Input.GetAxis("Horizontal");
            float v = Input.GetAxis("Vertical");
            Vector3 move = new Vector3(h, 0f, v);
            if (move.sqrMagnitude > 1f) move.Normalize();
            move *= speed;

            if (_cc != null)
            {
                if (applyGravity)
                {
                    if (_cc.isGrounded) _yVel = -0.5f;
                    else _yVel -= gravity * Time.deltaTime;
                    move.y = _yVel;
                }
                _cc.Move(move * Time.deltaTime);
            }
            else
            {
                transform.position += move * Time.deltaTime;
            }
        }
    }
}
