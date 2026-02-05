#!/usr/bin/env python3
"""
Script para probar la conexión a Firebird y verificar que isql funciona
"""
import subprocess
import sys
import os

print("=" * 60)
print("TEST DE CONEXIÓN A FIREBIRD")
print("=" * 60)
print()

# 1. Verificar si isql.exe existe
# Usar ruta relativa al proyecto
ruta_fdb = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PDVDATA.FDB')
isql_paths = [
    r"C:\Program Files (x86)\Firebird\Firebird_2_5\bin\isql.exe",
    r"C:\Program Files\Firebird\Firebird_2_5\bin\isql.exe",
]

print("1. Buscando isql.exe...")
isql_encontrado = None
for path in isql_paths:
    if os.path.exists(path):
        print(f"   ✓ Encontrado: {path}")
        isql_encontrado = path
        break

if not isql_encontrado:
    print("   ✗ No se encontró isql.exe")
    exit(1)

print()

# 2. Verificar que la BD existe
print("2. Verificando archivo FDB...")
if os.path.exists(ruta_fdb):
    print(f"   ✓ Encontrado: {ruta_fdb}")
else:
    print(f"   ✗ No encontrado: {ruta_fdb}")
    exit(1)

print()

# 3. Intentar ejecutar una consulta simple
print("3. Ejecutando consulta de prueba...")
sql = "SELECT COUNT(*) as TEST FROM RDB$RELATIONS;\nQUIT;"

try:
    run_kwargs = {
        'input': sql,
        'capture_output': True,
        'text': True,
        'timeout': 10,
        'encoding': 'cp1252',
        'errors': 'ignore'
    }
    if sys.platform == 'win32':
        run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    resultado = subprocess.run(
        [isql_encontrado, '-u', 'SYSDBA', '-p', 'masterkey', ruta_fdb],
        **run_kwargs
    )
    
    print(f"   Return code: {resultado.returncode}")
    if resultado.returncode == 0:
        print("   ✓ Conexión exitosa")
        print()
        print("   Output:")
        for linea in resultado.stdout.split('\n')[:10]:
            if linea.strip():
                print(f"   > {linea}")
    else:
        print("   ✗ Error en la consulta")
        print(f"   Error: {resultado.stderr[:200]}")
except Exception as e:
    print(f"   ✗ Excepción: {str(e)}")

print()
print("=" * 60)
print("FIN DEL TEST")
print("=" * 60)
