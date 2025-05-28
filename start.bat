@echo off
setlocal EnableDelayedExpansion
cd /d "C:\Users\Owner\Desktop\Ai-working-on"

echo Starting Claude Engineer with devstral model...
echo.

REM Set environment for Unicode support
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1

REM Use specific Python version
set PYTHONPATH=C:\Users\Owner\AppData\Local\Programs\Python\Python311

REM Start in real Windows Terminal/CMD
start cmd /k "C:\Users\Owner\AppData\Local\Programs\Python\Python311\python.exe -c "import sys; print('Python:', sys.executable)" && echo n | C:\Users\Owner\AppData\Local\Programs\Python\Python311\python.exe ce3_ollama.py"

echo Application starting in new terminal window...
pause
