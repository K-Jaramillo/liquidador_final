# 📚 DOCUMENTACIÓN DEL SISTEMA LIQUIDADOR DE REPARTIDORES

**Versión:** 2.1.0  
**Última actualización:** 5 de Febrero de 2026

---

## 📑 ÍNDICE DE DOCUMENTACIÓN

| # | Documento | Descripción |
|---|-----------|-------------|
| 1 | [Descripción General](01_descripcion_general.md) | Propósito, características y requisitos del sistema |
| 2 | [Arquitectura del Sistema](02_arquitectura_sistema.md) | Estructura de archivos, clases y componentes |
| 3 | [Módulos del Sistema](03_modulos_sistema.md) | Detalle de cada pestaña y sus funcionalidades |
| 4 | [Base de Datos](04_base_datos.md) | Esquema SQLite y Firebird, tablas y relaciones |
| 5 | [Operaciones por Módulo](05_operaciones_modulo.md) | CRUD y operaciones específicas de cada módulo |
| 6 | [Flujo de Trabajo](06_flujo_trabajo.md) | Proceso diario completo paso a paso |
| 7 | [Cálculos Financieros](07_calculos_financieros.md) | Fórmulas y lógica de cálculos |
| 8 | [Integración Firebird](08_integracion_firebird.md) | Conexión con Eleventa PDV |

---

## 💰 FLUJO DEL DINERO: DE LA VENTA AL CIERRE DE CAJA

Este es el flujo completo que sigue el dinero desde que entra por una venta hasta el cierre de caja.

### 🔄 DIAGRAMA GENERAL DEL FLUJO

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PUNTO DE VENTA (ELEVENTA)                         │
│                                                                             │
│   Cliente paga → Cajero registra venta → Se genera factura en Firebird     │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENTRADA DE DINERO                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   EFECTIVO ──────────────────────────────────────────────► CAJA FÍSICA     │
│      │                                                          │           │
│      │   TARJETA ────────────────────────────────────► BANCO    │           │
│      │      │                                                   │           │
│      │      │   CRÉDITO ─────────────────────► CUENTA POR COBRAR│           │
│      │      │      │                                            │           │
│      ▼      ▼      ▼                                            ▼           │
│   ┌──────────────────────────────────────────────────────────────┐          │
│   │              TOTAL FACTURADO DEL DÍA                         │          │
│   │         (Registrado en VENTATICKETS de Firebird)             │          │
│   └──────────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LIQUIDADOR DE REPARTIDORES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ 1. CARGAR       │    │ 2. ASIGNAR      │    │ 3. REGISTRAR    │         │
│  │    FACTURAS     │───►│    REPARTIDORES │───►│    OPERACIONES  │         │
│  │    (Firebird)   │    │                 │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                        │                    │
│                                                        ▼                    │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    OPERACIONES DEL DÍA                          │       │
│  ├─────────────────────────────────────────────────────────────────┤       │
│  │                                                                 │       │
│  │  (-) Cancelaciones     → Facturas anuladas (devuelven dinero)   │       │
│  │  (-) Gastos            → Efectivo que sale para gastos          │       │
│  │  (-) Pago Proveedores  → Pagos a proveedores                    │       │
│  │  (-) Préstamos         → Dinero prestado a empleados            │       │
│  │  (-) Nómina            → Pagos de sueldo                        │       │
│  │  (-) Socios            → Retiros de socios                      │       │
│  │  (-) Transferencias    → Envíos bancarios                       │       │
│  │  (+) Ingresos Extras   → Dinero que entra (no ventas)           │       │
│  │                                                                 │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                        │                    │
│                                                        ▼                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ 4. CONTEO DE    │    │ 5. CUADRE DE    │    │ 6. CIERRE DE    │         │
│  │    DINERO       │───►│    CAJA         │───►│    DÍA          │         │
│  │    (Físico)     │    │                 │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 📋 PASO A PASO DETALLADO

#### FASE 1: GENERACIÓN DE VENTAS (En Eleventa PDV)

```
CLIENTE LLEGA A COMPRAR
         │
         ▼
┌─────────────────────────────────────┐
│  Cajero registra productos en PDV   │
│  - Escanea código de barras         │
│  - Ingresa cantidad                 │
│  - Sistema calcula total            │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Cliente elige forma de pago        │
│                                     │
│  ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │EFECTIVO │ │ TARJETA │ │CRÉDITO│ │
│  └────┬────┘ └────┬────┘ └───┬───┘ │
└───────┼───────────┼──────────┼─────┘
        │           │          │
        ▼           ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ VA A    │ │ VA A    │ │ QUEDA   │
   │ CAJA    │ │ BANCO   │ │ PENDIENTE│
   │ FÍSICA  │ │ (POS)   │ │ COBRO   │
   └─────────┘ └─────────┘ └─────────┘
```

