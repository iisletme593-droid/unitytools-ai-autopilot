#include "ASVPlaceholderEnemy.h"

#include "ASVWaveManager.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"

AASVPlaceholderEnemy::AASVPlaceholderEnemy()
{
    PrimaryActorTick.bCanEverTick = true;

    EnemyMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("EnemyMesh"));
    SetRootComponent(EnemyMesh);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshFinder(TEXT("/Engine/BasicShapes/Cone.Cone"));
    if (MeshFinder.Succeeded())
    {
        EnemyMesh->SetStaticMesh(MeshFinder.Object);
    }
    EnemyMesh->SetWorldScale3D(FVector(0.7f, 0.7f, 1.4f));
    Tags.Add(TEXT("Enemy"));
}

void AASVPlaceholderEnemy::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    if (bDefeated || !bMoveToTarget || !TargetActor)
    {
        return;
    }

    const FVector Current = GetActorLocation();
    const FVector Target = TargetActor->GetActorLocation();
    FVector Direction = Target - Current;
    Direction.Z = 0.0f;
    if (Direction.SizeSquared() < 2500.0f)
    {
        return;
    }

    Direction.Normalize();
    SetActorLocation(Current + Direction * MoveSpeed * DeltaSeconds);
    SetActorRotation(Direction.Rotation());
}

void AASVPlaceholderEnemy::SetTargetActor(AActor* NewTarget)
{
    TargetActor = NewTarget;
}

void AASVPlaceholderEnemy::ApplyArenaDamage(float DamageAmount, AActor* DamageInstigator)
{
    if (bDefeated)
    {
        return;
    }

    Health -= FMath::Max(0.0f, DamageAmount);
    UE_LOG(LogTemp, Log, TEXT("[ArenaSurvivor] Enemy damaged: %s damage=%.1f health=%.1f instigator=%s"),
        *GetActorLabel(),
        DamageAmount,
        Health,
        DamageInstigator ? *DamageInstigator->GetName() : TEXT("Unknown"));

    if (Health <= 0.0f)
    {
        Defeat();
    }
}

void AASVPlaceholderEnemy::Defeat()
{
    if (bDefeated)
    {
        return;
    }

    bDefeated = true;
    SetActorHiddenInGame(true);
    SetActorEnableCollision(false);

    if (AASVWaveManager* Manager = Cast<AASVWaveManager>(TargetActor))
    {
        Manager->RegisterEnemyDefeated();
    }

    UE_LOG(LogTemp, Log, TEXT("[ArenaSurvivor] Enemy defeated: %s"), *GetActorLabel());
    Destroy();
}
