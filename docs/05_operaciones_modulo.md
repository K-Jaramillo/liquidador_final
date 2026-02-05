# ⚙️ 5. OPERACIONES POR MÓDULO

Detalle de todas las operaciones CRUD y procesos de cada módulo.

---

## 5.1 Operaciones de Carga de Datos (Firebird)

### Cargar Facturas del Día

```python
def _cargar_facturas(self):
    """Carga todas las facturas del día desde Firebird."""
```

**Flujo:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CARGAR FACTURAS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Construir consulta SQL                                                  │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ SELECT ID, FOLIO, TOTAL, SUBTOTAL, CLIENTE, CREDITO,             │    │
│     │        TOTAL_CREDITO, CANCELADO, CANCELADO_FECHA                 │    │
│     │ FROM VENTATICKETS                                                │    │
│     │ WHERE CAST(FECHA AS DATE) = '{fecha}'                            │    │
│     │ ORDER BY FOLIO                                                   │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  2. Ejecutar consulta via isql                                             │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ subprocess.run([isql_path, '-u', 'SYSDBA', '-p', 'masterkey',    │    │
│     │                 db_path], input=sql, capture_output=True)        │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  3. Parsear salida de texto                                                 │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ • Detectar líneas de datos (no headers ni separadores)           │    │
│     │ • Extraer campos por posición                                    │    │
│     │ • Convertir tipos (int, float, bool)                            │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  4. Cargar asignaciones existentes (SQLite)                                │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ asignaciones = db_local.obtener_asignaciones_fecha(fecha)        │    │
│     │ cache_asign = {a['folio']: a['repartidor'] for a in asignaciones}│    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  5. Construir lista de ventas                                               │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ ventas = []                                                      │    │
│     │ for factura in facturas_firebird:                               │    │
│     │     v = {                                                        │    │
│     │         'folio': factura.folio,                                  │    │
│     │         'subtotal': factura.subtotal,                            │    │
│     │         'total_original': factura.total,                         │    │
│     │         'nombre': factura.cliente,                               │    │
│     │         'cancelada': factura.cancelado == 1,                     │    │
│     │         'es_credito': factura.credito == 1,                      │    │
│     │         'total_credito': factura.total_credito,                  │    │
│     │         'repartidor': cache_asign.get(factura.folio, '')         │    │
│     │     }                                                            │    │
│     │     ventas.append(v)                                             │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  6. Actualizar DataStore                                                    │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ self.ds.set_ventas(ventas)  # Notifica a todos los listeners     │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cargar Corte de Caja

```python
def _cargar_corte_cajero(self):
    """Carga el corte de caja del turno actual."""
```

**Flujo:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CARGAR CORTE CAJERO                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Obtener turno más reciente del día                                     │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ SELECT ID, FONDO_DE_CAJA, VENTAS_EN_EFECTIVO, ...                │    │
│     │ FROM TURNOS                                                      │    │
│     │ WHERE CAST(FECHA_INICIAL AS DATE) = '{fecha}'                    │    │
│     │ ORDER BY ID DESC LIMIT 1                                         │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  2. Obtener cancelaciones por usuario                                       │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ obtener_cancelaciones_por_usuario(fecha)                         │    │
│     │ → {'CAJERO1': {'total': 500, 'efectivo': 300, 'credito': 200}}  │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  3. Calcular totales del corte                                              │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ total_dinero_caja = fondo_caja + ventas_efectivo - devoluciones  │    │
│     │                     - total_cancelaciones_efectivo               │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│                                     ▼                                       │
│  4. Actualizar labels de la UI                                              │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │ self.lbl_corte_total_dinero.config(text=f"${total:,.2f}")        │    │
│     │ self.lbl_corte_ventas_efectivo.config(...)                       │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5.2 Operaciones de Asignación

### Asignar Repartidor a Factura

```
ENTRADA:
├── folio: int           (número de factura)
├── fecha: str           (YYYY-MM-DD)
└── repartidor: str      (nombre del repartidor)

PROCESO:
├── 1. Validar que la factura existe
├── 2. Verificar que no está cancelada
├── 3. Crear/actualizar registro en SQLite
│      INSERT OR REPLACE INTO asignaciones (fecha, folio, repartidor)
│      VALUES (?, ?, ?)
├── 4. Actualizar DataStore
│      ds.set_repartidor_factura(folio, repartidor)
└── 5. Notificar cambios
       ds._notificar()

SALIDA:
└── Boolean indicando éxito
```

### Quitar Asignación

