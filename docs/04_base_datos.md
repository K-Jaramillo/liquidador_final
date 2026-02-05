# 🗄️ 4. BASE DE DATOS

El sistema utiliza dos bases de datos complementarias.

---

## 4.1 Arquitectura de Datos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FUENTES DE DATOS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐    │
│  │      FIREBIRD (Eleventa)    │    │     SQLite (Liquidador)         │    │
│  │         PDVDATA.FDB         │    │     liquidador_data.db          │    │
│  ├─────────────────────────────┤    ├─────────────────────────────────┤    │
│  │                             │    │                                 │    │
│  │  📄 VENTATICKETS (Facturas) │    │  📋 asignaciones                │    │
│  │  📊 TURNOS (Corte caja)     │    │  💰 gastos                      │    │
│  │  ↩️ DEVOLUCIONES            │    │  💵 conteo_dinero               │    │
│  │  👤 CLIENTES                │    │  📦 pago_proveedores            │    │
│  │  📦 PRODUCTOS               │    │  💳 prestamos                   │    │
│  │                             │    │  👔 pago_nomina                 │    │
│  │  ⚠️ SOLO LECTURA            │    │  👥 pago_socios                 │    │
│  │                             │    │  🏦 transferencias              │    │
│  │                             │    │  ✓ creditos_punteados           │    │
│  │                             │    │  📝 anotaciones                 │    │
│  │                             │    │  📜 historial_liquidaciones     │    │
│  │                             │    │                                 │    │
│  │                             │    │  ✅ LECTURA/ESCRITURA           │    │
│  └─────────────────────────────┘    └─────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4.2 Base de Datos Firebird (PDVDATA.FDB)

### Descripción
Base de datos del sistema Eleventa PDV. El liquidador **solo lee** datos de esta base.

### Conexión

```python
# Windows
cmd = ['isql-fb', '-u', 'SYSDBA', '-p', 'masterkey', '-ch', 'WIN1252', 'PDVDATA.FDB']

# Linux (modo embebido)
cmd = ['isql-fb', '-u', 'SYSDBA', '-p', 'masterkey', 'PDVDATA.FDB']
env = {
    'LD_LIBRARY_PATH': './firebird25_lib',
    'FIREBIRD': './firebird25_lib'
}
```

### Tablas Principales

#### VENTATICKETS (Facturas de Venta)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| ID | INTEGER | Identificador único |
| FOLIO | INTEGER | Número de factura visible |
| FECHA | TIMESTAMP | Fecha y hora de la venta |
| SUBTOTAL | DECIMAL | Subtotal sin IVA |
| IVA | DECIMAL | Monto de IVA |
| TOTAL | DECIMAL | Total de la factura |
| CLIENTE | VARCHAR | Nombre del cliente |
| CLIENTE_ID | INTEGER | ID del cliente |
| FORMAPAGO | VARCHAR | Forma de pago |
| CREDITO | SMALLINT | 1=Es crédito, 0=Contado |
| TOTAL_CREDITO | DECIMAL | Monto a crédito |
| CANCELADO | SMALLINT | 1=Cancelada, 0=Vigente |
| CANCELADO_FECHA | TIMESTAMP | Fecha de cancelación |
| VENDEDOR | VARCHAR | Nombre del vendedor |
| CONDICION | VARCHAR | Condición de venta |

**Consulta típica:**
```sql
SELECT ID, FOLIO, FECHA, TOTAL, SUBTOTAL, CLIENTE, 
       CREDITO, TOTAL_CREDITO, CANCELADO, CANCELADO_FECHA
FROM VENTATICKETS 
WHERE CAST(FECHA AS DATE) = '2026-02-05'
ORDER BY FOLIO;
```

#### TURNOS (Cortes de Caja)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| ID | INTEGER | ID del turno |
| FECHA_INICIAL | TIMESTAMP | Inicio del turno |
| FECHA_FINAL | TIMESTAMP | Fin del turno |
| FONDO_DE_CAJA | DECIMAL | Fondo inicial |
| VENTAS_EN_EFECTIVO | DECIMAL | Ventas en efectivo |
| TOTAL_TARJETA | DECIMAL | Ventas con tarjeta |
| TOTAL_VALES | DECIMAL | Ventas con vales |
| RETIROS | DECIMAL | Retiros de caja |
| DEPOSITOS | DECIMAL | Depósitos a caja |
| CAJERO | VARCHAR | Nombre del cajero |

**Consulta típica:**
```sql
SELECT ID, FONDO_DE_CAJA, VENTAS_EN_EFECTIVO, TOTAL_TARJETA,
       TOTAL_VALES, RETIROS, DEPOSITOS
FROM TURNOS 
WHERE CAST(FECHA_INICIAL AS DATE) = '2026-02-05'
ORDER BY ID DESC;
```

