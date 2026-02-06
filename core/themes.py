#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Definición de temas de colores para la aplicación.
"""

# ===========================================================================
#  TEMAS DE COLORES
# ===========================================================================
TEMAS = {
    'oscuro': {
        'nombre': '🌙 Oscuro',
        'PRIMARY': '#2196f3', 'PRIMARY_DARK': '#1976d2', 'PRIMARY_LIGHT': '#64b5f6',
        'SUCCESS': '#4caf50', 'SUCCESS_DARK': '#388e3c',
        'WARNING': '#ff9800', 'ERROR': '#f44336',
        'BG_DARK': '#1e1e1e', 'BG_DARKER': '#121212', 'BG_CARD': '#2d2d2d',
        'BG_HOVER': '#3d3d3d', 'BG_SELECTED': '#0d47a1',
        'TEXT_PRIMARY': '#ffffff', 'TEXT_SECONDARY': '#b0b0b0', 'TEXT_MUTED': '#757575',
        'BORDER_COLOR': '#404040',
        'TREE_ROW_PAR': '#2d2d2d', 'TREE_ROW_IMPAR': '#3d3d3d'
    },
    'claro': {
        'nombre': '☀️ Claro',
        'PRIMARY': '#1976d2', 'PRIMARY_DARK': '#0d47a1', 'PRIMARY_LIGHT': '#42a5f5',
        'SUCCESS': '#2e7d32', 'SUCCESS_DARK': '#1b5e20',
        'WARNING': '#f57c00', 'ERROR': '#c62828',
        'BG_DARK': '#f5f5f5', 'BG_DARKER': '#e0e0e0', 'BG_CARD': '#ffffff',
        'BG_HOVER': '#eeeeee', 'BG_SELECTED': '#bbdefb',
        'TEXT_PRIMARY': '#212121', 'TEXT_SECONDARY': '#757575', 'TEXT_MUTED': '#9e9e9e',
        'BORDER_COLOR': '#bdbdbd',
        'TREE_ROW_PAR': '#ffffff', 'TREE_ROW_IMPAR': '#f5f5f5'
    },
    'azul_noche': {
        'nombre': '🌌 Azul Noche',
        'PRIMARY': '#5c6bc0', 'PRIMARY_DARK': '#3949ab', 'PRIMARY_LIGHT': '#7986cb',
        'SUCCESS': '#26a69a', 'SUCCESS_DARK': '#00897b',
        'WARNING': '#ffa726', 'ERROR': '#ef5350',
        'BG_DARK': '#1a1a2e', 'BG_DARKER': '#16213e', 'BG_CARD': '#0f3460',
        'BG_HOVER': '#1f4287', 'BG_SELECTED': '#3949ab',
        'TEXT_PRIMARY': '#e8e8e8', 'TEXT_SECONDARY': '#a0a0c0', 'TEXT_MUTED': '#6a6a8a',
        'BORDER_COLOR': '#1f4287',
        'TREE_ROW_PAR': '#0f3460', 'TREE_ROW_IMPAR': '#16213e'
    },
    'verde_bosque': {
        'nombre': '🌲 Verde Bosque',
        'PRIMARY': '#66bb6a', 'PRIMARY_DARK': '#43a047', 'PRIMARY_LIGHT': '#81c784',
        'SUCCESS': '#26a69a', 'SUCCESS_DARK': '#00897b',
        'WARNING': '#ffca28', 'ERROR': '#ef5350',
        'BG_DARK': '#1b2a1b', 'BG_DARKER': '#0d1a0d', 'BG_CARD': '#2d3d2d',
        'BG_HOVER': '#3d4d3d', 'BG_SELECTED': '#2e7d32',
        'TEXT_PRIMARY': '#e0f2e9', 'TEXT_SECONDARY': '#a5d6a7', 'TEXT_MUTED': '#6b8e6b',
        'BORDER_COLOR': '#4a5d4a',
        'TREE_ROW_PAR': '#2d3d2d', 'TREE_ROW_IMPAR': '#253525'
    },
    'purpura': {
        'nombre': '💜 Púrpura',
        'PRIMARY': '#ab47bc', 'PRIMARY_DARK': '#8e24aa', 'PRIMARY_LIGHT': '#ce93d8',
        'SUCCESS': '#66bb6a', 'SUCCESS_DARK': '#43a047',
        'WARNING': '#ffa726', 'ERROR': '#ef5350',
        'BG_DARK': '#1a1625', 'BG_DARKER': '#120e1a', 'BG_CARD': '#2d2838',
        'BG_HOVER': '#3d3848', 'BG_SELECTED': '#7b1fa2',
        'TEXT_PRIMARY': '#f3e5f5', 'TEXT_SECONDARY': '#ce93d8', 'TEXT_MUTED': '#8e6a9e',
        'BORDER_COLOR': '#4a3d5c',
        'TREE_ROW_PAR': '#2d2838', 'TREE_ROW_IMPAR': '#231e2e'
    },
    'oceano': {
        'nombre': '🌊 Océano',
        'PRIMARY': '#26c6da', 'PRIMARY_DARK': '#00acc1', 'PRIMARY_LIGHT': '#4dd0e1',
        'SUCCESS': '#66bb6a', 'SUCCESS_DARK': '#43a047',
        'WARNING': '#ffb74d', 'ERROR': '#e57373',
        'BG_DARK': '#0a1929', 'BG_DARKER': '#051321', 'BG_CARD': '#132f4c',
        'BG_HOVER': '#1a3a5c', 'BG_SELECTED': '#0288d1',
        'TEXT_PRIMARY': '#e3f2fd', 'TEXT_SECONDARY': '#90caf9', 'TEXT_MUTED': '#5090b0',
        'BORDER_COLOR': '#1e4976',
        'TREE_ROW_PAR': '#132f4c', 'TREE_ROW_IMPAR': '#0d2137'
    },
    'naranja_atardecer': {
        'nombre': '🌅 Atardecer',
        'PRIMARY': '#ff7043', 'PRIMARY_DARK': '#f4511e', 'PRIMARY_LIGHT': '#ff8a65',
        'SUCCESS': '#66bb6a', 'SUCCESS_DARK': '#43a047',
        'WARNING': '#ffca28', 'ERROR': '#e53935',
        'BG_DARK': '#2a1a1a', 'BG_DARKER': '#1a0d0d', 'BG_CARD': '#3d2a2a',
        'BG_HOVER': '#4d3a3a', 'BG_SELECTED': '#bf360c',
        'TEXT_PRIMARY': '#fff3e0', 'TEXT_SECONDARY': '#ffab91', 'TEXT_MUTED': '#a07060',
        'BORDER_COLOR': '#5d4037',
        'TREE_ROW_PAR': '#3d2a2a', 'TREE_ROW_IMPAR': '#332222'
    },
    'rosa': {
        'nombre': '🌸 Rosa',
        'PRIMARY': '#ec407a', 'PRIMARY_DARK': '#d81b60', 'PRIMARY_LIGHT': '#f48fb1',
        'SUCCESS': '#66bb6a', 'SUCCESS_DARK': '#43a047',
        'WARNING': '#ffd54f', 'ERROR': '#e53935',
        'BG_DARK': '#2a1a22', 'BG_DARKER': '#1a0d14', 'BG_CARD': '#3d2a34',
        'BG_HOVER': '#4d3a44', 'BG_SELECTED': '#ad1457',
        'TEXT_PRIMARY': '#fce4ec', 'TEXT_SECONDARY': '#f48fb1', 'TEXT_MUTED': '#a06080',
        'BORDER_COLOR': '#5d3a47',
        'TREE_ROW_PAR': '#3d2a34', 'TREE_ROW_IMPAR': '#33222a'
    }
}


def get_tema(nombre: str) -> dict:
    """Obtiene un tema por nombre. Si no existe, retorna el oscuro."""
    return TEMAS.get(nombre, TEMAS['oscuro'])


def get_nombres_temas() -> dict:
    """Retorna un diccionario {nombre_visible: id_tema}."""
    return {v['nombre']: k for k, v in TEMAS.items()}


def get_lista_temas() -> list:
    """Retorna lista de nombres visibles de temas."""
    return list(get_nombres_temas().keys())
