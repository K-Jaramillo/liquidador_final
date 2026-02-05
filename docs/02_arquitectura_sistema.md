# 🏗️ 2. ARQUITECTURA DEL SISTEMA

## 2.1 Visión General de la Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CAPA DE PRESENTACIÓN                           │
│                                  (Tkinter GUI)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │Asignar  │ │Liquida- │ │Descuen- │ │ Gastos  │ │ Conteo  │ │Créditos │   │
│  │Reps     │ │ción     │ │tos      │ │         │ │ Dinero  │ │Punteados│   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
│       └───────────┴───────────┴───────────┴───────────┴───────────┘        │
│                                     │                                       │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CAPA DE LÓGICA                                 │
│                           (LiquidadorRepartidores)                          │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                            DataStore                                  │   │
│  │   • Estado global de la aplicación                                   │   │
│  │   • Sincronización entre pestañas                                    │   │
│  │   • Caché de datos                                                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│       CAPA DE DATOS             │         │       CAPA DE DATOS             │
│         (Firebird)              │         │         (SQLite)                │
│                                 │         │                                 │
│  ┌───────────────────────────┐  │         │  ┌───────────────────────────┐  │
│  │      PDVDATA.FDB          │  │         │  │   liquidador_data.db      │  │
│  │  • Facturas (VENTATICKETS)│  │         │  │  • Asignaciones           │  │
│  │  • Corte (TURNOS)         │  │         │  │  • Gastos                 │  │
│  │  • Devoluciones           │  │         │  │  • Conteo Dinero          │  │
│  │  • Clientes               │  │         │  │  • Créditos Punteados     │  │
│  └───────────────────────────┘  │         │  │  • Historial              │  │
│                                 │         │  └───────────────────────────┘  │
│      SOLO LECTURA               │         │       LECTURA/ESCRITURA         │
└─────────────────────────────────┘         └─────────────────────────────────┘
```

---

## 2.2 Estructura de Archivos

```
liquidador_final/
│
├── 📄 main.py                      # Punto de entrada
│   └── Inicializa la aplicación y crea la ventana principal
│
├── 📄 liquidador_repartidores.py   # Clase principal (8000+ líneas)
│   ├── class DataStore             # Modelo de datos centralizado
│   └── class LiquidadorRepartidores # GUI y lógica de negocio
│
├── 📄 database_local.py            # Acceso a SQLite (3300+ líneas)
│   ├── init_database()             # Crea tablas
│   └── Funciones CRUD por entidad
│
├── 📄 corte_cajero.py              # Integración Firebird
│   ├── obtener_cancelaciones_por_usuario()
│   └── Consultas SQL a Eleventa
│
├── 📄 exportador_ventas.py         # Exportación de datos
├── 📄 utils_descuentos.py          # Utilidades descuentos
├── 📄 utils_repartidores.py        # Utilidades repartidores
│
├── 📁 core/                        # Módulos centrales
│   ├── __init__.py
│   ├── config.py                   # Configuración global
│   ├── datastore.py                # (Alternativo)
│   ├── database.py                 # Conexión Firebird directa
│   └── firebird_setup.py           # Setup Firebird Linux
│
├── 📁 gui/                         # Componentes GUI
│   ├── __init__.py
│   ├── styles.py                   # Estilos visuales
│   └── widgets.py                  # Widgets personalizados
│
├── 📁 firebird25_lib/              # Librerías Firebird (Linux)
│   ├── libfbclient.so.2
│   ├── libfbembed.so.2.5
│   └── ...
│
├── 📁 firebird25_bin/              # Binarios Firebird (Linux)
│   └── isql-fb
│
├── 📁 docs/                        # Documentación
│   └── *.md
│
├── 📄 PDVDATA.FDB                  # Base de datos Eleventa
├── 📄 liquidador_data.db           # Base de datos local
├── 📄 requirements.txt             # Dependencias Python
├── 📄 Iniciar_Liquidador.bat       # Launcher Windows
└── 📄 iniciar_linux.sh             # Launcher Linux
```

---

## 2.3 Clase DataStore (Modelo de Datos)

El `DataStore` es el corazón del sistema. Mantiene el estado global y sincroniza todas las pestañas.

### Diagrama de la Clase

```python
class DataStore:
    """Mantiene el estado global de la aplicación."""
    
    # ═══════════════════════════════════════════════════════════════
    # ATRIBUTOS PRINCIPALES
    # ═══════════════════════════════════════════════════════════════
    
    fecha: str                    # Fecha de trabajo (YYYY-MM-DD)
    ventas: list                  # Lista de facturas del día
    _repartidores: set            # Repartidores activos
    _listeners: list              # Callbacks de actualización
    
    devoluciones: list            # Devoluciones del día
    movimientos_entrada: list     # Ingresos extras
    movimientos_salida: list      # Salidas de efectivo
    gastos: list                  # Gastos registrados
    dinero: dict                  # Conteo de dinero por repartidor
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE SUSCRIPCIÓN (Patrón Observer)
    # ═══════════════════════════════════════════════════════════════
    
    def suscribir(callback)       # Registra listener
    def _notificar()              # Notifica cambios
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE VENTAS
    # ═══════════════════════════════════════════════════════════════
    
    def set_ventas(ventas)        # Carga facturas
    def get_ventas()              # Obtiene facturas
    def get_total_subtotal()      # Total vendido
    def get_total_canceladas()    # Total canceladas mismo día
    def get_total_credito()       # Total a crédito
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE REPARTIDORES
    # ═══════════════════════════════════════════════════════════════
    
    def get_repartidores()        # Lista de repartidores
    def set_repartidor_factura()  # Asigna repartidor
    def clear_repartidor_factura()# Quita asignación
    def clear_all_asignaciones()  # Limpia todas
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE GASTOS
    # ═══════════════════════════════════════════════════════════════
    
    def agregar_gasto()           # Nuevo gasto
    def eliminar_gasto()          # Borra gasto
    def get_gastos()              # Lista gastos
    def get_total_gastos()        # Suma gastos
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS FINANCIEROS
    # ═══════════════════════════════════════════════════════════════
    
    def agregar_pago_proveedor()  # Pago a proveedor
    def agregar_prestamo()        # Nuevo préstamo
    def agregar_pago_nomina()     # Pago nómina
    def agregar_pago_socios()     # Pago a socios
    def agregar_transferencia()   # Nueva transferencia
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE CONTEO
    # ═══════════════════════════════════════════════════════════════
    
    def set_dinero()              # Guarda conteo
    def get_dinero()              # Obtiene conteo
    def get_total_dinero()        # Suma total
