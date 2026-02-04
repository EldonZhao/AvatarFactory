@echo off
REM Quick test script - verifies venv installation (Windows)

echo 🧪 Quick Test - AvatarFactory
echo.

REM Check if venv is activated
if "%VIRTUAL_ENV%"=="" (
    echo ❌ Virtual environment not activated!
    echo.
    echo Please activate venv first:
    echo   CMD:        venv\Scripts\activate.bat
    echo   PowerShell: venv\Scripts\Activate.ps1
    exit /b 1
)

echo ✅ Virtual environment active: %VIRTUAL_ENV%
echo.

REM Run verification
python verify_install.py

echo.
echo Test complete! If all checks passed, you're ready to use AvatarFactory.
echo.
echo Try: avatarfactory chat
pause
