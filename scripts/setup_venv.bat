@echo off
REM Virtual Environment Setup and Verification Script for AvatarFactory (Windows)

echo ============================================================
echo   AvatarFactory - Virtual Environment Setup ^& Verification
echo ============================================================
echo.

REM Check Python version
echo 1. Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo    ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
echo    ✅ Python found
echo.

REM Create virtual environment
echo 2. Creating virtual environment...
if exist venv (
    echo    WARNING: venv directory already exists
    set /p REPLY="   Delete and recreate? (y/N): "
    if /i "%REPLY%"=="y" (
        echo    Deleting old venv...
        rmdir /s /q venv
        python -m venv venv
        echo    ✅ New virtual environment created
    ) else (
        echo    Using existing venv
    )
) else (
    python -m venv venv
    echo    ✅ Virtual environment created
)
echo.

REM Activate virtual environment
echo 3. Activating virtual environment...
call venv\Scripts\activate.bat
echo    ✅ Virtual environment activated
echo.

REM Upgrade pip
echo 4. Upgrading pip...
python -m pip install --upgrade pip --quiet
echo    ✅ pip upgraded
echo.

REM Install requirements
echo 5. Installing dependencies...
echo.
echo    Choose installation type:
echo    1) Standard (all LLM providers)
echo    2) Development (with testing tools)
echo.
set /p choice="   Enter choice [1-2]: "

if "%choice%"=="1" (
    set REQ_FILE=requirements.txt
    echo    Installing: Standard
) else if "%choice%"=="2" (
    set REQ_FILE=requirements-dev.txt
    echo    Installing: Development
) else (
    echo    Invalid choice, using Standard installation
    set REQ_FILE=requirements.txt
)

echo.
pip install -r %REQ_FILE%
echo    ✅ Dependencies installed
echo.

REM Install package in editable mode
echo 6. Installing AvatarFactory package...
pip install -e .
echo    ✅ AvatarFactory package installed
echo.

REM Check .env file
echo 7. Checking configuration...
if exist .env (
    echo    ✅ .env file found
) else (
    echo    ⚠️  .env file not found
    if exist .env.example (
        set /p REPLY="   Create .env from .env.example? (Y/n): "
        if /i not "%REPLY%"=="n" (
            copy .env.example .env
            echo    ✅ .env created from .env.example
            echo    ⚠️  IMPORTANT: Edit .env and add your API keys!
        )
    )
)
echo.

REM Run verification
echo 8. Running installation verification...
echo.
python scripts\verify_install.py

REM Show activation instructions
echo.
echo ============================================================
echo   ✅ Setup Complete!
echo ============================================================
echo.
echo Virtual environment is activated in this session.
echo.
echo To use AvatarFactory:
echo   • In this terminal: avatarfactory chat
echo.
echo To activate venv in a new terminal:
echo   • CMD:        venv\Scripts\activate.bat
echo   • PowerShell: venv\Scripts\Activate.ps1
echo   • Git Bash:   source venv/Scripts/activate
echo.
echo To deactivate:
echo   • Run: deactivate
echo.
echo Next steps:
echo   1. Edit .env and add your API keys
echo   2. Run: avatarfactory chat
echo   3. Start creating personas!
echo.
pause