```
ENTRADA:
├── folio: int
└── fecha: str

PROCESO:
├── 1. Eliminar de SQLite
│      DELETE FROM asignaciones WHERE fecha = ? AND folio = ?
├── 2. Limpiar en DataStore
│      ds.clear_repartidor_factura(folio)
└── 3. Notificar cambios

SALIDA:
└── Boolean indicando éxito
```

### Asignación Masiva

```
ENTRADA:
├── folios: List[int]    (lista de folios seleccionados)
├── fecha: str
└── repartidor: str

PROCESO:
├── FOR cada folio en folios:
│   ├── asignar_repartidor(folio, fecha, repartidor)
│   └── actualizar_ui_progreso()
└── Refrescar lista completa

SALIDA:
└── Cantidad de asignaciones realizadas
```

---

## 5.3 Operaciones de Gastos

### Agregar Gasto

```python
def agregar_gasto(fecha, repartidor, concepto, monto, observaciones=''):
    """Crea un nuevo gasto en SQLite."""
```

**Diagrama:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGREGAR GASTO                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ENTRADA                                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ fecha:        "2026-02-05"                                         │     │
│  │ repartidor:   "DAVID"                                              │     │
│  │ concepto:     "Gasolina"                                           │     │
│  │ monto:        200.00                                               │     │
│  │ observaciones: "Tanque lleno"                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                     │                                       │
│                                     ▼                                       │
│  VALIDACIÓN                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ ✓ monto > 0                                                        │     │
│  │ ✓ repartidor no vacío                                              │     │
│  │ ✓ fecha válida                                                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                     │                                       │
│                                     ▼                                       │
│  SQL                                                                        │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ INSERT INTO gastos                                                 │     │
│  │ (fecha, repartidor, concepto, monto, observaciones)                │     │
│  │ VALUES (?, ?, ?, ?, ?)                                             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                     │                                       │
│                                     ▼                                       │
│  SALIDA                                                                     │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ gasto_id: 123  (ID del registro creado)                            │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Obtener Total Gastos

```python
def obtener_total_gastos_fecha(fecha: str, repartidor: str = '') -> float:
    """Suma todos los gastos de una fecha, opcionalmente filtrados."""
```

**SQL:**
```sql
-- Sin filtro de repartidor
SELECT COALESCE(SUM(monto), 0) as total
FROM gastos
WHERE fecha = ?

-- Con filtro de repartidor
SELECT COALESCE(SUM(monto), 0) as total
FROM gastos
WHERE fecha = ? AND repartidor = ?
```

---

## 5.4 Operaciones de Conteo de Dinero

### Crear Sesión de Conteo

```
ENTRADA:
├── fecha: str
├── repartidor: str
└── nombre_sesion: str    (ej: "CONTEO FINAL")

PROCESO:
├── 1. Crear registro de sesión
│      INSERT INTO conteos_sesion (fecha, repartidor, nombre_sesion)
│      VALUES (?, ?, ?)
├── 2. Obtener ID de la sesión
│      sesion_id = cursor.lastrowid
└── 3. Retornar ID para agregar detalles

SALIDA:
└── sesion_id: int
```

### Guardar Detalle de Conteo

```
ENTRADA:
├── sesion_id: int
├── denominacion: float   (ej: 500.00)
└── cantidad: int         (ej: 8)

PROCESO:
├── 1. Calcular subtotal
│      subtotal = denominacion * cantidad
├── 2. Insertar o actualizar detalle
│      INSERT OR REPLACE INTO conteos_sesion_detalle
│      (sesion_id, denominacion, cantidad, subtotal)
│      VALUES (?, ?, ?, ?)
└── 3. Actualizar total de la sesión
       UPDATE conteos_sesion SET total = (
         SELECT SUM(subtotal) FROM conteos_sesion_detalle
         WHERE sesion_id = ?
       ) WHERE id = ?

SALIDA:
└── subtotal: float
```

### Calcular Total General

```python
def obtener_total_general_conteos_fecha(fecha: str) -> float:
    """Suma todos los conteos de todos los repartidores."""
```

**SQL:**
```sql
SELECT COALESCE(SUM(total), 0) as total_general
FROM conteos_sesion
WHERE fecha = ?
```

---

## 5.5 Operaciones de Descuentos

### Agregar Descuento a Factura

