@echo off
REM Script para ejecutar Exportador de Ventas
REM Cambiar a la carpeta del proyecto
cd /d "%~dp0"

REM Ejecutar con el intérprete Python del entorno virtual
.venv\Scripts\python.exe exportador_ventas.py

pause
