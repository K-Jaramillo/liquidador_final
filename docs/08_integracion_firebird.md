# 🔥 8. INTEGRACIÓN CON FIREBIRD

Documentación de la conexión con la base de datos Firebird de Eleventa.

---

## 8.1 Arquitectura de Conexión

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA DE INTEGRACIÓN                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│  │   ELEVENTA  │         │   FIREBIRD  │         │ LIQUIDADOR  │           │
│  │    (POS)    │────────►│  PDVDATA    │◄────────│   (Python)  │           │
│  │             │         │    .FDB     │         │             │           │
│  └─────────────┘         └─────────────┘         └─────────────┘           │
│       │                        │                        │                   │
│       │                        │                        │                   │
│  Escribe datos            Base de datos           Lee datos                 │
│  de ventas               compartida              de ventas                  │
│                                                                             │
│                                                                             │
│  MODO DE CONEXIÓN: Firebird 2.5 Embedded                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   LINUX (Embedded)                                  │    │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │    │
│  │  │ isql-fb      │    │ libfbclient  │    │ PDVDATA.FDB  │          │    │
│  │  │ (cliente)    │───►│ (librería)   │───►│ (base datos) │          │    │
│  │  └──────────────┘    └──────────────┘    └──────────────┘          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8.2 Configuración en Linux

### 8.2.1 Estructura de Directorios

```
liquidador_final/
├── firebird25_bin/           # Binarios de Firebird
│   ├── isql-fb               # Cliente SQL interactivo
│   └── ...
│
├── firebird25_lib/           # Librerías de Firebird
│   ├── libfbclient.so.2      # Cliente Firebird
│   ├── libfbembed.so.2.5     # Motor embebido
│   ├── libicudata.so.30      # ICU data
│   ├── libicui18n.so.30      # ICU internacionalización
│   └── libicuuc.so.30        # ICU unicode
│
└── config_firebird.py        # Configuración de conexión
```

### 8.2.2 Variables de Entorno

```python
# config_firebird.py

import os
import platform

def configurar_firebird_linux():
    """
    Configura las variables de entorno para Firebird embebido en Linux.
    """
    
    # Directorio de la aplicación
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Rutas de Firebird
    firebird_lib = os.path.join(app_dir, 'firebird25_lib')
    firebird_bin = os.path.join(app_dir, 'firebird25_bin')
    
    # Configurar LD_LIBRARY_PATH para las librerías
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    if firebird_lib not in ld_path:
        os.environ['LD_LIBRARY_PATH'] = f"{firebird_lib}:{ld_path}"
    
    # Ruta al cliente isql
    isql_path = os.path.join(firebird_bin, 'isql-fb')
    
    return {
        'lib_path': firebird_lib,
        'bin_path': firebird_bin,
        'isql': isql_path
    }
```

### 8.2.3 Script de Inicio (Linux)

```bash
#!/bin/bash
# iniciar_linux.sh

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configurar librerías de Firebird
export LD_LIBRARY_PATH="$SCRIPT_DIR/firebird25_lib:$LD_LIBRARY_PATH"

# Ejecutar la aplicación
cd "$SCRIPT_DIR"
python3 main.py
```

---

## 8.3 Ejecución de Consultas

### 8.3.1 Método Principal

```python
def ejecutar_consulta_firebird(sql, db_path):
    """
    Ejecuta una consulta SQL en Firebird usando isql-fb.
    
    Parámetros:
        sql: Consulta SQL a ejecutar
        db_path: Ruta completa al archivo .FDB
    
    Retorna:
        str: Resultado de la consulta en texto
    
    IMPORTANTE para Linux:
        - NO usar -ch WIN1252 (causa error de encoding)
        - El sistema usa UTF-8 por defecto
    """
    import subprocess
    import tempfile
    
    # Configurar Firebird
    config = configurar_firebird_linux()
    isql = config['isql']
    
    # Crear archivo temporal con la consulta
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(sql)
        f.write('\n')
        sql_file = f.name
    
    try:
        # Construir comando
        # NOTA: En Linux NO incluir -ch WIN1252
        cmd = [
            isql,
            '-user', 'SYSDBA',
            '-password', 'masterkey',
            '-i', sql_file,
            db_path
        ]
        
        # Configurar entorno
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = f"{config['lib_path']}:{env.get('LD_LIBRARY_PATH', '')}"
        
        # Ejecutar
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        
        if result.returncode != 0:
            raise Exception(f"Error Firebird: {result.stderr}")
        
        return result.stdout
        
    finally:
        # Limpiar archivo temporal
        os.unlink(sql_file)
```

### 8.3.2 Parser de Resultados

