#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TabAnotaciones - Pestaña de Notas Adhesivas (Sticky Notes) con Checklist
Versión mejorada con mejor rendimiento, filtrado por fecha, y soporte de imágenes
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import mimetypes
import webbrowser
import time
import os
import re
import json
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Tuple, Optional

# Intentar soporte DnD (tkinterdnd2)
try:
    from tkinterdnd2 import DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

# Intentar soporte de Pillow para pegar imagen desde portapapeles
try:
    from PIL import ImageGrab, Image, ImageTk
    HAS_PIL = True
except Exception:
    HAS_PIL = False

try:
    import database_local as db_local
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TabAnotaciones:
    """
    Pestaña de anotaciones con sticky notes arrastrables.
    Incluye funcionalidad de checklist/to-do y soporte de imágenes.
    Versión mejorada: sin límite de notas, filtrado por fecha robusto.
    """
    
    # Configuración de distribución de notas - más compacta
    NOTA_ANCHO = 200
    NOTA_ALTO = 180  # Altura reducida
    MARGEN_X = 15
    MARGEN_Y = 15
    COLUMNAS_MAX = 8  # Más columnas para mejor uso del espacio
    
    def __init__(self, parent: ttk.Frame, app, datastore):
        """
        Inicializa la pestaña de anotaciones.
        
        Args:
            parent: Frame padre donde se creará la pestaña
            app: Referencia a la aplicación principal
            datastore: Referencia al DataStore compartido
        """
        self.parent = parent
        self.app = app
        self.ds = datastore

        # Suscribirse a cambios del DataStore (para fecha global)
        try:
            if hasattr(self.ds, 'suscribir'):
                self.ds.suscribir(self.refrescar)
        except Exception:
            pass
        
        # Variables de estado
        self.notas_widgets = {}  # {window_id: {'nota_id': int, 'frame': tk.Frame}}
        self.color_nota_var = None
        self.filtro_notas_var = None
        self.fecha_var = None
        self.canvas_notas = None
        self._notas_cache = {}  # Cache para optimizar búsquedas
        self._cargando = False  # Flag para evitar carga simultánea
        self._pending_refresh = False  # Flag para refresh pendiente
        self._drag_data = {}  # Datos de arrastre temporal
        
        self._crear_interfaz()

    def _fecha_actual(self) -> str:
        """Retorna la fecha actual usada por la pestaña (preferir DataStore)."""
        try:
            if hasattr(self.ds, 'fecha') and self.ds.fecha:
                fecha = self.ds.fecha
                # Validar formato
                datetime.strptime(fecha, '%Y-%m-%d')
                return fecha
        except (ValueError, AttributeError, TypeError):
            pass
        return datetime.now().strftime('%Y-%m-%d')

    def _ensure_attachments_dir(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        attach_dir = os.path.join(base, 'attachments')
        os.makedirs(attach_dir, exist_ok=True)
        return attach_dir

    def _save_file_to_attachments(self, nota_id: int, src_path: str) -> str:
        """Copia src_path a attachments/ y actualiza DB; retorna ruta relativa guardada."""
        if not HAS_DB:
            return ''
        try:
            attach_dir = self._ensure_attachments_dir()
            nombre = os.path.basename(src_path)
            prefijo = time.strftime('%Y%m%d%H%M%S')
            dest_name = f"{prefijo}_{nombre}"
            dest_path = os.path.join(attach_dir, dest_name)
            shutil.copy2(src_path, dest_path)
            rel_path = os.path.relpath(dest_path, start=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

            # Actualizar DB: obtener lista actual y anexar
            fecha = self._fecha_actual()
            notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
            nota = next((n for n in notas if n['id'] == nota_id), None)
            attachments = nota.get('attachments') or [] if nota else []
            attachments.append(rel_path)
            db_local.actualizar_anotacion(nota_id, attachments=attachments)

            # Refrescar UI
            self._cargar_anotaciones()
            return rel_path
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo guardar adjunto: {e}')
            return ''

    def _handle_drop(self, event, nota_id: int):
        """Maneja archivos arrastrados sobre una nota (requiere tkinterdnd2)."""
        data = event.data
        # data puede venir como '{C:/ruta/archivo1} {C:/ruta/archivo2}' o con espacios
        paths = re.findall(r"\{([^}]+)\}", data)
        if not paths:
            # intentar separar por espacios
            paths = data.split()
        for p in paths:
            p = p.strip()
            if os.path.exists(p):
                # Aceptar solo archivos (imágenes/videos/otros)
                self._save_file_to_attachments(nota_id, p)

    def _handle_paste(self, event, nota_id: int, text_widget=None):
        """Maneja pegar en el editor: si hay imagen en portapapeles, la guarda."""
        if not HAS_PIL:
            return None
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                return None  # No hay imagen en portapapeles
            
            # Guardar imagen en attachments
            attach_dir = self._ensure_attachments_dir()
            fname = f"img_{time.strftime('%Y%m%d%H%M%S')}.png"
            dest_path = os.path.join(attach_dir, fname)
            
            # Convertir a RGB si es necesario
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(dest_path, 'PNG')
            
            rel_path = os.path.relpath(dest_path, 
                start=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

            # Actualizar DB
            if HAS_DB:
                fecha = self._fecha_actual()
                notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
                nota = next((n for n in notas if n['id'] == nota_id), None)
                if nota:
                    attachments = nota.get('attachments') or []
                    attachments.append(rel_path)
                    db_local.actualizar_anotacion(nota_id, attachments=attachments)

            # Refrescar UI
            self._cargar_anotaciones()
            messagebox.showinfo('✓ Imagen pegada', f'Imagen guardada: {fname}')
            return 'break'
        except Exception as e:
            messagebox.showerror('Error', f'Error pegando imagen: {e}')
            return None
    
    def _pegar_imagen_global(self, event=None):
        """Pega imagen del portapapeles en la primera nota visible o pregunta dónde."""
        if not HAS_PIL:
            return None
        
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                return None  # No hay imagen en portapapeles
            
            # Buscar notas disponibles
            if not self.notas_widgets:
                messagebox.showwarning('Sin notas', 'Crea una nota primero para pegar la imagen')
                return 'break'
            
            # Si hay una sola nota, usar esa
            if len(self.notas_widgets) == 1:
                nota_id = list(self.notas_widgets.values())[0]['nota_id']
                return self._handle_paste(event, nota_id)
            
            # Si hay múltiples notas, mostrar diálogo para elegir
            self._mostrar_selector_nota_para_pegar(img)
            return 'break'
            
        except Exception as e:
            print(f"[DEBUG] Error en pegar global: {e}")
            return None
    
    def _mostrar_selector_nota_para_pegar(self, img):
        """Muestra un diálogo para elegir en qué nota pegar la imagen."""
        if not HAS_DB:
            return
        
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=False, fecha=fecha)
        
        if not notas:
            messagebox.showwarning('Sin notas', 'No hay notas activas')
            return
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("📋 ¿En qué nota pegar la imagen?")
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.geometry("350x300")
        dialog.resizable(False, False)
        
        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Selecciona la nota:", 
                  font=("Segoe UI", 11, "bold")).pack(pady=(0, 10))
        
        # Listbox con las notas
        listbox = tk.Listbox(frame, font=("Segoe UI", 10), height=10)
        listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        for nota in notas:
            titulo = nota.get('titulo', 'Sin título')[:30]
            attachments = nota.get('attachments') or []
            icon = "📷" if attachments else "📝"
            listbox.insert(tk.END, f"{icon} {titulo}")
        
        if notas:
            listbox.selection_set(0)
        
        def pegar_en_nota():
            sel = listbox.curselection()
            if not sel:
                return
            nota = notas[sel[0]]
            dialog.destroy()
            self._handle_paste(None, nota['id'])
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT)
        
        btn_pegar = tk.Button(btn_frame, text="📋 Pegar aquí", 
                             font=("Segoe UI", 10, "bold"),
                             bg="#4CAF50", fg="white",
                             command=pegar_en_nota)
        btn_pegar.pack(side=tk.RIGHT)
        
        # Doble clic para pegar
        listbox.bind('<Double-Button-1>', lambda e: pegar_en_nota())
        
        # Centrar
        dialog.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _crear_interfaz(self):
        """Crea la interfaz de la pestaña."""
        tab = self.parent
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # ══════════════════════════════════════════════════════════════
        # BARRA DE HERRAMIENTAS - Diseño responsivo con grid
        # ══════════════════════════════════════════════════════════════
        toolbar_container = ttk.Frame(tab)
        toolbar_container.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 3))
        toolbar_container.columnconfigure(0, weight=1)
        
        # Fila 1: Botones principales
        toolbar_row1 = ttk.Frame(toolbar_container)
        toolbar_row1.grid(row=0, column=0, sticky="ew", pady=2)
        
        # Frame izquierdo: botones de crear
        left_frame = ttk.Frame(toolbar_row1)
        left_frame.pack(side=tk.LEFT, fill=tk.X)
        
        ttk.Button(left_frame, text="➕ Nota", command=self._nueva_anotacion, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_frame, text="📋 Lista", command=self._nueva_lista, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_frame, text="🔄", command=self._reorganizar_notas, width=4).pack(side=tk.LEFT, padx=2)
        
        # Variable de fecha (se sincroniza con DataStore)
        self.fecha_var = tk.StringVar(value=self._fecha_actual())
        
        # Frame central: colores (compacto)
        color_frame = ttk.Frame(toolbar_row1)
        color_frame.pack(side=tk.LEFT, padx=10)
        
        self.color_nota_var = tk.StringVar(value="#FFEB3B")
        colores = [
            ("#FFEB3B", "🟡"),  # Amarillo
            ("#81D4FA", "🔵"),  # Azul claro
            ("#A5D6A7", "🟢"),  # Verde claro
            ("#FFAB91", "🟠"),  # Naranja
            ("#CE93D8", "🟣"),  # Morado
            ("#EF9A9A", "🔴"),  # Rojo claro
        ]
        for color, emoji in colores:
            btn = tk.Button(color_frame, text="", width=2, height=1, bg=color, 
                           relief=tk.FLAT, bd=1,
                           command=lambda c=color: self.color_nota_var.set(c))
            btn.pack(side=tk.LEFT, padx=1)
        
        # Frame derecho: filtro (compacto)
        right_frame = ttk.Frame(toolbar_row1)
        right_frame.pack(side=tk.RIGHT, padx=5)
        
        self.filtro_notas_var = tk.StringVar(value="Activas")
        filtro_combo = ttk.Combobox(right_frame, textvariable=self.filtro_notas_var,
                                    values=["Activas", "Archivadas", "Todas", "Eliminadas"],
                                    state="readonly", width=10)
        filtro_combo.pack(side=tk.LEFT)
        filtro_combo.bind("<<ComboboxSelected>>", lambda e: self._cargar_anotaciones())
        
        # ══════════════════════════════════════════════════════════════
        # CANVAS PARA STICKY NOTES
        # ══════════════════════════════════════════════════════════════
        frame_canvas = ttk.Frame(tab)
        frame_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        frame_canvas.columnconfigure(0, weight=1)
        frame_canvas.rowconfigure(0, weight=1)
        
        # Obtener color de fondo según el modo
        bg_color = "#2d2d2d" if getattr(self.app, 'modo_oscuro', True) else "#e0e0e0"
        self.canvas_notas = tk.Canvas(frame_canvas, bg=bg_color, highlightthickness=0)
        self.canvas_notas.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbars
        scrolly = ttk.Scrollbar(frame_canvas, orient=tk.VERTICAL, command=self.canvas_notas.yview)
        scrolly.grid(row=0, column=1, sticky="ns")
        scrollx = ttk.Scrollbar(frame_canvas, orient=tk.HORIZONTAL, command=self.canvas_notas.xview)
        scrollx.grid(row=1, column=0, sticky="ew")
        
        self.canvas_notas.configure(yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        self.canvas_notas.configure(scrollregion=(0, 0, 2000, 2000))
        
        # Bind para scroll con rueda del mouse
        self.canvas_notas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas_notas.bind("<Button-4>", self._on_mousewheel)
        self.canvas_notas.bind("<Button-5>", self._on_mousewheel)
        
        # Binding global para pegar imagen desde portapapeles
        self.canvas_notas.bind('<Control-v>', self._pegar_imagen_global)
        self.canvas_notas.bind('<Control-V>', self._pegar_imagen_global)
        
        # Cargar anotaciones existentes (sin threading durante inicialización)
        self._cargar_anotaciones(use_threading=False)

    def _on_fecha_cambio(self):
        """Maneja el cambio de fecha desde el entry de la pestaña."""
        nueva = self.fecha_var.get().strip()
        try:
            datetime.strptime(nueva, '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning('Fecha inválida', 'Formato: YYYY-MM-DD (ej: 2026-02-04)')
            self.fecha_var.set(self._fecha_actual())
            return

        # Actualizar DataStore para coherencia global
        try:
            if hasattr(self.ds, 'fecha'):
                self.ds.fecha = nueva
        except Exception:
            pass

        # Refrescar
        self._cargar_anotaciones()

    def _validar_fecha_entrada(self):
        """Valida la fecha al perder el foco."""
        nueva = self.fecha_var.get().strip()
        try:
            datetime.strptime(nueva, '%Y-%m-%d')
        except ValueError:
            self.fecha_var.set(self._fecha_actual())

    def _cambiar_fecha(self, dias: int):
        """Cambia la fecha por N días (positivo o negativo)."""
        try:
            fecha_actual = datetime.strptime(self.fecha_var.get(), '%Y-%m-%d')
            nueva_fecha = fecha_actual + timedelta(days=dias)
            self._ir_a_fecha(nueva_fecha.strftime('%Y-%m-%d'))
        except ValueError:
            self.fecha_var.set(self._fecha_actual())

    def _ir_a_fecha(self, fecha_str: str):
        """Cambia a una fecha específica."""
        try:
            datetime.strptime(fecha_str, '%Y-%m-%d')
            self.fecha_var.set(fecha_str)
            self._on_fecha_cambio()
        except ValueError:
            messagebox.showwarning('Fecha inválida', 'Formato: YYYY-MM-DD')
    
    def _on_mousewheel(self, event):
        """Maneja el scroll con rueda del mouse."""
        if event.num == 4:
            self.canvas_notas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas_notas.yview_scroll(1, "units")
        else:
            self.canvas_notas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _calcular_siguiente_posicion(self) -> tuple:
        """
        Calcula la siguiente posición disponible para una nueva nota.
        Distribuye las notas en una cuadrícula evitando superposiciones.
        
        Returns:
            Tuple (x, y) con la posición calculada
        """
        if not HAS_DB:
            return (self.MARGEN_X, self.MARGEN_Y)
        
        # Obtener posiciones de notas existentes
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=False, fecha=fecha)
        
        if not notas:
            return (self.MARGEN_X, self.MARGEN_Y)
        
        # Crear set de posiciones ocupadas (redondeadas a grid)
        posiciones_ocupadas = set()
        for nota in notas:
            x = nota.get('pos_x', 0)
            y = nota.get('pos_y', 0)
            # Convertir a índices de grid
            col = round((x - self.MARGEN_X) / (self.NOTA_ANCHO + self.MARGEN_X))
            fila = round((y - self.MARGEN_Y) / (self.NOTA_ALTO + self.MARGEN_Y))
            posiciones_ocupadas.add((col, fila))
        
        # Buscar primera posición libre
        for fila in range(100):  # Máximo 100 filas
            for col in range(self.COLUMNAS_MAX):
                if (col, fila) not in posiciones_ocupadas:
                    x = self.MARGEN_X + col * (self.NOTA_ANCHO + self.MARGEN_X)
                    y = self.MARGEN_Y + fila * (self.NOTA_ALTO + self.MARGEN_Y)
                    return (x, y)
        
        # Fallback: posición por defecto
        return (self.MARGEN_X, self.MARGEN_Y)
    
    def _reorganizar_notas(self):
        """Reorganiza todas las notas en una cuadrícula ordenada."""
        if not HAS_DB:
            return
        
        fecha = self._fecha_actual()
        filtro = self.filtro_notas_var.get() if self.filtro_notas_var else "Activas"
        
        # Obtener notas según el filtro actual (incluir eliminadas para poder filtrar)
        notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
        
        # Aplicar filtro
        if filtro == "Eliminadas":
            notas = [n for n in notas if n.get('eliminada', 0) == 1]
        elif filtro == "Archivadas":
            notas = [n for n in notas if n.get('archivada', 0) == 1 and n.get('eliminada', 0) == 0]
        elif filtro == "Activas":
            notas = [n for n in notas if n.get('archivada', 0) == 0 and n.get('eliminada', 0) == 0]
        elif filtro == "Todas":
            notas = [n for n in notas if n.get('eliminada', 0) == 0]
        
        if not notas:
            messagebox.showinfo("Reorganizar", "No hay notas para reorganizar")
            return
        
        print(f"[DEBUG] Reorganizando {len(notas)} notas")
        
        # Actualizar posiciones en la BD
        for idx, nota in enumerate(notas):
            col = idx % self.COLUMNAS_MAX
            fila = idx // self.COLUMNAS_MAX
            x = self.MARGEN_X + col * (self.NOTA_ANCHO + self.MARGEN_X)
            y = self.MARGEN_Y + fila * (self.NOTA_ALTO + self.MARGEN_Y)
            
            print(f"[DEBUG] Nota {nota['id']} -> pos ({x}, {y})")
            db_local.actualizar_anotacion(nota['id'], pos_x=x, pos_y=y)
        
        # Actualizar visualmente en el canvas directamente
        for window_id, info in self.notas_widgets.items():
            nota_id = info['nota_id']
            # Buscar la nota en la lista
            for idx, nota in enumerate(notas):
                if nota['id'] == nota_id:
                    col = idx % self.COLUMNAS_MAX
                    fila = idx // self.COLUMNAS_MAX
                    x = self.MARGEN_X + col * (self.NOTA_ANCHO + self.MARGEN_X)
                    y = self.MARGEN_Y + fila * (self.NOTA_ALTO + self.MARGEN_Y)
                    self.canvas_notas.coords(window_id, x, y)
                    break
        
        self._actualizar_scrollregion()
        messagebox.showinfo("Reorganizado", f"Se reorganizaron {len(notas)} notas")
    
    def _cargar_anotaciones(self, use_threading=True):
        """
        Carga las anotaciones desde SQLite de forma eficiente.
        Evita bloqueos UI usando threading si hay muchas notas.
        Garantiza que todas las notas se cargan correctamente.
        
        Args:
            use_threading: Si False, carga de forma síncrona (útil durante inicialización)
        """
        if not HAS_DB:
            return
        
        # Evitar carga simultánea
        if self._cargando:
            self._pending_refresh = True
            return
        
        self._cargando = True
        
        # Obtener valores de variables tkinter en el hilo principal ANTES de crear el hilo
        # Verificar que filtro_notas_var esté inicializado
        if self.filtro_notas_var is None:
            filtro = "Activas"
        else:
            filtro = self.filtro_notas_var.get()
        fecha = self._fecha_actual()
        
        def cargar_datos():
            """Función que carga los datos (puede ejecutarse en cualquier hilo)"""
            try:
                print(f"[DEBUG] Cargando anotaciones para fecha: {fecha}, filtro: {filtro}")
                
                # Obtener notas con la fecha específica (incluir eliminadas para poder filtrar)
                notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
                
                print(f"[DEBUG] Total de notas en BD para {fecha}: {len(notas)}")
                
                # Filtrar por estado de archivo y eliminación
                if filtro == "Eliminadas":
                    notas = [n for n in notas if n.get('eliminada', 0) == 1]
                elif filtro == "Archivadas":
                    notas = [n for n in notas if n.get('archivada', 0) == 1 and n.get('eliminada', 0) == 0]
                elif filtro == "Activas":
                    notas = [n for n in notas if n.get('archivada', 0) == 0 and n.get('eliminada', 0) == 0]
                # Si filtro == "Todas", mantener todas las notas excepto eliminadas por defecto
                elif filtro == "Todas":
                    notas = [n for n in notas if n.get('eliminada', 0) == 0]
                
                print(f"[DEBUG] Notas después de filtro '{filtro}': {len(notas)}")
                
                # Actualizar cache
                self._notas_cache = {n['id']: n for n in notas}
                
                return notas
                
            except Exception as e:
                print(f"[ERROR] Error cargando anotaciones: {e}")
                import traceback
                traceback.print_exc()
                return []
        
        def finalizar():
            self._cargando = False
            if self._pending_refresh:
                self._pending_refresh = False
                self.parent.after(100, self._cargar_anotaciones)
        
        if use_threading:
            # Usar threading para no bloquear UI
            def cargar_en_background():
                try:
                    notas = cargar_datos()
                    # Actualizar UI en thread principal
                    self.parent.after(0, self._actualizar_canvas_notas, notas)
                except Exception as e:
                    print(f"[ERROR] Error en background: {e}")
                finally:
                    self.parent.after(0, finalizar)
            
            thread = threading.Thread(target=cargar_en_background, daemon=True)
            thread.start()
        else:
            # Carga síncrona (para inicialización)
            try:
                notas = cargar_datos()
                self._actualizar_canvas_notas(notas)
            finally:
                finalizar()

    def _actualizar_canvas_notas(self, notas: List[Dict]):
        """Actualiza el canvas con las notas (debe ejecutarse en thread principal)."""
        try:
            print(f"[DEBUG] _actualizar_canvas_notas: Actualizando {len(notas)} notas")
            
            # Limpiar solo los widgets que ya no existen en la lista
            widget_ids_a_eliminar = []
            for widget_id in list(self.notas_widgets.keys()):
                nota_id = self.notas_widgets[widget_id].get('nota_id')
                if not any(n['id'] == nota_id for n in notas):
                    widget_ids_a_eliminar.append(widget_id)
            
            # Eliminar widgets que ya no tienen nota
            for widget_id in widget_ids_a_eliminar:
                try:
                    self.canvas_notas.delete(widget_id)
                    del self.notas_widgets[widget_id]
                except Exception as e:
                    print(f"[DEBUG] Error eliminando widget {widget_id}: {e}")
            
            # Actualizar o crear notas
            notas_ids_existentes = {self.notas_widgets[w].get('nota_id') for w in self.notas_widgets}
            
            for nota in notas:
                nota_id = nota['id']
                
                if nota_id not in notas_ids_existentes:
                    # Nueva nota - crear
                    print(f"[DEBUG] Creando nueva nota {nota_id}")
                    self._crear_sticky_note(nota)
                else:
                    # Nota existente - verificar que está en cache
                    if nota_id not in self._notas_cache:
                        self._notas_cache[nota_id] = nota
                    print(f"[DEBUG] Nota {nota_id} ya existe, manteniendo")
            
            print(f"[DEBUG] Total de widgets en canvas: {len(self.notas_widgets)}")
            
            # Actualizar scrollregion
            self._actualizar_scrollregion()
            
        except Exception as e:
            print(f"[ERROR] Error en _actualizar_canvas_notas: {e}")
            import traceback
            traceback.print_exc()
    
    def _actualizar_scrollregion(self):
        """Actualiza el área de scroll basado en las notas."""
        if not self.notas_widgets:
            self.canvas_notas.configure(scrollregion=(0, 0, 2000, 2000))
            return
        
        max_x, max_y = 0, 0
        for widget_id in self.notas_widgets:
            coords = self.canvas_notas.coords(widget_id)
            if coords:
                max_x = max(max_x, coords[0] + self.NOTA_ANCHO + 50)
                max_y = max(max_y, coords[1] + self.NOTA_ALTO + 50)
        
        self.canvas_notas.configure(scrollregion=(0, 0, max(2000, max_x), max(2000, max_y)))
    
    def _crear_sticky_note(self, nota: dict):
        """Crea un sticky note en el canvas."""
        nota_id = nota['id']
        x = nota.get('pos_x', 20)
        y = nota.get('pos_y', 20)
        ancho = nota.get('ancho', self.NOTA_ANCHO)
        color = nota.get('color', '#FFEB3B')
        titulo = nota.get('titulo', 'Sin título')
        contenido = nota.get('contenido', '')
        prioridad = nota.get('prioridad', 'normal')
        archivada = nota.get('archivada', 0)
        eliminada = nota.get('eliminada', 0)
        es_checklist = nota.get('es_checklist', 0)
        attachments = nota.get('attachments') or []
        
        # Ajustar altura según contenido
        altura_base = nota.get('alto', self.NOTA_ALTO)
        if attachments:
            # Agregar espacio extra para el botón y miniaturas
            altura = max(altura_base, 280)
        else:
            altura = altura_base
        
        # Frame para la nota
        frame = tk.Frame(self.canvas_notas, bg=color, bd=2, relief=tk.RAISED)
        # Registrar drop si está disponible
        if HAS_DND:
            try:
                frame.drop_target_register(DND_FILES)
                frame.dnd_bind('<<Drop>>', lambda e, nid=nota_id: self._handle_drop(e, nid))
            except Exception:
                pass
        
        # Barra de título - altura fija y compacta
        barra = tk.Frame(frame, bg=self._oscurecer_color(color), height=22)
        barra.pack(fill=tk.X)
        barra.pack_propagate(False)
        
        # Indicador de prioridad
        prioridad_icons = {'baja': '⬇️', 'normal': '➖', 'alta': '⬆️', 'urgente': '🔥'}
        icon = prioridad_icons.get(prioridad, '➖')
        
        # Indicador de checklist
        tipo_icon = '☑️' if es_checklist else '📝'
        
        # Indicador de adjuntos (attachments ya se obtuvieron arriba)
        attach_icon = f"📎{len(attachments)}" if attachments else ''
        eliminada_icon = '🗑️' if eliminada else ''
        # Título más corto para evitar overflow
        titulo_corto = titulo[:10] + "…" if len(titulo) > 10 else titulo
        titulo_display = f"{tipo_icon}{icon}{titulo_corto}"
        
        lbl_titulo = tk.Label(barra, text=titulo_display, 
                              bg=self._oscurecer_color(color),
                              font=("Segoe UI", 8, "bold"), anchor="w",
                              fg="#999999" if eliminada else "black")
        lbl_titulo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Doble clic para renombrar el título directamente
        lbl_titulo.bind("<Double-Button-1>", lambda e: self._renombrar_titulo_inline(nota_id, barra, lbl_titulo, color))
        
        # Botones de control - más compactos con padding reducido
        btn_frame = tk.Frame(barra, bg=self._oscurecer_color(color))
        btn_frame.pack(side=tk.RIGHT)
        
        # Estilo común para botones compactos
        btn_style = {"font": ("Segoe UI", 7), "bd": 0, "padx": 1, "pady": 0,
                     "bg": self._oscurecer_color(color), "width": 2}
        
        # Botón para adjuntar foto rápidamente
        tk.Button(btn_frame, text="📷", command=lambda: self._adjuntar_foto_rapido(nota_id), **btn_style).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="✏️", command=lambda: self._editar_anotacion(nota_id), **btn_style).pack(side=tk.LEFT)
        
        if eliminada:
            tk.Button(btn_frame, text="♻️", command=lambda: self._restaurar_nota(nota_id), **btn_style).pack(side=tk.LEFT)
        elif archivada:
            tk.Button(btn_frame, text="📤", command=lambda: self._desarchivar_nota(nota_id), **btn_style).pack(side=tk.LEFT)
        else:
            tk.Button(btn_frame, text="📥", command=lambda: self._archivar_nota(nota_id), **btn_style).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="❌", command=lambda: self._eliminar_anotacion(nota_id), **btn_style).pack(side=tk.LEFT)
        
        # Contenido de la nota
        if es_checklist:
            self._crear_contenido_checklist(frame, nota_id, contenido, color)
        else:
            self._crear_contenido_texto(frame, nota_id, contenido, color)
        
        # Mostrar miniaturas de imágenes si hay adjuntos de imagen
        if attachments:
            self._crear_vista_adjuntos(frame, nota_id, attachments, color)
        
        # Grip de redimensionamiento en esquina inferior derecha - compacto
        grip_frame = tk.Frame(frame, bg=color, height=14)
        grip_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        grip = tk.Label(grip_frame, text="◢", font=("Segoe UI", 8), 
                        bg=self._oscurecer_color(color), fg="#888888",
                        cursor="bottom_right_corner", padx=1, pady=0)
        grip.pack(side=tk.RIGHT, anchor="se")
        
        # Crear ventana en canvas
        window_id = self.canvas_notas.create_window(x, y, window=frame, anchor="nw", 
                                                     width=ancho, height=altura)
        
        self.notas_widgets[window_id] = {'nota_id': nota_id, 'frame': frame, 'ancho': ancho, 'alto': altura}
        
        # Hacer la nota arrastrable desde la barra de título y el label
        self._hacer_arrastrable(window_id, barra, nota_id)
        self._hacer_arrastrable(window_id, lbl_titulo, nota_id)
        
        # Hacer la nota redimensionable desde el grip
        self._hacer_redimensionable(window_id, grip, nota_id, ancho, altura)
        
        # Binding para pegar imagen con Ctrl+V en cualquier parte de la nota
        frame.bind('<Control-v>', lambda e, nid=nota_id: self._handle_paste(e, nid))
        frame.bind('<Control-V>', lambda e, nid=nota_id: self._handle_paste(e, nid))
        barra.bind('<Control-v>', lambda e, nid=nota_id: self._handle_paste(e, nid))
        barra.bind('<Control-V>', lambda e, nid=nota_id: self._handle_paste(e, nid))
    
    def _renombrar_titulo_inline(self, nota_id: int, barra: tk.Frame, lbl_titulo: tk.Label, color: str):
        """Permite renombrar el título de la nota directamente sin modal."""
        # Obtener título actual (sin los iconos)
        if not HAS_DB:
            return
        
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
        nota = next((n for n in notas if n['id'] == nota_id), None)
        if not nota:
            return
        
        titulo_actual = nota.get('titulo', 'Sin título')
        
        # Ocultar el label y crear un Entry en su lugar
        lbl_titulo.pack_forget()
        
        entry = tk.Entry(barra, font=("Segoe UI", 9, "bold"),
                         bg=self._oscurecer_color(color), bd=0,
                         highlightthickness=1, highlightcolor="#2196F3")
        entry.insert(0, titulo_actual)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        def guardar_titulo(event=None):
            nuevo_titulo = entry.get().strip()
            if not nuevo_titulo:
                nuevo_titulo = titulo_actual
            
            # Actualizar en BD
            try:
                db_local.actualizar_anotacion(nota_id, titulo=nuevo_titulo)
            except Exception as e:
                print(f"[ERROR] No se pudo actualizar título: {e}")
            
            # Destruir entry y recargar notas
            entry.destroy()
            self._cargar_anotaciones()
        
        def cancelar(event=None):
            entry.destroy()
            lbl_titulo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        entry.bind("<Return>", guardar_titulo)
        entry.bind("<Escape>", cancelar)
        entry.bind("<FocusOut>", guardar_titulo)
    
    def _crear_contenido_texto(self, parent, nota_id, contenido, color):
        """Crea el contenido de texto normal."""
        txt = tk.Text(parent, bg=color, font=("Segoe UI", 9), wrap=tk.WORD, 
                      width=25, height=6, bd=0, highlightthickness=0)
        txt.insert("1.0", contenido)
        txt.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Guardar al perder foco (con debounce)
        def guardar_con_delay():
            contenido_nuevo = txt.get("1.0", tk.END).strip()
            self.parent.after(500, lambda: self._guardar_contenido_nota(nota_id, contenido_nuevo))
        
        txt.bind("<FocusOut>", lambda e: guardar_con_delay())
        # Pegar imagen desde portapapeles (Ctrl+V)
        txt.bind('<Control-v>', lambda e, nid=nota_id, t=txt: self._handle_paste(e, nid, t))
        txt.bind('<Control-V>', lambda e, nid=nota_id, t=txt: self._handle_paste(e, nid, t))
    
    def _crear_contenido_checklist(self, parent, nota_id, contenido, color):
        """Crea el contenido como checklist."""
        # Frame scrollable para los items
        frame_items = tk.Frame(parent, bg=color)
        frame_items.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Parsear items del checklist
        # Formato: "[x] Item completado\n[ ] Item pendiente"
        items = self._parsear_checklist(contenido)
        
        for idx, (completado, texto) in enumerate(items):
            self._crear_item_checklist(frame_items, nota_id, idx, completado, texto, color)
        
        # Botón para agregar item
        btn_add = tk.Button(frame_items, text="+ Agregar", font=("Segoe UI", 8),
                           bg=self._oscurecer_color(color), bd=0,
                           command=lambda: self._agregar_item_checklist(nota_id))
        btn_add.pack(anchor="w", pady=(5, 0))
    
    def _parsear_checklist(self, contenido: str) -> list:
        """
        Parsea el contenido como checklist.
        Formato: "[x] Item completado" o "[ ] Item pendiente"
        """
        items = []
        for linea in contenido.split('\n'):
            linea = linea.strip()
            if not linea:
                continue
            
            if linea.startswith('[x]') or linea.startswith('[X]'):
                items.append((True, linea[3:].strip()))
            elif linea.startswith('[ ]'):
                items.append((False, linea[3:].strip()))
            else:
                # Item sin formato, asumir no completado
                items.append((False, linea))
        
        return items
    
    def _formatear_checklist(self, items: list) -> str:
        """Convierte lista de items a string."""
        lineas = []
        for completado, texto in items:
            marca = '[x]' if completado else '[ ]'
            lineas.append(f"{marca} {texto}")
        return '\n'.join(lineas)
    
    def _crear_item_checklist(self, parent, nota_id, idx, completado, texto, color):
        """Crea un item del checklist."""
        frame = tk.Frame(parent, bg=color)
        frame.pack(fill=tk.X, pady=1)
        
        var_check = tk.BooleanVar(value=completado)
        
        chk = tk.Checkbutton(frame, variable=var_check, bg=color, 
                             activebackground=color,
                             command=lambda: self._toggle_item_checklist(nota_id, idx, var_check.get()))
        chk.pack(side=tk.LEFT)
        
        # Texto del item (tachado si completado)
        font_style = ("Segoe UI", 9, "overstrike") if completado else ("Segoe UI", 9)
        fg_color = "#888888" if completado else "#000000"
        
        lbl = tk.Label(frame, text=texto[:30], bg=color, fg=fg_color,
                       font=font_style, anchor="w")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Botón eliminar item
        btn_del = tk.Button(frame, text="×", font=("Segoe UI", 8), bd=0,
                           bg=color, fg="#cc0000",
                           command=lambda: self._eliminar_item_checklist(nota_id, idx))
        btn_del.pack(side=tk.RIGHT)
    
    def _toggle_item_checklist(self, nota_id: int, idx: int, completado: bool):
        """Marca/desmarca un item del checklist."""
        if not HAS_DB:
            return
        
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
        nota = next((n for n in notas if n['id'] == nota_id), None)
        if not nota:
            return
        
        items = self._parsear_checklist(nota.get('contenido', ''))
        if 0 <= idx < len(items):
            items[idx] = (completado, items[idx][1])
            nuevo_contenido = self._formatear_checklist(items)
            db_local.actualizar_anotacion(nota_id, contenido=nuevo_contenido)
            self._cargar_anotaciones()
    
    def _agregar_item_checklist(self, nota_id: int):
        """Agrega un nuevo item al checklist."""
        dialog = tk.Toplevel(self.app.ventana)
        dialog.title("Agregar Item")
        dialog.geometry("300x100")
        dialog.transient(self.app.ventana)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Texto del item:").pack(anchor="w")
        texto_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=texto_var, width=35)
        entry.pack(fill=tk.X, pady=5)
        entry.focus_set()
        
        def guardar():
            texto = texto_var.get().strip()
            if texto:
                fecha = self._fecha_actual()
                notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
                nota = next((n for n in notas if n['id'] == nota_id), None)
                if nota:
                    items = self._parsear_checklist(nota.get('contenido', ''))
                    items.append((False, texto))
                    nuevo_contenido = self._formatear_checklist(items)
                    db_local.actualizar_anotacion(nota_id, contenido=nuevo_contenido)
                    self._cargar_anotaciones()
            dialog.destroy()
        
        entry.bind("<Return>", lambda e: guardar())
        ttk.Button(frame, text="Agregar", command=guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT)
    
    def _eliminar_item_checklist(self, nota_id: int, idx: int):
        """Elimina un item del checklist."""
        if not HAS_DB:
            return
        
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
        nota = next((n for n in notas if n['id'] == nota_id), None)
        if not nota:
            return
        
        items = self._parsear_checklist(nota.get('contenido', ''))
        if 0 <= idx < len(items):
            del items[idx]
            nuevo_contenido = self._formatear_checklist(items)
            db_local.actualizar_anotacion(nota_id, contenido=nuevo_contenido)
            self._cargar_anotaciones()
    
    def _adjuntar_foto_rapido(self, nota_id: int):
        """Abre diálogo para adjuntar una foto rápidamente."""
        if not HAS_DB:
            return
        
        # Filtros para imágenes
        filetypes = [
            ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("GIF", "*.gif"),
            ("Todos los archivos", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title='📷 Seleccionar fotos para adjuntar',
            filetypes=filetypes
        )
        
        if not files:
            return
        
        attach_dir = self._ensure_attachments_dir()
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
        nota = next((n for n in notas if n['id'] == nota_id), None)
        
        if not nota:
            return
        
        attachments = nota.get('attachments') or []
        
        for f in files:
            try:
                nombre = os.path.basename(f)
                prefijo = time.strftime('%Y%m%d%H%M%S')
                dest_name = f"{prefijo}_{nombre}"
                dest_path = os.path.join(attach_dir, dest_name)
                shutil.copy2(f, dest_path)
                rel_path = os.path.relpath(dest_path, 
                    start=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                attachments.append(rel_path)
            except Exception as e:
                messagebox.showerror('Error', f'No se pudo adjuntar {f}: {e}')
        
        # Actualizar BD
        db_local.actualizar_anotacion(nota_id, attachments=attachments)
        self._cargar_anotaciones()
        messagebox.showinfo('✓ Fotos adjuntadas', f'Se adjuntaron {len(files)} foto(s)')
    
    def _crear_vista_adjuntos(self, parent, nota_id: int, attachments: list, color: str):
        """Crea una vista compacta de adjuntos con botón prominente."""
        if not attachments:
            return
        
        # Filtrar imágenes y otros
        extensiones_imagen = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        imagenes = [a for a in attachments if os.path.splitext(a)[1].lower() in extensiones_imagen]
        otros = [a for a in attachments if os.path.splitext(a)[1].lower() not in extensiones_imagen]
        
        # Frame para adjuntos - fondo destacado
        frame_adj = tk.Frame(parent, bg='#E3F2FD', bd=1, relief=tk.GROOVE)
        frame_adj.pack(fill=tk.X, side=tk.BOTTOM, padx=3, pady=3)
        
        # Fila superior: miniaturas + contador
        top_frame = tk.Frame(frame_adj, bg='#E3F2FD')
        top_frame.pack(fill=tk.X, padx=2, pady=2)
        
        # Mostrar miniaturas compactas (máximo 4)
        if imagenes and HAS_PIL:
            if not hasattr(self, '_thumb_refs'):
                self._thumb_refs = {}
            
            for i, img_path in enumerate(imagenes[:4]):
                try:
                    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    full_path = os.path.join(base, img_path)
                    
                    if os.path.exists(full_path):
                        img = Image.open(full_path)
                        img.thumbnail((35, 35))
                        photo = ImageTk.PhotoImage(img, master=self.app.ventana)
                        
                        key = f"{nota_id}_{i}"
                        self._thumb_refs[key] = photo
                        
                        lbl = tk.Label(top_frame, image=photo, bg='#E3F2FD', 
                                      cursor="hand2", bd=1, relief=tk.RAISED)
                        lbl.pack(side=tk.LEFT, padx=1)
                        lbl.bind("<Button-1>", lambda e, p=full_path: self._abrir_imagen(p))
                except Exception:
                    pass
            
            # Indicador de más
            if len(imagenes) > 4:
                tk.Label(top_frame, text=f"+{len(imagenes)-4}", 
                        bg='#E3F2FD', font=("Segoe UI", 8, "bold"), fg="#1565C0").pack(side=tk.LEFT, padx=2)
        
        # Indicador de otros archivos
        if otros:
            tk.Label(top_frame, text=f"📎{len(otros)}", 
                    bg='#E3F2FD', font=("Segoe UI", 8), fg="#666").pack(side=tk.LEFT, padx=2)
        
        # Botón grande y visible para ver/editar adjuntos
        btn_ver = tk.Button(frame_adj, 
                           text=f"👁️ VER {len(attachments)} FOTO(S)", 
                           font=("Segoe UI", 9, "bold"), 
                           bg="#2196F3", fg="white",
                           activebackground="#1976D2", activeforeground="white",
                           cursor="hand2", relief=tk.RAISED, bd=2,
                           command=lambda: self._ver_fotos_nota(nota_id, attachments))
        btn_ver.pack(fill=tk.X, padx=2, pady=(2, 3))
    
    def _ver_fotos_nota(self, nota_id: int, attachments: list):
        """Muestra un visor de fotos para los adjuntos de una nota."""
        if not HAS_PIL:
            messagebox.showerror('Error', 'Se requiere PIL/Pillow para ver imágenes')
            return
        
        if not attachments:
            messagebox.showinfo('Sin adjuntos', 'Esta nota no tiene fotos adjuntas')
            return
        
        # Filtrar solo imágenes
        extensiones_imagen = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        imagenes = [a for a in attachments if os.path.splitext(a)[1].lower() in extensiones_imagen]
        
        if not imagenes:
            messagebox.showinfo('Sin fotos', 'Esta nota no tiene fotos, solo otros archivos')
            return
        
        # Importar PIL localmente para asegurar disponibilidad
        from PIL import Image as PILImage, ImageTk as PILImageTk
        
        # Crear ventana de visor
        visor = tk.Toplevel(self.parent)
        visor.title(f"📷 Fotos de la nota ({len(imagenes)})")
        visor.transient(self.parent)
        visor.grab_set()
        visor.geometry("700x550")
        visor.configure(bg="#1a1a1a")
        
        # Variables de navegación (con master explícito)
        indice_actual = tk.IntVar(master=visor, value=0)
        
        # Guardar referencias de imágenes
        if not hasattr(self, '_visor_img_refs'):
            self._visor_img_refs = {}
        
        # Frame superior con controles
        top_frame = tk.Frame(visor, bg="#333")
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        lbl_contador = tk.Label(top_frame, text=f"1 / {len(imagenes)}", 
                               font=("Segoe UI", 12, "bold"), bg="#333", fg="white")
        lbl_contador.pack(side=tk.LEFT, padx=10)
        
        # Botón cerrar
        tk.Button(top_frame, text="✕ Cerrar", font=("Segoe UI", 10),
                 bg="#E53935", fg="white", activebackground="#C62828",
                 command=visor.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Botón abrir con app externa
        def abrir_externa():
            idx = indice_actual.get()
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            full_path = os.path.join(base, imagenes[idx])
            self._abrir_imagen(full_path)
        
        tk.Button(top_frame, text="🔗 Abrir externa", font=("Segoe UI", 10),
                 bg="#4CAF50", fg="white", activebackground="#388E3C",
                 command=abrir_externa).pack(side=tk.RIGHT, padx=5)
        
        # Frame central para la imagen
        img_frame = tk.Frame(visor, bg="#1a1a1a")
        img_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        lbl_imagen = tk.Label(img_frame, bg="#1a1a1a")
        lbl_imagen.pack(fill=tk.BOTH, expand=True)
        
        # Nombre del archivo
        lbl_nombre = tk.Label(visor, text="", font=("Segoe UI", 9), bg="#1a1a1a", fg="#aaa")
        lbl_nombre.pack(pady=(0, 5))
        
        def mostrar_imagen(idx):
            """Muestra la imagen en el índice dado."""
            if idx < 0 or idx >= len(imagenes):
                return
            
            indice_actual.set(idx)
            lbl_contador.config(text=f"{idx + 1} / {len(imagenes)}")
            
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            full_path = os.path.join(base, imagenes[idx])
            lbl_nombre.config(text=os.path.basename(imagenes[idx]))
            
            if not os.path.exists(full_path):
                lbl_imagen.config(image='', text="❌ Imagen no encontrada", fg="red",
                                 font=("Segoe UI", 14))
                return
            
            try:
                img = PILImage.open(full_path)
                
                # Calcular tamaño para ajustar al frame (mantener proporción)
                visor.update_idletasks()
                max_w = img_frame.winfo_width() - 20 or 650
                max_h = img_frame.winfo_height() - 20 or 400
                
                # Redimensionar manteniendo proporción
                img_w, img_h = img.size
                ratio = min(max_w / img_w, max_h / img_h, 1.0)  # No ampliar más de original
                new_w = int(img_w * ratio)
                new_h = int(img_h * ratio)
                
                if ratio < 1.0:
                    img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
                
                photo = PILImageTk.PhotoImage(img, master=visor)
                self._visor_img_refs[nota_id] = photo  # Guardar referencia
                
                lbl_imagen.config(image=photo, text='')
            except Exception as e:
                lbl_imagen.config(image='', text=f"❌ Error: {e}", fg="red",
                                 font=("Segoe UI", 12))
        
        # Frame inferior con navegación
        nav_frame = tk.Frame(visor, bg="#333")
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        def anterior():
            idx = indice_actual.get()
            if idx > 0:
                mostrar_imagen(idx - 1)
        
        def siguiente():
            idx = indice_actual.get()
            if idx < len(imagenes) - 1:
                mostrar_imagen(idx + 1)
        
        btn_ant = tk.Button(nav_frame, text="◀ Anterior", font=("Segoe UI", 11, "bold"),
                           bg="#2196F3", fg="white", activebackground="#1976D2",
                           width=12, command=anterior)
        btn_ant.pack(side=tk.LEFT, padx=20, pady=5)
        
        # Miniaturas en el centro
        thumb_frame = tk.Frame(nav_frame, bg="#333")
        thumb_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
        
        for i, img_path in enumerate(imagenes[:8]):  # Máximo 8 miniaturas
            try:
                base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                full_path = os.path.join(base, img_path)
                if os.path.exists(full_path):
                    img = PILImage.open(full_path)
                    img.thumbnail((40, 40))
                    photo = PILImageTk.PhotoImage(img, master=visor)
                    
                    key = f"visor_thumb_{nota_id}_{i}"
                    self._visor_img_refs[key] = photo
                    
                    btn_thumb = tk.Button(thumb_frame, image=photo, bg="#333", bd=2,
                                         command=lambda idx=i: mostrar_imagen(idx))
                    btn_thumb.pack(side=tk.LEFT, padx=2)
            except Exception:
                pass
        
        btn_sig = tk.Button(nav_frame, text="Siguiente ▶", font=("Segoe UI", 11, "bold"),
                           bg="#2196F3", fg="white", activebackground="#1976D2",
                           width=12, command=siguiente)
        btn_sig.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # Atajos de teclado
        visor.bind("<Left>", lambda e: anterior())
        visor.bind("<Right>", lambda e: siguiente())
        visor.bind("<Escape>", lambda e: visor.destroy())
        
        # Mostrar primera imagen
        visor.after(100, lambda: mostrar_imagen(0))
        
        # Centrar ventana
        visor.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (visor.winfo_width() // 2)
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (visor.winfo_height() // 2)
        visor.geometry(f"+{x}+{y}")
    
    def _abrir_imagen(self, path: str):
        """Abre una imagen con el visor del sistema."""
        try:
            if os.name == 'nt':
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path])
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo abrir: {e}')
    
    def _oscurecer_color(self, hex_color: str) -> str:
        """Oscurece un color hex."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        factor = 0.85
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _hacer_arrastrable(self, window_id, widget, nota_id):
        """Permite arrastrar la nota arrastrando desde la barra de título."""
        
        def on_press(event):
            # Guardar posición inicial del mouse en coordenadas de pantalla
            self._drag_data[window_id] = {
                'start_x': event.x_root,
                'start_y': event.y_root,
                'dragging': True
            }
            # Cambiar cursor para indicar arrastre
            widget.config(cursor="fleur")
            print(f"[DEBUG] Iniciando drag nota {nota_id} en ({event.x_root}, {event.y_root})")
        
        def on_drag(event):
            if window_id not in self._drag_data:
                return
            if not self._drag_data[window_id].get('dragging'):
                return
            
            # Calcular desplazamiento desde posición inicial
            dx = event.x_root - self._drag_data[window_id]['start_x']
            dy = event.y_root - self._drag_data[window_id]['start_y']
            
            if dx == 0 and dy == 0:
                return
            
            try:
                # Obtener posición actual en el canvas
                coords = self.canvas_notas.coords(window_id)
                if coords:
                    # Mover a nueva posición
                    new_x = max(0, coords[0] + dx)
                    new_y = max(0, coords[1] + dy)
                    self.canvas_notas.coords(window_id, new_x, new_y)
                    
                    # Actualizar posición de referencia
                    self._drag_data[window_id]['start_x'] = event.x_root
                    self._drag_data[window_id]['start_y'] = event.y_root
            except Exception as e:
                print(f"[ERROR] Error durante drag: {e}")
        
        def on_release(event):
            if window_id not in self._drag_data:
                return
            
            # Restaurar cursor
            widget.config(cursor="")
            
            # Guardar posición final en BD
            try:
                coords = self.canvas_notas.coords(window_id)
                if coords and HAS_DB:
                    pos_x = max(0, int(coords[0]))
                    pos_y = max(0, int(coords[1]))
                    print(f"[DEBUG] Guardando posicion nota {nota_id}: ({pos_x}, {pos_y})")
                    db_local.actualizar_anotacion(nota_id, pos_x=pos_x, pos_y=pos_y)
                    self._actualizar_scrollregion()
            except Exception as e:
                print(f"[ERROR] Error guardando posicion: {e}")
            
            # Limpiar datos de arrastre
            if window_id in self._drag_data:
                del self._drag_data[window_id]
        
        # Vincular eventos al widget
        widget.bind("<ButtonPress-1>", on_press, add="+")
        widget.bind("<B1-Motion>", on_drag, add="+")
        widget.bind("<ButtonRelease-1>", on_release, add="+")
    
    def _hacer_redimensionable(self, window_id, grip, nota_id, ancho_inicial, alto_inicial):
        """Permite redimensionar la nota arrastrando desde el grip."""
        
        # Datos de redimensionamiento
        resize_data = {'ancho': ancho_inicial, 'alto': alto_inicial}
        
        def on_resize_start(event):
            """Inicia el redimensionamiento."""
            resize_data['start_x'] = event.x_root
            resize_data['start_y'] = event.y_root
            resize_data['resizing'] = True
            # Obtener tamaño actual del item del canvas
            if window_id in self.notas_widgets:
                resize_data['ancho'] = self.notas_widgets[window_id].get('ancho', ancho_inicial)
                resize_data['alto'] = self.notas_widgets[window_id].get('alto', alto_inicial)
            print(f"[DEBUG] Iniciando resize nota {nota_id}, tamaño actual: {resize_data['ancho']}x{resize_data['alto']}")
        
        def on_resize_drag(event):
            """Redimensiona durante el arrastre."""
            if not resize_data.get('resizing'):
                return
            
            # Calcular diferencia
            dx = event.x_root - resize_data['start_x']
            dy = event.y_root - resize_data['start_y']
            
            # Nuevo tamaño con límites mínimos
            nuevo_ancho = max(120, resize_data['ancho'] + dx)
            nuevo_alto = max(80, resize_data['alto'] + dy)
            
            # Actualizar el canvas window
            try:
                self.canvas_notas.itemconfig(window_id, width=nuevo_ancho, height=nuevo_alto)
            except Exception as e:
                print(f"[ERROR] Error durante resize: {e}")
        
        def on_resize_end(event):
            """Finaliza el redimensionamiento y guarda en BD."""
            if not resize_data.get('resizing'):
                return
            
            resize_data['resizing'] = False
            
            # Calcular tamaño final
            dx = event.x_root - resize_data['start_x']
            dy = event.y_root - resize_data['start_y']
            nuevo_ancho = max(120, resize_data['ancho'] + dx)
            nuevo_alto = max(80, resize_data['alto'] + dy)
            
            # Guardar en BD
            try:
                if HAS_DB:
                    db_local.actualizar_anotacion(nota_id, ancho=nuevo_ancho, alto=nuevo_alto)
                    print(f"[DEBUG] Guardado tamaño nota {nota_id}: {nuevo_ancho}x{nuevo_alto}")
                
                # Actualizar widget data
                if window_id in self.notas_widgets:
                    self.notas_widgets[window_id]['ancho'] = nuevo_ancho
                    self.notas_widgets[window_id]['alto'] = nuevo_alto
                
                self._actualizar_scrollregion()
            except Exception as e:
                print(f"[ERROR] Error guardando tamaño: {e}")
        
        # Vincular eventos al grip
        grip.bind("<ButtonPress-1>", on_resize_start)
        grip.bind("<B1-Motion>", on_resize_drag)
        grip.bind("<ButtonRelease-1>", on_resize_end)
    
    def _nueva_anotacion(self):
        """Crea una nueva anotación de texto preguntando primero la prioridad."""
        if not HAS_DB:
            messagebox.showerror("Error", "Base de datos no disponible")
            return
        
        # Mostrar diálogo de selección de prioridad
        self._mostrar_selector_prioridad(es_checklist=False)
    
    def _mostrar_selector_prioridad(self, es_checklist: bool = False):
        """Muestra un diálogo para seleccionar la prioridad de la nueva nota."""
        # Colores y posiciones según prioridad
        # Urgente: Rojo, primera posición (arriba-izquierda)
        # Alta: Naranja, segunda posición
        # Normal: Amarillo, siguiente posición disponible
        # Baja: Verde, al final
        prioridades_config = {
            'urgente': {'color': '#EF9A9A', 'icon': '🔥', 'orden': 0},
            'alta':    {'color': '#FFAB91', 'icon': '⬆️', 'orden': 1},
            'normal':  {'color': '#FFEB3B', 'icon': '➖', 'orden': 2},
            'baja':    {'color': '#A5D6A7', 'icon': '⬇️', 'orden': 3}
        }
        
        # Guardar config como atributo de instancia para usar después
        self._prioridades_config = prioridades_config
        
        # Crear ventana de selección
        dialog = tk.Toplevel(self.parent)
        dialog.title("📌 Prioridad de la nota")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Tamaño de ventana más amplio
        dialog.geometry("320x280")
        dialog.resizable(False, False)
        
        # Frame principal
        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="¿Qué prioridad tiene esta nota?", 
                  font=("Segoe UI", 11, "bold")).pack(pady=(0, 15))
        
        prioridad_var = tk.StringVar(master=dialog, value='normal')
        
        # Radiobuttons de prioridad
        radio_frame = ttk.Frame(frame)
        radio_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        for prioridad, config in prioridades_config.items():
            rb_frame = tk.Frame(radio_frame, bg=config['color'], padx=5, pady=3)
            rb_frame.pack(fill=tk.X, pady=2)
            
            rb = tk.Radiobutton(rb_frame, 
                               text=f"{config['icon']} {prioridad.capitalize()}",
                               variable=prioridad_var,
                               value=prioridad,
                               font=("Segoe UI", 10),
                               bg=config['color'],
                               activebackground=self._oscurecer_color(config['color']),
                               selectcolor=self._oscurecer_color(config['color']),
                               anchor="w",
                               indicatoron=True)
            rb.pack(fill=tk.X)
        
        # Frame para botones
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Botón Cancelar
        def cancelar():
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Cancelar", command=cancelar).pack(side=tk.LEFT, padx=5)
        
        # Botón Crear nota (más prominente)
        def crear_nota():
            prioridad = prioridad_var.get()
            dialog.destroy()
            self._crear_nota_con_prioridad(prioridad, es_checklist)
        
        btn_crear = tk.Button(btn_frame, text="➕ Agregar Nota", command=crear_nota,
                             font=("Segoe UI", 10, "bold"), bg="#4CAF50", fg="white",
                             activebackground="#388E3C", activeforeground="white",
                             padx=15, pady=5)
        btn_crear.pack(side=tk.RIGHT, padx=5)
        
        # Centrar ventana respecto a la principal
        dialog.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _crear_nota_con_prioridad(self, prioridad: str, es_checklist: bool):
        """Crea la nota con la prioridad seleccionada."""
        try:
            # Usar config guardada o crear una por defecto
            prioridades_config = getattr(self, '_prioridades_config', {
                'urgente': {'color': '#EF9A9A', 'icon': '🔥', 'orden': 0},
                'alta':    {'color': '#FFAB91', 'icon': '⬆️', 'orden': 1},
                'normal':  {'color': '#FFEB3B', 'icon': '➖', 'orden': 2},
                'baja':    {'color': '#A5D6A7', 'icon': '⬇️', 'orden': 3}
            })
            
            config = prioridades_config.get(prioridad, prioridades_config['normal'])
            color = config['color']
            orden = config['orden']
            
            # Calcular posición - usar siguiente posición disponible (sin separar por prioridad)
            x, y = self._calcular_siguiente_posicion()
            
            print(f"[DEBUG] Posición calculada: x={x}, y={y}")
            
            # Usar la fecha del DataStore para consistencia
            fecha = self._fecha_actual()
            
            titulo = "Nueva lista" if es_checklist else "Nueva nota"
            contenido = "[ ] Primer item" if es_checklist else ""

            print(f"[DEBUG] Creando nota - Prioridad: {prioridad}, Color: {color}, Fecha: {fecha}")
            
            nota_id = db_local.agregar_anotacion(
                fecha=fecha,
                titulo=titulo, 
                contenido=contenido, 
                color=color,
                pos_x=x,
                pos_y=y,
                es_checklist=es_checklist,
                prioridad=prioridad
            )
            
            print(f"[DEBUG] Nota creada con ID: {nota_id}")
            
            if nota_id and nota_id > 0:
                # Recargar anotaciones inmediatamente
                self.parent.after(100, self._cargar_anotaciones)
            else:
                messagebox.showerror('Error', 'No se pudo crear la nota (ID inválido)')
                print(f"[ERROR] agregar_anotacion retornó ID inválido: {nota_id}")
        except Exception as e:
            messagebox.showerror('Error', f'Error creando nota: {e}')
            print(f"[ERROR] Excepción en _crear_nota_con_prioridad: {e}")
            import traceback
            traceback.print_exc()
    
    def _calcular_posicion_por_prioridad(self, orden_prioridad: int) -> tuple:
        """
        Calcula la posición según la prioridad.
        Prioridad urgente/alta: primeras filas
        Prioridad normal: filas intermedias
        Prioridad baja: últimas filas
        """
        if not HAS_DB:
            return (self.MARGEN_X, self.MARGEN_Y)
        
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=False, fecha=fecha)
        
        # Fila base según prioridad (0=urgente, 1=alta, 2=normal, 3=baja)
        fila_base = orden_prioridad * 2  # Espaciado de 2 filas entre prioridades
        
        # Buscar posiciones ocupadas en esas filas
        posiciones_ocupadas = set()
        for nota in notas:
            x = nota.get('pos_x', 0)
            y = nota.get('pos_y', 0)
            col = round((x - self.MARGEN_X) / (self.NOTA_ANCHO + self.MARGEN_X))
            fila = round((y - self.MARGEN_Y) / (self.NOTA_ALTO + self.MARGEN_Y))
            posiciones_ocupadas.add((col, fila))
        
        # Buscar primera columna libre en la fila base o siguiente
        for fila_offset in range(10):  # Buscar en las siguientes 10 filas
            fila = fila_base + fila_offset
            for col in range(self.COLUMNAS_MAX):
                if (col, fila) not in posiciones_ocupadas:
                    x = self.MARGEN_X + col * (self.NOTA_ANCHO + self.MARGEN_X)
                    y = self.MARGEN_Y + fila * (self.NOTA_ALTO + self.MARGEN_Y)
                    return (x, y)
        
        # Fallback
        return self._calcular_siguiente_posicion()
    
    def _nueva_lista(self):
        """Crea una nueva lista preguntando primero la prioridad."""
        if not HAS_DB:
            messagebox.showerror("Error", "Base de datos no disponible")
            return
        
        # Mostrar diálogo de selección de prioridad
        self._mostrar_selector_prioridad(es_checklist=True)
    
    def _editar_anotacion(self, nota_id: int):
        """Abre diálogo para editar una anotación."""
        if not HAS_DB:
            return
        
        # Obtener datos actuales
        fecha = self._fecha_actual()
        notas = db_local.obtener_anotaciones(incluir_archivadas=True, fecha=fecha, incluir_eliminadas=True)
        nota = next((n for n in notas if n['id'] == nota_id), None)
        if not nota:
            return
        
        dialog = tk.Toplevel(self.app.ventana)
        dialog.title("✏️ Editar Nota")
        dialog.geometry("450x450")
        dialog.transient(self.app.ventana)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(frame, text="Título:").pack(anchor="w")
        titulo_var = tk.StringVar(value=nota.get('titulo', ''))
        ttk.Entry(frame, textvariable=titulo_var, width=45).pack(fill=tk.X, pady=(0, 10))
        
        # Tipo (texto o checklist)
        ttk.Label(frame, text="Tipo:").pack(anchor="w")
        tipo_var = tk.StringVar(value="checklist" if nota.get('es_checklist', 0) else "texto")
        frame_tipo = ttk.Frame(frame)
        frame_tipo.pack(anchor="w", pady=(0, 10))
        ttk.Radiobutton(frame_tipo, text="📝 Texto", variable=tipo_var, value="texto").pack(side=tk.LEFT)
        ttk.Radiobutton(frame_tipo, text="☑️ Lista", variable=tipo_var, value="checklist").pack(side=tk.LEFT, padx=10)
        
        # Prioridad
        ttk.Label(frame, text="Prioridad:").pack(anchor="w")
        prioridad_var = tk.StringVar(value=nota.get('prioridad', 'normal'))
        ttk.Combobox(frame, textvariable=prioridad_var, 
                     values=["baja", "normal", "alta", "urgente"],
                     state="readonly", width=15).pack(anchor="w", pady=(0, 10))
        
        # Color
        ttk.Label(frame, text="Color:").pack(anchor="w")
        color_var = tk.StringVar(value=nota.get('color', '#FFEB3B'))
        frame_colores = ttk.Frame(frame)
        frame_colores.pack(anchor="w", pady=(0, 10))
        colores = ["#FFEB3B", "#81D4FA", "#A5D6A7", "#FFAB91", "#CE93D8", "#EF9A9A"]
        for c in colores:
            btn = tk.Button(frame_colores, bg=c, width=3, height=1,
                           command=lambda col=c: color_var.set(col))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Contenido
        ttk.Label(frame, text="Contenido:").pack(anchor="w")
        txt_contenido = tk.Text(frame, height=10, width=50)
        txt_contenido.insert("1.0", nota.get('contenido', ''))
        txt_contenido.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        # Permitir pegar imágenes desde portapapeles en el editor
        txt_contenido.bind('<Control-v>', lambda e, nid=nota_id, t=txt_contenido: self._handle_paste(e, nid, t))
        txt_contenido.bind('<Control-V>', lambda e, nid=nota_id, t=txt_contenido: self._handle_paste(e, nid, t))
        
        # Info para checklist
        lbl_info = ttk.Label(frame, text="Para listas: usa [ ] para items pendientes y [x] para completados",
                            font=("Segoe UI", 8), foreground="#666666")
        lbl_info.pack(anchor="w")

        # Attachments con vista previa de imágenes
        ttk.Label(frame, text="Adjuntos:").pack(anchor="w", pady=(10, 0))
        attach_frame = ttk.Frame(frame)
        attach_frame.pack(fill=tk.X, pady=(0, 10))

        attachments_listbox = tk.Listbox(attach_frame, height=4)
        attachments_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        attach_btns = ttk.Frame(attach_frame)
        attach_btns.pack(side=tk.RIGHT, padx=5)

        def ensure_attachments_dir():
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            attach_dir = os.path.join(base, 'attachments')
            os.makedirs(attach_dir, exist_ok=True)
            return attach_dir

        # Cargar attachments existentes
        nota_attachments = nota.get('attachments') or []
        for a in nota_attachments:
            attachments_listbox.insert(tk.END, a)

        def agregar_adjuntos():
            files = filedialog.askopenfilenames(title='Seleccionar archivos')
            if not files:
                return
            attach_dir = ensure_attachments_dir()
            for f in files:
                try:
                    nombre = os.path.basename(f)
                    # prefijo para evitar colisiones
                    prefijo = time.strftime('%Y%m%d%H%M%S%f')[-6:]
                    dest_name = f"{prefijo}_{nombre}"
                    dest_path = os.path.join(attach_dir, dest_name)
                    shutil.copy2(f, dest_path)
                    rel_path = os.path.relpath(dest_path, start=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                    attachments_listbox.insert(tk.END, rel_path)
                except Exception as e:
                    messagebox.showerror('Error', f'No se pudo adjuntar {f}: {e}')

        def abrir_attachment():
            sel = attachments_listbox.curselection()
            if not sel:
                return
            item = attachments_listbox.get(sel[0])
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            path = os.path.join(base, item)
            if os.path.exists(path):
                try:
                    if os.name == 'nt':
                        os.startfile(path)
                    else:
                        import subprocess
                        subprocess.Popen(['xdg-open', path])
                except Exception as e:
                    messagebox.showerror('Error', f'No se pudo abrir: {e}')
            else:
                messagebox.showwarning('No encontrado', 'El archivo no existe en disco')

        def eliminar_attachment():
            sel = attachments_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            item = attachments_listbox.get(idx)
            if messagebox.askyesno('Eliminar', f'¿Eliminar {os.path.basename(item)}?'):
                # Intentar borrar archivo físico
                base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                path = os.path.join(base, item)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
                attachments_listbox.delete(idx)

        def agregar_fotos():
            """Adjuntar solo imágenes con filtros específicos."""
            filetypes = [
                ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("GIF", "*.gif"),
                ("Todos los archivos", "*.*")
            ]
            files = filedialog.askopenfilenames(title='📷 Seleccionar fotos', filetypes=filetypes)
            if not files:
                return
            attach_dir = ensure_attachments_dir()
            for f in files:
                try:
                    nombre = os.path.basename(f)
                    prefijo = time.strftime('%Y%m%d%H%M%S%f')[-6:]
                    dest_name = f"{prefijo}_{nombre}"
                    dest_path = os.path.join(attach_dir, dest_name)
                    shutil.copy2(f, dest_path)
                    rel_path = os.path.relpath(dest_path, start=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                    attachments_listbox.insert(tk.END, rel_path)
                except Exception as e:
                    messagebox.showerror('Error', f'No se pudo adjuntar {f}: {e}')

        ttk.Button(attach_btns, text='📷 Fotos', command=agregar_fotos).pack(fill=tk.X, pady=2)
        ttk.Button(attach_btns, text='📎 Archivos', command=agregar_adjuntos).pack(fill=tk.X, pady=2)
        ttk.Button(attach_btns, text='👁️ Abrir', command=abrir_attachment).pack(fill=tk.X, pady=2)
        ttk.Button(attach_btns, text='🗑️ Eliminar', command=eliminar_attachment).pack(fill=tk.X, pady=2)
        
        def guardar():
            es_checklist = tipo_var.get() == "checklist"
            contenido = txt_contenido.get("1.0", tk.END).strip()
            
            # Si cambió a checklist, formatear el contenido
            if es_checklist and not nota.get('es_checklist', 0):
                lineas = contenido.split('\n')
                contenido_formateado = []
                for linea in lineas:
                    linea = linea.strip()
                    if linea and not linea.startswith('['):
                        contenido_formateado.append(f"[ ] {linea}")
                    elif linea:
                        contenido_formateado.append(linea)
                contenido = '\n'.join(contenido_formateado)
            
            # Obtener lista de attachments desde el listbox
            attachments = list(attachments_listbox.get(0, tk.END))
            db_local.actualizar_anotacion(
                nota_id,
                titulo=titulo_var.get(),
                contenido=contenido,
                color=color_var.get(),
                prioridad=prioridad_var.get(),
                es_checklist=es_checklist,
                attachments=attachments
            )
            dialog.destroy()
            self._cargar_anotaciones()
        
        frame_btns = ttk.Frame(frame)
        frame_btns.pack(pady=10)
        ttk.Button(frame_btns, text="💾 Guardar", command=guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_btns, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT)
    
    def _guardar_contenido_nota(self, nota_id: int, contenido: str):
        """Guarda el contenido de una nota con verificación."""
        if HAS_DB:
            try:
                print(f"[DEBUG] Guardando contenido para nota ID {nota_id}")
                resultado = db_local.actualizar_anotacion(nota_id, contenido=contenido)
                print(f"[DEBUG] Resultado de guardado: {resultado}")
                
                # Verificar que se guardó correctamente
                conn = db_local.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT contenido FROM anotaciones WHERE id = ?', (nota_id,))
                fila = cursor.fetchone()
                conn.close()
                
                if fila and fila['contenido'] == contenido:
                    print(f"[DEBUG] Contenido verificado en BD para nota {nota_id}")
                else:
                    print(f"[ERROR] El contenido no coincide después de guardar")
                    
            except Exception as e:
                print(f"[ERROR] Error guardando contenido: {e}")
                import traceback
                traceback.print_exc()
    
    def _archivar_nota(self, nota_id: int):
        """Archiva una nota."""
        if HAS_DB:
            db_local.archivar_anotacion(nota_id, True)
            self._cargar_anotaciones()
    
    def _desarchivar_nota(self, nota_id: int):
        """Restaura una nota archivada."""
        if HAS_DB:
            db_local.archivar_anotacion(nota_id, False)
            self._cargar_anotaciones()
    
    def _eliminar_anotacion(self, nota_id: int):
        """Marca una anotación como eliminada (borrado lógico)."""
        if messagebox.askyesno("Confirmar", "¿Eliminar esta nota?"):
            if HAS_DB:
                print(f"[DEBUG] Marcando nota {nota_id} como eliminada")
                db_local.actualizar_anotacion(nota_id, eliminada=1)
                self._cargar_anotaciones()
    
    def _restaurar_nota(self, nota_id):
        """Restaura una nota eliminada."""
        if messagebox.askyesno("Confirmar", "¿Restaurar esta nota?"):
            if HAS_DB:
                print(f"[DEBUG] Restaurando nota {nota_id}")
                db_local.actualizar_anotacion(nota_id, eliminada=0)
                self._cargar_anotaciones()
    
    def refrescar(self):
        """Refresca los datos de la pestaña. Sincroniza con fecha del DataStore."""
        # Sincronizar fecha_var con DataStore
        if hasattr(self, 'fecha_var') and self.fecha_var:
            fecha_ds = self._fecha_actual()
            if self.fecha_var.get() != fecha_ds:
                self.fecha_var.set(fecha_ds)
        self._cargar_anotaciones()
