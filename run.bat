@echo off
cd /d "C:\Users\Owner\Desktop\Ai-working-on"

echo Starting Claude Engineer v3 with Ollama + devstral...
echo.

REM Set proper encoding
set PYTHONIOENCODING=utf-8

REM Auto-skip e2b dependency prompt and start
echo n | C:\Users\Owner\AppData\Local\Programs\Python\Python311\python.exe ce3_ollama.py

pause
