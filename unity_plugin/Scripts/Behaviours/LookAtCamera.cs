// Runtime: billboards toward Camera.main every frame.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/LookAtCamera")]
    public class LookAtCamera : MonoBehaviour
    {
        [Tooltip("If true, only yaw rotates (pitch stays level). Good for nameplate-style UI.")]
        public bool lockYAxis = true;

        void LateUpdate()
        {
            var cam = Camera.main;
            if (cam == null) return;
            Vector3 toCam = cam.transform.position - transform.position;
            if (lockYAxis) toCam.y = 0f;
            if (toCam.sqrMagnitude < 0.0001f) return;
            transform.rotation = Quaternion.LookRotation(-toCam.normalized, Vector3.up);
        }
    }
}