#### DEVOLUCIONES (Cancelaciones)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| ID | INTEGER | ID de devolución |
| TICKET_ID | INTEGER | ID de la factura original |
| TOTAL_DEVUELTO | DECIMAL | Monto devuelto |
| DEVUELTO_EN | TIMESTAMP | Fecha de devolución |
| CAJERO | VARCHAR | Cajero que procesó |
| MOTIVO | VARCHAR | Motivo de cancelación |

**Consulta típica:**
```sql
SELECT D.CAJERO, SUM(D.TOTAL_DEVUELTO) AS TOTAL,
       COUNT(*) AS CANTIDAD
FROM DEVOLUCIONES D
WHERE CAST(D.DEVUELTO_EN AS DATE) = '2026-02-05'
GROUP BY D.CAJERO;
```

---

## 4.3 Base de Datos SQLite (liquidador_data.db)

### Descripción
Base de datos local para persistir todas las operaciones del liquidador.

### Ubicación
```
liquidador_final/liquidador_data.db
```

### Conexión

```python
import sqlite3

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
    return conn
```

---

## 4.4 Tablas SQLite - Detalle Completo

### 📋 ASIGNACIONES

Relaciona facturas con repartidores.

```sql
CREATE TABLE IF NOT EXISTS asignaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    folio INTEGER NOT NULL,
    repartidor TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fecha, folio)
);

CREATE INDEX idx_asignaciones_fecha ON asignaciones(fecha);
CREATE INDEX idx_asignaciones_folio ON asignaciones(folio);
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único |
| fecha | DATE | Fecha de la asignación |
| folio | INTEGER | Número de factura |
| repartidor | TEXT | Nombre del repartidor |
| fecha_creacion | TIMESTAMP | Cuándo se creó |

**Operaciones:**
```python
# Agregar asignación
INSERT INTO asignaciones (fecha, folio, repartidor) VALUES (?, ?, ?)

# Obtener asignaciones del día
SELECT * FROM asignaciones WHERE fecha = ?

# Eliminar asignación
DELETE FROM asignaciones WHERE fecha = ? AND folio = ?
```

---

### 💰 GASTOS

Gastos operativos por repartidor.

```sql
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    repartidor TEXT NOT NULL,
    concepto TEXT NOT NULL,
    monto REAL NOT NULL DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gastos_fecha ON gastos(fecha);
CREATE INDEX idx_gastos_repartidor ON gastos(repartidor);
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único |
| fecha | DATE | Fecha del gasto |
| repartidor | TEXT | Quién hizo el gasto |
| concepto | TEXT | Descripción (gasolina, etc.) |
| monto | REAL | Cantidad en pesos |
| observaciones | TEXT | Notas adicionales |

---

### 💵 DESCUENTOS

Descuentos aplicados a facturas específicas.

```sql
CREATE TABLE IF NOT EXISTS descuentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    folio INTEGER NOT NULL,
    tipo TEXT NOT NULL,  -- 'ajuste', 'credito', 'devolucion'
    monto REAL NOT NULL DEFAULT 0,
    concepto TEXT,
    repartidor TEXT,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_descuentos_fecha ON descuentos(fecha);
CREATE INDEX idx_descuentos_folio ON descuentos(folio);
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único |
| fecha | DATE | Fecha del descuento |
| folio | INTEGER | Factura afectada |
| tipo | TEXT | ajuste/credito/devolucion |
| monto | REAL | Cantidad descontada |
| concepto | TEXT | Razón del descuento |
| repartidor | TEXT | Responsable |

---

### 📦 PAGO_PROVEEDORES

Pagos realizados a proveedores.

```sql
CREATE TABLE IF NOT EXISTS pago_proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    proveedor TEXT NOT NULL,
    concepto TEXT,
    monto REAL NOT NULL DEFAULT 0,
    repartidor TEXT,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pago_proveedores_fecha ON pago_proveedores(fecha);
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único |
| fecha | DATE | Fecha del pago |
| proveedor | TEXT | Nombre del proveedor |
| concepto | TEXT | Descripción del pago |
| monto | REAL | Cantidad pagada |
| repartidor | TEXT | Quién pagó (opcional) |

---

### 💳 PRESTAMOS

Préstamos otorgados a empleados.

