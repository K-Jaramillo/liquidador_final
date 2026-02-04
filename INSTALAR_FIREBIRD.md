# Instalación de Firebird en Windows

## OPCIÓN 1: Instalación Normal (RECOMENDADO)

### Pasos:
1. **Descargar Firebird**
   - Ve a: https://www.firebirdsql.org/download/
   - Descarga "Firebird 2.5.9" o "Firebird 3.0" para Windows
   - Elige la versión **x64** si tu Windows es de 64 bits

2. **Instalar**
   - Ejecuta el instalador (.exe)
   - Acepta la ruta por defecto: `C:\Program Files\Firebird\Firebird_X_X\`
   - Marca "Install Firebird as Service" (opcional)

3. **Verificar Instalación**
   - Ejecuta desde Terminal: `diagnostico_firebird.py`
   - Si todo está bien, mostrará la ruta de `isql.exe`

4. **Usar en la Aplicación**
   - Abre `liquidador_repartidores.py`
   - Haz clic en "Examinar" para seleccionar `PDVDATA.FDB`
   - Haz clic en "Verificar" para confirmar la conexión

---

## OPCIÓN 2: Instalación Portable (Sin Instalar)

Si no quieres instalar:

1. **Descargar Firebird Portable**
   - Ve a: https://www.firebirdsql.org/download/
   - Descarga "Firebird Portable" para Windows

2. **Extraer**
   - Extrae el .zip en: `C:\Firebird\`
   - La carpeta `bin` estará en: `C:\Firebird\bin\`

3. **Agregar al PATH (Opcional)**
   - Abre Variables de Entorno en Windows:
     - `Win + X` → "Sistema"
     - "Configuración avanzada del sistema"
     - "Variables de entorno"
   - Busca la variable `PATH`
   - Agrega: `C:\Firebird\bin`

---

## OPCIÓN 3: Sin Firebird (Para Pruebas)

Si no quieres instalar Firebird aún:

1. Ejecuta: `python liquidador_modo_demo.py`
   - Esto abre la aplicación con **datos de ejemplo**
   - Puedes probar todas las funciones
   - Los datos se guardan en JSON local

2. Cuando instales Firebird:
   - Vuelve a usar: `python liquidador_repartidores.py`
   - Selecciona tu `PDVDATA.FDB`
   - ¡Todo funcionará igual!

---

## Solución de Problemas

### Error: "No se encontró isql.exe"
- Verifica que Firebird esté en: `C:\Program Files\Firebird\`
- Ejecuta el diagnóstico: `python diagnostico_firebird.py`
- Si aún no aparece, agrega la carpeta `bin` a tu PATH

### Error: "Archivo no encontrado"
- Verifica que `PDVDATA.FDB` existe en tu ruta
- Abre el selector: botón "Examinar"
- Navega hasta tu archivo FDB

### Error: "No se puede conectar a la BD"
- Verifica credenciales: Usuario `SYSDBA`, Contraseña `masterkey`
- Verifica que el archivo FDB no esté corrupto
- Prueba abrir el archivo con otra herramienta Firebird

---

## Contacto / Ayuda

Si tienes problemas:
1. Ejecuta: `python diagnostico_firebird.py`
2. Copia el resultado completo
3. Comparte para ayudarte a diagnosticar

---

**Firebird es gratis y open-source. ¡No hay complicaciones! 🎉**
