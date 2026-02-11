"""
Funciones para calcular devoluciones reales sin duplicidades.

El problema identificado:
- Cuando se hace una devolución parcial y luego se cancela la factura,
  CORTE_MOVIMIENTOS registra el mismo artículo 2 veces
- TURNOS suma de CORTE_MOVIMIENTOS, por lo que también tiene el valor inflado
- La tabla DEVOLUCIONES solo tiene el valor correcto (sin duplicar)

Esta función calcula el valor REAL descontando duplicados.
"""
import fdb
from typing import Dict, Tuple, List
from decimal import Decimal

DB_PATH = r"D:\BDEV\PDVDATA.FDB"


def conectar_db():
    """Conecta a la base de datos Firebird."""
    return fdb.connect(
        dsn=DB_PATH,
        user='SYSDBA',
        password='masterkey',
        charset='WIN1252'
    )


def obtener_devoluciones_sin_duplicados(turno_id: int) -> Dict:
    """
    Obtiene el total de devoluciones de un turno SIN contar duplicados.
    
    La duplicidad ocurre cuando:
    1. Se hace una devolución parcial de un artículo
    2. Después se cancela la factura completa
    3. Eleventa registra el mismo artículo 2 veces en CORTE_MOVIMIENTOS
    
    Args:
        turno_id: ID del turno a analizar
        
    Returns:
        Dict con:
        - total_con_duplicados: Suma bruta de CORTE_MOVIMIENTOS
        - total_sin_duplicados: Suma descontando duplicados
        - duplicados_descontados: Monto de duplicados encontrados
        - detalle_duplicados: Lista de artículos duplicados
    """
    conn = conectar_db()
    cur = conn.cursor()
    
    # 1. Obtener todos los movimientos de devolución del turno
    cur.execute('''
        SELECT DESCRIPCION, MONTO, COUNT(*) AS VECES
        FROM CORTE_MOVIMIENTOS
        WHERE ID_TURNO = ?
          AND TIPO CONTAINING 'Devol'
        GROUP BY DESCRIPCION, MONTO
    ''', (turno_id,))
    
    total_con_duplicados = Decimal('0')
    total_sin_duplicados = Decimal('0')
    duplicados_descontados = Decimal('0')
    detalle_duplicados = []
    
    for row in cur.fetchall():
        descripcion = row[0]
        monto = Decimal(str(row[1]))
        veces = row[2]
        
        # Sumar todas las ocurrencias (con duplicados)
        total_con_duplicados += monto * veces
        
        # Sumar solo una vez (sin duplicados)
        total_sin_duplicados += monto
        
        # Si aparece más de una vez, es duplicado
        if veces > 1:
            monto_duplicado = monto * (veces - 1)
            duplicados_descontados += monto_duplicado
            detalle_duplicados.append({
                'descripcion': descripcion,
                'monto_unitario': float(monto),
                'veces': veces,
                'monto_duplicado': float(monto_duplicado)
            })
    
    conn.close()
    
    return {
        'turno_id': turno_id,
        'total_con_duplicados': float(total_con_duplicados),
        'total_sin_duplicados': float(total_sin_duplicados),
        'duplicados_descontados': float(duplicados_descontados),
        'detalle_duplicados': detalle_duplicados
    }


def obtener_devoluciones_fecha_sin_duplicados(fecha: str) -> Dict:
    """
    Obtiene el total de devoluciones de una fecha SIN contar duplicados.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        Dict con totales y detalles por turno
    """
    conn = conectar_db()
    cur = conn.cursor()
    
    # Obtener turnos del día
    cur.execute('''
        SELECT ID FROM TURNOS 
        WHERE CAST(INICIO_EN AS DATE) = ?
        ORDER BY ID
    ''', (fecha,))
    
    turnos = [r[0] for r in cur.fetchall()]
    conn.close()
    
    resultado = {
        'fecha': fecha,
        'turnos': [],
        'total_con_duplicados': 0.0,
        'total_sin_duplicados': 0.0,
        'total_duplicados_descontados': 0.0
    }
    
    for turno_id in turnos:
        datos_turno = obtener_devoluciones_sin_duplicados(turno_id)
        resultado['turnos'].append(datos_turno)
        resultado['total_con_duplicados'] += datos_turno['total_con_duplicados']
        resultado['total_sin_duplicados'] += datos_turno['total_sin_duplicados']
        resultado['total_duplicados_descontados'] += datos_turno['duplicados_descontados']
    
    return resultado


