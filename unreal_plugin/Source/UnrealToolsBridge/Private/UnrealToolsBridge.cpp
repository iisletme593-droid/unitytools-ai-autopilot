#include "UnrealToolsBridge.h"

#include "Async/Async.h"
#include "Containers/Queue.h"
#include "Containers/Ticker.h"
#include "Editor.h"
#include "Framework/Docking/TabManager.h"
#include "Framework/MultiBox/MultiBoxBuilder.h"
#include "Interfaces/IMainFrameModule.h"
#include "Json.h"
#include "LevelEditor.h"
#include "Misc/Paths.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Styling/CoreStyle.h"
#include "ToolMenus.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "UnrealToolsBridge"

static const FName UnrealToolsChatTabName(TEXT("UnrealToolsAIChat"));

class SUnrealToolsChatPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SUnrealToolsChatPanel) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs)
    {
        Host = TEXT("127.0.0.1");
        Port = 7778;
        // Guvenlik: interpreter'i acik bir mutlak yolla override edilebilir kil
        // (PATH'ten bulunan sahte bir 'python' calistirilmasini onlemek icin).
        Command = TEXT("python");
        {
            FString PyOverride = FPlatformMisc::GetEnvironmentVariable(TEXT("UNITYTOOLS_PYTHON"));
            PyOverride.TrimStartAndEndInline();
            if (!PyOverride.IsEmpty())
            {
                Command = PyOverride;
            }
        }
        Arguments = TEXT("-m unitytools.cli.entry chat-server --use-dual-agent --engine unreal");
        AuthToken = ResolveAuthToken();

        ChildSlot
        [
            SNew(SBorder)
            .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
            .BorderBackgroundColor(FLinearColor(0.018f, 0.021f, 0.028f, 1.0f))
            .Padding(14)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SBorder)
                    .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                    .BorderBackgroundColor(FLinearColor(0.055f, 0.066f, 0.085f, 1.0f))
                    .Padding(14)
                    [
                        SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight()
                        [
                            SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().FillWidth(1.0f)
                            [
                                SNew(SVerticalBox)
                                + SVerticalBox::Slot().AutoHeight()
                                [
                                    SNew(STextBlock)
                                    .Text(LOCTEXT("StudioTitle", "UnrealTools Game Studio"))
                                    .Font(FCoreStyle::GetDefaultFontStyle("Bold", 22))
                                    .ColorAndOpacity(FLinearColor(0.94f, 0.96f, 1.0f, 1.0f))
                                ]
                                + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
                                [
                                    SAssignNew(StatusText, STextBlock)
                                    .Text(LOCTEXT("StudioStatus", "Local AI studio booting..."))
                                    .ColorAndOpacity(FLinearColor(0.62f, 0.68f, 0.76f, 1.0f))
                                ]
                            ]
                            + SHorizontalBox::Slot().AutoWidth()
                            [
                                SNew(SButton)
                                .Text(LOCTEXT("BootButton", "Start Studio"))
                                .OnClicked(this, &SUnrealToolsChatPanel::OnBootClicked)
                            ]
                        ]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 12, 0, 0)
                        [
                            SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 8, 0)
                            [ MakeChip(LOCTEXT("ChipUnreal", "Unreal Bridge 8777"), FLinearColor(0.10f, 0.18f, 0.26f, 1.0f)) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 8, 0)
                            [ MakeChip(LOCTEXT("ChipCore", "Python Core 7778"), FLinearColor(0.12f, 0.16f, 0.26f, 1.0f)) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 8, 0)
                            [ MakeChip(LOCTEXT("ChipDual", "Dual Agent"), FLinearColor(0.16f, 0.12f, 0.25f, 1.0f)) ]
                            + SHorizontalBox::Slot().FillWidth(1.0f)
                            [
                                SNew(STextBlock)
                                .Text(LOCTEXT("StudioHint", "Project, assets, levels, gameplay, UI, multiplayer, build."))
                                .Justification(ETextJustify::Right)
                                .ColorAndOpacity(FLinearColor(0.45f, 0.50f, 0.58f, 1.0f))
                            ]
                        ]
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 12, 0, 0)
                [
                    SNew(SBorder)
                    .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                    .BorderBackgroundColor(FLinearColor(0.034f, 0.040f, 0.052f, 1.0f))
                    .Padding(10)
                    [
                        SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight()
                        [
                            SNew(STextBlock)
                            .Text(LOCTEXT("PresetTitle", "Studio presets"))
                            .Font(FCoreStyle::GetDefaultFontStyle("Bold", 10))
                            .ColorAndOpacity(FLinearColor(0.55f, 0.61f, 0.70f, 1.0f))
                        ]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 7, 0, 0)
                        [
                            SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePresetButton(LOCTEXT("PresetScan", "Project Scan"), TEXT("unreal_scan_project ile Unreal projesini oku: aktif level, actorlar, /Game asset katalogu, seviyeler ve riskleri ozetle.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePresetButton(LOCTEXT("PresetLevel", "Level Plan"), TEXT("unreal_scan_project ile oku; sonra gerekirse unreal_create_basic_level ve unreal_create_blockout_map kullanarak premium playable blockout level kur.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePresetButton(LOCTEXT("PresetGameplay", "Gameplay Loop"), TEXT("Projeyi tara, core gameplay loop tasarla; mevcut level/actor/asset durumuna gore Unreal uygulanabilir sistem planini ve ilk blockout adimini uygula.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePresetButton(LOCTEXT("PresetUI", "UI/HUD"), TEXT("Projeyi tara; main menu, HUD, settings ve inventory UI icin sade premium Unreal uygulanabilir plan hazirla.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePresetButton(LOCTEXT("PresetMulti", "Multiplayer"), TEXT("Projeyi tara; Unreal replication, RPC, PlayerState/GameState ve dedicated server hazirlik plani cikar.")) ]
                            + SHorizontalBox::Slot().AutoWidth()
                            [ MakePresetButton(LOCTEXT("PresetBuild", "Build"), TEXT("Projeyi tara; Windows client build, dedicated server ve Steam sayfasi asset/copy checklist hazirla.")) ]
                        ]
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 0)
                [
                    SNew(SBorder)
                    .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                    .BorderBackgroundColor(FLinearColor(0.040f, 0.049f, 0.066f, 1.0f))
                    .Padding(10)
                    [
                        SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight()
                        [
                            SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().FillWidth(1.0f)
                            [
                                SNew(SVerticalBox)
                                + SVerticalBox::Slot().AutoHeight()
                                [
                                    SNew(STextBlock)
                                    .Text(LOCTEXT("SceneControlTitle", "Sahne kontrolu"))
                                    .Font(FCoreStyle::GetDefaultFontStyle("Bold", 10))
                                    .ColorAndOpacity(FLinearColor(0.58f, 0.66f, 0.78f, 1.0f))
                                ]
                                + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
                                [
                                    SAssignNew(ActiveSceneText, STextBlock)
                                    .Text(LOCTEXT("ActiveSceneUnknown", "Aktif sahne: okunuyor..."))
                                    .ColorAndOpacity(FLinearColor(0.78f, 0.84f, 0.92f, 1.0f))
                                ]
                            ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(6, 0, 0, 0)
                            [
                                SNew(SButton)
                                .Text(LOCTEXT("RefreshScene", "Yenile"))
                                .OnClicked(this, &SUnrealToolsChatPanel::OnRefreshSceneClicked)
                            ]
                        ]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
                        [
                            SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().FillWidth(1.0f).Padding(0, 0, 6, 0)
                            [
                                SAssignNew(SceneNameInput, SEditableTextBox)
                                .HintText(LOCTEXT("SceneNameHint", "Sahne adi yaz: NewMap, Lvl_IntroRoom, UT_ArenaSurvivor_V001..."))
                            ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [
                                SNew(SButton)
                                .Text(LOCTEXT("ListScenes", "Sahneleri Listele"))
                                .OnClicked(this, &SUnrealToolsChatPanel::OnListLevelsClicked)
                            ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [
                                SNew(SButton)
                                .Text(LOCTEXT("OpenScene", "Ac"))
                                .OnClicked(this, &SUnrealToolsChatPanel::OnOpenSceneClicked)
                            ]
                            + SHorizontalBox::Slot().AutoWidth()
                            [
                                SNew(SButton)
                                .Text(LOCTEXT("UseActiveScene", "Bu Sahnede Calis"))
                                .OnClicked(this, &SUnrealToolsChatPanel::OnUseActiveSceneClicked)
                            ]
                        ]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 0)
                        [
                            SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [
                                SNew(STextBlock)
                                .Text(LOCTEXT("QuickActionsLabel", "Hizli aksiyonlar:"))
                                .ColorAndOpacity(FLinearColor(0.50f, 0.57f, 0.66f, 1.0f))
                            ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePromptButton(LOCTEXT("SceneStatus", "Sahne Durumu"), TEXT("Sahne durumunu kontrol et ve risk ozetini goster.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePromptButton(LOCTEXT("SelectedContext", "Seciliyi Oku"), TEXT("Secili actorleri oku ve context ozetle.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePromptButton(LOCTEXT("CleanupPreview", "AI Temizlik Onizle"), TEXT("AI placed actors silmeden once onizle.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePromptButton(LOCTEXT("ForestGround", "Orman Zemini"), TEXT("Open world zemini hazirla, forest ground ve hafif fog uygula.")) ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [ MakePromptButton(LOCTEXT("ForestScatter", "Agac/Kaya Serp"), TEXT("Sahneye 18 agac ve kaya dogal dagit, forest palet uygula.")) ]
                            + SHorizontalBox::Slot().AutoWidth()
                            [ MakePromptButton(LOCTEXT("PremiumLight", "Isik/Sis"), TEXT("Aktif sahneye premium isik kamera ve sis ayarla.")) ]
                        ]
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 0)
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("Connect", "Connect"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnConnectClicked)
                    ]
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("StartCore", "Start Core"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnStartCoreClicked)
                    ]
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("StopCore", "Stop Core"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnStopCoreClicked)
                    ]
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("PingUnreal", "Ping"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnPingClicked)
                    ]
                    + SHorizontalBox::Slot().FillWidth(1.0f)
                    [
                        SNew(STextBlock)
                        .Text(LOCTEXT("ToolbarHint", "Local only. No cloud required with Ollama."))
                        .Justification(ETextJustify::Right)
                        .ColorAndOpacity(FLinearColor(0.42f, 0.47f, 0.54f, 1.0f))
                    ]
                ]
                + SVerticalBox::Slot().FillHeight(1.0f).Padding(0, 12, 0, 0)
                [
                    SNew(SBorder)
                    .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                    .BorderBackgroundColor(FLinearColor(0.025f, 0.030f, 0.040f, 1.0f))
                    .Padding(8)
                    [
                        SAssignNew(Messages, SScrollBox)
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 12, 0, 0)
                [
                    SNew(SBorder)
                    .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                    .BorderBackgroundColor(FLinearColor(0.040f, 0.047f, 0.060f, 1.0f))
                    .Padding(10)
                    [
                        SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight()
                        [
                            SAssignNew(Input, SMultiLineEditableTextBox)
                            .HintText(LOCTEXT("InputHint", "Ask the studio: scan this project, create a map plan, build a gameplay loop..."))
                            .AutoWrapText(true)
                            .AllowMultiLine(true)
                        ]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
                        [
                            SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().FillWidth(1.0f)
                            [
                                SNew(STextBlock)
                                .Text(LOCTEXT("SendHint", "Tip: presets fill the prompt; Send executes it through real Unreal tools."))
                                .ColorAndOpacity(FLinearColor(0.46f, 0.51f, 0.58f, 1.0f))
                            ]
                            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                            [
                                SNew(SButton)
                                .Text(LOCTEXT("Clear", "Clear"))
                                .OnClicked(this, &SUnrealToolsChatPanel::OnClearClicked)
                            ]
                            + SHorizontalBox::Slot().AutoWidth()
                            [
                                SNew(SButton)
                                .Text(LOCTEXT("Send", "Send"))
                                .OnClicked(this, &SUnrealToolsChatPanel::OnSendClicked)
                            ]
                        ]
                    ]
                ]
            ]
        ];

        AddMessage(TEXT("System"), TEXT("UnrealTools Game Studio ready. Core will auto-start; use Start Studio if needed."));
        RefreshActiveSceneLabel();
        TickerHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SUnrealToolsChatPanel::ProcessInbound), 0.1f);
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SUnrealToolsChatPanel::AutoBoot), 1.0f);
    }

    virtual ~SUnrealToolsChatPanel()
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
        Disconnect();
    }

