@echo off
chcp 65001 >nul
title ARCA Facturador
call venv\Scripts\activate.bat
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Error al iniciar la aplicacion. Verifique los logs.
    pause
)
