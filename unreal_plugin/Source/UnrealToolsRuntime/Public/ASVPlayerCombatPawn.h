#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"

class UCapsuleComponent;
class UCameraComponent;
class UStaticMeshComponent;
class UASVHUDWidget;

#include "ASVPlayerCombatPawn.generated.h"

UCLASS(Blueprintable)
class UNREALTOOLSRUNTIME_API AASVPlayerCombatPawn : public APawn
{
    GENERATED_BODY()

public:
    AASVPlayerCombatPawn();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<UCapsuleComponent> Capsule;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<UStaticMeshComponent> BodyMesh;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor")
    TObjectPtr<UCameraComponent> Camera;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Combat")
    float MoveSpeed = 620.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Combat")
    float LookSensitivity = 0.12f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Combat")
    float FireRange = 3200.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Combat")
    float FireDamage = 55.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|Combat")
    float FireCooldown = 0.18f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor|Combat")
    int32 ShotsFired = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arena Survivor|Combat")
    int32 HitsLanded = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arena Survivor|HUD")
    bool bAutoCreateHUD = true;

    UFUNCTION(BlueprintCallable, Category = "Arena Survivor|Combat")
    bool FireArenaWeapon();

private:
    float FireCooldownRemaining = 0.0f;
    float CameraPitch = -8.0f;

    UPROPERTY()
    TObjectPtr<UASVHUDWidget> HUDWidget;
};
