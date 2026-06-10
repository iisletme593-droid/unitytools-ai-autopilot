#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

class USphereComponent;
class UStaticMeshComponent;
class AActor;
class UPrimitiveComponent;
class AASVWaveManager;

#include "ASVPickup.generated.h"

UCLASS(Blueprintable)
class UNREALTOOLSRUNTIME_API AASVPickup : public AActor
{
    GENERATED_BODY()

public:
    AASVPickup();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<USphereComponent> Trigger;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<UStaticMeshComponent> PickupMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    FName PickupType = TEXT("Health");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    float Amount = 25.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    bool bDestroyOnPickup = false;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    bool bCollected = false;

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void Collect(AActor* Collector);

protected:
    virtual void BeginPlay() override;

    UFUNCTION()
    void OnPickupOverlap(
        UPrimitiveComponent* OverlappedComponent,
        AActor* OtherActor,
        UPrimitiveComponent* OtherComp,
        int32 OtherBodyIndex,
        bool bFromSweep,
        const FHitResult& SweepResult
    );
};
