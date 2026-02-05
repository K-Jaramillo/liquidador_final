# 📖 1. DESCRIPCIÓN GENERAL DEL SISTEMA

## 1.1 ¿Qué es el Liquidador de Repartidores?

El **Liquidador de Repartidores** es una aplicación de escritorio diseñada para gestionar el proceso completo de liquidación diaria de un negocio con entregas a domicilio. Integra datos del sistema de punto de venta Eleventa (Firebird) con una base de datos local SQLite para control financiero.

---

## 1.2 Propósito Principal

El sistema resuelve el problema de:

> "¿Cuánto dinero debería tener en caja al final del día y cómo se llegó a esa cifra?"

Permite:
- Saber exactamente cuánto vendió cada repartidor
- Controlar todos los gastos y salidas de efectivo
- Cuadrar el dinero físico contra lo esperado
- Detectar faltantes o sobrantes
- Mantener un historial de operaciones

---

## 1.3 Usuarios del Sistema

| Rol | Uso Principal |
|-----|---------------|
| **Cajero/Administrador** | Opera el sistema diariamente, registra gastos, cuenta dinero |
| **Dueño/Gerente** | Revisa liquidaciones, analiza diferencias |
| **Repartidores** | Sus entregas son rastreadas (no usan el sistema directamente) |

---

## 1.4 Características Principales

### 📊 Integración con Eleventa PDV
- Conexión directa a base de datos Firebird (PDVDATA.FDB)
- Carga automática de facturas del día
- Lectura de corte de caja
- Información de cancelaciones y devoluciones

### 👥 Gestión de Repartidores
- Catálogo de repartidores activos
- Asignación de facturas individual o masiva
- Filtros por repartidor para análisis
- Rastreo de quién entregó cada pedido

### 💰 Control Financiero Completo
- Registro de múltiples tipos de salidas:
  - Gastos operativos
  - Pagos a proveedores
  - Préstamos a empleados
  - Nómina
  - Retiros de socios
  - Transferencias bancarias
- Descuentos y ajustes por factura
- Manejo de créditos y abonos

### 🧮 Conteo de Dinero
- Conteo por denominaciones (billetes y monedas)
- Múltiples sesiones de conteo
- Cálculo automático de totales
- Comparación con esperado

### 📋 Herramientas Adicionales
- Sistema de notas adhesivas
- Marcado de créditos punteados
- Exportación de datos
- Historial de liquidaciones

---

## 1.5 Requisitos del Sistema

### Hardware Mínimo
- Procesador: 1 GHz o superior
- RAM: 2 GB
- Espacio en disco: 100 MB (más datos)
- Resolución: 1280x720 o superior

### Software Requerido

#### Windows
```
- Windows 7 o superior
- Python 3.8+ (si se ejecuta desde código)
- Firebird 2.5 Client (para conexión a Eleventa)
```

#### Linux (Ubuntu/Debian)
```
- Ubuntu 18.04+ / Debian 10+
- Python 3.8+
- Librerías Firebird embebidas (incluidas)
- Tkinter (python3-tk)
```

### Dependencias Python
```
tkcalendar      # Selector de fecha (opcional)
fdb             # Conexión Firebird (opcional para conexión directa)
```

---

## 1.6 Instalación

### Windows
1. Copiar carpeta `liquidador_final` a ubicación deseada
2. Asegurar que `PDVDATA.FDB` está accesible
3. Ejecutar `Iniciar_Liquidador.bat` o `python main.py`

### Linux
1. Copiar carpeta `liquidador_final`
2. Instalar dependencias:
   ```bash
   sudo apt install python3-tk
   pip install tkcalendar
   ```
3. Dar permisos de ejecución:
   ```bash
   chmod +x iniciar_linux.sh
   ```
4. Ejecutar:
   ```bash
   ./iniciar_linux.sh
   # o
   python3 main.py
   ```

---

## 1.7 Modos de Operación

### Modo Completo (Con Firebird)
- Lee facturas directamente de Eleventa
- Obtiene corte de caja automáticamente
- Sincroniza cancelaciones
- **Requiere:** PDVDATA.FDB accesible

### Modo Local (Sin Firebird)
- Trabaja solo con datos SQLite
- Para registro manual de operaciones
- Útil para pruebas o cuando Firebird no está disponible
- **Funciona con:** Solo la aplicación

---

## 1.8 Estructura de una Sesión Típica

```
1. APERTURA (8:00 AM)
   └── Abrir sistema, verificar fecha
   
2. DURANTE EL DÍA
   ├── Las ventas se registran en Eleventa (automático)
   ├── Se asignan repartidores a facturas
   └── Se registran gastos conforme ocurren
   
3. CIERRE (10:00 PM)
   ├── Recargar facturas finales
   ├── Completar registro de gastos
   ├── Contar dinero físico
   ├── Revisar cuadre
   └── Investigar diferencias si las hay

4. POST-CIERRE
   ├── Datos quedan guardados en SQLite
   └── Disponibles para consulta histórica
```

---

## 1.9 Conceptos Clave

### Factura
Documento de venta generado en Eleventa. Tiene un folio único, total, cliente y forma de pago.

### Asignación
Relación entre una factura y el repartidor que la entregó. Permite rastrear responsabilidades.

### Descuento
Ajuste aplicado a una factura específica. Puede ser por:
- **Ajuste de precio**: Error en precio original
- **Devolución**: Cliente devolvió productos
- **Crédito**: Aplicación de crédito a favor

### Cancelación
Factura anulada completamente. Si se cancela el mismo día, reduce el total vendido.

### Crédito Punteado
Factura a crédito que ya fue verificada/cobrada pero aún no liquidada en sistema.

### Cuadre
Comparación entre el efectivo esperado (calculado) y el efectivo contado (físico).

### Diferencia
Resultado del cuadre:
- **$0**: Perfecto, todo coincide
- **Negativo**: Faltante, hay menos dinero del esperado
- **Positivo**: Sobrante, hay más dinero del esperado

---

## 1.10 Beneficios del Sistema

| Sin Sistema | Con Sistema |
|-------------|-------------|
| Cálculos manuales propensos a errores | Cálculos automáticos precisos |
| Sin rastreo de quién entregó qué | Asignación clara por repartidor |
| Difícil detectar faltantes | Diferencias identificadas al instante |
| Sin historial | Registro completo consultable |
| Proceso lento de cuadre | Cuadre en minutos |
| Múltiples hojas de papel | Todo en un solo lugar |

---

## 1.11 Limitaciones Conocidas

1. **Solo lectura de Firebird**: No modifica datos de Eleventa
2. **Un día a la vez**: Diseñado para liquidación diaria
3. **Moneda única**: Pesos mexicanos (configurable)
4. **Sin conexión remota**: Requiere acceso local a base de datos
5. **Usuario único**: No maneja múltiples usuarios simultáneos

---

## 1.12 Glosario de Términos

| Término | Definición |
|---------|------------|
| **PDV** | Punto de Venta (Eleventa) |
| **Firebird** | Sistema de base de datos usado por Eleventa |
| **SQLite** | Base de datos local del liquidador |
| **Folio** | Número único de factura |
| **Turno** | Sesión de caja en Eleventa |
| **Corte** | Resumen de caja de un turno |
| **Liquidación** | Proceso de cuadre diario |
| **Puntear** | Marcar un crédito como verificado |

---

*Siguiente: [02. Arquitectura del Sistema](02_arquitectura_sistema.md)*
