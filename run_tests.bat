@echo off
setlocal
set "PYTHONPATH="

echo ===========================================
echo   Starting Automated Regression Tests
echo ===========================================
echo.

call venv\Scripts\activate.bat

if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [STEP 1] Checking Environment...
python --version
python -c "import sys; print(sys.executable)"
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 'Python 3.12 is required; recreate the project venv with Python 3.12.')"
if errorlevel 1 (
    echo [ERROR] The project venv must use Python 3.12.
    pause
    exit /b 1
)
pip show pytest >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] pytest not found!
    echo Please run: venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    pause
    exit /b 1
)

echo.
echo [STEP 2] Running Tests...
echo.

python -m pytest tests -v --tb=short

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===========================================
    echo   [SUCCESS] All tests passed!
    echo ===========================================
) else (
    echo.
    echo ===========================================
    echo   [FAILURE] Some tests failed.
    echo ===========================================
)

echo.
pause
endlocal
