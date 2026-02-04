#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTILIDADES PARA DESCUENTOS
Funciones auxiliares para manejo de descuentos en la BD (archivo de descuentos).
"""

import os
import json
from datetime import datetime

# Archivo JSON local para almacenar descuentos
DESCUENTOS_FILE = os.path.join(os.path.dirname(__file__), 'descuentos.json')

def _cargar_archivo():
    """Carga descuentos del archivo JSON."""
    if os.path.exists(DESCUENTOS_FILE):
        try:
            with open(DESCUENTOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _guardar_archivo(data):
    """Guarda descuentos al archivo JSON."""
    try:
        with open(DESCUENTOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando descuentos: {e}")

def cargar_descuentos():
    """Carga todos los descuentos desde el archivo."""
    return _cargar_archivo()

def obtener_descuentos_factura(folio):
    """
    Obtiene descuentos asociados a una factura específica.
    
    Args:
        folio: Número de folio
    
    Returns:
        Lista de descuentos de la factura
    """
    data = _cargar_archivo()
    folio_key = str(folio)
    return data.get(folio_key, {}).get('descuentos', [])

def obtener_descuentos_repartidor(repartidor, fecha_inicio=None):
    """
    Obtiene descuentos asociados a un repartidor.
    
    Args:
        repartidor: Nombre del repartidor
        fecha_inicio: Fecha de inicio (opcional, filtro)
    
    Returns:
        Lista de descuentos
    """
    data = _cargar_archivo()
    descuentos = []
    
    for folio_key, folio_data in data.items():
        if folio_data.get('repartidor') == repartidor:
            for desc in folio_data.get('descuentos', []):
                if fecha_inicio is None or desc.get('fecha', '').startswith(fecha_inicio):
                    descuentos.append({
                        'folio': int(folio_key),
                        'tipo': desc.get('tipo'),
                        'monto': desc.get('monto', 0),
                        'observacion': desc.get('observacion', ''),
                        'fecha': desc.get('fecha', '')
                    })
    
    return descuentos

def agregar_descuento(folio, tipo, monto, observacion, repartidor):
    """
    Agrega un descuento a una factura.
    
    Args:
        folio: Número de folio
        tipo: Tipo de descuento (credito, devolucion, ajuste)
        monto: Monto del descuento
        observacion: Observación
        repartidor: Repartidor asociado
    """
    data = _cargar_archivo()
    folio_key = str(folio)
    
    if folio_key not in data:
        data[folio_key] = {
            'repartidor': repartidor,
            'descuentos': []
        }
    
    data[folio_key]['descuentos'].append({
        'tipo': tipo,
        'monto': float(monto),
        'observacion': observacion,
        'repartidor': repartidor,
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    _guardar_archivo(data)

def obtener_total_descuentos_factura(folio):
    """
    Calcula el total de descuentos de una factura.
    
    Args:
        folio: Número de folio
    
    Returns:
        Total en moneda (float)
    """
    descuentos = obtener_descuentos_factura(folio)
    return sum(d.get('monto', 0) for d in descuentos)

def limpiar_descuentos_factura(folio):
    """Elimina todos los descuentos de una factura."""
    data = _cargar_archivo()
    folio_key = str(folio)
    if folio_key in data:
        del data[folio_key]
        _guardar_archivo(data)
