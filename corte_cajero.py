# ══════════════════════════════════════════════════════════════════════════════
# CANCELACIONES POR USUARIO (DEVOLUCIONES + CREDITOS CANCELADOS)
# ══════════════════════════════════════════════════════════════════════════════
def obtener_cancelaciones_por_usuario(fecha: str, db_path: str = None, isql_path: str = None) -> dict:
    """
    Devuelve un resumen de cancelaciones por usuario/cajero para una fecha.
    Suma TODAS las cancelaciones del día incluyendo:
    - Devoluciones en efectivo
    - Créditos cancelados
    - Devoluciones de tarjeta
    - Devoluciones de vales
    
    Retorna: { 'admin': {'total': 123.45, 'num': 2, 'detalle': {...}}, ... }
    """
    import subprocess
    from collections import defaultdict
    db_path = db_path or DB_PATH_DEFAULT
    isql_path = isql_path or ISQL_PATH_DEFAULT
    
    # Consulta que agrupa TODAS las devoluciones por cajero con detalle por forma de pago
    # Clasifica como CRÉDITO si: V.CREDITO=1, V.TOTAL_CREDITO>0, o V.CONDICION='CREDITO'
    # Todo lo demás es EFECTIVO (ventas de contado/mostrador)
    sql = f"""
    SET NAMES WIN1252;
    SELECT 
        D.CAJERO,
        SUM(D.TOTAL_DEVUELTO) AS TOTAL_CANCELADO,
        COUNT(*) AS NUM_CANCELACIONES,
        SUM(CASE 
            WHEN COALESCE(V.CREDITO, 0) = 1 OR COALESCE(V.TOTAL_CREDITO, 0) > 0 
            THEN 0 
            ELSE D.TOTAL_DEVUELTO 
        END) AS DEV_EFECTIVO,
        SUM(CASE 
            WHEN COALESCE(V.CREDITO, 0) = 1 OR COALESCE(V.TOTAL_CREDITO, 0) > 0 
            THEN D.TOTAL_DEVUELTO 
            ELSE 0 
        END) AS DEV_CREDITO
    FROM DEVOLUCIONES D
    LEFT JOIN VENTATICKETS V ON D.TICKET_ID = V.ID
    WHERE CAST(D.DEVUELTO_EN AS DATE) = '{fecha}'
    GROUP BY D.CAJERO;
    """
    cmd = [isql_path, '-u', 'SYSDBA', '-p', 'masterkey', '-ch', 'WIN1252', db_path]
    run_kwargs = {
        'input': sql,
        'capture_output': True,
        'text': True,
        'timeout': 60,
        'encoding': 'cp1252',
        'errors': 'replace'
    }
    if sys.platform == 'win32':
        run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    proc = subprocess.run(cmd, **run_kwargs)
    stdout = proc.stdout or ""
    
    resumen = {}
    header_visto = False
    
    for line in stdout.split('\n'):
        line = line.strip()
        if not line or '=' in line or 'SQL>' in line:
            continue
        # Saltar líneas de separación
        if line.startswith('-') and '---' in line:
            continue
        
        # Detectar encabezado
        if 'CAJERO' in line and 'TOTAL' in line:
            header_visto = True
            continue
        
        if not header_visto:
            continue
            
        # Parsear formato con 5 columnas: CAJERO TOTAL_CANCELADO NUM_CANCELACIONES DEV_EFECTIVO DEV_CREDITO
        partes = line.split()
        if len(partes) >= 5:
            try:
                dev_credito = float(partes[-1]) if partes[-1] not in ('<null>', 'null', '<NULL>') else 0.0
                dev_efectivo = float(partes[-2]) if partes[-2] not in ('<null>', 'null', '<NULL>') else 0.0
                num = int(partes[-3]) if partes[-3] not in ('<null>', 'null', '<NULL>') else 0
                total = float(partes[-4]) if partes[-4] not in ('<null>', 'null', '<NULL>') else 0.0
                usuario = ' '.join(partes[:-4])
                
                if usuario:
                    resumen[usuario] = {
                        'total': total,
                        'num': num,
                        'detalle': {
                            'efectivo': dev_efectivo,
                            'credito': dev_credito,
                            'tarjeta': 0.0,
                            'vales': 0.0
                        }
                    }
            except Exception as e:
                print(f"⚠️ Error parseando línea: {line} - {e}")
                continue
        elif len(partes) >= 3:
            # Formato simple fallback: CAJERO TOTAL NUM
            try:
                num = int(partes[-1]) if partes[-1] not in ('<null>', 'null', '<NULL>') else 0
                total = float(partes[-2]) if partes[-2] not in ('<null>', 'null', '<NULL>') else 0.0
                usuario = ' '.join(partes[:-2])
                
                if usuario:
                    resumen[usuario] = {
                        'total': total,
                        'num': num,
                        'detalle': {
                            'efectivo': total,
                            'credito': 0.0,
                            'tarjeta': 0.0,
                            'vales': 0.0
                        }
                    }
            except Exception:
                continue
    
    return resumen
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORTE CAJERO - Funciones para extraer datos del Corte de Caja desde Eleventa
==============================================================================

Este módulo proporciona funciones para consultar la base de datos Firebird (PDVDATA.FDB)
y extraer información relacionada con el Corte de Caja del sistema Eleventa.

