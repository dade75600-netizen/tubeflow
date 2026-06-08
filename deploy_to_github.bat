@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===================================================
2: echo   TUBEFLOW - AUTOMATIC GITHUB CLOUD DEPLOYMENT
echo ===================================================
echo.
echo Per pubblicare i video nel cloud in automatico, dobbiamo
echo caricare questo progetto su GitHub.
echo.
echo 1. Crea un Token di Accesso Personale (Classic PAT) su GitHub:
echo    Sito: https://github.com/settings/tokens
echo    Permessi necessari (scopes): spunta "repo" (tutto il blocco).
echo.

set /p GH_USER="Inserisci il tuo username di GitHub: "
set /p GH_TOKEN="Inserisci il tuo Personal Access Token (PAT): "

if "%GH_USER%"=="" goto error
if "%GH_TOKEN%"=="" goto error

echo.
echo [1/3] Creazione del repository privato "tubeflow" su GitHub in corso...
curl -H "Authorization: token %GH_TOKEN%" https://api.github.com/user/repos -d "{\"name\":\"tubeflow\",\"private\":true}" > temp_repo_res.json 2>nul

echo [2/3] Configurazione remota di Git con credenziali sicure...
git remote remove origin >nul 2>&1
git remote add origin https://%GH_USER%:%GH_TOKEN%@github.com/%GH_USER%/tubeflow.git

echo [3/3] Caricamento del progetto su GitHub (git push)...
git branch -M main
git push -u origin main --force

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Il caricamento su GitHub e fallito.
    echo Verifica il tuo username, il tuo Token e che non esista gia un repo "tubeflow".
    del temp_repo_res.json >nul 2>&1
    pause
    exit /b 1
)

echo.
echo ===================================================
echo  COMPLETATO CON SUCCESSO!
echo ===================================================
echo Il tuo codice e stato caricato su GitHub.
echo.
echo Adesso vai su:
echo https://github.com/%GH_USER%/tubeflow/settings/secrets/actions
echo ed inserisci i segreti del file .env seguendo la guida GITHUB_SETUP.md.
echo.
del temp_repo_res.json >nul 2>&1
pause
exit /b 0

:error
echo Errore: Username o Token vuoti!
pause
exit /b 1
