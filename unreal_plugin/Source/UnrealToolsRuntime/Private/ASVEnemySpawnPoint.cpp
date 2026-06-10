#include "ASVEnemySpawnPoint.h"

#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"

AASVEnemySpawnPoint::AASVEnemySpawnPoint()
{
    PrimaryActorTick.bCanEverTick = false;

    MarkerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MarkerMesh"));
    SetRootComponent(MarkerMesh);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshFinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    if (MeshFinder.Succeeded())
    {
        MarkerMesh->SetStaticMesh(MeshFinder.Object);
    }
    MarkerMesh->SetWorldScale3D(FVector(0.65f, 0.65f, 1.4f));
}