```python
def parsear_resultado_isql(output):
    """
    Convierte la salida de isql-fb a lista de diccionarios.
    
    La salida de isql tiene formato:
    
    CAMPO1     CAMPO2      CAMPO3
    ========== =========== ===========
    valor1     valor2      valor3
    valor4     valor5      valor6
    
    """
    lines = output.strip().split('\n')
    
    if len(lines) < 3:
        return []
    
    # Primera línea: nombres de campos
    headers = lines[0].split()
    
    # Segunda línea: separadores (ignorar)
    # Líneas siguientes: datos
    
    results = []
    for line in lines[2:]:
        if line.strip() and not line.startswith('='):
            # Dividir por espacios, respetando anchos
            values = line.split()
            
            # Crear diccionario
            row = {}
            for i, header in enumerate(headers):
                if i < len(values):
                    row[header] = values[i]
                else:
                    row[header] = None
            
            results.append(row)
    
    return results
```

---

## 8.4 Consultas Principales

### 8.4.1 Obtener Facturas del Día

```sql
-- Consulta: Facturas de una fecha específica
SELECT 
    d.IDDOCUMENTO,
    d.FOLIO,
    d.FECHAHORAVENTA,
    d.TOTAL,
    d.SUBTOTAL,
    d.TOTALIMPUESTO,
    d.STATUS,
    d.IDFORMADEPAGO,
    c.RAZONSOCIAL AS CLIENTE
FROM DOCUMENTO d
LEFT JOIN CLIENTE c ON d.IDCLIENTE = c.IDCLIENTE
WHERE CAST(d.FECHAHORAVENTA AS DATE) = '2026-02-05'
  AND d.STATUS <> 'C'  -- Excluir canceladas
ORDER BY d.FOLIO;
```

### 8.4.2 Obtener Corte de Caja

```sql
-- Consulta: Corte de caja de una fecha
SELECT 
    c.IDCORTE,
    c.FECHA,
    c.EFECTIVO,
    c.TARJETA,
    c.CHEQUE,
    c.VALES,
    c.CREDITO,
    c.TOTAL,
    c.FONDO
FROM CORTE c
WHERE CAST(c.FECHA AS DATE) = '2026-02-05'
ORDER BY c.FECHA DESC;
```

### 8.4.3 Obtener Cancelaciones

```sql
-- Consulta: Facturas canceladas en una fecha
SELECT 
    d.IDDOCUMENTO,
    d.FOLIO,
    d.FECHAHORAVENTA,
    d.TOTAL,
    d.STATUS
FROM DOCUMENTO d
WHERE CAST(d.FECHAHORAVENTA AS DATE) = '2026-02-05'
  AND d.STATUS = 'C'  -- Solo canceladas
ORDER BY d.FOLIO;
```

### 8.4.4 Obtener Formas de Pago

```sql
-- Consulta: Formas de pago disponibles
SELECT 
    IDFORMADEPAGO,
    NOMBRE,
    DESCRIPCION
FROM FORMADEPAGO
WHERE ACTIVO = 1;
```

### 8.4.5 Obtener Clientes

```sql
-- Consulta: Lista de clientes
SELECT 
    IDCLIENTE,
    RAZONSOCIAL,
    RFC,
    DIRECCION,
    TELEFONO,
    LIMITECREDITO,
    SALDOPENDIENTE
FROM CLIENTE
WHERE ACTIVO = 1
ORDER BY RAZONSOCIAL;
```

---

## 8.5 Tablas de Firebird Utilizadas

### 8.5.1 Diagrama de Tablas

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TABLAS DE FIREBIRD (ELEVENTA)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐         ┌───────────────┐         ┌───────────────┐     │
│  │   DOCUMENTO   │────────►│ DOCTODETALLE  │◄────────│   ARTICULO    │     │
│  │   (Facturas)  │         │   (Items)     │         │  (Productos)  │     │
│  └───────────────┘         └───────────────┘         └───────────────┘     │
│         │                                                                   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌───────────────┐         ┌───────────────┐                               │
│  │    CLIENTE    │         │    CORTE      │                               │
│  │               │         │   (Cierre)    │                               │
│  └───────────────┘         └───────────────┘                               │
│                                                                             │
│  ┌───────────────┐         ┌───────────────┐                               │
│  │ FORMADEPAGO   │         │   USUARIO     │                               │
│  │               │         │               │                               │
│  └───────────────┘         └───────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.5.2 Campos Importantes

#### DOCUMENTO (Facturas)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| IDDOCUMENTO | INTEGER | PK - ID único |
| FOLIO | VARCHAR(20) | Número de factura |
| FECHAHORAVENTA | TIMESTAMP | Fecha y hora |
| TOTAL | DECIMAL(15,2) | Total de la venta |
| SUBTOTAL | DECIMAL(15,2) | Subtotal sin impuestos |
| TOTALIMPUESTO | DECIMAL(15,2) | IVA |
| STATUS | CHAR(1) | A=Activa, C=Cancelada |
| IDFORMADEPAGO | INTEGER | FK a FORMADEPAGO |
| IDCLIENTE | INTEGER | FK a CLIENTE |

