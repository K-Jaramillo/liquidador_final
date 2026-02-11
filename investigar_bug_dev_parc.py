"""
Script para investigar detalle del Bug Dev. Parc. OT
"""
import fdb

DB_PATH = r"D:\BDEV\PDVDATA.FDB"
USER = "SYSDBA"
PASSWORD = "masterkey"

fecha = '2026-02-03'

conn = fdb.connect(
    dsn=DB_PATH,
    user=USER,
    password=PASSWORD,
    charset='UTF8'
)
cur = conn.cursor()

# Obtener turnos del día
cur.execute(f"""
    SELECT ID FROM TURNOS 
    WHERE CAST(INICIO_EN AS DATE) = '{fecha}'
""")
turnos = [row[0] for row in cur.fetchall()]
turnos_str = ','.join(map(str, turnos))

print(f"Turnos del día: {turnos}")
print()

# 1. Obtener tickets cancelados
cur.execute(f'''
    SELECT FOLIO, TOTAL 
    FROM VENTATICKETS 
    WHERE TURNO_ID IN ({turnos_str})
    AND ESTA_CANCELADO = 't'
    ORDER BY FOLIO
''')

tickets_cancelados = {}
for row in cur.fetchall():
    folio = row[0]
    total = float(row[1]) if row[1] else 0.0
    tickets_cancelados[folio] = total

print(f"Tickets cancelados: {len(tickets_cancelados)}")
print()

# 2. Obtener devoluciones por folio
import re

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
    
    match = re.search(r'#(\d+)', desc)
    if match:
        folio = int(match.group(1))
        if folio not in devoluciones_por_folio:
            devoluciones_por_folio[folio] = 0.0
        devoluciones_por_folio[folio] += monto

# 3. Mostrar detalle de cada folio con bug
print("=" * 80)
print("DETALLE DE FOLIOS CON BUG (CM > VT):")
print("=" * 80)

monto_bug_total = 0.0
for folio in sorted(tickets_cancelados.keys()):
    total_vt = tickets_cancelados[folio]
    total_cm = devoluciones_por_folio.get(folio, 0.0)
    
    if total_cm > total_vt + 0.01:
        diferencia = total_cm - total_vt
        monto_bug_total += diferencia
        print(f"Folio #{folio}:")
        print(f"  VENTATICKETS.TOTAL = ${total_vt:,.2f}")
        print(f"  CORTE_MOV.TOTAL    = ${total_cm:,.2f}")
        print(f"  DIFERENCIA (bug)   = ${diferencia:,.2f}")
        print()

print("=" * 80)
print(f"TOTAL BUG: ${monto_bug_total:,.2f}")
print()

# 4. Verificar específicamente los folios que mencionamos antes
print("=" * 80)
print("VERIFICACIÓN DE FOLIOS #23221 y #23232:")
print("=" * 80)

for folio in [23221, 23232]:
    print(f"\nFolio #{folio}:")
    
    # VT
    total_vt = tickets_cancelados.get(folio, 0.0)
    print(f"  VENTATICKETS.TOTAL = ${total_vt:,.2f}")
    
    # CM total
    total_cm = devoluciones_por_folio.get(folio, 0.0)
    print(f"  CORTE_MOV (calculado) = ${total_cm:,.2f}")
    
    # CM detalle
    cur.execute(f'''
        SELECT DESCRIPCION, MONTO 
        FROM CORTE_MOVIMIENTOS 
        WHERE ID_TURNO IN ({turnos_str})
        AND TIPO CONTAINING 'Devol'
        AND DESCRIPCION CONTAINING '#{folio}'
        ORDER BY MONTO DESC
    ''')
    print("  Detalle CORTE_MOV:")
    for row in cur.fetchall():
        print(f"    - ${float(row[1]):,.2f} : {row[0][:60]}")

conn.close()
