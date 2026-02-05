# 💰 7. CÁLCULOS FINANCIEROS

Todas las fórmulas y operaciones matemáticas del sistema.

---

## 7.1 Resumen de Fórmulas

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    FÓRMULAS PRINCIPALES DEL SISTEMA                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  TOTAL VENTA = Σ (Facturas del día)                                           ║
║                                                                               ║
║  TOTAL DESCUENTOS = Gastos Rep + Proveedores + Préstamos + Nómina +           ║
║                     Socios + Transferencias + Cancelaciones                   ║
║                                                                               ║
║  EFECTIVO ESPERADO = Total Venta - Total Descuentos - Créditos Punteados      ║
║                                                                               ║
║  DIFERENCIA = Conteo Físico - Efectivo Esperado                               ║
║                                                                               ║
║  Estado:  Diferencia = 0  → CUADRADO                                          ║
║           Diferencia > 0  → SOBRANTE                                          ║
║           Diferencia < 0  → FALTANTE                                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 7.2 Cálculo del Total de Ventas

### 7.2.1 Fórmula Base

```python
def calcular_total_ventas(facturas):
    """
    Total de ventas = Suma de todas las facturas del día
    Excluye: Facturas canceladas
    """
    total = 0
    for factura in facturas:
        if factura['estado'] != 'CANCELADA':
            total += factura['monto_total']
    return total
```

### 7.2.2 Fuente de Datos

| Campo | Fuente | Tabla |
|-------|--------|-------|
| Monto factura | Firebird | DOCUMENTO |
| Estado factura | Firebird | DOCUMENTO.status |
| Fecha factura | Firebird | DOCUMENTO.fechahoraventa |

### 7.2.3 Ejemplo Numérico

```
Facturas del día:
  F001: $1,500.00 (Entregada)     ✓
  F002: $2,300.00 (Entregada)     ✓
  F003:   $850.00 (Cancelada)     ✗
  F004: $3,100.00 (Entregada)     ✓
  F005: $1,200.00 (Pendiente)     ✓
                               ──────────
  TOTAL VENTAS:                 $8,100.00
  (No incluye F003 por estar cancelada)
```

---

## 7.3 Cálculo de Descuentos y Ajustes

### 7.3.1 Desglose de Categorías

```
TOTAL DESCUENTOS
│
├── Gastos de Repartidores
│   └── Σ gastos_repartidor WHERE fecha = hoy
│
├── Pago a Proveedores
│   └── Σ pago_proveedores WHERE fecha = hoy
│
├── Préstamos a Empleados
│   └── Σ prestamos WHERE fecha = hoy
│
├── Nómina / Sueldos
│   └── Σ nomina WHERE fecha = hoy
│
├── Retiros de Socios
│   └── Σ socios WHERE fecha = hoy
│
├── Transferencias Bancarias
│   └── Σ transferencias WHERE fecha = hoy
│
└── Cancelaciones
    └── Σ facturas_canceladas WHERE fecha = hoy
```

### 7.3.2 Fórmula Consolidada

```python
def calcular_total_descuentos(fecha, repartidor=None):
    """
    Calcula la suma total de todos los descuentos y ajustes.
    
    Si repartidor se especifica:
      - Gastos: filtrados por ese repartidor
      - Proveedores: filtrados por ese repartidor
      - Préstamos: filtrados por ese repartidor
      - Cancelaciones: filtradas por ese repartidor
      - Transferencias: filtradas por destinatario = repartidor
    
    Si repartidor es None:
      - Se suman todos los registros del día
    """
    
    total = 0
    
    # Gastos de repartidor
    total += db.obtener_total_gastos_repartidor(fecha, repartidor)
    
    # Pago a proveedores
    total += db.obtener_total_pago_proveedores(fecha, repartidor)
    
    # Préstamos
    total += db.obtener_total_prestamos(fecha, repartidor)
    
    # Nómina (solo en totales generales)
    if repartidor is None:
        total += db.obtener_total_nomina(fecha)
    
    # Socios (solo en totales generales)
    if repartidor is None:
        total += db.obtener_total_socios(fecha)
    
    # Transferencias
    total += db.obtener_total_transferencias(fecha, repartidor)
    
    # Cancelaciones
    total += db.obtener_total_cancelaciones(fecha, repartidor)
    
    return total
```

