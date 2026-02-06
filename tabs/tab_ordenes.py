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
    # FUNCIONES DE CONSULTA A BASE DE DATOS FIREBIRD
    # ══════════════════════════════════════════════════════════════════
    
    def _buscar_clientes_similares(self, texto: str, limite: int = 5) -> List[str]:
        """Busca clientes similares en la base de datos Firebird."""
        clientes = []
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
        
        resultado['cliente'] = cliente
        resultado['productos_texto'] = productos_texto
        resultado['productos'] = self._parsear_lineas_productos(productos_texto)
        
        if cliente:
            clientes_similares = self._buscar_clientes_similares(cliente, 3)
            if clientes_similares:
                resultado['cliente_sugerido'] = clientes_similares[0]
        
        return resultado
    
    def _parsear_lineas_productos(self, texto: str) -> List[Dict]:
        """Parsea líneas de productos con cantidades."""
        productos = []
        lineas = re.split(r'[,\n]', texto)
        
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            
            producto = {'nombre': linea, 'cantidad': 1, 'original': linea}
            
            patrones = [
                r'^(\d+)\s+(.+)$',
                r'^(.+?)\s*[xX]\s*(\d+)$',
                r'^(.+?)\s*\((\d+)\)$',
                r'^(.+?)\s+(\d+)\s*[uU]?$',
            ]
            
            for patron in patrones:
                match = re.match(patron, linea)
                if match:
                    grupos = match.groups()
                    if patron == patrones[0]:
                        producto['cantidad'] = int(grupos[0])
                        producto['nombre'] = grupos[1].strip()
                    else:
                        producto['nombre'] = grupos[0].strip()
                        producto['cantidad'] = int(grupos[1])
                    break
            
            if producto['nombre']:
                productos.append(producto)
        
        return productos
    
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
            
            self.parent.after(0, lambda: self.status_var.set("🟢 Bot activo"))
            
            self.loop.run_until_complete(self.bot_app.initialize())
            self.loop.run_until_complete(self.bot_app.start())
            self.loop.run_until_complete(self.bot_app.updater.start_polling())
            self.loop.run_forever()
            
        except Exception as e:
            error_msg = str(e)
            self.parent.after(0, lambda: self._on_bot_error(error_msg))
    
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
        """Comando /start - Saludo inicial."""
        productos_populares = self._obtener_productos_populares(5)
        productos_text = ""
        if productos_populares:
            productos_text = "\n\n📦 *Productos disponibles:*\n"
            for cod, desc, stock, precio in productos_populares:
                productos_text += f"• {desc[:30]} (Stock: {stock})\n"
        
        await update.message.reply_text(
            "🛒 *¡Bienvenido al Bot de Órdenes PlastiBot!*\n\n"
            "📝 *Para hacer un pedido:*\n"
            "Envía: `Cliente - productos`\n"
            "Ejemplo: `Juan Pérez - 10 bolsas, 5 rollos`\n\n"
            "🔍 *Comandos rápidos:*\n"
            "• /b [texto] - Buscar producto o cliente\n"
            "• /s [producto] - Ver stock\n"
            "• /c [nombre] - Buscar cliente\n"
            "• /productos - Ver catálogo\n"
            "• /ayuda - Ver todos los comandos"
            f"{productos_text}",
            parse_mode="Markdown"
        )
    
    async def _cmd_ayuda(self, update, context):
        """Comando /ayuda - Lista de comandos."""
        await update.message.reply_text(
            "📖 *Comandos disponibles:*\n\n"
            "*PEDIDOS:*\n"
            "• `/pedido` o `/p` - Crear pedido\n"
            "  Formato: `Cliente - producto1 x5, producto2 x3`\n\n"
            "*BÚSQUEDAS:*\n"
            "• `/buscar` o `/b` [texto] - Busca clientes Y productos\n"
            "• `/stock` o `/s` [producto] - Ver inventario\n"
            "• `/cliente` o `/c` [nombre] - Buscar cliente\n"
            "• `/productos` - Lista de productos\n\n"
            "💡 Envía cualquier mensaje para registrarlo como pedido.",
            parse_mode="Markdown"
        )
    
    async def _cmd_pedido(self, update, context):
        """Comando /pedido - Crea una orden."""
        texto = ' '.join(context.args) if context.args else ''
        await self._crear_orden(update, texto)
    
    async def _msg_pedido(self, update, context):
        """Maneja mensajes normales como pedidos."""
        texto = update.message.text
        await self._crear_orden(update, texto)
    
    async def _crear_orden(self, update, texto: str):
        """Crea una orden de venta con parseo inteligente."""
        if not texto.strip():
            await update.message.reply_text(
                "⚠️ Por favor incluye el pedido.\n\n"
                "*Formatos aceptados:*\n"
                "• `Juan - 10 bolsas, 5 rollos`\n"
                "• `Juan Pérez: producto x5`\n\n"
                "Usa /buscar para encontrar clientes o productos",
                parse_mode="Markdown"
            )
            return
        
        user = update.message.from_user
        fecha = datetime.now().strftime('%Y-%m-%d')
        
        parsed = self._parsear_pedido(texto)
        cliente = parsed['cliente']
        productos_texto = parsed['productos_texto']
        productos_lista = parsed['productos']
        
        resumen_productos = []
        for prod in productos_lista:
            if prod['cantidad'] > 1:
                resumen_productos.append(f"{prod['cantidad']}x {prod['nombre']}")
            else:
                resumen_productos.append(prod['nombre'])
        
        productos_str = ', '.join(resumen_productos) if resumen_productos else productos_texto
        
        if HAS_DB:
            orden_id = db_local.crear_orden_telegram(
                fecha=fecha,
                telegram_user_id=user.id,
                telegram_username=user.username or '',
                telegram_nombre=user.full_name or user.first_name,
                mensaje_original=texto,
                cliente=cliente,
                productos=productos_str
            )
            
            if orden_id > 0:
                respuesta = f"✅ *Orden #{orden_id} registrada*\n\n"
                respuesta += f"👤 *Cliente:* {cliente or 'No especificado'}\n"
                
                if productos_lista:
                    respuesta += f"📦 *Productos:*\n"
                    for prod in productos_lista:
                        qty = f" x{prod['cantidad']}" if prod['cantidad'] > 1 else ""
                        respuesta += f"  • {prod['nombre']}{qty}\n"
                else:
                    respuesta += f"📦 *Productos:* {productos_texto}\n"
                
                if parsed.get('cliente_sugerido') and parsed['cliente_sugerido'].upper() != cliente.upper():
                    respuesta += f"\n💡 ¿Quisiste decir cliente: *{parsed['cliente_sugerido']}*?"
                
                respuesta += "\n_La orden será procesada pronto._"
                
                await update.message.reply_text(respuesta, parse_mode="Markdown")
                self.parent.after(0, self._cargar_ordenes)
            else:
                await update.message.reply_text("❌ Error al guardar la orden")
    
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
        
        clientes = self._buscar_clientes_similares(termino, 5)
        if clientes:
            respuesta += "👥 *Clientes:*\n"
            for i, cli in enumerate(clientes, 1):
                respuesta += f"  {i}. {cli}\n"
            respuesta += "\n"
        
        productos = self._buscar_productos_similares(termino, 8)
        if productos:
            respuesta += "📦 *Productos:*\n"
            for cod, desc, stock, precio in productos:
                emoji = "✅" if stock > 0 else "❌"
                respuesta += f"  {emoji} {desc[:30]}\n     Stock: {stock} | ${precio:.2f}\n"
        
        if not clientes and not productos:
            respuesta = f"❌ No se encontraron resultados para '{termino}'"
        
        await update.message.reply_text(respuesta, parse_mode="Markdown")
    
    async def _callback_handler(self, update, context):
        """Maneja callbacks de botones inline."""
        query = update.callback_query
        await query.answer()
    
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
            respuesta = f"👥 *Clientes encontrados:*\n\n"
            for i, cli in enumerate(clientes, 1):
                respuesta += f"{i}. {cli}\n"
            await update.message.reply_text(respuesta, parse_mode="Markdown")
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
