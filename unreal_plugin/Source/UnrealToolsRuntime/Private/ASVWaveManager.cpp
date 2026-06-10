#include "ASVWaveManager.h"

#include "ASVEnemySpawnPoint.h"
#include "ASVPlaceholderEnemy.h"
#include "Components/SceneComponent.h"
#include "Components/TextRenderComponent.h"
#include "EngineUtils.h"

AASVWaveManager::AASVWaveManager()
{
    PrimaryActorTick.bCanEverTick = false;

    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    ObjectiveText = CreateDefaultSubobject<UTextRenderComponent>(TEXT("ObjectiveText"));
    ObjectiveText->SetupAttachment(Root);
    ObjectiveText->SetHorizontalAlignment(EHorizTextAligment::EHTA_Center);
    ObjectiveText->SetVerticalAlignment(EVerticalTextAligment::EVRTA_TextCenter);
    ObjectiveText->SetWorldSize(72.0f);
    ObjectiveText->SetRelativeLocation(FVector(0.0f, 0.0f, 180.0f));
    EnemyClass = AASVPlaceholderEnemy::StaticClass();
    UpdateObjectiveText();
}

void AASVWaveManager::BeginPlay()
{
    Super::BeginPlay();
    if (bAutoStart)
    {
        StartWave();
    }
}

void AASVWaveManager::AdvanceWave()
{
    if (CurrentWave >= TotalWaves)
    {
        bVictory = true;
        AliveEnemies = 0;
        UpdateObjectiveText();
        return;
    }

    CurrentWave = FMath::Clamp(CurrentWave + 1, 1, TotalWaves);
    StartWave();
}

void AASVWaveManager::StartWave()
{
    if (!GetWorld() || !EnemyClass)
    {
        UpdateObjectiveText();
        return;
    }

    int32 Spawned = 0;
    for (TActorIterator<AASVEnemySpawnPoint> It(GetWorld()); It; ++It)
    {
        AASVEnemySpawnPoint* SpawnPoint = *It;
        if (!SpawnPoint || SpawnPoint->WaveIndex != CurrentWave)
        {
            continue;
        }
        if (Spawned >= EnemiesPerWave)
        {
            break;
        }

        FActorSpawnParameters SpawnParams;
        SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
        AActor* Enemy = GetWorld()->SpawnActor<AActor>(
            EnemyClass,
            SpawnPoint->GetActorLocation(),
            SpawnPoint->GetActorRotation(),
            SpawnParams
        );
        if (Enemy)
        {
#if WITH_EDITOR
            Enemy->SetActorLabel(FString::Printf(TEXT("ASV_RuntimeEnemy_W%d_%02d"), CurrentWave, Spawned + 1));
#endif
            if (AASVPlaceholderEnemy* Placeholder = Cast<AASVPlaceholderEnemy>(Enemy))
            {
                Placeholder->SetTargetActor(this);
            }
            ++Spawned;
        }
    }

    AliveEnemies = Spawned;
    UpdateObjectiveText();
}

void AASVWaveManager::RegisterEnemyDefeated()
{
    AliveEnemies = FMath::Max(0, AliveEnemies - 1);
    if (AliveEnemies == 0)
    {
        if (CurrentWave < TotalWaves)
        {
            AdvanceWave();
        }
        else
        {
            bVictory = true;
            UpdateObjectiveText();
        }
        return;
    }
    UpdateObjectiveText();
}

void AASVWaveManager::RegisterPickupCollected(FName PickupType, float Amount)
{
    ++CollectedPickups;
    UE_LOG(LogTemp, Log, TEXT("[ArenaSurvivor] Pickup registered by wave manager: %s amount=%.1f total=%d"),
        *PickupType.ToString(),
        Amount,
        CollectedPickups);
    UpdateObjectiveText();
}

void AASVWaveManager::ResetRuntimeState()
{
    CurrentWave = 1;
    AliveEnemies = 0;
    CollectedPickups = 0;
    bVictory = false;
    UpdateObjectiveText();
}

void AASVWaveManager::UpdateObjectiveText()
{
    if (!ObjectiveText)
    {
        return;
    }

    ObjectiveText->SetText(FText::FromString(GetStatusText()));
}

FString AASVWaveManager::GetStatusText() const
{
    const FString State = bVictory ? TEXT("Victory") : TEXT("Active");
    return FString::Printf(
        TEXT("%s\nState: %s | Wave %d / %d\nEnemies: %d | Pickups: %d\n%s"),
        *Objective,
        *State,
        CurrentWave,
        TotalWaves,
        AliveEnemies,
        CollectedPickups,
        *InteractionHint
    );
}
