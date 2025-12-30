; TwinStar Quantum Inno Setup Script
; Run with Inno Setup Compiler

#define MyAppName "TwinStar Quantum"
#define MyAppVersion "1.5.7"
#define MyAppPublisher "TwinStar"
#define MyAppExeName "TwinStar_Quantum.exe"

[Setup]
AppId={{B5445C72-197F-4147-920C-60DBC24899B0}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName=C:\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=C:\매매전략\installer
OutputBaseFilename=TwinStar_Quantum_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\매매전략\dist\TwinStar_Quantum\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function GetUninstallString(): String;
var
  sUninstPath: String;
  sUninstString: String;
begin
  sUninstPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{B5445C72-197F-4147-920C-60DBC24899B0}_is1';
  sUninstString := '';
  if not RegQueryStringValue(HKLM, sUninstPath, 'UninstallString', sUninstString) then
    RegQueryStringValue(HKCU, sUninstPath, 'UninstallString', sUninstString);
  Result := sUninstString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function InitializeSetup(): Boolean;
var
  iResultCode: Integer;
  sUninstString: String;
begin
  Result := True;
  if IsUpgrade() then
  begin
    sUninstString := GetUninstallString();
    sUninstString := RemoveQuotes(sUninstString);
    if Exec(sUninstString, '/SILENT /VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
    begin
      // Uninstalled successfully
    end;
  end;
end;
