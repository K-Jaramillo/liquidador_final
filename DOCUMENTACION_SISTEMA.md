# 📚 DOCUMENTACIÓN DEL SISTEMA LIQUIDADOR DE REPARTIDORES

**Versión:** 2.1.0  
**Última actualización:** 5 de Febrero de 2026  
**Plataformas soportadas:** Windows, Linux (Ubuntu/Debian)

---

## 📑 ÍNDICE

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Módulos del Sistema](#3-módulos-del-sistema)
4. [Base de Datos](#4-base-de-datos)
5. [Operaciones por Módulo](#5-operaciones-por-módulo)
6. [Flujo de Trabajo](#6-flujo-de-trabajo)
7. [Cálculos Financieros](#7-cálculos-financieros)
8. [Integración con Firebird (Eleventa)](#8-integración-con-firebird-eleventa)

---

## 1. DESCRIPCIÓN GENERAL

El **Liquidador de Repartidores** es una aplicación de escritorio desarrollada en Python con interfaz gráfica Tkinter. Su propósito principal es gestionar la liquidación diaria de ventas, asignación de repartidores, control de gastos y cuadre de caja.

### Características Principales:
- 📊 Carga automática de facturas desde Firebird (Eleventa PDV)
- 👥 Asignación de facturas a repartidores
- 💰 Control de gastos, préstamos, pagos a proveedores
- 🧮 Conteo de dinero físico con denominaciones
- 📋 Descuentos y ajustes por factura
- 💳 Gestión de créditos punteados
- 📝 Sistema de anotaciones (sticky notes)
- 📈 Cuadre general de caja

---

## 2. ARQUITECTURA DEL SISTEMA

### Estructura de Archivos:
```
liquidador_final/
├── main.py                    # Punto de entrada de la aplicación
├── liquidador_repartidores.py # Clase principal y toda la lógica de UI
├── database_local.py          # Funciones de acceso a SQLite
├── corte_cajero.py           # Integración con Firebird/Eleventa
├── exportador_ventas.py      # Exportación de datos
├── utils_descuentos.py       # Utilidades para descuentos
├── utils_repartidores.py     # Utilidades para repartidores
├── core/
│   ├── config.py             # Configuración global
│   ├── datastore.py          # Modelo de datos
│   ├── database.py           # Conexión Firebird
│   └── firebird_setup.py     # Configuración Firebird Linux
├── gui/
│   ├── styles.py             # Estilos visuales
│   └── widgets.py            # Widgets personalizados
├── firebird25_lib/           # Librerías Firebird (Linux)
├── firebird25_bin/           # Binarios Firebird (Linux)
├── PDVDATA.FDB               # Base de datos Firebird (Eleventa)
└── liquidador_data.db        # Base de datos SQLite local
```

### Clases Principales:

#### `DataStore`
Mantiene el estado global de la aplicación. Todas las pestañas leen/escriben aquí para sincronización automática.

```python
class DataStore:
    fecha: str                    # Fecha actual de trabajo
    ventas: list                  # Lista de facturas del día
    _repartidores: set            # Conjunto de repartidores activos
    devoluciones: list            # Devoluciones del día
    movimientos_entrada: list     # Ingresos extras
    movimientos_salida: list      # Salidas de efectivo
```

#### `LiquidadorRepartidores`
Clase principal que contiene la interfaz gráfica y toda la lógica de negocio.

---

## 3. MÓDULOS DEL SISTEMA

El sistema está organizado en **7 pestañas (tabs)** principales:

### 3.1 📋 Tab: Asignar Repartidores
**Archivo:** `_crear_tab_asignacion()` (línea ~2070)

**Funcionalidad:**
- Carga facturas del día desde Firebird
- Permite asignar/desasignar repartidores a cada factura
- Filtros por estado (Todos, Sin Repartidor, Canceladas, Crédito)
- Búsqueda por texto (folio, cliente)
- Colores distintivos por estado de factura

**Operaciones disponibles:**
| Operación | Descripción |
|-----------|-------------|
| Asignar Repartidor | Asigna un repartidor a una factura seleccionada |
| Quitar Asignación | Remueve el repartidor de una factura |
| Asignar Múltiple | Asigna el mismo repartidor a varias facturas seleccionadas |
| Limpiar Todas | Elimina todas las asignaciones del día |
| Exportar | Exporta las asignaciones a archivo |

---

### 3.2 📊 Tab: Liquidación
**Archivo:** `_crear_tab_liquidacion()` (línea ~3652)

**Funcionalidad:**
- Muestra el resumen financiero del día
- Carga datos del Corte de Caja (Eleventa)
- Calcula totales de ventas, cancelaciones, créditos
- Presenta el cuadre general

**Secciones de la Liquidación:**

#### Columna 1: DESCUENTOS Y AJUSTES
| Concepto | Descripción |
|----------|-------------|
| (-) Ajustes de Precios | Descuentos tipo 'ajuste' aplicados a facturas |
| (-) Gastos Repartidores | Total de gastos de repartidores (excluye cajero) |
| (-) Gastos Cajero | Gastos específicos del cajero |
| (-) Pago Proveedores | Pagos realizados a proveedores |
| (-) Préstamos | Préstamos otorgados |
| (-) Nómina | Pagos de nómina del día |
| (-) Socios | Retiros o pagos a socios |
| (-) Transferencias | Transferencias bancarias realizadas |
| **= Total Descuentos** | Suma de todos los descuentos |

#### Columna 2: CUADRE GENERAL
| Concepto | Descripción |
|----------|-------------|
| Total Dinero Caja | Efectivo según corte de caja Eleventa |
| (-) Total Descuentos | Suma de columna 1 |
| (-) Créditos Punteados | Créditos marcados como punteados |
| **= TOTAL EFECTIVO CAJA** | Efectivo esperado en caja |
| 💵 Conteo de Dinero | Efectivo contado físicamente |
| 📊 Diferencia Final | Conteo - Efectivo esperado |

#### Columna 3: RESULTADO FINAL
| Concepto | Descripción |
|----------|-------------|
| Total Facturado | Suma de todas las facturas del día |
| (-) Canceladas | Facturas canceladas el mismo día |
| **= Total Vendido** | Ventas netas del día |
| Facturas a Crédito | Total de ventas a crédito |
| **Neto a Entregar** | Efectivo final a entregar |

---

### 3.3 💵 Tab: Descuentos por Factura
**Archivo:** `_crear_tab_descuentos()` (línea ~5505)

**Funcionalidad:**
- Permite aplicar descuentos específicos a facturas individuales
- Tipos de descuento: Ajuste, Crédito, Devolución
- Persistencia automática en SQLite

**Operaciones:**
| Operación | Descripción |
|-----------|-------------|
| Agregar Descuento | Aplica un descuento a una factura |
| Editar Descuento | Modifica un descuento existente |
| Eliminar Descuento | Remueve un descuento |
| Ver Historial | Muestra el historial de descuentos de una factura |

**Tipos de Descuento:**
- **Ajuste**: Ajustes de precio (no afecta crédito)
- **Crédito**: Aplicado a facturas de crédito
- **Devolución**: Devolución parcial o total

---

### 3.4 💳 Tab: Gastos Adicionales
**Archivo:** `_crear_tab_gastos()` (línea ~6188)

**Funcionalidad:**
- Registro de gastos por repartidor
- Pagos a proveedores
- Préstamos
- Pagos de nómina
- Pagos a socios
- Transferencias bancarias

**Secciones:**

#### Gastos Repartidor
| Campo | Descripción |
|-------|-------------|
| Repartidor | Persona responsable del gasto |
| Concepto | Motivo del gasto (autocompletado) |
| Monto | Cantidad en pesos |
| Observaciones | Notas adicionales |

#### Pago a Proveedores
| Campo | Descripción |
|-------|-------------|
| Proveedor | Nombre del proveedor |
| Concepto | Descripción del pago |
| Monto | Cantidad pagada |
| Repartidor | Quien realizó el pago (opcional) |

#### Préstamos
| Campo | Descripción |
|-------|-------------|
| Repartidor | Persona que recibe el préstamo |
| Concepto | Motivo del préstamo |
| Monto | Cantidad prestada |

#### Nómina
| Campo | Descripción |
|-------|-------------|
| Empleado | Nombre del empleado |
| Concepto | Tipo de pago (sueldo, bono, etc.) |
| Monto | Cantidad pagada |

#### Socios
| Campo | Descripción |
|-------|-------------|
| Socio | Nombre del socio |
| Concepto | Motivo del retiro/pago |
| Monto | Cantidad |

#### Transferencias
| Campo | Descripción |
|-------|-------------|
| Destinatario | Persona/Cuenta destino |
| Concepto | Descripción de la transferencia |
| Monto | Cantidad transferida |

---

### 3.5 💰 Tab: Conteo de Dinero
**Archivo:** `_crear_tab_dinero()` (línea ~6934)

**Funcionalidad:**
- Conteo de efectivo por denominaciones
- Múltiples sesiones de conteo por repartidor
- Cálculo automático de totales

**Denominaciones Soportadas:**
| Billetes | Monedas |
|----------|---------|
| $1000 | $20 |
| $500 | $10 |
| $200 | $5 |
| $100 | $2 |
| $50 | $1 |
| $20 | $0.50 |

**Operaciones:**
| Operación | Descripción |
|-----------|-------------|
| Nueva Sesión | Crea un nuevo conteo |
| Guardar Conteo | Guarda el conteo actual |
| Eliminar Sesión | Borra una sesión de conteo |
| Ver Total | Muestra el total acumulado |

---

### 3.6 📝 Tab: Anotaciones
**Archivo:** `_crear_tab_anotaciones()` (línea ~1816)

**Funcionalidad:**
- Sistema de notas adhesivas (sticky notes)
- Colores personalizables
- Persistencia por fecha

**Operaciones:**
| Operación | Descripción |
|-----------|-------------|
| Nueva Nota | Crea una nota vacía |
| Editar Nota | Modifica contenido/color |
| Eliminar Nota | Borra la nota |
| Cambiar Color | Personaliza el color de fondo |

**Colores Disponibles:**
- 🟡 Amarillo (default)
- 🔵 Azul
- 🟢 Verde
- 🟣 Rosa
- 🟠 Naranja

---

### 3.7 💳 Tab: Créditos Punteados
**Archivo:** `_crear_tab_creditos_punteados()` (línea ~1224)

**Funcionalidad:**
- Lista de facturas a crédito del día
- Marcado de créditos "punteados" (verificados/cobrados)
- Seguimiento de abonos

**Operaciones:**
| Operación | Descripción |
|-----------|-------------|
| Marcar Punteado | Indica que el crédito fue verificado |
| Desmarcar | Quita la marca de punteado |
| Registrar Abono | Agrega un abono al crédito |
| Ver Historial | Muestra abonos anteriores |

---

## 4. BASE DE DATOS

El sistema utiliza **dos bases de datos**:

### 4.1 Firebird (PDVDATA.FDB) - Solo Lectura
Base de datos del sistema Eleventa PDV. Se utiliza para:
- Cargar facturas del día
- Obtener información de corte de caja
- Consultar créditos y devoluciones

### 4.2 SQLite (liquidador_data.db) - Lectura/Escritura
Base de datos local para persistencia de operaciones del liquidador.

**Tablas:**

| Tabla | Descripción |
|-------|-------------|
| `asignaciones` | Relación factura-repartidor |
| `descuentos` | Descuentos aplicados a facturas |
| `gastos` | Gastos por repartidor |
| `conteo_dinero` | Conteo simple de dinero |
| `conteos_sesion` | Sesiones de conteo múltiple |
| `conteos_sesion_detalle` | Detalle de denominaciones |
| `configuracion` | Configuración del sistema |
| `repartidores` | Catálogo de repartidores |
| `pago_proveedores` | Pagos a proveedores |
| `prestamos` | Préstamos otorgados |
| `pago_nomina` | Pagos de nómina |
| `pago_socios` | Pagos a socios |
| `transferencias` | Transferencias bancarias |
| `creditos_punteados` | Créditos marcados |
| `creditos_eleventa` | Cache de créditos Firebird |
| `historial_liquidaciones` | Histórico de liquidaciones |
| `devoluciones_parciales` | Devoluciones parciales |
| `conceptos_gastos` | Catálogo de conceptos |
| `corte_cajero` | Datos de corte de caja |
| `anotaciones` | Notas del sistema |
| `historial_abonos` | Abonos a créditos |
| `cancelaciones_usuario` | Cancelaciones por cajero |
| `cancelaciones_detalle` | Detalle de cancelaciones |
| `totales_cancelaciones_efectivo` | Totales de cancelaciones |

---

## 5. OPERACIONES POR MÓDULO

### 5.1 Operaciones de Asignación

```
CREAR ASIGNACIÓN
├── Entrada: folio, fecha, repartidor
├── Proceso: INSERT en tabla asignaciones
└── Salida: ID de asignación creada

ELIMINAR ASIGNACIÓN
├── Entrada: folio, fecha
├── Proceso: DELETE de tabla asignaciones
└── Salida: Boolean éxito/fallo

CARGAR ASIGNACIONES
├── Entrada: fecha
├── Proceso: SELECT de tabla asignaciones
└── Salida: Lista de {folio, repartidor}
```

### 5.2 Operaciones de Gastos

```
AGREGAR GASTO
├── Entrada: fecha, repartidor, concepto, monto, observaciones
├── Validación: monto > 0
├── Proceso: INSERT en tabla gastos
└── Salida: ID del gasto

OBTENER TOTAL GASTOS
├── Entrada: fecha, repartidor (opcional)
├── Proceso: SUM(monto) WHERE fecha = ? [AND repartidor = ?]
└── Salida: Float total

ACTUALIZAR GASTO
├── Entrada: gasto_id, nuevos_datos
├── Proceso: UPDATE tabla gastos
└── Salida: Boolean éxito
```

### 5.3 Operaciones de Conteo de Dinero

```
CREAR SESIÓN DE CONTEO
├── Entrada: fecha, repartidor, nombre_sesión
├── Proceso: INSERT en conteos_sesion
└── Salida: ID de sesión

GUARDAR DETALLE CONTEO
├── Entrada: sesion_id, denominación, cantidad
├── Proceso: INSERT/UPDATE en conteos_sesion_detalle
└── Salida: Boolean éxito

CALCULAR TOTAL SESIÓN
├── Entrada: sesion_id
├── Proceso: SUM(denominación * cantidad)
└── Salida: Float total
```

### 5.4 Operaciones de Créditos Punteados

```
MARCAR CRÉDITO PUNTEADO
├── Entrada: fecha, folio, cliente, monto
├── Proceso: INSERT en creditos_punteados
└── Salida: ID del registro

DESMARCAR CRÉDITO
├── Entrada: fecha, folio
├── Proceso: DELETE de creditos_punteados
└── Salida: Boolean éxito

OBTENER TOTAL PUNTEADOS
├── Entrada: fecha
├── Proceso: SUM(total) WHERE fecha = ?
└── Salida: Float total
```

---

## 6. FLUJO DE TRABAJO

### Flujo Diario Típico:

```
1. INICIO DEL DÍA
   │
   ├── Abrir aplicación
   ├── Verificar fecha (automática o manual)
   └── Cargar datos de Firebird
   
2. ASIGNACIÓN DE FACTURAS
   │
   ├── Revisar facturas sin asignar
   ├── Asignar repartidor a cada factura
   └── Verificar facturas a crédito
   
3. REGISTRO DE OPERACIONES
   │
   ├── Registrar gastos por repartidor
   ├── Registrar pagos a proveedores
   ├── Registrar préstamos (si aplica)
   └── Registrar pagos de nómina/socios
   
4. CONTEO DE EFECTIVO
   │
   ├── Crear sesión de conteo
   ├── Ingresar denominaciones
   └── Verificar total
   
5. CUADRE FINAL
   │
   ├── Revisar liquidación
   ├── Verificar diferencias
   ├── Marcar créditos punteados
   └── Agregar notas (si es necesario)
   
6. CIERRE
   │
   └── Datos guardados automáticamente en SQLite
```

---

## 7. CÁLCULOS FINANCIEROS

### 7.1 Fórmulas Principales

#### Total Vendido
```
Total Vendido = Total Facturas del Día - Facturas Canceladas - Devoluciones Parciales
```

#### Total Efectivo
```
Total Efectivo = Total Vendido - Total a Crédito
```

#### Total Descuentos
```
Total Descuentos = Ajustes + Gastos Repartidores + Gastos Cajero + 
                   Pago Proveedores + Préstamos + Nómina + Socios + Transferencias
```

#### Total Efectivo Caja
```
Total Efectivo Caja = Total Dinero Caja - Total Descuentos - Créditos Punteados
```

#### Diferencia Final
```
Diferencia Final = Conteo de Dinero - Total Efectivo Caja
```

#### Neto a Entregar
```
Neto a Entregar = Total Después Ajustes + Ingresos Extras - Gastos - 
                  Pago Proveedores - Préstamos - Nómina - Socios - 
                  Transferencias - Salidas
```

### 7.2 Tratamiento de Cancelaciones

**Canceladas del mismo día:**
- Se restan del Total Facturado
- Aparecen en rojo en la lista
- No afectan el conteo de efectivo

**Canceladas de otro día (informativas):**
- NO se restan del total del día actual
- Se muestran solo como información
- Color distintivo en la interfaz

---

## 8. INTEGRACIÓN CON FIREBIRD (ELEVENTA)

### 8.1 Conexión

El sistema se conecta a Firebird de dos maneras:

**Windows:**
```python
cmd = [isql_path, '-u', 'SYSDBA', '-p', 'masterkey', '-ch', 'WIN1252', db_path]
```

**Linux (modo embebido):**
```python
cmd = [isql_path, '-u', 'SYSDBA', '-p', 'masterkey', db_path]
env = firebird_setup.get_isql_env()  # Variables de entorno necesarias
```

### 8.2 Consultas Principales

#### Facturas del Día
```sql
SELECT V.ID, V.FOLIO, V.TOTAL, V.SUBTOTAL, V.CLIENTE, 
       V.CREDITO, V.TOTAL_CREDITO, V.CANCELADO, V.CANCELADO_FECHA
FROM VENTATICKETS V
WHERE CAST(V.FECHA AS DATE) = '{fecha}'
ORDER BY V.FOLIO;
```

#### Corte de Caja
```sql
SELECT T.ID AS TURNO_ID, T.FONDO_DE_CAJA, T.VENTAS_EN_EFECTIVO,
       T.TOTAL_TARJETA, T.TOTAL_VALES, T.RETIROS, T.DEPOSITOS
FROM TURNOS T
WHERE CAST(T.FECHA_INICIAL AS DATE) = '{fecha}'
ORDER BY T.ID DESC;
```

#### Cancelaciones por Usuario
```sql
SELECT D.CAJERO, SUM(D.TOTAL_DEVUELTO) AS TOTAL_CANCELADO,
       COUNT(*) AS NUM_CANCELACIONES
FROM DEVOLUCIONES D
WHERE CAST(D.DEVUELTO_EN AS DATE) = '{fecha}'
GROUP BY D.CAJERO;
```

### 8.3 Tablas de Firebird Utilizadas

| Tabla | Uso |
|-------|-----|
| `VENTATICKETS` | Facturas/Ventas |
| `TURNOS` | Cortes de caja |
| `DEVOLUCIONES` | Cancelaciones |
| `CLIENTES` | Información de clientes |
| `FACTURAS` | Facturas completas |

---

## 📞 SOPORTE

Para problemas técnicos o consultas sobre el sistema:

1. Revisar los logs de error en la consola
2. Verificar conexión con base de datos Firebird
3. Comprobar permisos de escritura en SQLite
4. Verificar que las librerías de Firebird estén correctamente instaladas

---

## 📝 HISTORIAL DE CAMBIOS

| Fecha | Versión | Cambios |
|-------|---------|---------|
| 2026-02-05 | 2.1.0 | Soporte Linux, filtro de transferencias por repartidor |
| 2026-02-04 | 2.0.0 | Nueva arquitectura modular |
| 2026-01-31 | 1.5.0 | Agregado módulo de créditos punteados |

---

*Documentación generada automáticamente - Liquidador de Repartidores v2.1.0*