def comparar_fuentes_devoluciones(turno_id: int) -> Dict:
    """
    Compara las 3 fuentes de devoluciones para un turno:
    1. TURNOS.DEVOLUCIONES_VENTAS_EFECTIVO (lo que muestra Eleventa)
    2. CORTE_MOVIMIENTOS sin duplicados (valor real calculado)
    3. Tabla DEVOLUCIONES (registro formal)
    
    Args:
        turno_id: ID del turno
        
    Returns:
        Dict con comparación de las 3 fuentes
    """
    conn = conectar_db()
    cur = conn.cursor()
    
    # 1. Valor en TURNOS
    cur.execute('SELECT DEVOLUCIONES_VENTAS_EFECTIVO FROM TURNOS WHERE ID = ?', (turno_id,))
    row = cur.fetchone()
    valor_turnos = float(row[0]) if row else 0.0
    
    # 2. Valor en tabla DEVOLUCIONES
    cur.execute('''
        SELECT SUM(D.TOTAL_DEVUELTO) 
        FROM DEVOLUCIONES D
        WHERE D.TURNO_ID = ?
    ''', (turno_id,))
    row = cur.fetchone()
    valor_tabla_devoluciones = float(row[0]) if row and row[0] else 0.0
    
    conn.close()
    
    # 3. Valor sin duplicados
    datos_sin_dup = obtener_devoluciones_sin_duplicados(turno_id)
    
    return {
        'turno_id': turno_id,
        'turnos_devoluciones_efectivo': valor_turnos,
        'corte_movimientos_con_duplicados': datos_sin_dup['total_con_duplicados'],
        'corte_movimientos_sin_duplicados': datos_sin_dup['total_sin_duplicados'],
        'tabla_devoluciones': valor_tabla_devoluciones,
        'duplicados_descontados': datos_sin_dup['duplicados_descontados'],
        'detalle_duplicados': datos_sin_dup['detalle_duplicados'],
        # Diferencias
        'diff_turnos_vs_sin_dup': valor_turnos - datos_sin_dup['total_sin_duplicados'],
        'diff_turnos_vs_tabla_dev': valor_turnos - valor_tabla_devoluciones,
        'diff_sin_dup_vs_tabla_dev': datos_sin_dup['total_sin_duplicados'] - valor_tabla_devoluciones
    }


