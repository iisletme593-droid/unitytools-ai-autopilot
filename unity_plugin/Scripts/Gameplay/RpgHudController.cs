using UnityEngine;

namespace Gameplay
{
    /// HUD denetleyicisi: can/stamina/combo değerlerini okur; OnGUI ile
    /// geçici çubuklar çizer (gerçek UI dilim 1 cilasında uGUI'ye taşınır).
    public class RpgHudController : MonoBehaviour
    {
        public bool showDebugBars = true;

        CombatComponent _combat;
        StaminaComponent _stamina;

        void Update()
        {
            if (_combat != null) return;
            var player = GameObject.FindGameObjectWithTag("Player");
            if (player == null) return;
            _combat = player.GetComponent<CombatComponent>();
            _stamina = player.GetComponent<StaminaComponent>();
        }

        void OnGUI()
        {
            if (!showDebugBars || _combat == null) return;
            DrawBar(12, 12, _combat.currentHealth / Mathf.Max(1f, _combat.maxHealth),
                new Color(0.75f, 0.15f, 0.15f), "HP");
            if (_stamina != null)
                DrawBar(12, 34, _stamina.currentStamina / Mathf.Max(1f, _stamina.maxStamina),
                    new Color(0.2f, 0.6f, 0.25f), "SP");
            if (_combat.comboCount > 1)
                GUI.Label(new Rect(12, 56, 220, 22), $"Combo x{_combat.comboCount}");
        }

        static void DrawBar(float x, float y, float ratio, Color color, string label)
        {
            const float w = 190f, h = 16f;
            var prev = GUI.color;
            GUI.color = Color.black; GUI.DrawTexture(new Rect(x - 1, y - 1, w + 2, h + 2), Texture2D.whiteTexture);
            GUI.color = color;       GUI.DrawTexture(new Rect(x, y, w * Mathf.Clamp01(ratio), h), Texture2D.whiteTexture);
            GUI.color = Color.white; GUI.Label(new Rect(x + 4, y - 1, 60, h + 4), label);
            GUI.color = prev;
        }
    }
}
