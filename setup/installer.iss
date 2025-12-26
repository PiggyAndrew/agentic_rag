[Setup]
AppId=AgenticRAG
AppName=Agentic RAG
AppVersion=1.0.0
DefaultDirName={code:GetDefaultDirForMode}
DisableDirPage=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x86 x64
ArchitecturesInstallIn64BitMode=x64
Compression=lzma
SolidCompression=yes
OutputBaseFilename=Agentic_RAG_Installer
SetupLogging=yes
UsePreviousAppDir=yes
AppMutex=AgenticRAGMutex
DefaultGroupName=Agentic RAG
DisableProgramGroupPage=yes
SetupIconFile=assets\icons\appIcon.ico

[Files]
Source: "web\agui-wpf\AGUI.WPF\bin\Release\net8.0-windows\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "assets\icons\appIcon.ico"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{commondesktop}\Agentic RAG"; Filename: "{app}\AGUI.WPF.exe"; WorkingDir: "{app}"; IconFilename: "{app}\appIcon.ico"; Check: IsAdminInstallMode
Name: "{userdesktop}\Agentic RAG"; Filename: "{app}\AGUI.WPF.exe"; WorkingDir: "{app}"; IconFilename: "{app}\appIcon.ico"; Check: not IsAdminInstallMode
Name: "{group}\Agentic RAG"; Filename: "{app}\AGUI.WPF.exe"; WorkingDir: "{app}"; IconFilename: "{app}\appIcon.ico"


[Code]
function IsSystemDir(Dir: string): Boolean;
var
  pf, pf32, pf64, windir: string;
begin
  pf := ExpandConstant('{pf}');
  pf32 := ExpandConstant('{pf32}');
  pf64 := ExpandConstant('{pf64}');
  windir := ExpandConstant('{win}');

  Dir := LowerCase(AddBackslash(Dir));
  pf := LowerCase(AddBackslash(pf));
  pf32 := LowerCase(AddBackslash(pf32));
  pf64 := LowerCase(AddBackslash(pf64));
  windir := LowerCase(AddBackslash(windir));

  Result := (Pos(pf, Dir) = 1) or (Pos(pf32, Dir) = 1) or (Pos(pf64, Dir) = 1) or (Pos(windir, Dir) = 1);
end;

// 函数：根据当前安装模式返回默认安装目�?
// 说明：作�?{code:GetDefaultDirForMode} 的实现，必须接受一�?string 参数（可忽略�?
function GetDefaultDirForMode(Param: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{pf}\Agentic RAG')
  else
    Result := ExpandConstant('{userappdata}\Agentic RAG');
end;

// 鍑芥暟锛氬湪鐩綍閫夋嫨椤电偣鍑烩€滀笅涓€姝モ€濇椂鏍￠獙鐩綍
// 浣滅敤锛氬己鍒跺畨瑁呭埌鐢ㄦ埛鐩綍锛岄伩鍏嶅啓鍏ョ郴缁熺洰褰曞鑷寸殑鏉冮檺鎻愮ず
function NextButtonClick(CurPageID: Integer): Boolean;
var
  defDir: string;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    // 闈炵鐞嗗憳妯″紡涓嬬姝㈤€夋嫨绯荤粺鐩綍锛涚鐞嗗憳妯″紡鍏佽锛堜负鎵€鏈変汉瀹夎锟?
    if not IsAdminInstallMode then
    begin
      defDir := ExpandConstant('{userappdata}\Agentic RAG');
      if IsSystemDir(WizardDirValue) then
      begin
        MsgBox('To install for all users, administrator privileges are required. Switched to user directory for a per-user install.', mbInformation, MB_OK);
        WizardForm.DirEdit.Text := defDir;
        Result := False; // 鐣欏湪褰撳墠椤碉紝鎻愮ず鐢ㄦ埛纭
      end;
    end;
  end;
end;

// 鍑芥暟锛氬畨瑁呭垵濮嬪寲鏃惰缃粯璁ょ洰褰曪紙淇濋殰榛樿瀹夎鏃犳潈闄愭彁绀猴級
// 浣滅敤锛氬皢榛樿瀹夎鐩綍璁句负鐢ㄦ埛鐩綍锛屼互瑙勯�?UAC
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// 鏃х増鏈嵏杞芥敮�?
// 璇存槑锛氬湪瀹夎寮€濮嬪墠锛岃嫢妫€娴嬪埌鏃х増鏈紝闈欓粯鍗歌浇浠ラ伩鍏嶉噸澶嶅畨瑁呴€犳垚鐨勬枃浠舵畫锟?
const UninstKeyCU = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\AgenticRAG_is1';
const UninstKeyLM = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\AgenticRAG_is1';

// 鑾峰彇鍗歌浇鍛戒护锟?
function GetUninstallString(var UninstStr: string): Boolean;
begin
  if RegQueryStringValue(HKCU, UninstKeyCU, 'UninstallString', UninstStr) then
  begin
    Result := True; Exit;
  end;
  if RegQueryStringValue(HKLM, UninstKeyLM, 'UninstallString', UninstStr) then
  begin
    Result := True; Exit;
  end;
  Result := False;
end;

// �?UninstallString 鎻愬彇鍙墽琛屾枃浠惰矾�?
function ExtractUninstExe(UninstStr: string): string;
var p: Integer;
begin
  UninstStr := Trim(UninstStr);
  if (Length(UninstStr) > 0) and (UninstStr[1] = '"') then
  begin
    Delete(UninstStr, 1, 1);
    p := Pos('"', UninstStr);
    if p > 0 then
      Result := Copy(UninstStr, 1, p - 1)
    else
      Result := UninstStr;
  end
  else
  begin
    p := Pos('.exe', LowerCase(UninstStr));
    if p > 0 then
      Result := Copy(UninstStr, 1, p + 4)
    else
      Result := UninstStr;
  end;
end;

// 璇㈤棶鐢ㄦ埛鏄惁鍗歌浇鏃х増鏈紙闈為潤榛橈�?
procedure InitializeWizard();
var UninstStr, UninstExe: string; Code: Integer;
begin
  // 鏍规嵁瀹夎妯″紡璁剧疆榛樿鐩綍锛氱鐞嗗憳妯″紡涓烘墍鏈変汉瀹夎锛屾櫘閫氭ā寮忎负褰撳墠鐢ㄦ埛瀹夎�?
  WizardForm.DirEdit.Text := GetDefaultDirForMode('');

  if GetUninstallString(UninstStr) then
  begin
    if MsgBox('A previous version of Agentic RAG is installed. Uninstall it now?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      UninstExe := ExtractUninstExe(UninstStr);
      if FileExists(UninstExe) then
      begin
        // 鎵ц鍗歌浇绋嬪簭锛屾樉绀虹晫闈紝鐢辩敤鎴风‘锟?
        ShellExec('', UninstExe, '', '', SW_SHOWNORMAL, ewWaitUntilTerminated, Code);
      end;
    end;
  end;
end;
