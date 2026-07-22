Param(
    [string]$ConfigPath = "",
    [ValidateSet('auto','force','skip')]
    [string]$Mode = 'auto'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

[console]::InputEncoding = [console]::OutputEncoding = New-Object System.Text.UTF8Encoding

$StateFile = Join-Path $PSScriptRoot '.ingestion-state.json'
$IngestScript = Join-Path $PSScriptRoot 'ingest-workspace.ps1'

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $PSScriptRoot 'ingestion.config.json'
}

function Load-Config {
    param([string]$Path)
    if (-not (Test-Path $Path)) { throw "Config file not found: $Path" }
    return Get-Content $Path -Raw | ConvertFrom-Json
}

function Load-State {
    if (-not (Test-Path $StateFile)) { return @{ last_run = '0001-01-01T00:00:00Z' } }
    try { return (Get-Content $StateFile -Raw | ConvertFrom-Json) } catch { return @{ last_run = '0001-01-01T00:00:00Z' } }
}

function Save-State {
    param($state)
    $state | ConvertTo-Json -Depth 5 | Set-Content -Path $StateFile -Encoding UTF8
}

function Get-WorkspaceLastWrite {
    param($cfg)
    $root = Resolve-Path (Join-Path $PSScriptRoot $cfg.ingestion.sources.workspace_root)
    $excludes = $cfg.ingestion.sources.exclude
    $files = Get-ChildItem -Path $root -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object { 
            $p = $_.FullName
            $isExcluded = $false
            foreach ($exclude in $excludes) {
                $pattern = $exclude.Replace('**', '*').Replace('/', [IO.Path]::DirectorySeparatorChar)
                if ($p -like "*$pattern*") {
                    $isExcluded = $true
                    break
                }
            }
            -not ($p -like "*$($PSScriptRoot)*") -and -not $isExcluded
        }
    if (-not $files) { return (Get-Date '0001-01-01T00:00:00Z') }
    return ($files | Measure-Object LastWriteTime -Maximum).Maximum
}

function Should-Ingest {
    param($cfg, $state, $mode)
    if ($mode -eq 'force') { return $true }
    if ($mode -eq 'skip') { return $false }
    $lastRun = Get-Date $state.last_run
    $lastWrite = Get-WorkspaceLastWrite $cfg
    return ($lastWrite -gt $lastRun)
}

function Run-Ingest {
    param($cfg)
    if (-not (Test-Path $IngestScript)) { throw "Ingestion script not found: $IngestScript" }
    & powershell -File $IngestScript -Mode once -ConfigPath $ConfigPath
}

$cfg = Load-Config $ConfigPath
$state = Load-State

if (Should-Ingest $cfg $state $Mode) {
    Write-Host "[auto-ingest] Workspace modifié depuis le dernier run. Lancement ingestion..." -ForegroundColor Cyan
    Run-Ingest $cfg
    $state.last_run = (Get-Date).ToUniversalTime().ToString('o')
    Save-State $state
} else {
    Write-Host "[auto-ingest] Indexation déjà à jour. Rien à faire." -ForegroundColor Green
}