#### CORTE (Cierre de Caja)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| IDCORTE | INTEGER | PK - ID único |
| FECHA | TIMESTAMP | Fecha del corte |
| EFECTIVO | DECIMAL(15,2) | Total en efectivo |
| TARJETA | DECIMAL(15,2) | Total en tarjeta |
| CREDITO | DECIMAL(15,2) | Total a crédito |
| TOTAL | DECIMAL(15,2) | Gran total |
| FONDO | DECIMAL(15,2) | Fondo de caja |

#### CLIENTE

| Campo | Tipo | Descripción |
|-------|------|-------------|
| IDCLIENTE | INTEGER | PK - ID único |
| RAZONSOCIAL | VARCHAR(100) | Nombre del cliente |
| RFC | VARCHAR(15) | RFC fiscal |
| LIMITECREDITO | DECIMAL(15,2) | Límite de crédito |
| SALDOPENDIENTE | DECIMAL(15,2) | Adeudo actual |

---

## 8.6 Manejo de Errores

### 8.6.1 Errores Comunes

```python
ERRORES_FIREBIRD = {
    'connection_refused': {
        'mensaje': 'No se puede conectar a la base de datos',
        'causa': 'Archivo FDB no accesible o bloqueado',
        'solucion': 'Verificar que Eleventa no esté usando el archivo'
    },
    'file_not_found': {
        'mensaje': 'Archivo de base de datos no encontrado',
        'causa': 'PDVDATA.FDB no existe en la ruta configurada',
        'solucion': 'Verificar ruta en configuración'
    },
    'library_not_found': {
        'mensaje': 'Librerías de Firebird no encontradas',
        'causa': 'LD_LIBRARY_PATH no configurado correctamente',
        'solucion': 'Ejecutar desde iniciar_linux.sh'
    },
    'encoding_error': {
        'mensaje': 'Error de codificación de caracteres',
        'causa': 'Uso de -ch WIN1252 en Linux',
        'solucion': 'No usar parámetro -ch en Linux'
    },
    'permission_denied': {
        'mensaje': 'Permiso denegado al acceder a la BD',
        'causa': 'Usuario sin permisos de lectura',
        'solucion': 'Verificar permisos del archivo FDB'
    }
}
```

### 8.6.2 Función de Manejo de Errores

```python
def manejar_error_firebird(error_msg):
    """
    Analiza el mensaje de error y proporciona solución.
    """
    import re
    
    error_lower = error_msg.lower()
    
    if 'library' in error_lower or 'libfbclient' in error_lower:
        return {
            'tipo': 'library_not_found',
            'mensaje': 'Librerías de Firebird no encontradas',
            'accion': 'Verificar que firebird25_lib/ contiene las librerías'
        }
    
    if 'permission' in error_lower or 'access' in error_lower:
        return {
            'tipo': 'permission_denied',
            'mensaje': 'Sin permisos para acceder a la base de datos',
            'accion': 'Ejecutar: chmod 644 /ruta/PDVDATA.FDB'
        }
    
    if 'not found' in error_lower or 'no such file' in error_lower:
        return {
            'tipo': 'file_not_found',
            'mensaje': 'Archivo de base de datos no encontrado',
            'accion': 'Verificar ruta a PDVDATA.FDB en configuración'
        }
    
    if 'character' in error_lower or 'encoding' in error_lower:
        return {
            'tipo': 'encoding_error',
            'mensaje': 'Error de codificación',
            'accion': 'No usar -ch WIN1252 en Linux'
        }
    
    return {
        'tipo': 'unknown',
        'mensaje': error_msg,
        'accion': 'Revisar logs para más detalles'
    }
```

---

## 8.7 Funciones de Alto Nivel

### 8.7.1 Cargar Facturas del Día

```python
def cargar_facturas_firebird(fecha, db_path):
    """
    Carga todas las facturas de una fecha desde Firebird.
    
    Retorna:
        list: Lista de diccionarios con datos de facturas
    """
    
    sql = f"""
    SELECT 
        d.IDDOCUMENTO,
        d.FOLIO,
        d.FECHAHORAVENTA,
        d.TOTAL,
        d.STATUS,
        d.IDFORMADEPAGO,
        COALESCE(c.RAZONSOCIAL, 'PUBLICO GENERAL') AS CLIENTE
    FROM DOCUMENTO d
    LEFT JOIN CLIENTE c ON d.IDCLIENTE = c.IDCLIENTE
    WHERE CAST(d.FECHAHORAVENTA AS DATE) = '{fecha}'
    ORDER BY d.FOLIO;
    """
    
    try:
        output = ejecutar_consulta_firebird(sql, db_path)
        facturas = parsear_resultado_isql(output)
        
        # Convertir tipos
        for f in facturas:
            f['TOTAL'] = float(f.get('TOTAL', 0) or 0)
            f['CANCELADA'] = f.get('STATUS') == 'C'
        
        return facturas
        
    except Exception as e:
        error_info = manejar_error_firebird(str(e))
        raise Exception(f"{error_info['mensaje']}: {error_info['accion']}")
```

