@echo off
:: =============================================================
:: MilJoy — AI Call Assistant
:: setup.bat — One-click dependency installer for Windows
:: =============================================================
:: Run this file once after cloning the repository.
:: Double-click setup.bat or run it in Command Prompt.
:: =============================================================

echo.
echo  ============================================
echo   MilJoy — AI Call Assistant Setup
echo  ============================================
echo.
echo  Installing Python dependencies...
echo.

:: Install all required packages
pip install -r requirements.txt

:: Check if installation succeeded
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Installation failed!
    echo  Make sure Python is installed: https://python.org
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   Installation complete!
echo  ============================================
echo.
echo  Next steps:
echo  1. Install VB-Audio Virtual Cable (vb-audio.com/Cable)
echo  2. Get a free Groq API key (console.groq.com)
echo  3. Run: python security.py  (app owners only)
echo  4. Run: python main.py
echo.
echo  The setup wizard will guide you through the rest.
echo.
pause
