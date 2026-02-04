@echo off
REM Script para ejecutar Liquidador de Repartidores
REM Cambiar a la carpeta del proyecto
cd /d "%~dp0"

REM Ejecutar con el intérprete Python del entorno virtual
.venv\Scripts\python.exe liquidador_repartidores.py

pause
