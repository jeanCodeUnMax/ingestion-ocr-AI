Param(
    [ValidateSet('auto', 'force', 'skip')]
    [string]$IngestMode = 'auto',
    [switch]$Watch = $true,
    [switch]$Quiet = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

[console]::InputEncoding = [console]::OutputEncoding = New-Object System.Text.UTF8Encoding

# Configuration du logging
$ScriptRoot = $PSScriptRoot
if (-not $ScriptRoot) { $ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path }
$LogDir = Join-Path $ScriptRoot "..\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$LogFile = Join-Path $LogDir "workspace.log"
$ErrorLogFile = Join-Path $LogDir "error.log"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    try {
        Add-Content -Path $LogFile -Value $logEntry -ErrorAction SilentlyContinue
    }
    catch {
        # Si le fichier log est inaccessible, on continue quand même
    }
    
    if ($Level -eq "WARN") {
        Write-Host $logEntry -ForegroundColor Yellow
    } elseif ($Level -eq "ERROR") {
        Write-Host $logEntry -ForegroundColor Red
    } elseif ($Message -match "✅|SUCCESS") {
        Write-Host $logEntry -ForegroundColor Green
    } else {
        Write-Host $logEntry -ForegroundColor Cyan
    }
}

function Write-ErrorLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [ERROR] $Message"
    
    try {
        Add-Content -Path $ErrorLogFile -Value $logEntry -ErrorAction SilentlyContinue
    }
    catch {
        # Si le fichier error log est inaccessible, on continue quand même
    }
    
    Write-Host $logEntry -ForegroundColor Red
}

function Stop-BridgePorts {
    param(
        [int[]]$Ports = @(8001, 8002)
    )

    foreach ($port in $Ports) {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($conns) {
            $pids = $conns | ForEach-Object { [int]$_.OwningProcess } | Where-Object { $_ -gt 4 } | Select-Object -Unique
            if ($pids) {
                foreach ($pidToKill in $pids) {
                    try {
                        Stop-Process -Id $pidToKill -Force -ErrorAction Stop
                        Write-Log "Port $port libere (PID $pidToKill termine)"
                    }
                    catch {
                        Write-ErrorLog "Echec kill PID $pidToKill sur port $port : $($_.Exception.Message)"
                    }
                }
            } else {
                Write-Log "Port $port deja libre"
            }
        }
        else {
            Write-Log "Port $port deja libre"
        }
    }
}

# $ScriptRoot is already defined at the top
$ProjectRoot = Split-Path -Parent $ScriptRoot  # = .agent folder
$ProjectRootDir = Split-Path -Parent $ProjectRoot  # = actual project root
$autoIngest = Join-Path $ScriptRoot 'auto-ingest.ps1'
$ingestScript = Join-Path $ScriptRoot 'ingest-workspace.ps1'
$ingestConfig = Join-Path $ScriptRoot 'ingestion.config.json'
$monitorScript = Join-Path $ScriptRoot 'monitor.js'

# --- KILL CIBLE MCP / BRIDGE SUR 8001 & 8002 (EN TOUT DEBUT) ---
Write-Log "Verification des ports bridge MCP (8001, 8002)..."
Stop-BridgePorts -Ports @(8001, 8002)

# --- NETTOYAGE SYSTÈME AVANT DÉMARRAGE (MENU MAINTENANCE ADMIN) ---
Write-Log "🧹 Lancement du menu maintenance admin (mode automatique)..."
$MaintenanceScript = Join-Path $ProjectRootDir "menu_maintenance_clean.ps1"
if (Test-Path $MaintenanceScript) {
    $env:JIMINY_MAINTENANCE_BYPASS = "1"
    & powershell -ExecutionPolicy Bypass -File $MaintenanceScript -Auto
    $env:JIMINY_MAINTENANCE_BYPASS = "0"
} else {
    Write-Log "⚠️ Script menu_maintenance_clean.ps1 non trouvé"
}

# --- INITIALISATION STRUCTURELLE (MÉMOIRE UNIFIÉE V3) ---
# Architecture: Global (persistant) + Local (workspace actif)
$MemoryGlobal = "D:\DATA-WEBMAN\memory"
$MemoryLocal = "D:\DATA-WEBMAN\memory\current_workspace"

