# Liquidador de Repartidores

Sistema de liquidación y administración de repartidores con soporte para bases de datos Firebird.

## Requisitos

### Windows
- Python 3.10 o superior
- Firebird 2.5 o superior instalado

### Linux
- Python 3.10 o superior
- Las bibliotecas de Firebird 2.5 están incluidas en el proyecto (no requiere instalación adicional)

## Instalación

### Windows

1. Instalar Python desde [python.org](https://python.org)
2. Instalar Firebird 2.5 desde [firebirdsql.org](https://firebirdsql.org)
3. Ejecutar:
```batch
pip install -r requirements.txt
```

### Linux (Ubuntu/Debian)

1. Clonar el repositorio:
```bash
git clone https://github.com/K-Jaramillo/liquidador_final.git
cd liquidador_final
```

2. Crear y activar entorno virtual:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instalar dependencias de Python:
```bash
pip install -r requirements.txt
```

4. Ejecutar el diagnóstico para verificar que todo esté correcto:
```bash
python3 diagnostico_firebird_linux.py
```

## Ejecutar la aplicación

### Windows
Ejecutar el archivo `Iniciar_Liquidador.bat` o:
```batch
python main.py
```

### Linux
Usar el script de inicio (recomendado):
```bash
./iniciar_linux.sh
```

O ejecutar directamente:
```bash
source .venv/bin/activate
python3 main.py
```

## Estructura del proyecto

```
liquidador_final/
├── core/
│   ├── config.py           # Configuración general
│   └── firebird_setup.py   # Configuración multiplataforma de Firebird
├── gui/                    # Módulos de interfaz gráfica
├── tabs/                   # Pestañas de la aplicación
├── firebird25_lib/         # Bibliotecas de Firebird 2.5 para Linux (bundled)
├── firebird25_bin/         # Binarios de Firebird 2.5 para Linux (bundled)
├── PDVDATA.FDB             # Base de datos Firebird
├── main.py                 # Punto de entrada
├── liquidador_repartidores.py  # Aplicación principal
├── iniciar_linux.sh        # Script de inicio para Linux
└── diagnostico_firebird_linux.py  # Diagnóstico de Firebird para Linux
```

## Compatibilidad de Firebird

Este proyecto está diseñado para trabajar con bases de datos Firebird 2.5 (ODS 11.0).

### En Linux
- El proyecto incluye bibliotecas de Firebird 2.5 embebidas (`firebird25_lib/`)
- No es necesario instalar Firebird del sistema
- La conexión usa la biblioteca `libfbembed.so.2.5.9` para modo embebido

### En Windows
- Se requiere Firebird 2.5 o compatible instalado en el sistema
- También puede usar `fbclient.dll` bundled si está disponible

## Diagnóstico

### Linux
Para verificar que Firebird está configurado correctamente:
```bash
python3 diagnostico_firebird_linux.py
```

Esto verificará:
- Bibliotecas de Firebird 2.5 bundled
- Binario isql disponible
- Base de datos PDVDATA.FDB presente
- Conexión con fdb y biblioteca embebida
- Funcionalidad de isql

## Dependencias

- `fdb>=1.7.1` - Driver de Firebird para Python
- `pandas>=1.5.3` - Procesamiento de datos
- `numpy>=1.24` - Operaciones numéricas
- `openpyxl>=3.1.2` - Exportación a Excel
- `tkcalendar>=1.6.1` - Selector de fechas

## Notas técnicas

### ODS (On-Disk Structure)
- La base de datos `PDVDATA.FDB` usa ODS 11.0 (Firebird 2.5)
- Las versiones más nuevas de Firebird (3.0+) usan ODS 12.x
- Por compatibilidad, en Linux se usan bibliotecas de Firebird 2.5

### Modo embebido
En Linux, el proyecto usa el modo embebido de Firebird, que permite:
- No requerir un servidor Firebird corriendo
- Acceso directo al archivo de base de datos
- Menor complejidad de configuración

## Licencia

Este proyecto es de código abierto.
