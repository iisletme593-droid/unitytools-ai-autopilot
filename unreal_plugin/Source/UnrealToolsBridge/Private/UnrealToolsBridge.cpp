#include "UnrealToolsBridge.h"

#include "Async/Async.h"
#include "Containers/Queue.h"
#include "Containers/Ticker.h"
#include "Framework/Docking/TabManager.h"
#include "Framework/MultiBox/MultiBoxBuilder.h"
#include "Interfaces/IMainFrameModule.h"
#include "Json.h"
#include "LevelEditor.h"
#include "Misc/Paths.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Styling/CoreStyle.h"
#include "ToolMenus.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
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
        Command = TEXT("python");
        Arguments = TEXT("-m unitytools.cli.entry chat-server --use-dual-agent --engine unreal");

        ChildSlot
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight().Padding(10, 8)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [
                    SNew(STextBlock)
                    .Text(LOCTEXT("Title", "UnrealTools AI Chat"))
                    .Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
                [
                    SAssignNew(StatusText, STextBlock)
                    .Text(LOCTEXT("StatusOff", "Kapali - Core baslat veya baglan"))
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(10, 0)
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                [
                    SNew(SButton)
                    .Text(LOCTEXT("Connect", "Baglan"))
                    .OnClicked(this, &SUnrealToolsChatPanel::OnConnectClicked)
                ]
                + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                [
                    SNew(SButton)
                    .Text(LOCTEXT("StartCore", "Core Baslat"))
                    .OnClicked(this, &SUnrealToolsChatPanel::OnStartCoreClicked)
                ]
                + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                [
                    SNew(SButton)
                    .Text(LOCTEXT("StopCore", "Core Durdur"))
                    .OnClicked(this, &SUnrealToolsChatPanel::OnStopCoreClicked)
                ]
                + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                [
                    SNew(SButton)
                    .Text(LOCTEXT("PingUnreal", "Unreal Ping"))
                    .OnClicked(this, &SUnrealToolsChatPanel::OnPingClicked)
                ]
                + SHorizontalBox::Slot().FillWidth(1.0f)
                [
                    SNew(STextBlock)
                    .Text(LOCTEXT("Hint", "127.0.0.1:7778 -> Python core, 8777 -> Unreal bridge"))
                    .Justification(ETextJustify::Right)
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(10, 8)
            [ SNew(SSeparator) ]
            + SVerticalBox::Slot().FillHeight(1.0f).Padding(10, 0)
            [
                SAssignNew(Messages, SScrollBox)
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(10, 8)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [
                    SAssignNew(Input, SMultiLineEditableTextBox)
                    .HintText(LOCTEXT("InputHint", "Ornek: Bu leveldaki actorlari listele, 5 cube olustur, /Game assetlerinden tree ara"))
                    .AutoWrapText(true)
                    .AllowMultiLine(true)
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("Send", "Gonder"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnSendClicked)
                    ]
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("Actors", "Actorlari Listele"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnListActorsClicked)
                    ]
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("Assets", "Asset Katalog"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnAssetCatalogClicked)
                    ]
                    + SHorizontalBox::Slot().AutoWidth()
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("Clear", "Temizle"))
                        .OnClicked(this, &SUnrealToolsChatPanel::OnClearClicked)
                    ]
                ]
            ]
        ];

        AddMessage(TEXT("System"), TEXT("UnrealTools hazir. Once Core Baslat, sonra Baglan."));
        TickerHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SUnrealToolsChatPanel::ProcessInbound), 0.1f);
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
    TSharedPtr<SScrollBox> Messages;
    TSharedPtr<SMultiLineEditableTextBox> Input;
    TSharedPtr<STextBlock> StatusText;
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

    void StartCore()
    {
        if (CoreProcess.IsValid())
        {
            AddMessage(TEXT("System"), TEXT("Core zaten bu panel tarafindan calisiyor."));
            return;
        }
        FString WorkingDir = FPaths::ProjectDir();
        CoreProcess = FPlatformProcess::CreateProc(*Command, *Arguments, true, false, false, &CorePid, 0, *WorkingDir, nullptr);
        if (CoreProcess.IsValid())
        {
            AddMessage(TEXT("System"), FString::Printf(TEXT("Core baslatildi: %s %s"), *Command, *Arguments));
            SetStatus(TEXT("Core basliyor; birkac saniye sonra Baglan."));
        }
        else
        {
            AddMessage(TEXT("Error"), TEXT("Core baslatilamadi. Python PATH veya unitytools install kontrol et."));
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
            AddMessage(TEXT("System"), TEXT("Core durduruldu."));
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
            AddMessage(TEXT("Error"), TEXT("Host gecersiz."));
            return;
        }
        Socket = SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealToolsChatClient"), false);
        if (!Socket || !Socket->Connect(*Addr))
        {
            AddMessage(TEXT("Error"), TEXT("Python core baglantisi yok. Core Baslat ve tekrar Baglan."));
            Disconnect();
            return;
        }
        StopReader = false;
        Async(EAsyncExecution::Thread, [this]() { ReadLoop(); });
        SetStatus(TEXT("Bagli - Unreal editor context aktif"));
        AddMessage(TEXT("System"), TEXT("Python core baglandi."));
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
        SetStatus(TEXT("Kapali"));
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

    void SendUserMessage(const FString& Text)
    {
        TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
        Root->SetStringField(TEXT("type"), TEXT("user_message"));
        Root->SetStringField(TEXT("content"), Text);
        FString Out;
        TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
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
        FString Line = Payload + TEXT("\n");
        FTCHARToUTF8 Convert(*Line);
        int32 Sent = 0;
        Socket->Send(reinterpret_cast<const uint8*>(Convert.Get()), Convert.Length(), Sent);
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
        FString Full = FString::Printf(TEXT("%s: %s"), *Speaker, *Text);
        Messages->AddSlot()
        .Padding(0, 3)
        [
            SNew(SBorder)
            .Padding(8)
            [
                SNew(STextBlock)
                .AutoWrapText(true)
                .Text(FText::FromString(Full))
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
