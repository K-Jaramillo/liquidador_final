@echo off
REM Script para ejecutar ambas aplicaciones simultaneamente
REM Cambiar a la carpeta del proyecto
cd /d "%~dp0"

REM Ejecutar ambas en ventanas separadas
start "Exportador de Ventas" .venv\Scripts\python.exe exportador_ventas.py
start "Liquidador de Repartidores" .venv\Scripts\python.exe liquidador_repartidores.py

echo.
echo Ambas aplicaciones se estan ejecutando.
echo Cierra esta ventana cuando termine.
pause
