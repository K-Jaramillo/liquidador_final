#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXPORTADOR DE VENTAS - PDVDATA.FDB
Interfaz gráfica para exportar ventas/facturas por fecha
Compatible con Firebird 2.5
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import pandas as pd
import subprocess
import sys
import os
import tempfile
from pathlib import Path
from utils_descuentos import cargar_descuentos, obtener_descuentos_repartidor, obtener_descuentos_factura, obtener_total_descuentos_factura
from utils_repartidores import obtener_repartidor_factura, obtener_repartidores_del_dia

class ExportadorVentas:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("Exportador de Ventas - PDVDATA.FDB")
        self.ventana.geometry("1000x600")
        self.ventana.resizable(True, True)
        
        # Configuración
        self.isql_path = '/opt/firebird/bin/isql'
        self.ruta_fdb_default = os.path.join(os.path.dirname(__file__), 'PDVDATA.FDB')
        self.ruta_fdb = tk.StringVar(value=self.ruta_fdb_default)
        self.usuario = 'SYSDBA'
        self.password = 'masterkey'
        
        # Variables para fechas
        self.fecha_inicio = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.fecha_fin = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        # Filtro ventas a crédito
        self.filtrar_credito = tk.BooleanVar(value=False)
        # Expresión SQL por defecto para intentar detectar ventas a crédito.
        # El usuario puede editarla según su esquema de BD.
        self.filtro_credito_sql = tk.StringVar(value="(FORMA_PAGO = 'CREDITO' OR CONDICION = 'CREDITO' OR CREDITO = 1)")
        
        self._crear_interfaz()
    
    def _crear_interfaz(self):
        """Crea la interfaz gráfica"""
        
        # ===== FRAME SUPERIOR: CONFIGURACIÓN =====
        frame_config = ttk.LabelFrame(self.ventana, text="Configuración", padding=15)
        frame_config.pack(fill=tk.X, padx=10, pady=10)
        
        # Fila 1: Archivo FDB
        ttk.Label(frame_config, text="Archivo FDB:").grid(row=0, column=0, sticky=tk.W, pady=5)
        frame_fdb = ttk.Frame(frame_config)
        frame_fdb.grid(row=0, column=1, columnspan=2, sticky=tk.EW, pady=5)
        ttk.Entry(frame_fdb, textvariable=self.ruta_fdb, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame_fdb, text="Examinar", command=self._seleccionar_archivo, width=10).pack(side=tk.LEFT, padx=5)
        
        # Fila 2: Fechas
        ttk.Label(frame_config, text="Fecha Inicio:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame_config, textvariable=self.fecha_inicio, width=20).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame_config, text="Fecha Fin:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=5)
        ttk.Entry(frame_config, textvariable=self.fecha_fin, width=20).grid(row=1, column=3, sticky=tk.W, pady=5)
        
        # Fila 3: Filtro Crédito
        ttk.Checkbutton(frame_config, text="Sólo ventas a crédito", variable=self.filtrar_credito).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame_config, text="Filtro SQL (editable):").grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Entry(frame_config, textvariable=self.filtro_credito_sql, width=60).grid(row=2, column=2, columnspan=2, sticky=tk.W, pady=5)
        
        # Botones rápidos
        frame_botones_fecha = ttk.Frame(frame_config)
        frame_botones_fecha.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=10)
        
        ttk.Button(frame_botones_fecha, text="Hoy", command=self._set_hoy, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_botones_fecha, text="Ayer", command=self._set_ayer, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_botones_fecha, text="Esta Semana", command=self._set_semana, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_botones_fecha, text="Este Mes", command=self._set_mes, width=10).pack(side=tk.LEFT, padx=2)
        
        frame_config.columnconfigure(1, weight=1)
        frame_config.columnconfigure(3, weight=1)
        
        # ===== FRAME CENTRAL: INFORMACIÓN =====
        frame_info = ttk.LabelFrame(self.ventana, text="Información", padding=15)
        frame_info.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.info_text = tk.Text(frame_info, height=15, width=100, state=tk.DISABLED, bg='#f0f0f0')
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame_info, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.config(yscrollcommand=scrollbar.set)
        
        # ===== FRAME INFERIOR: BOTONES =====
        frame_botones = ttk.Frame(self.ventana)
        frame_botones.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(frame_botones, text="Verificar Conexión", command=self._verificar_conexion, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Ver Datos", command=self._ver_datos, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Exportar a Excel", command=self._exportar_excel, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Exportar a CSV", command=self._exportar_csv, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Exportar por Repartidor", command=self._exportar_por_repartidor, width=20,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Liquidar Repartidores", command=self._abrir_liquidador, width=20, 
                  style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Limpiar", command=self._limpiar_info, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Salir", command=self.ventana.quit, width=10).pack(side=tk.RIGHT, padx=5)
    
    def _agregar_info(self, texto, titulo=None):
        """Agrega texto al cuadro de información"""
        self.info_text.config(state=tk.NORMAL)
        if titulo:
            self.info_text.insert(tk.END, f"\n{'='*80}\n{titulo}\n{'='*80}\n")
        self.info_text.insert(tk.END, texto + "\n")
        self.info_text.see(tk.END)
        self.info_text.config(state=tk.DISABLED)
        self.ventana.update()
    
    def _limpiar_info(self):
        """Limpia el cuadro de información"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete('1.0', tk.END)
        self.info_text.config(state=tk.DISABLED)
    
    def _seleccionar_archivo(self):
        """Abre diálogo para seleccionar archivo FDB"""
        archivo = filedialog.askopenfilename(
            title="Seleccionar PDVDATA.FDB",
            filetypes=[("Firebird Database", "*.FDB"), ("Todos", "*.*")]
        )
        if archivo:
            self.ruta_fdb.set(archivo)
    
    def _set_hoy(self):
        """Establece fecha de hoy"""
        hoy = datetime.now().strftime('%Y-%m-%d')
        self.fecha_inicio.set(hoy)
        self.fecha_fin.set(hoy)
    
    def _set_ayer(self):
        """Establece fecha de ayer"""
        ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.fecha_inicio.set(ayer)
        self.fecha_fin.set(ayer)
    
    def _set_semana(self):
        """Establece esta semana"""
        hoy = datetime.now()
        inicio = (hoy - timedelta(days=hoy.weekday())).strftime('%Y-%m-%d')
        fin = hoy.strftime('%Y-%m-%d')
        self.fecha_inicio.set(inicio)
        self.fecha_fin.set(fin)
    
    def _set_mes(self):
        """Establece este mes"""
        hoy = datetime.now()
        inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
        fin = hoy.strftime('%Y-%m-%d')
        self.fecha_inicio.set(inicio)
        self.fecha_fin.set(fin)
    
    def _ejecutar_sql(self, sql):
        """Ejecuta SQL contra Firebird"""
        try:
            if not os.path.exists(self.ruta_fdb.get()):
                raise Exception(f"Archivo no encontrado: {self.ruta_fdb.get()}")
            
            cmd = ['sudo', self.isql_path, '-u', self.usuario, '-p', self.password, 
                   self.ruta_fdb.get()]
            
            run_kwargs = {
                'input': sql,
                'capture_output': True,
                'text': True,
                'timeout': 30,
                'encoding': 'utf-8'
            }
            if sys.platform == 'win32':
                run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            resultado = subprocess.run(cmd, **run_kwargs)
            
            return resultado.returncode == 0, resultado.stdout, resultado.stderr
        
        except Exception as e:
            return False, "", str(e)

    def _condicion_credito_sql(self):
        """Devuelve la condición SQL para filtrar ventas a crédito si está activada."""
        if self.filtrar_credito.get():
            cond = self.filtro_credito_sql.get().strip()
            if cond:
                return f" AND ({cond})"
        return ""
    
    def _verificar_conexion(self):
        """Verifica la conexión a la base de datos"""
        self._limpiar_info()
        self._agregar_info("Verificando conexión...", "VERIFICACIÓN DE CONEXIÓN")
        
        sql = "SELECT COUNT(*) as VENTAS FROM VENTATICKETS;"
        
        ok, output, error = self._ejecutar_sql(sql)
        
        if ok:
            self._agregar_info(f"✓ Conexión exitosa\n{output}")
        else:
            self._agregar_info(f"✗ Error de conexión:\n{error}")
    
    def _ver_datos(self):
        """Muestra datos de ventas del rango de fechas"""
        self._limpiar_info()
        self._agregar_info("Consultando datos...", "VER DATOS DE VENTAS")
        
        fecha_ini = self.fecha_inicio.get()
        fecha_fin = self.fecha_fin.get()
        cond_credito = self._condicion_credito_sql()
        
        sql = f"""
        SET HEADING ON;
        SELECT 
            ID, FOLIO, NOMBRE, TOTAL, SUBTOTAL, IMPUESTOS
        FROM VENTATICKETS 
        WHERE CAST(CREADO_EN AS DATE) BETWEEN '{fecha_ini}' AND '{fecha_fin}'{cond_credito}
        ORDER BY CREADO_EN;
        """
        
        ok, output, error = self._ejecutar_sql(sql)
        
        if ok:
            self._agregar_info(output)
            
            # Calcular totales incluyendo descuentos
            lineas = output.strip().split('\n')
            total_descuentos = 0
            total_ventas = 0
            total_subtotal = 0
            
            header_visto = False
            for linea in lineas:
                linea = linea.strip()
                if linea and not linea.startswith('=') and 'ID' not in linea and linea and linea[0].isdigit():
                    try:
                        partes = linea.split()
                        if len(partes) >= 6:
                            folio = int(partes[1])
                            subtotal = float(partes[-2])
                            total_subtotal += subtotal
                            total_ventas += float(partes[-3])
                            total_descuentos += obtener_total_descuentos_factura(folio)
                    except:
                        pass
            
            if total_descuentos > 0:
                self._agregar_info(f"\n{'='*80}\nRESUMEN CON DESCUENTOS\n{'='*80}\n"
                                 f"Total Subtotal:     ${total_subtotal:>12,.2f}\n"
                                 f"Total Descuentos:   ${total_descuentos:>12,.2f}\n"
                                 f"Total Neto:         ${(total_ventas - total_descuentos):>12,.2f}\n", 
                                 titulo=None)
        else:
            self._agregar_info(f"✗ Error:\n{error}")
    
    def _exportar_excel(self):
        """Exporta ventas a Excel"""
        self._limpiar_info()
        self._agregar_info("Preparando exportación a Excel...", "EXPORTAR A EXCEL")
        
        fecha_ini = self.fecha_inicio.get()
        fecha_fin = self.fecha_fin.get()
        
        try:
            # Obtener datos
            cond_credito = self._condicion_credito_sql()
            sql = f"""
            SET HEADING ON;
            SELECT 
                ID, FOLIO, NOMBRE, TOTAL, SUBTOTAL, IMPUESTOS
            FROM VENTATICKETS 
            WHERE CAST(CREADO_EN AS DATE) BETWEEN '{fecha_ini}' AND '{fecha_fin}'{cond_credito}
            ORDER BY CREADO_EN;
            """
            
            ok, output, error = self._ejecutar_sql(sql)
            
            if not ok:
                self._agregar_info(f"✗ Error en consulta:\n{error}")
                return
            
            # Procesar datos
            lineas = output.strip().split('\n')
            if len(lineas) < 2:
                self._agregar_info("No hay datos para exportar en este rango de fechas")
                return
            
            # Extraer encabezados y datos
            datos = []
            encabezados_encontrado = False
            
            for linea in lineas:
                if 'ID' in linea and 'FOLIO' in linea:
                    encabezados_encontrado = True
                    continue
                
                if '---' in linea or not encabezados_encontrado:
                    continue
                
                if linea.strip():
                    datos.append(linea)
            
            if not datos:
                self._agregar_info("No hay datos procesables")
                return
            
            # Crear DataFrame
            df_data = []
            for linea in datos:
                partes = linea.split()
                if len(partes) >= 6:
                    try:
                        impuestos = float(partes[-1])
                        subtotal = float(partes[-2])
                        total = float(partes[-3])
                        folio = int(partes[1])
                        id_venta = int(partes[0])
                        nombre = ' '.join(partes[2:-3])
                        
                        df_data.append({
                            'ID': id_venta,
                            'FOLIO': folio,
                            'NOMBRE': nombre,
                            'TOTAL': total,
                            'SUBTOTAL': subtotal,
                            'IMPUESTOS': impuestos,
                            'DESCUENTOS': obtener_total_descuentos_factura(folio),
                        })
                    except (ValueError, IndexError):
                        continue
            
            if not df_data:
                self._agregar_info("No se pudieron procesar los datos")
                return
            
            df = pd.DataFrame(df_data)
            
            # Calcular total de descuentos
            total_descuentos = df['DESCUENTOS'].sum() if 'DESCUENTOS' in df.columns else 0
            
            # Guardar
            archivo_salida = f"Ventas_{fecha_ini}_a_{fecha_fin}.xlsx"
            df.to_excel(archivo_salida, index=False, sheet_name='Ventas')
            
            self._agregar_info(f"✓ Archivo guardado: {archivo_salida}\n"
                             f"  Total de registros: {len(df)}\n"
                             f"  Total Descuentos: ${total_descuentos:,.2f}\n"
                             f"  Ubicación: {os.path.abspath(archivo_salida)}")
            
        except Exception as e:
            self._agregar_info(f"✗ Error: {e}")
    
    def _exportar_csv(self):
        """Exporta ventas a CSV con descuentos"""
        self._limpiar_info()
        self._agregar_info("Preparando exportación a CSV...", "EXPORTAR A CSV")
        
        fecha_ini = self.fecha_inicio.get()
        fecha_fin = self.fecha_fin.get()
        
        try:
            # Obtener datos
            cond_credito = self._condicion_credito_sql()
            sql = f"""
            SET HEADING ON;
            SELECT 
                ID, FOLIO, NOMBRE, TOTAL, SUBTOTAL, IMPUESTOS
            FROM VENTATICKETS 
            WHERE CAST(CREADO_EN AS DATE) BETWEEN '{fecha_ini}' AND '{fecha_fin}'{cond_credito}
            ORDER BY CREADO_EN;
            """
            
            ok, output, error = self._ejecutar_sql(sql)
            
            if not ok:
                self._agregar_info(f"✗ Error en consulta:\n{error}")
                return
            
            # Procesar datos y agregar columna de descuentos
            lineas = output.strip().split('\n')
            datos_csv = []
            header_visto = False
            encabezado_csv = "ID,FOLIO,NOMBRE,TOTAL,SUBTOTAL,IMPUESTOS,DESCUENTOS\n"
            
            for linea in lineas:
                linea = linea.strip()
                if 'ID' in linea and 'FOLIO' in linea:
                    header_visto = True
                    continue
                if '---' in linea or not header_visto or not linea:
                    continue
                
                if linea and linea[0].isdigit():
                    partes = linea.split()
                    if len(partes) >= 6:
                        try:
                            id_v = int(partes[0])
                            folio = int(partes[1])
                            subtotal = float(partes[-2])
                            impuestos = float(partes[-1])
                            total = float(partes[-3])
                            nombre = ' '.join(partes[2:-3]).replace('"', '""')
                            desc_total = obtener_total_descuentos_factura(folio)
                            
                            datos_csv.append(f'{id_v},{folio},"{nombre}",{total},{subtotal},{impuestos},{desc_total}\n')
                        except:
                            pass
            
            # Guardar
            archivo_salida = f"Ventas_{fecha_ini}_a_{fecha_fin}.csv"
            with open(archivo_salida, 'w', encoding='utf-8-sig') as f:
                f.write(encabezado_csv)
                f.writelines(datos_csv)
            
            total_desc = sum(float(l.split(',')[-1]) for l in datos_csv if len(l.split(',')) > 6)
            
            self._agregar_info(f"✓ Archivo guardado: {archivo_salida}\n"
                             f"  Total de líneas: {len(datos_csv)}\n"
                             f"  Total Descuentos: ${total_desc:,.2f}\n"
                             f"  Ubicación: {os.path.abspath(archivo_salida)}")
            
        except Exception as e:
            self._agregar_info(f"✗ Error: {e}")
    def _exportar_por_repartidor(self):
        """Exporta ventas por repartidor en hojas diferentes"""
        self._limpiar_info()
        self._agregar_info("Preparando exportación por repartidor...", "EXPORTAR POR REPARTIDOR")
        
        fecha_ini = self.fecha_inicio.get()
        fecha_fin = self.fecha_fin.get()
        
        try:
            # Obtener datos
            cond_credito = self._condicion_credito_sql()
            sql = f"""
            SET HEADING ON;
            SELECT 
                ID, FOLIO, NOMBRE, TOTAL, SUBTOTAL, IMPUESTOS
            FROM VENTATICKETS 
            WHERE CAST(CREADO_EN AS DATE) BETWEEN '{fecha_ini}' AND '{fecha_fin}'{cond_credito}
            ORDER BY FOLIO;
            """
            
            ok, output, error = self._ejecutar_sql(sql)
            
            if not ok:
                self._agregar_info(f"✗ Error en consulta:\n{error}")
                return
            
            # Procesar datos
            lineas = output.strip().split('\n')
            
            datos_por_repartidor = {}
            facturas_sin_asignar = []
            
            for linea in lineas:
                linea = linea.strip()
                if linea and not linea.startswith('=') and 'ID' not in linea and linea[0].isdigit():
                    partes = linea.split()
                    if len(partes) >= 6:
                        try:
                            id_venta = int(partes[0])
                            folio = int(partes[1])
                            subtotal = float(partes[-2])
                            impuestos = float(partes[-1])
                            total = float(partes[-3])
                            nombre = ' '.join(partes[2:-3])
                            
                            # Obtener repartidor asignado
                            repartidor = obtener_repartidor_factura(folio, fecha_ini)
                            
                            if not repartidor:
                                facturas_sin_asignar.append(folio)
                                continue
                            
                            if repartidor not in datos_por_repartidor:
                                datos_por_repartidor[repartidor] = {
                                    "repartidor": repartidor,
                                    "ventas": []
                                }
                            
                            # Obtener observaciones de descuentos
                            obs_descuentos = []
                            try:
                                from utils_descuentos import obtener_descuentos_factura
                                descuentos = obtener_descuentos_factura(folio)
                                for desc in descuentos:
                                    if desc['fecha'].startswith(fecha_ini):
                                        obs_descuentos.append(f"{desc['tipo'].upper()}: {desc['observacion']}")
                            except:
                                pass
                            
                            datos_por_repartidor[repartidor]["ventas"].append({
                                'ID': id_venta,
                                'FOLIO': folio,
                                'NOMBRE': nombre,
                                'TOTAL': total,
                                'SUBTOTAL': subtotal,
                                'IMPUESTOS': impuestos,
                                'OBSERVACIONES': ' | '.join(obs_descuentos) if obs_descuentos else ''
                            })
                        except:
                            pass
            
            if not datos_por_repartidor:
                if facturas_sin_asignar:
                    self._agregar_info(f"⚠ Hay {len(facturas_sin_asignar)} facturas sin repartidor asignado.\n"
                                     f"Usa la pestaña 'Asignar Repartidores' para asignarlas.")
                else:
                    self._agregar_info("No hay datos para exportar")
                return
            
            # Crear Excel con hojas por repartidor
            archivo_salida = f"Ventas_por_Repartidor_{fecha_ini}_a_{fecha_fin}.xlsx"
            
            with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
                for repartidor, datos in sorted(datos_por_repartidor.items()):
                    df = pd.DataFrame(datos["ventas"])
                    nombre_hoja = repartidor[:31]  # Excel limit 31 chars
                    df.to_excel(writer, sheet_name=nombre_hoja, index=False)
            
            mensaje = f"✓ Archivo guardado: {archivo_salida}\n"
            mensaje += f"  Total de repartidores: {len(datos_por_repartidor)}\n"
            if facturas_sin_asignar:
                mensaje += f"  ⚠ Facturas sin asignar: {len(facturas_sin_asignar)}\n"
            mensaje += f"  Ubicación: {os.path.abspath(archivo_salida)}"
            
            self._agregar_info(mensaje)
            
        except Exception as e:
            self._agregar_info(f"✗ Error: {e}")
    
    def _abrir_liquidador(self):
        """Abre la ventana del liquidador de repartidores"""
        try:
            # Importar dinámicamente para evitar dependencias circulares
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            from liquidador_repartidores import LiquidadorRepartidores
            
            ventana_liquidador = tk.Toplevel(self.ventana)
            app = LiquidadorRepartidores(ventana_liquidador)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el liquidador:\n{str(e)}")

def main():
    """Función principal"""
    ventana = tk.Tk()
    app = ExportadorVentas(ventana)
    
    # Centrar ventana
    ventana.update_idletasks()
    ancho = ventana.winfo_width()
    alto = ventana.winfo_height()
    x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f"+{x}+{y}")
    
    ventana.mainloop()

if __name__ == '__main__':
    main()
