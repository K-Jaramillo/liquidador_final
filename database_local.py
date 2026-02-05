# Función para guardar resumen de cancelaciones por usuario
def guardar_cancelaciones_usuario(fecha: str, resumen: dict):
    """Guarda el resumen de cancelaciones por usuario para una fecha.
    
    El resumen incluye:
    - total: suma total de cancelaciones
    - num: número de cancelaciones
    - detalle: diccionario con cancelaciones por forma de pago
        - efectivo: cancelaciones en efectivo
        - credito: créditos cancelados
        - tarjeta: cancelaciones de tarjeta
        - vales: cancelaciones de vales
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Asegurar que existen las columnas de detalle
    try:
        cursor.execute('ALTER TABLE cancelaciones_usuario ADD COLUMN dev_efectivo REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE cancelaciones_usuario ADD COLUMN dev_credito REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE cancelaciones_usuario ADD COLUMN dev_tarjeta REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE cancelaciones_usuario ADD COLUMN dev_vales REAL DEFAULT 0')
    except:
        pass
    
    for usuario, datos in resumen.items():
        total = datos.get('total', 0)
        num = datos.get('num', 0)
        detalle = datos.get('detalle', {})
        dev_efectivo = detalle.get('efectivo', 0)
        dev_credito = detalle.get('credito', 0)
        dev_tarjeta = detalle.get('tarjeta', 0)
        dev_vales = detalle.get('vales', 0)
        
        cursor.execute('''
            INSERT OR REPLACE INTO cancelaciones_usuario 
            (fecha, usuario, total_cancelado, num_cancelaciones, dev_efectivo, dev_credito, dev_tarjeta, dev_vales)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha, usuario, total, num, dev_efectivo, dev_credito, dev_tarjeta, dev_vales))
    conn.commit()
    conn.close()

# Función para obtener resumen de cancelaciones por usuario
def obtener_cancelaciones_usuario(fecha: str) -> dict:
    """Obtiene el resumen de cancelaciones por usuario para una fecha.
    
    Retorna: { 'usuario': {'total': X, 'num': N, 'detalle': {...}}, ... }
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verificar si existen las columnas de detalle
    cursor.execute("PRAGMA table_info(cancelaciones_usuario)")
    columnas = [col[1] for col in cursor.fetchall()]
    tiene_detalle = 'dev_efectivo' in columnas
    
    if tiene_detalle:
        cursor.execute('''
            SELECT usuario, total_cancelado, num_cancelaciones,
                   COALESCE(dev_efectivo, 0) as dev_efectivo,
                   COALESCE(dev_credito, 0) as dev_credito,
                   COALESCE(dev_tarjeta, 0) as dev_tarjeta,
                   COALESCE(dev_vales, 0) as dev_vales
            FROM cancelaciones_usuario
            WHERE fecha = ?
        ''', (fecha,))
    else:
        cursor.execute('''
            SELECT usuario, total_cancelado, num_cancelaciones
            FROM cancelaciones_usuario
            WHERE fecha = ?
        ''', (fecha,))
    
    rows = cursor.fetchall()
    conn.close()
    resultado = {}
    for row in rows:
        detalle = {}
        if tiene_detalle:
            detalle = {
                'efectivo': row['dev_efectivo'],
                'credito': row['dev_credito'],
                'tarjeta': row['dev_tarjeta'],
                'vales': row['dev_vales']
            }
        resultado[row['usuario']] = {
            'total': row['total_cancelado'],
            'num': row['num_cancelaciones'],
            'detalle': detalle
        }
    return resultado
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATABASE LOCAL - Base de datos SQLite para persistencia del Liquidador
Almacena: asignaciones, descuentos, gastos, conteo de dinero, configuración
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# Ruta de la base de datos local
DB_PATH = os.path.join(os.path.dirname(__file__), "liquidador_data.db")