### 7.3.3 Ejemplo Numérico

```
Descuentos del día:

  GASTOS REPARTIDORES:
    Gasolina (Juan):         $500.00
    Comida (Pedro):          $150.00
    Refacción (Juan):        $350.00
                            ─────────
    Subtotal:              $1,000.00

  PAGO PROVEEDORES:
    Coca-Cola:             $5,000.00
    Sabritas:              $2,500.00
                            ─────────
    Subtotal:              $7,500.00

  PRÉSTAMOS:
    Adelanto (María):        $800.00
                            ─────────
    Subtotal:                $800.00

  NÓMINA:
    Sueldo (Carlos):       $2,000.00
                            ─────────
    Subtotal:              $2,000.00

  SOCIOS:
    Retiro (Socio A):      $1,500.00
                            ─────────
    Subtotal:              $1,500.00

  TRANSFERENCIAS:
    Depósito Banco:        $3,000.00
                            ─────────
    Subtotal:              $3,000.00

  CANCELACIONES:
    Factura F003:            $850.00
                            ─────────
    Subtotal:                $850.00

═══════════════════════════════════════
  TOTAL DESCUENTOS:       $16,650.00
═══════════════════════════════════════
```

---

## 7.4 Cálculo de Créditos Punteados

### 7.4.1 Concepto

```
Los créditos punteados representan ventas que fueron registradas 
pero el dinero NO está en caja porque se dieron a crédito.

Al "puntear" un crédito, indicamos que ya fue verificado/cobrado
y por lo tanto se RESTA del efectivo esperado.

┌────────────────────────────────────────────────────────────────┐
│                    FLUJO DE CRÉDITOS                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Venta a Crédito        Punteado        Cobro                  │
│       │                    │              │                    │
│       ▼                    ▼              ▼                    │
│  ┌─────────┐         ┌─────────┐    ┌─────────┐               │
│  │ Factura │ ──────► │Crédito  │ ──►│ Dinero  │               │
│  │emitida  │         │punteado │    │ en caja │               │
│  └─────────┘         └─────────┘    └─────────┘               │
│       │                    │              │                    │
│       │                    │              │                    │
│   Suma en            Resta del       Suma en                   │
│   Total Ventas       Esperado        Conteo                    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 7.4.2 Fórmula

```python
def calcular_creditos_punteados(fecha, repartidor=None):
    """
    Suma el total de créditos que han sido punteados en la fecha.
    
    Crédito punteado = El operador verificó que la venta fue 
                       efectivamente a crédito y la marcó.
    """
    query = """
        SELECT SUM(monto - abono) as total
        FROM creditos_punteados
        WHERE fecha = ? AND punteado = 1
    """
    
    if repartidor:
        query += " AND repartidor = ?"
        params = (fecha, repartidor)
    else:
        params = (fecha,)
    
    result = db.execute(query, params)
    return result['total'] or 0
```

### 7.4.3 Ejemplo

```
Créditos del día:

  Cliente A - Factura F010:  $3,500.00
    Punteado: ✓
    Abono: $500.00
    → Resta: $3,000.00

  Cliente B - Factura F015:  $2,000.00
    Punteado: ✓
    Abono: $0.00
    → Resta: $2,000.00

  Cliente C - Factura F020:  $1,500.00
    Punteado: ✗ (no punteado aún)
    → Resta: $0.00 (no cuenta)

═══════════════════════════════════════
  TOTAL CRÉDITOS PUNTEADOS: $5,000.00
