#!/bin/bash
# ==============================================================================
# Lanzador del Liquidador de Repartidores para Linux
# Configura automáticamente las bibliotecas de Firebird 2.5
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FB25_LIB="$SCRIPT_DIR/firebird25_lib"

# Verificar que existen las bibliotecas de Firebird 2.5
if [ -d "$FB25_LIB" ]; then
    export LD_LIBRARY_PATH="$FB25_LIB:$LD_LIBRARY_PATH"
    export FIREBIRD="$FB25_LIB"
    echo "✅ Configuradas bibliotecas de Firebird 2.5"
else
    echo "⚠️ No se encontraron bibliotecas de Firebird 2.5 bundled"
    echo "   Intentando usar las del sistema..."
fi

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python no está instalado"
    exit 1
fi

# Verificar entorno virtual
VENV_ACTIVATE=""
if [ -f "$SCRIPT_DIR/../.venv/bin/activate" ]; then
    VENV_ACTIVATE="$SCRIPT_DIR/../.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    VENV_ACTIVATE="$SCRIPT_DIR/.venv/bin/activate"
fi

if [ -n "$VENV_ACTIVATE" ]; then
    echo "✅ Activando entorno virtual..."
    source "$VENV_ACTIVATE"
fi

# Mostrar información de debug
echo "=============================================="
echo "  Liquidador de Repartidores - Linux"
echo "=============================================="
echo "📁 Directorio: $SCRIPT_DIR"
echo "🐍 Python: $($PYTHON_CMD --version)"
echo "📚 LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "🔥 FIREBIRD: $FIREBIRD"
echo "=============================================="

# Ejecutar la aplicación
cd "$SCRIPT_DIR"
$PYTHON_CMD main.py
