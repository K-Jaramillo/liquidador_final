================================================================================
SISTEMA EXPORTADOR DE VENTAS Y LIQUIDADOR DE REPARTIDORES
================================================================================

INSTRUCCIONES DE USO
================================================================================

1. REQUISITOS PREVIOS
   - Python 3.10 o superior
   - Firebird instalado con isql accesible
   - Archivo PDVDATA.FDB en la carpeta del proyecto

2. INSTALACION DE DEPENDENCIAS
   Ejecutar en terminal:
   
   pip install pandas openpyxl

3. EJECUTAR LAS APLICACIONES

   A) EXPORTADOR DE VENTAS
      -----------------------------------------------
      Permite exportar ventas a Excel/CSV con filtros de crédito y descuentos.
      
      Comando:
      C:\Users\UsoPersonal\Desktop\Repartidores\.venv\Scripts\python.exe ^
      C:\Users\UsoPersonal\Desktop\Repartidores\exportador_ventas.py
      
      O simplemente:
      python exportador_ventas.py

   B) LIQUIDADOR DE REPARTIDORES
      -----------------------------------------------
      Permite asignar repartidores, liquidar ventas, registrar descuentos y gastos.
      
      Comando:
      C:\Users\UsoPersonal\Desktop\Repartidores\.venv\Scripts\python.exe ^
      C:\Users\UsoPersonal\Desktop\Repartidores\liquidador_repartidores.py
      
      O simplemente:
      python liquidador_repartidores.py

4. SELECCIONAR ARCHIVO FDB

   En ambas aplicaciones hay un campo para seleccionar la ruta del archivo FDB:
   
   EXPORTADOR:
   - Campo "Archivo FDB" en la sección de Configuración
   - Botón "Examinar" para seleccionar archivo
   
   LIQUIDADOR:
   - Campo "Archivo FDB" en la barra de Configuración (parte superior)
   - Botón "Examinar" para seleccionar archivo
   - Botón "Verificar" para comprobar conexión

5. ARCHIVOS DEL SISTEMA

   Archivo: exportador_ventas.py
   - Exporta ventas por rango de fechas
   - Filtra por crédito
   - Exporta a Excel/CSV con descuentos incluidos
   
   Archivo: liquidador_repartidores.py
   - Asigna repartidores a facturas
   - Registra descuentos por factura
   - Liquida repartidores
   - Maneja gastos adicionales
   - Conteo de dinero
   
   Archivo: utils_descuentos.py
   - Gestiona descuentos (guardados en descuentos.json)
   
   Archivo: utils_repartidores.py
   - Gestiona asignaciones de repartidores
   
   Archivo: descuentos.json
   - Almacena descuentos registrados (se genera automáticamente)

6. SOLUCIONAR PROBLEMAS

   Error: "Archivo no encontrado: /home/..."
   - Haz clic en "Examinar" y selecciona la ruta correcta del PDVDATA.FDB
   - En Windows: C:\Users\...\Repartidores\PDVDATA.FDB
   
   Error: "Error BD - No se pudo consultar"
   - Verifica que Firebird esté instalado y accesible
   - Comprueba que el archivo PDVDATA.FDB existe
   - En Liquidador, usa botón "Verificar" para probar conexión
   
   Error: "ModuleNotFoundError: No module named 'pandas'"
   - Instala pandas: pip install pandas
   - Instala openpyxl: pip install openpyxl

7. DATOS GUARDADOS

   Descuentos: descuentos.json (en la carpeta del proyecto)
   Reportes: Se generan en la carpeta actual del proyecto

8. COMANDOS RAPIDOS

   Verificar Python instalado:
   python --version
   
   Instalar dependencias:
   pip install pandas openpyxl
   
   Compilar archivo Python (verificar sintaxis):
   python -m py_compile exportador_ventas.py

================================================================================
VERSION: 2.0
FECHA: 31 de enero de 2026
================================================================================
