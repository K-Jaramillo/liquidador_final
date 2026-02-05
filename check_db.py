import fdb
db_path = r'D:\BD\PDVDATA.FDB'
con = fdb.connect(dsn=db_path, user='SYSDBA', password='masterkey', charset='WIN1252')
cur = con.cursor()

# Ver fechas disponibles
cur.execute("SELECT CAST(PAGADO_EN AS DATE) as FECHA, COUNT(*) as TOTAL FROM VENTATICKETS WHERE PAGADO_EN IS NOT NULL GROUP BY CAST(PAGADO_EN AS DATE) ORDER BY FECHA DESC ROWS 30")
print('Fechas con ventas (ultimas 30):')
for row in cur.fetchall():
    print(f'  {row[0]} - {row[1]} tickets')
con.close()
