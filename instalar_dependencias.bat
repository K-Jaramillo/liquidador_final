@echo off
chcp 65001 >nul
echo ============================================
echo  INSTALADOR DE DEPENDENCIAS - LIQUIDADOR
echo ============================================
echo.

REM Detectar Python
set PYTHON_PATH=
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_PATH=python
) else (
    if exist "C:\Users\%USERNAME%\AppData\Local\Python\bin\python.exe" (
        set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Python\bin\python.exe
    ) else if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe" (
        set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe
    ) else if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" (
        set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe
    ) else if exist "C:\Python311\python.exe" (
        set PYTHON_PATH=C:\Python311\python.exe
    ) else if exist "C:\Python310\python.exe" (
        set PYTHON_PATH=C:\Python310\python.exe
    )
)

if "%PYTHON_PATH%"=="" (
    echo [ERROR] No se encontro Python instalado.
    echo Por favor instale Python desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado: %PYTHON_PATH%
echo.

echo ============================================
echo  ACTUALIZANDO PIP
echo ============================================
"%PYTHON_PATH%" -m pip install --upgrade pip
echo.

echo ============================================
echo  INSTALANDO DEPENDENCIAS DE PYTHON
echo ============================================
echo.

echo [1/6] Instalando fdb (Driver Firebird)...
"%PYTHON_PATH%" -m pip install fdb
echo.

echo [2/6] Instalando pandas...
"%PYTHON_PATH%" -m pip install pandas
echo.

echo [3/6] Instalando numpy...
"%PYTHON_PATH%" -m pip install numpy
echo.

echo [4/6] Instalando openpyxl (Excel)...
"%PYTHON_PATH%" -m pip install openpyxl
echo.

echo [5/6] Instalando tkcalendar (Calendario)...
"%PYTHON_PATH%" -m pip install tkcalendar
echo.

echo [6/6] Instalando pywin32 (Windows API)...
"%PYTHON_PATH%" -m pip install pywin32
echo.

echo ============================================
echo  VERIFICANDO FIREBIRD
echo ============================================
if exist "C:\Program Files\Firebird\Firebird_2_5\bin\fbclient.dll" (
    echo [OK] Firebird 2.5 encontrado
) else if exist "C:\Program Files\Firebird\Firebird_3_0\fbclient.dll" (
    echo [OK] Firebird 3.0 encontrado
) else if exist "C:\Program Files\Firebird\Firebird_4_0\fbclient.dll" (
    echo [OK] Firebird 4.0 encontrado
) else (
    echo [ADVERTENCIA] Firebird NO encontrado.
    echo Descargue e instale Firebird desde:
    echo https://firebirdsql.org/en/firebird-2-5/
    echo.
)

echo ============================================
echo  VERIFICANDO INSTALACION
echo ============================================
echo.
"%PYTHON_PATH%" -m pip list | findstr /i "fdb pandas numpy openpyxl tkcalendar pywin32"

echo.
echo ============================================
echo  PROBANDO CONEXION A BASE DE DATOS
echo ============================================
"%PYTHON_PATH%" -c "import fdb; print('[OK] Driver fdb version:', fdb.__version__)"

echo.
echo ============================================
echo  INSTALACION COMPLETADA
echo ============================================
echo.
echo Para ejecutar la aplicacion use: Iniciar_Liquidador.bat
echo.
pause
