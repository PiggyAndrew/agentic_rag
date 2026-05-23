@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0.."
set "VUE_DIR=%ROOT%\frontend\agui-vue"
set "ELECTRON_DIR=%ROOT%\frontend\agui-electron"

echo [1/3] Building Vue frontend
pushd "%VUE_DIR%" || (echo Error: Cannot enter %VUE_DIR% & if "%CI%"=="" pause & exit /b 1)
if not exist package.json (echo Error: package.json not found & popd & if "%CI%"=="" pause & exit /b 1)
call npm ci
if errorlevel 1 (echo Error: npm ci failed & popd & if "%CI%"=="" pause & exit /b 1)
call npm run build
if errorlevel 1 (echo Error: Vue build failed & popd & if "%CI%"=="" pause & exit /b 1)
popd

echo [2/3] Building Python backend (cx_Freeze)
pushd "%ROOT%" || (echo Error: Cannot enter %ROOT% & if "%CI%"=="" pause & exit /b 1)
call python setup\setup.py build
if errorlevel 1 (echo Error: Python build failed & popd & if "%CI%"=="" pause & exit /b 1)
popd

echo [3/3] Building Electron installer
pushd "%ELECTRON_DIR%" || (echo Error: Cannot enter %ELECTRON_DIR% & if "%CI%"=="" pause & exit /b 1)
if not exist package.json (echo Error: package.json not found & popd & if "%CI%"=="" pause & exit /b 1)
call npm install
if errorlevel 1 (echo Error: npm install failed & popd & if "%CI%"=="" pause & exit /b 1)
call npm run dist
if errorlevel 1 (echo Error: Electron dist failed & popd & if "%CI%"=="" pause & exit /b 1)
popd

echo Done: Electron installer generated under %ELECTRON_DIR%\release
if "%CI%"=="" pause
exit 0
