@echo off
cd /d "C:\Users\Owner\Desktop\Ai-working-on"

echo Testing Python environments...
echo.

echo === Testing Python 3.11 ===
C:\Users\Owner\AppData\Local\Programs\Python\Python311\python.exe -c "import ollama; print('ollama module found'); import ollama; client = ollama.Client(); print('Ollama client created successfully')"

echo.
echo === Testing ce3_ollama.py ===
echo n | C:\Users\Owner\AppData\Local\Programs\Python\Python311\python.exe ce3_ollama.py

pause
