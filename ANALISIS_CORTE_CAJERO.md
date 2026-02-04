# 📊 ANÁLISIS DEL CORTE DE CAJERO - ELEVENTA

## 🎯 Objetivo
Extraer y mostrar los datos del **Corte de Cajero** del sistema Eleventa (base de datos Firebird) en el Liquidador de Repartidores.

---

## 🗄️ Estructura de la Base de Datos Firebird

### Tablas Principales Utilizadas

| Tabla | Descripción | Campos Clave |
|-------|-------------|--------------|
| `TURNOS` | Información de cada turno/corte | `IDTURNO`, `FONDOCAJA`, `VENTASEFECTIVO`, `DEVOEFECTIVO`, `ABONOSEFECTIVO`, `VENTASTARJETA`, `VENTASCREDITO`, `VENTASVALES`, `GANANCIA` |
| `CORTE_MOVIMIENTOS` | Entradas y salidas de efectivo | `IDTURNO`, `TIPOMOV`, `TOTAL` |
| `DEVOLUCIONES` | Detalle de devoluciones | `IDDEVOLUCION`, `IDVENTA`, `TOTAL` |
| `VENTATICKETS` | Tickets de venta | `IDVENTA`, `FORMAPAGO`, `TOTAL`, `ESTATUS` |

---

## 💰 Secciones del Corte de Cajero

### 1. DINERO EN CAJA
Representa el **efectivo físico** que debe haber en la caja al final del turno.

| Campo | Fuente | Descripción |
|-------|--------|-------------|
| **Fondo de Caja** | `TURNOS.FONDOCAJA` | Efectivo inicial del turno |
| **Ventas en Efectivo** | `TURNOS.VENTASEFECTIVO` | Ventas cobradas en efectivo |
| **Abonos en Efectivo** | `TURNOS.ABONOSEFECTIVO` | Abonos a créditos recibidos en efectivo |
| **Entradas** | `CORTE_MOVIMIENTOS` (TIPOMOV=1) | Entradas manuales de efectivo |
| **Salidas** | `CORTE_MOVIMIENTOS` (TIPOMOV=2) | Salidas manuales de efectivo |
| **Devoluciones en Efectivo** | `TURNOS.DEVOEFECTIVO` | Devoluciones de ventas pagadas en efectivo |

**Fórmula:**
```
Total Dinero en Caja = Fondo + Ventas Efectivo + Abonos + Entradas - Salidas - Devoluciones Efectivo
```

---

### 2. VENTAS
Representa el **total de ventas** del turno, independiente de la forma de pago.

| Campo | Fuente | Descripción |
|-------|--------|-------------|
| **Ventas Efectivo** | `TURNOS.VENTASEFECTIVO` | Ventas cobradas en efectivo |
| **Ventas Tarjeta** | `TURNOS.VENTASTARJETA` | Ventas cobradas con tarjeta |
| **Ventas Crédito** | `TURNOS.VENTASCREDITO` | Ventas a crédito (fiado) |
| **Ventas Vales** | `TURNOS.VENTASVALES` | Ventas cobradas con vales |
| **Devoluciones de Ventas** | Calculado | TODAS las devoluciones (cualquier forma de pago) |
| **Ganancia** | `TURNOS.GANANCIA` | Utilidad del turno |

**Fórmula:**
```
Total Ventas = Efectivo + Tarjeta + Crédito + Vales - Devoluciones
```

---

## ⚠️ DIFERENCIA IMPORTANTE

### Devoluciones en Efectivo vs Devoluciones de Ventas

| Concepto | Valor Ejemplo | Qué Incluye |
|----------|---------------|-------------|
| **Devoluciones en Efectivo** | $1,801,371 | Solo devoluciones de ventas que fueron pagadas en EFECTIVO |
| **Devoluciones de Ventas** | $1,960,080 | TODAS las devoluciones (efectivo + crédito + tarjeta + vales) |
| **Diferencia** | $158,709 | Devoluciones de ventas a CRÉDITO (no afectan el efectivo) |

### ¿Por qué son diferentes?
- **Devoluciones en Efectivo**: Afecta la caja física. Si el cliente pagó en efectivo y devuelve, se le regresa efectivo.
- **Devoluciones de Ventas**: Afecta el reporte de ventas totales. Incluye devoluciones de ventas a crédito donde no hay movimiento de efectivo.

---

## 🔧 Implementación Técnica

### Archivo: `corte_cajero.py`