def get_connection():
    """Obtiene una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Para acceder a columnas por nombre
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CANCELACIONES_USUARIO
    # Guarda el total de cancelaciones por usuario/cajero y fecha
    # Incluye detalle por forma de pago (efectivo, crédito, tarjeta, vales)
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cancelaciones_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            usuario TEXT NOT NULL,
            total_cancelado REAL NOT NULL DEFAULT 0,
            num_cancelaciones INTEGER NOT NULL DEFAULT 0,
            dev_efectivo REAL DEFAULT 0,
            dev_credito REAL DEFAULT 0,
            dev_tarjeta REAL DEFAULT 0,
            dev_vales REAL DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fecha, usuario)
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: ASIGNACIONES
    # Guarda la asignación de facturas a repartidores por fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            folio INTEGER NOT NULL,
            repartidor TEXT NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fecha, folio)
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: DESCUENTOS
    # Guarda los descuentos aplicados a facturas (crédito, devolución, ajuste)
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS descuentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            folio INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('credito', 'devolucion', 'ajuste')),
            monto REAL NOT NULL DEFAULT 0,
            repartidor TEXT,
            observacion TEXT,
            cliente TEXT,
            articulo TEXT,
            precio_facturado REAL DEFAULT 0,
            precio_nuevo REAL DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Agregar columnas si no existen (para bases de datos existentes)
    try:
        cursor.execute('ALTER TABLE descuentos ADD COLUMN cliente TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE descuentos ADD COLUMN articulo TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE descuentos ADD COLUMN precio_facturado REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE descuentos ADD COLUMN precio_nuevo REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE descuentos ADD COLUMN cantidad REAL DEFAULT 0')
    except:
        pass
    # ══════════════════════════════════════════════════════════════════
    # TABLA: GASTOS
    # Guarda los gastos por repartidor y fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            repartidor TEXT NOT NULL,
            concepto TEXT NOT NULL,
            monto REAL NOT NULL DEFAULT 0,
            observaciones TEXT DEFAULT '',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Agregar columna observaciones si no existe (para bases de datos existentes)
    try:
        cursor.execute('ALTER TABLE gastos ADD COLUMN observaciones TEXT DEFAULT ""')
    except:
        pass  # La columna ya existe
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CONTEO_DINERO
    # Guarda el conteo de dinero por repartidor y fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conteo_dinero (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            repartidor TEXT NOT NULL,
            denominacion INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fecha, repartidor, denominacion)
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CONTEOS_SESION
    # Guarda múltiples conteos (sesiones) por repartidor y fecha
    # Permite que un repartidor tenga varios conteos en el mismo día
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conteos_sesion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            repartidor TEXT NOT NULL,
            descripcion TEXT DEFAULT '',
            hora TEXT DEFAULT '',
            total REAL NOT NULL DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CONTEOS_SESION_DETALLE
    # Detalle de denominaciones para cada sesión de conteo
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conteos_sesion_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id INTEGER NOT NULL,
            denominacion INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sesion_id) REFERENCES conteos_sesion(id) ON DELETE CASCADE,
            UNIQUE(sesion_id, denominacion)
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CONFIGURACION
    # Guarda configuraciones generales del programa
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: REPARTIDORES
    # Lista de repartidores registrados
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repartidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            activo INTEGER DEFAULT 1,
            telefono TEXT,
            notas TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: PAGO_PROVEEDORES
    # Guarda los pagos a proveedores por fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pago_proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            proveedor TEXT NOT NULL,
            concepto TEXT,
            monto REAL NOT NULL DEFAULT 0,
            repartidor TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # ══════════════════════════════════════════════════════════════════
    # TABLA: PRESTAMOS
    # Guarda los préstamos realizados a repartidores
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            repartidor TEXT NOT NULL,
            concepto TEXT,
            monto REAL NOT NULL DEFAULT 0,
            estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'pagado', 'parcial')),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: HISTORIAL_LIQUIDACIONES
    # Guarda el historial de liquidaciones generadas
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_liquidaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            repartidor TEXT NOT NULL,
            total_ventas REAL DEFAULT 0,
            total_descuentos REAL DEFAULT 0,
            total_gastos REAL DEFAULT 0,
            total_dinero REAL DEFAULT 0,
            neto REAL DEFAULT 0,
            diferencia REAL DEFAULT 0,
            fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            datos_json TEXT
        )
    ''')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: DEVOLUCIONES_PARCIALES
    # Guarda las devoluciones parciales de artículos por factura
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devoluciones_parciales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            folio INTEGER NOT NULL,
            devolucion_id INTEGER,
            codigo_producto TEXT,
            descripcion_producto TEXT,
            cantidad_devuelta REAL DEFAULT 0,
            valor_unitario REAL DEFAULT 0,
            dinero_devuelto REAL DEFAULT 0,
            fecha_devolucion DATE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Agregar columna valor_unitario si no existe (migración)
    try:
        cursor.execute('ALTER TABLE devoluciones_parciales ADD COLUMN valor_unitario REAL DEFAULT 0')
    except:
        pass  # La columna ya existe
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CONCEPTOS_GASTOS
    # Guarda los conceptos personalizados para gastos
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conceptos_gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concepto TEXT NOT NULL UNIQUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertar conceptos por defecto si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM conceptos_gastos')
    if cursor.fetchone()[0] == 0:
        conceptos_default = [
            'GASOLINA', 'ALMUERZO', 'PEAJE', 'PARQUEADERO', 'REPARACIÓN VEHÍCULO',
            'LAVADO VEHÍCULO', 'RECARGA CELULAR', 'NÓMINA', 'SOCIOS', 'OTROS'
        ]
        for c in conceptos_default:
            try:
                cursor.execute('INSERT INTO conceptos_gastos (concepto) VALUES (?)', (c,))
            except:
                pass
    else:
        # Asegurar que NÓMINA y SOCIOS existan (pueden ser agregados en actualizaciones)
        for c in ['NÓMINA', 'SOCIOS']:
            try:
                cursor.execute('INSERT OR IGNORE INTO conceptos_gastos (concepto) VALUES (?)', (c,))
            except:
                pass
    
    # Crear índices para mejorar rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_asignaciones_fecha ON asignaciones(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_descuentos_fecha ON descuentos(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conteo_fecha ON conteo_dinero(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devoluciones_parciales_fecha ON devoluciones_parciales(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devoluciones_parciales_folio ON devoluciones_parciales(folio)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pago_proveedores_fecha ON pago_proveedores(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prestamos_fecha ON prestamos(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prestamos_repartidor ON prestamos(repartidor)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conteos_sesion_fecha ON conteos_sesion(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conteos_sesion_repartidor ON conteos_sesion(repartidor)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conteos_sesion_detalle_sesion ON conteos_sesion_detalle(sesion_id)')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: PAGO_NOMINA
    # Guarda los pagos de nómina por fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pago_nomina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            empleado TEXT NOT NULL,
            concepto TEXT,
            monto REAL NOT NULL DEFAULT 0,
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pago_nomina_fecha ON pago_nomina(fecha)')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: PAGO_SOCIOS
    # Guarda los pagos a socios por fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pago_socios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            socio TEXT NOT NULL,
            concepto TEXT,
            monto REAL NOT NULL DEFAULT 0,
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pago_socios_fecha ON pago_socios(fecha)')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: TRANSFERENCIAS
    # Guarda las transferencias por fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transferencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            destinatario TEXT NOT NULL,
            concepto TEXT,
            monto REAL NOT NULL DEFAULT 0,
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transferencias_fecha ON transferencias(fecha)')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CREDITOS_PUNTEADOS
    # Registra las facturas marcadas como crédito punteado
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS creditos_punteados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            folio INTEGER NOT NULL,
            cliente TEXT,
            subtotal REAL DEFAULT 0,
            repartidor TEXT,
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fecha, folio)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_creditos_punteados_fecha ON creditos_punteados(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_creditos_punteados_folio ON creditos_punteados(folio)')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CORTE_CAJERO
    # Guarda los datos del Corte Cajero de Eleventa por turno y fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS corte_cajero (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            turno_id INTEGER NOT NULL,
            -- Dinero en Caja
            fondo_de_caja REAL DEFAULT 0,
            ventas_en_efectivo REAL DEFAULT 0,
            abonos_en_efectivo REAL DEFAULT 0,
            entradas REAL DEFAULT 0,
            salidas REAL DEFAULT 0,
            devoluciones_en_efectivo REAL DEFAULT 0,
            total_dinero_caja REAL DEFAULT 0,
            -- Ventas
            ventas_efectivo REAL DEFAULT 0,
            ventas_tarjeta REAL DEFAULT 0,
            ventas_credito REAL DEFAULT 0,
            ventas_vales REAL DEFAULT 0,
            devoluciones_ventas REAL DEFAULT 0,
            total_ventas REAL DEFAULT 0,
            -- Devoluciones por forma de pago
            dev_efectivo REAL DEFAULT 0,
            dev_credito REAL DEFAULT 0,
            dev_tarjeta REAL DEFAULT 0,
            -- Ganancia
            ganancia REAL DEFAULT 0,
            -- Metadatos
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fecha, turno_id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_corte_cajero_fecha ON corte_cajero(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_corte_cajero_turno ON corte_cajero(turno_id)')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: CANCELACIONES_DETALLE
    # Guarda el detalle de cada cancelación: folio, ticket_id, cajero que canceló
    # Extraído de la tabla DEVOLUCIONES de Firebird (PDVDATA.FDB)
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cancelaciones_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            folio INTEGER NOT NULL,
            ticket_id INTEGER NOT NULL,
            cajero_cancelo TEXT NOT NULL,
            monto REAL DEFAULT 0,
            fecha_cancelacion DATE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fecha, folio)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cancelaciones_detalle_fecha ON cancelaciones_detalle(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cancelaciones_detalle_folio ON cancelaciones_detalle(folio)')
    
    # ══════════════════════════════════════════════════════════════════
    # TABLA: TOTALES_CANCELACIONES_EFECTIVO
    # Guarda el total de cancelaciones en efectivo por cajero (CAJERO o ADMIN) por fecha
    # ══════════════════════════════════════════════════════════════════
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS totales_cancelaciones_efectivo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            cajero TEXT NOT NULL,
            total_efectivo REAL DEFAULT 0,
            num_cancelaciones INTEGER DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fecha, cajero)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_totales_canc_efectivo_fecha ON totales_cancelaciones_efectivo(fecha)')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Base de datos inicializada en: {DB_PATH}")


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA CANCELACIONES DETALLE (cajero que canceló cada factura)
# ══════════════════════════════════════════════════════════════════════════════

def guardar_cancelacion_detalle(fecha: str, folio: int, ticket_id: int, cajero_cancelo: str, monto: float = 0, fecha_cancelacion: str = None) -> bool:
    """Guarda el detalle de una cancelación: quién la canceló (CAJERO o ADMIN)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cancelaciones_detalle (fecha, folio, ticket_id, cajero_cancelo, monto, fecha_cancelacion)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(fecha, folio) DO UPDATE SET
                ticket_id = excluded.ticket_id,
                cajero_cancelo = excluded.cajero_cancelo,
                monto = excluded.monto,
                fecha_cancelacion = excluded.fecha_cancelacion
        ''', (fecha, folio, ticket_id, cajero_cancelo.upper(), monto, fecha_cancelacion))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando cancelación detalle: {e}")
        return False


def guardar_cancelaciones_detalle_lote(fecha: str, cancelaciones: list) -> bool:
    """Guarda múltiples cancelaciones en lote.
    
    Args:
        fecha: Fecha de consulta
        cancelaciones: Lista de dicts con: folio, ticket_id, cajero_cancelo, monto, fecha_cancelacion
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for canc in cancelaciones:
            cursor.execute('''
                INSERT INTO cancelaciones_detalle (fecha, folio, ticket_id, cajero_cancelo, monto, fecha_cancelacion)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(fecha, folio) DO UPDATE SET
                    ticket_id = excluded.ticket_id,
                    cajero_cancelo = excluded.cajero_cancelo,
                    monto = excluded.monto,
                    fecha_cancelacion = excluded.fecha_cancelacion
            ''', (
                fecha,
                canc.get('folio', 0),
                canc.get('ticket_id', 0),
                canc.get('cajero_cancelo', '').upper(),
                canc.get('monto', 0),
                canc.get('fecha_cancelacion')
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando cancelaciones en lote: {e}")
        return False


def obtener_cajero_cancelo(fecha: str, folio: int) -> Optional[str]:
    """Obtiene el cajero que canceló una factura específica."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT cajero_cancelo FROM cancelaciones_detalle
        WHERE fecha = ? AND folio = ?
    ''', (fecha, folio))
    row = cursor.fetchone()
    conn.close()
    return row['cajero_cancelo'] if row else None


