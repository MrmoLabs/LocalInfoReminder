#ifndef AppVersion
  #error AppVersion must be provided, for example /DAppVersion=1.0.0
#endif

#ifndef GitHubRepository
  #error GitHubRepository must be provided, for example /DGitHubRepository=owner/repo
#endif

#define AppName "Local Info Reminder"
#define AppExeName "LocalInfoReminder.exe"

[Setup]
AppId={{5D02BA93-C9DC-47E9-BB59-F8F82CC6794E}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Local Info Reminder contributors
AppPublisherURL=https://github.com/{#GitHubRepository}
AppSupportURL=https://github.com/{#GitHubRepository}/issues
AppUpdatesURL=https://github.com/{#GitHubRepository}/releases
DefaultDirName={localappdata}\Programs\LocalInfoReminder
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\..\release
OutputBaseFilename=LocalInfoReminder-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\..\assets\LocalInfoReminder.ico
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=yes
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\LocalInfoReminder\*"; DestDir: "{app}"; Excludes: "config.json,logs\*,state\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\LocalInfoReminder\config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