def validar_calculo_devoluciones(fecha: str) -> None:
    """
    Valida y muestra el cálculo de devoluciones para una fecha.
    Imprime comparación detallada de las fuentes.
    """
    conn = conectar_db()
    cur = conn.cursor()
    
    # Obtener turnos del día
    cur.execute('''
        SELECT ID FROM TURNOS 
        WHERE CAST(INICIO_EN AS DATE) = ?
        ORDER BY ID
    ''', (fecha,))
    turnos = [r[0] for r in cur.fetchall()]
    conn.close()
    
    print('=' * 80)
    print(f'VALIDACIÓN DE DEVOLUCIONES - {fecha}')
    print('=' * 80)
    
    totales = {
        'turnos': 0.0,
        'corte_con_dup': 0.0,
        'corte_sin_dup': 0.0,
        'tabla_dev': 0.0,
        'duplicados': 0.0
    }
    
    for turno_id in turnos:
        comp = comparar_fuentes_devoluciones(turno_id)
        
        print(f'\nTURNO {turno_id}:')
        print('-' * 60)
        print(f'  TURNOS.DEV_VENTAS_EFECTIVO:     ${comp["turnos_devoluciones_efectivo"]:>12,.2f}')
        print(f'  CORTE_MOV (con duplicados):     ${comp["corte_movimientos_con_duplicados"]:>12,.2f}')
        print(f'  CORTE_MOV (SIN duplicados):     ${comp["corte_movimientos_sin_duplicados"]:>12,.2f}')
        print(f'  Tabla DEVOLUCIONES:             ${comp["tabla_devoluciones"]:>12,.2f}')
        print(f'  Duplicados descontados:         ${comp["duplicados_descontados"]:>12,.2f}')
        
        if comp['detalle_duplicados']:
            print(f'\n  Duplicados encontrados:')
            for dup in comp['detalle_duplicados']:
                print(f'    - {dup["descripcion"][:50]}...')
                print(f'      Monto=${dup["monto_unitario"]:,.2f} x {dup["veces"]} veces = ${dup["monto_duplicado"]:,.2f} duplicado')
        
        # Acumular totales
        totales['turnos'] += comp['turnos_devoluciones_efectivo']
        totales['corte_con_dup'] += comp['corte_movimientos_con_duplicados']
        totales['corte_sin_dup'] += comp['corte_movimientos_sin_duplicados']
        totales['tabla_dev'] += comp['tabla_devoluciones']
        totales['duplicados'] += comp['duplicados_descontados']
    
    print('\n' + '=' * 80)
    print('RESUMEN TOTALES:')
    print('=' * 80)
    print(f'  TURNOS.DEV_VENTAS_EFECTIVO:     ${totales["turnos"]:>12,.2f}')
    print(f'  CORTE_MOV (con duplicados):     ${totales["corte_con_dup"]:>12,.2f}')
    print(f'  CORTE_MOV (SIN duplicados):     ${totales["corte_sin_dup"]:>12,.2f}  <-- VALOR REAL')
    print(f'  Tabla DEVOLUCIONES:             ${totales["tabla_dev"]:>12,.2f}')
    print(f'  Total duplicados:               ${totales["duplicados"]:>12,.2f}')
    
    print('\n' + '=' * 80)
    print('VALIDACIÓN:')
    print('=' * 80)
    diff_sin_dup_tabla = totales['corte_sin_dup'] - totales['tabla_dev']
    diff_turnos_tabla = totales['turnos'] - totales['tabla_dev']
    
    print(f'  CORTE SIN DUP - Tabla DEV =     ${diff_sin_dup_tabla:>12,.2f}')
    print(f'  TURNOS - Tabla DEV =            ${diff_turnos_tabla:>12,.2f}')
    
    if abs(diff_sin_dup_tabla) < 0.01:
        print('\n  ✅ CORTE_MOV sin duplicados COINCIDE con tabla DEVOLUCIONES')
        print(f'     VALOR REAL de devoluciones: ${totales["tabla_dev"]:,.2f}')
        if totales['duplicados'] > 0:
            print(f'     Duplicados detectados: ${totales["duplicados"]:,.2f}')
    else:
        # Hay diferencia - probablemente son devoluciones sin cancelación formal
        print(f'\n  ⚠️  Diferencia de ${diff_sin_dup_tabla:,.2f} entre CORTE y DEVOLUCIONES')
        print('     Esto indica devoluciones parciales sin cancelación formal')
        print(f'     VALOR REAL (usando CORTE sin dup): ${totales["corte_sin_dup"]:,.2f}')


def obtener_valor_real_devoluciones(turno_id: int) -> float:
    """
    Obtiene el VALOR REAL de devoluciones para un turno.
    
    Usa CORTE_MOVIMIENTOS sin duplicados ya que es la fuente más completa,
    incluye devoluciones parciales que no se registran en tabla DEVOLUCIONES.
    
    Args:
        turno_id: ID del turno
        
    Returns:
        Valor real de devoluciones en efectivo
    """
    datos = obtener_devoluciones_sin_duplicados(turno_id)
    return datos['total_sin_duplicados']


