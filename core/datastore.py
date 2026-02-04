# -*- coding: utf-8 -*-
"""
DataStore - Modelo de datos centralizado (única fuente de verdad)
"""
from datetime import datetime
from typing import List, Dict, Callable, Any, Optional


class DataStore:
    """
    Mantiene el estado global de la aplicación.
    Todas las pestañas leen/escriben aquí → sincronización automática.
    """

    def __init__(self):
        self.fecha: str = datetime.now().strftime('%Y-%m-%d')
        # Lista de dicts: {id, folio, nombre, subtotal, repartidor, cancelada, total_credito, es_credito}
        self.ventas: List[Dict[str, Any]] = []
        # Conjunto rápido de repartidores conocidos
        self._repartidores: set = set()
        # Callbacks registrados por las pestañas
        self._listeners: List[Callable] = []
        # Datos adicionales financieros
        self.devoluciones: List[Dict] = []      # Lista de devoluciones del día
        self.movimientos_entrada: List[Dict] = []  # Ingresos extras
        self.movimientos_salida: List[Dict] = []   # Salidas
        # Gastos adicionales
        self.gastos: List[Dict] = []
        # Conteo de dinero por repartidor
        self.dinero: Dict[str, Dict[int, int]] = {}
        
        # Funciones de persistencia (se inyectan desde utils)
        self._asignar_repartidor_fn = None
        self._cargar_asignaciones_fn = None
        self._guardar_asignaciones_fn = None
        self._limpiar_asignaciones_dia_fn = None
        self._cargar_descuentos_fn = None

    def set_persistence_functions(self, asignar, cargar, guardar, limpiar, cargar_desc):
        """Inyecta las funciones de persistencia."""
        self._asignar_repartidor_fn = asignar
        self._cargar_asignaciones_fn = cargar
        self._guardar_asignaciones_fn = guardar
        self._limpiar_asignaciones_dia_fn = limpiar
        self._cargar_descuentos_fn = cargar_desc

    # --- suscripción de eventos ---
    def suscribir(self, callback: Callable) -> None:
        """Registra un callback que se invoca al cambiar datos."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def desuscribir(self, callback: Callable) -> None:
        """Elimina un callback de la lista de listeners."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notificar(self) -> None:
        """Notifica a todos los listeners de un cambio."""
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                pass

    # --- ventas ---
    def set_ventas(self, ventas: List[Dict]) -> None:
        self.ventas = ventas
        self._repartidores = {v['repartidor'] for v in ventas if v.get('repartidor')}
        self._notificar()

    def get_ventas(self) -> List[Dict]:
        return self.ventas

    def get_total_subtotal(self) -> float:
        return sum(v['subtotal'] for v in self.ventas)

    def get_total_canceladas(self) -> float:
        """Retorna el total de facturas canceladas del mismo día."""
        return sum(v.get('total_original', 0) for v in self.ventas 
                   if v.get('cancelada', False) and not v.get('cancelada_otro_dia', False))

    def get_total_canceladas_otro_dia(self) -> float:
        """Retorna el total de facturas canceladas que son de otro día."""
        return sum(v.get('total_original', 0) for v in self.ventas 
                   if v.get('cancelada', False) and v.get('cancelada_otro_dia', False))

    def get_ventas_canceladas_otro_dia(self) -> List[Dict]:
        """Retorna lista de ventas canceladas de otro día."""
        return [v for v in self.ventas if v.get('cancelada', False) and v.get('cancelada_otro_dia', False)]

    def get_total_credito(self) -> float:
        """Retorna el total de facturas a crédito."""
        return sum(v.get('total_credito', 0) for v in self.ventas if v.get('es_credito', False))

    def get_ventas_credito(self) -> List[Dict]:
        """Retorna lista de ventas a crédito."""
        return [v for v in self.ventas if v.get('es_credito', False)]

    def get_ventas_canceladas(self) -> List[Dict]:
        """Retorna lista de ventas canceladas del mismo día."""
        return [v for v in self.ventas if v.get('cancelada', False) and not v.get('cancelada_otro_dia', False)]

    # --- devoluciones ---
    def set_devoluciones(self, devoluciones: List[Dict]) -> None:
        self.devoluciones = devoluciones
        self._notificar()

    def get_total_devoluciones(self) -> float:
        return sum(d.get('monto', 0) for d in self.devoluciones)

    # --- movimientos (ingresos/salidas) ---
    def set_movimientos(self, entradas: List[Dict], salidas: List[Dict]) -> None:
        self.movimientos_entrada = entradas
        self.movimientos_salida = salidas
        self._notificar()

    def get_total_ingresos_extras(self) -> float:
        return sum(m.get('monto', 0) for m in self.movimientos_entrada)

    def get_total_salidas(self) -> float:
        return sum(m.get('monto', 0) for m in self.movimientos_salida)

    # --- repartidores ---
    def get_repartidores(self) -> List[str]:
        return sorted(self._repartidores)

    def set_repartidor_factura(self, folio: int, repartidor: str) -> None:
        """Actualiza el repartidor de una factura y persiste."""
        for v in self.ventas:
            if v['folio'] == folio:
                v['repartidor'] = repartidor
                break
        if repartidor:
            self._repartidores.add(repartidor)
            if self._asignar_repartidor_fn:
                self._asignar_repartidor_fn(folio, self.fecha, repartidor)
        self._notificar()

    def clear_repartidor_factura(self, folio: int) -> None:
        """Limpia el repartidor de una factura."""
        for v in self.ventas:
            if v['folio'] == folio:
                v['repartidor'] = ''
                break
        # Eliminar de persistencia
        if self._cargar_asignaciones_fn and self._guardar_asignaciones_fn:
            asignaciones = self._cargar_asignaciones_fn()
            key = f"{self.fecha}_{folio}"
            if key in asignaciones:
                del asignaciones[key]
                self._guardar_asignaciones_fn(asignaciones)
        self._repartidores = {v['repartidor'] for v in self.ventas if v.get('repartidor')}
        self._notificar()

    def clear_all_asignaciones(self) -> None:
        """Limpia todas las asignaciones del día."""
        for v in self.ventas:
            v['repartidor'] = ''
        self._repartidores.clear()
        if self._limpiar_asignaciones_dia_fn:
            self._limpiar_asignaciones_dia_fn(self.fecha)
        self._notificar()

    # --- gastos adicionales ---
    def agregar_gasto(self, repartidor: str, concepto: str, monto: float) -> None:
        self.gastos.append({
            'repartidor': repartidor,
            'concepto': concepto,
            'monto': monto
        })
        self._notificar()

    def eliminar_gasto(self, index: int) -> None:
        if 0 <= index < len(self.gastos):
            del self.gastos[index]
            self._notificar()

    def get_gastos(self, repartidor: str = '') -> List[Dict]:
        if not repartidor:
            return list(self.gastos)
        return [g for g in self.gastos if g['repartidor'] == repartidor]

    def get_total_gastos(self, repartidor: str = '') -> float:
        return sum(g['monto'] for g in self.get_gastos(repartidor))

    # --- conteo de dinero ---
    def set_dinero(self, repartidor: str, conteo: Dict[int, int]) -> None:
        """Guarda el conteo de denominaciones para un repartidor."""
        self.dinero[repartidor] = dict(conteo)

    def get_dinero(self, repartidor: str) -> Dict[int, int]:
        """Retorna {valor_int: cantidad} para un repartidor."""
        return dict(self.dinero.get(repartidor, {}))

    def get_total_dinero(self, repartidor: str = '') -> float:
        """Suma total de dinero."""
        reps = [repartidor] if repartidor else list(self.dinero.keys())
        total = 0.0
        for r in reps:
            for valor, cant in self.dinero.get(r, {}).items():
                total += valor * cant
        return total

    # --- descuentos ---
    def get_total_descuentos(self, repartidor: str = '') -> float:
        """Obtiene el total de descuentos del día."""
        if not self._cargar_descuentos_fn:
            return 0.0
        total = 0.0
        desc_todos = self._cargar_descuentos_fn()
        for folio_key, datos in desc_todos.items():
            for desc in datos.get("descuentos", []):
                if desc.get("fecha", "").startswith(self.fecha):
                    if not repartidor or desc.get("repartidor") == repartidor:
                        total += desc.get("monto", 0)
        return total
    
    # --- estadísticas ---
    def get_estadisticas(self) -> Dict[str, Any]:
        """Retorna un diccionario con estadísticas generales."""
        total_ventas = len(self.ventas)
        asignadas = sum(1 for v in self.ventas if v.get('repartidor'))
        canceladas = sum(1 for v in self.ventas if v.get('cancelada'))
        credito = sum(1 for v in self.ventas if v.get('es_credito'))
        
        return {
            'total_ventas': total_ventas,
            'asignadas': asignadas,
            'sin_asignar': total_ventas - asignadas,
            'porcentaje_asignacion': (asignadas / total_ventas * 100) if total_ventas > 0 else 0,
            'canceladas': canceladas,
            'credito': credito,
            'repartidores_activos': len(self._repartidores),
            'total_monto': self.get_total_subtotal(),
            'total_canceladas_monto': self.get_total_canceladas(),
            'total_credito_monto': self.get_total_credito(),
        }
