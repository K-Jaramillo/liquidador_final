#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicación Standalone de Anotaciones (Sticky Notes)
Ejecuta la pestaña de anotaciones como una aplicación independiente
Importa las notas existentes de la base de datos SQLite
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import importlib.util
from datetime import datetime

# Agregar ruta actual al path para importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar dependencias
import database_local as db_local
from core.datastore import DataStore

# Importar TabAnotaciones directamente del archivo
import importlib.util
tab_anotaciones_path = os.path.join(os.path.dirname(__file__), 'tabs', 'tab_anotaciones.py')
spec = importlib.util.spec_from_file_location("tab_anotaciones", tab_anotaciones_path)
tab_anotaciones_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tab_anotaciones_module)
TabAnotaciones = tab_anotaciones_module.TabAnotaciones


class AppAnotacionesStandalone:
    """Aplicación standalone para gestionar anotaciones/sticky notes."""
    
    def __init__(self, root):
        self.root = root
        self.ventana = root  # Compatibilidad con TabAnotaciones que espera self.app.ventana
        self.root.title("📝 Gestor de Anotaciones - Sticky Notes")
        self.root.geometry("1400x800")
        
        # Configurar tema
        style = ttk.Style()
        style.theme_use('clam')
        
        # Crear DataStore
        self.datastore = DataStore()
        self.datastore.fecha = datetime.now().strftime('%Y-%m-%d')
        
        # Crear Frame principal
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Encabezado con información
        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        title_label = ttk.Label(header, text="📝 Gestor de Anotaciones", 
                               font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # Información de fecha
        fecha_str = self.datastore.fecha
        fecha_label = ttk.Label(header, text=f"Fecha: {fecha_str}", 
                               font=("Arial", 10))
        fecha_label.pack(side=tk.RIGHT, padx=20)
        
        # Crear la pestaña de anotaciones
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Frame para la pestaña
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="Notas Adhesivas")
        
        # Inicializar TabAnotaciones
        try:
            self.tab_anotaciones = TabAnotaciones(tab_frame, self, self.datastore)
            print("[OK] Aplicacion de anotaciones iniciada correctamente")
            
            # Cargar notas existentes
            self._cargar_notas_al_inicio()
            
        except Exception as e:
            print(f"[ERROR] Error inicializando TabAnotaciones: {e}")
            import traceback
            traceback.print_exc()
            
            # Mostrar error en la UI
            error_label = ttk.Label(tab_frame, 
                                   text=f"Error: {str(e)}\n\nRevisa la consola para más detalles",
                                   font=("Arial", 10), foreground="red")
            error_label.pack(padx=20, pady=20)
    
    def _cargar_notas_al_inicio(self):
        """Carga las notas existentes de la BD al iniciar la aplicación."""
        try:
            fecha_actual = self.datastore.fecha
            notas = db_local.obtener_anotaciones(incluir_archivadas=False, fecha=fecha_actual)
            
            if notas:
                print(f"[OK] Se cargaron {len(notas)} notas para {fecha_actual}")
                # La pestaña debería cargar automáticamente, pero forzamos un refresh
                if hasattr(self.tab_anotaciones, 'cargar_anotaciones'):
                    self.tab_anotaciones.cargar_anotaciones()
            else:
                print(f"[INFO] No hay notas guardadas para {fecha_actual}")
                
        except Exception as e:
            print(f"[WARN] Error cargando notas: {e}")


def main():
    """Punto de entrada principal."""
    print("=" * 60)
    print("Iniciando Gestor de Anotaciones Standalone")
    print("=" * 60)
    
    # Inicializar BD
    try:
        db_local.init_database()
        print("[OK] Base de datos inicializada")
    except Exception as e:
        print(f"[ERROR] Error inicializando BD: {e}")
        return
    
    # Crear ventana principal
    root = tk.Tk()
    
    # Configurar icono si existe
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass
    
    # Crear aplicación
    app = AppAnotacionesStandalone(root)
    
    # Iniciar loop principal
    root.mainloop()


if __name__ == "__main__":
    main()
