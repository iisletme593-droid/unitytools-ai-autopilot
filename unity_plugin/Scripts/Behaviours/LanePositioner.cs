// Runtime: snaps this GameObject to one of N parallel lanes along the
// X axis. Left/right arrow keys (or A/D) shift between lanes. Designed
// for endless-runner / lane-shooter genres.
//
// Lanes are evenly spaced around X=0. With laneCount=3 and laneWidth=2,
// lane indices 0,1,2 sit at X = -2, 0, +2.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/LanePositioner")]
    public class LanePositioner : MonoBehaviour
    {
        [Tooltip("Number of lanes. >= 1.")]
        public int laneCount = 3;

        [Tooltip("World-space distance between adjacent lanes.")]
        public float laneWidth = 2f;

        [Tooltip("Starting lane index (0-based, left-to-right).")]
        public int startLane = 1;

        [Tooltip("Seconds to interpolate between lanes. 0 = instant snap.")]
        public float switchDuration = 0.12f;

        [Tooltip("Key to shift one lane left.")]
        public KeyCode leftKey = KeyCode.A;

        [Tooltip("Key to shift one lane right.")]
        public KeyCode rightKey = KeyCode.D;

        [Tooltip("Also listen to Unity's Input.GetAxis('Horizontal') so arrow keys + joystick work without extra binding.")]
        public bool useHorizontalAxis = true;

        int _currentLane;
        float _targetX;
        float _axisCooldown;

        void Awake()
        {
            laneCount = Mathf.Max(1, laneCount);
            _currentLane = Mathf.Clamp(startLane, 0, laneCount - 1);
            _targetX = LaneX(_currentLane);
            var p = transform.position; p.x = _targetX;
            transform.position = p;
        }

        void Update()
        {
            // Key-based shift (discrete one lane per press)
            if (Input.GetKeyDown(leftKey)) ShiftLane(-1);
            if (Input.GetKeyDown(rightKey)) ShiftLane(1);

            // Horizontal axis: edge-trigger so a held axis doesn't drift
            // through every lane in one frame.
            if (useHorizontalAxis)
            {
                _axisCooldown -= Time.deltaTime;
                if (_axisCooldown <= 0f)
                {
                    float h = Input.GetAxisRaw("Horizontal");
                    if (h < -0.5f) { ShiftLane(-1); _axisCooldown = 0.25f; }
                    else if (h > 0.5f) { ShiftLane(1); _axisCooldown = 0.25f; }
                }
            }

            // Lerp toward target lane X
            var p = transform.position;
            if (switchDuration <= 0f)
            {
                p.x = _targetX;
            }
            else
            {
                p.x = Mathf.MoveTowards(p.x, _targetX, (laneWidth / switchDuration) * Time.deltaTime);
            }
            transform.position = p;
        }

        public void ShiftLane(int delta)
        {
            _currentLane = Mathf.Clamp(_currentLane + delta, 0, laneCount - 1);
            _targetX = LaneX(_currentLane);
        }

        float LaneX(int index)
        {
            // Center the band around X=0
            return (index - (laneCount - 1) / 2f) * laneWidth;
        }
    }
}