═══════════════════════════════════════
```

---

## 7.5 Cálculo del Efectivo Esperado

### 7.5.1 Fórmula Maestra

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   EFECTIVO ESPERADO = TOTAL VENTAS                                ║
║                     - TOTAL DESCUENTOS                            ║
║                     - CRÉDITOS PUNTEADOS                          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### 7.5.2 Implementación

```python
def calcular_efectivo_esperado(fecha, repartidor=None):
    """
    Calcula cuánto dinero DEBERÍA haber en caja.
    
    Parámetros:
        fecha: Fecha de la liquidación
        repartidor: Opcional, para filtrar por un repartidor específico
    
    Retorna:
        float: Monto esperado en caja
    """
    
    # Obtener total de ventas
    if repartidor:
        total_ventas = obtener_total_ventas_repartidor(fecha, repartidor)
    else:
        total_ventas = obtener_total_ventas(fecha)
    
    # Obtener total de descuentos
    total_descuentos = calcular_total_descuentos(fecha, repartidor)
    
    # Obtener créditos punteados
    creditos_punteados = calcular_creditos_punteados(fecha, repartidor)
    
    # Calcular efectivo esperado
    efectivo_esperado = total_ventas - total_descuentos - creditos_punteados
    
    return efectivo_esperado
```

### 7.5.3 Ejemplo Completo

```
CÁLCULO DE EFECTIVO ESPERADO
═══════════════════════════════════════════════════════════════

TOTAL VENTAS:                            +$40,500.00
  (Suma de todas las facturas no canceladas)

MENOS - DESCUENTOS:                      -$16,650.00
  ├── Gastos Repartidores:    $1,000.00
  ├── Pago Proveedores:       $7,500.00
  ├── Préstamos:                $800.00
  ├── Nómina:                 $2,000.00
  ├── Socios:                 $1,500.00
  ├── Transferencias:         $3,000.00
  └── Cancelaciones:            $850.00

MENOS - CRÉDITOS PUNTEADOS:               -$5,000.00
  ├── Cliente A (F010):       $3,000.00
  └── Cliente B (F015):       $2,000.00

═══════════════════════════════════════════════════════════════
EFECTIVO ESPERADO:                       =$18,850.00
═══════════════════════════════════════════════════════════════
```

---

## 7.6 Cálculo del Conteo de Dinero

### 7.6.1 Estructura de Denominaciones

```python
DENOMINACIONES = {
    'billetes': {
        1000: 'Billetes de $1000',
        500:  'Billetes de $500',
        200:  'Billetes de $200',
        100:  'Billetes de $100',
        50:   'Billetes de $50',
        20:   'Billetes de $20',
    },
    'monedas': {
        20:    'Monedas de $20',
        10:    'Monedas de $10',
        5:     'Monedas de $5',
        2:     'Monedas de $2',
        1:     'Monedas de $1',
        0.50:  'Monedas de $0.50',
    }
}
```

### 7.6.2 Fórmula de Conteo

```python
def calcular_total_conteo(conteo):
    """
    Calcula el total del dinero físico contado.
    
    Parámetros:
        conteo: Diccionario con cantidades por denominación
                {
                    'b1000': 5,   # 5 billetes de $1000
                    'b500': 10,   # 10 billetes de $500
                    ...
                    'm1': 50,     # 50 monedas de $1
                }
    
    Retorna:
        float: Total de dinero contado
    """
    
    total = 0
    
    # Billetes
    total += conteo.get('b1000', 0) * 1000
    total += conteo.get('b500', 0) * 500
    total += conteo.get('b200', 0) * 200
    total += conteo.get('b100', 0) * 100
    total += conteo.get('b50', 0) * 50
    total += conteo.get('b20', 0) * 20
    
    # Monedas
    total += conteo.get('m20', 0) * 20
    total += conteo.get('m10', 0) * 10
    total += conteo.get('m5', 0) * 5
    total += conteo.get('m2', 0) * 2
    total += conteo.get('m1', 0) * 1
    total += conteo.get('m050', 0) * 0.50
    
    return total
```

### 7.6.3 Ejemplo de Conteo

```
CONTEO DE DINERO FÍSICO
═══════════════════════════════════════════════════════════════