def obtener_cancelaciones_detalle_fecha(fecha: str) -> Dict[int, dict]:
    """Obtiene todas las cancelaciones de una fecha como dict {folio: {cajero_cancelo, monto, ...}}."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT folio, ticket_id, cajero_cancelo, monto, fecha_cancelacion
        FROM cancelaciones_detalle
        WHERE fecha = ?
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return {
        row['folio']: {
            'ticket_id': row['ticket_id'],
            'cajero_cancelo': row['cajero_cancelo'],
            'monto': row['monto'],
            'fecha_cancelacion': row['fecha_cancelacion']
        }
        for row in rows
    }


def obtener_cajeros_cancelaron_fecha(fecha: str) -> Dict[int, str]:
    """Obtiene un mapa de folio -> cajero que canceló para una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT folio, cajero_cancelo FROM cancelaciones_detalle
        WHERE fecha = ?
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return {row['folio']: row['cajero_cancelo'] for row in rows}


def limpiar_cancelaciones_detalle_fecha(fecha: str) -> bool:
    """Elimina todas las cancelaciones detalle de una fecha."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cancelaciones_detalle WHERE fecha = ?', (fecha,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error limpiando cancelaciones detalle: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA TOTALES DE CANCELACIONES EN EFECTIVO POR CAJERO
# ══════════════════════════════════════════════════════════════════════════════

def guardar_totales_cancelaciones_efectivo(fecha: str, totales_por_cajero: dict) -> bool:
    """Guarda los totales de cancelaciones en efectivo por cajero (CAJERO, ADMIN).
    
    Args:
        fecha: Fecha de las cancelaciones
        totales_por_cajero: Dict {'CAJERO': total, 'ADMIN': total}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        for cajero, total in totales_por_cajero.items():
            # Contar cuántas cancelaciones hay para este cajero en cancelaciones_detalle
            cursor.execute('''
                SELECT COUNT(*) as num FROM cancelaciones_detalle
                WHERE fecha = ? AND cajero_cancelo = ?
            ''', (fecha, cajero))
            row = cursor.fetchone()
            num_cancelaciones = row['num'] if row else 0
            
            cursor.execute('''
                INSERT INTO totales_cancelaciones_efectivo 
                (fecha, cajero, total_efectivo, num_cancelaciones, fecha_modificacion)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(fecha, cajero) DO UPDATE SET
                    total_efectivo = excluded.total_efectivo,
                    num_cancelaciones = excluded.num_cancelaciones,
                    fecha_modificacion = CURRENT_TIMESTAMP
            ''', (fecha, cajero.upper(), total, num_cancelaciones))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando totales cancelaciones efectivo: {e}")
        return False


def obtener_totales_cancelaciones_efectivo(fecha: str) -> dict:
    """Obtiene los totales de cancelaciones en efectivo por cajero para una fecha.
    
    Returns:
        Dict {'CAJERO': {'total': X, 'num': N}, 'ADMIN': {'total': X, 'num': N}}
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT cajero, total_efectivo, num_cancelaciones
        FROM totales_cancelaciones_efectivo
        WHERE fecha = ?
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    
    return {
        row['cajero']: {
            'total': row['total_efectivo'],
            'num': row['num_cancelaciones']
        }
        for row in rows
    }


def obtener_total_cancelaciones_cajero(fecha: str, cajero: str) -> float:
    """Obtiene el total de cancelaciones en efectivo para un cajero específico."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT total_efectivo FROM totales_cancelaciones_efectivo
        WHERE fecha = ? AND cajero = ?
    ''', (fecha, cajero.upper()))
    row = cursor.fetchone()
    conn.close()
    return row['total_efectivo'] if row else 0.0# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA ASIGNACIONES
# ══════════════════════════════════════════════════════════════════════════════

def guardar_asignacion(fecha: str, folio: int, repartidor: str) -> bool:
    """Guarda o actualiza una asignación de factura a repartidor."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO asignaciones (fecha, folio, repartidor, fecha_modificacion)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(fecha, folio) DO UPDATE SET
                repartidor = excluded.repartidor,
                fecha_modificacion = CURRENT_TIMESTAMP
        ''', (fecha, folio, repartidor))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando asignación: {e}")
        return False


def obtener_asignacion(fecha: str, folio: int) -> Optional[str]:
    """Obtiene el repartidor asignado a una factura."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT repartidor FROM asignaciones
        WHERE fecha = ? AND folio = ?
    ''', (fecha, folio))
    row = cursor.fetchone()
    conn.close()
    return row['repartidor'] if row else None


def obtener_asignaciones_fecha(fecha: str) -> Dict[int, str]:
    """Obtiene todas las asignaciones de una fecha como dict {folio: repartidor}."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT folio, repartidor FROM asignaciones
        WHERE fecha = ?
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return {row['folio']: row['repartidor'] for row in rows}


def eliminar_asignacion(fecha: str, folio: int) -> bool:
    """Elimina una asignación específica."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM asignaciones WHERE fecha = ? AND folio = ?', (fecha, folio))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando asignación: {e}")
        return False


def limpiar_asignaciones_fecha(fecha: str) -> bool:
    """Elimina todas las asignaciones de una fecha."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM asignaciones WHERE fecha = ?', (fecha,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error limpiando asignaciones: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA DESCUENTOS
# ══════════════════════════════════════════════════════════════════════════════

def agregar_descuento(fecha: str, folio: int, tipo: str, monto: float, 
                      repartidor: str = '', observacion: str = '',
                      cliente: str = '', articulo: str = '',
                      precio_facturado: float = 0, precio_nuevo: float = 0,
                      cantidad: float = 0) -> int:
    """Agrega un nuevo descuento. Retorna el ID del descuento creado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO descuentos (fecha, folio, tipo, monto, repartidor, observacion,
                                    cliente, articulo, precio_facturado, precio_nuevo, cantidad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha, folio, tipo, monto, repartidor, observacion,
              cliente, articulo, precio_facturado, precio_nuevo, cantidad))
        conn.commit()
        desc_id = cursor.lastrowid
        conn.close()
        return desc_id
    except Exception as e:
        print(f"Error agregando descuento: {e}")
        return -1


def obtener_descuentos_folio(folio: int) -> List[Dict]:
    """Obtiene todos los descuentos de un folio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM descuentos WHERE folio = ?
        ORDER BY fecha_creacion DESC
    ''', (folio,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_descuentos_fecha(fecha: str) -> List[Dict]:
    """Obtiene todos los descuentos de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM descuentos WHERE fecha = ?
        ORDER BY folio, fecha_creacion
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_descuentos_repartidor(fecha: str, repartidor: str) -> List[Dict]:
    """Obtiene los descuentos de un repartidor en una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM descuentos 
        WHERE fecha = ? AND repartidor = ?
        ORDER BY folio
    ''', (fecha, repartidor))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def eliminar_descuento(descuento_id: int) -> bool:
    """Elimina un descuento por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM descuentos WHERE id = ?', (descuento_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando descuento: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA GASTOS
# ══════════════════════════════════════════════════════════════════════════════

def agregar_gasto(fecha: str, repartidor: str, concepto: str, monto: float, observaciones: str = '') -> int:
    """Agrega un nuevo gasto. Retorna el ID del gasto creado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gastos (fecha, repartidor, concepto, monto, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (fecha, repartidor, concepto, monto, observaciones))
        conn.commit()
        gasto_id = cursor.lastrowid
        conn.close()
        return gasto_id
    except Exception as e:
        print(f"Error agregando gasto: {e}")
        return -1


