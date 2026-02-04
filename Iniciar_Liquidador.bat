@echo off
REM Script para iniciar Liquidador de Repartidores
REM Asegura que Firebird está disponible y ejecuta la aplicación

SETLOCAL ENABLEDELAYEDEXPANSION

ECHO.
ECHO ====================================================
ECHO  LIQUIDADOR DE REPARTIDORES v2
ECHO ====================================================
ECHO.

REM Verificar que Python está instalado
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO ERROR: Python no está instalado o no está en PATH
    ECHO.
    ECHO Descarga Python desde: https://www.python.org/downloads/
    PAUSE
    EXIT /B 1
)

REM Verificar que isql de Firebird está disponible
WHERE isql.exe >nul 2>&1
IF ERRORLEVEL 1 (
    REM Intentar con rutas conocidas
    IF EXIST "C:\Program Files (x86)\Firebird\Firebird_2_5\bin\isql.exe" (
        REM Encontrado en x86
        ECHO ✓ Firebird encontrado en Program Files (x86)
    ) ELSE IF EXIST "C:\Program Files\Firebird\Firebird_2_5\bin\isql.exe" (
        REM Encontrado en Program Files
        ECHO ✓ Firebird encontrado en Program Files
    ) ELSE (
        ECHO ADVERTENCIA: Firebird no se encontró en PATH
        ECHO.
        ECHO Verifica que Firebird está instalado:
        ECHO - Ejecuta: python diagnostico_firebird.py
        ECHO.
        PAUSE
    )
) ELSE (
    ECHO ✓ Firebird encontrado en PATH
)

ECHO.
ECHO Iniciando Liquidador de Repartidores...
ECHO.

REM Ejecutar la aplicación
python "%~dp0liquidador_repartidores.py"

IF ERRORLEVEL 1 (
    ECHO.
    ECHO ERROR al ejecutar la aplicación
    ECHO.
    PAUSE
    EXIT /B 1
)

EXIT /B 0
