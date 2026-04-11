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
  --collect-all pywebview ^
  --distpath "%DISTDIR%" ^
  --noconfirm ^
  "%ENTRY%"

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo  Build erfolgreich!
    echo  Ausgabe: dist\%NAME%\
    echo ========================================
) else (
    echo ========================================
    echo  Build FEHLGESCHLAGEN! Fehlercode: %ERRORLEVEL%
    echo ========================================
)

echo.
pause
endlocal
