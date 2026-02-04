# -*- coding: utf-8 -*-
"""
Widgets personalizados para la GUI
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional, Callable


class TreeviewWithScroll(ttk.Frame):
    """Treeview con scrollbars integradas y funcionalidades extra."""
    
    def __init__(self, parent, columns: List[str], height: int = 15,
                 show: str = "headings", selectmode: str = "extended",
                 on_copy: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_copy = on_copy
        
        # Crear Treeview
        self.tree = ttk.Treeview(self, columns=columns, height=height,
                                 show=show, selectmode=selectmode)
        
        # Scrollbar vertical
        self.scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, 
                                      command=self.tree.yview)
        
        # Scrollbar horizontal
        self.scroll_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, 
                                      command=self.tree.xview)
        
        # Configurar scrollbars
        self.tree.configure(yscrollcommand=self.scroll_y.set,
                           xscrollcommand=self.scroll_x.set)
        
        # Layout con grid
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")
        
        # Configurar expansión
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Bindings
        self.tree.bind("<Control-c>", self._copy_selection)
        self.tree.bind("<Control-C>", self._copy_selection)
        self.tree.bind("<Button-3>", self._show_context_menu)
    
    def _copy_selection(self, event=None):
        """Copia la selección al portapapeles."""
        selection = self.tree.selection()
        if not selection:
            return
        
        lines = []
        for item in selection:
            values = self.tree.item(item, 'values')
            lines.append('\t'.join(str(v) for v in values))
        
        text = '\n'.join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        
        if self.on_copy:
            self.on_copy(text)
    
    def _copy_all(self):
        """Copia toda la tabla al portapapeles."""
        items = self.tree.get_children()
        if not items:
            return
        
        # Encabezados
        columns = self.tree['columns']
        headers = [self.tree.heading(col, 'text') for col in columns]
        lines = ['\t'.join(headers)]
        
        # Datos
        for item in items:
            values = self.tree.item(item, 'values')
            lines.append('\t'.join(str(v) for v in values))
        
        text = '\n'.join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        
        if self.on_copy:
            self.on_copy(text)
    
    def _show_context_menu(self, event):
        """Muestra menú contextual."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📋 Copiar selección (Ctrl+C)", 
                        command=self._copy_selection)
        menu.add_command(label="📄 Copiar toda la tabla", 
                        command=self._copy_all)
        menu.add_separator()
        menu.add_command(label="Cerrar", command=menu.destroy)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def configure_column(self, col: str, **kwargs):
        """Configura una columna."""
        self.tree.column(col, **kwargs)
    
    def configure_heading(self, col: str, **kwargs):
        """Configura un encabezado."""
        self.tree.heading(col, **kwargs)
    
    def insert(self, *args, **kwargs):
        """Inserta un item."""
        return self.tree.insert(*args, **kwargs)
    
    def delete(self, *args):
        """Elimina items."""
        self.tree.delete(*args)
    
    def get_children(self):
        """Obtiene los hijos."""
        return self.tree.get_children()
    
    def selection(self):
        """Obtiene la selección."""
        return self.tree.selection()
    
    def item(self, *args, **kwargs):
        """Accede a un item."""
        return self.tree.item(*args, **kwargs)
    
    def bind(self, *args, **kwargs):
        """Bind en el Treeview."""
        return self.tree.bind(*args, **kwargs)
    
    def tag_configure(self, *args, **kwargs):
        """Configura un tag."""
        return self.tree.tag_configure(*args, **kwargs)


