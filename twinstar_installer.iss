; TwinStar Quantum Trading Bot 설치 스크립트
; Inno Setup 6.0 이상 필요

#define MyAppName "TwinStar Quantum"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TwinStar Trading"
#define MyAppURL "https://your-website.com"
#define MyAppExeName "TwinStar_Quantum.exe"

[Setup]
; 고유 ID (변경하지 마세요)
AppId={{8F9A2B3C-4D5E-6F7A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\TwinStar
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=TwinStar_Quantum_Setup_v{#MyAppVersion}
; SetupIconFile=GUI\assets\icon.ico
Compression=lzma
SolidCompression=no
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\TwinStar_Quantum\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TwinStar_Quantum\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Dirs]
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\user"; Permissions: users-full
Name: "{app}\config"; Permissions: users-full
Name: "{app}\cache"; Permissions: users-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// 설치 전 이전 버전 체크
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UninstallString: String;
begin
  if RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8F9A2B3C-4D5E-6F7A-8B9C-0D1E2F3A4B5C}_is1',
    'UninstallString', UninstallString) then
  begin
    if MsgBox('이전 버전이 이미 설치되어 있습니다.' + #13#10 + '기존 버전을 제거하고 새로 설치하시겠습니까?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec(RemoveQuotes(UninstallString), '/SILENT', '', SW_HIDE, 
           ewWaitUntilTerminated, ResultCode);
    end;
  end;
  Result := True;
end;

// 삭제 시 사용자 데이터 처리 (JSON, cache 제외)
procedure CurUninstallStepChanged(UninstallStep: TUninstallStep);
begin
  if UninstallStep = usPostUninstall then
  begin
    // 로그 삭제 여부만 확인 (JSON/cache는 보존)
    if MsgBox('매매 로그(logs) 폴더를 삭제하시겠습니까?' + #13#10 + #13#10 + 
              '※ API 키, 프리셋(JSON), 수집된 데이터(cache)는 보존됩니다.' + #13#10 +
              '(아니오를 선택하면 로그도 유지됩니다)', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 로그만 삭제
      DelTree(ExpandConstant('{app}\logs'), True, True, True);
    end;
    
    // 안내 메시지
    MsgBox('삭제 완료!' + #13#10 + #13#10 + 
           '다음 데이터가 보존되었습니다:' + #13#10 +
           '- config/ : API 키, 설정' + #13#10 +
           '- user/ : 프리셋, 사용자 설정' + #13#10 +
           '- cache/ : 수집된 가격 데이터' + #13#10 + #13#10 +
           '완전 삭제를 원하시면 수동으로 폴더를 삭제해주세요:' + #13#10 +
           ExpandConstant('{app}'),
           mbInformation, MB_OK);
  end;
end;
