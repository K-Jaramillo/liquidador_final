# -*- coding: utf-8 -*-
"""
DatabaseManager - Gestor de conexiones a Firebird
"""
import subprocess
import os
import shutil
import sys
from typing import Tuple, Optional, List, Dict, Any


class DatabaseManager:
    """Gestiona las conexiones y consultas a la base de datos Firebird."""
    
    def __init__(self, fdb_path: str, isql_path: str):
        self.fdb_path = fdb_path
        self.isql_path = isql_path
        self._connected = False
        self._connection_string = None
        
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def verificar_conexion(self) -> Tuple[bool, str]:
        """Verifica la conexión a la base de datos."""
        if not os.path.exists(self.fdb_path):
            return False, f"No se encontró el archivo: {self.fdb_path}"
        
        if not os.path.exists(self.isql_path):
            return False, f"No se encontró isql en: {self.isql_path}"
        
        # Intentar conexión de prueba
        sql_test = "SELECT 1 FROM RDB$DATABASE;"
        resultado, error = self.ejecutar_sql(sql_test)
        
        if error:
            return False, f"Error de conexión: {error}"
        
        self._connected = True
        return True, "Conexión exitosa"
    
    def _preparar_conexion_linux(self) -> str:
        """Prepara la conexión para Linux copiando el archivo FDB a /tmp."""
        uid = os.getuid() if hasattr(os, 'getuid') else 1000
        tmp_fdb = f"/tmp/PDVDATA_{uid}.FDB"
        
        try:
            # Copiar si no existe o si el original es más nuevo
            if not os.path.exists(tmp_fdb) or \
               os.path.getmtime(self.fdb_path) > os.path.getmtime(tmp_fdb):
                shutil.copy2(self.fdb_path, tmp_fdb)
                os.chmod(tmp_fdb, 0o666)
        except Exception as e:
            return self.fdb_path
        
        return f"localhost:{tmp_fdb}"
    
    def ejecutar_sql(self, sql: str) -> Tuple[str, Optional[str]]:
        """Ejecuta una consulta SQL y retorna (resultado, error)."""
        # Preparar conexión según SO
        if sys.platform != 'win32':
            connection_string = self._preparar_conexion_linux()
        else:
            connection_string = self.fdb_path
        
        # Construir comando
        cmd = [
            self.isql_path,
            '-u', 'SYSDBA',
            '-p', 'masterkey',
            '-ch', 'UTF8',
            connection_string
        ]
        
        try:
            # En Windows, ocultar ventana CMD
            kwargs = {
                'input': sql,
                'capture_output': True,
                'text': True,
                'timeout': 60,
                'encoding': 'utf-8',
                'errors': 'replace'
            }
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            proc = subprocess.run(cmd, **kwargs)
            
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            
            # Verificar si hay datos válidos en stdout
            has_valid_data = (
                '===' in stdout or
                'FOLIO' in stdout.upper() or
                'NOMBRE' in stdout.upper() or
                'TOTAL' in stdout.upper() or
                any(line.strip() and not line.startswith('Database:') 
                    for line in stdout.split('\n'))
            )
            
            # Si hay datos válidos, ignorar ciertos errores de stderr
            if has_valid_data:
                if "Use CONNECT or CREATE DATABASE" in stderr:
                    stderr = ""
            
            return stdout, stderr if stderr else None
            
        except subprocess.TimeoutExpired:
            return "", "Timeout: La consulta tardó demasiado"
        except FileNotFoundError:
            return "", f"No se encontró isql en: {self.isql_path}"
        except Exception as e:
            return "", str(e)
    
    def consultar_ventas(self, fecha: str) -> Tuple[List[Dict], Optional[str]]:
        """Consulta las ventas de una fecha específica."""
        sql = f"""
SET HEADING ON;
SELECT ID, FOLIO, NOMBRE, SUBTOTAL, TOTAL, ESTA_CANCELADO, TOTAL_CREDITO,
       CAST(CREADO_EN AS DATE) AS FECHA_CREACION
FROM VENTATICKETS
WHERE CAST(CREADO_EN AS DATE) = '{fecha}'
  AND FOLIO > 0
ORDER BY FOLIO;
"""
        resultado, error = self.ejecutar_sql(sql)
        
        if error:
            return [], error
        
        ventas = self._parsear_ventas(resultado)
        return ventas, None
    
    def consultar_canceladas_otro_dia(self, fecha: str, dias_atras: int = 7) -> Tuple[List[Dict], Optional[str]]:
        """Consulta facturas canceladas de días anteriores."""
        sql = f"""
SET HEADING ON;
SELECT vt.ID, vt.FOLIO, vt.NOMBRE, vt.SUBTOTAL, vt.TOTAL, 
       vt.TOTAL_CREDITO, CAST(vt.CREADO_EN AS DATE) AS FECHA_CREACION
FROM VENTATICKETS vt
WHERE vt.ESTA_CANCELADO = 1
  AND CAST(vt.CREADO_EN AS DATE) < '{fecha}'
  AND CAST(vt.CREADO_EN AS DATE) >= '{fecha}' - {dias_atras}
  AND vt.FOLIO > 0
ORDER BY vt.FOLIO;
"""
        resultado, error = self.ejecutar_sql(sql)
        
        if error:
            return [], error
        
        return self._parsear_ventas(resultado), None
    
    def consultar_devoluciones(self, fecha: str) -> Tuple[List[Dict], Optional[str]]:
        """Consulta las devoluciones del día."""
        sql = f"""
SET HEADING ON;
SELECT ID, FOLIO_ORIGINAL, DESCRIPCION, MONTO, CAST(CREADO_EN AS DATE) AS FECHA
FROM DEVOLUCIONES
WHERE CAST(CREADO_EN AS DATE) = '{fecha}';
"""
        resultado, error = self.ejecutar_sql(sql)
        
        if error:
            return [], error
        
        devoluciones = []
        lines = [l.strip() for l in resultado.split('\n') if l.strip() and not l.startswith('Database:')]
        
        header_found = False
        for line in lines:
            if 'ID' in line.upper() and 'FOLIO' in line.upper():
                header_found = True
                continue
            if '===' in line:
                continue
            if header_found and line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        devoluciones.append({
                            'id': int(parts[0]),
                            'folio_original': int(parts[1]),
                            'descripcion': ' '.join(parts[2:-1]),
                            'monto': float(parts[-1].replace(',', ''))
                        })
                    except (ValueError, IndexError):
                        continue
        
        return devoluciones, None
    
    def consultar_movimientos(self, fecha: str) -> Tuple[List[Dict], List[Dict], Optional[str]]:
        """Consulta los movimientos (entradas y salidas) del día."""
        sql = f"""
SET HEADING ON;
SELECT ID, TIPO, DESCRIPCION, MONTO, CAST(CREADO_EN AS DATE) AS FECHA
FROM MOVIMIENTOS
WHERE CAST(CREADO_EN AS DATE) = '{fecha}';
"""
        resultado, error = self.ejecutar_sql(sql)
        
        if error:
            return [], [], error
        
        entradas = []
        salidas = []
        
        lines = [l.strip() for l in resultado.split('\n') if l.strip() and not l.startswith('Database:')]
        
        header_found = False
        for line in lines:
            if 'ID' in line.upper() and 'TIPO' in line.upper():
                header_found = True
                continue
            if '===' in line:
                continue
            if header_found and line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        mov = {
                            'id': int(parts[0]),
                            'tipo': parts[1],
                            'descripcion': ' '.join(parts[2:-1]),
                            'monto': float(parts[-1].replace(',', ''))
                        }
                        if 'ENTRADA' in mov['tipo'].upper() or 'INGRESO' in mov['tipo'].upper():
                            entradas.append(mov)
                        else:
                            salidas.append(mov)
                    except (ValueError, IndexError):
                        continue
        
        return entradas, salidas, None
    
    def consultar_productos_factura(self, folio: int) -> Tuple[List[Dict], Optional[str]]:
        """Consulta los productos de una factura específica."""
        sql = f"""
SET HEADING ON;
SELECT p.DESCRIPCION, vtp.CANTIDAD, vtp.PRECIO
FROM VENTATICKETS_PRODUCTOS vtp
JOIN PRODUCTOS p ON vtp.PRODUCTO_ID = p.ID
WHERE vtp.VENTATICKET_ID = (
    SELECT ID FROM VENTATICKETS WHERE FOLIO = {folio}
);
"""
        resultado, error = self.ejecutar_sql(sql)
        
        if error:
            return [], error
        
        productos = []
        lines = [l.strip() for l in resultado.split('\n') if l.strip() and not l.startswith('Database:')]
        
        header_found = False
        for line in lines:
            if 'DESCRIPCION' in line.upper():
                header_found = True
                continue
            if '===' in line:
                continue
            if header_found and line:
                # Formato: DESCRIPCION    CANTIDAD    PRECIO
                parts = line.rsplit(None, 2)  # Dividir desde la derecha
                if len(parts) >= 3:
                    try:
                        productos.append({
                            'descripcion': parts[0],
                            'cantidad': int(float(parts[1])),
                            'precio': float(parts[2].replace(',', ''))
                        })
                    except (ValueError, IndexError):
                        continue
        
        return productos, None
    
    def _parsear_ventas(self, resultado: str) -> List[Dict]:
        """Parsea el resultado de una consulta de ventas."""
        ventas = []
        lines = [l.strip() for l in resultado.split('\n') if l.strip() and not l.startswith('Database:')]
        
        header_found = False
        for line in lines:
            if 'ID' in line.upper() and 'FOLIO' in line.upper():
                header_found = True
                continue
            if '===' in line:
                continue
            if header_found and line:
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        venta = {
                            'id': int(parts[0]),
                            'folio': int(parts[1]),
                            'nombre': ' '.join(parts[2:-4]) if len(parts) > 6 else parts[2],
                            'subtotal': float(parts[-4].replace(',', '')),
                            'total': float(parts[-3].replace(',', '')),
                            'cancelada': parts[-2] == '1',
                            'total_credito': float(parts[-1].replace(',', '')) if parts[-1].replace(',', '').replace('.', '').isdigit() else 0,
                        }
                        venta['es_credito'] = venta['total_credito'] > 0
                        venta['total_original'] = venta['total']
                        ventas.append(venta)
                    except (ValueError, IndexError):
                        continue
        
        return ventas