BILLETES:
  Billetes de $1000:    5  ×  $1,000.00  =  $5,000.00
  Billetes de $500:    12  ×    $500.00  =  $6,000.00
  Billetes de $200:     8  ×    $200.00  =  $1,600.00
  Billetes de $100:    35  ×    $100.00  =  $3,500.00
  Billetes de $50:     15  ×     $50.00  =    $750.00
  Billetes de $20:     20  ×     $20.00  =    $400.00
                                          ───────────
  Subtotal Billetes:                      $17,250.00

MONEDAS:
  Monedas de $20:       5  ×     $20.00  =    $100.00
  Monedas de $10:      30  ×     $10.00  =    $300.00
  Monedas de $5:       50  ×      $5.00  =    $250.00
  Monedas de $2:       75  ×      $2.00  =    $150.00
  Monedas de $1:      200  ×      $1.00  =    $200.00
  Monedas de $0.50:   100  ×      $0.50  =     $50.00
                                          ───────────
  Subtotal Monedas:                        $1,050.00

═══════════════════════════════════════════════════════════════
TOTAL CONTEO:                             $18,300.00
═══════════════════════════════════════════════════════════════
```

---

## 7.7 Cálculo de la Diferencia

### 7.7.1 Fórmula

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   DIFERENCIA = CONTEO FÍSICO - EFECTIVO ESPERADO                  ║
║                                                                   ║
║   Si DIFERENCIA = 0    →  ✅ CUADRADO (perfecto)                  ║
║   Si DIFERENCIA > 0    →  ⚠️ SOBRANTE (hay más dinero)            ║
║   Si DIFERENCIA < 0    →  ❌ FALTANTE (falta dinero)              ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### 7.7.2 Implementación

```python
def calcular_diferencia(fecha, repartidor=None):
    """
    Calcula la diferencia entre el dinero contado y el esperado.
    
    Retorna:
        tuple: (diferencia, estado)
            diferencia: float con el monto de diferencia
            estado: str 'CUADRADO', 'SOBRANTE', o 'FALTANTE'
    """
    
    # Obtener efectivo esperado
    esperado = calcular_efectivo_esperado(fecha, repartidor)
    
    # Obtener conteo físico
    conteo = obtener_conteo_dinero(fecha, repartidor)
    
    # Calcular diferencia
    diferencia = conteo - esperado
    
    # Determinar estado
    tolerancia = 0.01  # Margen para redondeos
    
    if abs(diferencia) < tolerancia:
        estado = 'CUADRADO'
    elif diferencia > 0:
        estado = 'SOBRANTE'
    else:
        estado = 'FALTANTE'
    
    return diferencia, estado
```

### 7.7.3 Ejemplo Final

```
CUADRE DE CAJA
═══════════════════════════════════════════════════════════════

  Efectivo Esperado:           $18,850.00
  Conteo Físico:               $18,300.00
                              ───────────
  DIFERENCIA:                    -$550.00

  ESTADO: ❌ FALTANTE

═══════════════════════════════════════════════════════════════

Análisis del Faltante:
  Posibles causas:
  • Gasto no registrado: $550 aprox
  • Error al dar cambio
  • Crédito no punteado
  
  Acción recomendada:
  → Revisar todos los comprobantes del día
  → Verificar si hay algún gasto sin registrar