```

### Flujo de Datos en DataStore

```
┌─────────────────────────────────────────────────────────────────┐
│                         DataStore                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────┐    set_ventas()     ┌─────────┐                  │
│   │Firebird │ ──────────────────► │ ventas  │                  │
│   └─────────┘                     │  list   │                  │
│                                   └────┬────┘                  │
│                                        │                        │
│                                   _notificar()                  │
│                                        │                        │
│              ┌─────────────────────────┼─────────────────────┐  │
│              ▼                         ▼                     ▼  │
│   ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐│
│   │Tab Asignación   │    │Tab Liquidación  │    │Tab Descuentos││
│   │callback()       │    │callback()       │    │callback()    ││
│   │  actualiza UI   │    │  actualiza UI   │    │  actualiza UI││
│   └─────────────────┘    └─────────────────┘    └──────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2.4 Clase LiquidadorRepartidores (GUI Principal)

Esta clase contiene toda la interfaz gráfica y la lógica de las pestañas.

### Estructura de Métodos

```python
class LiquidadorRepartidores:
    """Clase principal de la aplicación."""
    
    # ═══════════════════════════════════════════════════════════════
    # INICIALIZACIÓN
    # ═══════════════════════════════════════════════════════════════
    
    def __init__(root)            # Constructor
    def _crear_interfaz()         # Crea estructura principal
    def _crear_notebook()         # Crea contenedor de pestañas
    
    # ═══════════════════════════════════════════════════════════════
    # PESTAÑAS (TABS)
    # ═══════════════════════════════════════════════════════════════
    
    def _crear_tab_asignacion()        # Tab 1: Asignar Repartidores
    def _crear_tab_liquidacion()       # Tab 2: Liquidación
    def _crear_tab_descuentos()        # Tab 3: Descuentos por Factura
    def _crear_tab_gastos()            # Tab 4: Gastos Adicionales
    def _crear_tab_dinero()            # Tab 5: Conteo de Dinero
    def _crear_tab_anotaciones()       # Tab 6: Anotaciones
    def _crear_tab_creditos_punteados()# Tab 7: Créditos Punteados
    
    # ═══════════════════════════════════════════════════════════════
    # OPERACIONES DE DATOS
    # ═══════════════════════════════════════════════════════════════
    
    def _cargar_facturas()             # Carga de Firebird
    def _refrescar_liquidacion()       # Actualiza cálculos
    def _filtrar_facturas_asign()      # Filtra vista
    def _guardar_liquidacion()         # Persiste datos
    
    # ═══════════════════════════════════════════════════════════════
    # EVENTOS Y CALLBACKS
    # ═══════════════════════════════════════════════════════════════
    
    def _on_fecha_global_cambio()      # Cambio de fecha
    def _on_filtro_rep_global_cambio() # Filtro repartidor
    def _on_asignar_repartidor()       # Asignación
```

---

## 2.5 Flujo de Inicialización

