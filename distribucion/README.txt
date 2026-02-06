================================================================================
                         LIQUIVENTAS v3.0 - INSTALACIÓN
================================================================================

REQUISITOS:
-----------
• Windows 10 o superior
• Firebird 2.5 instalado (para conexión con Eleventa)
• Archivo PDVDATA.FDB de Eleventa


INSTRUCCIONES DE INSTALACIÓN:
-----------------------------

1. EXTRAER EL CONTENIDO
   Extraer todo el contenido del ZIP en una carpeta de su preferencia.
   Ejemplo: C:\LiquiVentas\

2. COPIAR BASE DE DATOS ELEVENTA
   Copiar el archivo PDVDATA.FDB de Eleventa a la carpeta BDEV.
   
   Ubicación típica de Eleventa:
   C:\Archivos Eleventa\ELEVENTA_DATOS\PDVDATA.FDB
   
   Destino:
   [Carpeta de instalación]\BDEV\PDVDATA.FDB

3. EJECUTAR LA APLICACIÓN
   Doble clic en LiquiVentas.exe

4. CONFIGURAR RUTA DE BASE DE DATOS
   Al iniciar por primera vez:
   - Ir a la barra superior donde dice "Ruta BD Eleventa"
   - Clic en "Examinar" y seleccionar el archivo PDVDATA.FDB en la carpeta BDEV
   - Clic en "Verificar" para confirmar la conexión


ESTRUCTURA DE CARPETAS:
-----------------------
LiquiVentas/
├── LiquiVentas.exe          (Aplicación principal)
├── BDEV/                    (Carpeta para la BD de Eleventa)
│   └── PDVDATA.FDB          (Copiar aquí el archivo de Eleventa)
├── liquiventas_data.db      (Se crea automáticamente - NO BORRAR)
└── README.txt               (Este archivo)


NOTAS IMPORTANTES:
------------------
• La base de datos local (liquiventas_data.db) se crea automáticamente
  en la misma carpeta del ejecutable. Contiene todas las asignaciones,
  créditos y configuraciones. NO BORRAR.

• Si mueve la aplicación a otra carpeta, también debe mover:
  - El archivo PDVDATA.FDB a la nueva carpeta BDEV
  - El archivo liquiventas_data.db (para conservar los datos)

• Para actualizar los datos de Eleventa, simplemente copie una versión
  actualizada del archivo PDVDATA.FDB a la carpeta BDEV.


ATAJOS DE TECLADO:
------------------
• F10         - Enfocar buscador global
• Ctrl+S      - Guardar cambios pendientes
• Ctrl+F      - Buscar en tabla actual
• Enter       - Confirmar selección


SOPORTE:
--------
Desarrollado por JhomaScript
Versión 3.0 - Febrero 2026

================================================================================
