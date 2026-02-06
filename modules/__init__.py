#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de inicialización de los módulos de la aplicación.
"""

from .mixin_creditos import CreditosMixin
from .mixin_liquidacion import LiquidacionMixin
from .mixin_descuentos import DescuentosMixin
from .mixin_gastos import GastosMixin
from .mixin_dinero import DineroMixin
from .mixin_reportes import ReportesMixin
from .mixin_asignacion import AsignacionMixin

__all__ = [
    'CreditosMixin',
    'LiquidacionMixin', 
    'DescuentosMixin',
    'GastosMixin',
    'DineroMixin',
    'ReportesMixin',
    'AsignacionMixin'
]