class StatusBar(ttk.Frame):
    """Barra de estado profesional."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Icono de estado
        self.icon_label = ttk.Label(self, text="●", width=3)
        self.icon_label.pack(side=tk.LEFT, padx=(8, 4))
        
        # Mensaje
        self.message_label = ttk.Label(self, text="Listo")
        self.message_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Información adicional (derecha)
        self.info_label = ttk.Label(self, text="")
        self.info_label.pack(side=tk.RIGHT, padx=8)
        
        self._status = 'info'
    
    def set_status(self, message: str, status: str = 'info', info: str = ''):
        """Actualiza el estado."""
        self._status = status
        
        icons = {
            'success': ('●', '#2e7d32'),
            'warning': ('●', '#f57c00'),
            'error': ('●', '#c62828'),
            'info': ('●', '#1565c0'),
        }
        
        icon, color = icons.get(status, icons['info'])
        self.icon_label.configure(text=icon, foreground=color)
        self.message_label.configure(text=message)
        self.info_label.configure(text=info)


class SummaryPanel(ttk.LabelFrame):
    """Panel de resumen con estadísticas."""
    
    def __init__(self, parent, title: str = "📊 RESUMEN", **kwargs):
        super().__init__(parent, text=title, padding=(10, 8), **kwargs)
        
        self._items = {}
        self._row = 0
    
    def add_item(self, key: str, label: str, value: str = "0",
                 style: str = 'normal', column: int = 0) -> Tuple[ttk.Label, ttk.Label]:
        """Añade un item al resumen."""
        col_offset = column * 3
        
        # Label
        lbl = ttk.Label(self, text=label)
        lbl.grid(row=self._row, column=col_offset, sticky=tk.W, padx=(0, 4))
        
        # Valor
        val_style = {
            'normal': {},
            'bold': {'font': ('Segoe UI', 9, 'bold')},
            'success': {'font': ('Segoe UI', 9, 'bold'), 'foreground': '#2e7d32'},
            'warning': {'font': ('Segoe UI', 9, 'bold'), 'foreground': '#f57c00'},
            'error': {'font': ('Segoe UI', 9, 'bold'), 'foreground': '#c62828'},
            'primary': {'font': ('Segoe UI', 9, 'bold'), 'foreground': '#1565c0'},
            'large': {'font': ('Segoe UI', 12, 'bold'), 'foreground': '#2e7d32'},
        }
        
        val = ttk.Label(self, text=value, **val_style.get(style, {}))
        val.grid(row=self._row, column=col_offset + 1, sticky=tk.E, padx=(4, 20))
        
        self._items[key] = (lbl, val)
        
        if column == 0:
            self._row += 1
        
        return lbl, val
    
    def update_value(self, key: str, value: str):
        """Actualiza el valor de un item."""
        if key in self._items:
            _, val_label = self._items[key]
            val_label.configure(text=value)
    
    def get_value_label(self, key: str) -> Optional[ttk.Label]:
        """Obtiene el label de valor de un item."""
        if key in self._items:
            return self._items[key][1]
        return None


class InfoCard(ttk.Frame):
    """Tarjeta de información con icono y valor."""
    
    def __init__(self, parent, icon: str, title: str, value: str = "0",
                 color: str = '#1565c0', **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(style='Card.TFrame')
        
        # Icono
        self.icon_label = ttk.Label(self, text=icon, font=('Segoe UI', 24))
        self.icon_label.pack(side=tk.LEFT, padx=(10, 5))
        
        # Container para título y valor
        info_frame = ttk.Frame(self)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Título
        self.title_label = ttk.Label(info_frame, text=title,
                                     font=('Segoe UI', 8),
                                     foreground='#757575')
        self.title_label.pack(anchor=tk.W)
        
        # Valor
        self.value_label = ttk.Label(info_frame, text=value,
                                     font=('Segoe UI', 14, 'bold'),
                                     foreground=color)
        self.value_label.pack(anchor=tk.W)
    
    def set_value(self, value: str):
        """Actualiza el valor."""
        self.value_label.configure(text=value)


class SearchEntry(ttk.Frame):
    """Entry de búsqueda con icono y botón de limpiar."""
    
    def __init__(self, parent, placeholder: str = "Buscar...",
                 on_search: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_search = on_search
        self.placeholder = placeholder
        
        # Icono
        self.icon = ttk.Label(self, text="🔍", font=('Segoe UI', 10))
        self.icon.pack(side=tk.LEFT, padx=(4, 0))
        
        # Entry
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=30)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        
        # Botón limpiar
        self.clear_btn = ttk.Button(self, text="✕", width=3,
                                    command=self._clear)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        # Bindings
        self.var.trace_add('write', self._on_change)
        self.entry.bind('<Return>', lambda e: self._trigger_search())
    
    def _on_change(self, *args):
        """Llamado cuando cambia el texto."""
        if self.on_search:
            self.on_search(self.var.get())
    
    def _clear(self):
        """Limpia el entry."""
        self.var.set('')
    
    def _trigger_search(self):
        """Dispara la búsqueda."""
        if self.on_search:
            self.on_search(self.var.get())
    
    def get(self) -> str:
        """Obtiene el valor."""
        return self.var.get()
    
    def set(self, value: str):
        """Establece el valor."""
        self.var.set(value)