```
ENTRADA:
├── fecha: str
├── folio: int
├── tipo: str           ('ajuste' | 'credito' | 'devolucion')
├── monto: float
├── concepto: str
└── repartidor: str

VALIDACIÓN:
├── ✓ folio existe
├── ✓ monto > 0
├── ✓ tipo válido
└── ✓ monto <= total_factura (opcional)

PROCESO:
├── INSERT INTO descuentos
│   (fecha, folio, tipo, monto, concepto, repartidor)
│   VALUES (?, ?, ?, ?, ?, ?)
└── Retornar ID

EFECTO EN LIQUIDACIÓN:
├── tipo='ajuste'     → Resta de total_ajustes
├── tipo='credito'    → Suma a créditos aplicados
└── tipo='devolucion' → Resta de total_devoluciones
```

### Obtener Descuentos por Tipo

```python
def obtener_total_ajustes(fecha: str, repartidor: str = '') -> float:
    """Solo descuentos tipo 'ajuste'."""

def obtener_total_devoluciones(fecha: str, repartidor: str = '') -> float:
    """Solo descuentos tipo 'devolucion'."""
```

---

## 5.6 Operaciones de Créditos Punteados

### Marcar Crédito como Punteado

```
ENTRADA:
├── fecha: str
├── folio: int
├── cliente: str
├── total: float
└── repartidor: str

PROCESO:
├── 1. Verificar que es factura a crédito
├── 2. Insertar registro
│      INSERT INTO creditos_punteados
│      (fecha, folio, cliente, total, repartidor)
│      VALUES (?, ?, ?, ?, ?)
└── 3. Notificar cambio para actualizar liquidación

EFECTO:
└── El monto se resta del efectivo esperado en caja
    (ya se "cobró" pero no está físicamente)
```

### Despuntear Crédito

```
ENTRADA:
├── fecha: str
└── folio: int

PROCESO:
├── DELETE FROM creditos_punteados
│   WHERE fecha = ? AND folio = ?
└── Notificar cambio

EFECTO:
└── El monto vuelve al efectivo esperado
```

### Obtener Total Punteados

```python
def obtener_total_creditos_punteados(fecha: str) -> float:
    """Suma de todos los créditos punteados del día."""
```

**SQL:**
```sql
SELECT COALESCE(SUM(total), 0) as total
FROM creditos_punteados
WHERE fecha = ?
```

---

## 5.7 Operaciones de Transferencias

### Agregar Transferencia

```
ENTRADA:
├── fecha: str
├── destinatario: str   (cuenta/persona destino)
├── concepto: str
├── monto: float
└── observaciones: str

PROCESO:
├── INSERT INTO transferencias
│   (fecha, destinatario, concepto, monto, observaciones)
│   VALUES (?, ?, ?, ?, ?)
└── Retornar ID

EFECTO:
└── Resta del efectivo esperado (dinero que salió de caja)
```

### Obtener Total Transferencias Filtrado

```python
def obtener_total_transferencias_fecha(fecha: str, destinatario: str = '') -> float:
    """Total de transferencias, opcionalmente filtrado por destinatario."""
```

**SQL:**
```sql
-- Sin filtro
SELECT COALESCE(SUM(monto), 0) as total
FROM transferencias
WHERE fecha = ?

-- Con filtro (para ver transferencias de un repartidor específico)
SELECT COALESCE(SUM(monto), 0) as total
FROM transferencias
WHERE fecha = ? AND destinatario = ?
```

---

## 5.8 Operaciones de Anotaciones

### Crear Nota

```
ENTRADA:
├── fecha: str
├── contenido: str      (texto de la nota)
└── color: str          (código hex, ej: '#FFEB3B')

PROCESO:
├── INSERT INTO anotaciones
│   (fecha, contenido, color)
│   VALUES (?, ?, ?)
└── Retornar ID

VISUALIZACIÓN:
└── Se muestra como "sticky note" en la pestaña de anotaciones
```

### Actualizar Nota

```
ENTRADA:
├── nota_id: int
├── contenido: str
└── color: str

PROCESO:
├── UPDATE anotaciones
│   SET contenido = ?, color = ?, fecha_modificacion = CURRENT_TIMESTAMP
│   WHERE id = ?
└── Refrescar UI
```

---

## 5.9 Operación Principal: Refrescar Liquidación

Esta es la operación más compleja que calcula todos los totales.

```python
def _refrescar_liquidacion(self):
    """Recalcula todos los valores de la liquidación."""
```

