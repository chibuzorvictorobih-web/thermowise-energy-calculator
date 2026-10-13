@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   ThermoWise 2.0 - Validate and Launch
 echo ==========================================
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto :fail
)
echo.
echo Installing dependencies if needed...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
echo.
echo Checking 58 automated engineering tests...
".venv\Scripts\python.exe" -m unittest discover -s . -p "test_*.py" -v
if errorlevel 1 goto :fail
echo.
echo Starting browser application. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto :fail
goto :done
:fail
echo.
echo A step failed. Read START_HERE.txt and send the full error message.
pause
exit /b 1
:done
endlocal
