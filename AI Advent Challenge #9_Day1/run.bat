@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"%~dp0env\Scripts\python.exe" "%~dp0AI_Advent_Challenge__9_Day1.py"
pause