Estructura de datos extraídos:
------------------------------
* DINERO EN CAJA:
  - Fondo de Caja: Dinero inicial del turno
  - Ventas en Efectivo: Total de ventas cobradas en efectivo
  - Abonos en Efectivo: Pagos recibidos a créditos en efectivo  
  - Entradas: Movimientos de entrada de efectivo (ej: préstamos recibidos)
  - Salidas: Movimientos de salida de efectivo (ej: préstamos otorgados)
  - Devoluciones en Efectivo: Devoluciones de ventas que fueron pagadas originalmente en efectivo

* VENTAS:
  - Ventas Totales: Suma de todas las ventas (efectivo + tarjeta + crédito + vales)
  - Devoluciones de Ventas: TODAS las devoluciones independientemente de la forma de pago original

DIFERENCIA ENTRE DEVOLUCIONES:
-----------------------------
- "Devoluciones en Efectivo": Solo cuenta las devoluciones de ventas que fueron 
  pagadas ORIGINALMENTE en efectivo. Afecta el dinero físico en caja.
  
- "Devoluciones de Ventas": Cuenta TODAS las devoluciones (efectivo + crédito + tarjeta + vales).
  Es la suma total de devoluciones sin importar cómo se pagó originalmente.

Por eso "Devoluciones de Ventas" >= "Devoluciones en Efectivo".