# Lecture depuis .env si existe
$EnvFile = Join-Path $ProjectRootDir ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if (-not $_.StartsWith('#') -and $_.Contains('=')) {
            $parts = $_.Split('=', 2)
            $key = $parts[0].Trim()
            $value = $parts[1].Trim()
            if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") { $value = $matches[1] }
            if ($key -eq "MEMORY_GLOBAL" -and $value) { $MemoryGlobal = $value }
            if ($key -eq "MEMORY_LOCAL" -and $value) { $MemoryLocal = $value }
        }
    }
}

$GraphDir = Join-Path $MemoryLocal "graph"
$VectorDir = Join-Path $MemoryLocal "vector"
$CacheDir = Join-Path $MemoryGlobal "cache"
$KnowledgeDir = Join-Path $ScriptRoot "../knowledge"

# Création immédiate des dossiers parents UNIQUEMENT.
# Les fichiers .db seront créés proprement par les serveurs MCP lors de l'accès.
$criticalDirs = @($GraphDir, $VectorDir, $CacheDir, $KnowledgeDir)
foreach ($dir in $criticalDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Log "Structure de répertoires locale synchronisée."

# --- LECTURE DU FICHIER .ENV ---
$EnvFile = Join-Path $ProjectRootDir ".env"
if (Test-Path $EnvFile) {
    Write-Log "Lecture de .env..."
    Get-Content $EnvFile | ForEach-Object {
        if (-not $_.StartsWith('#')) {
            $parts = $_.Split('=', 2)
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                # Supprimer les guillemets si présents
                if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
                    $value = $matches[1]
                }
                if ($key -eq "CASCADE_DB_ROOT" -and -not [string]::IsNullOrWhiteSpace($value)) {
                    $env:CASCADE_DB_ROOT = $value
                    Write-Log "CASCADE_DB_ROOT défini depuis .env: $value"
                }
            }
        }
    }
}

# --- STOCKAGE UNIFIÉ V3 (Global + Local) ---
# Global: patterns, rules, corrections (persistants)
# Local: current_workspace (spécifique au workspace actif)

Write-Log "Configuration STOCKAGE UNIFIÉ V3:"
Write-Log "  🧠 Global: $MemoryGlobal"
Write-Log "  📝 Local:  $MemoryLocal"

# Configuration des dossiers dans la mémoire unifiée V3
$globalCacheDir = Join-Path $MemoryGlobal "cache"
$globalPatternsDir = Join-Path $MemoryGlobal "patterns"
$globalRulesDir = Join-Path $MemoryGlobal "rules"
$globalCorrectionsDir = Join-Path $MemoryGlobal "corrections"
$localGraphDir = Join-Path $MemoryLocal "graph"
$localVectorDir = Join-Path $MemoryLocal "vector"

# Créer l'arborescence V3 si absente
foreach ($dir in @($globalCacheDir, $globalPatternsDir, $globalRulesDir, $globalCorrectionsDir, $localGraphDir, $localVectorDir)) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

# --- LES SERVEURS MCP SONT GÉRÉS PAR L'IDE (WINDSURF) ---
# Suppression du démarrage manuel pour éviter les conflits de ports et les erreurs système.

# --- PONT REST RAG (AUTONOME) ---
# Lance le pont HTTP Python qui traduit les appels REST du pipeline
# en appels MCP stdio vers Zvec et Memory (instances dédiées, non gérées par l'IDE).
$BridgeScript = Join-Path (Join-Path $ProjectRootDir "core\rag") "rag_rest_bridge.py"
$BridgePidFile = Join-Path $ScriptRoot "rag_bridge.pid"

# Arrêter le bridge précédent s'il tourne encore
if (Test-Path $BridgePidFile) {
    $oldPid = Get-Content $BridgePidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        try {
            $oldProc = Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue
            if ($oldProc) { 
                Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
            }
        }
        catch { }  # Process déjà mort, on continue
    }
    Remove-Item $BridgePidFile -Force -ErrorAction SilentlyContinue
}

# FERMETURE DES ORPHELINS (Zvec, Memory)
# Le bridge peut laisser des processus node en vie s'il est tué avec -Force
$orphans = @(Get-Process node -ErrorAction SilentlyContinue | Where-Object { 
    try { $_.CommandLine -like "*Zvec*" -or $_.CommandLine -like "*memory*" } catch { $false }
})

if ($orphans.Count -gt 0) {
    Write-Log "Nettoyage de $($orphans.Count) processus MCP orphelins..."
    $orphans | Stop-Process -Force -ErrorAction SilentlyContinue
}