### 8.7.2 Obtener Corte de Cajero

```python
def obtener_corte_cajero(fecha, db_path):
    """
    Obtiene el corte de caja más reciente de una fecha.
    
    Retorna:
        dict: Datos del corte o None si no existe
    """
    
    sql = f"""
    SELECT FIRST 1
        c.IDCORTE,
        c.FECHA,
        c.EFECTIVO,
        c.TARJETA,
        c.CREDITO,
        c.TOTAL,
        c.FONDO
    FROM CORTE c
    WHERE CAST(c.FECHA AS DATE) = '{fecha}'
    ORDER BY c.FECHA DESC;
    """
    
    try:
        output = ejecutar_consulta_firebird(sql, db_path)
        cortes = parsear_resultado_isql(output)
        
        if cortes:
            corte = cortes[0]
            # Convertir a float
            for campo in ['EFECTIVO', 'TARJETA', 'CREDITO', 'TOTAL', 'FONDO']:
                corte[campo] = float(corte.get(campo, 0) or 0)
            return corte
        
        return None
        
    except Exception as e:
        error_info = manejar_error_firebird(str(e))
        raise Exception(f"{error_info['mensaje']}: {error_info['accion']}")
```

---

## 8.8 Modo Solo Lectura

### 8.8.1 Principio

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    IMPORTANTE: MODO SOLO LECTURA                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  El Liquidador NUNCA escribe en la base de datos de Firebird.                 ║
║                                                                               ║
║  ┌───────────────────┐                       ┌───────────────────┐            ║
║  │     ELEVENTA      │  ────── ESCRIBE ────► │   PDVDATA.FDB     │            ║
║  │     (POS)         │                       │                   │            ║
║  └───────────────────┘                       └───────────────────┘            ║
║                                                      │                        ║
║                                                      │                        ║
║                                               LEE SOLAMENTE                   ║
║                                                      │                        ║
║                                                      ▼                        ║
║                                              ┌───────────────────┐            ║
║                                              │    LIQUIDADOR     │            ║
║                                              │     (Python)      │            ║
║                                              └───────────────────┘            ║
║                                                      │                        ║
║                                                      │                        ║
║                                               ESCRIBE EN                      ║
║                                                      │                        ║
║                                                      ▼                        ║
║                                              ┌───────────────────┐            ║
║                                              │ liquidador_data.db│            ║
║                                              │    (SQLite)       │            ║
║                                              └───────────────────┘            ║
║                                                                               ║
║  Razones:                                                                     ║
║  • Evitar conflictos con Eleventa                                             ║
║  • Mantener integridad de datos de ventas                                     ║
║  • Separación de responsabilidades                                            ║
║  • Facilitar respaldos independientes                                         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 8.9 Troubleshooting

### 8.9.1 Checklist de Conexión

```
☐ isql-fb tiene permisos de ejecución
   chmod +x firebird25_bin/isql-fb

☐ Librerías en firebird25_lib/
   ls -la firebird25_lib/
   → libfbclient.so.2
   → libfbembed.so.2.5
   → libicudata.so.30
   → libicui18n.so.30
   → libicuuc.so.30

☐ LD_LIBRARY_PATH configurado
   echo $LD_LIBRARY_PATH
   → Debe incluir ruta a firebird25_lib/

☐ PDVDATA.FDB accesible
   ls -la /ruta/a/PDVDATA.FDB
   → Debe tener permisos de lectura

☐ Eleventa no está bloqueando el archivo
   lsof /ruta/a/PDVDATA.FDB
   → Verificar que no hay bloqueo exclusivo
```

### 8.9.2 Comandos de Diagnóstico

```bash
# Verificar librerías
ldd firebird25_bin/isql-fb

# Probar conexión manual
export LD_LIBRARY_PATH=/ruta/firebird25_lib:$LD_LIBRARY_PATH
./firebird25_bin/isql-fb -user SYSDBA -password masterkey /ruta/PDVDATA.FDB

# Consulta de prueba
SELECT FIRST 5 * FROM DOCUMENTO;
```

---

*Volver al [README](README.md)*
