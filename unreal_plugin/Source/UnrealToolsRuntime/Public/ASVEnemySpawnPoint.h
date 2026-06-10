#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

class UStaticMeshComponent;

#include "ASVEnemySpawnPoint.generated.h"

UCLASS(Blueprintable)
class UNREALTOOLSRUNTIME_API AASVEnemySpawnPoint : public AActor
{
    GENERATED_BODY()

public:
    AASVEnemySpawnPoint();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<UStaticMeshComponent> MarkerMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    int32 WaveIndex = 1;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    float SpawnDelay = 0.0f;
};