```sql
CREATE TABLE IF NOT EXISTS prestamos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    repartidor TEXT NOT NULL,
    concepto TEXT,
    monto REAL NOT NULL DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prestamos_fecha ON prestamos(fecha);
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único |
| fecha | DATE | Fecha del préstamo |
| repartidor | TEXT | Quién recibe |
| concepto | TEXT | Motivo |
| monto | REAL | Cantidad prestada |

---

### 👔 PAGO_NOMINA

Pagos de nómina/sueldo.

```sql
CREATE TABLE IF NOT EXISTS pago_nomina (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    empleado TEXT NOT NULL,
    concepto TEXT,
    monto REAL NOT NULL DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pago_nomina_fecha ON pago_nomina(fecha);
```

---

### 👥 PAGO_SOCIOS

Pagos o retiros de socios.

```sql
CREATE TABLE IF NOT EXISTS pago_socios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    socio TEXT NOT NULL,
    concepto TEXT,
    monto REAL NOT NULL DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pago_socios_fecha ON pago_socios(fecha);
```

---

### 🏦 TRANSFERENCIAS

Transferencias bancarias realizadas por repartidores.

```sql
CREATE TABLE IF NOT EXISTS transferencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    repartidor TEXT NOT NULL,       -- Quien realiza la transferencia
    destinatario TEXT NOT NULL,     -- Cuenta/banco/persona destino
    concepto TEXT,
    monto REAL NOT NULL DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transferencias_fecha ON transferencias(fecha);
CREATE INDEX idx_transferencias_repartidor ON transferencias(repartidor);
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único |
| fecha | DATE | Fecha de la transferencia |
| repartidor | TEXT | Quien realiza la transferencia |
| destinatario | TEXT | Cuenta/Persona destino |
| concepto | TEXT | Descripción |
| monto | REAL | Cantidad transferida |

---

### ✓ CREDITOS_PUNTEADOS

Créditos marcados como verificados.

```sql
CREATE TABLE IF NOT EXISTS creditos_punteados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    folio INTEGER NOT NULL,
    cliente TEXT,
    subtotal REAL DEFAULT 0,
    total REAL DEFAULT 0,
    repartidor TEXT,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fecha, folio)
);

CREATE INDEX idx_creditos_punteados_fecha ON creditos_punteados(fecha);
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único |
| fecha | TEXT | Fecha del crédito |
| folio | INTEGER | Número de factura |
| cliente | TEXT | Nombre del cliente |
| total | REAL | Monto del crédito |
| repartidor | TEXT | Responsable |

---

### 💵 CONTEO_DINERO

Conteo simple de dinero por repartidor.

```sql
CREATE TABLE IF NOT EXISTS conteo_dinero (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    repartidor TEXT NOT NULL,
    denominacion INTEGER NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 0,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fecha, repartidor, denominacion)
);

CREATE INDEX idx_conteo_dinero_fecha ON conteo_dinero(fecha);
```

---

### 💵 CONTEOS_SESION

Sesiones de conteo múltiple.

```sql
CREATE TABLE IF NOT EXISTS conteos_sesion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    repartidor TEXT NOT NULL,
    nombre_sesion TEXT NOT NULL DEFAULT 'Conteo',
    total REAL DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conteos_sesion_fecha ON conteos_sesion(fecha);
```

---

### 💵 CONTEOS_SESION_DETALLE

Detalle por denominación de cada sesión.

```sql
CREATE TABLE IF NOT EXISTS conteos_sesion_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    denominacion REAL NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES conteos_sesion(id) ON DELETE CASCADE
);

CREATE INDEX idx_conteos_detalle_sesion ON conteos_sesion_detalle(sesion_id);
```

---

### 📝 ANOTACIONES

Notas adhesivas del sistema.

```sql
CREATE TABLE IF NOT EXISTS anotaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    contenido TEXT NOT NULL DEFAULT '',
    color TEXT DEFAULT '#FFEB3B',
    posicion_x INTEGER DEFAULT 0,
    posicion_y INTEGER DEFAULT 0,
    ancho INTEGER DEFAULT 200,
    alto INTEGER DEFAULT 150,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_anotaciones_fecha ON anotaciones(fecha);
```

---

### 📜 HISTORIAL_LIQUIDACIONES

Historial de liquidaciones guardadas.

```sql
CREATE TABLE IF NOT EXISTS historial_liquidaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    total_vendido REAL DEFAULT 0,
    total_canceladas REAL DEFAULT 0,
    total_credito REAL DEFAULT 0,
    total_descuentos REAL DEFAULT 0,
    total_gastos REAL DEFAULT 0,
    total_conteo REAL DEFAULT 0,
    diferencia REAL DEFAULT 0,
    observaciones TEXT,
    datos_json TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_historial_fecha ON historial_liquidaciones(fecha);
```

---

### 👤 REPARTIDORES

Catálogo de repartidores.

```sql
CREATE TABLE IF NOT EXISTS repartidores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    activo INTEGER DEFAULT 1,
    telefono TEXT,
    observaciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### ⚙️ CONFIGURACION

