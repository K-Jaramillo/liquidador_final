@echo off
REM Script para iniciar Liquidador de Repartidores
REM Asegura que Firebird está disponible y ejecuta la aplicación

SETLOCAL ENABLEDELAYEDEXPANSION
chcp 65001 >nul

ECHO.
ECHO ====================================================
ECHO  LIQUIDADOR DE REPARTIDORES v2
ECHO ====================================================
ECHO.

REM Detectar Python
set PYTHON_PATH=
where python >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        set PYTHON_PATH=%%i
        goto :python_found
    )
)

if exist "C:\Users\%USERNAME%\AppData\Local\Python\bin\python.exe" (
    set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Python\bin\python.exe
    goto :python_found
)
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe" (
    set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe
    goto :python_found
)
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" (
    set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe
    goto :python_found
)

ECHO ERROR: Python no esta instalado
ECHO Descarga Python desde: https://www.python.org/downloads/
PAUSE
EXIT /B 1

:python_found
ECHO [OK] Python: %PYTHON_PATH%

REM Verificar Firebird
IF EXIST "C:\Program Files\Firebird\Firebird_2_5\bin\isql.exe" (
    ECHO [OK] Firebird 2.5 encontrado
) ELSE IF EXIST "C:\Program Files\Firebird\Firebird_3_0\isql.exe" (
    ECHO [OK] Firebird 3.0 encontrado
) ELSE IF EXIST "C:\Program Files (x86)\Firebird\Firebird_2_5\bin\isql.exe" (
    ECHO [OK] Firebird 2.5 (x86) encontrado
) ELSE (
    ECHO [ADVERTENCIA] Firebird no encontrado - puede haber problemas de conexion
)

ECHO.
ECHO Iniciando Liquidador de Repartidores...
ECHO.

REM Ejecutar la aplicación
cd /d "%~dp0"
"%PYTHON_PATH%" main.py

IF ERRORLEVEL 1 (
    ECHO.
    ECHO ERROR al ejecutar la aplicacion
    ECHO.
    PAUSE
    EXIT /B 1
)

EXIT /B 0
