@echo off
setlocal

set NAME=WeltenWandler Companion
set ICON=assets\icon.ico
set ENTRY=main.py
set DISTDIR=%~dp0release

echo ========================================
echo  WRT Companion App - Build
echo ========================================
echo.

:: Alte Build-Artefakte loeschen
if exist "%DISTDIR%\%NAME%" (
    echo Loesche alten Build...
    rmdir /s /q "%DISTDIR%\%NAME%" 2>nul
    timeout /t 2 /nobreak >nul
)
if exist "build" (
    rmdir /s /q "build" 2>nul
)

echo Starte PyInstaller...
echo.

.venv\Scripts\pyinstaller.exe ^
  --name "%NAME%" ^
  --windowed ^
  --onedir ^
  --icon="%ICON%" ^
  --add-data "assets;assets" ^
  --hidden-import=pywebview.platforms.qt ^
  --hidden-import=pystray._win32 ^
  --hidden-import=PyQt6.QtWebEngineWidgets ^
  --hidden-import=PyQt6.QtWebEngineCore ^
  --hidden-import=PyQt6.QtWebChannel ^
  --hidden-import=PyQt6.QtNetwork ^
  --collect-all pywebview ^
  --collect-all PyQt6 ^
  --distpath "%DISTDIR%" ^
  --noconfirm ^
  "%ENTRY%"

if %ERRORLEVEL% NEQ 0 (
    echo ========================================
    echo  Build FEHLGESCHLAGEN! Fehlercode: %ERRORLEVEL%
    echo ========================================
    echo.
    pause
    exit /b 1
)

echo ========================================
echo  Build erfolgreich! Starte Inno Setup...
echo ========================================
echo.

:: Inno Setup Compiler (Standard-Installationspfad)
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist %ISCC% (
    echo FEHLER: Inno Setup nicht gefunden unter %ISCC%
    echo Bitte installer.iss manuell mit Inno Setup kompilieren.
    echo.
    pause
    exit /b 1
)

%ISCC% installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo  Installer erfolgreich erstellt!
    echo  Ausgabe: installer\
    echo ========================================
) else (
    echo.
    echo ========================================
    echo  Installer-Build FEHLGESCHLAGEN!
    echo ========================================
)

echo.
pause
endlocal
