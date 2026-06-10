#include "ASVHUDWidget.h"

#include "ASVPlayerCombatPawn.h"
#include "ASVWaveManager.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"

void UASVHUDWidget::SetSources(AASVWaveManager* InWaveManager, AASVPlayerCombatPawn* InPlayerPawn)
{
    WaveManager = InWaveManager;
    PlayerPawn = InPlayerPawn;
}

int32 UASVHUDWidget::NativePaint(
    const FPaintArgs& Args,
    const FGeometry& AllottedGeometry,
    const FSlateRect& MyCullingRect,
    FSlateWindowElementList& OutDrawElements,
    int32 LayerId,
    const FWidgetStyle& InWidgetStyle,
    bool bParentEnabled
) const
{
    const int32 NextLayer = Super::NativePaint(
        Args,
        AllottedGeometry,
        MyCullingRect,
        OutDrawElements,
        LayerId,
        InWidgetStyle,
        bParentEnabled
    );

    FString Text = TEXT("Arena Survivor\n");
    Text += WaveManager ? WaveManager->GetStatusText() : TEXT("No ASVWaveManager found");
    if (PlayerPawn)
    {
        Text += FString::Printf(
            TEXT("\nShots: %d | Hits: %d\nControls: WASD + Mouse, Left Click Fire"),
            PlayerPawn->ShotsFired,
            PlayerPawn->HitsLanded
        );
    }

    FSlateFontInfo FontInfo = FCoreStyle::Get().GetFontStyle(TEXT("NormalFont"));
    FontInfo.Size = 18;
    const FVector2f Position(32.0f, 32.0f);
    const FVector2f Size(860.0f, 260.0f);

    FSlateDrawElement::MakeText(
        OutDrawElements,
        NextLayer + 1,
        AllottedGeometry.ToPaintGeometry(Size, FSlateLayoutTransform(Position)),
        FText::FromString(Text),
        FontInfo,
        ESlateDrawEffect::None,
        FLinearColor(0.92f, 0.86f, 0.72f, 1.0f)
    );

    return NextLayer + 1;
}