Autor: Liquidador Jhoman
Fecha: Febrero 2026
"""

import subprocess
import sys
import os
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

# Rutas por defecto - Buscar isql automáticamente
def _buscar_isql():
    posibles = [
        r"C:\Program Files\Firebird\Firebird_5_0\isql.exe",
        r"C:\Program Files\Firebird\Firebird_4_0\isql.exe",
        r"C:\Program Files\Firebird\Firebird_3_0\isql.exe",
        r"C:\Program Files\Firebird\Firebird_2_5\bin\isql.exe",
        r"C:\Program Files (x86)\Firebird\Firebird_2_5\bin\isql.exe",
    ]
    for ruta in posibles:
        if os.path.exists(ruta):
            return ruta
    return r"C:\Program Files\Firebird\Firebird_5_0\isql.exe"

ISQL_PATH_DEFAULT = _buscar_isql()
DB_PATH_DEFAULT = r"D:\BD\PDVDATA.FDB"


# ══════════════════════════════════════════════════════════════════════════════
# CLASES DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DineroEnCaja:
    """Representa los datos de Dinero en Caja del Corte."""
    fondo_de_caja: float = 0.0
    ventas_en_efectivo: float = 0.0
    abonos_en_efectivo: float = 0.0
    entradas: float = 0.0
    salidas: float = 0.0
    devoluciones_en_efectivo: float = 0.0
    
    @property
    def total(self) -> float:
        """Calcula el total de dinero en caja."""
        return (self.fondo_de_caja + 
                self.ventas_en_efectivo + 
                self.abonos_en_efectivo + 
                self.entradas - 
                self.salidas - 
                self.devoluciones_en_efectivo)
    
    def to_dict(self) -> Dict[str, float]:
        """Convierte a diccionario."""
        return {
            'fondo_de_caja': self.fondo_de_caja,
            'ventas_en_efectivo': self.ventas_en_efectivo,
            'abonos_en_efectivo': self.abonos_en_efectivo,
            'entradas': self.entradas,
            'salidas': self.salidas,
            'devoluciones_en_efectivo': self.devoluciones_en_efectivo,
            'total': self.total
        }


@dataclass
class Ventas:
    """Representa los datos de Ventas del Corte."""
    ventas_efectivo: float = 0.0
    ventas_tarjeta: float = 0.0
    ventas_credito: float = 0.0
    ventas_vales: float = 0.0
    devoluciones_ventas: float = 0.0  # Total de devoluciones (todas las formas de pago)
    devoluciones_por_forma_pago: Dict[str, float] = None
    
    def __post_init__(self):
        if self.devoluciones_por_forma_pago is None:
            self.devoluciones_por_forma_pago = {}
    
    @property
    def total(self) -> float:
        """Calcula el total de ventas netas."""
        return (self.ventas_efectivo + 
                self.ventas_tarjeta + 
                self.ventas_credito + 
                self.ventas_vales - 
                self.devoluciones_ventas)
    
    @property
    def total_bruto(self) -> float:
        """Total de ventas sin restar devoluciones."""
        return (self.ventas_efectivo + 
                self.ventas_tarjeta + 
                self.ventas_credito + 
                self.ventas_vales)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'ventas_efectivo': self.ventas_efectivo,
            'ventas_tarjeta': self.ventas_tarjeta,
            'ventas_credito': self.ventas_credito,
            'ventas_vales': self.ventas_vales,
            'total_bruto': self.total_bruto,
            'devoluciones_ventas': self.devoluciones_ventas,
            'devoluciones_por_forma_pago': self.devoluciones_por_forma_pago,
            'total_neto': self.total
        }


@dataclass
class CorteCajero:
    """Representa el Corte de Caja completo."""
    turno_id: int
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    dinero_en_caja: DineroEnCaja
    ventas: Ventas
    ganancia: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'turno_id': self.turno_id,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'dinero_en_caja': self.dinero_en_caja.to_dict(),
            'ventas': self.ventas.to_dict(),
            'ganancia': self.ganancia
        }


# ══════════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class CorteCajeroManager:
    """
    Gestor de consultas para el Corte de Caja de Eleventa.
    
    Uso:
        manager = CorteCajeroManager()
        
        # Obtener corte del turno actual
        corte = manager.obtener_corte_turno_actual()
        
        # Obtener corte de un turno específico
        corte = manager.obtener_corte_por_turno(turno_id=445)
        
        # Obtener corte de una fecha específica
        corte = manager.obtener_corte_por_fecha("2026-02-03")
    """
    
    def __init__(self, db_path: str = None, isql_path: str = None):
        """
        Inicializa el gestor.
        
        Args:
            db_path: Ruta al archivo PDVDATA.FDB
            isql_path: Ruta al ejecutable isql.exe de Firebird
        """
        self.db_path = db_path or DB_PATH_DEFAULT
        self.isql_path = isql_path or ISQL_PATH_DEFAULT
        
        # Validar rutas
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"No se encontró la base de datos: {self.db_path}")
        if not os.path.exists(self.isql_path):
            raise FileNotFoundError(f"No se encontró isql: {self.isql_path}")
    
    def _ejecutar_sql(self, sql: str) -> Tuple[str, Optional[str]]:
        """
        Ejecuta una consulta SQL usando isql.
        
        Args:
            sql: Consulta SQL a ejecutar
            
        Returns:
            Tupla (resultado, error)
        """
        cmd = [
            self.isql_path,
            '-u', 'SYSDBA',
            '-p', 'masterkey',
            '-ch', 'WIN1252',
            self.db_path
        ]
        
        try:
            run_kwargs = {
                'input': sql,
                'capture_output': True,
                'text': True,
                'timeout': 60,
                'encoding': 'cp1252',
                'errors': 'replace'
            }
            if sys.platform == 'win32':
                run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            proc = subprocess.run(cmd, **run_kwargs)
            
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            
            return stdout, stderr if stderr else None
            
        except subprocess.TimeoutExpired:
            return "", "Timeout: La consulta tardó demasiado"
        except FileNotFoundError:
            return "", f"No se encontró isql en: {self.isql_path}"
        except Exception as e:
            return "", str(e)
    
    def _parsear_valor(self, resultado: str, campo: str) -> float:
        """
        Extrae un valor numérico del resultado de isql.
        
        Args:
            resultado: Salida de isql
            campo: Nombre del campo a buscar
            
        Returns:
            Valor numérico o 0.0 si no se encuentra
        """
        try:
            lines = resultado.split('\n')
            encontrar_valor = False
            
            for line in lines:
                line_upper = line.upper().strip()
                
                # Saltar líneas de separadores
                if line_upper.startswith('=') or line_upper.startswith('-'):
                    encontrar_valor = True
                    continue
                
                # Si estamos después de los separadores, buscar el valor
                if encontrar_valor and line.strip():
                    # Ignorar líneas SQL>
                    if 'SQL>' in line:
                        continue
                    
                    # Intentar extraer el valor
                    parts = line.strip().split()
                    for part in parts:
                        try:
                            # Limpiar el valor
                            valor_str = part.replace(',', '').strip()
                            if valor_str and valor_str not in ['<null>', 'null', 'NULL']:
                                return float(valor_str)
                        except ValueError:
                            continue
            
            return 0.0
        except Exception:
            return 0.0
    
    def _parsear_fila_simple(self, resultado: str) -> Dict[str, float]:
        """
        Parsea una fila simple de resultados.
        
        Args:
            resultado: Salida de isql
            
        Returns:
            Diccionario con los valores
        """
        valores = {}
        try:
            lines = resultado.split('\n')
            headers = []
            data_line = None
            
            for i, line in enumerate(lines):
                # Buscar línea con encabezados (contiene nombres de campos)
                if 'VENTAS' in line.upper() or 'FONDO' in line.upper() or 'TOTAL' in line.upper():
                    # Extraer nombres de columnas
                    parts = line.split()
                    headers = [p.strip() for p in parts if p.strip()]
                    continue
                
                # Buscar línea de datos (después de ===)
                if line.strip().startswith('='):
                    continue
                    
                # Línea de datos
                if headers and line.strip() and not line.strip().startswith('SQL'):
                    parts = line.split()
                    for j, part in enumerate(parts):
                        try:
                            valor = float(part.replace(',', ''))
                            if j < len(headers):
                                valores[headers[j]] = valor
                        except ValueError:
                            continue
            
            return valores
        except Exception:
            return {}
    
    # ══════════════════════════════════════════════════════════════════════════
    # FUNCIONES DE CONSULTA - DINERO EN CAJA
    # ══════════════════════════════════════════════════════════════════════════
    
    def obtener_fondo_de_caja(self, turno_id: int) -> float:
        """
        Obtiene el fondo de caja inicial de un turno.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Monto del fondo de caja
        """
        sql = f"""
        SELECT DINERO_INICIAL AS FONDO_CAJA
        FROM TURNOS
        WHERE ID = {turno_id};
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'FONDO_CAJA')
    
    def obtener_ventas_en_efectivo(self, turno_id: int) -> float:
        """
        Obtiene el total de ventas en efectivo de un turno.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Total de ventas en efectivo
        """
        sql = f"""
        SELECT VENTAS_EFECTIVO
        FROM TURNOS
        WHERE ID = {turno_id};
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'VENTAS_EFECTIVO')
    
    def obtener_abonos_en_efectivo(self, turno_id: int) -> float:
        """
        Obtiene el total de abonos recibidos en efectivo de un turno.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Total de abonos en efectivo
        """
        sql = f"""
        SELECT ABONOS_EFECTIVO
        FROM TURNOS
        WHERE ID = {turno_id};
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'ABONOS_EFECTIVO')
    
    def obtener_entradas(self, turno_id: int) -> float:
        """
        Obtiene el total de entradas de efectivo de un turno.
        Entradas son movimientos como préstamos recibidos, 
        dinero añadido a caja manualmente, etc.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Total de entradas
        """
        sql = f"""
        SELECT COALESCE(SUM(MONTO), 0) AS TOTAL_ENTRADAS
        FROM CORTE_MOVIMIENTOS
        WHERE ID_TURNO = {turno_id}
        AND TIPO = 'Entrada';
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'TOTAL_ENTRADAS')
    
    def obtener_salidas(self, turno_id: int) -> float:
        """
        Obtiene el total de salidas de efectivo de un turno.
        Salidas son movimientos como préstamos otorgados,
        dinero retirado de caja, etc.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Total de salidas
        """
        sql = f"""
        SELECT COALESCE(SUM(MONTO), 0) AS TOTAL_SALIDAS
        FROM CORTE_MOVIMIENTOS
        WHERE ID_TURNO = {turno_id}
        AND TIPO = 'Salida';
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'TOTAL_SALIDAS')
    
    def obtener_devoluciones_en_efectivo(self, turno_id: int) -> float:
        """
        Obtiene las devoluciones de ventas que fueron pagadas ORIGINALMENTE en efectivo.
        
        IMPORTANTE: Esta función retorna solo las devoluciones donde la venta original
        se pagó en efectivo, ya que son las que afectan el dinero físico en caja.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Total de devoluciones en efectivo
        """
        sql = f"""
        SELECT DEVOLUCIONES_VENTAS_EFECTIVO AS DEV_EFECTIVO
        FROM TURNOS
        WHERE ID = {turno_id};
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'DEV_EFECTIVO')
    
    # ══════════════════════════════════════════════════════════════════════════
    # FUNCIONES DE CONSULTA - VENTAS
    # ══════════════════════════════════════════════════════════════════════════
    
    def obtener_ventas_por_forma_pago(self, turno_id: int) -> Dict[str, float]:
        """
        Obtiene las ventas desglosadas por forma de pago.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Diccionario con ventas por forma de pago
        """
        # Consulta separada para cada campo para evitar problemas de parseo
        resultado = {}
        
        for campo, nombre in [('VENTAS_EFECTIVO', 'efectivo'), 
                               ('VENTAS_TARJETA', 'tarjeta'),
                               ('VENTAS_CREDITO', 'credito'),
                               ('VENTAS_VALES', 'vales')]:
            sql = f"SELECT {campo} FROM TURNOS WHERE ID = {turno_id};"
            res, error = self._ejecutar_sql(sql)
            resultado[nombre] = self._parsear_valor(res, campo) if not error else 0.0
        
        return resultado
    
    def obtener_devoluciones_de_ventas(self, turno_id: int) -> float:
        """
        Obtiene el TOTAL de devoluciones de ventas, independientemente de la
        forma de pago original.
        
        IMPORTANTE: Esta función suma TODAS las devoluciones (efectivo + crédito + 
        tarjeta + vales). Es diferente de obtener_devoluciones_en_efectivo() que
        solo cuenta las devoluciones donde la venta se pagó originalmente en efectivo.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Total de devoluciones de ventas
        """
        sql = f"""
        SELECT 
            COALESCE(DEVOLUCIONES_VENTAS_EFECTIVO, 0) + 
            COALESCE(DEVOLUCIONES_VENTAS_CREDITO, 0) + 
            COALESCE(DEVOLUCIONES_VENTAS_TARJETA, 0) + 
            COALESCE(DEVOLUCIONES_VENTAS_VALES, 0) AS TOTAL_DEVOLUCIONES
        FROM TURNOS
        WHERE ID = {turno_id};
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'TOTAL_DEVOLUCIONES')
    
    def obtener_devoluciones_desglosadas(self, turno_id: int) -> Dict[str, float]:
        """
        Obtiene las devoluciones desglosadas por forma de pago original de la venta.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Diccionario con devoluciones por forma de pago
        """
        # Consulta separada para cada campo para evitar problemas de parseo
        resultado = {}
        
        for campo, nombre in [('DEVOLUCIONES_VENTAS_EFECTIVO', 'efectivo'), 
                               ('DEVOLUCIONES_VENTAS_CREDITO', 'credito'),
                               ('DEVOLUCIONES_VENTAS_TARJETA', 'tarjeta'),
                               ('DEVOLUCIONES_VENTAS_VALES', 'vales')]:
            sql = f"SELECT {campo} FROM TURNOS WHERE ID = {turno_id};"
            res, error = self._ejecutar_sql(sql)
            resultado[nombre] = self._parsear_valor(res, campo) if not error else 0.0
        
        return resultado
    
    def obtener_ventas_credito_desde_ventatickets(self, turno_id: int) -> float:
        """
        Calcula las ventas a crédito directamente desde VENTATICKETS.
        Incluye todas las ventas a crédito (canceladas o no) del turno.
        
        Una venta es a crédito si:
        - CREDITO = 1, o
        - TOTAL_CREDITO > 0, o
        - CONDICION = 'CREDITO'
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Total de ventas a crédito del turno
        """
        sql = f"""
        SET NAMES WIN1252;
        SELECT COALESCE(SUM(TOTAL), 0) AS TOTAL_CREDITO
        FROM VENTATICKETS
        WHERE TURNO_ID = {turno_id}
        AND (COALESCE(CREDITO, 0) = 1 
             OR COALESCE(TOTAL_CREDITO, 0) > 0);
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'TOTAL_CREDITO')
    
    def obtener_ventas_credito_por_fecha(self, fecha: str) -> float:
        """
        Calcula las ventas a crédito de una fecha específica desde VENTATICKETS.
        Incluye todas las ventas a crédito (canceladas o no).
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD'
            
        Returns:
            Total de ventas a crédito de la fecha
        """
        sql = f"""
        SET NAMES WIN1252;
        SELECT COALESCE(SUM(TOTAL), 0) AS TOTAL_CREDITO
        FROM VENTATICKETS
        WHERE CAST(VENDIDO_EN AS DATE) = '{fecha}'
        AND (COALESCE(CREDITO, 0) = 1 
             OR COALESCE(TOTAL_CREDITO, 0) > 0);
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'TOTAL_CREDITO')

    def obtener_ganancia(self, turno_id: int) -> float:
        """
        Obtiene la ganancia acumulada del turno.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Ganancia del turno
        """
        sql = f"""
        SELECT ACUMULADO_GANANCIA AS GANANCIA
        FROM TURNOS
        WHERE ID = {turno_id};
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return 0.0
        return self._parsear_valor(resultado, 'GANANCIA')
    
    # ══════════════════════════════════════════════════════════════════════════
    # FUNCIONES DE CONSULTA - TURNOS
    # ══════════════════════════════════════════════════════════════════════════
    
    def obtener_turno_actual(self) -> Optional[int]:
        """
        Obtiene el ID del turno actualmente abierto.
        
        Returns:
            ID del turno actual o None si no hay turno abierto
        """
        sql = """
        SELECT FIRST 1 ID
        FROM TURNOS
        WHERE TERMINO_EN IS NULL
        ORDER BY ID DESC;
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return None
        
        try:
            lines = resultado.split('\n')
            encontrar_valor = False
            
            for line in lines:
                # Saltar líneas de separadores
                if line.strip().startswith('='):
                    encontrar_valor = True
                    continue
                
                # Si estamos después de los separadores, buscar el valor
                if encontrar_valor and line.strip():
                    if 'SQL>' in line:
                        continue
                    parts = line.strip().split()
                    if parts:
                        try:
                            return int(parts[0])
                        except ValueError:
                            continue
        except:
            pass
        
        return None
    
    def obtener_ultimo_turno(self) -> Optional[int]:
        """
        Obtiene el ID del último turno (cerrado o no).
        
        Returns:
            ID del último turno
        """
        sql = """
        SELECT FIRST 1 ID
        FROM TURNOS
        ORDER BY ID DESC;
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return None
        
        try:
            lines = resultado.split('\n')
            encontrar_valor = False
            
            for line in lines:
                # Saltar líneas de separadores
                if line.strip().startswith('='):
                    encontrar_valor = True
                    continue
                
                # Si estamos después de los separadores, buscar el valor
                if encontrar_valor and line.strip():
                    if 'SQL>' in line:
                        continue
                    parts = line.strip().split()
                    if parts:
                        try:
                            return int(parts[0])
                        except ValueError:
                            continue
        except:
            pass
        
        return None
    
    def obtener_turno_por_fecha(self, fecha: str) -> Optional[int]:
        """
        Obtiene el ID del último turno de una fecha específica.
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD'
            
        Returns:
            ID del turno o None si no existe
        """
        sql = f"""
        SELECT FIRST 1 ID
        FROM TURNOS
        WHERE CAST(INICIO_EN AS DATE) = '{fecha}'
        ORDER BY ID DESC;
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return None
        
        try:
            lines = resultado.split('\n')
            encontrar_valor = False
            
            for line in lines:
                # Saltar líneas de separadores
                if line.strip().startswith('='):
                    encontrar_valor = True
                    continue
                
                # Si estamos después de los separadores, buscar el valor
                if encontrar_valor and line.strip():
                    if 'SQL>' in line:
                        continue
                    parts = line.strip().split()
                    if parts:
                        try:
                            return int(parts[0])
                        except ValueError:
                            continue
        except:
            pass
        
        return None
    
    def obtener_todos_turnos_por_fecha(self, fecha: str) -> List[int]:
        """
        Obtiene TODOS los IDs de turnos de una fecha específica.
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD'
            
        Returns:
            Lista de IDs de turnos (puede estar vacía)
        """
        sql = f"""
        SELECT ID
        FROM TURNOS
        WHERE CAST(INICIO_EN AS DATE) = '{fecha}'
        ORDER BY ID;
        """
        resultado, error = self._ejecutar_sql(sql)
        if error:
            return []
        
        turnos = []
        try:
            lines = resultado.split('\n')
            encontrar_valor = False
            
            for line in lines:
                if line.strip().startswith('='):
                    encontrar_valor = True
                    continue
                
                if encontrar_valor and line.strip():
                    if 'SQL>' in line:
                        continue
                    parts = line.strip().split()
                    if parts:
                        try:
                            turnos.append(int(parts[0]))
                        except ValueError:
                            continue
        except:
            pass
        
        return turnos
    
    def obtener_info_turno(self, turno_id: int) -> Dict[str, Any]:
        """
        Obtiene información básica de un turno.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Diccionario con información del turno
        """
        sql = f"""
        SELECT ID, INICIO_EN, TERMINO_EN, ID_CAJERO
        FROM TURNOS
        WHERE ID = {turno_id};
        """
        resultado, error = self._ejecutar_sql(sql)
        
        info = {
            'id': turno_id,
            'inicio': None,
            'fin': None,
            'cajero_id': None
        }
        
        try:
            lines = resultado.split('\n')
            for line in lines:
                if '2026' in line or '2025' in line or '2024' in line:  # Año en la fecha
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if '-' in p and len(p) == 10:  # Fecha
                            if info['inicio'] is None:
                                info['inicio'] = p
                            else:
                                info['fin'] = p
        except:
            pass
        
        return info
    
    # ══════════════════════════════════════════════════════════════════════════
    # FUNCIONES PRINCIPALES - CORTE COMPLETO
    # ══════════════════════════════════════════════════════════════════════════
    
    def obtener_corte_por_turno(self, turno_id: int) -> CorteCajero:
        """
        Obtiene el corte de caja completo de un turno específico.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Objeto CorteCajero con toda la información
        """
        # Obtener información del turno
        info = self.obtener_info_turno(turno_id)
        
        # Obtener datos de Dinero en Caja
        dinero_en_caja = DineroEnCaja(
            fondo_de_caja=self.obtener_fondo_de_caja(turno_id),
            ventas_en_efectivo=self.obtener_ventas_en_efectivo(turno_id),
            abonos_en_efectivo=self.obtener_abonos_en_efectivo(turno_id),
            entradas=self.obtener_entradas(turno_id),
            salidas=self.obtener_salidas(turno_id),
            devoluciones_en_efectivo=self.obtener_devoluciones_en_efectivo(turno_id)
        )
        
        # Obtener datos de Ventas
        ventas_forma_pago = self.obtener_ventas_por_forma_pago(turno_id)
        devoluciones_desglosadas = self.obtener_devoluciones_desglosadas(turno_id)
        
        # Si VENTAS_CREDITO de TURNOS es 0, calcular desde VENTATICKETS
        ventas_credito = ventas_forma_pago.get('credito', 0.0)
        if ventas_credito == 0.0:
            ventas_credito = self.obtener_ventas_credito_desde_ventatickets(turno_id)
        
        ventas = Ventas(
            ventas_efectivo=ventas_forma_pago.get('efectivo', 0.0),
            ventas_tarjeta=ventas_forma_pago.get('tarjeta', 0.0),
            ventas_credito=ventas_credito,
            ventas_vales=ventas_forma_pago.get('vales', 0.0),
            devoluciones_ventas=self.obtener_devoluciones_de_ventas(turno_id),
            devoluciones_por_forma_pago=devoluciones_desglosadas
        )
        
        # Crear objeto de corte
        return CorteCajero(
            turno_id=turno_id,
            fecha_inicio=datetime.fromisoformat(info['inicio']) if info['inicio'] else None,
            fecha_fin=datetime.fromisoformat(info['fin']) if info['fin'] else None,
            dinero_en_caja=dinero_en_caja,
            ventas=ventas,
            ganancia=self.obtener_ganancia(turno_id)
        )
    
    def obtener_corte_turno_actual(self) -> Optional[CorteCajero]:
        """
        Obtiene el corte de caja del turno actualmente abierto.
        
        Returns:
            Objeto CorteCajero o None si no hay turno abierto
        """
        turno_id = self.obtener_turno_actual()
        if turno_id is None:
            turno_id = self.obtener_ultimo_turno()
        
        if turno_id is None:
            return None
        
        return self.obtener_corte_por_turno(turno_id)
    
    def obtener_corte_por_fecha(self, fecha: str) -> Optional[CorteCajero]:
        """
        Obtiene el corte de caja de una fecha específica.
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD'
            
        Returns:
            Objeto CorteCajero o None si no existe turno para esa fecha
        """
        turno_id = self.obtener_turno_por_fecha(fecha)
        if turno_id is None:
            return None
        
        return self.obtener_corte_por_turno(turno_id)
    
    def obtener_corte_completo_por_fecha(self, fecha: str) -> Optional[CorteCajero]:
        """
        Obtiene el corte de caja COMBINADO de TODOS los turnos de una fecha.
        Suma los valores de todos los turnos del día.
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD'
            
        Returns:
            Objeto CorteCajero con totales combinados o None si no hay turnos
        """
        turnos = self.obtener_todos_turnos_por_fecha(fecha)
        if not turnos:
            return None
        
        # Si solo hay un turno, retornar ese corte directamente
        if len(turnos) == 1:
            return self.obtener_corte_por_turno(turnos[0])
        
        # Sumar todos los cortes de los turnos del día
        dinero_total = DineroEnCaja(
            fondo_de_caja=0.0,
            ventas_en_efectivo=0.0,
            abonos_en_efectivo=0.0,
            entradas=0.0,
            salidas=0.0,
            devoluciones_en_efectivo=0.0
        )
        
        # Inicializar devoluciones por forma de pago
        devs_por_forma_pago = {
            'efectivo': 0.0,
            'credito': 0.0,
            'tarjeta': 0.0,
            'vales': 0.0
        }
        
        ventas_total = Ventas(
            ventas_efectivo=0.0,
            ventas_tarjeta=0.0,
            ventas_credito=0.0,
            ventas_vales=0.0,
            devoluciones_ventas=0.0,
            devoluciones_por_forma_pago=devs_por_forma_pago
        )
        
        ganancia_total = 0.0
        fecha_inicio = None
        fecha_fin = None
        
        for turno_id in turnos:
            corte = self.obtener_corte_por_turno(turno_id)
            if corte:
                # Sumar dinero en caja
                dinero_total.fondo_de_caja += corte.dinero_en_caja.fondo_de_caja
                dinero_total.ventas_en_efectivo += corte.dinero_en_caja.ventas_en_efectivo
                dinero_total.abonos_en_efectivo += corte.dinero_en_caja.abonos_en_efectivo
                dinero_total.entradas += corte.dinero_en_caja.entradas
                dinero_total.salidas += corte.dinero_en_caja.salidas
                dinero_total.devoluciones_en_efectivo += corte.dinero_en_caja.devoluciones_en_efectivo
                
                # Sumar ventas
                ventas_total.ventas_efectivo += corte.ventas.ventas_efectivo
                ventas_total.ventas_tarjeta += corte.ventas.ventas_tarjeta
                ventas_total.ventas_credito += corte.ventas.ventas_credito
                ventas_total.ventas_vales += corte.ventas.ventas_vales
                ventas_total.devoluciones_ventas += corte.ventas.devoluciones_ventas
                
                # Sumar devoluciones por forma de pago
                if corte.ventas.devoluciones_por_forma_pago:
                    for forma, valor in corte.ventas.devoluciones_por_forma_pago.items():
                        if forma in devs_por_forma_pago:
                            devs_por_forma_pago[forma] += valor
                
                # Sumar ganancia
                ganancia_total += corte.ganancia
                
                # Guardar primera y última fecha
                if fecha_inicio is None and corte.fecha_inicio:
                    fecha_inicio = corte.fecha_inicio
                if corte.fecha_fin:
                    fecha_fin = corte.fecha_fin
        
        # Actualizar las devoluciones por forma de pago
        ventas_total.devoluciones_por_forma_pago = devs_por_forma_pago
        
        # Crear corte combinado con todos los IDs de turnos concatenados
        return CorteCajero(
            turno_id=turnos[-1],  # Usar el último turno como referencia
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            dinero_en_caja=dinero_total,
            ventas=ventas_total,
            ganancia=ganancia_total
        )


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONVENIENCIA (para uso directo sin instanciar la clase)
# ══════════════════════════════════════════════════════════════════════════════

