@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo Создаётся отдельное окружение Python...
if exist ".venv\Scripts\python.exe" goto install
py -3.14 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.14 -m venv .venv
    goto checkenv
)
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" -m venv .venv
    goto checkenv
)
python -c "import sys; assert (3,11) <= sys.version_info[:2] <= (3,14)" >nul 2>&1
if errorlevel 1 goto nopython
python -m venv .venv
:checkenv
if not exist ".venv\Scripts\python.exe" goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import sklearn, tkinter, joblib"
if errorlevel 1 goto failed
echo.
echo ГОТОВО. Закройте это окно и запустите 02_start.bat
pause
exit /b 0
:nopython
echo Python 3.11–3.14 не найден. Откройте README.md.
pause
exit /b 1
:failed
echo.
echo Ошибка установки. Скопируйте сообщение выше или сделайте скриншот.
pause
exit /b 1
