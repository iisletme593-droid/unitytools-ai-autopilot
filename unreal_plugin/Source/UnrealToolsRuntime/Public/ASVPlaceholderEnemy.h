#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

class UStaticMeshComponent;
class AActor;

#include "ASVPlaceholderEnemy.generated.h"

UCLASS(Blueprintable)
class UNREALTOOLSRUNTIME_API AASVPlaceholderEnemy : public AActor
{
    GENERATED_BODY()

public:
    AASVPlaceholderEnemy();

    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<UStaticMeshComponent> EnemyMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    float Health = 100.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    float MoveSpeed = 120.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    bool bMoveToTarget = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor")
    TObjectPtr<AActor> TargetActor;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    bool bDefeated = false;

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void SetTargetActor(AActor* NewTarget);

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void ApplyArenaDamage(float DamageAmount, AActor* DamageInstigator);

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor")
    void Defeat();
};