def obtener_gastos_repartidor(fecha: str, repartidor: str) -> List[Dict]:
    """Obtiene los gastos de un repartidor en una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM gastos 
        WHERE fecha = ? AND repartidor = ?
        ORDER BY fecha_creacion
    ''', (fecha, repartidor))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_gastos_fecha(fecha: str) -> List[Dict]:
    """Obtiene todos los gastos de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM gastos WHERE fecha = ?
        ORDER BY repartidor, fecha_creacion
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def eliminar_gasto(gasto_id: int) -> bool:
    """Elimina un gasto por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM gastos WHERE id = ?', (gasto_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando gasto: {e}")
        return False


def actualizar_gasto(gasto_id: int, repartidor: str, concepto: str, monto: float, observaciones: str = '') -> bool:
    """Actualiza un gasto existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE gastos 
            SET repartidor = ?, concepto = ?, monto = ?, observaciones = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (repartidor, concepto, monto, observaciones, gasto_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando gasto: {e}")
        return False


def obtener_gasto_por_id(gasto_id: int) -> Optional[Dict]:
    """Obtiene un gasto por su ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM gastos WHERE id = ?', (gasto_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA CONTEO DE DINERO
# ══════════════════════════════════════════════════════════════════════════════

def guardar_conteo_dinero(fecha: str, repartidor: str, conteo: Dict[int, int]) -> bool:
    """
    Guarda el conteo de dinero de un repartidor.
    conteo = {denominacion: cantidad, ...} ej: {1000: 5, 500: 3, 200: 2, ...}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        for denominacion, cantidad in conteo.items():
            cursor.execute('''
                INSERT INTO conteo_dinero (fecha, repartidor, denominacion, cantidad, fecha_modificacion)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(fecha, repartidor, denominacion) DO UPDATE SET
                    cantidad = excluded.cantidad,
                    fecha_modificacion = CURRENT_TIMESTAMP
            ''', (fecha, repartidor, denominacion, cantidad))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando conteo: {e}")
        return False


def obtener_conteo_dinero(fecha: str, repartidor: str) -> Dict[int, int]:
    """Obtiene el conteo de dinero de un repartidor como dict {denominacion: cantidad}."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT denominacion, cantidad FROM conteo_dinero
        WHERE fecha = ? AND repartidor = ?
    ''', (fecha, repartidor))
    rows = cursor.fetchall()
    conn.close()
    return {row['denominacion']: row['cantidad'] for row in rows}


def obtener_total_dinero(fecha: str, repartidor: str) -> float:
    """Calcula el total de dinero de un repartidor."""
    conteo = obtener_conteo_dinero(fecha, repartidor)
    return sum(denom * cant for denom, cant in conteo.items())


def obtener_resumen_conteos_fecha(fecha: str) -> list:
    """
    Obtiene un resumen de todos los conteos de dinero para una fecha.
    Retorna lista de dicts: [{'repartidor': 'X', 'total': Y}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT repartidor, SUM(denominacion * cantidad) as total
        FROM conteo_dinero
        WHERE fecha = ?
        GROUP BY repartidor
        ORDER BY repartidor
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [{'repartidor': row['repartidor'], 'total': row['total'] or 0} for row in rows]


def obtener_detalle_conteo_repartidor(fecha: str, repartidor: str) -> list:
    """
    Obtiene el detalle del conteo de un repartidor en una fecha.
    Retorna lista de dicts con denominacion, cantidad y subtotal.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT denominacion, cantidad, (denominacion * cantidad) as subtotal
        FROM conteo_dinero
        WHERE fecha = ? AND repartidor = ?
        ORDER BY denominacion DESC
    ''', (fecha, repartidor))
    rows = cursor.fetchall()
    conn.close()
    return [{'denominacion': row['denominacion'], 'cantidad': row['cantidad'], 'subtotal': row['subtotal']} for row in rows]


def actualizar_repartidor_conteo(fecha: str, repartidor_viejo: str, repartidor_nuevo: str) -> bool:
    """Actualiza el nombre del repartidor en un conteo de dinero."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE conteo_dinero 
            SET repartidor = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE fecha = ? AND repartidor = ?
        ''', (repartidor_nuevo, fecha, repartidor_viejo))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando repartidor conteo: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA CONTEOS MÚLTIPLES (SESIONES)
# Permite guardar varios conteos por repartidor en un mismo día
# ══════════════════════════════════════════════════════════════════════════════

def guardar_conteo_sesion(fecha: str, repartidor: str, conteo: Dict[int, int], 
                          descripcion: str = '', hora: str = '') -> Optional[int]:
    """
    Guarda una nueva sesión de conteo para un repartidor.
    Retorna el ID de la sesión creada o None si hay error.
    conteo = {denominacion: cantidad, ...} ej: {1000: 5, 500: 3, 200: 2, ...}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calcular total
        total = sum(denom * cant for denom, cant in conteo.items())
        
        # Hora automática si no se proporciona
        if not hora:
            hora = datetime.now().strftime('%H:%M')
        
        # Insertar sesión
        cursor.execute('''
            INSERT INTO conteos_sesion (fecha, repartidor, descripcion, hora, total, fecha_modificacion)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (fecha, repartidor, descripcion, hora, total))
        
        sesion_id = cursor.lastrowid
        
        # Insertar detalles
        for denominacion, cantidad in conteo.items():
            if cantidad > 0:  # Solo guardar denominaciones con cantidad > 0
                cursor.execute('''
                    INSERT INTO conteos_sesion_detalle (sesion_id, denominacion, cantidad)
                    VALUES (?, ?, ?)
                ''', (sesion_id, denominacion, cantidad))
        
        conn.commit()
        conn.close()
        return sesion_id
    except Exception as e:
        print(f"Error guardando conteo sesión: {e}")
        return None


def actualizar_conteo_sesion(sesion_id: int, conteo: Dict[int, int], 
                             descripcion: str = None) -> bool:
    """
    Actualiza una sesión de conteo existente.
    conteo = {denominacion: cantidad, ...}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calcular nuevo total
        total = sum(denom * cant for denom, cant in conteo.items())
        
        # Actualizar sesión
        if descripcion is not None:
            cursor.execute('''
                UPDATE conteos_sesion 
                SET total = ?, descripcion = ?, fecha_modificacion = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (total, descripcion, sesion_id))
        else:
            cursor.execute('''
                UPDATE conteos_sesion 
                SET total = ?, fecha_modificacion = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (total, sesion_id))
        
        # Eliminar detalles anteriores
        cursor.execute('DELETE FROM conteos_sesion_detalle WHERE sesion_id = ?', (sesion_id,))
        
        # Insertar nuevos detalles
        for denominacion, cantidad in conteo.items():
            if cantidad > 0:
                cursor.execute('''
                    INSERT INTO conteos_sesion_detalle (sesion_id, denominacion, cantidad)
                    VALUES (?, ?, ?)
                ''', (sesion_id, denominacion, cantidad))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando conteo sesión: {e}")
        return False


def eliminar_conteo_sesion(sesion_id: int) -> bool:
    """Elimina una sesión de conteo y sus detalles."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Eliminar detalles primero
        cursor.execute('DELETE FROM conteos_sesion_detalle WHERE sesion_id = ?', (sesion_id,))
        # Eliminar sesión
        cursor.execute('DELETE FROM conteos_sesion WHERE id = ?', (sesion_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando conteo sesión: {e}")
        return False


def obtener_conteos_sesion_repartidor(fecha: str, repartidor: str) -> List[Dict]:
    """
    Obtiene todas las sesiones de conteo de un repartidor en una fecha.
    Retorna lista de dicts: [{'id': X, 'hora': 'HH:MM', 'descripcion': '', 'total': Y}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, hora, descripcion, total, fecha_creacion
        FROM conteos_sesion
        WHERE fecha = ? AND repartidor = ?
        ORDER BY fecha_creacion ASC
    ''', (fecha, repartidor))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': row['id'], 'hora': row['hora'], 'descripcion': row['descripcion'], 
             'total': row['total'], 'fecha_creacion': row['fecha_creacion']} for row in rows]


def obtener_detalle_conteo_sesion(sesion_id: int) -> Dict[int, int]:
    """
    Obtiene el detalle de una sesión de conteo.
    Retorna dict {denominacion: cantidad, ...}
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT denominacion, cantidad 
        FROM conteos_sesion_detalle
        WHERE sesion_id = ?
    ''', (sesion_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row['denominacion']: row['cantidad'] for row in rows}


def obtener_total_conteos_repartidor(fecha: str, repartidor: str) -> float:
    """
    Calcula el total de TODOS los conteos de un repartidor en una fecha.
    Suma todos los totales de las sesiones.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(total), 0) as total
        FROM conteos_sesion
        WHERE fecha = ? AND repartidor = ?
    ''', (fecha, repartidor))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def obtener_resumen_conteos_multiples_fecha(fecha: str) -> List[Dict]:
    """
    Obtiene un resumen de todos los conteos (sesiones) por repartidor para una fecha.
    Retorna lista de dicts: [{'repartidor': 'X', 'num_conteos': N, 'total': Y}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT repartidor, COUNT(*) as num_conteos, SUM(total) as total
        FROM conteos_sesion
        WHERE fecha = ?
        GROUP BY repartidor
        ORDER BY repartidor
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [{'repartidor': row['repartidor'], 'num_conteos': row['num_conteos'], 
             'total': row['total'] or 0} for row in rows]


def obtener_total_general_conteos_fecha(fecha: str) -> float:
    """
    Calcula el total general de TODOS los conteos de TODOS los repartidores en una fecha.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(total), 0) as total
        FROM conteos_sesion
        WHERE fecha = ?
    ''', (fecha,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def actualizar_repartidor_conteo_sesion(sesion_id: int, nuevo_repartidor: str) -> bool:
    """Actualiza el repartidor de una sesión de conteo específica."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE conteos_sesion 
            SET repartidor = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (nuevo_repartidor, sesion_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando repartidor sesión: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA REPARTIDORES
# ══════════════════════════════════════════════════════════════════════════════

def agregar_repartidor(nombre: str, telefono: str = '', notas: str = '') -> bool:
    """Agrega un nuevo repartidor a la lista."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO repartidores (nombre, telefono, notas)
            VALUES (?, ?, ?)
        ''', (nombre, telefono, notas))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Ya existe
        return False
    except Exception as e:
        print(f"Error agregando repartidor: {e}")
        return False


