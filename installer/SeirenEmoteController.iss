#define MyAppName "Seiren Emote Controller"
#define MyAppVersion "1.0.0"
#define MyAppExeName "SeirenEmoteController.exe"
[Setup]
AppId={{D2183FF9-7433-495F-A0C5-2A7E84268E7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\SeirenEmoteController
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputBaseFilename=SeirenEmoteController_Setup_{#MyAppVersion}
OutputDir=..\release
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible
AppPublisher=Seiren Emote Controller community
AppPublisherURL=https://github.com/EudoksjuszSzalony/Razer-Seiren-Emote-Controller
AppSupportURL=https://github.com/EudoksjuszSzalony/Razer-Seiren-Emote-Controller/issues
AppUpdatesURL=https://github.com/EudoksjuszSzalony/Razer-Seiren-Emote-Controller/releases
SetupIconFile=..\build_assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
[Tasks]
Name: "autostart"; Description: "Start automatically when I sign in"; GroupDescription: "Additional options:"; Flags: unchecked
[Files]
Source: "..\dist\SeirenEmoteController\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName} (Tray)"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--tray"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Seiren Emote Controller"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SeirenEmoteController"; ValueData: """{app}\{#MyAppExeName}"" --tray"; Tasks: autostart; Flags: uninsdeletevalue

[Code]
// Autostart may be changed from the tray after installation. The uninstaller
// should still remove the obsolete HKCU Run value, not leave a broken shortcut.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'SeirenEmoteController');
end;
