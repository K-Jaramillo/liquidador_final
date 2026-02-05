# -*- coding: utf-8 -*-
"""
Configuración global del Liquidador de Repartidores
"""
import os
import sys


class Config:
    """Configuración centralizada de la aplicación."""
    
    # Versión de la aplicación
    VERSION = "2.1.0"
    APP_NAME = "Liquidador de Repartidores"
    
    # Colores del tema profesional
    COLORS = {
        # Colores primarios
        'primary': '#1565c0',
        'primary_dark': '#0d47a1',
        'primary_light': '#1976d2',
        
        # Colores de acento
        'accent': '#ff6f00',
        'accent_light': '#ffa000',
        
        # Colores de fondo
        'bg_main': '#f5f5f5',
        'bg_card': '#ffffff',
        'bg_header': '#e3f2fd',
        
        # Colores de texto
        'text_primary': '#212121',
        'text_secondary': '#757575',
        'text_light': '#ffffff',
        
        # Colores de estado
        'success': '#2e7d32',
        'warning': '#f57c00',
        'error': '#c62828',
        'info': '#1565c0',
        
        # Colores para filas de tabla
        'row_assigned': '#e8f5e9',
        'row_unassigned': '#fff3e0',
        'row_cancelled': '#ffccbc',
        'row_cancelled_other_day': '#ff8a80',
        'row_credit': '#fff9c4',
        'row_selected': '#1976d2',
    }
    
    # Fuentes
    FONTS = {
        'title': ('Segoe UI', 14, 'bold'),
        'subtitle': ('Segoe UI', 11, 'bold'),
        'heading': ('Segoe UI', 10, 'bold'),
        'body': ('Segoe UI', 9),
        'body_bold': ('Segoe UI', 9, 'bold'),
        'small': ('Segoe UI', 8),
        'monospace': ('Consolas', 9),
    }
    
    # Dimensiones
    WINDOW_SIZE = "1320x920"
    WINDOW_MIN_SIZE = (1100, 750)
    
    # Filas de tabla
    TREEVIEW_ROW_HEIGHT = 28
    
    @classmethod
    def get_base_path(cls):
        """Obtiene la ruta base de la aplicación."""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    @classmethod
    def get_fdb_path(cls):
        """Obtiene la ruta del archivo FDB según el SO."""
        # Ruta de la BD real con datos actualizados
        return r'D:\BD\PDVDATA.FDB'
    
    @classmethod
    def get_isql_path(cls):
        """Obtiene la ruta de isql según el SO."""
        if sys.platform == 'win32':
            # Buscar en múltiples ubicaciones posibles
            posibles_rutas = [
                r'C:\Program Files\Firebird\Firebird_5_0\isql.exe',
                r'C:\Program Files\Firebird\Firebird_4_0\isql.exe',
                r'C:\Program Files\Firebird\Firebird_3_0\isql.exe',
                r'C:\Program Files\Firebird\Firebird_2_5\bin\isql.exe',
                r'C:\Program Files (x86)\Firebird\Firebird_2_5\bin\isql.exe',
                r'C:\Firebird\isql.exe',
                r'C:\Firebird\bin\isql.exe',
            ]
            for ruta in posibles_rutas:
                if os.path.exists(ruta):
                    return ruta
            # Si no encuentra ninguna, retornar la más común
            return r'C:\Program Files\Firebird\Firebird_5_0\isql.exe'
        else:
            return '/opt/firebird/bin/isql'
