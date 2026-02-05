#!/usr/bin/env python3
"""
Diagnóstico de instalación de Firebird en Windows
Ayuda a encontrar la ruta correcta de isql.exe
"""
import os
import sys
import subprocess
import winreg  # Solo en Windows
from pathlib import Path

print("=" * 60)
print("DIAGNÓSTICO DE FIREBIRD")
print("=" * 60)
print()

# 1. Verificar PATH
print("1. Verificando si 'isql' está en PATH...")
try:
    run_kwargs = {'capture_output': True, 'text': True}
    if sys.platform == 'win32':
        run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    resultado = subprocess.run(['where', 'isql'], **run_kwargs)
    if resultado.returncode == 0:
        print(f"   ✓ Encontrado en PATH: {resultado.stdout.strip()}")
    else:
        print("   ✗ No encontrado en PATH")
except:
    print("   ✗ Error verificando PATH")

print()

# 2. Buscar en rutas estándar
print("2. Buscando en rutas de instalación comunes...")
rutas_a_buscar = [
    r"C:\Program Files\Firebird",
    r"C:\Program Files (x86)\Firebird",
    r"C:\Firebird",
]

encontradas = []
for ruta_base in rutas_a_buscar:
    if os.path.exists(ruta_base):
        print(f"   → Encontrada carpeta: {ruta_base}")
        # Buscar isql.exe dentro
        for root, dirs, files in os.walk(ruta_base):
            for file in files:
                if file.lower() == 'isql.exe':
                    ruta_completa = os.path.join(root, file)
                    encontradas.append(ruta_completa)
                    print(f"      ✓ isql.exe: {ruta_completa}")
    else:
        print(f"   ✗ No existe: {ruta_base}")

print()

# 3. Intentar leer registro de Windows
print("3. Buscando en registro de Windows...")
try:
    # Claves de registro donde Firebird puede estar registrado
    claves = [
        r"SOFTWARE\Classes\Firebird.Database.Manager",
        r"SOFTWARE\Firebird Project",
        r"SOFTWARE\Firebird",
    ]
    
    for clave in claves:
        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, clave)
            print(f"   → Encontrada clave: {clave}")
            try:
                valor = winreg.QueryValue(reg, "")
                print(f"      Valor: {valor}")
            except:
                pass
            winreg.CloseKey(reg)
        except WindowsError:
            pass
except:
    print("   ✗ Error accediendo registro")

print()

# 4. Verificar versión de Firebird
print("4. Intentando verificar versión de Firebird...")
if encontradas:
    isql_path = encontradas[0]  # Usar la primera encontrada
    try:
        run_kwargs = {'capture_output': True, 'text': True, 'timeout': 5}
        if sys.platform == 'win32':
            run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        resultado = subprocess.run([isql_path, '-version'], **run_kwargs)
        print(f"   ✓ Versión: {resultado.stdout.strip()}")
    except:
        print(f"   ✗ No se pudo obtener versión")
else:
    print("   ✗ No se encontró isql.exe para verificar")

print()

# 5. Resumen y recomendaciones
print("=" * 60)
print("RESUMEN Y RECOMENDACIONES")
print("=" * 60)
print()

if encontradas:
    print("✓ Firebird SÍ está instalado")
    print()
    print("Rutas de isql.exe encontradas:")
    for ruta in encontradas:
        print(f"  • {ruta}")
    print()
    print("Usa esta ruta en liquidador_repartidores.py")
else:
    print("✗ Firebird NO parece estar instalado")
    print()
    print("Qué hacer:")
    print("  1. Descarga Firebird desde: https://www.firebirdsql.org/download/")
    print("  2. Instala la versión para Windows (generalmente x64 o x32)")
    print("  3. Anota la ruta de instalación")
    print("  4. Ejecuta este script de nuevo después de instalar")
    print()
    print("O, agrega la carpeta 'bin' de Firebird a tu PATH:")
    print("  - Abre 'Variables de Entorno' en Windows")
    print("  - Busca la carpeta bin dentro de Firebird")
    print("  - Agrégala a la variable PATH")

print()
print("=" * 60)