```

---

## 7.8 Cálculos por Repartidor

### 7.8.1 Liquidación Individual

```python
def liquidar_repartidor(fecha, repartidor):
    """
    Calcula la liquidación específica de un repartidor.
    
    Incluye solo:
    - Facturas asignadas a ese repartidor
    - Gastos de ese repartidor
    - Créditos entregados por ese repartidor
    - Cancelaciones de ese repartidor
    - Transferencias donde él es el destinatario
    """
    
    # Total vendido por el repartidor
    total_vendido = obtener_total_ventas_repartidor(fecha, repartidor)
    
    # Descuentos del repartidor
    gastos = obtener_gastos_repartidor(fecha, repartidor)
    cancelaciones = obtener_cancelaciones_repartidor(fecha, repartidor)
    transferencias = obtener_transferencias_repartidor(fecha, repartidor)
    
    total_descuentos = gastos + cancelaciones + transferencias
    
    # Créditos del repartidor
    creditos = obtener_creditos_punteados_repartidor(fecha, repartidor)
    
    # Efectivo a entregar
    a_entregar = total_vendido - total_descuentos - creditos
    
    return {
        'repartidor': repartidor,
        'total_vendido': total_vendido,
        'gastos': gastos,
        'cancelaciones': cancelaciones,
        'transferencias': transferencias,
        'total_descuentos': total_descuentos,
        'creditos': creditos,
        'a_entregar': a_entregar
    }
```

### 7.8.2 Ejemplo por Repartidor

```
LIQUIDACIÓN DE: JUAN PÉREZ
Fecha: 2026-02-05
═══════════════════════════════════════════════════════════════

FACTURAS ENTREGADAS:                     +$12,500.00
  F001: $1,500.00  - Cliente ABC
  F004: $3,100.00  - Cliente DEF
  F008: $2,800.00  - Cliente GHI
  F012: $5,100.00  - Cliente JKL

MENOS - GASTOS:                           -$850.00
  Gasolina:           $500.00
  Refacción moto:     $350.00

MENOS - CANCELACIONES:                    -$0.00
  (ninguna)

MENOS - TRANSFERENCIAS:                   -$1,000.00
  Depósito a cta proveedor: $1,000.00

MENOS - CRÉDITOS PUNTEADOS:               -$3,500.00
  Cliente ABC (F001): $1,500.00
  Cliente JKL (F012): $2,000.00

═══════════════════════════════════════════════════════════════
DEBE ENTREGAR:                            $7,150.00
═══════════════════════════════════════════════════════════════
```

---

## 7.9 Fórmulas de Descuentos por Factura

### 7.9.1 Estructura

```python
def calcular_descuento_factura(factura_id):
    """
    Calcula los descuentos aplicados a una factura específica.
    
    Los descuentos por factura se aplican ANTES de calcular
    el total que el repartidor debe entregar.
    """
    
    descuentos = obtener_descuentos_factura(factura_id)
    
    total_descuento = sum(d['monto'] for d in descuentos)
    
    # El descuento reduce el monto que el repartidor debe entregar
    # pero NO cambia el total de la factura en el sistema de ventas
    
    return total_descuento
```

### 7.9.2 Tipos de Descuentos

```
DESCUENTOS POR FACTURA
│
├── Merma / Producto dañado
│   └── Producto llegó dañado, cliente no paga ese item
│
├── Promoción / Descuento comercial
│   └── Se aplicó descuento adicional al cliente
│
├── Error de precio
│   └── Se cobró precio incorrecto, se ajusta
│
└── Devolución parcial
    └── Cliente devolvió parte del pedido
```

---

## 7.10 Formatos de Visualización

### 7.10.1 Formato de Moneda

```python
def formatear_moneda(monto):
    """
    Formatea un monto como moneda mexicana.
    
    Ejemplos:
        1234.56  →  "$1,234.56"
        -500.00  →  "-$500.00"
        0        →  "$0.00"
    """
    if monto < 0:
        return f"-${abs(monto):,.2f}"
    return f"${monto:,.2f}"
```

### 7.10.2 Formato de Diferencia con Color

```python
def formatear_diferencia(diferencia):
    """
    Retorna el formato y color según la diferencia.
    """
    if abs(diferencia) < 0.01:
        return ("$0.00", "verde", "✅ CUADRADO")
    elif diferencia > 0:
        return (f"+${diferencia:,.2f}", "azul", "⚠️ SOBRANTE")
    else:
        return (f"-${abs(diferencia):,.2f}", "rojo", "❌ FALTANTE")
```

---

*Siguiente: [08. Integración con Firebird](08_integracion_firebird.md)*