def obtener_valor_real_devoluciones_fecha(fecha: str) -> Dict:
    """
    Obtiene el VALOR REAL de devoluciones para una fecha completa.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        Dict con valor real y detalles
    """
    conn = conectar_db()
    cur = conn.cursor()
    
    # Turnos del día
    cur.execute('''
        SELECT ID FROM TURNOS 
        WHERE CAST(INICIO_EN AS DATE) = ?
        ORDER BY ID
    ''', (fecha,))
    turnos = [r[0] for r in cur.fetchall()]
    conn.close()
    
    total_real = 0.0
    total_duplicados = 0.0
    detalles = []
    
    for turno_id in turnos:
        datos = obtener_devoluciones_sin_duplicados(turno_id)
        valor = datos['total_sin_duplicados']
        total_real += valor
        total_duplicados += datos['duplicados_descontados']
        detalles.append({
            'turno_id': turno_id, 
            'valor_real': valor,
            'duplicados': datos['duplicados_descontados']
        })
    
    return {
        'fecha': fecha,
        'valor_real_total': total_real,
        'duplicados_total': total_duplicados,
        'turnos': detalles
    }


def detectar_bugs_devoluciones(fecha: str) -> Dict:
    """
    Detecta bugs de duplicación de Eleventa para una fecha.
    
    Tipos de bugs detectados:
    1. TURNOS > CORTE_MOV: Eleventa suma devoluciones de más en TURNOS
    2. CORTE_MOV duplicados: Artículos aparecen múltiples veces en CORTE_MOVIMIENTOS
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        Dict con bugs detectados:
        {
            'fecha': str,
            'tiene_bugs': bool,
            'total_bugs': float,  # Monto total de bugs
            'bugs': [
                {
                    'turno_id': int,
                    'tipo': str,  # 'turnos_mayor_corte' o 'duplicado_corte'
                    'descripcion': str,
                    'monto_bug': float,
                    'detalle': list  # Artículos/descripciones involucradas
                }
            ]
        }
    """
    conn = conectar_db()
    cur = conn.cursor()
    
    # Obtener turnos del día
    cur.execute('''
        SELECT ID FROM TURNOS 
        WHERE CAST(INICIO_EN AS DATE) = ?
        ORDER BY ID
    ''', (fecha,))
    turnos = [r[0] for r in cur.fetchall()]
    
    resultado = {
        'fecha': fecha,
        'tiene_bugs': False,
        'total_bugs': 0.0,
        'bugs': []
    }
    
    for turno_id in turnos:
        # 1. Obtener valor en TURNOS
        cur.execute('SELECT DEVOLUCIONES_VENTAS_EFECTIVO FROM TURNOS WHERE ID = ?', (turno_id,))
        row = cur.fetchone()
        valor_turnos = float(row[0]) if row and row[0] else 0.0
        
        # 2. Obtener suma bruta de CORTE_MOVIMIENTOS
        cur.execute('''SELECT SUM(MONTO) FROM CORTE_MOVIMIENTOS
            WHERE ID_TURNO = ? AND TIPO CONTAINING 'Devol' ''', (turno_id,))
        row = cur.fetchone()
        valor_corte_bruto = float(row[0]) if row and row[0] else 0.0
        
        # 3. Detectar duplicados en CORTE_MOVIMIENTOS
        cur.execute('''SELECT DESCRIPCION, MONTO, COUNT(*) AS VECES FROM CORTE_MOVIMIENTOS
            WHERE ID_TURNO = ? AND TIPO CONTAINING 'Devol'
            GROUP BY DESCRIPCION, MONTO
            HAVING COUNT(*) > 1''', (turno_id,))
        duplicados = cur.fetchall()
        
        # Calcular monto de duplicados
        monto_duplicados = 0.0
        detalle_duplicados = []
        for row in duplicados:
            desc = row[0]
            monto = float(row[1])
            veces = row[2]
            monto_dup = monto * (veces - 1)  # Solo el exceso
            monto_duplicados += monto_dup
            detalle_duplicados.append({
                'descripcion': desc,
                'monto_unitario': monto,
                'veces': veces,
                'monto_duplicado': monto_dup
            })
        
        # Bug tipo 1: TURNOS > CORTE_MOV (Eleventa suma de más en TURNOS)
        diff_turnos_corte = valor_turnos - valor_corte_bruto
        if diff_turnos_corte > 0.01:  # Tolerancia de 1 centavo
            # Buscar qué artículo genera la diferencia
            cur.execute('''SELECT DESCRIPCION, MONTO FROM CORTE_MOVIMIENTOS
                WHERE ID_TURNO = ? AND TIPO CONTAINING 'Devol'
                AND MONTO BETWEEN ? AND ?''', (turno_id, diff_turnos_corte - 0.02, diff_turnos_corte + 0.02))
            articulos_candidatos = []
            for row in cur.fetchall():
                articulos_candidatos.append({
                    'descripcion': row[0],
                    'monto': float(row[1])
                })
            
            resultado['bugs'].append({
                'turno_id': turno_id,
                'tipo': 'turnos_mayor_corte',
                'descripcion': f'TURNOS tiene ${diff_turnos_corte:,.2f} más que CORTE_MOVIMIENTOS',
                'monto_bug': diff_turnos_corte,
                'detalle': articulos_candidatos
            })
            resultado['total_bugs'] += diff_turnos_corte
            resultado['tiene_bugs'] = True
        
        # Bug tipo 2: Duplicados en CORTE_MOVIMIENTOS
        if monto_duplicados > 0.01:
            resultado['bugs'].append({
                'turno_id': turno_id,
                'tipo': 'duplicado_corte',
                'descripcion': f'Artículos duplicados en CORTE_MOVIMIENTOS: ${monto_duplicados:,.2f}',
                'monto_bug': monto_duplicados,
                'detalle': detalle_duplicados
            })
            resultado['total_bugs'] += monto_duplicados
            resultado['tiene_bugs'] = True
        
        # Bug tipo 3: Cancelaciones en CORTE_MOV que NO están en DEVOLUCIONES (no formalizadas)
        # Obtener devoluciones FORMALIZADAS (tabla DEVOLUCIONES) para este turno
        cur.execute('''
            SELECT COALESCE(SUM(TOTAL_DEVUELTO), 0)
            FROM DEVOLUCIONES
            WHERE TURNO_ID = ?
        ''', (turno_id,))
        row = cur.fetchone()
        valor_devoluciones_formales = float(row[0]) if row and row[0] else 0.0
        
        # Valor real de CORTE_MOV sin duplicados
        valor_corte_sin_dup = valor_corte_bruto - monto_duplicados
        
        # Diferencia = lo que está en CORTE_MOV pero no formalizado
        diff_no_formalizada = valor_corte_sin_dup - valor_devoluciones_formales
        
        if diff_no_formalizada > 0.01:  # Tolerancia de 1 centavo
            # Buscar qué tickets tienen devoluciones no formalizadas
            cur.execute('''
                SELECT cm.DESCRIPCION, cm.MONTO
                FROM CORTE_MOVIMIENTOS cm
                WHERE cm.ID_TURNO = ? AND cm.TIPO CONTAINING 'Devol'
            ''', (turno_id,))
            articulos_corte = {}
            for row in cur.fetchall():
                desc = row[0] or 'Sin descripción'
                monto = float(row[1]) if row[1] else 0.0
                key = (desc, monto)
                articulos_corte[key] = articulos_corte.get(key, 0) + 1
            
            detalle_no_form = []
            for (desc, monto), count in articulos_corte.items():
                detalle_no_form.append({
                    'descripcion': desc,
                    'monto': monto,
                    'cantidad': count
                })
            
            resultado['bugs'].append({
                'turno_id': turno_id,
                'tipo': 'cancelacion_no_formalizada',
                'descripcion': f'Cancelaciones no formalizadas: ${diff_no_formalizada:,.2f}',
                'monto_bug': diff_no_formalizada,
                'detalle': detalle_no_form
            })
            resultado['total_bugs'] += diff_no_formalizada
            resultado['tiene_bugs'] = True
    
    # Bug tipo 4: Devoluciones parciales de otro turno (Dev. Parc. OT)
    # Ocurre cuando: ticket con devol. parciales se cancela después y Eleventa duplica
    bug_dev_parc_ot = detectar_bug_dev_parc_otro_turno(cur, turnos, fecha)
    if bug_dev_parc_ot['monto'] > 0.01:
        resultado['bugs'].append({
            'turno_id': 0,  # Aplica a múltiples turnos
            'tipo': 'dev_parc_otro_turno',
            'descripcion': f'Dev. parciales de otro turno duplicadas: ${bug_dev_parc_ot["monto"]:,.2f}',
            'monto_bug': bug_dev_parc_ot['monto'],
            'detalle': bug_dev_parc_ot['detalle']
        })
        resultado['total_bugs'] += bug_dev_parc_ot['monto']
        resultado['tiene_bugs'] = True
    
    conn.close()
    return resultado