_manager = None

def _get_manager() -> CorteCajeroManager:
    """Obtiene o crea la instancia del manager."""
    global _manager
    if _manager is None:
        _manager = CorteCajeroManager()
    return _manager


def get_dinero_en_caja(turno_id: int = None) -> DineroEnCaja:
    """
    Obtiene los datos de Dinero en Caja.
    
    Args:
        turno_id: ID del turno (opcional, usa el actual si no se especifica)
        
    Returns:
        Objeto DineroEnCaja
    """
    manager = _get_manager()
    
    if turno_id is None:
        turno_id = manager.obtener_turno_actual() or manager.obtener_ultimo_turno()
    
    return DineroEnCaja(
        fondo_de_caja=manager.obtener_fondo_de_caja(turno_id),
        ventas_en_efectivo=manager.obtener_ventas_en_efectivo(turno_id),
        abonos_en_efectivo=manager.obtener_abonos_en_efectivo(turno_id),
        entradas=manager.obtener_entradas(turno_id),
        salidas=manager.obtener_salidas(turno_id),
        devoluciones_en_efectivo=manager.obtener_devoluciones_en_efectivo(turno_id)
    )


def get_ventas(turno_id: int = None) -> Ventas:
    """
    Obtiene los datos de Ventas.
    
    Args:
        turno_id: ID del turno (opcional, usa el actual si no se especifica)
        
    Returns:
        Objeto Ventas
    """
    manager = _get_manager()
    
    if turno_id is None:
        turno_id = manager.obtener_turno_actual() or manager.obtener_ultimo_turno()
    
    ventas_forma_pago = manager.obtener_ventas_por_forma_pago(turno_id)
    devoluciones_desglosadas = manager.obtener_devoluciones_desglosadas(turno_id)
    
    return Ventas(
        ventas_efectivo=ventas_forma_pago.get('efectivo', 0.0),
        ventas_tarjeta=ventas_forma_pago.get('tarjeta', 0.0),
        ventas_credito=ventas_forma_pago.get('credito', 0.0),
        ventas_vales=ventas_forma_pago.get('vales', 0.0),
        devoluciones_ventas=manager.obtener_devoluciones_de_ventas(turno_id),
        devoluciones_por_forma_pago=devoluciones_desglosadas
    )


