@echo off
title ARCA Facturador - Instalacion
chcp 65001 >nul

echo ============================================
echo   ARCA Facturador - Configuracion Inicial
echo ============================================
echo.

echo [1/5] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado. Instale Python 3.10+ desde python.org
    pause
    exit /b 1
)
python --version

echo [2/5] Verificando OpenSSL...
openssl version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: OpenSSL no encontrado en PATH
    echo Puede descargarlo de: https://slproweb.com/products/Win32OpenSSL.html
)

echo [3/5] Creando entorno virtual...
if not exist venv (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo Entorno virtual creado
) else (
    echo Entorno virtual ya existe
)

echo [4/5] Instalando dependencias...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)
echo Dependencias instaladas correctamente

echo [5/5] Creando estructura de carpetas...
if not exist certs mkdir certs
if not exist data mkdir data
if not exist data\backups mkdir data\backups
if not exist logs mkdir logs
if not exist temp mkdir temp
if not exist resources mkdir resources

echo.
echo ============================================
echo   Instalacion completada!
echo ============================================
echo.
echo Para iniciar la aplicacion:
echo   1. Active el entorno: venv\Scripts\activate
echo   2. Ejecute: python main.py
echo.
echo O directamente: run.bat
echo.

pause
