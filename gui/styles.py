# -*- coding: utf-8 -*-
"""
StyleManager - Gestor de estilos profesionales para la GUI
"""
import tkinter as tk
from tkinter import ttk
import sys


class StyleManager:
    """Gestiona los estilos visuales de la aplicación."""
    
    # Paleta de colores profesional
    COLORS = {
        # Colores primarios (azul corporativo)
        'primary': '#1565c0',
        'primary_dark': '#0d47a1',
        'primary_light': '#42a5f5',
        'primary_bg': '#e3f2fd',
        
        # Colores secundarios
        'secondary': '#455a64',
        'secondary_light': '#78909c',
        
        # Fondos
        'bg_main': '#fafafa',
        'bg_card': '#ffffff',
        'bg_header': '#eceff1',
        'bg_input': '#ffffff',
        
        # Texto
        'text_primary': '#212121',
        'text_secondary': '#616161',
        'text_disabled': '#9e9e9e',
        'text_light': '#ffffff',
        
        # Estados
        'success': '#2e7d32',
        'success_bg': '#e8f5e9',
        'warning': '#f57c00',
        'warning_bg': '#fff3e0',
        'error': '#c62828',
        'error_bg': '#ffebee',
        'info': '#0288d1',
        'info_bg': '#e1f5fe',
        
        # Bordes
        'border': '#e0e0e0',
        'border_focus': '#1565c0',
        
        # Filas de tabla
        'row_even': '#ffffff',
        'row_odd': '#f5f5f5',
        'row_selected': '#1976d2',
        'row_hover': '#e3f2fd',
        
        # Estados específicos
        'assigned': '#e8f5e9',
        'unassigned': '#fff8e1',
        'cancelled': '#ffccbc',
        'cancelled_other': '#ef9a9a',
        'credit': '#fff9c4',
    }
    
    # Fuentes
    FONTS = {
        'title': ('Segoe UI', 16, 'bold'),
        'subtitle': ('Segoe UI', 12, 'bold'),
        'heading': ('Segoe UI', 10, 'bold'),
        'body': ('Segoe UI', 9),
        'body_bold': ('Segoe UI', 9, 'bold'),
        'small': ('Segoe UI', 8),
        'tiny': ('Segoe UI', 7),
        'mono': ('Consolas', 9),
        'mono_small': ('Consolas', 8),
    }
    
    # Usar fuentes alternativas en Linux
    if sys.platform != 'win32':
        FONTS = {
            'title': ('DejaVu Sans', 14, 'bold'),
            'subtitle': ('DejaVu Sans', 11, 'bold'),
            'heading': ('DejaVu Sans', 9, 'bold'),
            'body': ('DejaVu Sans', 9),
            'body_bold': ('DejaVu Sans', 9, 'bold'),
            'small': ('DejaVu Sans', 8),
            'tiny': ('DejaVu Sans', 7),
            'mono': ('DejaVu Sans Mono', 9),
            'mono_small': ('DejaVu Sans Mono', 8),
        }
    
    @classmethod
    def apply_theme(cls, root: tk.Tk) -> None:
        """Aplica el tema profesional a toda la aplicación."""
        style = ttk.Style(root)
        
        # Usar tema base según SO
        if sys.platform == 'win32':
            style.theme_use('vista')
        else:
            try:
                style.theme_use('clam')
            except:
                pass
        
        # Configurar fondo de la ventana principal
        root.configure(bg=cls.COLORS['bg_main'])
        
        # === ESTILOS DE FRAME ===
        style.configure('TFrame',
                       background=cls.COLORS['bg_main'])
        
        style.configure('Card.TFrame',
                       background=cls.COLORS['bg_card'],
                       relief='flat')
        
        # === ESTILOS DE LABELFRAME ===
        style.configure('TLabelframe',
                       background=cls.COLORS['bg_card'],
                       borderwidth=1,
                       relief='solid')
        style.configure('TLabelframe.Label',
                       background=cls.COLORS['bg_card'],
                       foreground=cls.COLORS['primary'],
                       font=cls.FONTS['heading'])
        
        # Variante para secciones importantes
        style.configure('Primary.TLabelframe',
                       background=cls.COLORS['primary_bg'])
        style.configure('Primary.TLabelframe.Label',
                       background=cls.COLORS['primary_bg'],
                       foreground=cls.COLORS['primary_dark'],
                       font=cls.FONTS['subtitle'])
        
        # === ESTILOS DE LABEL ===
        style.configure('TLabel',
                       background=cls.COLORS['bg_card'],
                       foreground=cls.COLORS['text_primary'],
                       font=cls.FONTS['body'])
        
        style.configure('Title.TLabel',
                       font=cls.FONTS['title'],
                       foreground=cls.COLORS['primary_dark'])
        
        style.configure('Subtitle.TLabel',
                       font=cls.FONTS['subtitle'],
                       foreground=cls.COLORS['text_primary'])
        
        style.configure('Heading.TLabel',
                       font=cls.FONTS['heading'],
                       foreground=cls.COLORS['primary'])
        
        style.configure('Success.TLabel',
                       foreground=cls.COLORS['success'],
                       font=cls.FONTS['body_bold'])
        
        style.configure('Warning.TLabel',
                       foreground=cls.COLORS['warning'],
                       font=cls.FONTS['body_bold'])
        
        style.configure('Error.TLabel',
                       foreground=cls.COLORS['error'],
                       font=cls.FONTS['body_bold'])
        
        style.configure('Info.TLabel',
                       foreground=cls.COLORS['info'],
                       font=cls.FONTS['body_bold'])
        
        style.configure('Muted.TLabel',
                       foreground=cls.COLORS['text_secondary'],
                       font=cls.FONTS['small'])
        
        # === ESTILOS DE BOTÓN ===
        style.configure('TButton',
                       padding=(12, 6),
                       font=cls.FONTS['body'])
        
        style.configure('Primary.TButton',
                       padding=(16, 8),
                       font=cls.FONTS['body_bold'])
        
        style.configure('Success.TButton',
                       padding=(12, 6),
                       font=cls.FONTS['body_bold'])
        
        style.configure('Small.TButton',
                       padding=(8, 4),
                       font=cls.FONTS['small'])
        
        # === ESTILOS DE ENTRY ===
        style.configure('TEntry',
                       padding=(8, 4),
                       font=cls.FONTS['body'])
        
        # === ESTILOS DE COMBOBOX ===
        style.configure('TCombobox',
                       padding=(8, 4),
                       font=cls.FONTS['body'])
        
        # === ESTILOS DE TREEVIEW ===
        style.configure('Treeview',
                       background=cls.COLORS['bg_card'],
                       foreground=cls.COLORS['text_primary'],
                       fieldbackground=cls.COLORS['bg_card'],
                       rowheight=28,
                       font=cls.FONTS['body'])
        
        style.configure('Treeview.Heading',
                       background=cls.COLORS['primary'],
                       foreground=cls.COLORS['text_light'],
                       font=cls.FONTS['heading'],
                       padding=(8, 6),
                       relief='flat')
        
        style.map('Treeview',
                  background=[('selected', cls.COLORS['row_selected'])],
                  foreground=[('selected', cls.COLORS['text_light'])])
        
        style.map('Treeview.Heading',
                  background=[('active', cls.COLORS['primary_dark']),
                             ('pressed', cls.COLORS['primary_dark'])])
        
        # === ESTILOS DE NOTEBOOK (Pestañas) ===
        style.configure('TNotebook',
                       background=cls.COLORS['bg_main'],
                       tabmargins=(4, 4, 4, 0))
        
        style.configure('TNotebook.Tab',
                       padding=(16, 8),
                       font=cls.FONTS['body_bold'],
                       background=cls.COLORS['bg_header'],
                       foreground=cls.COLORS['text_secondary'])
        
        style.map('TNotebook.Tab',
                  background=[('selected', cls.COLORS['bg_card']),
                             ('active', cls.COLORS['primary_bg'])],
                  foreground=[('selected', cls.COLORS['primary']),
                             ('active', cls.COLORS['primary'])],
                  expand=[('selected', (1, 1, 1, 0))])
        
        # === ESTILOS DE SCROLLBAR ===
        style.configure('TScrollbar',
                       background=cls.COLORS['bg_header'],
                       troughcolor=cls.COLORS['bg_main'],
                       borderwidth=0,
                       arrowsize=14)
        
        # === ESTILOS DE PROGRESSBAR ===
        style.configure('TProgressbar',
                       background=cls.COLORS['primary'],
                       troughcolor=cls.COLORS['bg_header'])
        
        # === ESTILOS DE SEPARATOR ===
        style.configure('TSeparator',
                       background=cls.COLORS['border'])
    
    @classmethod
    def configure_treeview_tags(cls, tree: ttk.Treeview) -> None:
        """Configura los tags de colores para un Treeview."""
        tree.tag_configure('assigned', 
                          background=cls.COLORS['assigned'],
                          font=cls.FONTS['body'])
        tree.tag_configure('unassigned', 
                          background=cls.COLORS['unassigned'],
                          font=cls.FONTS['body'])
        tree.tag_configure('cancelled', 
                          background=cls.COLORS['cancelled'],
                          font=cls.FONTS['body'])
        tree.tag_configure('cancelled_other', 
                          background=cls.COLORS['cancelled_other'],
                          font=cls.FONTS['body_bold'])
        tree.tag_configure('credit', 
                          background=cls.COLORS['credit'],
                          font=cls.FONTS['body'])
        tree.tag_configure('even', 
                          background=cls.COLORS['row_even'])
        tree.tag_configure('odd', 
                          background=cls.COLORS['row_odd'])
    
    @classmethod
    def get_status_style(cls, status: str) -> dict:
        """Retorna estilo según el estado."""
        styles = {
            'success': {
                'bg': cls.COLORS['success_bg'],
                'fg': cls.COLORS['success'],
                'icon': '✅'
            },
            'warning': {
                'bg': cls.COLORS['warning_bg'],
                'fg': cls.COLORS['warning'],
                'icon': '⚠️'
            },
            'error': {
                'bg': cls.COLORS['error_bg'],
                'fg': cls.COLORS['error'],
                'icon': '❌'
            },
            'info': {
                'bg': cls.COLORS['info_bg'],
                'fg': cls.COLORS['info'],
                'icon': 'ℹ️'
            },
        }
        return styles.get(status, styles['info'])
