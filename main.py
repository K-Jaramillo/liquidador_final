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
import time

# Agregar el directorio actual al path para importaciones relativas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar temas y base de datos para cargar tema guardado
try:
    from core.themes import TEMAS
    import database_local as db_local
    HAS_THEMES = True
except ImportError:
    HAS_THEMES = False
    TEMAS = None


def get_splash_colors():
    """Obtiene los colores del splash según el tema guardado."""
    if not HAS_THEMES:
        return {
            'bg': "#1a1a2e",
            'accent': "#16213e", 
            'border': "#0f3460",
            'text': "#ffffff",
            'subtext': "#7f8fa6",
            'highlight': "#e94560",
            'progress_bg': "#16213e",
            'progress_fill': "#e94560",
            'status': "#00d9ff"
        }
    
    try:
        tema_id = db_local.obtener_config('tema_actual', 'oscuro')
        tema = TEMAS.get(tema_id, TEMAS.get('oscuro', {}))
    except Exception:
        tema = TEMAS.get('oscuro', {})
    
    # Mapear colores del tema al splash (usando las claves correctas del tema)
    return {
        'bg': tema.get('BG_DARKER', "#1a1a2e"),
        'accent': tema.get('BG_CARD', "#16213e"),
        'border': tema.get('BORDER_COLOR', "#0f3460"),
        'text': tema.get('TEXT_PRIMARY', "#ffffff"),
        'subtext': tema.get('TEXT_SECONDARY', "#7f8fa6"),
        'highlight': tema.get('PRIMARY', "#e94560"),
        'progress_bg': tema.get('BG_DARK', "#16213e"),
        'progress_fill': tema.get('SUCCESS', "#4CAF50"),
        'status': tema.get('PRIMARY_LIGHT', "#00d9ff")
    }


class SplashScreen:
    """Pantalla de carga animada mientras se inicializa la aplicación."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cargando...")
        self.root.overrideredirect(True)  # Sin bordes de ventana
        
        # Tamaño y posición centrada
        width, height = 420, 300
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Colores del splash según tema guardado
        colors = get_splash_colors()
        BG_COLOR = colors['bg']
        ACCENT = colors['accent']
        
        self.root.configure(bg=BG_COLOR)
        
        # Frame principal con borde
        main_frame = tk.Frame(self.root, bg=BG_COLOR, highlightbackground=colors['border'], 
                              highlightthickness=2)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame interno con padding
        inner_frame = tk.Frame(main_frame, bg=BG_COLOR)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        # Logo/Título
        tk.Label(inner_frame, text="💰", font=("Segoe UI Emoji", 52), 
                bg=BG_COLOR, fg=colors['highlight']).pack(pady=(15, 5))
        
        tk.Label(inner_frame, text="LIQUIDADOR", font=("Segoe UI", 26, "bold"), 
                bg=BG_COLOR, fg=colors['text']).pack()
        
        tk.Label(inner_frame, text="DE REPARTIDORES", font=("Segoe UI", 13), 
                bg=BG_COLOR, fg=colors['subtext']).pack()
        
        # Separador visual
        separator = tk.Frame(inner_frame, height=2, bg=colors['border'])
        separator.pack(fill=tk.X, pady=15)
        
        # Mensaje de estado con fondo para mejor visibilidad
        status_frame = tk.Frame(inner_frame, bg=ACCENT, padx=10, pady=5)
        status_frame.pack(fill=tk.X)
        
        self.status_var = tk.StringVar(value="Iniciando...")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var,
                                     font=("Segoe UI", 11), bg=ACCENT, fg=colors['status'],
                                     anchor="center")
        self.status_label.pack(fill=tk.X)
        
        # Frame para barra de progreso con fondo
        progress_frame = tk.Frame(inner_frame, bg=BG_COLOR)
        progress_frame.pack(fill=tk.X, pady=(15, 10))
        
        # Barra de progreso con Canvas personalizado (más visible)
        self.progress_canvas = tk.Canvas(progress_frame, height=20, bg=colors['progress_bg'], 
                                         highlightthickness=1, highlightbackground=colors['border'])
        self.progress_canvas.pack(fill=tk.X)
        
        # Dibujar barra de fondo
        self.progress_canvas.update_idletasks()
        self.canvas_width = 360
        self.progress_fill_color = colors['progress_fill']
        self.progress_bar = self.progress_canvas.create_rectangle(
            2, 2, 2, 18, fill=self.progress_fill_color, outline=""
        )
        
        # Porcentaje
        self.progress_text = self.progress_canvas.create_text(
            180, 10, text="0%", fill=colors['text'], font=("Segoe UI", 9, "bold")
        )
        
        # Versión
        tk.Label(inner_frame, text="v2.1.0", font=("Segoe UI", 9), 
                bg=BG_COLOR, fg=colors['subtext']).pack(side=tk.BOTTOM, pady=(5, 0))
        
        self.root.update()
    
    def update_status(self, message: str, progress: int = None):
        """Actualiza el mensaje de estado y la barra de progreso."""
        self.status_var.set(message)
        if progress is not None:
            # Actualizar barra de progreso en canvas
            self.progress_canvas.update_idletasks()
            canvas_w = self.progress_canvas.winfo_width() - 4
            if canvas_w < 10:
                canvas_w = self.canvas_width
            bar_width = int((progress / 100) * canvas_w)
            self.progress_canvas.coords(self.progress_bar, 2, 2, 2 + bar_width, 18)
            self.progress_canvas.itemconfig(self.progress_text, text=f"{progress}%")
        self.root.update()
    
    def close(self):
        """Cierra la pantalla de carga."""
        self.root.destroy()


def main():
    """Punto de entrada principal de la aplicación."""
    try:
        # Mostrar splash screen
        splash = SplashScreen()
        
        # Fase 1: Importar módulos base (rápido)
        splash.update_status("Importando módulos...", 15)
        
        # Fase 2: Importar base de datos local
        splash.update_status("Iniciando base de datos local...", 30)
        try:
            import database_local
        except Exception as e:
            print(f"[WARN] database_local: {e}")
        
        # Fase 3: Importar módulo principal
        splash.update_status("Cargando componentes...", 50)
        from liquidador_repartidores import LiquidadorRepartidores
        
        # Fase 4: Crear ventana principal (oculta)
        splash.update_status("Creando interfaz...", 70)
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
        splash.update_status("Inicializando aplicación...", 85)
        app = LiquidadorRepartidores(root)
        
        # Fase 6: Finalizar
        splash.update_status("¡Listo!", 100)
        
        # Centrar ventana
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Cerrar splash y mostrar ventana principal
        splash.close()
        root.deiconify()
        root.lift()
        root.focus_force()
        
        # Cargar datos en segundo plano DESPUÉS de mostrar la ventana
        root.after(50, app._cargar_datos_inicial)
        
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
