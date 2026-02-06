#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mixin para la pestaña de Créditos Punteados.
Contiene toda la funcionalidad relacionada con la gestión de créditos.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os

# Importar base de datos local
try:
    import database_local as db_local
    USE_SQLITE = True
except ImportError:
    USE_SQLITE = False


class CreditosMixin:
    """Mixin que provee funcionalidades de la pestaña de Créditos."""
    
    def _crear_tab_creditos_punteados(self):
        """Crea la pestaña de créditos unificada (Punteados + Eleventa)."""
        tab = self.tab_creditos_punteados
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # ═══════════════════════════════════════════════════════════════
        # BARRA DE HERRAMIENTAS
        # ═══════════════════════════════════════════════════════════════
        toolbar = ttk.Frame(tab)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        ttk.Label(toolbar, text="📋 Gestión de Créditos", 
                  font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)
        
        # Filtro de Estado interno
        ttk.Label(toolbar, text="Estado:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(5, 2))
        self.filtro_estado_creditos_var = tk.StringVar(value="Todos")
        self.combo_filtro_estado_creditos = ttk.Combobox(
            toolbar, 
            textvariable=self.filtro_estado_creditos_var,
            values=["Todos", "PENDIENTE", "PAGADO", "CANCELADO"],
            width=12,
            state="readonly"
        )
        self.combo_filtro_estado_creditos.pack(side=tk.LEFT, padx=5)
        self.combo_filtro_estado_creditos.bind("<<ComboboxSelected>>", lambda e: self._refrescar_creditos_tab())
        
        # Filtro de Origen
        ttk.Label(toolbar, text="Origen:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.filtro_origen_creditos_var = tk.StringVar(value="Todos")
        self.combo_filtro_origen_creditos = ttk.Combobox(
            toolbar, 
            textvariable=self.filtro_origen_creditos_var,
            values=["Todos", "ELEVENTA", "PUNTEADO"],
            width=12,
            state="readonly"
        )
        self.combo_filtro_origen_creditos.pack(side=tk.LEFT, padx=5)
        self.combo_filtro_origen_creditos.bind("<<ComboboxSelected>>", lambda e: self._refrescar_creditos_tab())
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)
        
        # Botón para cargar TODOS los créditos de Firebird
        ttk.Button(toolbar, text="📥 Cargar Créditos Eleventa", 
                   command=self._cargar_todos_creditos_eleventa).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="🔄 Actualizar", 
                   command=self._refrescar_creditos_tab).pack(side=tk.LEFT, padx=5)
        
        # Botón para saldar créditos viejos
        ttk.Button(toolbar, text="🗑️ Saldar Anteriores 2026", 
                   command=self._saldar_creditos_anteriores).pack(side=tk.LEFT, padx=5)
        
        # Total general
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)
        ttk.Label(toolbar, text="Total Pendiente:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.lbl_total_creditos_general = ttk.Label(toolbar, text="$0.00", 
                                                      font=("Segoe UI", 12, "bold"), 
                                                      foreground="#c62828")
        self.lbl_total_creditos_general.pack(side=tk.LEFT, padx=5)
        
        # Cantidad
        ttk.Label(toolbar, text="   Cantidad:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.lbl_cantidad_creditos = ttk.Label(toolbar, text="0", font=("Segoe UI", 10, "bold"))
        self.lbl_cantidad_creditos.pack(side=tk.LEFT, padx=5)
        
        # Info: usa el buscador global
        ttk.Label(toolbar, text="   (Usa 'Buscar Cliente' para filtrar)", 
                  font=("Segoe UI", 8, "italic"), foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # ═══════════════════════════════════════════════════════════════
        # LISTADO UNIFICADO DE CRÉDITOS
        # ═══════════════════════════════════════════════════════════════
        frame_lista = ttk.Frame(tab)
        frame_lista.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        frame_lista.columnconfigure(0, weight=1)
        frame_lista.rowconfigure(0, weight=1)
        
        # Treeview unificado
        columnas = ("fecha", "folio", "cliente", "valor_factura", "valor_credito", "abono", "saldo", "estado", "origen")
        self.tree_creditos = ttk.Treeview(frame_lista, columns=columnas, show="headings", height=20)
        
        self.tree_creditos.heading("fecha", text="Fecha", anchor=tk.CENTER)
        self.tree_creditos.heading("folio", text="Folio", anchor=tk.CENTER)
        self.tree_creditos.heading("cliente", text="Cliente", anchor=tk.W)
        self.tree_creditos.heading("valor_factura", text="Valor Factura", anchor=tk.E)
        self.tree_creditos.heading("valor_credito", text="Valor Crédito", anchor=tk.E)
        self.tree_creditos.heading("abono", text="Abono", anchor=tk.E)
        self.tree_creditos.heading("saldo", text="Saldo", anchor=tk.E)
        self.tree_creditos.heading("estado", text="Estado", anchor=tk.CENTER)
        self.tree_creditos.heading("origen", text="Origen", anchor=tk.CENTER)
        
        self.tree_creditos.column("fecha", width=90, anchor=tk.CENTER)
        self.tree_creditos.column("folio", width=70, anchor=tk.CENTER)
        self.tree_creditos.column("cliente", width=200, anchor=tk.W)
        self.tree_creditos.column("valor_factura", width=100, anchor=tk.E)
        self.tree_creditos.column("valor_credito", width=100, anchor=tk.E)
        self.tree_creditos.column("abono", width=90, anchor=tk.E)
        self.tree_creditos.column("saldo", width=100, anchor=tk.E)
        self.tree_creditos.column("estado", width=100, anchor=tk.CENTER)
        self.tree_creditos.column("origen", width=100, anchor=tk.CENTER)
        
        scrolly = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree_creditos.yview)
        scrollx = ttk.Scrollbar(frame_lista, orient=tk.HORIZONTAL, command=self.tree_creditos.xview)
        self.tree_creditos.configure(yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        
        self.tree_creditos.grid(row=0, column=0, sticky="nsew")
        scrolly.grid(row=0, column=1, sticky="ns")
        scrollx.grid(row=1, column=0, sticky="ew")
        
        # Clic simple para editar estado/abono in-place
        self.tree_creditos.bind("<Button-1>", self._on_clic_credito)
        
        # Tags para estados - colores más suaves y profesionales
        self.tree_creditos.tag_configure("pagado", background="#e8f5e9", foreground="#2e7d32")
        self.tree_creditos.tag_configure("pendiente", background="#fff8e1", foreground="#f57c00")
        self.tree_creditos.tag_configure("cancelado", background="#fce4ec", foreground="#c2185b")
        
        # Widget flotante para edición in-place
        self.credito_edit_widget = None
        
        # Variables para compatibilidad
        self.tree_creditos_punt = self.tree_creditos
        self.tree_creditos_elev = self.tree_creditos
        self.lbl_total_creditos_punt_tab = self.lbl_total_creditos_general
        self.lbl_total_creditos_elev_tab = self.lbl_total_creditos_general
        self.lbl_cantidad_creditos_punt = self.lbl_cantidad_creditos
        self.lbl_cantidad_creditos_elev = self.lbl_cantidad_creditos
        
        # Cargar datos iniciales
        self._refrescar_creditos_tab()
    
    def _on_clic_credito(self, event):
        """Maneja clic en créditos para editar abono o estado in-place."""
        self._cerrar_edicion_credito()
        
        item_id = self.tree_creditos.identify_row(event.y)
        column = self.tree_creditos.identify_column(event.x)
        
        if not item_id or not column:
            return
        
        col_idx = int(column.replace('#', '')) - 1
        columnas = ("fecha", "folio", "cliente", "valor_factura", "valor_credito", "abono", "saldo", "estado", "origen")
        
        if col_idx < 0 or col_idx >= len(columnas):
            return
        
        col_name = columnas[col_idx]
        
        if col_name not in ("abono", "estado"):
            self.tree_creditos.selection_set(item_id)
            return
        
        values = self.tree_creditos.item(item_id, 'values')
        fecha = values[0]
        folio = int(values[1])
        origen = values[8]
        tipo = 'eleventa' if origen == 'ELEVENTA' else 'punteado'
        
        bbox = self.tree_creditos.bbox(item_id, column)
        if not bbox:
            return
        
        x, y, width, height = bbox
        
        if col_name == "abono":
            self._crear_entry_abono(item_id, tipo, fecha, folio, x, y, width, height, values)
        elif col_name == "estado":
            self._crear_combo_estado(item_id, tipo, fecha, folio, x, y, width, height, values)
    
    def _cerrar_edicion_credito(self, event=None):
        """Cierra el widget de edición in-place."""
        if hasattr(self, 'credito_edit_widget') and self.credito_edit_widget:
            try:
                self.credito_edit_widget.destroy()
            except:
                pass
            self.credito_edit_widget = None
        if hasattr(self, 'credito_edit_frame') and self.credito_edit_frame:
            try:
                self.credito_edit_frame.destroy()
            except:
                pass
            self.credito_edit_frame = None
    
    def _crear_entry_abono(self, item_id, tipo, fecha, folio, x, y, width, height, values):
        """Crea Entry in-place con botón para editar abono."""
        abono_actual = values[5].replace('$', '').replace(',', '') if values[5] else '0'
        valor_credito_str = values[4].replace('$', '').replace(',', '') if values[4] else '0'
        cliente = values[2] if len(values) > 2 else ''
        
        try:
            valor_credito = float(valor_credito_str)
        except:
            valor_credito = 0
        
        frame = tk.Frame(self.tree_creditos, bg='white', highlightbackground='#1976d2', highlightthickness=2)
        frame.place(x=x-5, y=y, width=width+80, height=height+4)
        
        self.credito_edit_frame = frame
        
        entry = tk.Entry(frame, font=("Segoe UI", 10), justify='right', bd=0)
        entry.insert(0, abono_actual)
        entry.select_range(0, tk.END)
        entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        entry.focus_set()
        
        self.credito_edit_widget = entry
        
        def guardar(event=None):
            try:
                nuevo_abono = float(entry.get().replace(',', '').replace('$', ''))
                if nuevo_abono > valor_credito:
                    entry.config(background='#ffcccc')
                    messagebox.showwarning("Advertencia", 
                        f"El abono (${nuevo_abono:,.2f}) no puede ser mayor al valor del crédito (${valor_credito:,.2f})",
                        parent=self.ventana)
                    return
                
                if tipo == 'punteado':
                    resultado = db_local.actualizar_abono_credito_punteado(fecha, folio, nuevo_abono)
                else:
                    resultado = db_local.actualizar_abono_credito_eleventa(fecha, folio, nuevo_abono)
                
                if isinstance(resultado, dict) and resultado.get('success'):
                    nuevo_saldo = resultado.get('nuevo_saldo', 0)
                    nuevo_estado = resultado.get('nuevo_estado', '')
                    cambio_estado = resultado.get('cambio_estado', False)
                    
                    msg = f"✅ Folio {folio} | Abono: ${nuevo_abono:,.2f} | Saldo: ${nuevo_saldo:,.2f}"
                    if cambio_estado:
                        msg += f" | Estado: {nuevo_estado}"
                        if nuevo_estado == 'PAGADO':
                            messagebox.showinfo("Crédito Pagado", 
                                f"¡El crédito del folio {folio} ha sido pagado completamente!\n\n"
                                f"Cliente: {cliente}\n"
                                f"Valor Crédito: ${valor_credito:,.2f}\n"
                                f"Total Abonado: ${nuevo_abono:,.2f}\n"
                                f"Saldo: ${nuevo_saldo:,.2f}",
                                parent=self.ventana)
                    print(msg)
                elif isinstance(resultado, dict):
                    messagebox.showerror("Error", resultado.get('error', 'Error desconocido'), parent=self.ventana)
                
                self._cerrar_edicion_credito()
                self._refrescar_creditos_tab()
            except ValueError:
                entry.config(background='#ffcccc')
        
        def cancelar(event=None):
            self._cerrar_edicion_credito()
        
        btn_guardar = tk.Button(frame, text="✓", font=("Segoe UI", 9, "bold"), 
                                bg='#4caf50', fg='white', bd=0, width=3,
                                command=guardar, cursor='hand2')
        btn_guardar.pack(side=tk.LEFT, padx=1)
        
        btn_cancelar = tk.Button(frame, text="✗", font=("Segoe UI", 9, "bold"), 
                                 bg='#f44336', fg='white', bd=0, width=3,
                                 command=cancelar, cursor='hand2')
        btn_cancelar.pack(side=tk.LEFT, padx=1)
        
        entry.bind("<Return>", guardar)
        entry.bind("<Escape>", cancelar)
    
    def _crear_combo_estado(self, item_id, tipo, fecha, folio, x, y, width, height, values):
        """Crea Combobox in-place para seleccionar estado."""
        estado_actual = values[7] if len(values) > 7 else 'PENDIENTE'
        
        frame = tk.Frame(self.tree_creditos, bg='white', highlightbackground='#1976d2', highlightthickness=2)
        frame.place(x=x-5, y=y, width=width+50, height=height+4)
        
        self.credito_edit_frame = frame
        
        combo = ttk.Combobox(frame, values=["PENDIENTE", "PAGADO", "CANCELADO"],
                             state="readonly", font=("Segoe UI", 9), width=12)
        combo.set(estado_actual)
        combo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        combo.focus_set()
        
        self.credito_edit_widget = combo
        
        def guardar(event=None):
            nuevo_estado = combo.get()
            if tipo == 'punteado':
                resultado = db_local.actualizar_estado_credito_punteado(fecha, folio, nuevo_estado)
            else:
                resultado = db_local.actualizar_estado_credito_eleventa(fecha, folio, nuevo_estado)
            
            if resultado:
                print(f"✅ Estado actualizado: Folio {folio} | Estado: {nuevo_estado}")
            
            self._cerrar_edicion_credito()
            self._refrescar_creditos_tab()
        
        def cancelar(event=None):
            self._cerrar_edicion_credito()
        
        btn_cancelar = tk.Button(frame, text="✗", font=("Segoe UI", 9, "bold"), 
                                 bg='#f44336', fg='white', bd=0, width=3,
                                 command=cancelar, cursor='hand2')
        btn_cancelar.pack(side=tk.LEFT, padx=1)
        
        combo.bind("<<ComboboxSelected>>", guardar)
        combo.bind("<Escape>", cancelar)
        combo.bind("<FocusOut>", cancelar)
    
    def _saldar_creditos_anteriores(self):
        """Salda automáticamente todos los créditos anteriores al 01 de enero de 2026."""
        respuesta = messagebox.askyesno(
            "Confirmar Saldado Masivo",
            "¿Está seguro de saldar TODOS los créditos anteriores al 01 de Enero de 2026?\n\n"
            "Esto pondrá el ABONO igual al VALOR CRÉDITO para todos esos registros,\n"
            "cambiando su estado a PAGADO.\n\n"
            "Esta acción quedará registrada en el historial y NO se puede deshacer.",
            parent=self.ventana
        )
        
        if not respuesta:
            return
        
        try:
            resultado = db_local.saldar_creditos_anteriores_a_fecha('2026-01-01')
            
            total_creditos = resultado['eleventa_count'] + resultado['punteados_count']
            total_monto = resultado['total_saldado_eleventa'] + resultado['total_saldado_punteados']
            
            if total_creditos > 0:
                messagebox.showinfo(
                    "Saldado Completado",
                    f"Se saldaron {total_creditos} créditos anteriores al 01/01/2026:\n\n"
                    f"• Eleventa: {resultado['eleventa_count']} créditos (${resultado['total_saldado_eleventa']:,.2f})\n"
                    f"• Punteados: {resultado['punteados_count']} créditos (${resultado['total_saldado_punteados']:,.2f})\n\n"
                    f"Total saldado: ${total_monto:,.2f}\n\n"
                    f"Todos los cambios quedaron registrados en el historial.",
                    parent=self.ventana
                )
            else:
                messagebox.showinfo(
                    "Sin Cambios",
                    "No se encontraron créditos pendientes anteriores al 01/01/2026.",
                    parent=self.ventana
                )
            
            self._refrescar_creditos_tab()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al saldar créditos: {e}", parent=self.ventana)
    
    def _cargar_todos_creditos_eleventa(self):
        """Consulta TODOS los créditos de Firebird y los guarda en SQLite."""
        if not self.ruta_fdb or not os.path.exists(self.ruta_fdb):
            messagebox.showerror("Error", "No se ha configurado la ruta de la base de datos Firebird.")
            return
        
        sql = (
            "SET HEADING ON;\n"
            "SELECT V.ID, V.FOLIO, V.NOMBRE, V.SUBTOTAL, V.TOTAL_CREDITO, "
            "CAST(V.CREADO_EN AS DATE) AS FECHA_CREACION\n"
            "FROM VENTATICKETS V\n"
            "WHERE V.TOTAL_CREDITO > 0\n"
            "ORDER BY V.CREADO_EN DESC, V.FOLIO;\n"
        )
        
        ok, stdout, stderr = self._ejecutar_sql(sql)
        
        if not ok or not stdout:
            error_msg = stderr or "No se recibieron datos de la BD"
            messagebox.showerror("Error BD", f"No se pudo consultar créditos:\n{error_msg}")
            return
        
        creditos = []
        header_visto = False
        
        try:
            for linea in stdout.split('\n'):
                linea = linea.strip()
                if not linea or linea.startswith('='):
                    continue
                if 'ID' in linea and 'FOLIO' in linea:
                    header_visto = True
                    continue
                if not header_visto:
                    continue
                
                partes = linea.split()
                if len(partes) < 5:
                    continue
                
                try:
                    id_v = int(partes[0])
                    folio_s = partes[1]
                    if folio_s == '<null>':
                        continue
                    folio = int(folio_s)
                    
                    fecha = partes[-1] if partes[-1] != '<null>' else ''
                    total_credito = float(partes[-2]) if partes[-2] != '<null>' else 0.0
                    subtotal = float(partes[-3]) if partes[-3] != '<null>' else 0.0
                    nombre = ' '.join(partes[2:-3]).replace('<null>', '').strip()
                    if not nombre:
                        nombre = 'MOSTRADOR'
                    
                    if folio <= 0 or total_credito <= 0:
                        continue
                    
                    creditos.append({
                        'fecha': fecha,
                        'folio': folio,
                        'id': id_v,
                        'nombre': nombre,
                        'subtotal': subtotal,
                        'total_credito': total_credito,
                        'repartidor': ''
                    })
                except (ValueError, IndexError):
                    continue
            
            if not creditos:
                messagebox.showinfo("Info", "No se encontraron créditos en el sistema Eleventa.")
                return
            
            creditos_por_fecha = {}
            for c in creditos:
                fecha = c['fecha']
                if fecha not in creditos_por_fecha:
                    creditos_por_fecha[fecha] = []
                creditos_por_fecha[fecha].append(c)
            
            total_guardados = 0
            for fecha, lista in creditos_por_fecha.items():
                count = db_local.guardar_creditos_eleventa_bulk(fecha, lista)
                total_guardados += count
            
            messagebox.showinfo("Carga Completa", 
                f"Se cargaron {total_guardados} créditos de {len(creditos_por_fecha)} fechas diferentes.")
            
            self._refrescar_creditos_tab()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error procesando créditos: {e}")
    
    def _refrescar_creditos_tab(self):
        """Refresca la lista unificada de créditos (Punteados + Eleventa)."""
        self.tree_creditos.delete(*self.tree_creditos.get_children())
        
        if not USE_SQLITE:
            return
        
        filtro_cliente = self.buscar_global_var.get().strip().lower() if hasattr(self, 'buscar_global_var') else ""
        filtro_estado = self.filtro_estado_creditos_var.get() if hasattr(self, 'filtro_estado_creditos_var') else "Todos"
        filtro_origen = self.filtro_origen_creditos_var.get() if hasattr(self, 'filtro_origen_creditos_var') else "Todos"
        
        self.tree_creditos.tag_configure("pagado", background="#e8f5e9", foreground="#2e7d32")
        self.tree_creditos.tag_configure("pendiente", background="#fff8e1", foreground="#f57c00")
        self.tree_creditos.tag_configure("cancelado", background="#fce4ec", foreground="#c2185b")
        
        creditos_unificados = []
        
        # CRÉDITOS PUNTEADOS
        if filtro_origen in ("Todos", "PUNTEADO"):
            creditos_punt = db_local.obtener_todos_creditos_punteados()
            for cp in creditos_punt:
                creditos_unificados.append({
                    'fecha': cp.get('fecha', ''),
                    'folio': cp.get('folio', ''),
                    'cliente': cp.get('cliente', ''),
                    'valor_factura': cp.get('subtotal', 0) or 0,
                    'valor_credito': cp.get('valor_credito', 0) or cp.get('subtotal', 0) or 0,
                    'abono': cp.get('abono', 0) or 0,
                    'estado': cp.get('estado', 'PENDIENTE') or 'PENDIENTE',
                    'origen': 'PUNTEADO'
                })
        
        # CRÉDITOS ELEVENTA
        if filtro_origen in ("Todos", "ELEVENTA"):
            creditos_elev = db_local.obtener_todos_creditos_eleventa()
            for ce in creditos_elev:
                valor_factura = ce.get('subtotal', 0) or 0
                valor_credito = ce.get('total_credito', 0) or 0
                estado_guardado = ce.get('estado', 'PENDIENTE') or 'PENDIENTE'
                
                if valor_factura == 0 and valor_credito > 0 and estado_guardado not in ('PAGADO',):
                    estado = 'CANCELADO'
                else:
                    estado = estado_guardado
                
                creditos_unificados.append({
                    'fecha': ce.get('fecha', ''),
                    'folio': ce.get('folio', ''),
                    'cliente': ce.get('cliente', ''),
                    'valor_factura': valor_factura,
                    'valor_credito': valor_credito,
                    'abono': ce.get('abono', 0) or 0,
                    'estado': estado,
                    'origen': 'ELEVENTA'
                })
        
        creditos_unificados.sort(key=lambda x: x['fecha'], reverse=True)
        
        total_credito = 0
        total_pendiente = 0
        count_total = 0
        
        for c in creditos_unificados:
            fecha = c['fecha']
            folio = c['folio']
            cliente = c['cliente']
            valor_factura = c['valor_factura']
            valor_credito = c['valor_credito']
            abono = c['abono']
            estado = c['estado']
            origen = c['origen']
            
            if filtro_cliente:
                if filtro_cliente not in cliente.lower() and filtro_cliente not in str(folio):
                    continue
            
            if filtro_estado != "Todos" and estado != filtro_estado:
                continue
            
            total_credito += valor_credito
            if estado == 'PENDIENTE':
                total_pendiente += (valor_credito - abono)
            count_total += 1
            
            if estado == "PAGADO":
                tag = "pagado"
            elif estado == "CANCELADO":
                tag = "cancelado"
            else:
                tag = "pendiente"
            
            saldo = valor_credito - abono
            self.tree_creditos.insert("", tk.END, values=(
                fecha,
                folio,
                cliente,
                f"${valor_factura:,.2f}",
                f"${valor_credito:,.2f}",
                f"${abono:,.2f}",
                f"${saldo:,.2f}",
                estado,
                origen
            ), tags=(tag,))
        
        self.lbl_cantidad_creditos.config(text=str(count_total))
        self.lbl_total_creditos_general.config(text=f"${total_pendiente:,.2f}")