def obtener_repartidores_activos() -> List[str]:
    """Obtiene la lista de repartidores activos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT nombre FROM repartidores WHERE activo = 1 ORDER BY nombre')
    rows = cursor.fetchall()
    conn.close()
    return [row['nombre'] for row in rows]


def desactivar_repartidor(nombre: str) -> bool:
    """Desactiva un repartidor (no lo elimina)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE repartidores SET activo = 0 WHERE nombre = ?', (nombre,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error desactivando repartidor: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def guardar_config(clave: str, valor: Any) -> bool:
    """Guarda una configuración (convierte a JSON si es necesario)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        valor_str = json.dumps(valor) if not isinstance(valor, str) else valor
        cursor.execute('''
            INSERT INTO configuracion (clave, valor, fecha_modificacion)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(clave) DO UPDATE SET
                valor = excluded.valor,
                fecha_modificacion = CURRENT_TIMESTAMP
        ''', (clave, valor_str))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando config: {e}")
        return False


def obtener_config(clave: str, default: Any = None) -> Any:
    """Obtiene una configuración."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', (clave,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return default
    
    try:
        return json.loads(row['valor'])
    except (json.JSONDecodeError, TypeError):
        return row['valor']


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA DEVOLUCIONES PARCIALES
# ══════════════════════════════════════════════════════════════════════════════

