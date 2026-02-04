#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIQUIDADOR DE REPARTIDORES v2.1
================================
Aplicación modular para gestión de liquidaciones de repartidores.

Estructura del proyecto:
├── core/
│   ├── __init__.py
│   ├── config.py      - Configuración global
│   ├── datastore.py   - Modelo de datos centralizado
│   └── database.py    - Gestor de conexiones Firebird
├── gui/
│   ├── __init__.py
│   ├── styles.py      - Estilos visuales profesionales
│   └── widgets.py     - Widgets personalizados
└── main.py            - Punto de entrada principal

Autor: Sistema de Gestión de Repartidores
Versión: 2.1.0
"""

import tkinter as tk
import sys
import os

# Agregar el directorio actual al path para importaciones relativas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Punto de entrada principal de la aplicación."""
    try:
        # Importar el liquidador principal
        from liquidador_repartidores import LiquidadorRepartidores
        
        # Crear ventana principal
        root = tk.Tk()
        
        # Configurar icono si existe
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        
        # Inicializar la aplicación
        app = LiquidadorRepartidores(root)
        
        # Centrar ventana en pantalla
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Iniciar loop principal
        root.mainloop()
        
    except ImportError as e:
        print(f"Error de importación: {e}")
        print("Asegúrate de tener todas las dependencias instaladas.")
        sys.exit(1)
    except Exception as e:
        print(f"Error al iniciar la aplicación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