Configuración del sistema.

```sql
CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT,
    descripcion TEXT,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4.5 Diagrama de Relaciones

```
┌─────────────────┐     ┌─────────────────┐
│    FIREBIRD     │     │     SQLite      │
│   VENTATICKETS  │────►│   asignaciones  │
│     (folio)     │     │     (folio)     │
└─────────────────┘     └─────────────────┘
                               │
                               │ folio
                               ▼
                        ┌─────────────────┐
                        │   descuentos    │
                        └─────────────────┘
                               │
                               │ folio
                               ▼
                        ┌─────────────────┐
                        │creditos_punteados│
                        └─────────────────┘


┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ conteos_sesion  │────►│conteos_sesion_  │     │  repartidores   │
│       (id)      │     │    detalle      │     │    (nombre)     │
└─────────────────┘     │   (sesion_id)   │     └────────┬────────┘
                        └─────────────────┘              │
                                                         │ repartidor
                                    ┌────────────────────┼────────────────────┐
                                    ▼                    ▼                    ▼
                            ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                            │   gastos    │      │  prestamos  │      │asignaciones │
                            └─────────────┘      └─────────────┘      └─────────────┘
```

---

## 4.6 Funciones CRUD Principales

### Asignaciones

```python
# database_local.py

def agregar_asignacion(fecha: str, folio: int, repartidor: str) -> int:
    """Crea una asignación. Retorna ID."""
    
def obtener_asignaciones_fecha(fecha: str) -> List[Dict]:
    """Obtiene todas las asignaciones de una fecha."""
    
def obtener_asignacion(fecha: str, folio: int) -> Optional[Dict]:
    """Obtiene la asignación de un folio específico."""
    
def eliminar_asignacion(fecha: str, folio: int) -> bool:
    """Elimina una asignación."""
    
def limpiar_asignaciones_fecha(fecha: str) -> bool:
    """Elimina todas las asignaciones de una fecha."""
```

### Gastos

```python
def agregar_gasto(fecha, repartidor, concepto, monto, observaciones='') -> int:
    """Crea un gasto. Retorna ID."""
    
def obtener_gastos_fecha(fecha: str) -> List[Dict]:
    """Todos los gastos de una fecha."""
    
def obtener_gastos_repartidor(fecha: str, repartidor: str) -> List[Dict]:
    """Gastos filtrados por repartidor."""
    
def obtener_total_gastos_fecha(fecha: str) -> float:
    """Suma total de gastos."""
    
def actualizar_gasto(gasto_id, repartidor, concepto, monto, observaciones) -> bool:
    """Modifica un gasto existente."""
    
def eliminar_gasto(gasto_id: int) -> bool:
    """Elimina un gasto."""
```

### Patrón General

Todas las entidades siguen el mismo patrón CRUD:

```python
def agregar_{entidad}(fecha, ...) -> int:
    """Crea registro, retorna ID"""

def obtener_{entidad}_fecha(fecha) -> List[Dict]:
    """Lista todos los registros de una fecha"""

def obtener_total_{entidad}_fecha(fecha) -> float:
    """Suma de montos de una fecha"""

def actualizar_{entidad}(id, ...) -> bool:
    """Modifica registro existente"""

def eliminar_{entidad}(id) -> bool:
    """Borra registro"""
```

---

## 4.7 Backup y Mantenimiento

### Ubicación del Archivo
```bash
# El archivo SQLite está en:
liquidador_final/liquidador_data.db
```

### Backup Manual
```bash
# Linux
cp liquidador_data.db liquidador_data_backup_$(date +%Y%m%d).db

# Windows
copy liquidador_data.db liquidador_data_backup_%date:~-4,4%%date:~-7,2%%date:~-10,2%.db
```

### Consultas Útiles

```sql
-- Ver todas las tablas
SELECT name FROM sqlite_master WHERE type='table';

-- Contar registros por tabla
SELECT 'asignaciones' as tabla, COUNT(*) as registros FROM asignaciones
UNION ALL
SELECT 'gastos', COUNT(*) FROM gastos
UNION ALL
SELECT 'descuentos', COUNT(*) FROM descuentos;

-- Resumen por fecha
SELECT fecha, 
       COUNT(*) as total_asignaciones,
       COUNT(DISTINCT repartidor) as repartidores
FROM asignaciones 
GROUP BY fecha 
ORDER BY fecha DESC 
LIMIT 10;

-- Limpiar datos antiguos (más de 90 días)
DELETE FROM asignaciones WHERE fecha < date('now', '-90 days');
DELETE FROM gastos WHERE fecha < date('now', '-90 days');
```

---

*Siguiente: [05. Operaciones por Módulo](05_operaciones_modulo.md)*
