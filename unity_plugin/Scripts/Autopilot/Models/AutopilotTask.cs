using System;
using UnityEngine;

namespace Autopilot
{
    /// <summary>
    /// Cross-engine autopilot task. Supported engines: "unity", "blender", "hf", "validate".
    /// TaskType determines execution path; different engines handle different task types.
    ///
    /// Engine types:
    ///   - "unity": Unity editor/runtime tasks (SceneBuild, MaterialPaint, etc.)
    ///   - "blender": Headless Blender FBX export (BlenderExport, BlenderMaterial)
    ///   - "hf": Hugging Face image-to-3D pipeline (HfMeshImport, staging)
    ///   - "validate": Validation-only tasks (no execution, report generation)
    ///
    /// Task types (extend as needed):
    ///   - BlenderExport: Export Blender work.blend → final.fbx
    ///   - BlenderMaterial: Refresh/validate Blender materials
    ///   - HfMeshImport: Import staged HF-generated 3D models
    ///   - VisionIterate: Run Vision Learner N iterations
    ///   - (existing Unity types: SceneBuild, MaterialPaint, GameplayValidation, etc.)
    /// </summary>
    [Serializable]
    public class AutopilotTask
    {
        public string id;
        public string title;
        public string description;
        public string engine = "unity"; // "unity", "blender", "hf", "validate"
        public string taskType = "ReportStatus";
        public string sourceDoc;
        public string[] inputs;
        public string[] outputs;
        public string[] qualityGates;
        public int priority;
        public string status; // Pending, InProgress, Completed, Failed, Abandoned, Skipped
        public string statusReason;
        public string createdAt;
        public string updatedAt;
        public string assignee;
        public float estimatedSeconds;
        public int retryCount;
    }

    [Serializable]
    public class AutopilotTaskList
    {
        public AutopilotTask[] tasks;
    }
}
