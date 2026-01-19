@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

REM Build and Package Automation Script
REM Steps:
REM 1) Clean WPF bin directory
REM 2) Build Vue project
REM 3) Build Python backend
REM 4) Build WPF project
REM 5) Copy dist to WPF directory
REM 6) Compile Inno Setup installer

REM Directory Variables
set "ROOT=%~dp0.."
set "VUE_DIR=%ROOT%\frontend\agui-vue"
set "WPF_PROJECT_DIR=%ROOT%\frontend\agui-wpf\AGUI.WPF"
set "WPF_BIN_DIR=%WPF_PROJECT_DIR%\bin"
set "WPF_OUTPUT_DIR=%WPF_BIN_DIR%\Release\net8.0-windows"
set "ISS_PATH=%ROOT%\setup\installer.iss"

REM Step 1: Clean WPF bin directory
echo [1/6] Cleaning WPF bin directory: %WPF_BIN_DIR%
if exist "%WPF_BIN_DIR%" (
    rmdir /s /q "%WPF_BIN_DIR%"
    if errorlevel 1 (
        echo Error: Failed to clean WPF bin directory
        if "%CI%"=="" pause
        exit /b 1
    )
)

REM Step 2: Build Frontend
echo [2/6] Building Frontend: %VUE_DIR%
pushd "%VUE_DIR%" || (echo Error: Cannot enter directory %VUE_DIR% & if "%CI%"=="" pause & exit /b 1)
if not exist package.json (
  echo Error: package.json not found
  popd
  if "%CI%"=="" pause
  exit /b 1
)
call npm run build
if errorlevel 1 (
  echo Error: Frontend build failed
  popd
  if "%CI%"=="" pause
  exit /b 1
)
popd

REM Step 3: Build Python backend (cx_Freeze)
echo [3/6] Building Python backend: %ROOT%\setup\setup.py
pushd "%ROOT%" || (echo Error: Cannot enter directory %ROOT% & if "%CI%"=="" pause & exit /b 1)
rem Prefer using uv virtual environment if available
where uv >nul 2>&1
if not errorlevel 1 (
  if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
  ) else (
    uv venv
    if errorlevel 1 (
      echo Error: Failed to create uv virtual environment
      popd
      if "%CI%"=="" pause
      exit /b 1
    )
    if exist ".venv\Scripts\activate.bat" (
      call ".venv\Scripts\activate.bat"
    ) else (
      echo Error: uv venv activation script not found
      popd
      if "%CI%"=="" pause
      exit /b 1
    )
  )
)
where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo Error: Python not found in PATH
    popd
    if "%CI%"=="" pause
    exit /b 1
  ) else (
    py -3 setup\setup.py build
  )
) else (
  python setup\setup.py build
)
if errorlevel 1 (
  echo Error: Python backend build failed
  popd
  if "%CI%"=="" pause
  exit /b 1
)
popd

REM Step 4: Build WPF Project
echo [4/6] Building WPF Project: %WPF_PROJECT_DIR%
pushd "%WPF_PROJECT_DIR%" || (echo Error: Cannot enter directory %WPF_PROJECT_DIR% & if "%CI%"=="" pause & exit /b 1)
dotnet build -c Release
if errorlevel 1 (
    echo Error: WPF build failed
    popd
    if "%CI%"=="" pause
    exit /b 1
)
popd

REM Step 5: Copy artifacts to WPF directory (dist + backend)
echo [5/6] Copying frontend dist and backend to WPF: %WPF_OUTPUT_DIR%
if not exist "%VUE_DIR%\dist" (
  echo Error: Build output dist not found
  if "%CI%"=="" pause
  exit /b 1
)
REM Ensure target directory exists (it should after WPF build)
if not exist "%WPF_OUTPUT_DIR%" (
  mkdir "%WPF_OUTPUT_DIR%"
)

if not exist "%WPF_OUTPUT_DIR%\dist" mkdir "%WPF_OUTPUT_DIR%\dist"
robocopy "%VUE_DIR%\dist" "%WPF_OUTPUT_DIR%\dist" /E /PURGE
set "ROBO_EXIT=%ERRORLEVEL%"
REM Robocopy exit codes < 8 are success
if %ROBO_EXIT% GEQ 8 (
    echo Error: Robocopy dist failed with code %ROBO_EXIT%
    if "%CI%"=="" pause
    exit /b 1
)

REM Copy Python build output (exe + libs) without purge
set "PY_BUILD=%ROOT%\build"
set "PY_EXE_DIR="
for /d %%D in ("%PY_BUILD%\exe.win-amd64-*") do (
  set "PY_EXE_DIR=%%~fD"
)
if defined PY_EXE_DIR (
  echo Copying Python backend from %PY_EXE_DIR% to %WPF_OUTPUT_DIR%
  robocopy "%PY_EXE_DIR%" "%WPF_OUTPUT_DIR%" /E
  set "ROBO_EXIT2=%ERRORLEVEL%"
  if !ROBO_EXIT2! GEQ 8 (
      echo Error: Robocopy backend failed with code !ROBO_EXIT2!
      if "%CI%"=="" pause
      exit /b 1
  )
) else (
  echo Warning: Python build output directory not found under %PY_BUILD%
)

REM Step 6: Compile Installer
echo [6/6] Compiling Installer: %ISS_PATH%
set "ISCC_X64=C:\Program Files\Inno Setup 6\ISCC.exe"
set "ISCC_X86=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%ISCC_X64%" (
  set "ISCC=%ISCC_X64%"
) else if exist "%ISCC_X86%" (
  set "ISCC=%ISCC_X86%"
) else (
  where ISCC.exe >nul 2>&1
  if errorlevel 1 (
    echo Error: Inno Setup compiler ISCC.exe not found. Please install Inno Setup 6 or add ISCC.exe to PATH.
    if "%CI%"=="" pause
    exit /b 1
  ) else (
    set "ISCC=ISCC.exe"
  )
)

pushd "%ROOT%" || (echo Error: Cannot enter directory %ROOT% & if "%CI%"=="" pause & exit /b 1)
"%ISCC%" "%ISS_PATH%"
set "ISCC_EXIT=%ERRORLEVEL%"
popd

if not "%ISCC_EXIT%"=="0" (
  echo Error: Installer compilation failed (Exit code %ISCC_EXIT%)
  if "%CI%"=="" pause
  exit /b %ISCC_EXIT%
)

echo Done: Installer generated successfully.
if "%CI%"=="" pause
exit 0