**¿Qué se registra en Firebird?**
- Tabla `VENTATICKETS`: Factura completa con total, cliente, forma de pago
- Campos importantes:
  - `FOLIO`: Número de factura
  - `TOTAL`: Monto total
  - `FORMAPAGO`: Efectivo/Tarjeta/Crédito
  - `CREDITO`: 1 si es a crédito
  - `TOTAL_CREDITO`: Monto a crédito
  - `CANCELADO`: 1 si fue cancelada

---

#### FASE 2: CARGA EN LIQUIDADOR

```
LIQUIDADOR SE ABRE
         │
         ▼
┌─────────────────────────────────────┐
│  Conexión a Firebird (PDVDATA.FDB)  │
│                                     │
│  SELECT * FROM VENTATICKETS         │
│  WHERE FECHA = 'HOY'                │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Se cargan todas las facturas       │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ Folio │ Total  │ Estado      │  │
│  ├───────┼────────┼─────────────┤  │
│  │ 1001  │ $500   │ ✅ Normal    │  │
│  │ 1002  │ $1,200 │ 💳 Crédito   │  │
│  │ 1003  │ $300   │ ❌ Cancelada │  │
│  │ 1004  │ $750   │ ✅ Normal    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Clasificación automática:**
- ✅ **Normal**: Venta de contado válida → Suma al efectivo
- 💳 **Crédito**: Venta a crédito → No suma al efectivo inmediato
- ❌ **Cancelada mismo día**: Se resta del total facturado
- ⚠️ **Cancelada otro día**: Solo informativa, no afecta

---

#### FASE 3: ASIGNACIÓN DE REPARTIDORES

```
┌─────────────────────────────────────────────────────────────┐
│  FACTURAS SIN ASIGNAR                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Folio 1001 - $500 - CLIENTE X          [Sin asignar] │  │
│  │ Folio 1004 - $750 - CLIENTE Y          [Sin asignar] │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           SELECCIONAR REPARTIDOR                      │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │  │
│  │  │ DAVID  │  │CRISTIAN│  │ CAJERO │  │  OTRO  │      │  │
│  │  └────────┘  └────────┘  └────────┘  └────────┘      │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  FACTURAS ASIGNADAS                                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Folio 1001 - $500 - CLIENTE X          [DAVID]       │  │
│  │ Folio 1004 - $750 - CLIENTE Y          [CRISTIAN]    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**¿Por qué asignar?**
- Saber quién entregó cada pedido
- Calcular comisiones
- Controlar gastos por persona
- Rastrear faltantes

---

#### FASE 4: REGISTRO DE SALIDAS DE EFECTIVO

```
┌─────────────────────────────────────────────────────────────┐
│                    SALIDAS DE EFECTIVO                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  💼 GASTOS REPARTIDOR                                       │
│  ├── DAVID: Gasolina $200                                   │
│  ├── DAVID: Estacionamiento $50                             │
│  └── CRISTIAN: Reparación moto $300                         │
│                                          Subtotal: $550     │
│                                                             │
│  🏪 PAGO PROVEEDORES                                        │
│  ├── Coca-Cola: Refresco $1,500                             │
│  └── Bimbo: Pan $800                                        │
│                                          Subtotal: $2,300   │
│                                                             │
│  💰 PRÉSTAMOS                                               │
│  └── DAVID: Préstamo personal $500                          │
│                                          Subtotal: $500     │
│                                                             │
│  👷 NÓMINA                                                  │
│  ├── DAVID: Sueldo semanal $1,200                           │
│  └── CRISTIAN: Sueldo semanal $1,200                        │
│                                          Subtotal: $2,400   │
│                                                             │
│  👔 SOCIOS                                                  │
│  └── Socio 1: Retiro $3,000                                 │
│                                          Subtotal: $3,000   │
│                                                             │
│  🏦 TRANSFERENCIAS                                          │
│  └── Banco: Depósito $5,000                                 │
│                                          Subtotal: $5,000   │
│                                                             │
│  ═══════════════════════════════════════════════════════    │
│  TOTAL SALIDAS:                              $13,750        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Cada salida reduce el efectivo esperado en caja.**

---

#### FASE 5: CONTEO FÍSICO DE DINERO

```
┌─────────────────────────────────────────────────────────────┐
│                   CONTEO DE DINERO                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 SESIÓN: CONTEO FINAL                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  DENOMINACIÓN  │  CANTIDAD  │    SUBTOTAL           │    │
│  ├────────────────┼────────────┼───────────────────────┤    │
│  │  $1,000        │     5      │    $5,000             │    │
│  │  $500          │     8      │    $4,000             │    │
│  │  $200          │    12      │    $2,400             │    │
│  │  $100          │    15      │    $1,500             │    │
│  │  $50           │    10      │      $500             │    │
│  │  $20           │    25      │      $500             │    │
│  │  Moneda $10    │    30      │      $300             │    │
│  │  Moneda $5     │    20      │      $100             │    │
│  │  Moneda $1     │    50      │       $50             │    │
│  ├────────────────┴────────────┼───────────────────────┤    │
│  │  TOTAL CONTADO              │   $14,350             │    │
│  └─────────────────────────────┴───────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

