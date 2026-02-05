#!/usr/bin/env python3
"""
Script para explorar el contenido completo de la base de datos Firebird
"""

import fdb
import os
import sys

# Agregar el directorio padre al path para importar core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.firebird_setup import get_firebird_setup, get_fdb_connection
from core.config import Config

# Inicializar la configuración de Firebird multiplataforma
firebird_setup = get_firebird_setup()

def conectar():
    """Conectar a la base de datos usando la configuración multiplataforma"""
    return get_fdb_connection()

def listar_tablas(cursor):
    """Listar todas las tablas de usuario"""
    cursor.execute("""
        SELECT RDB$RELATION_NAME 
        FROM RDB$RELATIONS 
        WHERE RDB$SYSTEM_FLAG = 0 
        AND RDB$VIEW_BLR IS NULL
        ORDER BY RDB$RELATION_NAME
    """)
    return [row[0].strip() for row in cursor.fetchall()]

def listar_vistas(cursor):
    """Listar todas las vistas"""
    cursor.execute("""
        SELECT RDB$RELATION_NAME 
        FROM RDB$RELATIONS 
        WHERE RDB$SYSTEM_FLAG = 0 
        AND RDB$VIEW_BLR IS NOT NULL
        ORDER BY RDB$RELATION_NAME
    """)
    return [row[0].strip() for row in cursor.fetchall()]

def obtener_columnas(cursor, tabla):
    """Obtener columnas de una tabla"""
    cursor.execute("""
        SELECT rf.RDB$FIELD_NAME, t.RDB$TYPE_NAME, f.RDB$FIELD_LENGTH
        FROM RDB$RELATION_FIELDS rf
        JOIN RDB$FIELDS f ON rf.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME
        JOIN RDB$TYPES t ON f.RDB$FIELD_TYPE = t.RDB$TYPE AND t.RDB$FIELD_NAME = 'RDB$FIELD_TYPE'
        WHERE rf.RDB$RELATION_NAME = ?
        ORDER BY rf.RDB$FIELD_POSITION
    """, (tabla,))
    return cursor.fetchall()

def contar_registros(cursor, tabla):
    """Contar registros de una tabla"""
    try:
        cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
        return cursor.fetchone()[0]
    except:
        return "Error"

def main():
    print("=" * 80)
    print("EXPLORACIÓN DE BASE DE DATOS FIREBIRD")
    print(f"Archivo: {DB_PATH}")
    print("=" * 80)
    print()
    
    try:
        conn = conectar()
        cursor = conn.cursor()
        
        # Mostrar estructura de DEVOLUCIONES
        print("\n" + "=" * 80)
        print("ESTRUCTURA DE LA TABLA DEVOLUCIONES")
        print("-" * 80)
        columnas = obtener_columnas(cursor, "DEVOLUCIONES")
        for col in columnas:
            nombre = col[0].strip() if col[0] else "?"
            tipo = col[1].strip() if col[1] else "?"
            longitud = col[2] if col[2] else ""
            print(f"   - {nombre}: {tipo}({longitud})")

        # Mostrar estructura de la tabla VENTAS (facturas canceladas)
        print("\n" + "=" * 80)
        print("ESTRUCTURA DE LA TABLA VENTAS")
        print("-" * 80)
        columnas = obtener_columnas(cursor, "VENTAS")
        for col in columnas:
            nombre = col[0].strip() if col[0] else "?"
            tipo = col[1].strip() if col[1] else "?"
            longitud = col[2] if col[2] else ""
            print(f"   - {nombre}: {tipo}({longitud})")

        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
