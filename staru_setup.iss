; TwinStar Quantum Inno Setup Script
; Requires Inno Setup 6.0 or later

#define MyAppName "TwinStar Quantum"
#define MyAppVersion "1.1.9"
#define MyAppPublisher "YoungStreet"
#define MyAppURL "https://youngstreet.co.kr"
#define MyAppExeName "TwinStar_Quantum.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".tsq"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{A1B2C3D4-E5F6-7890-1234-567890ABCDEF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\{#MyAppName}
UsePreviousAppDir=no
; "ArchitecturesAllowed=x64compatible" specifies that Setup cannot run
; on anything but x64 and Windows 11 on Arm.
ArchitecturesAllowed=x64compatible
; "ArchitecturesInstallIn64BitMode=x64compatible" requests that the
; install be done in "64-bit mode" on x64 or Windows 11 on Arm,
; meaning that {app} is the native 64-bit Program Files directory and
; the 64-bit view of the registry is used.
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
OutputDir=C:\매매전략\dist
OutputBaseFilename=TwinStar_Quantum_Setup_v{#MyAppVersion}
;SetupIconFile=C:\매매전략\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\매매전략\dist\TwinStar_Quantum\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\매매전략\dist\TwinStar_Quantum\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Dirs]
Name: "{app}\config"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\data"; Permissions: users-modify
