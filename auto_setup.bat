@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

REM Build and Package Automation Script
REM Steps:
REM 1) Build Vue project
REM 2) Copy dist to WPF directory
REM 3) Compile Inno Setup installer

REM Directory Variables
set "ROOT=D:\Gitspace\agentic_rag"
set "VUE_DIR=%ROOT%\web\agui-vue"
set "WPF_DIR=%ROOT%\web\agui-wpf\AGUI.WPF\bin\Release\net8.0-windows"
set "ISS_PATH=%ROOT%\installer.iss"

REM Step 1: Build Frontend
echo [1/3] Building Frontend: %VUE_DIR%
pushd "%VUE_DIR%" || (echo Error: Cannot enter directory %VUE_DIR% & pause & exit /b 1)
if not exist package.json (
  echo Error: package.json not found
  popd
  pause
  exit /b 1
)
call npm run build
if errorlevel 1 (
  echo Error: Frontend build failed
  popd
  pause
  exit /b 1
)
popd

REM Step 2: Build Python backend (cx_Freeze)
echo [2/4] Building Python backend: %ROOT%\setup.py
pushd "%ROOT%" || (echo Error: Cannot enter directory %ROOT% & pause & exit /b 1)
where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo Error: Python not found in PATH
    popd
    pause
    exit /b 1
  ) else (
    py -3 setup.py build
  )
) else (
  python setup.py build
)
if errorlevel 1 (
  echo Error: Python backend build failed
  popd
  pause
  exit /b 1
)
popd

REM Step 3: Copy artifacts to WPF directory (dist + backend)
echo [3/4] Copying frontend dist and backend to WPF: %WPF_DIR%
if not exist "%VUE_DIR%\dist" (
  echo Error: Build output dist not found
  pause
  exit /b 1
)
if not exist "%WPF_DIR%" (
  echo Error: WPF target directory not found: %WPF_DIR%
  pause
  exit /b 1
)
if not exist "%WPF_DIR%\dist" mkdir "%WPF_DIR%\dist"
robocopy "%VUE_DIR%\dist" "%WPF_DIR%\dist" /E /PURGE
set "ROBO_EXIT=%ERRORLEVEL%"
echo Robocopy dist exit code: %ROBO_EXIT%

REM Copy Python build output (exe + libs) without purge
set "PY_BUILD=%ROOT%\build\exe.win-amd64-3.13"
if exist "%PY_BUILD%" (
  echo Copying Python backend from %PY_BUILD% to %WPF_DIR%
  robocopy "%PY_BUILD%" "%WPF_DIR%" /E
  set "ROBO_EXIT2=%ERRORLEVEL%"
  echo Robocopy backend exit code: %ROBO_EXIT2%
) else (
  echo Warning: Python build output not found: %PY_BUILD%
)

REM Step 4: Compile Installer
echo [4/4] Compiling Installer: %ISS_PATH%
set "ISCC_X86=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "ISCC_X64=C:\Program Files\Inno Setup 6\ISCC.exe"
set "ISCC=%ISCC_X64%"
if exist "%ISCC_X86%" set "ISCC=%ISCC_X86%"
if exist "%ISCC_X64%" set "ISCC=%ISCC_X64%"

if not exist "%ISCC%" (
  where ISCC.exe >nul 2>&1
  if errorlevel 1 (
    echo Error: Inno Setup compiler ISCC.exe not found. Please install Inno Setup 6.
    pause
    exit /b 1
  ) else (
    set "ISCC=ISCC.exe"
  )
)

pushd "%ROOT%" || (echo Error: Cannot enter directory %ROOT% & pause & exit /b 1)
"%ISCC%" "%ISS_PATH%"
set "ISCC_EXIT=%ERRORLEVEL%"
popd

if not "%ISCC_EXIT%"=="0" (
  echo Error: Installer compilation failed (Exit code %ISCC_EXIT%)
  pause
  exit /b %ISCC_EXIT%
)

echo Done: Installer generated successfully.
pause
exit  0
