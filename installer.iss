#define AppName "WeltenWandler Companion"
#define AppVersion "1.0.4"
#define AppPublisher "WeltenWandler"
#define AppExeName "WeltenWandler Companion.exe"
#define BuildDir "release\WeltenWandler Companion"

[Setup]
AppId={{A7F3B2D1-4E6C-4A8F-9B2E-1D3C5F7A9E0B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://weltenwandler.cloud
AppSupportURL=https://weltenwandler.cloud
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=WeltenWandler-Companion-Setup-v{#AppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Aufgaben:"; Flags: unchecked
Name: "startupicon"; Description: "Beim Windows-Start automatisch starten"; GroupDescription: "Zusätzliche Aufgaben:"; Flags: unchecked

[Files]
Source: "{#BuildDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BuildDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "WRT Companion"; ValueData: """{app}\{#AppExeName}"" --tray"; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{#AppName} jetzt starten"; Flags: nowait postinstall

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/f /im ""{#AppExeName}"""; Flags: runhidden; RunOnceId: "KillApp"

[InstallDelete]
; Alte _internal-Inhalte bereinigen bevor neue Dateien kopiert werden
Type: filesandordirs; Name: "{app}\_internal"

[Code]
// Laufende Instanz vor dem Upgrade beenden
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
    Exec('taskkill.exe', '/f /im "WeltenWandler Companion.exe"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Config-Verzeichnis optional löschen
    if MsgBox('Möchtest du die gespeicherten Einstellungen ebenfalls löschen?', mbConfirmation, MB_YESNO) = IDYES then
      DelTree(ExpandConstant('{userappdata}\WeltenWandler'), True, True, True);
  end;
end;