def guardar_devolucion_parcial(fecha: str, folio: int, devolucion_id: int,
                                codigo: str, descripcion: str, cantidad: float,
                                valor_unitario: float, dinero: float, 
                                fecha_devolucion: str = None) -> int:
    """Guarda un registro de devolución parcial de artículo.
    
    Args:
        fecha: Fecha de la venta original
        folio: Número de folio de la factura
        devolucion_id: ID de la devolución en Firebird
        codigo: Código del producto
        descripcion: Descripción del producto
        cantidad: Cantidad devuelta
        valor_unitario: Valor unitario del artículo
        dinero: Total devuelto (cantidad * valor_unitario)
        fecha_devolucion: Fecha en que se realizó la devolución
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO devoluciones_parciales 
            (fecha, folio, devolucion_id, codigo_producto, descripcion_producto,
             cantidad_devuelta, valor_unitario, dinero_devuelto, fecha_devolucion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha, folio, devolucion_id, codigo, descripcion, cantidad, 
              valor_unitario, dinero, fecha_devolucion))
        conn.commit()
        dev_id = cursor.lastrowid
        conn.close()
        return dev_id
    except Exception as e:
        print(f"Error guardando devolución parcial: {e}")
        return -1


def obtener_devoluciones_parciales_folio(folio: int) -> List[Dict]:
    """Obtiene las devoluciones parciales de un folio específico."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM devoluciones_parciales 
        WHERE folio = ?
        ORDER BY fecha_creacion
    ''', (folio,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_devoluciones_parciales_fecha(fecha: str) -> List[Dict]:
    """Obtiene todas las devoluciones parciales de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM devoluciones_parciales 
        WHERE fecha = ?
        ORDER BY folio, fecha_creacion
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_total_devoluciones_parciales_folio(folio: int) -> float:
    """Obtiene el total de dinero devuelto para un folio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(dinero_devuelto), 0) as total
        FROM devoluciones_parciales 
        WHERE folio = ?
    ''', (folio,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def obtener_total_devoluciones_parciales_fecha(fecha: str) -> float:
    """Obtiene el total de devoluciones parciales de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(dinero_devuelto), 0) as total
        FROM devoluciones_parciales 
        WHERE fecha = ?
    ''', (fecha,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def obtener_devoluciones_parciales_por_folio_fecha(fecha: str) -> Dict[int, float]:
    """Obtiene un diccionario con el total de devoluciones parciales por folio para una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT folio, SUM(dinero_devuelto) as total
        FROM devoluciones_parciales 
        WHERE fecha = ?
        GROUP BY folio
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return {row['folio']: row['total'] for row in rows}


def obtener_detalle_devoluciones_por_fecha(fecha: str) -> Dict[int, List[Dict]]:
    """Obtiene el detalle de artículos devueltos agrupados por folio para una fecha.
    Retorna: {folio: [{codigo, articulo, cantidad, valor_unitario, dinero}, ...]}"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT folio, codigo_producto, descripcion_producto, 
               cantidad_devuelta, valor_unitario, dinero_devuelto
        FROM devoluciones_parciales 
        WHERE fecha = ?
        ORDER BY folio, id
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    
    result: Dict[int, List[Dict]] = {}
    for row in rows:
        folio = row['folio']
        if folio not in result:
            result[folio] = []
        result[folio].append({
            "codigo": row['codigo_producto'] or "—",
            "articulo": row['descripcion_producto'] or "Sin descripción",
            "cantidad": row['cantidad_devuelta'] or 0,
            "valor_unitario": row['valor_unitario'] or 0,
            "dinero": row['dinero_devuelto'] or 0
        })
    return result


def limpiar_devoluciones_parciales_fecha(fecha: str) -> bool:
    """Limpia las devoluciones parciales de una fecha (para recargar)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM devoluciones_parciales WHERE fecha = ?', (fecha,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error limpiando devoluciones: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA PAGO A PROVEEDORES
# ══════════════════════════════════════════════════════════════════════════════

def agregar_pago_proveedor(fecha: str, proveedor: str, concepto: str, monto: float, 
                           repartidor: str = '', observaciones: str = '') -> int:
    """Agrega un nuevo pago a proveedor. Retorna el ID del pago creado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pago_proveedores (fecha, proveedor, concepto, monto, repartidor, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fecha, proveedor, concepto, monto, repartidor, observaciones))
        conn.commit()
        pago_id = cursor.lastrowid
        conn.close()
        return pago_id
    except Exception as e:
        print(f"Error agregando pago proveedor: {e}")
        return -1


def obtener_pagos_proveedores_fecha(fecha: str) -> List[Dict]:
    """Obtiene todos los pagos a proveedores de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM pago_proveedores WHERE fecha = ?
        ORDER BY fecha_creacion
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_pagos_proveedores_repartidor(fecha: str, repartidor: str) -> List[Dict]:
    """Obtiene los pagos a proveedores de un repartidor en una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM pago_proveedores 
        WHERE fecha = ? AND (repartidor = ? OR repartidor IS NULL OR repartidor = '')
        ORDER BY fecha_creacion
    ''', (fecha, repartidor))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_total_pagos_proveedores_fecha(fecha: str, repartidor: str = '') -> float:
    """Obtiene el total de pagos a proveedores de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    if repartidor:
        cursor.execute('''
            SELECT COALESCE(SUM(monto), 0) as total
            FROM pago_proveedores 
            WHERE fecha = ? AND (repartidor = ? OR repartidor IS NULL OR repartidor = '')
        ''', (fecha, repartidor))
    else:
        cursor.execute('''
            SELECT COALESCE(SUM(monto), 0) as total
            FROM pago_proveedores 
            WHERE fecha = ?
        ''', (fecha,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def eliminar_pago_proveedor(pago_id: int) -> bool:
    """Elimina un pago a proveedor por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pago_proveedores WHERE id = ?', (pago_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando pago proveedor: {e}")
        return False


def actualizar_pago_proveedor(pago_id: int, proveedor: str, concepto: str, 
                               monto: float, repartidor: str = '', observaciones: str = '') -> bool:
    """Actualiza un pago a proveedor existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pago_proveedores 
            SET proveedor = ?, concepto = ?, monto = ?, repartidor = ?, observaciones = ?,
                fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (proveedor, concepto, monto, repartidor, observaciones, pago_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando pago proveedor: {e}")
        return False


def obtener_pago_proveedor_por_id(pago_id: int) -> Optional[Dict]:
    """Obtiene un pago a proveedor por su ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pago_proveedores WHERE id = ?', (pago_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA PRÉSTAMOS
# ══════════════════════════════════════════════════════════════════════════════

def agregar_prestamo(fecha: str, repartidor: str, concepto: str, monto: float,
                     observaciones: str = '', estado: str = 'pendiente') -> int:
    """Agrega un nuevo préstamo. Retorna el ID del préstamo creado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO prestamos (fecha, repartidor, concepto, monto, estado, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fecha, repartidor, concepto, monto, estado, observaciones))
        conn.commit()
        prestamo_id = cursor.lastrowid
        conn.close()
        return prestamo_id
    except Exception as e:
        print(f"Error agregando préstamo: {e}")
        return -1


def obtener_prestamos_fecha(fecha: str) -> List[Dict]:
    """Obtiene todos los préstamos de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM prestamos WHERE fecha = ?
        ORDER BY fecha_creacion
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_prestamos_repartidor(fecha: str, repartidor: str) -> List[Dict]:
    """Obtiene los préstamos de un repartidor en una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM prestamos 
        WHERE fecha = ? AND repartidor = ?
        ORDER BY fecha_creacion
    ''', (fecha, repartidor))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_total_prestamos_fecha(fecha: str, repartidor: str = '') -> float:
    """Obtiene el total de préstamos de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    if repartidor:
        cursor.execute('''
            SELECT COALESCE(SUM(monto), 0) as total
            FROM prestamos 
            WHERE fecha = ? AND repartidor = ?
        ''', (fecha, repartidor))
    else:
        cursor.execute('''
            SELECT COALESCE(SUM(monto), 0) as total
            FROM prestamos 
            WHERE fecha = ?
        ''', (fecha,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def eliminar_prestamo(prestamo_id: int) -> bool:
    """Elimina un préstamo por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM prestamos WHERE id = ?', (prestamo_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando préstamo: {e}")
        return False


def actualizar_prestamo(prestamo_id: int, repartidor: str, concepto: str, monto: float, observaciones: str = '') -> bool:
    """Actualiza un préstamo existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE prestamos 
            SET repartidor = ?, concepto = ?, monto = ?, observaciones = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (repartidor, concepto, monto, observaciones, prestamo_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando préstamo: {e}")
        return False


def actualizar_estado_prestamo(prestamo_id: int, estado: str) -> bool:
    """Actualiza el estado de un préstamo."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE prestamos 
            SET estado = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (estado, prestamo_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando préstamo: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA HISTORIAL DE LIQUIDACIONES
# ══════════════════════════════════════════════════════════════════════════════

def guardar_liquidacion(fecha: str, repartidor: str, datos: Dict) -> int:
    """Guarda una liquidación en el historial."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO historial_liquidaciones 
            (fecha, repartidor, total_ventas, total_descuentos, total_gastos, 
             total_dinero, neto, diferencia, datos_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fecha,
            repartidor,
            datos.get('total_ventas', 0),
            datos.get('total_descuentos', 0),
            datos.get('total_gastos', 0),
            datos.get('total_dinero', 0),
            datos.get('neto', 0),
            datos.get('diferencia', 0),
            json.dumps(datos)
        ))
        conn.commit()
        liq_id = cursor.lastrowid
        conn.close()
        return liq_id
    except Exception as e:
        print(f"Error guardando liquidación: {e}")
        return -1


def obtener_historial_liquidaciones(fecha: str = None, repartidor: str = None) -> List[Dict]:
    """Obtiene el historial de liquidaciones con filtros opcionales."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM historial_liquidaciones WHERE 1=1'
    params = []
    
    if fecha:
        query += ' AND fecha = ?'
        params.append(fecha)
    if repartidor:
        query += ' AND repartidor = ?'
        params.append(repartidor)
    
    query += ' ORDER BY fecha_generacion DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE MIGRACIÓN (JSON a SQLite)
# ══════════════════════════════════════════════════════════════════════════════

def migrar_desde_json():
    """Migra datos existentes de archivos JSON a la base de datos SQLite."""
    import os
    
    base_dir = os.path.dirname(__file__)
    
    # Migrar descuentos.json
    descuentos_file = os.path.join(base_dir, 'descuentos.json')
    if os.path.exists(descuentos_file):
        try:
            with open(descuentos_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conn = get_connection()
            cursor = conn.cursor()
            
            for folio_str, info in data.items():
                folio = int(folio_str)
                for desc in info.get('descuentos', []):
                    fecha = desc.get('fecha', '').split()[0] if desc.get('fecha') else ''
                    cursor.execute('''
                        INSERT OR IGNORE INTO descuentos 
                        (fecha, folio, tipo, monto, repartidor, observacion)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        fecha,
                        folio,
                        desc.get('tipo', 'ajuste'),
                        desc.get('monto', 0),
                        desc.get('repartidor', ''),
                        desc.get('observacion', '')
                    ))
            
            conn.commit()
            conn.close()
            print(f"✅ Migrados descuentos desde {descuentos_file}")
        except Exception as e:
            print(f"⚠️ Error migrando descuentos: {e}")
    
    # Migrar asignaciones (si existe el archivo)
    asignaciones_file = os.path.join(base_dir, 'asignaciones.json')
    if os.path.exists(asignaciones_file):
        try:
            with open(asignaciones_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conn = get_connection()
            cursor = conn.cursor()
            
            for key, repartidor in data.items():
                parts = key.split('_')
                if len(parts) >= 2:
                    fecha = parts[0]
                    folio = int(parts[1])
                    cursor.execute('''
                        INSERT OR IGNORE INTO asignaciones (fecha, folio, repartidor)
                        VALUES (?, ?, ?)
                    ''', (fecha, folio, repartidor))
            
            conn.commit()
            conn.close()
            print(f"✅ Migradas asignaciones desde {asignaciones_file}")
        except Exception as e:
            print(f"⚠️ Error migrando asignaciones: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA CONCEPTOS DE GASTOS
# ══════════════════════════════════════════════════════════════════════════════

def obtener_conceptos_gastos() -> List[str]:
    """Obtiene todos los conceptos de gastos guardados."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT concepto FROM conceptos_gastos ORDER BY concepto')
    conceptos = [row['concepto'] for row in cursor.fetchall()]
    conn.close()
    return conceptos


def agregar_concepto_gasto(concepto: str) -> bool:
    """Agrega un nuevo concepto. Retorna True si se agregó correctamente."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO conceptos_gastos (concepto) VALUES (?)', (concepto.upper(),))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def eliminar_concepto_gasto(concepto: str) -> bool:
    """Elimina un concepto."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM conceptos_gastos WHERE concepto = ?', (concepto,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA CRÉDITOS PUNTEADOS
# ══════════════════════════════════════════════════════════════════════════════

def agregar_credito_punteado(fecha: str, folio: int, cliente: str, subtotal: float, 
                              repartidor: str = '', observaciones: str = '') -> int:
    """Marca una factura como crédito punteado. Retorna el ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO creditos_punteados (fecha, folio, cliente, subtotal, repartidor, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(fecha, folio) DO UPDATE SET
                cliente = excluded.cliente,
                subtotal = excluded.subtotal,
                repartidor = excluded.repartidor,
                observaciones = excluded.observaciones
        ''', (fecha, folio, cliente, subtotal, repartidor, observaciones))
        conn.commit()
        credito_id = cursor.lastrowid
        conn.close()
        return credito_id
    except Exception as e:
        print(f"Error agregando crédito punteado: {e}")
        return -1


def eliminar_credito_punteado(fecha: str, folio: int) -> bool:
    """Elimina una factura de créditos punteados."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM creditos_punteados WHERE fecha = ? AND folio = ?', (fecha, folio))
        conn.commit()
        afectados = cursor.rowcount
        conn.close()
        return afectados > 0
    except Exception as e:
        print(f"Error eliminando crédito punteado: {e}")
        return False


def obtener_creditos_punteados_fecha(fecha: str) -> List[Dict]:
    """Obtiene todos los créditos punteados de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM creditos_punteados WHERE fecha = ?
        ORDER BY folio
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def es_credito_punteado(fecha: str, folio: int) -> bool:
    """Verifica si una factura está marcada como crédito punteado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM creditos_punteados WHERE fecha = ? AND folio = ?', (fecha, folio))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def obtener_total_creditos_punteados(fecha: str) -> float:
    """Obtiene el total de créditos punteados de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COALESCE(SUM(subtotal), 0) FROM creditos_punteados WHERE fecha = ?', (fecha,))
    total = cursor.fetchone()[0]
    conn.close()
    return total or 0.0


def obtener_total_creditos_punteados_por_folios(fecha: str, folios: list) -> float:
    """Obtiene el total de créditos punteados de una fecha filtrado por lista de folios."""
    if not folios:
        return 0.0
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(folios))
    cursor.execute(f'SELECT COALESCE(SUM(subtotal), 0) FROM creditos_punteados WHERE fecha = ? AND folio IN ({placeholders})', 
                   [fecha] + folios)
    total = cursor.fetchone()[0]
    conn.close()
    return total or 0.0


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA PAGO DE NÓMINA
# ══════════════════════════════════════════════════════════════════════════════

def agregar_pago_nomina(fecha: str, empleado: str, concepto: str, monto: float,
                        observaciones: str = '') -> int:
    """Agrega un nuevo pago de nómina. Retorna el ID creado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pago_nomina (fecha, empleado, concepto, monto, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (fecha, empleado, concepto, monto, observaciones))
        conn.commit()
        pago_id = cursor.lastrowid
        conn.close()
        return pago_id
    except Exception as e:
        print(f"Error agregando pago de nómina: {e}")
        return -1


def obtener_pagos_nomina_fecha(fecha: str) -> List[Dict]:
    """Obtiene todos los pagos de nómina de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM pago_nomina WHERE fecha = ?
        ORDER BY fecha_creacion
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_total_pagos_nomina_fecha(fecha: str) -> float:
    """Obtiene el total de pagos de nómina de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(monto), 0) as total
        FROM pago_nomina 
        WHERE fecha = ?
    ''', (fecha,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def eliminar_pago_nomina(pago_id: int) -> bool:
    """Elimina un pago de nómina por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pago_nomina WHERE id = ?', (pago_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando pago de nómina: {e}")
        return False


def actualizar_pago_nomina(pago_id: int, empleado: str, concepto: str, monto: float, observaciones: str = '') -> bool:
    """Actualiza un pago de nómina existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pago_nomina 
            SET empleado = ?, concepto = ?, monto = ?, observaciones = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (empleado, concepto, monto, observaciones, pago_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando pago de nómina: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA PAGO DE SOCIOS
# ══════════════════════════════════════════════════════════════════════════════

def agregar_pago_socios(fecha: str, socio: str, concepto: str, monto: float,
                        observaciones: str = '') -> int:
    """Agrega un nuevo pago a socios. Retorna el ID creado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pago_socios (fecha, socio, concepto, monto, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (fecha, socio, concepto, monto, observaciones))
        conn.commit()
        pago_id = cursor.lastrowid
        conn.close()
        return pago_id
    except Exception as e:
        print(f"Error agregando pago a socios: {e}")
        return -1


def obtener_pagos_socios_fecha(fecha: str) -> List[Dict]:
    """Obtiene todos los pagos a socios de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM pago_socios WHERE fecha = ?
        ORDER BY fecha_creacion
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_total_pagos_socios_fecha(fecha: str) -> float:
    """Obtiene el total de pagos a socios de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(monto), 0) as total
        FROM pago_socios 
        WHERE fecha = ?
    ''', (fecha,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def eliminar_pago_socios(pago_id: int) -> bool:
    """Elimina un pago a socios por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pago_socios WHERE id = ?', (pago_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando pago a socios: {e}")
        return False


def actualizar_pago_socios(pago_id: int, socio: str, concepto: str, monto: float, observaciones: str = '') -> bool:
    """Actualiza un pago a socios existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pago_socios 
            SET socio = ?, concepto = ?, monto = ?, observaciones = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (socio, concepto, monto, observaciones, pago_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando pago a socios: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA TRANSFERENCIAS
# ══════════════════════════════════════════════════════════════════════════════

def agregar_transferencia(fecha: str, destinatario: str, concepto: str, monto: float, observaciones: str = '') -> int:
    """Agrega una nueva transferencia. Retorna el ID del registro creado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transferencias (fecha, destinatario, concepto, monto, observaciones)
        VALUES (?, ?, ?, ?, ?)
    ''', (fecha, destinatario, concepto, monto, observaciones))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def obtener_transferencias_fecha(fecha: str) -> List[Dict[str, Any]]:
    """Obtiene las transferencias de una fecha específica."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, fecha, destinatario, concepto, monto, observaciones, fecha_creacion
        FROM transferencias 
        WHERE fecha = ?
        ORDER BY id DESC
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_total_transferencias_fecha(fecha: str) -> float:
    """Obtiene el total de transferencias de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(monto), 0) as total
        FROM transferencias 
        WHERE fecha = ?
    ''', (fecha,))
    row = cursor.fetchone()
    conn.close()
    return row['total'] if row else 0


def eliminar_transferencia(transferencia_id: int) -> bool:
    """Elimina una transferencia por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transferencias WHERE id = ?', (transferencia_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando transferencia: {e}")
        return False


def actualizar_transferencia(transferencia_id: int, destinatario: str, concepto: str, monto: float, observaciones: str = '') -> bool:
    """Actualiza una transferencia existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transferencias 
            SET destinatario = ?, concepto = ?, monto = ?, observaciones = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (destinatario, concepto, monto, observaciones, transferencia_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando transferencia: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PARA CORTE CAJERO (Eleventa)
# ══════════════════════════════════════════════════════════════════════════════

def guardar_corte_cajero(fecha: str, turno_id: int, datos: Dict[str, Any]) -> bool:
    """
    Guarda o actualiza los datos del Corte Cajero de Eleventa.
    
    Args:
        fecha: Fecha del corte (YYYY-MM-DD)
        turno_id: ID del turno en Eleventa
        datos: Diccionario con los datos del corte:
            - dinero_en_caja: dict con fondo_de_caja, ventas_en_efectivo, etc.
            - ventas: dict con ventas_efectivo, ventas_tarjeta, etc.
            - ganancia: float
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        dinero = datos.get('dinero_en_caja', {})
        ventas = datos.get('ventas', {})
        devs = datos.get('devoluciones_por_forma_pago', {})
        
        cursor.execute('''
            INSERT INTO corte_cajero (
                fecha, turno_id,
                fondo_de_caja, ventas_en_efectivo, abonos_en_efectivo, 
                entradas, salidas, devoluciones_en_efectivo, total_dinero_caja,
                ventas_efectivo, ventas_tarjeta, ventas_credito, ventas_vales,
                devoluciones_ventas, total_ventas,
                dev_efectivo, dev_credito, dev_tarjeta,
                ganancia, fecha_modificacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(fecha, turno_id) DO UPDATE SET
                fondo_de_caja = excluded.fondo_de_caja,
                ventas_en_efectivo = excluded.ventas_en_efectivo,
                abonos_en_efectivo = excluded.abonos_en_efectivo,
                entradas = excluded.entradas,
                salidas = excluded.salidas,
                devoluciones_en_efectivo = excluded.devoluciones_en_efectivo,
                total_dinero_caja = excluded.total_dinero_caja,
                ventas_efectivo = excluded.ventas_efectivo,
                ventas_tarjeta = excluded.ventas_tarjeta,
                ventas_credito = excluded.ventas_credito,
                ventas_vales = excluded.ventas_vales,
                devoluciones_ventas = excluded.devoluciones_ventas,
                total_ventas = excluded.total_ventas,
                dev_efectivo = excluded.dev_efectivo,
                dev_credito = excluded.dev_credito,
                dev_tarjeta = excluded.dev_tarjeta,
                ganancia = excluded.ganancia,
                fecha_modificacion = CURRENT_TIMESTAMP
        ''', (
            fecha, turno_id,
            dinero.get('fondo_de_caja', 0),
            dinero.get('ventas_en_efectivo', 0),
            dinero.get('abonos_en_efectivo', 0),
            dinero.get('entradas', 0),
            dinero.get('salidas', 0),
            dinero.get('devoluciones_en_efectivo', 0),
            dinero.get('total', 0),
            ventas.get('ventas_efectivo', 0),
            ventas.get('ventas_tarjeta', 0),
            ventas.get('ventas_credito', 0),
            ventas.get('ventas_vales', 0),
            ventas.get('devoluciones_ventas', 0),
            ventas.get('total', 0),
            devs.get('efectivo', 0),
            devs.get('credito', 0),
            devs.get('tarjeta', 0),
            datos.get('ganancia', 0)
        ))
        conn.commit()
        conn.close()
        print(f"✅ Corte Cajero guardado: Fecha={fecha}, Turno={turno_id}")
        return True
    except Exception as e:
        print(f"Error guardando corte cajero: {e}")
        return False


def obtener_corte_cajero(fecha: str, turno_id: int = None) -> Optional[Dict[str, Any]]:
    """
    Obtiene los datos del Corte Cajero de una fecha (y opcionalmente turno).
    Si no se especifica turno_id, devuelve el último turno de esa fecha.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if turno_id:
        cursor.execute('SELECT * FROM corte_cajero WHERE fecha = ? AND turno_id = ?', 
                       (fecha, turno_id))
    else:
        cursor.execute('''
            SELECT * FROM corte_cajero WHERE fecha = ? 
            ORDER BY turno_id DESC LIMIT 1
        ''', (fecha,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def obtener_cortes_cajero_fecha(fecha: str) -> List[Dict[str, Any]]:
    """Obtiene todos los cortes de caja de una fecha."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM corte_cajero WHERE fecha = ?
        ORDER BY turno_id
    ''', (fecha,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_ultimo_corte_cajero() -> Optional[Dict[str, Any]]:
    """Obtiene el último corte de caja guardado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM corte_cajero 
        ORDER BY fecha DESC, turno_id DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN AUTOMÁTICA
# ══════════════════════════════════════════════════════════════════════════════

# Inicializar la base de datos al importar el módulo
if not os.path.exists(DB_PATH):
    init_database()
    migrar_desde_json()
else:
    # Verificar que existan todas las tablas
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row['name'] for row in cursor.fetchall()}
    conn.close()
    
    required_tables = {'asignaciones', 'descuentos', 'gastos', 'conteo_dinero', 
                       'configuracion', 'repartidores', 'historial_liquidaciones',
                       'pago_proveedores', 'prestamos', 'devoluciones_parciales',
                       'conceptos_gastos', 'creditos_punteados', 'pago_nomina', 'pago_socios',
                       'transferencias', 'corte_cajero', 'conteos_sesion', 'conteos_sesion_detalle'}
    
    if not required_tables.issubset(tables):
        init_database()


if __name__ == '__main__':
    # Prueba de inicialización
    init_database()
    print(f"\n📁 Base de datos: {DB_PATH}")
    print("\n📋 Tablas creadas:")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for row in cursor.fetchall():
        print(f"   • {row['name']}")
    conn.close()
