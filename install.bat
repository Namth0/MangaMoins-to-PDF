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
call venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
call venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] L'installation des dependances a echoue.
    pause
    exit /b 1
)

echo.
echo [3/3] Support navigateur (Playwright)
echo MangaMoins bloque l'acces direct aux images : ce module est
echo necessaire pour telecharger la plupart des chapitres aujourd'hui.
echo Cette etape telecharge Chromium ^(~300 Mo^), recommandee.
set /p INSTALL_PLAYWRIGHT="Installer le support navigateur maintenant ? (O/n) "
if /i not "!INSTALL_PLAYWRIGHT!"=="n" (
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
