@echo off
rem Klik dua kali untuk membuka Laprak Studio (http://localhost:8000)
cd /d "%~dp0"
where py >nul 2>nul && (py -3 studio\server.py --buka) || (python studio\server.py --buka)
pause
