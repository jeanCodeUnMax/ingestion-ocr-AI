<#
.SYNOPSIS
    Menu maintenance admin - Nettoyage automatique du workspace Hephaistos

.DESCRIPTION
    Effectue un ensemble de taches de nettoyage et de maintenance du systeme :
      - Suppression des fichiers temporaires et des logs trop anciens
      - Nettoyage des fichiers __pycache__ Python
      - Verification et suppression des fichiers .pid orphelins
      - Rotation des logs volumineux
      - Rapport de maintenance dans .agent/logs/maintenance.log

.PARAMETER Auto
    Lance le menu en mode non-interactif (automatique). Toutes les taches
    configurees s'executent sans demande de confirmation.

.PARAMETER DryRun
    Simule les operations sans rien supprimer ni modifier.
#>

Param(
    [switch]$Auto,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

# --- Chemins ---

$ScriptDir   = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

$ProjectRoot = $ScriptDir
$AgentDir    = Join-Path $ProjectRoot ".agent"
$LogDir      = Join-Path $AgentDir "logs"
$ScriptsDir  = Join-Path $AgentDir "scripts"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

$LogFile = Join-Path $LogDir "maintenance.log"

# --- Logging ---

function Write-MLog {
    param([string]$Message, [string]$Level = "INFO")
    $ts    = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$ts] [$Level] [MAINTENANCE] $Message"
    Add-Content -Path $LogFile -Value $entry -ErrorAction SilentlyContinue
    switch ($Level) {
        "ERROR"   { Write-Host $entry -ForegroundColor Red }
        "WARNING" { Write-Host $entry -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $entry -ForegroundColor Green }
        default   { Write-Host $entry }
    }
}

# --- Utilitaires ---

$Stats = @{ removed = 0; skipped = 0; errors = 0; bytes_freed = 0 }

function Remove-SafeItem {
    param([string]$Path, [string]$Reason = "")
    if (-not (Test-Path $Path)) { return }
    try {
        $item = Get-Item $Path -ErrorAction Stop
        $size = if ($item.PSIsContainer) {
            $meas = Get-ChildItem -LiteralPath $item.FullName -Recurse -File -ErrorAction SilentlyContinue |
                    Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue
            if ($meas -and $meas.Sum) { $meas.Sum } else { 0 }
        } else { $item.Length }

        if ($DryRun) {
            Write-MLog "  [DRY-RUN] Aurait supprime : $Path ($Reason)"
            $script:Stats.skipped++
        } else {
            Microsoft.PowerShell.Management\Remove-Item $Path -Recurse -Force -ErrorAction Stop
            $script:Stats.removed++
            $script:Stats.bytes_freed += ($size -as [long])
            Write-MLog "  [OK] Supprime : $Path ($Reason)" -Level "SUCCESS"
        }
    } catch {
        Write-MLog "  [FAIL] Echec suppression $Path : $($_.Exception.Message)" -Level "ERROR"
        $script:Stats.errors++
    }
}

# --- Taches de maintenance ---

function Clear-PycacheDirectories {
    Write-MLog "Nettoyage __pycache__ Python..."
    $caches = @(Get-ChildItem -Path $ProjectRoot -Filter "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue)
    if ($caches.Count -eq 0) {
        Write-MLog "  Aucun __pycache__ trouve."
        return
    }
    foreach ($c in $caches) { Remove-SafeItem $c.FullName "__pycache__" }
    Write-MLog "  -> $($caches.Count) repertoire(s) __pycache__ traites."
}

function Clear-OldLogs {
    param([int]$RetentionDays = 7)
    Write-MLog "Rotation des logs (retention : ${RetentionDays}j)..."
    $cutoff  = (Get-Date).AddDays(-$RetentionDays)
    $logFiles = @(Get-ChildItem -Path $LogDir -Filter "*.log" -File -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTime -lt $cutoff })
    if ($logFiles.Count -eq 0) {
        Write-MLog "  Aucun log expire."
        return
    }
    foreach ($lf in $logFiles) { Remove-SafeItem $lf.FullName "log>${RetentionDays}j" }
}

function Clear-OrphanedPidFiles {
    Write-MLog "Verification des fichiers .pid orphelins..."
    $pidFiles = @(Get-ChildItem -Path $ScriptsDir -Filter "*.pid" -File -ErrorAction SilentlyContinue)
    foreach ($pf in $pidFiles) {
        $rawPid = (Get-Content $pf.FullName -ErrorAction SilentlyContinue) -as [string]
        $numPid = $rawPid -as [int]
        if ($numPid -and $numPid -gt 0) {
            $proc = Get-Process -Id $numPid -ErrorAction SilentlyContinue
            if (-not $proc) {
                Write-MLog "  PID $numPid ($($pf.Name)) est mort - suppression du .pid"
                Remove-SafeItem $pf.FullName "pid_orphelin"
            } else {
                Write-MLog "  PID $numPid ($($pf.Name)) actif - conserve."
            }
        } else {
            Remove-SafeItem $pf.FullName "pid_invalide"
        }
    }
}

