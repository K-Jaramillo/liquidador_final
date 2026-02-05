#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico de Firebird para Linux
Verifica la instalación de Firebird y la conectividad con la base de datos
"""

import os
import sys
import subprocess
import shutil

def print_header(titulo):
    print("\n" + "=" * 60)
    print(f"  {titulo}")
    print("=" * 60)

def print_ok(msg):
    print(f"  ✅ {msg}")

def print_error(msg):
    print(f"  ❌ {msg}")

def print_warn(msg):
    print(f"  ⚠️  {msg}")

def print_info(msg):
    print(f"  ℹ️  {msg}")

def main():
    print_header("DIAGNÓSTICO DE FIREBIRD PARA LINUX")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # =========================================================================
    # 1. Verificar bibliotecas bundled de Firebird 2.5
    # =========================================================================
    print_header("1. Bibliotecas de Firebird 2.5 bundled")
    
    fb25_lib = os.path.join(base_path, 'firebird25_lib')
    fb25_bin = os.path.join(base_path, 'firebird25_bin')
    
    if os.path.exists(fb25_lib):
        print_ok(f"Directorio encontrado: {fb25_lib}")
        
        # Verificar archivos clave
        archivos_requeridos = [
            'libfbembed.so.2.5.9',
            'libfbclient.so.2.5.9',
            'security2.fdb',
            'firebird.conf'
        ]
        for archivo in archivos_requeridos:
            ruta = os.path.join(fb25_lib, archivo)
            if os.path.exists(ruta):
                print_ok(f"  {archivo}")
            else:
                print_warn(f"  {archivo} (no encontrado)")
    else:
        print_error(f"No encontrado: {fb25_lib}")
        print_info("Ejecuta el script de instalación para configurar Firebird 2.5")
    
    if os.path.exists(fb25_bin):
        isql_bundled = os.path.join(fb25_bin, 'isql')
        if os.path.exists(isql_bundled):
            print_ok(f"isql bundled encontrado: {isql_bundled}")
        else:
            print_warn("isql bundled no encontrado")
    else:
        print_warn(f"Directorio bin no encontrado: {fb25_bin}")
    
    # =========================================================================
    # 2. Verificar isql del sistema
    # =========================================================================
    print_header("2. Verificación de isql en el sistema")
    
    rutas_isql = [
        '/usr/bin/isql-fb',
        '/usr/bin/isql',
        '/opt/firebird/bin/isql',
    ]
    
    isql_encontrado = None
    for ruta in rutas_isql:
        if os.path.exists(ruta):
            print_ok(f"Encontrado: {ruta}")
            isql_encontrado = ruta
            break
    
    if not isql_encontrado:
        isql_in_path = shutil.which('isql-fb') or shutil.which('isql')
        if isql_in_path:
            print_ok(f"Encontrado en PATH: {isql_in_path}")
            isql_encontrado = isql_in_path
        else:
            print_warn("No se encontró isql del sistema")
    
    # =========================================================================
    # 3. Verificar base de datos
    # =========================================================================
    print_header("3. Base de datos PDVDATA.FDB")
    
    db_path = os.path.join(base_path, 'PDVDATA.FDB')
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print_ok(f"Encontrada: {db_path}")
        print_info(f"Tamaño: {size_mb:.2f} MB")
    else:
        print_error(f"No encontrada: {db_path}")
    
    # =========================================================================
    # 4. Probar conexión con biblioteca embebida
    # =========================================================================
    print_header("4. Prueba de conexión (fdb + Firebird 2.5 embebido)")
    
    try:
        # Importar el módulo de configuración
        sys.path.insert(0, base_path)
        from core.firebird_setup import get_firebird_setup, get_fdb_connection
        
        setup = get_firebird_setup()
        print_info(f"Biblioteca: {setup.fb_library_name}")
        print_info(f"isql: {setup.isql_path}")
        
        conn = get_fdb_connection()
        print_ok("¡Conexión exitosa!")
        
        cur = conn.cursor()
        cur.execute("SELECT FIRST 1 RDB$RELATION_NAME FROM RDB$RELATIONS WHERE RDB$SYSTEM_FLAG = 0")
        row = cur.fetchone()
        if row:
            print_ok(f"Tabla de prueba: {row[0].strip()}")
        
        conn.close()
        print_ok("Conexión cerrada correctamente")
        
    except ImportError as e:
        print_error(f"Error importando módulos: {e}")
    except Exception as e:
        print_error(f"Error de conexión: {e}")
    
    # =========================================================================
    # 5. Probar isql bundled
    # =========================================================================
    print_header("5. Prueba de isql bundled")
    
    isql_bundled = os.path.join(fb25_bin, 'isql')
    if os.path.exists(isql_bundled) and os.path.exists(db_path):
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = f"{fb25_lib}:{env.get('LD_LIBRARY_PATH', '')}"
        env['FIREBIRD'] = fb25_lib
        
        try:
            result = subprocess.run(
                [isql_bundled, '-z'],
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )
            if 'ISQL Version' in result.stdout:
                version = result.stdout.split('\n')[0]
                print_ok(f"isql funciona: {version}")
            else:
                print_warn(f"Respuesta inesperada: {result.stdout[:100]}")
        except Exception as e:
            print_error(f"Error ejecutando isql: {e}")
    else:
        print_warn("No se puede probar isql bundled (archivos faltantes)")
    
    # =========================================================================
    # Resumen
    # =========================================================================
    print_header("RESUMEN")
    print_info("Si todos los checks están en verde (✅), Firebird está listo.")
    print_info("Para iniciar la aplicación, usa: ./iniciar_linux.sh")
    print()

if __name__ == '__main__':
    main()
