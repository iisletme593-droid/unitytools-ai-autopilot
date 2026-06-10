#include "ASVPlayerCombatPawn.h"

#include "ASVHUDWidget.h"
#include "ASVPlaceholderEnemy.h"
#include "ASVWaveManager.h"
#include "Blueprint/UserWidget.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "UObject/ConstructorHelpers.h"

AASVPlayerCombatPawn::AASVPlayerCombatPawn()
{
    PrimaryActorTick.bCanEverTick = true;
    AutoPossessPlayer = EAutoReceiveInput::Player0;

    Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
    Capsule->SetCapsuleHalfHeight(96.0f);
    Capsule->SetCapsuleRadius(42.0f);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));
    SetRootComponent(Capsule);

    BodyMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BodyMesh"));
    BodyMesh->SetupAttachment(Capsule);
    BodyMesh->SetRelativeLocation(FVector(0.0f, 0.0f, -48.0f));
    BodyMesh->SetRelativeScale3D(FVector(0.65f, 0.65f, 1.05f));

    static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshFinder(TEXT("/Engine/BasicShapes/Capsule.Capsule"));
    if (MeshFinder.Succeeded())
    {
        BodyMesh->SetStaticMesh(MeshFinder.Object);
    }

    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(Capsule);
    Camera->SetRelativeLocation(FVector(0.0f, 0.0f, 72.0f));
    Camera->SetRelativeRotation(FRotator(CameraPitch, 0.0f, 0.0f));
}

void AASVPlayerCombatPawn::BeginPlay()
{
    Super::BeginPlay();

    if (APlayerController* PC = Cast<APlayerController>(GetController()))
    {
        PC->bShowMouseCursor = false;
        PC->SetInputMode(FInputModeGameOnly());

        if (bAutoCreateHUD && !HUDWidget)
        {
            HUDWidget = CreateWidget<UASVHUDWidget>(PC, UASVHUDWidget::StaticClass());
            if (HUDWidget)
            {
                AASVWaveManager* Manager = nullptr;
                for (TActorIterator<AASVWaveManager> It(GetWorld()); It; ++It)
                {
                    Manager = *It;
                    break;
                }
                HUDWidget->SetSources(Manager, this);
                HUDWidget->AddToViewport(10);
            }
        }
    }
}

void AASVPlayerCombatPawn::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    FireCooldownRemaining = FMath::Max(0.0f, FireCooldownRemaining - DeltaSeconds);

    APlayerController* PC = Cast<APlayerController>(GetController());
    if (!PC)
    {
        return;
    }

    const FRotator YawRotation(0.0f, GetActorRotation().Yaw, 0.0f);
    const FVector Forward = YawRotation.Vector();
    const FVector Right = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);

    FVector Move = FVector::ZeroVector;
    if (PC->IsInputKeyDown(EKeys::W)) Move += Forward;
    if (PC->IsInputKeyDown(EKeys::S)) Move -= Forward;
    if (PC->IsInputKeyDown(EKeys::D)) Move += Right;
    if (PC->IsInputKeyDown(EKeys::A)) Move -= Right;

    if (!Move.IsNearlyZero())
    {
        Move.Normalize();
        AddActorWorldOffset(Move * MoveSpeed * DeltaSeconds, true);
    }

    float MouseX = 0.0f;
    float MouseY = 0.0f;
    PC->GetInputMouseDelta(MouseX, MouseY);
    AddActorWorldRotation(FRotator(0.0f, MouseX * LookSensitivity, 0.0f));
    CameraPitch = FMath::Clamp(CameraPitch + MouseY * LookSensitivity, -65.0f, 35.0f);
    Camera->SetRelativeRotation(FRotator(CameraPitch, 0.0f, 0.0f));

    if (PC->IsInputKeyDown(EKeys::LeftMouseButton) && FireCooldownRemaining <= 0.0f)
    {
        FireArenaWeapon();
    }
}

bool AASVPlayerCombatPawn::FireArenaWeapon()
{
    FireCooldownRemaining = FireCooldown;
    ++ShotsFired;

    const FVector Start = Camera ? Camera->GetComponentLocation() : GetActorLocation();
    const FVector Direction = Camera ? Camera->GetForwardVector() : GetActorForwardVector();
    const FVector End = Start + Direction * FireRange;

    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ASVFire), true, this);
    const bool bHit = GetWorld() && GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);

    if (bHit)
    {
        if (AASVPlaceholderEnemy* Enemy = Cast<AASVPlaceholderEnemy>(Hit.GetActor()))
        {
            Enemy->ApplyArenaDamage(FireDamage, this);
            ++HitsLanded;
            DrawDebugLine(GetWorld(), Start, Hit.ImpactPoint, FColor::Green, false, 0.12f, 0, 3.0f);
            return true;
        }
        DrawDebugLine(GetWorld(), Start, Hit.ImpactPoint, FColor::Yellow, false, 0.08f, 0, 2.0f);
        return false;
    }

    DrawDebugLine(GetWorld(), Start, End, FColor::Red, false, 0.08f, 0, 2.0f);
    return false;
}
