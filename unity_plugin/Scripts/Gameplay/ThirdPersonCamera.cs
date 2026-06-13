using UnityEngine;

namespace Gameplay
{
    /// Tepeden takip kamerası (isim eski tasarımdan; davranış GAME_DESIGN v1.0:
    /// ~50 derece açılı V-Rising tarzı). Player tag'li objeyi takip eder.
    public class ThirdPersonCamera : MonoBehaviour
    {
        public Transform target;
        public float height = 13f;
        public float distance = 8f;
        public float pitchDeg = 52f;
        public float followLerp = 6f;

        void LateUpdate()
        {
            if (target == null)
            {
                var p = GameObject.FindGameObjectWithTag("Player");
                if (p != null) target = p.transform;
                else return;
            }
            Vector3 desired = target.position + new Vector3(0f, height, -distance);
            transform.position = Vector3.Lerp(transform.position, desired, followLerp * Time.deltaTime);
            transform.rotation = Quaternion.Euler(pitchDeg, 0f, 0f);
        }
    }
}
