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
from tkinter import ttk
import sys
import os
import threading

# Agregar el directorio actual al path para importaciones relativas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SplashScreen:
    """Pantalla de carga animada mientras se inicializa la aplicación."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cargando...")
        self.root.overrideredirect(True)  # Sin bordes de ventana
        
        # Tamaño y posición centrada
        width, height = 400, 250
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Fondo con gradiente simulado
        self.root.configure(bg="#1a237e")
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg="#1a237e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Logo/Título
        tk.Label(main_frame, text="💰", font=("Segoe UI", 48), 
                bg="#1a237e", fg="white").pack(pady=(20, 10))
        
        tk.Label(main_frame, text="LIQUIDADOR", font=("Segoe UI", 24, "bold"), 
                bg="#1a237e", fg="white").pack()
        
        tk.Label(main_frame, text="DE REPARTIDORES", font=("Segoe UI", 14), 
                bg="#1a237e", fg="#90caf9").pack()
        
        # Mensaje de estado
        self.status_var = tk.StringVar(value="Iniciando...")
        self.status_label = tk.Label(main_frame, textvariable=self.status_var,
                                     font=("Segoe UI", 10), bg="#1a237e", fg="#b3e5fc")
        self.status_label.pack(pady=(20, 10))
        
        # Barra de progreso
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Splash.Horizontal.TProgressbar", 
                       troughcolor='#303f9f', 
                       background='#4caf50',
                       lightcolor='#4caf50',
                       darkcolor='#388e3c')
        
        self.progress = ttk.Progressbar(main_frame, length=300, mode='determinate',
                                        style="Splash.Horizontal.TProgressbar")
        self.progress.pack(pady=10)
        
        # Versión
        tk.Label(main_frame, text="v2.1.0", font=("Segoe UI", 8), 
                bg="#1a237e", fg="#7986cb").pack(side=tk.BOTTOM)
        
        self.root.update()
    
    def update_status(self, message: str, progress: int = None):
        """Actualiza el mensaje de estado y la barra de progreso."""
        self.status_var.set(message)
        if progress is not None:
            self.progress['value'] = progress
        self.root.update()
    
    def close(self):
        """Cierra la pantalla de carga."""
        self.root.destroy()


def main():
    """Punto de entrada principal de la aplicación."""
    try:
        # Mostrar splash screen
        splash = SplashScreen()
        
        # Fase 1: Importar módulos base
        splash.update_status("Cargando módulos del sistema...", 10)
        import time
        time.sleep(0.2)  # Pequeña pausa para mostrar el progreso
        
        # Fase 2: Importar base de datos
        splash.update_status("Conectando base de datos...", 25)
        try:
            import database_local
            time.sleep(0.2)
        except Exception as e:
            print(f"[WARN] database_local: {e}")
        
        # Fase 3: Importar módulo principal
        splash.update_status("Cargando interfaz principal...", 45)
        from liquidador_repartidores import LiquidadorRepartidores
        time.sleep(0.2)
        
        # Fase 4: Crear ventana principal (oculta)
        splash.update_status("Inicializando ventana...", 60)
        root = tk.Tk()
        root.withdraw()  # Ocultar mientras carga
        
        # Configurar icono si existe
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        if os.path.exists(icon_path):
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass
        
        # Fase 5: Inicializar la aplicación
        splash.update_status("Cargando datos de repartidores...", 75)
        app = LiquidadorRepartidores(root)
        time.sleep(0.3)
        
        # Fase 6: Preparar interfaz
        splash.update_status("Preparando interfaz...", 90)
        root.update_idletasks()
        time.sleep(0.2)
        
        # Fase 7: Centrar ventana
        splash.update_status("¡Listo!", 100)
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        time.sleep(0.3)
        
        # Cerrar splash y mostrar ventana principal
        splash.close()
        root.deiconify()  # Mostrar ventana principal
        
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
