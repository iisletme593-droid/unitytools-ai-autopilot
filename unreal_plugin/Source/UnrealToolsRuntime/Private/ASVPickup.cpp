#include "ASVPickup.h"

#include "ASVWaveManager.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "UObject/ConstructorHelpers.h"

AASVPickup::AASVPickup()
{
    PrimaryActorTick.bCanEverTick = false;

    Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
    SetRootComponent(Trigger);
    Trigger->SetSphereRadius(90.0f);
    Trigger->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Trigger->SetCollisionResponseToAllChannels(ECR_Overlap);

    PickupMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PickupMesh"));
    PickupMesh->SetupAttachment(Trigger);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshFinder(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    if (MeshFinder.Succeeded())
    {
        PickupMesh->SetStaticMesh(MeshFinder.Object);
    }
    PickupMesh->SetRelativeScale3D(FVector(0.55f, 0.55f, 0.55f));
}

void AASVPickup::BeginPlay()
{
    Super::BeginPlay();
    if (Trigger)
    {
        Trigger->OnComponentBeginOverlap.AddDynamic(this, &AASVPickup::OnPickupOverlap);
    }
}

void AASVPickup::Collect(AActor* Collector)
{
    if (bCollected)
    {
        return;
    }
    bCollected = true;
    SetActorHiddenInGame(true);
    SetActorEnableCollision(false);

    UE_LOG(LogTemp, Log, TEXT("[ArenaSurvivor] Pickup collected: %s by %s type=%s amount=%.1f"),
        *GetActorLabel(),
        Collector ? *Collector->GetName() : TEXT("Unknown"),
        *PickupType.ToString(),
        Amount);

    if (GetWorld())
    {
        for (TActorIterator<AASVWaveManager> It(GetWorld()); It; ++It)
        {
            It->RegisterPickupCollected(PickupType, Amount);
            break;
        }
    }

    if (bDestroyOnPickup)
    {
        Destroy();
    }
}

void AASVPickup::OnPickupOverlap(
    UPrimitiveComponent* OverlappedComponent,
    AActor* OtherActor,
    UPrimitiveComponent* OtherComp,
    int32 OtherBodyIndex,
    bool bFromSweep,
    const FHitResult& SweepResult
)
{
    if (!OtherActor || OtherActor == this || bCollected)
    {
        return;
    }
    if (OtherActor->IsA<APawn>() || OtherActor->ActorHasTag(TEXT("Player")))
    {
        Collect(OtherActor);
    }
}
