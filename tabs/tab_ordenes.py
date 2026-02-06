#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TabOrdenes - Pestaña de Órdenes de Venta con integración Telegram
Permite recibir órdenes de vendedores vía bot de Telegram y consultarlas
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
import threading
import asyncio
import os
import re

# Intentar importar telegram
try:
    from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler, InlineQueryHandler
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    # Stubs para type hints cuando telegram no está instalado
    Update = None
    ContextTypes = None
    print("⚠️ python-telegram-bot no instalado")

try:
    import database_local as db_local
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TabOrdenes:
    """
    Pestaña de órdenes de venta con integración de bot de Telegram.
    Permite recibir pedidos de vendedores y consultar inventario/clientes.
    """
    
    def __init__(self, parent: ttk.Frame, app, datastore):
        """
        Inicializa la pestaña de órdenes.
        
        Args:
            parent: Frame padre donde se creará la pestaña
            app: Referencia a la aplicación principal
            datastore: Referencia al DataStore compartido
        """
        self.parent = parent
        self.app = app
        self.ds = datastore
        
        # Estado del bot
        self.bot_running = False
        self.bot_thread = None
        self.bot_app = None
        self.loop = None
        
        # Sesiones de usuarios (para guardar cliente seleccionado)
        # {user_id: {'cliente': 'nombre', 'productos': [], 'timestamp': datetime}}
        self.user_sessions = {}
        
        # ════════════════════════════════════════════════════════════════
        # CACHÉ DE PRODUCTOS Y CLIENTES DE LA BD
        # ════════════════════════════════════════════════════════════════
        self.productos_cache = []  # Lista de (codigo, descripcion, stock, precio)
        self.clientes_cache = []   # Lista de nombres de clientes
        self.productos_por_dimension = {}  # {'8x12': [(cod, desc, stock, precio), ...]}
        self.productos_por_color = {}      # {'negra': [(cod, desc, stock, precio), ...]}
        self.productos_por_tipo_t = {}     # {'T15': [(cod, desc, stock, precio), ...]}
        
        # Variables de configuración
        self.token_var = None
        self.status_var = None
        
        # Suscribirse a cambios del DataStore
        try:
            if hasattr(self.ds, 'suscribir'):
                self.ds.suscribir(self.refrescar)
        except Exception:
            pass
        
        self._crear_interfaz()
        self._cargar_config()
        self._cargar_ordenes()
        
        # Cargar caché de productos en segundo plano
        self._cargar_cache_bd()
    
    def _fecha_actual(self) -> str:
        """Retorna la fecha actual del DataStore."""
        try:
            if hasattr(self.ds, 'fecha') and self.ds.fecha:
                return self.ds.fecha
        except:
            pass
        return datetime.now().strftime('%Y-%m-%d')
    
    def _crear_interfaz(self):
        """Crea la interfaz de la pestaña."""
        tab = self.parent
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # ══════════════════════════════════════════════════════════════
        # BARRA SUPERIOR: Configuración del Bot
        # ══════════════════════════════════════════════════════════════
        config_frame = ttk.LabelFrame(tab, text="🤖 Configuración del Bot de Telegram", padding=10)
        config_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        config_frame.columnconfigure(1, weight=1)
        
        # Token del bot
        ttk.Label(config_frame, text="Token:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.token_var = tk.StringVar(master=self.app.ventana)
        self.token_entry = ttk.Entry(config_frame, textvariable=self.token_var, width=50, show="•")
        self.token_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Botón mostrar/ocultar token
        self.show_token = False
        self.btn_show_token = ttk.Button(config_frame, text="👁️", width=3, 
                                          command=self._toggle_show_token)
        self.btn_show_token.grid(row=0, column=2, padx=2)
        
        # Botón guardar token
        ttk.Button(config_frame, text="💾 Guardar", 
                   command=self._guardar_token).grid(row=0, column=3, padx=5)
        
        # Fila 2: Controles del bot
        control_frame = ttk.Frame(config_frame)
        control_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        
        self.btn_iniciar = ttk.Button(control_frame, text="▶️ Iniciar Bot", 
                                       command=self._iniciar_bot, style="Success.TButton")
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)
        
        self.btn_detener = ttk.Button(control_frame, text="⏹️ Detener Bot", 
                                       command=self._detener_bot, state=tk.DISABLED)
        self.btn_detener.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)
        
        # Estado del bot
        ttk.Label(control_frame, text="Estado:").pack(side=tk.LEFT, padx=5)
        self.status_var = tk.StringVar(master=self.app.ventana, value="⚫ Detenido")
        self.lbl_status = ttk.Label(control_frame, textvariable=self.status_var, 
                                     font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=5)
        
        # Botón refrescar órdenes
        ttk.Button(control_frame, text="🔄 Refrescar", 
                   command=self._cargar_ordenes).pack(side=tk.RIGHT, padx=5)
        
        # ══════════════════════════════════════════════════════════════
        # PANEL PRINCIPAL: Lista de órdenes
        # ══════════════════════════════════════════════════════════════
        main_frame = ttk.Frame(tab)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Panel izquierdo: Lista de órdenes
        ordenes_frame = ttk.LabelFrame(main_frame, text="📋 Órdenes Recibidas", padding=5)
        ordenes_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ordenes_frame.columnconfigure(0, weight=1)
        ordenes_frame.rowconfigure(0, weight=1)
        
        # Treeview para órdenes
        columns = ("id", "hora", "vendedor", "cliente", "productos", "estado")
        self.tree_ordenes = ttk.Treeview(ordenes_frame, columns=columns, show="headings", height=15)
        
        self.tree_ordenes.heading("id", text="ID")
        self.tree_ordenes.heading("hora", text="Hora")
        self.tree_ordenes.heading("vendedor", text="Vendedor")
        self.tree_ordenes.heading("cliente", text="Cliente")
        self.tree_ordenes.heading("productos", text="Productos")
        self.tree_ordenes.heading("estado", text="Estado")
        
        self.tree_ordenes.column("id", width=40, anchor="center")
        self.tree_ordenes.column("hora", width=70, anchor="center")
        self.tree_ordenes.column("vendedor", width=100)
        self.tree_ordenes.column("cliente", width=120)
        self.tree_ordenes.column("productos", width=200)
        self.tree_ordenes.column("estado", width=80, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(ordenes_frame, orient=tk.VERTICAL, command=self.tree_ordenes.yview)
        self.tree_ordenes.configure(yscrollcommand=scrollbar.set)
        
        self.tree_ordenes.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Tags para estados
        self.tree_ordenes.tag_configure("pendiente", background="#fff3e0", foreground="#e65100")
        self.tree_ordenes.tag_configure("verificada", background="#e8f5e9", foreground="#2e7d32")
        self.tree_ordenes.tag_configure("procesada", background="#e3f2fd", foreground="#1565c0")
        
        # Botones de acción para órdenes
        btn_ordenes_frame = ttk.Frame(ordenes_frame)
        btn_ordenes_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        ttk.Button(btn_ordenes_frame, text="✅ Verificar", 
                   command=self._verificar_orden).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_ordenes_frame, text="📦 Procesar", 
                   command=self._procesar_orden).pack(side=tk.LEFT, padx=2)
        
        # Separador visual
        ttk.Separator(btn_ordenes_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        
        # Botón para crear venta en Firebird
        self.btn_crear_venta = ttk.Button(btn_ordenes_frame, text="🛒 Crear Venta en Eleventa", 
                                           command=self._crear_venta_firebird, style="Accent.TButton")
        self.btn_crear_venta.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(btn_ordenes_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        
        ttk.Button(btn_ordenes_frame, text="🗑️ Eliminar", 
                   command=self._eliminar_orden).pack(side=tk.LEFT, padx=2)
        
        # Panel derecho: Detalle de orden seleccionada
        detalle_frame = ttk.LabelFrame(main_frame, text="📝 Detalle de Orden", padding=10)
        detalle_frame.grid(row=0, column=1, sticky="nsew")
        detalle_frame.columnconfigure(0, weight=1)
        
        # Mensaje original
        ttk.Label(detalle_frame, text="Mensaje original:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.txt_mensaje = tk.Text(detalle_frame, height=8, wrap=tk.WORD, 
                                    font=("Segoe UI", 9), state=tk.DISABLED)
        self.txt_mensaje.pack(fill=tk.BOTH, expand=True, pady=(2, 10))
        
        # Info del vendedor
        info_frame = ttk.Frame(detalle_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="Vendedor:").grid(row=0, column=0, sticky="w")
        self.lbl_vendedor = ttk.Label(info_frame, text="-", font=("Segoe UI", 9, "bold"))
        self.lbl_vendedor.grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        ttk.Label(info_frame, text="Usuario TG:").grid(row=1, column=0, sticky="w")
        self.lbl_username = ttk.Label(info_frame, text="-")
        self.lbl_username.grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        ttk.Label(info_frame, text="Fecha:").grid(row=2, column=0, sticky="w")
        self.lbl_fecha_orden = ttk.Label(info_frame, text="-")
        self.lbl_fecha_orden.grid(row=2, column=1, sticky="w", padx=(10, 0))
        
        # Bind selección
        self.tree_ordenes.bind("<<TreeviewSelect>>", self._on_orden_select)
        
        # ══════════════════════════════════════════════════════════════
        # PANEL INFERIOR: Comandos disponibles
        # ══════════════════════════════════════════════════════════════
        ayuda_frame = ttk.LabelFrame(tab, text="📖 Comandos del Bot", padding=10)
        ayuda_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        comandos = [
            ("/pedido o /p [cliente] - [productos]", "Crea una orden: /p Juan - 10 bolsas, 5 rollos"),
            ("/buscar o /b [texto]", "Busca clientes Y productos: /b bolsa"),
            ("/stock o /s [producto]", "Consulta inventario: /s rollo"),
            ("/cliente o /c [nombre]", "Busca un cliente: /c juan"),
            ("/productos", "Lista productos con stock disponible"),
        ]
        
        for i, (cmd, desc) in enumerate(comandos):
            ttk.Label(ayuda_frame, text=cmd, font=("Consolas", 9, "bold"), 
                      foreground="#2196f3").grid(row=i, column=0, sticky="w", padx=(0, 20))
            ttk.Label(ayuda_frame, text=desc).grid(row=i, column=1, sticky="w")
    
    def _toggle_show_token(self):
        """Muestra/oculta el token."""
        self.show_token = not self.show_token
        self.token_entry.config(show="" if self.show_token else "•")
        self.btn_show_token.config(text="🙈" if self.show_token else "👁️")
    
    def _cargar_config(self):
        """Carga la configuración guardada."""
        # Token por defecto
        DEFAULT_TOKEN = "8589747046:AAFT4vFU2ZYmB4_xJmF9shK1I2JRExjWPb0"
        
        if HAS_DB:
            token = db_local.obtener_config('telegram_bot_token', '')
            if not token:
                token = DEFAULT_TOKEN
                # Guardar el token por defecto
                db_local.guardar_config('telegram_bot_token', token)
            self.token_var.set(token)
        else:
            self.token_var.set(DEFAULT_TOKEN)
    
    def _guardar_token(self):
        """Guarda el token del bot."""
        if HAS_DB:
            token = self.token_var.get().strip()
            db_local.guardar_config('telegram_bot_token', token)
            messagebox.showinfo("Guardado", "Token guardado correctamente")
    
    def _cargar_ordenes(self):
        """Carga las órdenes de la fecha actual."""
        if not HAS_DB:
            return
        
        # Limpiar treeview
        for item in self.tree_ordenes.get_children():
            self.tree_ordenes.delete(item)
        
        fecha = self._fecha_actual()
        ordenes = db_local.obtener_ordenes_telegram(fecha=fecha)
        
        for orden in ordenes:
            hora = orden.get('fecha_creacion', '')
            if hora and len(hora) > 10:
                hora = hora[11:16]  # Extraer HH:MM
            
            estado = orden.get('estado', 'pendiente')
            tag = estado
            
            self.tree_ordenes.insert("", "end", values=(
                orden['id'],
                hora,
                orden.get('telegram_nombre', 'Desconocido'),
                orden.get('cliente', '-'),
                orden.get('productos', '-')[:50],
                estado.capitalize()
            ), tags=(tag,))
    
    def _on_orden_select(self, event):
        """Muestra el detalle de la orden seleccionada."""
        selection = self.tree_ordenes.selection()
        if not selection:
            return
        
        item = self.tree_ordenes.item(selection[0])
        orden_id = item['values'][0]
        
        # Buscar orden completa
        if HAS_DB:
            fecha = self._fecha_actual()
            ordenes = db_local.obtener_ordenes_telegram(fecha=fecha)
            orden = next((o for o in ordenes if o['id'] == orden_id), None)
            
            if orden:
                # Actualizar detalle
                self.txt_mensaje.config(state=tk.NORMAL)
                self.txt_mensaje.delete("1.0", tk.END)
                self.txt_mensaje.insert("1.0", orden.get('mensaje_original', ''))
                self.txt_mensaje.config(state=tk.DISABLED)
                
                self.lbl_vendedor.config(text=orden.get('telegram_nombre', '-'))
                self.lbl_username.config(text=f"@{orden.get('telegram_username', '-')}")
                self.lbl_fecha_orden.config(text=orden.get('fecha_creacion', '-'))
    
    def _verificar_orden(self):
        """Marca la orden seleccionada como verificada."""
        selection = self.tree_ordenes.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona una orden primero")
            return
        
        orden_id = self.tree_ordenes.item(selection[0])['values'][0]
        if HAS_DB:
            db_local.actualizar_orden_telegram(orden_id, estado='verificada', verificada=1)
            self._cargar_ordenes()
    
    def _procesar_orden(self):
        """Marca la orden seleccionada como procesada."""
        selection = self.tree_ordenes.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona una orden primero")
            return
        
        orden_id = self.tree_ordenes.item(selection[0])['values'][0]
        if HAS_DB:
            db_local.actualizar_orden_telegram(orden_id, estado='procesada', procesada=1)
            self._cargar_ordenes()
    
    def _eliminar_orden(self):
        """Elimina la orden seleccionada."""
        selection = self.tree_ordenes.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona una orden primero")
            return
        
        if messagebox.askyesno("Confirmar", "¿Eliminar esta orden?"):
            orden_id = self.tree_ordenes.item(selection[0])['values'][0]
            if HAS_DB:
                db_local.eliminar_orden_telegram(orden_id)
                self._cargar_ordenes()
    
    # ══════════════════════════════════════════════════════════════════
    # CREAR VENTA EN FIREBIRD (ELEVENTA)
    # ══════════════════════════════════════════════════════════════════
    
    def _crear_venta_firebird(self):
        """Abre el diálogo para crear una venta en Firebird desde la orden seleccionada."""
        selection = self.tree_ordenes.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona una orden primero")
            return
        
        # Obtener datos de la orden
        item = self.tree_ordenes.item(selection[0])
        valores = item['values']
        orden_id = valores[0]
        cliente = valores[3] if len(valores) > 3 else ''
        productos_texto = valores[4] if len(valores) > 4 else ''
        
        # Obtener mensaje original de la BD
        if HAS_DB:
            ordenes = db_local.obtener_ordenes_telegram(orden_id=orden_id)
            if ordenes:
                orden_data = ordenes[0]
                mensaje_original = orden_data.get('mensaje_original', '')
                cliente = orden_data.get('cliente', cliente)
            else:
                mensaje_original = productos_texto
        else:
            mensaje_original = productos_texto
        
        # Abrir diálogo de creación de venta
        dialogo = DialogoCrearVenta(
            parent=self.app.ventana,
            app=self.app,
            orden_id=orden_id,
            cliente=cliente,
            mensaje_original=mensaje_original,
            on_venta_creada=self._on_venta_creada
        )
    
    def _on_venta_creada(self, orden_id: int, folio: int):
        """Callback cuando se crea una venta exitosamente."""
        # Actualizar estado de la orden a procesada
        if HAS_DB:
            db_local.actualizar_orden_telegram(orden_id, estado='procesada', procesada=1)
        
        self._cargar_ordenes()
        messagebox.showinfo("Venta Creada", 
                           f"✅ Venta creada exitosamente\n\n"
                           f"Folio: {folio}\n"
                           f"Orden #{orden_id} marcada como procesada")
    
    # ══════════════════════════════════════════════════════════════════
    # CACHÉ DE PRODUCTOS Y CLIENTES
    # ══════════════════════════════════════════════════════════════════
    
    def _cargar_cache_bd(self):
        """
        Carga productos y clientes de la BD Firebird en memoria.
        Esto permite parseo inteligente de pedidos.
        """
        try:
            if not hasattr(self.app, '_ejecutar_sql'):
                return
            
            # ═══════════════════════════════════════════════════════════
            # CARGAR TODOS LOS PRODUCTOS
            # ═══════════════════════════════════════════════════════════
            sql_productos = """
                SET HEADING ON;
                SELECT CODIGO, DESCRIPCION, DINVENTARIO, PVENTA 
                FROM PRODUCTOS 
                ORDER BY DESCRIPCION;
            """
            ok, stdout, stderr = self.app._ejecutar_sql(sql_productos)
            if ok and stdout:
                self.productos_cache = []
                self.productos_por_dimension = {}
                self.productos_por_color = {}
                self.productos_por_tipo_t = {}
                
                for linea in stdout.split('\n'):
                    linea = linea.strip()
                    if not linea or linea.startswith('=') or 'CODIGO' in linea:
                        continue
                    
                    partes = linea.split()
                    if len(partes) >= 4:
                        try:
                            codigo = partes[0]
                            precio = float(partes[-1]) if partes[-1].replace('.','').isdigit() else 0
                            stock_str = partes[-2]
                            stock = int(float(stock_str)) if stock_str != '<null>' and stock_str.replace('.','').isdigit() else 0
                            descripcion = ' '.join(partes[1:-2])
                            
                            prod = (codigo, descripcion, stock, precio)
                            self.productos_cache.append(prod)
                            
                            # ══════════════════════════════════════════════════════
                            # Indexar por dimensiones (múltiples formatos)
                            # Ejemplos: 8X12, 10X14, 24X32X10, 24X32X100
                            # ══════════════════════════════════════════════════════
                            
                            # Formato básico: NxN (8X12, 10X14, etc)
                            dim_match = re.search(r'(\d{1,2})\s*[xX]\s*(\d{1,2})', descripcion)
                            if dim_match:
                                dim = f"{dim_match.group(1)}X{dim_match.group(2)}"
                                if dim not in self.productos_por_dimension:
                                    self.productos_por_dimension[dim] = []
                                self.productos_por_dimension[dim].append(prod)
                            
                            # Formato extendido: NxNxN (24X32X10, 26X40X100)
                            dim_ext_match = re.search(r'(\d{1,2})\s*[xX]\s*(\d{1,2})\s*[xX]\s*(\d+)', descripcion)
                            if dim_ext_match:
                                # Indexar también como dimensión base (24X32)
                                dim_base = f"{dim_ext_match.group(1)}X{dim_ext_match.group(2)}"
                                if dim_base not in self.productos_por_dimension:
                                    self.productos_por_dimension[dim_base] = []
                                if prod not in self.productos_por_dimension[dim_base]:
                                    self.productos_por_dimension[dim_base].append(prod)
                            
                            # También indexar por código si parece dimensión (2432 = 24x32)
                            # Solo si el código es numérico y tiene formato de dimensión válida
                            if re.match(r'^\d{3,4}$', codigo):
                                if len(codigo) == 4:
                                    d1, d2 = int(codigo[:2]), int(codigo[2:])
                                    # Solo dimensiones razonables (5-50 pulgadas)
                                    if 5 <= d1 <= 50 and 5 <= d2 <= 50:
                                        cod_dim = f"{d1}X{d2}"
                                        if cod_dim not in self.productos_por_dimension:
                                            self.productos_por_dimension[cod_dim] = []
                                        if prod not in self.productos_por_dimension[cod_dim]:
                                            self.productos_por_dimension[cod_dim].append(prod)
                                elif len(codigo) == 3:
                                    d1, d2 = int(codigo[0]), int(codigo[1:])
                                    if 4 <= d1 <= 9 and 5 <= d2 <= 30:
                                        cod_dim = f"{d1}X{d2}"
                                        if cod_dim not in self.productos_por_dimension:
                                            self.productos_por_dimension[cod_dim] = []
                                        if prod not in self.productos_por_dimension[cod_dim]:
                                            self.productos_por_dimension[cod_dim].append(prod)
                            
                            # Indexar por color/tipo
                            desc_upper = descripcion.upper()
                            for color in ['NEGRA', 'BLANCA', 'OPACA', 'HERMETICA', 'LISA', 'PERFORADA', 
                                         'DECORADA', 'BASURERA', 'UNICOLOR', 'VERDE', 'ROJA']:
                                if color in desc_upper:
                                    color_key = color.lower()
                                    if color_key not in self.productos_por_color:
                                        self.productos_por_color[color_key] = []
                                    self.productos_por_color[color_key].append(prod)
                            
                            # ══════════════════════════════════════════════════════
                            # Indexar bolsas tipo T (T15, T20, T25, T30, T40, T50)
                            # Ejemplos: "T 15 BLANCO", "T 25 NEGRA FINA", "T 30 BLANCO ECO"
                            # ══════════════════════════════════════════════════════
                            t_match = re.search(r'\bT\s*(\d+)\b', desc_upper)
                            if t_match:
                                t_num = t_match.group(1)
                                t_key = f"T{t_num}"  # T15, T20, T25, etc.
                                if t_key not in self.productos_por_tipo_t:
                                    self.productos_por_tipo_t[t_key] = []
                                self.productos_por_tipo_t[t_key].append(prod)
                        except:
                            pass
            
            # ═══════════════════════════════════════════════════════════
            # CARGAR CLIENTES ÚNICOS
            # ═══════════════════════════════════════════════════════════
            sql_clientes = """
                SET HEADING ON;
                SELECT DISTINCT NOMBRE FROM VENTATICKETS 
                WHERE NOMBRE IS NOT NULL AND NOMBRE <> ''
                ORDER BY NOMBRE;
            """
            ok, stdout, stderr = self.app._ejecutar_sql(sql_clientes)
            if ok and stdout:
                self.clientes_cache = []
                for linea in stdout.split('\n'):
                    linea = linea.strip()
                    if linea and not linea.startswith('=') and 'NOMBRE' not in linea:
                        if linea != '<null>' and not linea.startswith('Ticket '):
                            self.clientes_cache.append(linea)
            
            print(f"[CACHE] Cargados {len(self.productos_cache)} productos, {len(self.clientes_cache)} clientes")
            print(f"[CACHE] Dimensiones indexadas: {list(self.productos_por_dimension.keys())[:10]}...")
            print(f"[CACHE] Tipos T indexados: {list(self.productos_por_tipo_t.keys())}")
            
        except Exception as e:
            print(f"[CACHE] Error cargando caché: {e}")
    
    def _buscar_en_cache(self, texto: str, dimensiones: str = None, color: str = None) -> List[Tuple]:
        """
        Busca productos en el caché local usando código, dimensiones, color y tipo T.
        Retorna lista de (codigo, descripcion, stock, precio).
        """
        resultados = []
        texto_upper = texto.upper().strip() if texto else ''
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 1: Buscar por código exacto primero
        # ═══════════════════════════════════════════════════════════════
        if texto_upper and self.productos_cache:
            for prod in self.productos_cache:
                if prod[0].upper() == texto_upper:  # Código exacto
                    resultados.append(prod)
                    return resultados  # Encontró código exacto, retornar
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 1.5: Buscar bolsas tipo T (T15, T20, T25, T30, T40, T50)
        # Formatos: "T15", "T 15", "t15", "T-15", etc.
        # ═══════════════════════════════════════════════════════════════
        if texto_upper:
            t_match = re.search(r'\bT\s*[-]?\s*(\d+)\b', texto_upper)
            if t_match:
                t_num = t_match.group(1)
                t_key = f"T{t_num}"
                if t_key in self.productos_por_tipo_t:
                    candidatos = self.productos_por_tipo_t[t_key]
                    if color:
                        color_upper = color.upper()
                        resultados = [p for p in candidatos if color_upper in p[1].upper()]
                    else:
                        resultados = list(candidatos)
                    if resultados:
                        return resultados[:10]
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 2: Buscar por dimensiones específicas
        # ═══════════════════════════════════════════════════════════════
        if dimensiones:
            dim_key = dimensiones.upper().replace(' ', '').replace('X', 'X')
            
            # Buscar dimensión exacta
            if dim_key in self.productos_por_dimension:
                candidatos = self.productos_por_dimension[dim_key]
                if color:
                    color_upper = color.upper()
                    resultados = [p for p in candidatos if color_upper in p[1].upper()]
                else:
                    resultados = list(candidatos)
            
            # Si no encontró exacta, buscar dimensiones similares
            if not resultados:
                # Extraer números de la dimensión buscada
                dim_parts = re.findall(r'\d+', dim_key)
                if len(dim_parts) >= 2:
                    d1, d2 = int(dim_parts[0]), int(dim_parts[1])
                    
                    # Buscar dimensiones cercanas (±1)
                    variantes = [
                        f"{d1}X{d2}", f"{d1}X{d2-1}", f"{d1}X{d2+1}",
                        f"{d1-1}X{d2}", f"{d1+1}X{d2}"
                    ]
                    for var in variantes:
                        if var in self.productos_por_dimension:
                            candidatos = self.productos_por_dimension[var]
                            if color:
                                matches = [p for p in candidatos if color.upper() in p[1].upper()]
                                resultados.extend(matches)
                            else:
                                resultados.extend(candidatos)
                    
                    # También buscar formatos con tercer número (24X32X10, 24X32X50, etc)
                    for dim_cache, prods in self.productos_por_dimension.items():
                        if dim_cache.startswith(f"{d1}X{d2}") or dim_cache.startswith(f"{d1}X{d2-1}") or dim_cache.startswith(f"{d1}X{d2+1}"):
                            for p in prods:
                                if p not in resultados:
                                    if color:
                                        if color.upper() in p[1].upper():
                                            resultados.append(p)
                                    else:
                                        resultados.append(p)
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 3: Buscar por color si no hay dimensiones
        # ═══════════════════════════════════════════════════════════════
        if not resultados and color:
            color_key = color.lower()
            if color_key in self.productos_por_color:
                resultados = list(self.productos_por_color[color_key])
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 4: Búsqueda general por texto
        # ═══════════════════════════════════════════════════════════════
        if not resultados and texto_upper:
            for prod in self.productos_cache:
                # Buscar en código o descripción
                if texto_upper in prod[0].upper() or texto_upper in prod[1].upper():
                    resultados.append(prod)
                    if len(resultados) >= 10:
                        break
        
        return resultados[:10]
    
    # ══════════════════════════════════════════════════════════════════
    # FUNCIONES DE CONSULTA A BASE DE DATOS FIREBIRD
    # ══════════════════════════════════════════════════════════════════
    
    def _buscar_clientes_similares(self, texto: str, limite: int = 5) -> List[str]:
        """Busca clientes similares, primero en caché, luego en BD."""
        clientes = []
        texto_upper = texto.upper().strip()
        
        # Buscar primero en caché (más rápido)
        if self.clientes_cache:
            for cliente in self.clientes_cache:
                if texto_upper in cliente.upper():
                    clientes.append(cliente)
                    if len(clientes) >= limite:
                        break
            if clientes:
                return clientes[:limite]
        
        # Si no hay caché o no encontró, buscar en BD
        try:
            if hasattr(self.app, '_ejecutar_sql'):
                sql = f"""
                    SET HEADING ON;
                    SELECT FIRST {limite} DISTINCT NOMBRE 
                    FROM VENTATICKETS 
                    WHERE UPPER(NOMBRE) LIKE UPPER('%{texto}%')
                    AND NOMBRE IS NOT NULL
                    ORDER BY NOMBRE;
                """
                ok, stdout, stderr = self.app._ejecutar_sql(sql)
                if ok and stdout:
                    for linea in stdout.split('\n'):
                        linea = linea.strip()
                        if linea and not linea.startswith('=') and 'NOMBRE' not in linea:
                            if linea and linea != '<null>':
                                clientes.append(linea)
        except Exception as e:
            print(f"Error buscando clientes: {e}")
        return clientes
    
    def _buscar_productos_similares(self, texto: str, limite: int = 5) -> List[Tuple]:
        """Busca productos similares en la base de datos Firebird."""
        productos = []
        try:
            if hasattr(self.app, '_ejecutar_sql'):
                sql = f"""
                    SET HEADING ON;
                    SELECT FIRST {limite} CODIGO, DESCRIPCION, DINVENTARIO, PVENTA 
                    FROM PRODUCTOS 
                    WHERE UPPER(DESCRIPCION) LIKE UPPER('%{texto}%')
                    ORDER BY DESCRIPCION;
                """
                ok, stdout, stderr = self.app._ejecutar_sql(sql)
                if ok and stdout:
                    header_visto = False
                    for linea in stdout.split('\n'):
                        linea = linea.strip()
                        if not linea or linea.startswith('='):
                            continue
                        if 'CODIGO' in linea and 'DESCRIPCION' in linea:
                            header_visto = True
                            continue
                        if not header_visto:
                            continue
                        partes = linea.split()
                        if len(partes) >= 4:
                            try:
                                codigo = partes[0]
                                precio = float(partes[-1])
                                stock = int(float(partes[-2])) if partes[-2] != '<null>' else 0
                                descripcion = ' '.join(partes[1:-2])
                                productos.append((codigo, descripcion, stock, precio))
                            except:
                                pass
        except Exception as e:
            print(f"Error buscando productos: {e}")
        return productos
    
    def _obtener_productos_populares(self, limite: int = 10) -> List[Tuple]:
        """Obtiene productos con stock."""
        productos = []
        try:
            if hasattr(self.app, '_ejecutar_sql'):
                sql = f"""
                    SET HEADING ON;
                    SELECT FIRST {limite} CODIGO, DESCRIPCION, DINVENTARIO, PVENTA 
                    FROM PRODUCTOS 
                    WHERE DINVENTARIO > 0
                    ORDER BY DINVENTARIO DESC;
                """
                ok, stdout, stderr = self.app._ejecutar_sql(sql)
                if ok and stdout:
                    header_visto = False
                    for linea in stdout.split('\n'):
                        linea = linea.strip()
                        if not linea or linea.startswith('='):
                            continue
                        if 'CODIGO' in linea and 'DESCRIPCION' in linea:
                            header_visto = True
                            continue
                        if not header_visto:
                            continue
                        partes = linea.split()
                        if len(partes) >= 4:
                            try:
                                codigo = partes[0]
                                precio = float(partes[-1])
                                stock = int(float(partes[-2])) if partes[-2] != '<null>' else 0
                                descripcion = ' '.join(partes[1:-2])
                                productos.append((codigo, descripcion, stock, precio))
                            except:
                                pass
        except Exception as e:
            print(f"Error obteniendo productos: {e}")
        return productos
    
    def _parsear_pedido(self, texto: str) -> Dict:
        """Parsea un mensaje de pedido y extrae cliente y productos."""
        resultado = {
            'cliente': '',
            'productos': [],
            'productos_texto': '',
            'cliente_sugerido': None,
            'productos_sugeridos': []
        }
        
        texto = texto.strip()
        if not texto:
            return resultado
        
        # Patrones para separar cliente de productos
        separadores = [' - ', ': ', '\n']
        
        cliente = ''
        productos_texto = texto
        
        for sep in separadores:
            if sep in texto:
                partes = texto.split(sep, 1)
                if len(partes) == 2:
                    posible_cliente = partes[0].strip()
                    posible_productos = partes[1].strip()
                    if len(posible_cliente) >= 2 and not posible_cliente.isdigit():
                        cliente = posible_cliente
                        productos_texto = posible_productos
                        break
        
        if not cliente and '\n' in texto:
            lineas = texto.split('\n')
            primera_linea = lineas[0].strip()
            resto = '\n'.join(lineas[1:]).strip()
            if not any(c.isdigit() for c in primera_linea) and len(primera_linea) < 50:
                cliente = primera_linea
                productos_texto = resto
        
        # Si no se detectó cliente y el texto parece ser un nombre (sin números, corto)
        # Tratarlo como cliente potencial
        if not cliente and texto:
            # Verificar si es texto corto sin números (probable nombre de cliente)
            tiene_numeros = any(c.isdigit() for c in texto)
            es_corto = len(texto) < 60
            tiene_palabras = len(texto.split()) <= 6
            
            if not tiene_numeros and es_corto and tiene_palabras and len(texto) >= 2:
                # Es muy probable que sea un nombre de cliente
                cliente = texto
                productos_texto = ''
        
        resultado['cliente'] = cliente
        resultado['productos_texto'] = productos_texto
        resultado['productos'] = self._parsear_lineas_productos(productos_texto)
        
        if cliente:
            clientes_similares = self._buscar_clientes_similares(cliente, 3)
            if clientes_similares:
                resultado['cliente_sugerido'] = clientes_similares[0]
        
        return resultado
    
    def _parsear_lineas_productos(self, texto: str) -> List[Dict]:
        """
        Parsea líneas de productos con cantidades.
        Interpreta formatos especiales:
        - t15, t20, t25, t30, t40, t50, t 15 = bolsas por paquetes de 100
        - 812, 8x12, 8 x 12 = dimensiones de bolsa (8x12 pulgadas)
        - 1216, 12x16 = dimensiones de bolsa
        - millar, millares = 1000 unidades
        - docena = 12 unidades
        """
        productos = []
        lineas = re.split(r'[,\n]', texto)
        
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            
            producto = {
                'nombre': linea, 
                'cantidad': 1, 
                'original': linea,
                'unidad': 'paq',  # Por defecto paquetes (bolsas)
                'nota': '',
                'dimensiones': None,
                'tamano_t': None,
                'color': None
            }
            
            linea_trabajo = linea
            
            # ═══════════════════════════════════════════════════════════
            # EXTRAER CANTIDAD (al inicio de la línea)
            # ═══════════════════════════════════════════════════════════
            cantidad_match = re.match(r'^(\d+)\s+(.+)$', linea_trabajo)
            if cantidad_match:
                producto['cantidad'] = int(cantidad_match.group(1))
                linea_trabajo = cantidad_match.group(2).strip()
            
            # ═══════════════════════════════════════════════════════════
            # DETECTAR DIMENSIONES DE BOLSA
            # Formatos: 812, 8x12, 8 x 12, 8X12, 1216, 12x16, etc.
            # ═══════════════════════════════════════════════════════════
            
            # Formato compacto: 812 = 8x12, 1216 = 12x16, 1620 = 16x20
            dim_compacta = re.search(r'\b(\d{1,2})(\d{2})\b', linea_trabajo)
            if dim_compacta:
                d1 = dim_compacta.group(1)
                d2 = dim_compacta.group(2)
                # Verificar que sean dimensiones válidas (no años ni códigos largos)
                if int(d1) <= 30 and int(d2) <= 40:
                    producto['dimensiones'] = f"{d1}x{d2}"
                    producto['nota'] = f"Bolsa {d1}x{d2} (paq 100)"
                    # Remover del texto para buscar color/tipo
                    linea_trabajo = re.sub(r'\b\d{3,4}\b', '', linea_trabajo, count=1).strip()
            
            # Formato explícito: 8x12, 8 x 12, 8X12
            dim_explicita = re.search(r'\b(\d{1,2})\s*[xX]\s*(\d{1,2})\b', linea_trabajo)
            if dim_explicita and not producto['dimensiones']:
                d1 = dim_explicita.group(1)
                d2 = dim_explicita.group(2)
                producto['dimensiones'] = f"{d1}x{d2}"
                producto['nota'] = f"Bolsa {d1}x{d2} (paq 100)"
                linea_trabajo = re.sub(r'\b\d{1,2}\s*[xX]\s*\d{1,2}\b', '', linea_trabajo).strip()
            
            # ═══════════════════════════════════════════════════════════
            # DETECTAR TAMAÑO T (t15, t20, t25, t30, t40, t50, t 15)
            # ═══════════════════════════════════════════════════════════
            tamano_match = re.search(r'\b[tT]\s*(\d+)\b', linea_trabajo)
            if tamano_match:
                tamano = tamano_match.group(1)
                producto['tamano_t'] = tamano
                producto['nota'] = f"Bolsa T{tamano} (paq 100)"
                linea_trabajo = re.sub(r'\b[tT]\s*\d+\b', '', linea_trabajo).strip()
            
            # ═══════════════════════════════════════════════════════════
            # DETECTAR COLOR/TIPO
            # ═══════════════════════════════════════════════════════════
            colores = ['negra', 'negro', 'blanca', 'blanco', 'opaca', 'opaco', 
                      'transparente', 'trans', 'cristal', 'roja', 'rojo',
                      'azul', 'verde', 'amarilla', 'amarillo', 'natural',
                      'perf', 'perforada', 'perforado', 'gruesa', 'grueso',
                      'delgada', 'delgado', 'biodegradable', 'bio']
            
            for color in colores:
                if re.search(rf'\b{color}\b', linea_trabajo, re.IGNORECASE):
                    producto['color'] = color.lower()
                    break
            
            # ═══════════════════════════════════════════════════════════
            # DETECTAR MILLARES/DOCENAS
            # ═══════════════════════════════════════════════════════════
            if re.search(r'\bmillares?\b', linea_trabajo, re.IGNORECASE):
                producto['unidad'] = 'millar'
                producto['nota'] += ' (x1000)'
                linea_trabajo = re.sub(r'\bmillares?\b', '', linea_trabajo, flags=re.IGNORECASE)
            
            if re.search(r'\bdocenas?\b', linea_trabajo, re.IGNORECASE):
                producto['unidad'] = 'docena'
                producto['nota'] += ' (x12)'
                linea_trabajo = re.sub(r'\bdocenas?\b', '', linea_trabajo, flags=re.IGNORECASE)
            
            # Guardar nombre limpio para búsqueda
            producto['nombre'] = linea_trabajo.strip() if linea_trabajo.strip() else linea
            
            if producto['nombre'] or producto['dimensiones'] or producto['tamano_t']:
                productos.append(producto)
        
        return productos
    
    def _buscar_producto_en_bd(self, texto_producto: str, limite: int = 5, 
                                producto_parseado: Dict = None) -> List[Tuple]:
        """
        Busca productos usando caché local y BD Firebird.
        Maneja códigos, dimensiones (8x12, 812), tamaños T, colores y tipos.
        """
        productos_encontrados = []
        
        # Si tenemos producto parseado, usar su información
        dimensiones = None
        tamano_t = None
        color = None
        
        if producto_parseado:
            dimensiones = producto_parseado.get('dimensiones')
            tamano_t = producto_parseado.get('tamano_t')
            color = producto_parseado.get('color')
        else:
            # Extraer información del texto directamente
            # Dimensiones compactas: 812, 1216
            dim_match = re.search(r'\b(\d{1,2})(\d{2})\b', texto_producto)
            if dim_match:
                d1, d2 = dim_match.group(1), dim_match.group(2)
                if int(d1) <= 30 and int(d2) <= 40:
                    dimensiones = f"{d1}x{d2}"
            
            # Dimensiones explícitas: 8x12
            if not dimensiones:
                dim_match = re.search(r'\b(\d{1,2})\s*[xX]\s*(\d{1,2})\b', texto_producto)
                if dim_match:
                    dimensiones = f"{dim_match.group(1)}x{dim_match.group(2)}"
            
            # Tamaño T
            t_match = re.search(r'\b[tT]\s*(\d+)\b', texto_producto)
            if t_match:
                tamano_t = t_match.group(1)
            
            # Color/Tipo
            tipos = ['negra', 'negro', 'blanca', 'blanco', 'opaca', 'opaco', 
                    'transparente', 'trans', 'cristal', 'perf', 'perforada',
                    'hermetica', 'lisa', 'tb lisa', 'decorada', 'basurera', 'unicolor']
            for c in tipos:
                if re.search(rf'\b{c}\b', texto_producto, re.IGNORECASE):
                    color = c.split()[0]  # Solo la primera palabra
                    break
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 1: Buscar en caché local (más rápido)
        # ═══════════════════════════════════════════════════════════════
        if self.productos_cache:
            resultados_cache = self._buscar_en_cache(texto_producto, dimensiones, color)
            if resultados_cache:
                productos_encontrados = resultados_cache[:limite]
                return productos_encontrados
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 2: Si no hay caché, buscar en BD
        # ═══════════════════════════════════════════════════════════════
        
        try:
            if hasattr(self.app, '_ejecutar_sql'):
                condiciones = []
                
                # Buscar por dimensiones
                if dimensiones:
                    # Buscar tanto "8x12" como "8X12" como "8 x 12"
                    d1, d2 = dimensiones.split('x')
                    condiciones.append(f"(UPPER(DESCRIPCION) LIKE '%{d1}X{d2}%' OR "
                                      f"UPPER(DESCRIPCION) LIKE '%{d1} X {d2}%' OR "
                                      f"UPPER(CODIGO) LIKE '%{d1}{d2}%')")
                
                # Buscar por tamaño T
                if tamano_t:
                    condiciones.append(f"(UPPER(DESCRIPCION) LIKE '%T{tamano_t}%' OR "
                                      f"UPPER(DESCRIPCION) LIKE '%T {tamano_t}%' OR "
                                      f"UPPER(DESCRIPCION) LIKE '%T-{tamano_t}%')")
                
                # Buscar por color
                if color:
                    condiciones.append(f"UPPER(DESCRIPCION) LIKE UPPER('%{color}%')")
                
                # Si no hay condiciones específicas, buscar por texto general
                if not condiciones:
                    palabras = re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}', texto_producto.lower())
                    for palabra in palabras[:3]:
                        condiciones.append(f"UPPER(DESCRIPCION) LIKE UPPER('%{palabra}%')")
                
                if condiciones:
                    where = ' AND '.join(condiciones)
                    sql = f"""
                        SELECT FIRST {limite} CODIGO, DESCRIPCION, 
                               COALESCE(INVENTARIO, 0) as INV, COALESCE(PRECIO1, 0) as PRECIO
                        FROM PRODUCTOS 
                        WHERE {where}
                        ORDER BY INVENTARIO DESC;
                    """
                    ok, stdout, stderr = self.app._ejecutar_sql(sql)
                    if ok and stdout:
                        for linea in stdout.split('\n'):
                            linea = linea.strip()
                            if linea and not linea.startswith('=') and 'CODIGO' not in linea:
                                partes = linea.split()
                                if len(partes) >= 4:
                                    cod = partes[0]
                                    precio = float(partes[-1]) if partes[-1].replace('.','').isdigit() else 0
                                    inv = int(partes[-2]) if partes[-2].isdigit() else 0
                                    desc = ' '.join(partes[1:-2])
                                    productos_encontrados.append((cod, desc, inv, precio))
                
                # Si aún no hay resultados, buscar solo por dimensiones sin color
                if not productos_encontrados and dimensiones:
                    d1, d2 = dimensiones.split('x')
                    sql = f"""
                        SELECT FIRST {limite} CODIGO, DESCRIPCION, 
                               COALESCE(INVENTARIO, 0) as INV, COALESCE(PRECIO1, 0) as PRECIO
                        FROM PRODUCTOS 
                        WHERE UPPER(DESCRIPCION) LIKE '%{d1}X{d2}%' 
                           OR UPPER(DESCRIPCION) LIKE '%{d1} X {d2}%'
                           OR UPPER(CODIGO) LIKE '%{d1}{d2}%'
                        ORDER BY INVENTARIO DESC;
                    """
                    ok, stdout, stderr = self.app._ejecutar_sql(sql)
                    if ok and stdout:
                        for linea in stdout.split('\n'):
                            linea = linea.strip()
                            if linea and not linea.startswith('=') and 'CODIGO' not in linea:
                                partes = linea.split()
                                if len(partes) >= 4:
                                    cod = partes[0]
                                    precio = float(partes[-1]) if partes[-1].replace('.','').isdigit() else 0
                                    inv = int(partes[-2]) if partes[-2].isdigit() else 0
                                    desc = ' '.join(partes[1:-2])
                                    if (cod, desc, inv, precio) not in productos_encontrados:
                                        productos_encontrados.append((cod, desc, inv, precio))
                
                # Búsqueda general si no hay resultados
                if not productos_encontrados:
                    productos_encontrados = self._buscar_productos_similares(texto_producto, limite)
                    
        except Exception as e:
            print(f"Error buscando producto: {e}")
        
        return productos_encontrados[:limite]
    
    # ══════════════════════════════════════════════════════════════════
    # BOT DE TELEGRAM
    # ══════════════════════════════════════════════════════════════════
    
    def _iniciar_bot(self):
        """Inicia el bot de Telegram en un hilo separado."""
        if not HAS_TELEGRAM:
            messagebox.showerror("Error", "python-telegram-bot no está instalado.\n"
                                          "Ejecuta: pip install python-telegram-bot")
            return
        
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Token", "Ingresa el token del bot primero")
            return
        
        if self.bot_running:
            messagebox.showinfo("Bot", "El bot ya está en ejecución")
            return
        
        self.bot_running = True
        self.status_var.set("🟢 Iniciando...")
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_detener.config(state=tk.NORMAL)
        
        self.bot_thread = threading.Thread(target=self._run_bot, args=(token,), daemon=True)
        self.bot_thread.start()
    
    def _run_bot(self, token: str):
        """Ejecuta el bot de Telegram (en hilo separado)."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.bot_app = Application.builder().token(token).build()
            
            self.bot_app.add_handler(CommandHandler("start", self._cmd_start))
            self.bot_app.add_handler(CommandHandler("ayuda", self._cmd_ayuda))
            self.bot_app.add_handler(CommandHandler("help", self._cmd_ayuda))
            self.bot_app.add_handler(CommandHandler("pedido", self._cmd_pedido))
            self.bot_app.add_handler(CommandHandler("p", self._cmd_pedido))
            self.bot_app.add_handler(CommandHandler("stock", self._cmd_stock))
            self.bot_app.add_handler(CommandHandler("s", self._cmd_stock))
            self.bot_app.add_handler(CommandHandler("cliente", self._cmd_cliente))
            self.bot_app.add_handler(CommandHandler("c", self._cmd_cliente))
            self.bot_app.add_handler(CommandHandler("productos", self._cmd_productos))
            self.bot_app.add_handler(CommandHandler("buscar", self._cmd_buscar))
            self.bot_app.add_handler(CommandHandler("b", self._cmd_buscar))
            self.bot_app.add_handler(CallbackQueryHandler(self._callback_handler))
            # Handler de inline queries para autosugerencias
            self.bot_app.add_handler(InlineQueryHandler(self._inline_query_handler))
            self.bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._msg_pedido))
            
            # Manejador de errores para evitar tracebacks largos
            self.bot_app.add_error_handler(self._error_handler)
            
            self.parent.after(0, lambda: self.status_var.set("🟢 Bot activo"))
            
            self.loop.run_until_complete(self.bot_app.initialize())
            self.loop.run_until_complete(self.bot_app.start())
            self.loop.run_until_complete(self.bot_app.updater.start_polling())
            self.loop.run_forever()
            
        except Exception as e:
            error_msg = str(e)
            self.parent.after(0, lambda: self._on_bot_error(error_msg))
    
    async def _error_handler(self, update, context):
        """Manejador global de errores del bot - evita tracebacks largos."""
        from telegram.error import TimedOut, NetworkError, BadRequest
        
        error = context.error
        
        # Errores de red (timeout, sin conexión) - solo log simple
        if isinstance(error, (TimedOut, NetworkError)):
            print(f"[BOT] ⚠️ Error de red: {type(error).__name__}")
            return
        
        # Errores de Telegram (query expirado, mensaje muy viejo)
        if isinstance(error, BadRequest):
            error_msg = str(error).lower()
            if "query is too old" in error_msg or "message is not modified" in error_msg:
                return  # Ignorar silenciosamente
            print(f"[BOT] ⚠️ BadRequest: {error}")
            return
        
        # Otros errores - log con más detalle
        print(f"[BOT] ❌ Error: {type(error).__name__}: {error}")
    
    def _on_bot_error(self, error: str):
        """Maneja errores del bot."""
        self.status_var.set("🔴 Error")
        self.bot_running = False
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        messagebox.showerror("Error del Bot", f"Error al iniciar el bot:\n{error}")
    
    def _detener_bot(self):
        """Detiene el bot de Telegram."""
        if not self.bot_running:
            return
        
        self.bot_running = False
        self.status_var.set("🟡 Deteniendo...")
        
        try:
            if self.loop and self.bot_app:
                async def stop_bot():
                    await self.bot_app.updater.stop()
                    await self.bot_app.stop()
                    await self.bot_app.shutdown()
                
                future = asyncio.run_coroutine_threadsafe(stop_bot(), self.loop)
                future.result(timeout=5)
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception as e:
            print(f"Error deteniendo bot: {e}")
        
        self.status_var.set("⚫ Detenido")
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
    
    # ══════════════════════════════════════════════════════════════════
    # HANDLERS DEL BOT
    # ══════════════════════════════════════════════════════════════════
    
    async def _cmd_start(self, update, context):
        """Comando /start - Saludo inicial mejorado."""
        user = update.message.from_user
        nombre = user.first_name or "Usuario"
        
        # Mensaje de bienvenida personalizado
        bienvenida = f"👋 *¡Hola {nombre}!*\n\n"
        bienvenida += "Soy tu asistente de pedidos. Puedo ayudarte a:\n\n"
        bienvenida += "📦 Registrar pedidos de clientes\n"
        bienvenida += "🔍 Buscar productos y precios\n"
        bienvenida += "👥 Encontrar clientes en el sistema\n\n"
        
        bienvenida += "━━━━━━━━━━━━━━━━━━━━━\n"
        bienvenida += "📝 *¿Cómo hacer un pedido?*\n"
        bienvenida += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        bienvenida += "Simplemente escribe el nombre del cliente\n"
        bienvenida += "seguido de los productos:\n\n"
        bienvenida += "```\nLas Granjas\n10 812 negra\n5 t25 blanca\n```\n\n"
        
        # Botones de inicio rápido
        keyboard = [
            [InlineKeyboardButton("🔍 Buscar Cliente", callback_data="inicio_buscar_cliente"),
             InlineKeyboardButton("📦 Ver Productos", callback_data="inicio_ver_productos")],
            [InlineKeyboardButton("❓ Ayuda", callback_data="inicio_ayuda")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            bienvenida,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    async def _cmd_ayuda(self, update, context):
        """Comando /ayuda - Lista de comandos mejorada."""
        ayuda = "📚 *GUÍA RÁPIDA*\n"
        ayuda += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        ayuda += "🛒 *HACER UN PEDIDO:*\n"
        ayuda += "Escribe directamente:\n"
        ayuda += "```\nNombre Cliente\n10 812 negra\n5 t25 blanca\n```\n\n"
        
        ayuda += "🔤 *FORMATOS DE PRODUCTOS:*\n"
        ayuda += "• `812` o `8x12` → Bolsa 8x12\n"
        ayuda += "• `t25` o `t 25` → Bolsa T25\n"
        ayuda += "• `negra`, `blanca`, `opaca`\n\n"
        
        ayuda += "⌨️ *COMANDOS:*\n"
        ayuda += "• `/b texto` - Buscar todo\n"
        ayuda += "• `/c nombre` - Buscar cliente\n"
        ayuda += "• `/s producto` - Ver stock\n\n"
        
        ayuda += "💡 *TIPS:*\n"
        ayuda += "• Toca los botones para seleccionar\n"
        ayuda += "• No necesitas escribir todo exacto\n"
        ayuda += "• El bot te sugiere opciones"
        
        keyboard = [
            [InlineKeyboardButton("🔍 Probar Búsqueda", callback_data="inicio_buscar_cliente")],
            [InlineKeyboardButton("📦 Ver Productos", callback_data="inicio_ver_productos")]
        ]
        
        await update.message.reply_text(
            ayuda,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _cmd_pedido(self, update, context):
        """Comando /pedido - Crea una orden."""
        texto = ' '.join(context.args) if context.args else ''
        await self._procesar_mensaje_pedido(update, texto)
    
    async def _msg_pedido(self, update, context):
        """Maneja mensajes normales como pedidos."""
        texto = update.message.text
        user_id = update.message.from_user.id
        
        # Verificar si el usuario tiene una sesión activa esperando algo
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            
            # Esperando productos adicionales
            if session.get('esperando_productos'):
                await self._agregar_productos_sesion(update, texto)
                return
            
            # Esperando búsqueda de cliente
            if session.get('esperando_cliente'):
                session['esperando_cliente'] = False
                clientes = self._buscar_clientes_similares(texto, 8)
                if clientes:
                    keyboard = []
                    for cli in clientes:
                        keyboard.append([InlineKeyboardButton(f"👤 {cli[:40]}", callback_data=f"confirmar_cli:{cli[:50]}")])
                    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
                    
                    await update.message.reply_text(
                        f"🔍 *Resultados para '{texto}':*\n\n"
                        f"Encontré {len(clientes)} cliente(s).\n"
                        f"_Toca para seleccionar:_",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        f"😕 No encontré clientes con '{texto}'\n\n"
                        f"Intenta con otro nombre o usa el nombre tal cual.",
                        parse_mode="Markdown"
                    )
                return
            
            # Esperando búsqueda de producto
            if session.get('esperando_busqueda_prod') is not None:
                idx = session['esperando_busqueda_prod']
                session['esperando_busqueda_prod'] = None
                productos = self._buscar_producto_en_bd(texto, 8)
                if productos:
                    keyboard = []
                    for cod, desc, stock, precio in productos:
                        emoji = "✅" if stock > 0 else "❌"
                        callback_data = f"confirmar_prod:{idx}:{cod}:{desc[:35]}"
                        keyboard.append([InlineKeyboardButton(f"{emoji} {desc[:30]}", callback_data=callback_data)])
                    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data=f"volver_prod:{idx}")])
                    
                    await update.message.reply_text(
                        f"🔍 *Resultados para '{texto}':*\n\n"
                        f"_Toca el producto correcto:_",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        f"😕 No encontré '{texto}'\n\nIntenta con otro término.",
                        parse_mode="Markdown"
                    )
                return
        
        await self._procesar_mensaje_pedido(update, texto)
    
    async def _procesar_mensaje_pedido(self, update, texto: str):
        """
        Procesa un mensaje de pedido con confirmación interactiva mejorada.
        Flujo: Mensaje -> Confirmar Cliente -> Confirmar Productos -> Crear Orden
        """
        if not texto.strip():
            keyboard = [
                [InlineKeyboardButton("🔍 Buscar Cliente", callback_data="inicio_buscar_cliente")],
                [InlineKeyboardButton("❓ Ver Ayuda", callback_data="inicio_ayuda")]
            ]
            await update.message.reply_text(
                "📝 *¿Cómo hacer un pedido?*\n\n"
                "Escribe el cliente y productos así:\n\n"
                "```\nJuan Pérez\n10 812 negra\n5 t25 blanca\n```\n\n"
                "O busca un cliente primero 👇",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        user = update.message.from_user
        user_id = user.id
        
        # Indicador de procesamiento
        processing_msg = await update.message.reply_text("⏳ _Analizando pedido..._", parse_mode="Markdown")
        
        # Parsear el mensaje
        parsed = self._parsear_pedido(texto)
        cliente_texto = parsed['cliente']
        productos_parseados = parsed['productos']
        
        # Eliminar mensaje de procesamiento
        try:
            await processing_msg.delete()
        except:
            pass
        
        # Buscar clientes similares
        clientes_encontrados = []
        if cliente_texto:
            clientes_encontrados = self._buscar_clientes_similares(cliente_texto, 5)
        
        # Crear sesión temporal para este pedido
        self.user_sessions[user_id] = {
            'mensaje_original': texto,
            'cliente_texto': cliente_texto,
            'cliente_confirmado': None,
            'productos_parseados': productos_parseados,
            'productos_confirmados': [],
            'producto_actual_idx': 0,
            'timestamp': datetime.now(),
            'esperando_productos': False,
            'esperando_cliente': False,
            'esperando_busqueda_prod': None
        }
        
        # Crear resumen del pedido detectado
        resumen_productos = ""
        if productos_parseados:
            resumen_productos = "\n📦 *Productos detectados:*\n"
            for i, p in enumerate(productos_parseados, 1):
                dims = p.get('dimensiones', '')
                tam = p.get('tamano_t', '')
                color = p.get('color', '')
                info = dims or (f"T{tam}" if tam else '') or ''
                if info and color:
                    info = f"{info} {color}"
                elif color:
                    info = color
                resumen_productos += f"  {i}. {p['cantidad']}x {info or p['nombre'][:20]}\n"
        
        # PASO 1: Confirmar cliente
        if clientes_encontrados:
            keyboard = []
            
            # Mostrar el más probable primero con emoji especial
            keyboard.append([InlineKeyboardButton(
                f"✅ {clientes_encontrados[0][:38]}", 
                callback_data=f"confirmar_cli:{clientes_encontrados[0][:50]}"
            )])
            
            # Resto de clientes
            for cli in clientes_encontrados[1:]:
                keyboard.append([InlineKeyboardButton(
                    f"👤 {cli[:40]}", 
                    callback_data=f"confirmar_cli:{cli[:50]}"
                )])
            
            keyboard.append([
                InlineKeyboardButton("✏️ Usar original", callback_data=f"usar_cliente:{cliente_texto[:50]}"),
                InlineKeyboardButton("🔍 Otro", callback_data="buscar_cliente")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            mensaje = f"━━━━━━━━━━━━━━━━━━━━━\n"
            mensaje += f"📋 *NUEVO PEDIDO*\n"
            mensaje += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            mensaje += f"👤 *Cliente:* `{cliente_texto}`\n"
            mensaje += resumen_productos
            mensaje += f"\n━━━━━━━━━━━━━━━━━━━━━\n"
            mensaje += f"*¿Es este cliente?*\n"
            mensaje += f"_Toca la opción correcta:_"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
            
        elif cliente_texto:
            # No se encontraron clientes similares
            keyboard = [
                [InlineKeyboardButton("✅ Sí, usar este nombre", callback_data=f"usar_cliente:{cliente_texto[:50]}")],
                [InlineKeyboardButton("🔍 Buscar otro cliente", callback_data="buscar_cliente")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            mensaje = f"━━━━━━━━━━━━━━━━━━━━━\n"
            mensaje += f"📋 *NUEVO PEDIDO*\n"
            mensaje += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            mensaje += f"👤 *Cliente:* `{cliente_texto}`\n"
            mensaje += resumen_productos
            mensaje += f"\n⚠️ _No encontré este cliente en el sistema_\n"
            mensaje += f"_¿Continuar con este nombre?_"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            # No se detectó cliente - mostrar productos y pedir cliente
            keyboard = [
                [InlineKeyboardButton("🔍 Buscar cliente", callback_data="buscar_cliente")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            mensaje = f"━━━━━━━━━━━━━━━━━━━━━\n"
            mensaje += f"📋 *NUEVO PEDIDO*\n"
            mensaje += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            mensaje += f"⚠️ *No detecté el cliente*\n"
            mensaje += resumen_productos
            mensaje += f"\n_Busca el cliente para continuar:_"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
    
    async def _confirmar_productos(self, update, user_id: int, editar_mensaje: bool = True):
        """Muestra productos para confirmar con interfaz mejorada."""
        if user_id not in self.user_sessions:
            return
        
        session = self.user_sessions[user_id]
        productos = session['productos_parseados']
        idx = session['producto_actual_idx']
        total_productos = len(productos)
        confirmados = len(session['productos_confirmados'])
        
        if idx >= total_productos:
            # Todos los productos confirmados, mostrar resumen final
            await self._mostrar_resumen_final(update, user_id, editar_mensaje)
            return
        
        producto = productos[idx]
        cantidad = producto['cantidad']
        nombre = producto['nombre']
        original = producto.get('original', nombre)
        nota = producto.get('nota', '')
        unidad = producto.get('unidad', 'paq')
        dimensiones = producto.get('dimensiones')
        tamano_t = producto.get('tamano_t')
        color = producto.get('color')
        
        # Buscar coincidencias en BD pasando el producto parseado
        coincidencias = self._buscar_producto_en_bd(nombre, 6, producto_parseado=producto)
        
        keyboard = []
        
        # Barra de progreso visual
        progress = "".join(["●" if i < confirmados else "○" for i in range(total_productos)])
        
        texto_producto = f"━━━━━━━━━━━━━━━━━━━━━\n"
        texto_producto += f"📦 *PRODUCTO {idx + 1} DE {total_productos}*\n"
        texto_producto += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        texto_producto += f"Progreso: {progress}\n\n"
        
        texto_producto += f"📝 `{original}`\n\n"
        texto_producto += f"🔢 *Cantidad:* {cantidad} {unidad}\n"
        
        # Mostrar interpretación de forma compacta
        interpretacion = []
        if dimensiones:
            interpretacion.append(f"📐 {dimensiones}")
        if tamano_t:
            interpretacion.append(f"T{tamano_t}")
        if color:
            interpretacion.append(f"🎨 {color}")
        
        if interpretacion:
            texto_producto += f"🔍 *Detectado:* {' • '.join(interpretacion)}\n"
        
        texto_producto += f"\n_Selecciona el producto correcto:_\n"
        
        if coincidencias:
            # Primer resultado con emoji especial (más probable)
            cod, desc, stock, precio = coincidencias[0]
            emoji = "✅" if stock > 0 else "⚠️"
            btn_text = f"{emoji} {desc[:32]}"
            callback_data = f"confirmar_prod:{idx}:{cod}:{desc[:35]}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
            
            # Resto de resultados
            for cod, desc, stock, precio in coincidencias[1:]:
                emoji = "📦" if stock > 0 else "❌"
                btn_text = f"{emoji} {desc[:32]}"
                callback_data = f"confirmar_prod:{idx}:{cod}:{desc[:35]}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
        else:
            texto_producto += "\n⚠️ _No encontré coincidencias_\n"
        
        # Opciones adicionales en una fila compacta
        keyboard.append([
            InlineKeyboardButton("🔍 Buscar", callback_data=f"buscar_prod:{idx}"),
            InlineKeyboardButton("🔢 Cantidad", callback_data=f"cambiar_cant:{idx}")
        ])
        keyboard.append([
            InlineKeyboardButton("⏭️ Omitir", callback_data=f"omitir_prod:{idx}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if editar_mensaje:
            try:
                await update.callback_query.message.edit_text(
                    texto_producto,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            except:
                await update.callback_query.message.reply_text(
                    texto_producto,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                texto_producto,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    
    async def _mostrar_resumen_final(self, update, user_id: int, editar_mensaje: bool = True):
        """Muestra resumen final del pedido con interfaz mejorada."""
        if user_id not in self.user_sessions:
            return
        
        session = self.user_sessions[user_id]
        cliente = session.get('cliente_confirmado', session.get('cliente_texto', 'Sin cliente'))
        productos = session.get('productos_confirmados', [])
        
        texto = f"━━━━━━━━━━━━━━━━━━━━━\n"
        texto += f"✅ *PEDIDO LISTO*\n"
        texto += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        texto += f"👤 *Cliente:*\n{cliente}\n\n"
        texto += f"📦 *Productos ({len(productos)}):*\n"
        
        if productos:
            total_items = 0
            for p in productos:
                total_items += p['cantidad']
                texto += f"  ✓ {p['cantidad']}x {p['descripcion'][:30]}\n"
            texto += f"\n📊 *Total items:* {total_items}\n"
        else:
            texto += "  ⚠️ _Sin productos confirmados_\n"
        
        texto += f"\n━━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [
            [InlineKeyboardButton("✅ CREAR PEDIDO", callback_data="crear_pedido_final")],
            [InlineKeyboardButton("➕ Agregar productos", callback_data="agregar_mas_productos"),
             InlineKeyboardButton("✏️ Editar", callback_data="reiniciar_pedido")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if editar_mensaje:
            try:
                await update.callback_query.message.edit_text(
                    texto,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            except:
                await update.callback_query.message.reply_text(
                    texto,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                texto,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    
    async def _agregar_productos_sesion(self, update, texto: str):
        """Agrega productos adicionales a la sesión actual."""
        user_id = update.message.from_user.id
        if user_id not in self.user_sessions:
            return
        
        session = self.user_sessions[user_id]
        nuevos_productos = self._parsear_lineas_productos(texto)
        
        if nuevos_productos:
            session['productos_parseados'].extend(nuevos_productos)
            session['esperando_productos'] = False
            
            await update.message.reply_text(
                f"✅ {len(nuevos_productos)} producto(s) agregado(s).\n"
                f"Continuando con la confirmación..."
            )
            
            # Continuar confirmación desde donde quedó
            await self._confirmar_productos(update, user_id, editar_mensaje=False)
    
    async def _cmd_buscar(self, update, context):
        """Comando /buscar - Búsqueda combinada."""
        if not context.args:
            await update.message.reply_text(
                "🔍 *Búsqueda rápida*\n\n"
                "Uso: `/buscar [texto]`\n"
                "Ejemplo: `/buscar bolsa` o `/b juan`",
                parse_mode="Markdown"
            )
            return
        
        termino = ' '.join(context.args)
        respuesta = f"🔍 *Resultados para '{termino}':*\n\n"
        keyboard = []
        
        clientes = self._buscar_clientes_similares(termino, 5)
        if clientes:
            respuesta += "👥 *Clientes (toca para seleccionar):*\n"
            for i, cli in enumerate(clientes, 1):
                respuesta += f"  {i}. {cli}\n"
                # Agregar botón para cada cliente
                keyboard.append([InlineKeyboardButton(f"👤 {cli[:30]}", callback_data=f"cli:{cli[:60]}")])
            respuesta += "\n"
        
        productos = self._buscar_productos_similares(termino, 8)
        if productos:
            respuesta += "📦 *Productos (toca para agregar):*\n"
            for cod, desc, stock, precio in productos:
                emoji = "✅" if stock > 0 else "❌"
                respuesta += f"  {emoji} {desc[:30]}\n     Stock: {stock} | ${precio:.2f}\n"
                # Agregar botón para cada producto
                keyboard.append([InlineKeyboardButton(f"📦 {desc[:25]} (${precio:.0f})", callback_data=f"prod:{desc[:50]}")])
        
        if not clientes and not productos:
            respuesta = f"❌ No se encontraron resultados para '{termino}'"
            await update.message.reply_text(respuesta, parse_mode="Markdown")
        else:
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await update.message.reply_text(respuesta, parse_mode="Markdown", reply_markup=reply_markup)
    
    async def _callback_handler(self, update, context):
        """Maneja callbacks de botones inline con flujo de confirmación."""
        query = update.callback_query
        data = query.data
        user_id = query.from_user.id
        
        # Helper para responder de forma segura (ignora timeouts de Telegram)
        async def safe_answer(text=None, show_alert=False):
            try:
                await query.answer(text, show_alert=show_alert)
            except Exception:
                pass  # Ignorar errores de query expirado
        
        # ═══════════════════════════════════════════════════════════════
        # BOTONES DE INICIO RÁPIDO
        # ═══════════════════════════════════════════════════════════════
        
        if data == "inicio_buscar_cliente":
            await safe_answer()
            await query.message.edit_text(
                "🔍 *Buscar Cliente*\n\n"
                "Escribe el nombre del cliente que buscas:\n\n"
                "_Ejemplo: escribe 'granjas' para buscar_",
                parse_mode="Markdown"
            )
            # Crear sesión para esperar búsqueda
            self.user_sessions[user_id] = {
                'esperando_cliente': True,
                'productos_parseados': [],
                'productos_confirmados': [],
                'producto_actual_idx': 0,
                'timestamp': datetime.now()
            }
            return
        
        elif data == "inicio_ver_productos":
            await safe_answer()
            productos = self._obtener_productos_populares(15)
            
            if productos:
                texto = "📦 *PRODUCTOS DISPONIBLES*\n"
                texto += "━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                keyboard = []
                for cod, desc, stock, precio in productos:
                    if stock > 0:
                        keyboard.append([InlineKeyboardButton(
                            f"✅ {desc[:28]} (${precio:.0f})",
                            callback_data=f"info_prod:{cod}"
                        )])
                
                keyboard.append([InlineKeyboardButton("🔍 Buscar otro", callback_data="inicio_buscar_producto")])
                keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="inicio_volver")])
                
                await query.message.edit_text(
                    texto + "_Toca un producto para ver detalles:_",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.message.edit_text("❌ No hay productos disponibles")
            return
        
        elif data == "inicio_buscar_producto":
            await safe_answer()
            await query.message.edit_text(
                "🔍 *Buscar Producto*\n\n"
                "Escribe el código o nombre:\n"
                "_Ejemplo: '812 negra' o 't25'_",
                parse_mode="Markdown"
            )
            self.user_sessions[user_id] = {
                'esperando_busqueda_prod': -1,  # -1 indica búsqueda general
                'productos_parseados': [],
                'productos_confirmados': [],
                'producto_actual_idx': 0,
                'timestamp': datetime.now()
            }
            return
        
        elif data.startswith("info_prod:"):
            codigo = data[10:]
            await safe_answer()
            productos = self._buscar_productos_similares(codigo, 1)
            if productos:
                cod, desc, stock, precio = productos[0]
                texto = f"📦 *{desc}*\n\n"
                texto += f"📋 Código: `{cod}`\n"
                texto += f"📊 Stock: {stock} unidades\n"
                texto += f"💰 Precio: ${precio:.2f}\n"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Ver más productos", callback_data="inicio_ver_productos")]
                ]
                await query.message.edit_text(
                    texto,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return
        
        elif data == "inicio_ayuda":
            await safe_answer()
            await self._cmd_ayuda(update.callback_query, context)
            return
        
        elif data == "inicio_volver":
            await safe_answer()
            # Volver a mensaje de inicio
            keyboard = [
                [InlineKeyboardButton("🔍 Buscar Cliente", callback_data="inicio_buscar_cliente"),
                 InlineKeyboardButton("📦 Ver Productos", callback_data="inicio_ver_productos")],
                [InlineKeyboardButton("❓ Ayuda", callback_data="inicio_ayuda")]
            ]
            await query.message.edit_text(
                "📝 *¿Qué deseas hacer?*\n\n"
                "Selecciona una opción o envía un pedido directamente.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # ═══════════════════════════════════════════════════════════════
        # FLUJO DE CONFIRMACIÓN DE PEDIDO NUEVO
        # ═══════════════════════════════════════════════════════════════
        
        if data.startswith("confirmar_cli:"):
            # Confirmar cliente de la BD
            cliente = data[14:]
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['cliente_confirmado'] = cliente
            await safe_answer(f"✅ {cliente[:20]}")
            # Proceder a confirmar productos
            await self._confirmar_productos(update, user_id)
        
        elif data.startswith("usar_cliente:"):
            # Usar cliente tal como se escribió
            cliente = data[13:]
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['cliente_confirmado'] = cliente
            await safe_answer(f"✅ {cliente}")
            await self._confirmar_productos(update, user_id)
        
        elif data == "buscar_cliente":
            # Pedir que busque cliente
            await safe_answer()
            await query.message.edit_text(
                "🔍 *Buscar cliente*\n\n"
                "Escribe el nombre del cliente para buscarlo:",
                parse_mode="Markdown"
            )
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['esperando_cliente'] = True
        
        elif data.startswith("confirmar_prod:"):
            # Confirmar producto de la BD
            # Formato: confirmar_prod:idx:codigo:descripcion
            partes = data.split(":", 3)
            if len(partes) >= 4:
                idx = int(partes[1])
                codigo = partes[2]
                descripcion = partes[3]
                
                if user_id in self.user_sessions:
                    session = self.user_sessions[user_id]
                    if idx < len(session['productos_parseados']):
                        cantidad = session['productos_parseados'][idx]['cantidad']
                        unidad = session['productos_parseados'][idx].get('unidad', 'pza')
                        
                        session['productos_confirmados'].append({
                            'codigo': codigo,
                            'descripcion': descripcion,
                            'cantidad': cantidad,
                            'unidad': unidad
                        })
                        session['producto_actual_idx'] = idx + 1
                        
                await safe_answer(f"✅ {descripcion[:20]}")
                await self._confirmar_productos(update, user_id)
        
        elif data.startswith("buscar_prod:"):
            # Buscar otro producto
            idx = int(data.split(":")[1])
            await safe_answer()
            await query.message.edit_text(
                f"🔍 *Buscar producto {idx + 1}*\n\n"
                "Escribe el código o nombre del producto:",
                parse_mode="Markdown"
            )
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['esperando_busqueda_prod'] = idx
        
        elif data.startswith("omitir_prod:"):
            # Omitir producto
            idx = int(data.split(":")[1])
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['producto_actual_idx'] = idx + 1
            await safe_answer("⏭️ Omitido")
            await self._confirmar_productos(update, user_id)
        
        elif data.startswith("cambiar_cant:"):
            # Cambiar cantidad
            idx = int(data.split(":")[1])
            await safe_answer()
            if user_id in self.user_sessions:
                session = self.user_sessions[user_id]
                producto = session['productos_parseados'][idx]
                keyboard = [
                    [InlineKeyboardButton("1", callback_data=f"setcant:{idx}:1"),
                     InlineKeyboardButton("5", callback_data=f"setcant:{idx}:5"),
                     InlineKeyboardButton("10", callback_data=f"setcant:{idx}:10")],
                    [InlineKeyboardButton("20", callback_data=f"setcant:{idx}:20"),
                     InlineKeyboardButton("50", callback_data=f"setcant:{idx}:50"),
                     InlineKeyboardButton("100", callback_data=f"setcant:{idx}:100")],
                    [InlineKeyboardButton("⬅️ Volver", callback_data=f"volver_prod:{idx}")]
                ]
                await query.message.edit_text(
                    f"🔢 *Cambiar cantidad para:*\n`{producto['nombre']}`\n\n"
                    f"Cantidad actual: {producto['cantidad']}\n"
                    "Selecciona nueva cantidad:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        elif data.startswith("setcant:"):
            # Establecer cantidad
            partes = data.split(":")
            idx = int(partes[1])
            cantidad = int(partes[2])
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['productos_parseados'][idx]['cantidad'] = cantidad
            await safe_answer(f"✅ Cantidad: {cantidad}")
            await self._confirmar_productos(update, user_id)
        
        elif data.startswith("volver_prod:"):
            idx = int(data.split(":")[1])
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['producto_actual_idx'] = idx
            await safe_answer()
            await self._confirmar_productos(update, user_id)
        
        elif data == "crear_pedido_final":
            # Crear pedido final
            if user_id not in self.user_sessions:
                await safe_answer("⚠️ Sin sesión activa")
                return
            
            session = self.user_sessions[user_id]
            cliente = session.get('cliente_confirmado', session.get('cliente_texto', ''))
            productos = session.get('productos_confirmados', [])
            
            if not productos:
                await safe_answer("⚠️ Sin productos confirmados")
                return
            
            await safe_answer("✅ Creando pedido...")
            
            # Formatear productos
            productos_str = ", ".join([f"{p['cantidad']}x {p['descripcion']}" for p in productos])
            
            # Guardar en base de datos
            if HAS_DB:
                from datetime import date
                orden_id = db_local.crear_orden_telegram(
                    fecha=date.today().isoformat(),
                    telegram_user_id=user_id,
                    telegram_username=query.from_user.username or '',
                    telegram_nombre=query.from_user.full_name or query.from_user.first_name,
                    mensaje_original=session.get('mensaje_original', ''),
                    cliente=cliente,
                    productos=productos_str
                )
                
                if orden_id > 0:
                    respuesta = f"✅ *Pedido #{orden_id} Creado*\n\n"
                    respuesta += f"👤 *Cliente:* {cliente}\n\n"
                    respuesta += f"📦 *Productos:*\n"
                    for p in productos:
                        respuesta += f"  • {p['cantidad']}x {p['descripcion']}\n"
                        if p.get('codigo'):
                            respuesta += f"    _{p['codigo']}_\n"
                    respuesta += "\n✅ _Pedido registrado correctamente_"
                    
                    await query.message.edit_text(respuesta, parse_mode="Markdown")
                    self.parent.after(0, self._cargar_ordenes)
                else:
                    await query.message.edit_text("❌ Error al guardar el pedido")
            
            # Limpiar sesión
            del self.user_sessions[user_id]
        
        elif data == "agregar_mas_productos":
            # Esperar más productos
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['esperando_productos'] = True
            await safe_answer()
            await query.message.edit_text(
                "➕ *Agregar más productos*\n\n"
                "Escribe los productos adicionales:\n"
                "`10 t25 negra`\n"
                "`5 1216 opaca`",
                parse_mode="Markdown"
            )
        
        elif data == "reiniciar_pedido":
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            await safe_answer("🔄 Reiniciado")
            await query.message.edit_text(
                "🔄 *Pedido reiniciado*\n\n"
                "Envía un nuevo mensaje con tu pedido.",
                parse_mode="Markdown"
            )
        
        # ═══════════════════════════════════════════════════════════════
        # FLUJO ANTIGUO (compatibilidad con /c y /b)
        # ═══════════════════════════════════════════════════════════════
        
        elif data.startswith("cli:"):
            # Selección de cliente desde búsqueda /c
            cliente = data[4:]
            # Crear nueva sesión para este cliente
            self.user_sessions[user_id] = {
                'cliente_confirmado': cliente,
                'cliente_texto': cliente,
                'productos_parseados': [],
                'productos_confirmados': [],
                'producto_actual_idx': 0,
                'timestamp': datetime.now(),
                'esperando_productos': True
            }
            await safe_answer(f"✅ {cliente}")
            
            await query.message.reply_text(
                f"👤 *Cliente:* `{cliente}`\n\n"
                f"📦 Ahora envía los productos:\n"
                f"`10 t25 negra`\n"
                f"`5 1216 opaca`\n\n"
                f"O usa /b para buscar productos",
                parse_mode="Markdown"
            )
        
        elif data.startswith("prod:"):
            # Selección de producto desde búsqueda /b
            producto = data[5:]
            await safe_answer(f"✅ {producto}")
            
            if user_id in self.user_sessions:
                session = self.user_sessions[user_id]
                session['productos_confirmados'].append({
                    'codigo': '',
                    'descripcion': producto,
                    'cantidad': 1,
                    'unidad': 'pza'
                })
                
                resumen = f"👤 *Cliente:* {session.get('cliente_confirmado', 'No seleccionado')}\n\n"
                resumen += "📦 *Productos:*\n"
                for p in session['productos_confirmados']:
                    resumen += f"  • {p['cantidad']}x {p['descripcion']}\n"
                
                keyboard = [
                    [InlineKeyboardButton("🔍 Buscar más", callback_data="buscar_mas_productos")],
                    [InlineKeyboardButton("✅ Crear Pedido", callback_data="crear_pedido_final")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]
                ]
                
                await query.message.reply_text(
                    resumen,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.message.reply_text(
                    f"📦 `{producto}`\n\n"
                    "Primero selecciona un cliente con /c",
                    parse_mode="Markdown"
                )
        
        elif data == "buscar_mas_productos":
            await safe_answer()
            await query.message.reply_text(
                "🔍 Usa `/b [producto]` para buscar",
                parse_mode="Markdown"
            )
        
        elif data == "cancelar":
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            await safe_answer("❌ Cancelado")
            await query.message.edit_text(
                "❌ *Pedido cancelado*",
                parse_mode="Markdown"
            )
        
        else:
            await safe_answer()
    
    async def _cmd_stock(self, update, context):
        """Comando /stock - Consulta inventario."""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Indica el producto a consultar.\n"
                "Ejemplo: `/stock leche`",
                parse_mode="Markdown"
            )
            return
        
        producto = ' '.join(context.args)
        productos = self._buscar_productos_similares(producto, 10)
        
        if productos:
            respuesta = f"📦 *Stock de '{producto}':*\n\n"
            for codigo, desc, inv, precio in productos:
                emoji = "✅" if inv > 0 else "❌"
                respuesta += f"{emoji} {desc}\n   Código: {codigo} | Stock: {inv} | ${precio:.2f}\n\n"
            await update.message.reply_text(respuesta, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ No se encontró '{producto}'")
    
    async def _cmd_cliente(self, update, context):
        """Comando /cliente - Busca un cliente."""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Indica el nombre a buscar.\n"
                "Ejemplo: `/cliente juan`",
                parse_mode="Markdown"
            )
            return
        
        nombre = ' '.join(context.args)
        clientes = self._buscar_clientes_similares(nombre, 10)
        
        if clientes:
            respuesta = f"👥 *Clientes encontrados:*\n\n_Toca uno para seleccionarlo:_\n"
            keyboard = []
            for i, cli in enumerate(clientes, 1):
                respuesta += f"{i}. {cli}\n"
                # Crear botón para cada cliente
                keyboard.append([InlineKeyboardButton(f"👤 {cli[:35]}", callback_data=f"cli:{cli[:60]}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(respuesta, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"❌ No se encontró cliente '{nombre}'")
    
    async def _cmd_productos(self, update, context):
        """Comando /productos - Lista productos con stock."""
        productos = self._obtener_productos_populares(20)
        
        if productos:
            respuesta = "📦 *Productos con stock:*\n\n"
            for cod, desc, inv, precio in productos:
                respuesta += f"• {desc[:25]} ({inv}) - ${precio:.2f}\n"
            respuesta += "\n_Usa /stock [producto] para más detalles_"
            await update.message.reply_text(respuesta, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ No hay productos con stock")
    
    # ══════════════════════════════════════════════════════════════════
    # INLINE QUERIES - AUTOSUGERENCIAS
    # ══════════════════════════════════════════════════════════════════
    
    async def _inline_query_handler(self, update, context):
        """
        Maneja inline queries para autosugerencias.
        Uso: @BotName cliente:juan o @BotName producto:bolsa o @BotName texto
        """
        query = update.inline_query.query
        if not query or len(query) < 2:
            return
        
        results = []
        unique_id = 0
        
        # Determinar tipo de búsqueda
        search_type = "ambos"
        search_term = query
        
        if query.lower().startswith("cliente:") or query.lower().startswith("c:"):
            search_type = "cliente"
            search_term = query.split(":", 1)[1].strip()
        elif query.lower().startswith("producto:") or query.lower().startswith("p:"):
            search_type = "producto"
            search_term = query.split(":", 1)[1].strip()
        
        if not search_term or len(search_term) < 2:
            return
        
        # Buscar clientes
        if search_type in ["cliente", "ambos"]:
            clientes = self._buscar_clientes_similares(search_term, 5)
            for cliente in clientes:
                unique_id += 1
                results.append(
                    InlineQueryResultArticle(
                        id=f"cli_{unique_id}",
                        title=f"👤 {cliente}",
                        description="Cliente - Toca para usar este nombre",
                        input_message_content=InputTextMessageContent(
                            message_text=f"Cliente: {cliente}"
                        ),
                        thumbnail_url="https://img.icons8.com/color/48/000000/user.png"
                    )
                )
        
        # Buscar productos
        if search_type in ["producto", "ambos"]:
            productos = self._buscar_productos_similares(search_term, 8)
            for codigo, descripcion, stock, precio in productos:
                unique_id += 1
                emoji_stock = "✅" if stock > 0 else "❌"
                results.append(
                    InlineQueryResultArticle(
                        id=f"prod_{unique_id}",
                        title=f"📦 {descripcion}",
                        description=f"{emoji_stock} Stock: {stock} | ${precio:.2f}",
                        input_message_content=InputTextMessageContent(
                            message_text=f"{descripcion}"
                        ),
                        thumbnail_url="https://img.icons8.com/color/48/000000/box.png"
                    )
                )
        
        # Si no hay resultados, mostrar sugerencia
        if not results:
            results.append(
                InlineQueryResultArticle(
                    id="no_results",
                    title="🔍 Sin resultados",
                    description=f"No se encontró '{search_term}'. Intenta otro término.",
                    input_message_content=InputTextMessageContent(
                        message_text=f"Buscar: {search_term}"
                    )
                )
            )
        
        # Limitar a 50 resultados (límite de Telegram)
        results = results[:50]
        
        try:
            await update.inline_query.answer(results, cache_time=10)
        except Exception as e:
            print(f"Error respondiendo inline query: {e}")
    
    def refrescar(self, *args):
        """Refresca los datos cuando cambia la fecha global."""
        self._cargar_ordenes()


class DialogoCrearVenta(tk.Toplevel):
    """Diálogo para crear una venta en Firebird desde una orden de Telegram."""
    
    def __init__(self, parent, app, orden_id: int, cliente: str, mensaje_original: str, 
                 on_venta_creada=None):
        super().__init__(parent)
        self.app = app
        self.orden_id = orden_id
        self.cliente_inicial = cliente
        self.mensaje_original = mensaje_original
        self.on_venta_creada = on_venta_creada
        
        self.title(f"🛒 Crear Venta - Orden #{orden_id}")
        self.geometry("900x650")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        
        # Lista de productos a vender
        self.productos_venta = []
        
        self._crear_interfaz()
        self._cargar_datos_iniciales()
        
        # Centrar ventana
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _crear_interfaz(self):
        """Crea la interfaz del diálogo."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # ═══════════════════════════════════════════════════════════════
        # SECCIÓN 1: DATOS DEL CLIENTE
        # ═══════════════════════════════════════════════════════════════
        cliente_frame = ttk.LabelFrame(main_frame, text="👤 Datos del Cliente", padding=10)
        cliente_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        cliente_frame.columnconfigure(1, weight=1)
        
        ttk.Label(cliente_frame, text="Cliente:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.cliente_var = tk.StringVar(master=self, value=self.cliente_inicial)
        self.entry_cliente = ttk.Entry(cliente_frame, textvariable=self.cliente_var, width=40)
        self.entry_cliente.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Botón buscar cliente
        ttk.Button(cliente_frame, text="🔍 Buscar", 
                   command=self._buscar_cliente).grid(row=0, column=2, padx=5)
        
        # Lista de clientes sugeridos
        self.lista_clientes = tk.Listbox(cliente_frame, height=3, exportselection=False)
        self.lista_clientes.grid(row=1, column=1, sticky="ew", padx=5, pady=(5, 0))
        self.lista_clientes.bind('<<ListboxSelect>>', self._seleccionar_cliente)
        self.lista_clientes.grid_remove()  # Ocultar inicialmente
        
        # Forma de pago
        ttk.Label(cliente_frame, text="Forma de Pago:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        self.forma_pago_var = tk.StringVar(master=self, value="EFECTIVO")
        combo_pago = ttk.Combobox(cliente_frame, textvariable=self.forma_pago_var, 
                                   values=["EFECTIVO", "CREDITO", "TARJETA", "TRANSFERENCIA"],
                                   state="readonly", width=15)
        combo_pago.grid(row=2, column=1, sticky="w", padx=5, pady=(10, 0))
        
        # ═══════════════════════════════════════════════════════════════
        # SECCIÓN 2: MENSAJE ORIGINAL
        # ═══════════════════════════════════════════════════════════════
        msg_frame = ttk.LabelFrame(main_frame, text="📱 Mensaje Original (Telegram)", padding=10)
        msg_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10), padx=(0, 5))
        msg_frame.columnconfigure(0, weight=1)
        msg_frame.rowconfigure(0, weight=1)
        
        self.txt_mensaje = tk.Text(msg_frame, height=6, wrap=tk.WORD, font=("Segoe UI", 9))
        self.txt_mensaje.pack(fill=tk.BOTH, expand=True)
        self.txt_mensaje.insert("1.0", self.mensaje_original)
        self.txt_mensaje.config(state=tk.DISABLED)
        
        # ═══════════════════════════════════════════════════════════════
        # SECCIÓN 3: BUSCAR PRODUCTOS
        # ═══════════════════════════════════════════════════════════════
        buscar_frame = ttk.LabelFrame(main_frame, text="🔍 Buscar Productos en Catálogo", padding=10)
        buscar_frame.grid(row=1, column=1, sticky="nsew", pady=(0, 10), padx=(5, 0))
        buscar_frame.columnconfigure(0, weight=1)
        buscar_frame.rowconfigure(1, weight=1)
        
        # Entrada de búsqueda
        search_row = ttk.Frame(buscar_frame)
        search_row.pack(fill=tk.X, pady=(0, 5))
        
        self.buscar_prod_var = tk.StringVar(master=self)
        entry_buscar = ttk.Entry(search_row, textvariable=self.buscar_prod_var)
        entry_buscar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        entry_buscar.bind('<Return>', lambda e: self._buscar_productos())
        
        ttk.Button(search_row, text="Buscar", command=self._buscar_productos).pack(side=tk.LEFT)
        
        # Tabla de productos encontrados
        cols_busq = ("codigo", "descripcion", "stock", "precio")
        self.tree_busqueda = ttk.Treeview(buscar_frame, columns=cols_busq, show="headings", height=5)
        self.tree_busqueda.heading("codigo", text="Código")
        self.tree_busqueda.heading("descripcion", text="Descripción")
        self.tree_busqueda.heading("stock", text="Stock")
        self.tree_busqueda.heading("precio", text="Precio")
        self.tree_busqueda.column("codigo", width=70)
        self.tree_busqueda.column("descripcion", width=150)
        self.tree_busqueda.column("stock", width=50, anchor="center")
        self.tree_busqueda.column("precio", width=70, anchor="e")
        self.tree_busqueda.pack(fill=tk.BOTH, expand=True)
        self.tree_busqueda.bind('<Double-1>', self._agregar_producto_dobleclick)
        
        # Botón agregar
        ttk.Button(buscar_frame, text="➕ Agregar Seleccionado", 
                   command=self._agregar_producto).pack(pady=(5, 0))
        
        # ═══════════════════════════════════════════════════════════════
        # SECCIÓN 4: PRODUCTOS DE LA VENTA
        # ═══════════════════════════════════════════════════════════════
        venta_frame = ttk.LabelFrame(main_frame, text="🛒 Productos de la Venta", padding=10)
        venta_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        venta_frame.columnconfigure(0, weight=1)
        venta_frame.rowconfigure(0, weight=1)
        
        # Tabla de productos a vender
        cols_venta = ("codigo", "descripcion", "cantidad", "precio_unit", "subtotal")
        self.tree_venta = ttk.Treeview(venta_frame, columns=cols_venta, show="headings", height=8)
        self.tree_venta.heading("codigo", text="Código")
        self.tree_venta.heading("descripcion", text="Descripción")
        self.tree_venta.heading("cantidad", text="Cant.")
        self.tree_venta.heading("precio_unit", text="P. Unit.")
        self.tree_venta.heading("subtotal", text="Subtotal")
        self.tree_venta.column("codigo", width=80)
        self.tree_venta.column("descripcion", width=250)
        self.tree_venta.column("cantidad", width=60, anchor="center")
        self.tree_venta.column("precio_unit", width=80, anchor="e")
        self.tree_venta.column("subtotal", width=90, anchor="e")
        
        scroll_venta = ttk.Scrollbar(venta_frame, orient=tk.VERTICAL, command=self.tree_venta.yview)
        self.tree_venta.configure(yscrollcommand=scroll_venta.set)
        
        self.tree_venta.grid(row=0, column=0, sticky="nsew")
        scroll_venta.grid(row=0, column=1, sticky="ns")
        
        # Botones para editar productos
        btn_productos = ttk.Frame(venta_frame)
        btn_productos.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        ttk.Button(btn_productos, text="✏️ Editar Cantidad", 
                   command=self._editar_cantidad).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_productos, text="🗑️ Quitar", 
                   command=self._quitar_producto).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_productos, text="🧹 Limpiar Todo", 
                   command=self._limpiar_productos).pack(side=tk.LEFT, padx=2)
        
        # Total
        total_frame = ttk.Frame(btn_productos)
        total_frame.pack(side=tk.RIGHT)
        ttk.Label(total_frame, text="TOTAL:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=5)
        self.lbl_total = ttk.Label(total_frame, text="$0.00", font=("Segoe UI", 14, "bold"), 
                                    foreground="#2e7d32")
        self.lbl_total.pack(side=tk.LEFT)
        
        # ═══════════════════════════════════════════════════════════════
        # BOTONES FINALES
        # ═══════════════════════════════════════════════════════════════
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        
        ttk.Button(btn_frame, text="❌ Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="✅ Crear Venta en Eleventa", 
                   command=self._crear_venta, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
    
    def _cargar_datos_iniciales(self):
        """Carga sugerencias de clientes si hay texto inicial."""
        if self.cliente_inicial:
            self._buscar_cliente()
    
    def _buscar_cliente(self):
        """Busca clientes similares en Firebird."""
        texto = self.cliente_var.get().strip()
        if not texto or len(texto) < 2:
            self.lista_clientes.grid_remove()
            return
        
        try:
            if hasattr(self.app, '_ejecutar_sql'):
                sql = f"""
                    SET HEADING ON;
                    SELECT FIRST 5 DISTINCT NOMBRE 
                    FROM VENTATICKETS 
                    WHERE UPPER(NOMBRE) LIKE UPPER('%{texto}%')
                    AND NOMBRE IS NOT NULL
                    ORDER BY NOMBRE;
                """
                ok, stdout, stderr = self.app._ejecutar_sql(sql)
                
                if ok and stdout:
                    self.lista_clientes.delete(0, tk.END)
                    for linea in stdout.split('\n'):
                        linea = linea.strip()
                        if linea and not linea.startswith('=') and 'NOMBRE' not in linea:
                            if linea and linea != '<null>':
                                self.lista_clientes.insert(tk.END, linea)
                    
                    if self.lista_clientes.size() > 0:
                        self.lista_clientes.grid()
                    else:
                        self.lista_clientes.grid_remove()
        except Exception as e:
            print(f"Error buscando clientes: {e}")
    
    def _seleccionar_cliente(self, event):
        """Selecciona un cliente de la lista."""
        selection = self.lista_clientes.curselection()
        if selection:
            cliente = self.lista_clientes.get(selection[0])
            self.cliente_var.set(cliente)
            self.lista_clientes.grid_remove()
    
    def _buscar_productos(self):
        """Busca productos en el catálogo de Firebird."""
        texto = self.buscar_prod_var.get().strip()
        if not texto or len(texto) < 2:
            return
        
        # Limpiar resultados anteriores
        for item in self.tree_busqueda.get_children():
            self.tree_busqueda.delete(item)
        
        try:
            if hasattr(self.app, '_ejecutar_sql'):
                sql = f"""
                    SET HEADING ON;
                    SELECT FIRST 15 CODIGO, DESCRIPCION, DINVENTARIO, PVENTA 
                    FROM PRODUCTOS 
                    WHERE UPPER(DESCRIPCION) LIKE UPPER('%{texto}%')
                    OR UPPER(CODIGO) LIKE UPPER('%{texto}%')
                    ORDER BY DESCRIPCION;
                """
                ok, stdout, stderr = self.app._ejecutar_sql(sql)
                
                if ok and stdout:
                    header_visto = False
                    for linea in stdout.split('\n'):
                        linea = linea.strip()
                        if not linea or linea.startswith('='):
                            continue
                        if 'CODIGO' in linea and 'DESCRIPCION' in linea:
                            header_visto = True
                            continue
                        if not header_visto:
                            continue
                        
                        # Parsear línea
                        partes = linea.split()
                        if len(partes) >= 4:
                            codigo = partes[0]
                            precio = partes[-1]
                            stock = partes[-2]
                            descripcion = ' '.join(partes[1:-2])
                            
                            try:
                                precio_float = float(precio)
                                stock_int = int(float(stock)) if stock != '<null>' else 0
                                self.tree_busqueda.insert("", tk.END, values=(
                                    codigo, descripcion, stock_int, f"${precio_float:,.2f}"
                                ))
                            except:
                                pass
        except Exception as e:
            print(f"Error buscando productos: {e}")
    
    def _agregar_producto_dobleclick(self, event):
        """Agrega producto con doble click."""
        self._agregar_producto()
    
    def _agregar_producto(self):
        """Agrega el producto seleccionado a la venta."""
        selection = self.tree_busqueda.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona un producto primero")
            return
        
        item = self.tree_busqueda.item(selection[0])
        valores = item['values']
        codigo = valores[0]
        descripcion = valores[1]
        stock = valores[2]
        precio_str = valores[3].replace('$', '').replace(',', '')
        
        try:
            precio = float(precio_str)
        except:
            precio = 0
        
        # Pedir cantidad
        cantidad = simpledialog.askinteger("Cantidad", 
                                            f"Cantidad de '{descripcion}':",
                                            initialvalue=1, minvalue=1, parent=self)
        if not cantidad:
            return
        
        # Verificar stock
        if cantidad > stock:
            if not messagebox.askyesno("Stock Insuficiente", 
                                        f"Solo hay {stock} en stock.\n"
                                        f"¿Agregar {cantidad} de todos modos?"):
                return
        
        # Agregar a la lista de productos
        subtotal = cantidad * precio
        self.productos_venta.append({
            'codigo': codigo,
            'descripcion': descripcion,
            'cantidad': cantidad,
            'precio': precio,
            'subtotal': subtotal
        })
        
        self.tree_venta.insert("", tk.END, values=(
            codigo, descripcion, cantidad, f"${precio:,.2f}", f"${subtotal:,.2f}"
        ))
        
        self._actualizar_total()
    
    def _editar_cantidad(self):
        """Edita la cantidad de un producto."""
        selection = self.tree_venta.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona un producto primero")
            return
        
        idx = self.tree_venta.index(selection[0])
        producto = self.productos_venta[idx]
        
        nueva_cantidad = simpledialog.askinteger("Editar Cantidad", 
                                                  f"Nueva cantidad de '{producto['descripcion']}':",
                                                  initialvalue=producto['cantidad'], 
                                                  minvalue=1, parent=self)
        if nueva_cantidad:
            producto['cantidad'] = nueva_cantidad
            producto['subtotal'] = nueva_cantidad * producto['precio']
            
            self.tree_venta.item(selection[0], values=(
                producto['codigo'], producto['descripcion'], nueva_cantidad,
                f"${producto['precio']:,.2f}", f"${producto['subtotal']:,.2f}"
            ))
            self._actualizar_total()
    
    def _quitar_producto(self):
        """Quita el producto seleccionado."""
        selection = self.tree_venta.selection()
        if not selection:
            return
        
        idx = self.tree_venta.index(selection[0])
        del self.productos_venta[idx]
        self.tree_venta.delete(selection[0])
        self._actualizar_total()
    
    def _limpiar_productos(self):
        """Limpia todos los productos."""
        if self.productos_venta and messagebox.askyesno("Confirmar", "¿Limpiar todos los productos?"):
            self.productos_venta.clear()
            for item in self.tree_venta.get_children():
                self.tree_venta.delete(item)
            self._actualizar_total()
    
    def _actualizar_total(self):
        """Actualiza el total de la venta."""
        total = sum(p['subtotal'] for p in self.productos_venta)
        self.lbl_total.config(text=f"${total:,.2f}")
    
    def _crear_venta(self):
        """Crea la venta en Firebird."""
        # Validaciones
        cliente = self.cliente_var.get().strip()
        if not cliente:
            messagebox.showwarning("Cliente", "Ingresa el nombre del cliente")
            return
        
        if not self.productos_venta:
            messagebox.showwarning("Productos", "Agrega al menos un producto")
            return
        
        forma_pago = self.forma_pago_var.get()
        es_credito = 1 if forma_pago == "CREDITO" else 0
        
        total = sum(p['subtotal'] for p in self.productos_venta)
        total_credito = total if es_credito else 0
        
        # Confirmar
        resumen = f"Cliente: {cliente}\n"
        resumen += f"Forma de Pago: {forma_pago}\n"
        resumen += f"Productos: {len(self.productos_venta)}\n"
        resumen += f"Total: ${total:,.2f}\n"
        if es_credito:
            resumen += f"\n⚠️ VENTA A CRÉDITO"
        
        if not messagebox.askyesno("Confirmar Venta", f"¿Crear esta venta?\n\n{resumen}"):
            return
        
        # Ejecutar INSERT en Firebird
        try:
            folio = self._insertar_venta_firebird(cliente, forma_pago, es_credito, total, total_credito)
            
            if folio:
                # Callback para actualizar la orden
                if self.on_venta_creada:
                    self.on_venta_creada(self.orden_id, folio)
                self.destroy()
            else:
                messagebox.showerror("Error", "No se pudo crear la venta")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear la venta:\n{e}")
    
    def _insertar_venta_firebird(self, cliente: str, forma_pago: str, es_credito: int, 
                                   total: float, total_credito: float) -> Optional[int]:
        """Inserta la venta en las tablas de Firebird."""
        
        if not hasattr(self.app, '_ejecutar_sql'):
            raise Exception("No se puede acceder a la base de datos Firebird")
        
        # 1. Obtener el siguiente FOLIO disponible
        sql_folio = """
            SET HEADING ON;
            SELECT MAX(FOLIO) FROM VENTATICKETS;
        """
        ok, stdout, stderr = self.app._ejecutar_sql(sql_folio)
        
        if not ok:
            raise Exception(f"Error obteniendo folio: {stderr}")
        
        # Parsear el folio máximo
        max_folio = 0
        for linea in stdout.split('\n'):
            linea = linea.strip()
            if linea and linea.isdigit():
                max_folio = int(linea)
                break
            elif linea and linea != '<null>' and 'MAX' not in linea and '=' not in linea:
                try:
                    max_folio = int(linea)
                    break
                except:
                    pass
        
        nuevo_folio = max_folio + 1
        
        # 2. Obtener el siguiente ID disponible
        sql_id = """
            SET HEADING ON;
            SELECT MAX(ID) FROM VENTATICKETS;
        """
        ok, stdout, stderr = self.app._ejecutar_sql(sql_id)
        
        max_id = 0
        for linea in stdout.split('\n'):
            linea = linea.strip()
            if linea and linea.isdigit():
                max_id = int(linea)
                break
            elif linea and linea != '<null>' and 'MAX' not in linea and '=' not in linea:
                try:
                    max_id = int(linea)
                    break
                except:
                    pass
        
        nuevo_id = max_id + 1
        
        # 3. Obtener TURNO_ID activo (el último abierto)
        sql_turno = """
            SET HEADING ON;
            SELECT FIRST 1 ID FROM TURNOS ORDER BY ID DESC;
        """
        ok, stdout, stderr = self.app._ejecutar_sql(sql_turno)
        
        turno_id = 1  # Por defecto
        for linea in stdout.split('\n'):
            linea = linea.strip()
            if linea and linea.isdigit():
                turno_id = int(linea)
                break
        
        # 4. Calcular subtotal (sin IVA - asumiendo 16% de IVA)
        subtotal = total / 1.16  # Ajustar según configuración de IVA
        iva = total - subtotal
        
        # 5. Insertar en VENTATICKETS
        # Escapar comillas simples en el nombre del cliente
        cliente_escapado = cliente.replace("'", "''")
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        sql_insert = f"""
            INSERT INTO VENTATICKETS (
                ID, FOLIO, NOMBRE, SUBTOTAL, TOTAL, 
                TOTAL_CREDITO, ESTA_CANCELADO, CREADO_EN, TURNO_ID
            ) VALUES (
                {nuevo_id}, {nuevo_folio}, '{cliente_escapado}', 
                {subtotal:.2f}, {total:.2f}, 
                {total_credito:.2f}, 0, '{fecha_actual}', {turno_id}
            );
            COMMIT;
        """
        
        ok, stdout, stderr = self.app._ejecutar_sql(sql_insert)
        
        if not ok:
            raise Exception(f"Error insertando ticket: {stderr}")
        
        # 6. Insertar artículos en VENTATICKETS_ARTICULOS
        for producto in self.productos_venta:
            codigo_escapado = str(producto['codigo']).replace("'", "''")
            desc_escapada = producto['descripcion'].replace("'", "''")
            
            # Obtener ID de artículo
            sql_art_id = f"""
                SET HEADING ON;
                SELECT MAX(ID) FROM VENTATICKETS_ARTICULOS;
            """
            ok, stdout, stderr = self.app._ejecutar_sql(sql_art_id)
            
            max_art_id = 0
            for linea in stdout.split('\n'):
                linea = linea.strip()
                if linea and linea.isdigit():
                    max_art_id = int(linea)
                    break
            
            nuevo_art_id = max_art_id + 1
            
            sql_articulo = f"""
                INSERT INTO VENTATICKETS_ARTICULOS (
                    ID, TICKET_ID, PRODUCTO_CODIGO, PRODUCTO_NOMBRE, 
                    CANTIDAD, PRECIO_FINAL
                ) VALUES (
                    {nuevo_art_id}, {nuevo_id}, '{codigo_escapado}', 
                    '{desc_escapada}', {producto['cantidad']}, {producto['precio']:.2f}
                );
                COMMIT;
            """
            
            ok, stdout, stderr = self.app._ejecutar_sql(sql_articulo)
            
            if not ok:
                print(f"⚠️ Error insertando artículo {codigo_escapado}: {stderr}")
        
        return nuevo_folio