private:
    FString Host;
    int32 Port = 7778;
    FString Command;
    FString Arguments;
    FString AuthToken;
    TSharedPtr<SScrollBox> Messages;
    TSharedPtr<SMultiLineEditableTextBox> Input;
    TSharedPtr<SEditableTextBox> SceneNameInput;
    TSharedPtr<STextBlock> StatusText;
    TSharedPtr<STextBlock> ActiveSceneText;
    FTSTicker::FDelegateHandle TickerHandle;
    FProcHandle CoreProcess;
    uint32 CorePid = 0;
    FSocket* Socket = nullptr;
    FThreadSafeBool StopReader = false;
    TQueue<FString, EQueueMode::Mpsc> InboundLines;

    bool ProcessInbound(float DeltaTime)
    {
        FString Line;
        while (InboundLines.Dequeue(Line))
        {
            HandleLine(Line);
        }
        return true;
    }

    FReply OnStartCoreClicked()
    {
        StartCore();
        return FReply::Handled();
    }

    FReply OnBootClicked()
    {
        StartCore();
        Connect();
        if (!Socket)
        {
            FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SUnrealToolsChatPanel::DelayedConnect), 1.5f);
        }
        return FReply::Handled();
    }

    FReply OnStopCoreClicked()
    {
        StopCore();
        return FReply::Handled();
    }

    FReply OnConnectClicked()
    {
        if (Socket)
        {
            Disconnect();
            return FReply::Handled();
        }
        Connect();
        return FReply::Handled();
    }

    FReply OnPingClicked()
    {
        SendJson(TEXT("{\"type\":\"ping\"}"));
        return FReply::Handled();
    }

    FReply OnRefreshSceneClicked()
    {
        RefreshActiveSceneLabel();
        AddMessage(TEXT("System"), FString::Printf(TEXT("Aktif sahne: %s"), *GetActiveMapName()));
        return FReply::Handled();
    }

    FReply OnListLevelsClicked()
    {
        const FString Prompt = TEXT("Sahneleri listele hangi mapler var; aktif map bilgisini de goster.");
        AddMessage(TEXT("Sen"), Prompt);
        SendUserMessage(Prompt);
        return FReply::Handled();
    }

    FReply OnOpenSceneClicked()
    {
        FString SceneName = SceneNameInput.IsValid() ? SceneNameInput->GetText().ToString() : TEXT("");
        SceneName.TrimStartAndEndInline();
        if (SceneName.IsEmpty())
        {
            AddMessage(TEXT("Error"), TEXT("Once sahne adi yaz: NewMap gibi."));
            return FReply::Handled();
        }
        const FString Prompt = FString::Printf(TEXT("%s sahnesini ac"), *SceneName);
        AddMessage(TEXT("Sen"), Prompt);
        SendUserMessage(Prompt);
        return FReply::Handled();
    }

    FReply OnUseActiveSceneClicked()
    {
        RefreshActiveSceneLabel();
        const FString ActiveMap = GetActiveMapName();
        const FString Prompt = FString::Printf(
            TEXT("Bu aktif sahnede calis: %s. Once unreal_get_project_info ile aktif map'i dogrula, sonra bundan sonraki talimatlari bu sahneye uygula."),
            *ActiveMap
        );
        AddMessage(TEXT("Sen"), Prompt);
        SendUserMessage(Prompt);
        return FReply::Handled();
    }

    FReply OnSendClicked()
    {
        FString Text = Input.IsValid() ? Input->GetText().ToString() : TEXT("");
        Text.TrimStartAndEndInline();
        if (Text.IsEmpty())
        {
            return FReply::Handled();
        }
        AddMessage(TEXT("Sen"), Text);
        SendUserMessage(Text);
        Input->SetText(FText::GetEmpty());
        return FReply::Handled();
    }

    FReply OnListActorsClicked()
    {
        Preset(TEXT("Aktif Unreal leveldaki actorlari semantic kategorileriyle listele ve onemli objeleri ozetle."));
        return FReply::Handled();
    }

    FReply OnAssetCatalogClicked()
    {
        Preset(TEXT("/Game altindaki assetleri tara; tree, rock, material, texture, character, sound olarak grupla ve uygun kullanim oner."));
        return FReply::Handled();
    }

    FReply OnClearClicked()
    {
        if (Messages.IsValid())
        {
            Messages->ClearChildren();
        }
        SendJson(TEXT("{\"type\":\"reset\"}"));
        AddMessage(TEXT("System"), TEXT("Sohbet temizlendi."));
        return FReply::Handled();
    }

    void Preset(const FString& Text)
    {
        if (Input.IsValid())
        {
            Input->SetText(FText::FromString(Text));
        }
    }

    FString GetActiveMapName() const
    {
        if (GEditor)
        {
            UWorld* World = GEditor->GetEditorWorldContext().World();
            if (World)
            {
                return World->GetName();
            }
        }
        return TEXT("Unknown");
    }

    void RefreshActiveSceneLabel()
    {
        const FString ActiveMap = GetActiveMapName();
        if (ActiveSceneText.IsValid())
        {
            ActiveSceneText->SetText(FText::FromString(FString::Printf(TEXT("Aktif sahne: %s"), *ActiveMap)));
        }
        if (SceneNameInput.IsValid())
        {
            const FString CurrentText = SceneNameInput->GetText().ToString();
            if (CurrentText.IsEmpty() && ActiveMap != TEXT("Unknown"))
            {
                SceneNameInput->SetText(FText::FromString(ActiveMap));
            }
        }
    }

    bool AutoBoot(float DeltaTime)
    {
        StartCore();
        Connect();
        if (!Socket)
        {
            FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SUnrealToolsChatPanel::DelayedConnect), 1.5f);
        }
        return false;
    }

    bool DelayedConnect(float DeltaTime)
    {
        if (!Socket)
        {
            Connect();
        }
        return false;
    }

    TSharedRef<SWidget> MakeChip(const FText& Label, const FLinearColor& Color) const
    {
        return SNew(SBorder)
            .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
            .BorderBackgroundColor(Color)
            .Padding(FMargin(9, 4))
            [
                SNew(STextBlock)
                .Text(Label)
                .Font(FCoreStyle::GetDefaultFontStyle("Regular", 9))
                .ColorAndOpacity(FLinearColor(0.82f, 0.88f, 0.96f, 1.0f))
            ];
    }

    TSharedRef<SWidget> MakePresetButton(const FText& Label, const FString Prompt)
    {
        return SNew(SButton)
            .Text(Label)
            .OnClicked_Lambda([this, Prompt]()
            {
                Preset(Prompt);
                return FReply::Handled();
            });
    }

    TSharedRef<SWidget> MakePromptButton(const FText& Label, const FString Prompt)
    {
        return SNew(SButton)
            .Text(Label)
            .OnClicked_Lambda([this, Prompt]()
            {
                AddMessage(TEXT("Sen"), Prompt);
                SendUserMessage(Prompt);
                return FReply::Handled();
            });
    }

    void StartCore()
    {
        if (IsPortOpen(Port))
        {
            SetStatus(TEXT("Core already listening. Connecting..."));
            return;
        }
        if (CoreProcess.IsValid())
        {
            SetStatus(TEXT("Core already running. Connect when ready."));
            return;
        }
        FString WorkingDir = FPaths::ProjectDir();
        FString ProjectDirFull = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir());
        FPlatformMisc::SetEnvironmentVar(TEXT("UNREALTOOLS_ACTIVE_PROJECT"), *ProjectDirFull);
        CoreProcess = FPlatformProcess::CreateProc(*Command, *Arguments, true, false, false, &CorePid, 0, *WorkingDir, nullptr);
        if (CoreProcess.IsValid())
        {
            AddMessage(TEXT("System"), FString::Printf(TEXT("Core started: %s %s"), *Command, *Arguments));
            SetStatus(TEXT("Core starting. Connecting automatically..."));
        }
        else
        {
            AddMessage(TEXT("Error"), TEXT("Core could not start. Check Python PATH or pip install -e ."));
        }
    }

    void StopCore()
    {
        Disconnect();
        if (CoreProcess.IsValid())
        {
            FPlatformProcess::TerminateProc(CoreProcess, true);
            FPlatformProcess::CloseProc(CoreProcess);
            CoreProcess.Reset();
            CorePid = 0;
            AddMessage(TEXT("System"), TEXT("Core stopped."));
        }
    }

    void Connect()
    {
        ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
        TSharedRef<FInternetAddr> Addr = SocketSubsystem->CreateInternetAddr();
        bool bValid = false;
        Addr->SetIp(*Host, bValid);
        Addr->SetPort(Port);
        if (!bValid)
        {
            AddMessage(TEXT("Error"), TEXT("Invalid host."));
            return;
        }
        Socket = SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealToolsChatClient"), false);
        if (!Socket || !Socket->Connect(*Addr))
        {
            AddMessage(TEXT("Error"), TEXT("Python core is not ready yet. It will retry, or press Start Studio."));
            Disconnect();
            return;
        }
        StopReader = false;
        Async(EAsyncExecution::Thread, [this]() { ReadLoop(); });
        SetStatus(TEXT("Connected. Unreal editor context active."));
        AddMessage(TEXT("System"), TEXT("Python core connected. Studio is online."));
    }

    bool IsPortOpen(int32 InPort) const
    {
        ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
        if (!SocketSubsystem)
        {
            return false;
        }
        TSharedRef<FInternetAddr> Addr = SocketSubsystem->CreateInternetAddr();
        bool bValid = false;
        Addr->SetIp(*Host, bValid);
        Addr->SetPort(InPort);
        if (!bValid)
        {
            return false;
        }
        FSocket* Probe = SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealToolsCoreProbe"), false);
        if (!Probe)
        {
            return false;
        }
        const bool bConnected = Probe->Connect(*Addr);
        Probe->Close();
        SocketSubsystem->DestroySocket(Probe);
        return bConnected;
    }

    void Disconnect()
    {
        StopReader = true;
        if (Socket)
        {
            Socket->Close();
            ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);
            Socket = nullptr;
        }
        SetStatus(TEXT("Offline."));
    }

    void ReadLoop()
    {
        TArray<uint8> Pending;
        while (!StopReader && Socket)
        {
            uint32 Size = 0;
            if (!Socket->HasPendingData(Size))
            {
                FPlatformProcess::Sleep(0.03f);
                continue;
            }
            TArray<uint8> Buffer;
            Buffer.SetNumUninitialized(FMath::Min<uint32>(Size, 65536));
            int32 Read = 0;
            if (!Socket->Recv(Buffer.GetData(), Buffer.Num(), Read) || Read <= 0)
            {
                break;
            }
            for (int32 i = 0; i < Read; ++i)
            {
                uint8 Byte = Buffer[i];
                if (Byte == '\n')
                {
                    if (Pending.Num() > 0)
                    {
                        FUTF8ToTCHAR Convert(reinterpret_cast<const ANSICHAR*>(Pending.GetData()), Pending.Num());
                        InboundLines.Enqueue(FString(Convert.Length(), Convert.Get()));
                        Pending.Reset();
                    }
                }
                else
                {
                    Pending.Add(Byte);
                }
            }
        }
        InboundLines.Enqueue(TEXT("{\"type\":\"error\",\"message\":\"Core baglantisi kapandi.\"}"));
    }

    // Paylasilan token: env (UNITYTOOLS_BRIDGE_TOKEN/SECRET/KEY). Chat-server'daki
    // token ile ayni olmali; aksi halde mesajlar reddedilir.
    FString ResolveAuthToken() const
    {
        const TCHAR* Keys[] = { TEXT("UNITYTOOLS_BRIDGE_TOKEN"), TEXT("UNITYTOOLS_SECRET"), TEXT("UNITYTOOLS_KEY") };
        for (const TCHAR* Key : Keys)
        {
            FString V = FPlatformMisc::GetEnvironmentVariable(Key);
            V.TrimStartAndEndInline();
            if (!V.IsEmpty())
            {
                return V;
            }
        }
        return FString();
    }

    void SendUserMessage(const FString& Text)
    {
        TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
        Root->SetStringField(TEXT("type"), TEXT("user_message"));
        Root->SetStringField(TEXT("content"), Text);
        Root->SetStringField(TEXT("unreal_project"), FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()));
        if (!AuthToken.IsEmpty())
        {
            Root->SetStringField(TEXT("token"), AuthToken);
        }
        FString Out;
        TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
        FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
        SendJson(Out);
    }

    void SendJson(const FString& Payload)
    {
        if (!Socket)
        {
            AddMessage(TEXT("Error"), TEXT("Bagli degil."));
            return;
        }
        FString LinePayload = Payload;
        LinePayload.ReplaceInline(TEXT("\r"), TEXT(""));
        LinePayload.ReplaceInline(TEXT("\n"), TEXT(""));
        FString Line = LinePayload + TEXT("\n");
        FTCHARToUTF8 Convert(*Line);
        const uint8* Data = reinterpret_cast<const uint8*>(Convert.Get());
        int32 TotalSent = 0;
        const int32 TotalBytes = Convert.Length();
        while (TotalSent < TotalBytes)
        {
            int32 Sent = 0;
            if (!Socket->Send(Data + TotalSent, TotalBytes - TotalSent, Sent) || Sent <= 0)
            {
                AddMessage(TEXT("Error"), TEXT("Mesaj core'a gonderilemedi."));
                break;
            }
            TotalSent += Sent;
        }
    }

    void HandleLine(const FString& Line)
    {
        TSharedPtr<FJsonObject> Root;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Line);
        if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
        {
            AddMessage(TEXT("Error"), FString::Printf(TEXT("JSON parse hatasi: %s"), *Line));
            return;
        }
        FString Type = Root->GetStringField(TEXT("type"));
        if (Type == TEXT("hello"))
        {
            FString Mode = Root->GetStringField(TEXT("mode"));
            FString Engine = Root->HasField(TEXT("engine_context")) ? Root->GetStringField(TEXT("engine_context")) : TEXT("auto");
            int32 Tools = Root->GetIntegerField(TEXT("tools_loaded"));
            AddMessage(TEXT("System"), FString::Printf(TEXT("Core hazir. Mode=%s, Engine=%s, Tools=%d"), *Mode, *Engine, Tools));
        }
        else if (Type == TEXT("thinking"))
        {
            AddMessage(TEXT("AI"), TEXT("Dusunuyor ve gerekirse Unreal tool cagiracak..."));
        }
        else if (Type == TEXT("tool_call"))
        {
            FString Tool = Root->GetStringField(TEXT("tool"));
            AddMessage(TEXT("Tool"), FString::Printf(TEXT("-> %s"), *Tool));
        }
        else if (Type == TEXT("tool_result"))
        {
            FString Tool = Root->GetStringField(TEXT("tool"));
            bool bOk = Root->HasTypedField<EJson::Boolean>(TEXT("ok")) ? Root->GetBoolField(TEXT("ok")) : true;
            AddMessage(TEXT("Tool"), FString::Printf(TEXT("<- %s %s"), bOk ? TEXT("OK") : TEXT("ERR"), *Tool));
        }
        else if (Type == TEXT("assistant_text"))
        {
            AddMessage(TEXT("UnrealTools AI"), Root->GetStringField(TEXT("content")));
        }
        else if (Type == TEXT("master_thinking") || Type == TEXT("worker_executing") || Type == TEXT("reader_brief"))
        {
            FString Field = Type == TEXT("reader_brief") ? TEXT("brief") : TEXT("message");
            AddMessage(TEXT("Agent"), Root->HasField(Field) ? Root->GetStringField(Field) : Type);
        }
        else if (Type == TEXT("pong"))
        {
            AddMessage(TEXT("System"), TEXT("Pong."));
        }
        else if (Type == TEXT("error"))
        {
            FString Msg = Root->HasField(TEXT("message")) ? Root->GetStringField(TEXT("message")) : TEXT("Bilinmeyen hata");
            AddMessage(TEXT("Error"), Msg);
        }
    }

    void AddMessage(const FString& Speaker, const FString& Text)
    {
        if (!Messages.IsValid())
        {
            return;
        }
        FLinearColor CardColor(0.045f, 0.052f, 0.066f, 1.0f);
        FLinearColor AccentColor(0.48f, 0.56f, 0.68f, 1.0f);
        if (Speaker == TEXT("Sen"))
        {
            CardColor = FLinearColor(0.055f, 0.090f, 0.135f, 1.0f);
            AccentColor = FLinearColor(0.42f, 0.70f, 1.0f, 1.0f);
        }
        else if (Speaker == TEXT("UnrealTools AI") || Speaker == TEXT("AI"))
        {
            CardColor = FLinearColor(0.050f, 0.066f, 0.060f, 1.0f);
            AccentColor = FLinearColor(0.62f, 0.86f, 0.70f, 1.0f);
        }
        else if (Speaker == TEXT("Tool") || Speaker == TEXT("Agent"))
        {
            CardColor = FLinearColor(0.075f, 0.062f, 0.038f, 1.0f);
            AccentColor = FLinearColor(0.95f, 0.72f, 0.36f, 1.0f);
        }
        else if (Speaker == TEXT("Error"))
        {
            CardColor = FLinearColor(0.110f, 0.040f, 0.045f, 1.0f);
            AccentColor = FLinearColor(1.0f, 0.40f, 0.42f, 1.0f);
        }
        Messages->AddSlot()
        .Padding(0, 5)
        [
            SNew(SBorder)
            .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
            .BorderBackgroundColor(CardColor)
            .Padding(10)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [
                    SNew(STextBlock)
                    .Text(FText::FromString(Speaker))
                    .Font(FCoreStyle::GetDefaultFontStyle("Bold", 9))
                    .ColorAndOpacity(AccentColor)
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 5, 0, 0)
                [
                    SNew(STextBlock)
                    .AutoWrapText(true)
                    .Text(FText::FromString(Text))
                    .ColorAndOpacity(FLinearColor(0.88f, 0.91f, 0.96f, 1.0f))
                ]
            ]
        ];
        Messages->ScrollToEnd();
    }

    void SetStatus(const FString& Text)
    {
        if (StatusText.IsValid())
        {
            StatusText->SetText(FText::FromString(Text));
        }
    }
};