def detectar_bug_dev_parc_otro_turno(cur, turnos: List[int], fecha: str) -> Dict:
    """
    Detecta bug de devoluciones parciales de otro turno.
    
    Este bug ocurre cuando:
    1. Un ticket tiene devoluciones parciales en un turno
    2. El ticket se cancela en otro turno posterior
    3. Eleventa duplica las devoluciones parciales en CORTE_MOVIMIENTOS
    
    Se detecta comparando:
    - VENTATICKETS.TOTAL (tickets cancelados)
    - CORTE_MOVIMIENTOS con devoluciones para esos folios
    
    Returns:
        Dict con monto del bug y detalle de folios afectados
    """
    import re
    
    if not turnos:
        return {'monto': 0.0, 'detalle': []}
    
    turnos_str = ','.join(map(str, turnos))
    
    # 1. Obtener tickets cancelados de los turnos del día
    cur.execute(f'''
        SELECT FOLIO, TOTAL 
        FROM VENTATICKETS 
        WHERE TURNO_ID IN ({turnos_str})
        AND ESTA_CANCELADO = 't'
    ''')
    
    tickets_cancelados = {}
    for row in cur.fetchall():
        folio = row[0]
        total = float(row[1]) if row[1] else 0.0
        tickets_cancelados[folio] = total
    
    # 2. Obtener todas las devoluciones de los turnos del día y agrupar por folio
    cur.execute(f'''
        SELECT DESCRIPCION, MONTO 
        FROM CORTE_MOVIMIENTOS 
        WHERE ID_TURNO IN ({turnos_str})
        AND TIPO CONTAINING 'Devol'
    ''')
    
    devoluciones_por_folio = {}
    for row in cur.fetchall():
        desc = row[0] if row[0] else ''
        monto = float(row[1]) if row[1] else 0.0
        
        # Extraer folio de la descripción
        match = re.search(r'#(\d+)', desc)
        if match:
            folio = int(match.group(1))
            if folio not in devoluciones_por_folio:
                devoluciones_por_folio[folio] = 0.0
            devoluciones_por_folio[folio] += monto
    
    # 3. Comparar: si CM > VT para un folio cancelado, hay bug
    monto_bug_total = 0.0
    detalle = []
    
    for folio, total_vt in tickets_cancelados.items():
        total_cm = devoluciones_por_folio.get(folio, 0.0)
        
        # Si CM tiene más que el total del ticket, hay devoluciones de más
        if total_cm > total_vt + 0.01:  # Tolerancia 1 centavo
            diferencia = total_cm - total_vt
            monto_bug_total += diferencia
            detalle.append({
                'folio': folio,
                'ticket_total': total_vt,
                'cm_total': total_cm,
                'diferencia': diferencia
            })
    
    # También detectar devoluciones de folios NO cancelados (como #23252)
    for folio, total_cm in devoluciones_por_folio.items():
        if folio not in tickets_cancelados and total_cm > 0.01:
            # Este folio tiene devoluciones pero NO está cancelado
            # No es un bug que suma, es informativo
            pass
    
    return {
        'monto': monto_bug_total,
        'detalle': detalle
    }