function Clear-TempFiles {
    Write-MLog "Nettoyage des fichiers temporaires..."
    $patterns = @("*.tmp", "*.bak", "~$*", "*.pyc")
    $total    = 0
    foreach ($pat in $patterns) {
        $found = Get-ChildItem -Path $ProjectRoot -Filter $pat -Recurse -File -ErrorAction SilentlyContinue
        foreach ($f in $found) {
            Remove-SafeItem $f.FullName "temp:$pat"
            $total++
        }
    }
    if ($total -eq 0) { Write-MLog "  Aucun fichier temporaire trouve." }
}

function Rotate-LargeLogFile {
    param([string]$FilePath, [long]$MaxSizeBytes = 5242880)
    if (-not (Test-Path $FilePath)) { return }
    $file = Get-Item $FilePath -ErrorAction SilentlyContinue
    if ($file -and $file.Length -gt $MaxSizeBytes) {
        $archive = "$FilePath.$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
        $sizeMB = [math]::Round($file.Length / 1MB, 1)
        Write-MLog "  Rotation : $($file.Name) ($sizeMB MB) -> .bak"
        if (-not $DryRun) {
            try {
                Move-Item $FilePath $archive -Force -ErrorAction Stop
                New-Item -ItemType File -Path $FilePath -Force | Out-Null
                $script:Stats.removed++
            } catch {
                Write-MLog "  [FAIL] Rotation echouee : $($_.Exception.Message)" -Level "ERROR"
                $script:Stats.errors++
            }
        }
    }
}

function Rotate-BridgeLogs {
    Write-MLog "Rotation des logs du pont RAG si volumineux..."
    $bridgeLogs = @(
        (Join-Path $ScriptsDir "rag_bridge_stdout.log"),
        (Join-Path $ScriptsDir "rag_bridge_stderr.log"),
        (Join-Path $ScriptsDir "ingestion.log")
    )
    foreach ($bl in $bridgeLogs) { Rotate-LargeLogFile $bl -MaxSizeBytes 5242880 }
}

# --- Rapport final ---

function Write-MaintenanceReport {
    $freed = if ($Stats.bytes_freed -gt 1MB) {
        "$([math]::Round($Stats.bytes_freed / 1MB, 2)) MB"
    } else {
        "$([math]::Round($Stats.bytes_freed / 1KB, 1)) KB"
    }
    Write-MLog "--- RAPPORT MAINTENANCE ---"
    Write-MLog "   Supprimes : $($Stats.removed)"
    Write-MLog "   Ignores   : $($Stats.skipped)"
    Write-MLog "   Erreurs   : $($Stats.errors)"
    Write-MLog "   Libere    : $freed"
    if ($DryRun) { Write-MLog "   [!] Mode DRY-RUN - aucune modification reelle." -Level "WARNING" }
    Write-MLog "---------------------------"
}

# --- Point d'entree ---

Write-MLog "Demarrage menu maintenance Hephaistos"
Write-MLog "Mode : $(if ($Auto) { 'AUTO' } else { 'INTERACTIF' })$(if ($DryRun) { ' + DRY-RUN' })"
Write-MLog "Racine : $ProjectRoot"

if ($Auto) {
    Clear-PycacheDirectories
    Clear-OrphanedPidFiles
    Rotate-BridgeLogs
    Clear-TempFiles
    Clear-OldLogs -RetentionDays 7
} else {
    Write-Host ""
    Write-Host "MENU MAINTENANCE HEPHAISTOS" -ForegroundColor Cyan
    Write-Host "1. Nettoyer __pycache__" -ForegroundColor Cyan
    Write-Host "2. Verifier PID orphelins" -ForegroundColor Cyan
    Write-Host "3. Rotation logs du pont RAG" -ForegroundColor Cyan
    Write-Host "4. Supprimer fichiers temporaires" -ForegroundColor Cyan
    Write-Host "5. Rotation logs expires (7j)" -ForegroundColor Cyan
    Write-Host "A. TOUT (equivalent -Auto)" -ForegroundColor Cyan
    Write-Host "Q. Quitter" -ForegroundColor Cyan
    Write-Host ""

    $choice = Read-Host "Choisir une option"
    switch ($choice.ToUpper()) {
        "1" { Clear-PycacheDirectories }
        "2" { Clear-OrphanedPidFiles }
        "3" { Rotate-BridgeLogs }
        "4" { Clear-TempFiles }
        "5" { Clear-OldLogs -RetentionDays 7 }
        "A" {
            Clear-PycacheDirectories
            Clear-OrphanedPidFiles
            Rotate-BridgeLogs
            Clear-TempFiles
            Clear-OldLogs -RetentionDays 7
        }
        "Q" { Write-MLog "Maintenance annulee par l utilisateur."; exit 0 }
        default { Write-MLog "Option inconnue : $choice" -Level "WARNING" }
    }
}

Write-MaintenanceReport
Write-MLog "Maintenance terminee."
