# Script de instalación de Firebird 2.5.9 para Windows
# Ejecutar como Administrador

Write-Host "=== Instalador de Firebird 2.5.9 ===" -ForegroundColor Cyan
Write-Host ""

# Verificar si se ejecuta como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: Este script debe ejecutarse como Administrador" -ForegroundColor Red
    Write-Host "Haz clic derecho en PowerShell y selecciona 'Ejecutar como administrador'" -ForegroundColor Yellow
    pause
    exit
}

# SOLUCIÓN AL ERROR SSL/TLS: Habilitar TLS 1.2
Write-Host "Configurando protocolos de seguridad..." -ForegroundColor Yellow
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor `
                                              [Net.SecurityProtocolType]::Tls11 -bor `
                                              [Net.SecurityProtocolType]::Tls

# Configuración
$firebirdVersion = "2.5.9.27139"
$downloadUrl = "https://github.com/FirebirdSQL/firebird/releases/download/R2_5_9/Firebird-2.5.9.27139_0_Win32.exe"
$installerPath = "$env:TEMP\Firebird-2.5.9.exe"
$installPath = "C:\Program Files\Firebird\Firebird_2_5"

Write-Host "Verificando si Firebird ya está instalado..." -ForegroundColor Yellow

# Verificar si ya está instalado
$firebirdService = Get-Service | Where-Object {$_.Name -like "*Firebird*"}

if ($firebirdService) {
    Write-Host "Firebird ya está instalado:" -ForegroundColor Green
    $firebirdService | Format-Table Name, Status, DisplayName -AutoSize
    
    $response = Read-Host "¿Deseas reinstalar? (S/N)"
    if ($response -ne "S" -and $response -ne "s") {
        Write-Host "Instalación cancelada." -ForegroundColor Yellow
        exit
    }
}

Write-Host ""
Write-Host "Descargando Firebird $firebirdVersion..." -ForegroundColor Yellow

try {
    # Descargar el instalador con TLS 1.2 habilitado
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "Descarga completada: $(((Get-Item $installerPath).Length / 1MB).ToString('0.00')) MB" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudo descargar Firebird" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Intentando descarga alternativa..." -ForegroundColor Yellow
    
    try {
        # URL alternativa (espejo)
        $alternativeUrl = "https://sourceforge.net/projects/firebird/files/firebird-win32/2.5.9-Release/Firebird-2.5.9.27139_0_Win32.exe/download"
        Invoke-WebRequest -Uri $alternativeUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "Descarga completada desde servidor alternativo." -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Tampoco funcionó la descarga alternativa" -ForegroundColor Red
        Write-Host "Por favor descarga manualmente desde:" -ForegroundColor Yellow
        Write-Host "https://firebirdsql.org/en/firebird-2-5-9/" -ForegroundColor Cyan
        pause
        exit
    }
}

Write-Host ""
Write-Host "Instalando Firebird..." -ForegroundColor Yellow
Write-Host "Esto puede tomar unos minutos. Por favor espera..." -ForegroundColor Cyan

try {
    # Instalar en modo silencioso
    $installArgs = @(
        "/SP-",
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/COMPONENTS=ServerComponent,ClientComponent,DevAdminComponent",
        "/TASKS=UseApplicationTask,UseServiceTask,AutoStartTask"
    )
    
    Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -NoNewWindow
    
    Write-Host "Instalación completada." -ForegroundColor Green
} catch {
    Write-Host "ERROR durante la instalación" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    pause
    exit
}

Write-Host ""
Write-Host "Verificando la instalación..." -ForegroundColor Yellow

# Esperar un momento para que el servicio se registre
Start-Sleep -Seconds 3

# Verificar el servicio
$service = Get-Service | Where-Object {$_.Name -like "*Firebird*"}

if ($service) {
    Write-Host "Servicio de Firebird encontrado:" -ForegroundColor Green
    $service | Format-Table Name, Status, DisplayName -AutoSize
    
    # Iniciar el servicio si no está corriendo
    if ($service.Status -ne "Running") {
        Write-Host "Iniciando el servicio..." -ForegroundColor Yellow
        Start-Service $service.Name
        Start-Sleep -Seconds 2
        Write-Host "Servicio iniciado." -ForegroundColor Green
    }
} else {
    Write-Host "ADVERTENCIA: No se encontró el servicio de Firebird" -ForegroundColor Yellow
}

# Verificar archivos instalados
if (Test-Path "$installPath\bin\isql.exe") {
    Write-Host ""
    Write-Host "Firebird instalado correctamente en:" -ForegroundColor Green
    Write-Host $installPath -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "Herramientas disponibles:" -ForegroundColor Green
    Write-Host "  - isql.exe: $installPath\bin\isql.exe" -ForegroundColor Cyan
    Write-Host "  - gbak.exe: $installPath\bin\gbak.exe" -ForegroundColor Cyan
    Write-Host "  - gfix.exe: $installPath\bin\gfix.exe" -ForegroundColor Cyan
} else {
    Write-Host "ADVERTENCIA: No se encontraron los archivos de Firebird en la ruta esperada" -ForegroundColor Yellow
}

# Limpiar archivo temporal
if (Test-Path $installerPath) {
    Remove-Item $installerPath -Force
    Write-Host ""
    Write-Host "Archivos temporales eliminados." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Instalación finalizada ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANTE: La contraseña por defecto de SYSDBA es 'masterkey'" -ForegroundColor Yellow
Write-Host "Se recomienda cambiarla por seguridad." -ForegroundColor Yellow
Write-Host ""
Write-Host "Para conectarte a una base de datos:" -ForegroundColor Green
Write-Host '  cd "C:\Program Files\Firebird\Firebird_2_5\bin"' -ForegroundColor Cyan
Write-Host '  .\isql.exe -u SYSDBA -p masterkey "ruta\a\tu\base.fdb"' -ForegroundColor Cyan
Write-Host ""

pause