**Flujo Completo:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      REFRESCAR LIQUIDACIÓN                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. OBTENER DATOS BASE                                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ ventas = self.ds.get_ventas()                                      │     │
│  │ filtro = self.filtro_rep_global_var.get()                          │     │
│  │ fecha = self.ds.fecha                                              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  2. FILTRAR SI HAY REPARTIDOR SELECCIONADO                                  │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ if filtro and filtro not in ("(Todos)", "(Sin Asignar)"):          │     │
│  │     ventas = [v for v in ventas if v['repartidor'] == filtro]      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  3. CALCULAR TOTALES DE VENTAS                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ total_facturas = sum(v['total_original'] for v in ventas           │     │
│  │                      if not v.get('cancelada_otro_dia'))           │     │
│  │                                                                    │     │
│  │ total_canceladas = sum(v['total_original'] for v in ventas         │     │
│  │                        if v['cancelada'] and not cancelada_otro_dia)│     │
│  │                                                                    │     │
│  │ total_vendido = total_facturas - total_canceladas - dev_parciales  │     │
│  │                                                                    │     │
│  │ total_credito = sum(v['total_credito'] for v in ventas             │     │
│  │                     if v['es_credito'] and not v['cancelada'])     │     │
│  │                                                                    │     │
│  │ total_efectivo = total_vendido - total_credito                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  4. CALCULAR DESCUENTOS Y SALIDAS                                           │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ filtro_gastos = filtro if filtro not in ("(Todos)","(Sin Asignar)")│     │
│  │                 else ''                                            │     │
│  │                                                                    │     │
│  │ total_ajustes = ds.get_total_ajustes(filtro_gastos)                │     │
│  │ total_gastos = ds.get_total_gastos_repartidores(filtro_gastos)     │     │
│  │ total_gastos_cajero = ds.get_total_gastos_cajero(filtro_gastos)    │     │
│  │ total_proveedores = ds.get_total_pagos_proveedores(filtro_gastos)  │     │
│  │ total_prestamos = ds.get_total_prestamos(filtro_gastos)            │     │
│  │ total_nomina = ds.get_total_pagos_nomina()                         │     │
│  │ total_socios = ds.get_total_pagos_socios()                         │     │
│  │ total_transferencias = ds.get_total_transferencias(filtro_gastos)  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  5. CALCULAR TOTALES FINALES                                                │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ total_descuentos = total_ajustes + total_gastos + total_gastos_cajero    │
│  │                  + total_proveedores + total_prestamos + total_nomina    │
│  │                  + total_socios + total_transferencias                   │
│  │                                                                    │     │
│  │ total_creditos_punteados = db_local.obtener_total_creditos_punteados     │
│  │                                                                    │     │
│  │ # Cuadre                                                           │     │
│  │ efectivo_esperado = total_dinero_caja - total_descuentos           │     │
│  │                     - total_creditos_punteados                     │     │
│  │                                                                    │     │
│  │ conteo_dinero = ds.get_total_dinero()                              │     │
│  │                                                                    │     │
│  │ diferencia = conteo_dinero - efectivo_esperado                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  6. ACTUALIZAR INTERFAZ                                                     │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ # Columna 1: Descuentos y Ajustes                                  │     │
│  │ self.lbl_total_ajustes.config(text=f"${total_ajustes:,.2f}")       │     │
│  │ self.lbl_total_gastos_liq.config(text=f"${total_gastos:,.2f}")     │     │
│  │ ...                                                                │     │
│  │                                                                    │     │
│  │ # Columna 2: Cuadre General                                        │     │
│  │ self.lbl_total_efectivo_caja.config(text=f"${efectivo_esperado:,.2f}")  │
│  │ self.lbl_diferencia_cuadre.config(text=f"${diferencia:,.2f}")      │     │
│  │                                                                    │     │
│  │ # Colorear diferencia                                              │     │
│  │ if abs(diferencia) < 0.01:                                         │     │
│  │     color = "#4CAF50"  # Verde - cuadra                            │     │
│  │ elif diferencia < 0:                                               │     │
│  │     color = "#f44336"  # Rojo - faltante                           │     │
│  │ else:                                                              │     │
│  │     color = "#ff9800"  # Naranja - sobrante                        │     │
│  │ self.lbl_diferencia_cuadre.config(foreground=color)                │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5.10 Guardar Liquidación en Historial

```python
def _guardar_liquidacion(self):
    """Persiste la liquidación actual en el historial."""
```

**Datos guardados:**
```python
datos = {
    'fecha': self.ds.fecha,
    'total_vendido': total_vendido,
    'total_canceladas': total_canceladas,
    'total_credito': total_credito,
    'total_descuentos': total_descuentos,
    'total_gastos': total_gastos,
    'total_conteo': conteo_dinero,
    'diferencia': diferencia,
    'datos_json': json.dumps({
        'detalle_gastos': gastos_detalle,
        'detalle_descuentos': descuentos_detalle,
        'asignaciones': asignaciones_resumen
    })
}
```

---

*Siguiente: [06. Flujo de Trabajo](06_flujo_trabajo.md)*
