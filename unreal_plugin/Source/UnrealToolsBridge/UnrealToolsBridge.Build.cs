using UnrealBuildTool;

public class UnrealToolsBridge : ModuleRules
{
    public UnrealToolsBridge(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "Json",
            "JsonUtilities"
        });

        PrivateDependencyModuleNames.AddRange(new string[]
        {
            "ApplicationCore",
            "EditorStyle",
            "LevelEditor",
            "Projects",
            "Slate",
            "SlateCore",
            "Sockets",
            "ToolMenus",
            "UnrealEd"
        });
    }
}