```python
# Clases de datos
@dataclass
class DineroEnCaja:
    fondo_de_caja: float
    ventas_en_efectivo: float
    abonos_en_efectivo: float
    entradas: float
    salidas: float
    devoluciones_en_efectivo: float
    total: float  # Calculado

@dataclass
class Ventas:
    ventas_efectivo: float
    ventas_tarjeta: float
    ventas_credito: float
    ventas_vales: float
    devoluciones_ventas: float
    devoluciones_por_forma_pago: Dict[str, float]
    total: float  # Calculado
    ganancia: float

# Clase principal
class CorteCajeroManager:
    def obtener_corte_por_turno(turno_id) -> CorteCajero
    def obtener_turno_actual() -> int
    def obtener_ultimo_turno() -> int
```

### Consultas SQL Utilizadas

**Obtener datos del turno:**
```sql
SELECT IDTURNO, FONDOCAJA, VENTASEFECTIVO, ABONOSEFECTIVO, 
       VENTASTARJETA, VENTASCREDITO, VENTASVALES, 
       DEVOEFECTIVO, GANANCIA
FROM TURNOS 
WHERE IDTURNO = ?;
```

**Obtener entradas/salidas:**
```sql
SELECT COALESCE(SUM(TOTAL), 0) 
FROM CORTE_MOVIMIENTOS 
WHERE IDTURNO = ? AND TIPOMOV = ?;
-- TIPOMOV: 1 = Entrada, 2 = Salida
```

**Obtener devoluciones por forma de pago:**
```sql
SELECT VT.FORMAPAGO, SUM(D.TOTAL)
FROM DEVOLUCIONES D
JOIN VENTATICKETS VT ON D.IDVENTA = VT.IDVENTA
WHERE VT.IDTURNO = ?
GROUP BY VT.FORMAPAGO;
```

---

## 📱 Integración en GUI

### Módulo de Liquidación
Se agregó la sección **"CORTE CAJERO (ELEVENTA)"** que muestra:
- Dinero en Caja (6 campos + total)
- Ventas (6 campos + total)  
- Ganancia
- Explicación de diferencia en devoluciones

### Módulo de Asignar Repartidores
Se agregó un **resumen compacto** con los totales principales:
- Total Dinero en Caja
- Total Ventas
- Ganancia del Turno

---

## 💾 Persistencia en SQLite

Los datos del corte se guardan en la tabla `corte_cajero` de la base de datos local:

```sql
CREATE TABLE corte_cajero (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    turno_id INTEGER,
    fondo_caja REAL DEFAULT 0,
    ventas_efectivo REAL DEFAULT 0,
    abonos_efectivo REAL DEFAULT 0,
    entradas REAL DEFAULT 0,
    salidas REAL DEFAULT 0,
    devoluciones_efectivo REAL DEFAULT 0,
    total_dinero_caja REAL DEFAULT 0,
    ventas_tarjeta REAL DEFAULT 0,
    ventas_credito REAL DEFAULT 0,
    ventas_vales REAL DEFAULT 0,
    devoluciones_ventas REAL DEFAULT 0,
    total_ventas REAL DEFAULT 0,
    ganancia REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fecha, turno_id)
);
```

---

## 📋 Datos Verificados (Turno 445)

| Campo | Valor en Eleventa | Valor Extraído | ✓ |
|-------|-------------------|----------------|---|
| Fondo de Caja | $0.00 | $0.00 | ✅ |
| Ventas en Efectivo | $5,572,964 | $5,572,963.95 | ✅ |
| Entradas | $0.00 | $0.00 | ✅ |
| Devoluciones en Efectivo | $1,801,371 | $1,801,371.42 | ✅ |
| Total Dinero en Caja | $3,771,593 | $3,771,592.53 | ✅ |
| Total Vendido | $3,612,884 | $3,612,884.33 | ✅ |
| Devoluciones de Ventas | $1,960,080 | $1,960,079.62 | ✅ |
| Ganancia | $1,112,321 | $1,112,321.45 | ✅ |

---

## 🚀 Uso

```python
from corte_cajero import CorteCajeroManager

# Crear instancia
manager = CorteCajeroManager()

# Obtener corte del turno actual
turno_id = manager.obtener_turno_actual()
corte = manager.obtener_corte_por_turno(turno_id)

# Acceder a los datos
print(f"Total en Caja: ${corte.dinero_en_caja.total:,.2f}")
print(f"Total Ventas: ${corte.ventas.total:,.2f}")
print(f"Ganancia: ${corte.ganancia:,.2f}")
```

---

*Documentación generada el 3 de febrero de 2026*
