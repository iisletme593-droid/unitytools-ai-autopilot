using UnityEngine;

namespace Gameplay
{
    /// Gece/gündüz döngüsü. Autopilot yansımayla "sunLight" alanını doldurur;
    /// alan adı DEĞİŞMEMELİ. Thorny Ivy atmosferi gereği varsayılan gece ağırlıklı.
    public class DayCycleManager : MonoBehaviour
    {
        public Light sunLight;
        public float dayLengthMinutes = 20f;
        [Range(0f, 1f)] public float timeOfDay = 0.85f; // 0.85 ~ gece başı
        public Gradient lightColorOverDay;
        public AnimationCurve intensityOverDay = AnimationCurve.EaseInOut(0f, 0.05f, 1f, 0.05f);

        void Reset()
        {
            intensityOverDay = new AnimationCurve(
                new Keyframe(0f, 0.02f), new Keyframe(0.25f, 0.9f),
                new Keyframe(0.5f, 1.1f), new Keyframe(0.75f, 0.35f),
                new Keyframe(1f, 0.02f));
        }

        void Update()
        {
            if (sunLight == null) return;
            timeOfDay = Mathf.Repeat(timeOfDay + Time.deltaTime / (dayLengthMinutes * 60f), 1f);
            sunLight.transform.rotation = Quaternion.Euler(timeOfDay * 360f - 90f, 35f, 0f);
            sunLight.intensity = intensityOverDay.Evaluate(timeOfDay);
            if (lightColorOverDay != null && lightColorOverDay.colorKeys.Length > 0)
                sunLight.color = lightColorOverDay.Evaluate(timeOfDay);
        }
    }
}
