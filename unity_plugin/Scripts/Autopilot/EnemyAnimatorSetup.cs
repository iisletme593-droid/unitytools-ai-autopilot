#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    [InitializeOnLoad]
    public static class EnemyAnimatorSetup
    {
        private const string DoneKey       = "ThornyIvy_EnemyAnim_v2";
        private const string ControllerDir = "Assets/Art/Animations/Controllers";
        private const string ControllerPath = ControllerDir + "/AC_Enemy.controller";

        static EnemyAnimatorSetup()
        {
            if (!AutopilotExecutionMode.ShouldRunAutomatic("EnemyAnimatorSetup")) return;
            if (SessionState.GetBool(DoneKey, false)) return;
            EditorApplication.delayCall += AutoSetup;
        }

        private static void AutoSetup()
        {
            if (SessionState.GetBool(DoneKey, false)) return;
            SessionState.SetBool(DoneKey, true);
            Apply();
        }

        [MenuItem("Tools/Autopilot/Setup Enemy Animators")]
        public static void Apply()
        {
            EnsureDir(ControllerDir);
            var ctrl = BuildController();
            AssignToEnemies(ctrl);
            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            Debug.Log("[EnemyAnimatorSetup] Tamamlandı.");
        }

        // ── AnimatorController ────────────────────────────────────────────────
        private static AnimatorController BuildController()
        {
            if (AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath) != null)
                AssetDatabase.DeleteAsset(ControllerPath);

            var ctrl = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);

            ctrl.AddParameter("Speed",        AnimatorControllerParameterType.Float);
            ctrl.AddParameter("Attack",       AnimatorControllerParameterType.Trigger);
            ctrl.AddParameter("Attack2",      AnimatorControllerParameterType.Trigger);
            ctrl.AddParameter("Alert",        AnimatorControllerParameterType.Trigger);
            ctrl.AddParameter("IsDead",       AnimatorControllerParameterType.Bool);
            ctrl.AddParameter("IsStunned",    AnimatorControllerParameterType.Bool);
            ctrl.AddParameter("IsRetreating", AnimatorControllerParameterType.Bool);

            var sm = ctrl.layers[0].stateMachine;

            // States
            var idle    = sm.AddState("Idle",    new Vector3(-200,   0));
            var walk    = sm.AddState("Walk",    new Vector3(-200,  80));
            var run     = sm.AddState("Run",     new Vector3(-200, 160));
            var attack1 = sm.AddState("Attack1", new Vector3( 180,   0));
            var charge  = sm.AddState("Charge",  new Vector3( 180,  80));
            var alert   = sm.AddState("Alert",   new Vector3( 180, 160));
            var hit     = sm.AddState("Hit",     new Vector3( 180, 240));
            var retreat = sm.AddState("Retreat", new Vector3(-200, 240));
            var die     = sm.AddState("Die",     new Vector3(-200, 320));

            // Clip assignment (best-effort search in project)
            idle.motion    = FindClip("Idle",   "Stand",    "T-Pose");
            walk.motion    = FindClip("Walk",   "Walking",  "Walk");
            run.motion     = FindClip("Run",    "Running",  "Sprint",  "Jog");
            attack1.motion = FindClip("Attack", "Slash",    "Swing",   "Melee", "Strike");
            charge.motion  = FindClip("Charge", "Lunge",    "Rush",    "Dash");
            alert.motion   = FindClip("Roar",   "Scream",   "Alert",   "Taunt");
            hit.motion     = FindClip("Hit",    "Stagger",  "Flinch",  "Hurt");
            retreat.motion = FindClip("WalkBack","Retreat", "BackStep","Backup");
            die.motion     = FindClip("Death",  "Die",      "Dead",    "Dying");

            sm.defaultState = idle;

            // Locomotion transitions
            Tr(idle, walk).AddCondition(AnimatorConditionMode.Greater, 0.2f,  "Speed");
            Tr(walk, idle).AddCondition(AnimatorConditionMode.Less,    0.15f, "Speed");
            Tr(walk, run ).AddCondition(AnimatorConditionMode.Greater, 3.0f,  "Speed");
            Tr(run,  walk).AddCondition(AnimatorConditionMode.Less,    2.5f,  "Speed");

            // Any → Attack1
            AnyTrigger(sm, attack1, "Attack",  false);
            // Any → Charge
            AnyTrigger(sm, charge,  "Attack2", false);
            // Any → Alert
            AnyTrigger(sm, alert,   "Alert",   false);
            // Any → Hit (stun)
            AnyBool(sm, hit, "IsStunned", true);
            // Any → Die (highest priority)
            AnyBool(sm, die, "IsDead",    true);

            // Return to idle after attacks/alert (via exit time)
            ExitTr(attack1, idle, 0.85f);
            ExitTr(charge,  idle, 0.90f);
            ExitTr(alert,   idle, 0.95f);

            // Hit → idle when stun clears
            var unstun = hit.AddTransition(idle);
            unstun.AddCondition(AnimatorConditionMode.IfNot, 0, "IsStunned");
            unstun.hasExitTime = false; unstun.duration = 0.15f;

            // Idle/Walk → Retreat
            var r1 = idle.AddTransition(retreat);
            r1.AddCondition(AnimatorConditionMode.If, 0, "IsRetreating");
            r1.hasExitTime = false; r1.duration = 0.2f;

            var r2 = walk.AddTransition(retreat);
            r2.AddCondition(AnimatorConditionMode.If, 0, "IsRetreating");
            r2.hasExitTime = false; r2.duration = 0.2f;

            var r3 = run.AddTransition(retreat);
            r3.AddCondition(AnimatorConditionMode.If, 0, "IsRetreating");
            r3.hasExitTime = false; r3.duration = 0.2f;

            // Retreat → idle
            var rOff = retreat.AddTransition(idle);
            rOff.AddCondition(AnimatorConditionMode.IfNot, 0, "IsRetreating");
            rOff.hasExitTime = false; rOff.duration = 0.2f;

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"[EnemyAnimatorSetup] Controller: {ControllerPath}");
            return ctrl;
        }

        // ── Transition helpers ────────────────────────────────────────────────
        private static AnimatorStateTransition Tr(AnimatorState from, AnimatorState to)
        {
            var t = from.AddTransition(to);
            t.hasExitTime = false;
            t.duration    = 0.15f;
            return t;
        }

        private static void ExitTr(AnimatorState from, AnimatorState to, float exitTime)
        {
            var t = from.AddTransition(to);
            t.hasExitTime = true;
            t.exitTime    = exitTime;
            t.duration    = 0.12f;
        }

        private static void AnyTrigger(AnimatorStateMachine sm, AnimatorState to,
                                        string param, bool canSelf)
        {
            var t = sm.AddAnyStateTransition(to);
            t.hasExitTime        = false;
            t.duration           = 0.1f;
            t.canTransitionToSelf = canSelf;
            t.AddCondition(AnimatorConditionMode.If, 0, param);
        }

        private static void AnyBool(AnimatorStateMachine sm, AnimatorState to,
                                     string param, bool value)
        {
            var t = sm.AddAnyStateTransition(to);
            t.hasExitTime        = false;
            t.duration           = 0.08f;
            t.canTransitionToSelf = false;
            t.AddCondition(value ? AnimatorConditionMode.If : AnimatorConditionMode.IfNot, 0, param);
        }

        // ── Clip search ───────────────────────────────────────────────────────
        private static AnimationClip FindClip(params string[] keywords)
        {
            foreach (string kw in keywords)
            {
                // Direct AnimationClip assets
                string[] guids = AssetDatabase.FindAssets($"t:AnimationClip {kw}");
                foreach (string g in guids)
                {
                    var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(
                        AssetDatabase.GUIDToAssetPath(g));
                    if (clip != null && !clip.name.StartsWith("__preview__"))
                        return clip;
                }

                // Sub-assets inside FBX/model files
                foreach (string g in AssetDatabase.FindAssets("t:Model"))
                {
                    string path = AssetDatabase.GUIDToAssetPath(g);
                    foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(path))
                    {
                        if (asset is AnimationClip clip &&
                            !clip.name.StartsWith("__preview__") &&
                            clip.name.IndexOf(kw, System.StringComparison.OrdinalIgnoreCase) >= 0)
                            return clip;
                    }
                }
            }
            return null;
        }

        // ── Assign to scene enemies ───────────────────────────────────────────
        private static void AssignToEnemies(AnimatorController ctrl)
        {
            var enemies = UnityEngine.Object.FindObjectsByType<Gameplay.EnemyAIController>(
                FindObjectsInactive.Include);
            int assigned = 0;
            foreach (var e in enemies)
            {
                var anim = e.GetComponentInChildren<Animator>();
                if (anim == null) anim = e.gameObject.AddComponent<Animator>();
                if (anim.runtimeAnimatorController == ctrl) continue;
                anim.runtimeAnimatorController = ctrl;
                EditorUtility.SetDirty(anim);
                assigned++;
            }
            Debug.Log($"[EnemyAnimatorSetup] {assigned}/{enemies.Length} düşmana animator atandı.");
        }

        // ── Folder helper ─────────────────────────────────────────────────────
        private static void EnsureDir(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = System.IO.Path.GetDirectoryName(path).Replace('\\', '/');
            string folder = System.IO.Path.GetFileName(path);
            EnsureDir(parent);
            AssetDatabase.CreateFolder(parent, folder);
        }
    }
}
#endif