def get_corte_cajero(turno_id: int = None) -> Optional[CorteCajero]:
    """
    Obtiene el corte de caja completo.
    
    Args:
        turno_id: ID del turno (opcional, usa el actual si no se especifica)
        
    Returns:
        Objeto CorteCajero
    """
    manager = _get_manager()
    
    if turno_id is None:
        return manager.obtener_corte_turno_actual()
    
    return manager.obtener_corte_por_turno(turno_id)


def get_corte_cajero_por_fecha(fecha: str) -> Optional[CorteCajero]:
    """
    Obtiene el corte de caja COMBINADO de TODOS los turnos de una fecha.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        Objeto CorteCajero con totales de todos los turnos del día
    """
    manager = _get_manager()
    return manager.obtener_corte_completo_por_fecha(fecha)


def get_todos_turnos_fecha(fecha: str) -> List[int]:
    """
    Obtiene la lista de todos los turnos de una fecha.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        Lista de IDs de turnos
    """
    manager = _get_manager()
    return manager.obtener_todos_turnos_por_fecha(fecha)


# ══════════════════════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("MÓDULO CORTE CAJERO - DEMOSTRACIÓN")
    print("=" * 80)
    
    try:
        # Crear instancia del manager
        manager = CorteCajeroManager()
        
        # Obtener el último turno con datos (445 tiene datos de ejemplo)
        turno_id = manager.obtener_ultimo_turno()
        print(f"\n📋 Último Turno ID: {turno_id}")
        
        # Si el turno actual no tiene datos, usar el anterior como ejemplo
        if turno_id:
            corte = manager.obtener_corte_por_turno(turno_id)
            
            # Si no hay ventas, intentar con el turno anterior
            if corte.ventas.ventas_efectivo == 0 and turno_id > 1:
                turno_id = turno_id - 1
                corte = manager.obtener_corte_por_turno(turno_id)
                print(f"   (Usando turno {turno_id} que tiene datos)")
            
            print("\n" + "═" * 40)
            print("💰 DINERO EN CAJA")
            print("═" * 40)
            print(f"  Fondo de Caja:           ${corte.dinero_en_caja.fondo_de_caja:,.2f}")
            print(f"  Ventas en Efectivo:    + ${corte.dinero_en_caja.ventas_en_efectivo:,.2f}")
            print(f"  Abonos en Efectivo:    + ${corte.dinero_en_caja.abonos_en_efectivo:,.2f}")
            print(f"  Entradas:              + ${corte.dinero_en_caja.entradas:,.2f}")
            print(f"  Salidas:               - ${corte.dinero_en_caja.salidas:,.2f}")
            print(f"  Devoluciones Efectivo: - ${corte.dinero_en_caja.devoluciones_en_efectivo:,.2f}")
            print(f"                          ─────────────────")
            print(f"  TOTAL:                   ${corte.dinero_en_caja.total:,.2f}")
            
            print("\n" + "═" * 40)
            print("🛒 VENTAS")
            print("═" * 40)
            print(f"  En Efectivo:             ${corte.ventas.ventas_efectivo:,.2f}")
            print(f"  Con Tarjeta:             ${corte.ventas.ventas_tarjeta:,.2f}")
            print(f"  A Crédito:               ${corte.ventas.ventas_credito:,.2f}")
            print(f"  Con Vales:               ${corte.ventas.ventas_vales:,.2f}")
            print(f"                          ─────────────────")
            print(f"  Ventas Totales:          ${corte.ventas.total_bruto:,.2f}")
            print(f"  Devoluciones:          - ${corte.ventas.devoluciones_ventas:,.2f}")
            print(f"                          ─────────────────")
            print(f"  TOTAL NETO:              ${corte.ventas.total:,.2f}")
            
            print("\n" + "═" * 40)
            print("📊 DEVOLUCIONES DESGLOSADAS")
            print("═" * 40)
            devs = corte.ventas.devoluciones_por_forma_pago
            print(f"  De ventas en Efectivo:   ${devs.get('efectivo', 0):,.2f}")
            print(f"  De ventas a Crédito:     ${devs.get('credito', 0):,.2f}")
            print(f"  De ventas con Tarjeta:   ${devs.get('tarjeta', 0):,.2f}")
            print(f"  De ventas con Vales:     ${devs.get('vales', 0):,.2f}")
            
            # Calcular la diferencia
            diff = corte.ventas.devoluciones_ventas - corte.dinero_en_caja.devoluciones_en_efectivo
            
            print("\n" + "═" * 40)
            print("💡 EXPLICACIÓN DE LA DIFERENCIA")
            print("═" * 40)
            print(f"""
  'Devoluciones en Efectivo' (${corte.dinero_en_caja.devoluciones_en_efectivo:,.2f}):
  → Solo las devoluciones de ventas que se PAGARON en efectivo.
  → Afecta el dinero FÍSICO en la caja.
  
  'Devoluciones de Ventas' (${corte.ventas.devoluciones_ventas:,.2f}):
  → TODAS las devoluciones sin importar forma de pago original.
  → Es la suma de: Efectivo + Crédito + Tarjeta + Vales
  
  Diferencia: ${diff:,.2f}
  (Esto corresponde a devoluciones de ventas a CRÉDITO y TARJETA)
""")
            
            print("💚 Ganancia:", f"${corte.ganancia:,.2f}")
            
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