static TSharedRef<SDockTab> SpawnUnrealToolsChatTab(const FSpawnTabArgs& Args)
{
    return SNew(SDockTab)
        .TabRole(ETabRole::NomadTab)
        [
            SNew(SUnrealToolsChatPanel)
        ];
}

static void OpenUnrealToolsChatTab()
{
    FGlobalTabmanager::Get()->TryInvokeTab(UnrealToolsChatTabName);
}

static void FillUnrealToolsTopMenu(FMenuBuilder& MenuBuilder)
{
    MenuBuilder.AddMenuEntry(
        LOCTEXT("OpenUnrealToolsAIChatTop", "Open UnrealTools AI Chat"),
        LOCTEXT("OpenUnrealToolsAIChatTopTooltip", "Open the embedded local AI game-studio panel."),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateStatic(&OpenUnrealToolsChatTab))
    );
}

static void FillUnrealToolsToolbar(FToolBarBuilder& ToolbarBuilder)
{
    ToolbarBuilder.AddToolBarButton(
        FUIAction(FExecuteAction::CreateStatic(&OpenUnrealToolsChatTab)),
        NAME_None,
        LOCTEXT("UnrealToolsToolbarLabel", "UnrealTools AI"),
        LOCTEXT("UnrealToolsToolbarTooltip", "Open UnrealTools AI Chat"),
        FSlateIcon()
    );
}