def obtener_bugs_devoluciones_para_ui(fecha: str) -> Tuple[float, str]:
    """
    Versión simplificada para mostrar en la UI de liquidación.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        Tuple (monto_total_bugs, descripcion_corta)
    """
    bugs = detectar_bugs_devoluciones(fecha)
    
    if not bugs['tiene_bugs']:
        return 0.0, ""
    
    # Generar descripción corta
    descripciones = []
    for bug in bugs['bugs']:
        if bug['tipo'] == 'turnos_mayor_corte':
            descripciones.append(f"TURNOS+${bug['monto_bug']:,.0f}")
        elif bug['tipo'] == 'duplicado_corte':
            descripciones.append(f"DUP${bug['monto_bug']:,.0f}")
        elif bug['tipo'] == 'cancelacion_no_formalizada':
            descripciones.append(f"NO_FORM${bug['monto_bug']:,.0f}")
        elif bug['tipo'] == 'dev_parc_otro_turno':
            descripciones.append(f"DEV_OT${bug['monto_bug']:,.0f}")
    
    return bugs['total_bugs'], " | ".join(descripciones)


def obtener_detalle_bugs_para_tooltip(fecha: str) -> str:
    """
    Genera texto detallado para mostrar en tooltip.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        Texto descriptivo de los bugs
    """
    bugs = detectar_bugs_devoluciones(fecha)
    
    if not bugs['tiene_bugs']:
        return "Sin bugs de duplicación detectados"
    
    lineas = [f"🐛 BUGS DE ELEVENTA ({fecha})", "=" * 40]
    
    for bug in bugs['bugs']:
        lineas.append(f"\nTurno {bug['turno_id']}:")
        lineas.append(f"  Tipo: {bug['tipo']}")
        lineas.append(f"  Monto: ${bug['monto_bug']:,.2f}")
        
        if bug['detalle']:
            lineas.append("  Artículos:")
            for item in bug['detalle'][:3]:  # Máximo 3 para no saturar
                if 'descripcion' in item:
                    desc = item['descripcion'][:45] if item.get('descripcion') else 'Sin descripción'
                    lineas.append(f"    - {desc}")
    
    lineas.append(f"\n{'=' * 40}")
    lineas.append(f"TOTAL BUGS: ${bugs['total_bugs']:,.2f}")
    
    return "\n".join(lineas)


