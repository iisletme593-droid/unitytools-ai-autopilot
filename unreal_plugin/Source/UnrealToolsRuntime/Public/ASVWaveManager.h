#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

class USceneComponent;
class UTextRenderComponent;
class AASVEnemySpawnPoint;
class AASVPlaceholderEnemy;

#include "ASVWaveManager.generated.h"

UCLASS(Blueprintable)
class UNREALTOOLSRUNTIME_API AASVWaveManager : public AActor
{
    GENERATED_BODY()

public:
    AASVWaveManager();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<USceneComponent> Root;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<UTextRenderComponent> ObjectiveText;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    int32 TotalWaves = 3;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    int32 CurrentWave = 1;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    int32 EnemiesPerWave = 4;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    int32 AliveEnemies = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    bool bAutoStart = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    TSubclassOf<AActor> EnemyClass;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    FString Objective = TEXT("Survive 3 waves near the core");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    FString InteractionHint = TEXT("Collect pickups, kite enemies, protect the core.");

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    int32 CollectedPickups = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    bool bVictory = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Metrics")
    float FunScore = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Metrics")
    float ClarityScore = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Metrics")
    float DifficultyScore = 0.0f;

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void AdvanceWave();

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void StartWave();

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void RegisterEnemyDefeated();

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void RegisterPickupCollected(FName PickupType, float Amount);

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void ResetRuntimeState();

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void UpdateObjectiveText();

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    FString GetStatusText() const;

protected:
    virtual void BeginPlay() override;
};
