// Runtime: destroys this GameObject (or its parent) after a delay.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/DestroyAfter")]
    public class DestroyAfter : MonoBehaviour
    {
        [Tooltip("Seconds to wait after enable before destroying.")]
        public float seconds = 5f;

        [Tooltip("If true, destroys the root of the transform hierarchy instead of just this GO.")]
        public bool destroyRoot = false;

        void OnEnable()
        {
            GameObject target = destroyRoot ? transform.root.gameObject : gameObject;
            Destroy(target, Mathf.Max(0f, seconds));
        }
    }
}