static void AddUnrealToolsMenuEntry(const FName MenuName)
{
    UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(MenuName);
    if (!Menu)
    {
        return;
    }
    FToolMenuSection& Section = Menu->FindOrAddSection(TEXT("UnrealTools"));
    Section.Label = LOCTEXT("UnrealToolsMenu", "UnrealTools");
    Section.AddMenuEntry(
        TEXT("OpenUnrealToolsAIChat"),
        LOCTEXT("OpenUnrealToolsAIChat", "Open UnrealTools AI Chat"),
        LOCTEXT("OpenUnrealToolsAIChatTooltip", "Open the embedded AI chat panel for UnrealTools."),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateStatic(&OpenUnrealToolsChatTab))
    );
}

void FUnrealToolsBridgeModule::StartupModule()
{
    FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
        UnrealToolsChatTabName,
        FOnSpawnTab::CreateStatic(&SpawnUnrealToolsChatTab))
        .SetDisplayName(LOCTEXT("UnrealToolsTabTitle", "UnrealTools AI Chat"))
        .SetTooltipText(LOCTEXT("UnrealToolsTabTooltip", "Local AI autopilot chat for Unreal Editor."))
        .SetMenuType(ETabSpawnerMenuType::Enabled);

    UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateLambda([]()
    {
        AddUnrealToolsMenuEntry(TEXT("LevelEditor.MainMenu.Tools"));
        AddUnrealToolsMenuEntry(TEXT("LevelEditor.MainMenu.Window"));
        AddUnrealToolsMenuEntry(TEXT("LevelEditor.MainMenu.Help"));
    }));

    if (FModuleManager::Get().IsModuleLoaded(TEXT("LevelEditor")) || FModuleManager::Get().ModuleExists(TEXT("LevelEditor")))
    {
        FLevelEditorModule& LevelEditorModule = FModuleManager::LoadModuleChecked<FLevelEditorModule>(TEXT("LevelEditor"));

        MenuExtender = MakeShared<FExtender>();
        MenuExtender->AddMenuBarExtension(
            TEXT("Help"),
            EExtensionHook::After,
            nullptr,
            FMenuBarExtensionDelegate::CreateLambda([](FMenuBarBuilder& MenuBarBuilder)
            {
                MenuBarBuilder.AddPullDownMenu(
                    LOCTEXT("UnrealToolsAITopMenu", "UnrealTools AI"),
                    LOCTEXT("UnrealToolsAITopMenuTooltip", "Open UnrealTools AI game-studio tools."),
                    FNewMenuDelegate::CreateStatic(&FillUnrealToolsTopMenu),
                    TEXT("UnrealToolsAI")
                );
            })
        );
        LevelEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);

        ToolbarExtender = MakeShared<FExtender>();
        ToolbarExtender->AddToolBarExtension(
            TEXT("Settings"),
            EExtensionHook::After,
            nullptr,
            FToolBarExtensionDelegate::CreateStatic(&FillUnrealToolsToolbar)
        );
        LevelEditorModule.GetToolBarExtensibilityManager()->AddExtender(ToolbarExtender);
    }

    FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateLambda([](float)
        {
            OpenUnrealToolsChatTab();
            return false;
        }),
        2.5f
    );

    UE_LOG(LogTemp, Display, TEXT("[UnrealTools] UnrealToolsBridge module loaded. Open from Tools/Window > UnrealTools > Open UnrealTools AI Chat."));
}

void FUnrealToolsBridgeModule::ShutdownModule()
{
    if (FModuleManager::Get().IsModuleLoaded(TEXT("LevelEditor")))
    {
        FLevelEditorModule& LevelEditorModule = FModuleManager::GetModuleChecked<FLevelEditorModule>(TEXT("LevelEditor"));
        if (MenuExtender.IsValid())
        {
            LevelEditorModule.GetMenuExtensibilityManager()->RemoveExtender(MenuExtender);
            MenuExtender.Reset();
        }
        if (ToolbarExtender.IsValid())
        {
            LevelEditorModule.GetToolBarExtensibilityManager()->RemoveExtender(ToolbarExtender);
            ToolbarExtender.Reset();
        }
    }
    if (UToolMenus::IsToolMenuUIEnabled())
    {
        UToolMenus::UnRegisterStartupCallback(this);
    }
    FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(UnrealToolsChatTabName);
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FUnrealToolsBridgeModule, UnrealToolsBridge)
