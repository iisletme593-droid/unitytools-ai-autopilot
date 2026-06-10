#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"

class AASVPlayerCombatPawn;
class AASVWaveManager;

#include "ASVHUDWidget.generated.h"

UCLASS()
class UNREALTOOLSRUNTIME_API UASVHUDWidget : public UUserWidget
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "Arena Survivor|HUD")
    void SetSources(AASVWaveManager* InWaveManager, AASVPlayerCombatPawn* InPlayerPawn);

protected:
    virtual int32 NativePaint(
        const FPaintArgs& Args,
        const FGeometry& AllottedGeometry,
        const FSlateRect& MyCullingRect,
        FSlateWindowElementList& OutDrawElements,
        int32 LayerId,
        const FWidgetStyle& InWidgetStyle,
        bool bParentEnabled
    ) const override;

private:
    UPROPERTY()
    TObjectPtr<AASVWaveManager> WaveManager;

    UPROPERTY()
    TObjectPtr<AASVPlayerCombatPawn> PlayerPawn;
};
