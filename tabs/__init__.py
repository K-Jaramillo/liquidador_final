#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulos de pestañas para el Liquidador de Repartidores.
Cada pestaña está en su propio archivo para mejor organización.
"""

# Importar solo los módulos que existen
try:
    from .tab_base import TabBase
except ImportError:
    TabBase = None

try:
    from .tab_asignacion import TabAsignacion
except ImportError:
    TabAsignacion = None

try:
    from .tab_liquidacion import TabLiquidacion
except ImportError:
    TabLiquidacion = None

try:
    from .tab_descuentos import TabDescuentos
except ImportError:
    TabDescuentos = None

try:
    from .tab_gastos import TabGastos
except ImportError:
    TabGastos = None

try:
    from .tab_conteo_dinero import TabConteoDinero
except ImportError:
    TabConteoDinero = None

try:
    from .tab_anotaciones import TabAnotaciones
except ImportError:
    TabAnotaciones = None

try:
    from .tab_ordenes import TabOrdenes
except ImportError:
    TabOrdenes = None

# Exportar solo lo que se logró importar
__all__ = [name for name in [
    'TabBase',
    'TabAsignacion',
    'TabLiquidacion',
    'TabDescuentos',
    'TabGastos',
    'TabConteoDinero',
    'TabAnotaciones',
    'TabOrdenes'
] if globals().get(name) is not None]