# Vérifier les ports 8001 / 8002 libres
$port8001Busy = (netstat -ano 2>$null | Select-String ":8001.*LISTENING") -ne $null
$port8002Busy = (netstat -ano 2>$null | Select-String ":8002.*LISTENING") -ne $null

if ($port8001Busy -or $port8002Busy) {
    Write-Log "⚠️  Ports 8001/8002 déjà occupés - ponte REST peut-être déjà actif."
}
else {
    if (Test-Path $BridgeScript) {
        Write-Log "Démarrage du pont REST RAG (ports 8001/8002)..."
        $zvecDataDir = Join-Path $MemoryLocal "vector" "zvec"
        
        # Définir les variables d'environnement pour le processus bridge
        $env:ZVEC_BRIDGE_PORT = "8001"
        $env:MEMORY_BRIDGE_PORT = "8002"
        $env:ZVEC_DATA_DIR = $zvecDataDir
        $env:MEMORY_GLOBAL = $MemoryGlobal
        $env:MEMORY_LOCAL = $MemoryLocal

        
        $bridgeLogFile = Join-Path $ScriptRoot "rag_bridge_stdout.log"
        $bridgeErrorFile = Join-Path $ScriptRoot "rag_bridge_stderr.log"
        $bridgeFolder = Split-Path $BridgeScript -Parent
        # Utiliser WorkingDirectory permet d'éviter les problèmes d'espaces dans le chemin du script
        $bridgeProcess = Start-Process python -ArgumentList @("-u", "rag_rest_bridge.py") -WorkingDirectory $bridgeFolder -WindowStyle Hidden -PassThru -RedirectStandardOutput $bridgeLogFile -RedirectStandardError $bridgeErrorFile

        
        $bridgeProcess.Id | Out-File $BridgePidFile -Encoding ascii
        Write-Log "✅ Pont REST RAG lancé (PID=$($bridgeProcess.Id))"
        
        # Attendre que le bridge soit prêt (max 60 secondes)
        $maxWait = 60

        $ready = $false
        for ($i = 0; $i -lt $maxWait; $i++) {
            if ($bridgeProcess.HasExited) {
                Write-Log "⚠️  Le pont REST RAG s'est arrêté prématurément (PID=$($bridgeProcess.Id), ExitCode=$($bridgeProcess.ExitCode))."
                break
            }
            Start-Sleep -Seconds 1
            try {
                $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -TimeoutSec 1 -ErrorAction Stop
                if ($resp.StatusCode -eq 200) { $ready = $true; break }
            }
            catch { }
        }
        if ($ready) {
            Write-Log "✅ Pont REST RAG opérationnel et répondant."
        }
        else {
            Write-Log "⚠️  Pont REST RAG non disponible (vérifie rag_bridge_stderr.log et rag_bridge_stdout.log)"
        }
    }
    else {
        Write-Log "⚠️  Script pont REST non trouvé : $BridgeScript"
    }
}

# Lancer le moniteur en arrière-plan
Write-Log "Lancement du Moniteur (Port 3055)"
Start-Process node -ArgumentList $monitorScript -WindowStyle Hidden

# Lancer le Watchdog Jiminy (logs visibles, asynchrone)
$WatchdogScript = Join-Path $ProjectRootDir "core\conscience\jiminy_watchdog.py"
if (Test-Path $WatchdogScript) {
    Write-Log "🐕 Lancement du Watchdog Jiminy (mode silencieux)..."
    Start-Process python -ArgumentList @($WatchdogScript, "--watch", "--quiet") -WorkingDirectory $ProjectRootDir -NoNewWindow
    Start-Sleep -Milliseconds 500  # Laisser le temps au processus de démarrer
} else {
    Write-Log "⚠️ Script watchdog.py non trouvé : $WatchdogScript"
}

Write-Log "Vérification/ingestion initiale ($IngestMode)"

& powershell -ExecutionPolicy Bypass -File $autoIngest -Mode $IngestMode -ConfigPath $ingestConfig

if ($Watch) {
    Write-Log "Starting continuous watch (Ctrl+C to stop)"
    $cmdArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ingestScript, "-Mode", "watch", "-ConfigPath", $ingestConfig)
    & powershell @cmdArgs
}
else {
    Write-Log 'Watch disabled (parameter -Watch:$false)'
}