```
main.py
   │
   ▼
┌─────────────────────────────────────┐
│ 1. Crear ventana Tk()               │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 2. LiquidadorRepartidores(root)     │
│    │                                │
│    ├── Crear DataStore()            │
│    ├── Configurar Firebird          │
│    ├── Inicializar SQLite           │
│    └── Crear interfaz               │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 3. _crear_interfaz()                │
│    │                                │
│    ├── Barra de título              │
│    ├── Barra de filtros             │
│    ├── Notebook (pestañas)          │
│    │   ├── Tab Asignación           │
│    │   ├── Tab Liquidación          │
│    │   ├── Tab Descuentos           │
│    │   ├── Tab Gastos               │
│    │   ├── Tab Conteo               │
│    │   ├── Tab Anotaciones          │
│    │   └── Tab Créditos             │
│    └── Barra de estado              │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 4. _cargar_facturas()               │
│    │                                │
│    ├── Conectar Firebird            │
│    ├── Ejecutar consulta            │
│    ├── Parsear resultados           │
│    ├── ds.set_ventas()              │
│    └── Actualizar UI                │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 5. root.mainloop()                  │
│    (Espera eventos de usuario)      │
└─────────────────────────────────────┘
```

---

## 2.6 Comunicación entre Componentes

### Patrón Observer (Suscripción)

```python
# DataStore notifica cambios a todos los suscriptores
class DataStore:
    def _notificar(self):
        for callback in self._listeners:
            callback()  # Cada pestaña actualiza su UI

# Cada tab se suscribe al inicializarse
class LiquidadorRepartidores:
    def _crear_tab_liquidacion(self):
        # ...crear widgets...
        self.ds.suscribir(self._refrescar_liquidacion)
```

### Diagrama de Comunicación

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Usuario    │     │  DataStore   │     │   SQLite     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  Click "Asignar"   │                    │
       │───────────────────►│                    │
       │                    │                    │
       │                    │  INSERT asignacion │
       │                    │───────────────────►│
       │                    │                    │
       │                    │◄───────────────────│
       │                    │      OK            │
       │                    │                    │
       │                    │  _notificar()      │
       │                    │────────┐           │
       │                    │        │           │
       │  UI Actualizada    │◄───────┘           │
       │◄───────────────────│                    │
       │                    │                    │
```

---

## 2.7 Gestión de Errores

### Niveles de Manejo

```python
# Nivel 1: Try/Except en operaciones críticas
def _cargar_facturas(self):
    try:
        # Operación de Firebird
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron cargar facturas: {e}")
        return

# Nivel 2: Validaciones antes de operaciones
def _on_asignar(self):
    if not self.folio_seleccionado:
        messagebox.showwarning("Atención", "Seleccione una factura primero")
        return
    
# Nivel 3: Fallbacks para funcionalidad degradada
def get_total_dinero(self):
    if USE_SQLITE:
        return db_local.obtener_total(...)
    return 0.0  # Fallback
```

---

## 2.8 Consideraciones de Rendimiento

### Optimizaciones Implementadas

1. **Caché de Datos**
   - Las facturas se cargan una vez y se mantienen en memoria
   - Los filtros operan sobre el caché, no consultan BD

2. **Lazy Loading**
   - Los datos de cada pestaña se cargan solo cuando es necesario
   - Las consultas pesadas se ejecutan en segundo plano

3. **Conexiones Eficientes**
   - SQLite usa una sola conexión por operación
   - Firebird se consulta mediante subproceso (isql)

4. **Actualizaciones Selectivas**
   - Solo se actualiza la UI que cambió
   - No se recarga toda la interfaz

---

## 2.9 Seguridad

### Medidas Implementadas

| Área | Medida |
|------|--------|
| **Base de Datos** | SQLite con acceso local únicamente |
| **Firebird** | Solo lectura, sin credenciales expuestas en código |
| **Archivos** | Permisos restrictivos en Linux |
| **Validación** | Sanitización de entradas numéricas |

### Credenciales Firebird
```python
# Las credenciales son las default de Firebird
# SYSDBA / masterkey
# Se asume instalación local segura
```

---

## 2.10 Extensibilidad

### Agregar Nueva Pestaña

```python
# 1. Crear el frame de la pestaña
self.tab_nueva = ttk.Frame(self.notebook)

# 2. Añadir al notebook
self.notebook.add(self.tab_nueva, text="  📌 Nueva Tab  ")

# 3. Crear el método de construcción
def _crear_tab_nueva(self):
    # Widgets de la pestaña
    pass

# 4. Suscribir para actualizaciones
self.ds.suscribir(self._refrescar_nueva)
```

### Agregar Nueva Tabla SQLite

```python
# En database_local.py, función init_database():

# Agregar creación de tabla
cursor.execute('''
    CREATE TABLE IF NOT EXISTS nueva_tabla (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATE NOT NULL,
        campo1 TEXT,
        campo2 REAL
    )
''')

# Agregar funciones CRUD
def agregar_registro_nueva_tabla(fecha, campo1, campo2):
    # ...

def obtener_registros_nueva_tabla(fecha):
    # ...
```

---

*Siguiente: [03. Módulos del Sistema](03_modulos_sistema.md)*