#### FASE 6: CUADRE DE CAJA (El momento de la verdad)

```
┌─────────────────────────────────────────────────────────────┐
│                      CUADRE DE CAJA                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📥 ENTRADAS                                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Total Facturado del día:              $45,000      │    │
│  │  (-) Facturas Canceladas:              -$2,500      │    │
│  │  (-) Ventas a Crédito:                 -$8,000      │    │
│  │  (+) Fondo de Caja Inicial:            +$3,000      │    │
│  │  ────────────────────────────────────────────────   │    │
│  │  = EFECTIVO QUE DEBIÓ ENTRAR:          $37,500      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  📤 SALIDAS                                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Gastos Repartidores:                    -$550      │    │
│  │  Gastos Cajero:                          -$200      │    │
│  │  Pago Proveedores:                     -$2,300      │    │
│  │  Préstamos:                              -$500      │    │
│  │  Nómina:                               -$2,400      │    │
│  │  Socios:                               -$3,000      │    │
│  │  Transferencias:                       -$5,000      │    │
│  │  Créditos Punteados:                   -$4,500      │    │
│  │  ────────────────────────────────────────────────   │    │
│  │  = TOTAL SALIDAS:                     -$18,450      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  📊 RESULTADO                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │  EFECTIVO ESPERADO EN CAJA:                         │    │
│  │  $37,500 - $18,450 = $19,050                        │    │
│  │                                                     │    │
│  │  EFECTIVO CONTADO:              $14,350             │    │
│  │                                                     │    │
│  │  ════════════════════════════════════════════       │    │
│  │  DIFERENCIA:                    -$4,700  ⚠️         │    │
│  │  ════════════════════════════════════════════       │    │
│  │                                                     │    │
│  │  ❌ FALTANTE: Hay $4,700 menos de lo esperado       │    │
│  │     (Requiere investigación)                        │    │
│  │                                                     │    │
│  │  ✅ SOBRANTE: Habría más de lo esperado             │    │
│  │     (Posible error en cambio o ingreso no          │    │
│  │      registrado)                                    │    │
│  │                                                     │    │
│  │  ⭐ CUADRE PERFECTO: Diferencia = $0                │    │
│  │     (Todo está correcto)                            │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 🎯 RESUMEN DEL FLUJO EN UNA IMAGEN

```
    VENTA EN PDV                    LIQUIDADOR                    CIERRE
         │                              │                            │
         │   ┌──────────────────────────┼────────────────────────┐   │
         ▼   ▼                          ▼                        ▼   ▼
    
    [$] ──► FACTURA ──► CARGAR ──► ASIGNAR ──► REGISTRAR ──► CONTAR ──► CUADRAR
     │        │           │          │          SALIDAS        │         │
     │        │           │          │             │           │         │
  Cliente   Firebird    SQLite    Repartidor    Gastos      Físico   Diferencia
   paga    registra     local     asignado    Préstamos   en caja      $0 ✓
                                              Nómina                  -$X ✗
                                              etc.                    +$X ?
```

---

### ⚡ FÓRMULAS CLAVE

```
TOTAL VENDIDO = Total Facturado - Canceladas - Devoluciones

EFECTIVO ESPERADO = Total Vendido - Créditos + Fondo Inicial

TOTAL DESCUENTOS = Gastos + Proveedores + Préstamos + Nómina + Socios + Transferencias

EFECTIVO FINAL ESPERADO = Efectivo Esperado - Total Descuentos - Créditos Punteados

DIFERENCIA = Dinero Contado - Efectivo Final Esperado

Si Diferencia = 0  → ✅ Cuadre perfecto
Si Diferencia < 0  → ❌ Faltante (investigar)
Si Diferencia > 0  → ⚠️ Sobrante (verificar)
```

---

## 🚀 INICIO RÁPIDO

Para usar el sistema:

1. **Abrir la aplicación** → `python main.py`
2. **Verificar la fecha** → Barra superior
3. **Cargar facturas** → Automático al abrir
4. **Asignar repartidores** → Tab "Asignar Repartidores"
5. **Registrar salidas** → Tab "Gastos Adicionales"
6. **Contar dinero** → Tab "Conteo de Dinero"
7. **Verificar cuadre** → Tab "Liquidación"

---

*Documentación del Sistema Liquidador de Repartidores v2.1.0*