# Ejecutar validación si se corre directamente
if __name__ == "__main__":
    print("\n" + "="*80)
    print("VALIDACIÓN 4 DE FEBRERO 2026")
    print("="*80)
    validar_calculo_devoluciones('2026-02-04')
    
    print("\n\n" + "="*80)
    print("VALIDACIÓN 9 DE FEBRERO 2026")
    print("="*80)
    validar_calculo_devoluciones('2026-02-09')
    
    print("\n\n" + "="*80)
    print("DETECCIÓN DE BUGS")
    print("="*80)
    bugs_4feb = detectar_bugs_devoluciones('2026-02-04')
    print(f"\n4 FEB - Tiene bugs: {bugs_4feb['tiene_bugs']}, Total: ${bugs_4feb['total_bugs']:,.2f}")
    for bug in bugs_4feb['bugs']:
        print(f"  - {bug['tipo']}: ${bug['monto_bug']:,.2f}")
    
    bugs_9feb = detectar_bugs_devoluciones('2026-02-09')
    print(f"\n9 FEB - Tiene bugs: {bugs_9feb['tiene_bugs']}, Total: ${bugs_9feb['total_bugs']:,.2f}")
    for bug in bugs_9feb['bugs']:
        print(f"  - {bug['tipo']}: ${bug['monto_bug']:,.2f}")
