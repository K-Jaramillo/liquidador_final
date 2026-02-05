#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidad para integración de Anotaciones Standalone
Permite ejecutar la aplicación de anotaciones desde la aplicación principal
o de forma independiente
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def get_anotaciones_runner():
    """Retorna el comando para ejecutar la aplicación de anotaciones."""
    script_dir = Path(__file__).parent
    anotaciones_script = script_dir / "run_anotaciones.py"
    
    if not anotaciones_script.exists():
        raise FileNotFoundError(f"No se encontró {anotaciones_script}")
    
    return str(anotaciones_script)


def ejecutar_anotaciones_standalone():
    """Ejecuta la aplicación de anotaciones como un proceso independiente."""
    try:
        script = get_anotaciones_runner()
        
        # Crear un proceso separado (no bloqueador)
        if platform.system() == "Windows":
            # Windows: usar CREATE_NEW_CONSOLE para una ventana separada
            subprocess.Popen(
                [sys.executable, script],
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
            )
        else:
            # Unix/Linux/macOS
            subprocess.Popen([sys.executable, script])
        
        return True
        
    except Exception as e:
        print(f"❌ Error ejecutando anotaciones: {e}")
        return False


def ejecutar_anotaciones_bloqueador():
    """Ejecuta la aplicación de anotaciones y espera a que cierre."""
    try:
        script = get_anotaciones_runner()
        subprocess.run([sys.executable, script])
        return True
    except Exception as e:
        print(f"❌ Error ejecutando anotaciones: {e}")
        return False


def main():
    """Prueba la utilidad."""
    print("Testing Anotaciones Standalone Runner...")
    print(f"Script encontrado: {get_anotaciones_runner()}")
    
    # Opción 1: No bloqueador (recomendado para integración)
    print("\n✅ Para integrar en tu app, usa:")
    print("   from anotaciones_runner import ejecutar_anotaciones_standalone")
    print("   ejecutar_anotaciones_standalone()  # Abre en ventana separada")
    
    # Opción 2: Bloqueador
    print("\n   O para ejecutar bloqueador:")
    print("   from anotaciones_runner import ejecutar_anotaciones_bloqueador")
    print("   ejecutar_anotaciones_bloqueador()  # Espera a que cierre")


if __name__ == "__main__":
    main()
