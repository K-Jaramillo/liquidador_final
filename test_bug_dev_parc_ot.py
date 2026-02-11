"""
Script de prueba para verificar la detección del Bug Dev. Parc. OT
"""
import utils_devoluciones
from datetime import date

# Obtener bugs para el 3 de febrero 2026
fecha = '2026-02-03'
bugs_resultado = utils_devoluciones.detectar_bugs_devoluciones(fecha)

print(f'=== BUGS DETECTADOS PARA {fecha} ===')
print(f'Tiene bugs: {bugs_resultado["tiene_bugs"]}')
print(f'Total bugs: ${bugs_resultado["total_bugs"]:,.2f}')
print()

bug_dev_parc_ot_total = 0
for bug in bugs_resultado['bugs']:
    print(f'  Tipo: {bug["tipo"]}')
    print(f'  Turno: {bug["turno_id"]}')
    print(f'  Monto: ${bug["monto_bug"]:,.2f}')
    print(f'  Descripción: {bug["descripcion"]}')
    print()
    
    if bug['tipo'] == 'dev_parc_otro_turno':
        bug_dev_parc_ot_total += bug['monto_bug']

print(f'=== RESUMEN ===')
print(f'Total Bug Dev. Parc. OT: ${bug_dev_parc_ot_total:,.2f}')
