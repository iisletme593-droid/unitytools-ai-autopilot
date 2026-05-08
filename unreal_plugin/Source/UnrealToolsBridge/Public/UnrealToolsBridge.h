#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Templates/SharedPointer.h"

class FExtender;

class FUnrealToolsBridgeModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;

private:
    TSharedPtr<FExtender> MenuExtender;
    TSharedPtr<FExtender> ToolbarExtender;
};
