@echo off
setlocal enabledelayedexpansion

echo === Installation de MangaMoins-to-PDF ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Installez Python depuis https://www.python.org/downloads/
    echo ^(cochez "Add python.exe to PATH" lors de l'installation^), puis relancez ce script.
    pause
    exit /b 1
)

echo [1/3] Creation de l'environnement virtuel...
python -m venv venv
if errorlevel 1 (
    echo [ERREUR] Impossible de creer l'environnement virtuel.
    pause
    exit /b 1
)

echo [2/3] Installation des dependances de base...
call venv\Scripts\pip.exe install --upgrade pip >nul
call venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] L'installation des dependances a echoue.
    pause
    exit /b 1
)

echo.
echo [3/3] Support navigateur optionnel (fallback si le site bloque le scraping)
echo Cette etape telecharge Chromium ^(~300 Mo^) et n'est utile qu'en cas de probleme.
set /p INSTALL_PLAYWRIGHT="Installer le support navigateur maintenant ? (o/N) "
if /i "!INSTALL_PLAYWRIGHT!"=="o" (
    call venv\Scripts\pip.exe install -r requirements-optional.txt
    call venv\Scripts\python.exe -m playwright install chromium
) else (
    echo Ignore. Vous pourrez l'installer plus tard avec :
    echo   venv\Scripts\pip.exe install -r requirements-optional.txt
    echo   venv\Scripts\python.exe -m playwright install chromium
)

echo.
echo === Installation terminee ===
echo Pour utiliser l'outil :
echo   venv\Scripts\python.exe main.py OP1188
echo.
pause
