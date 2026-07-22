Param(
    [ValidateSet('watch','once')]
    [string]$Mode = 'once',
    [string]$ConfigPath = "",
    [switch]$Force = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

[console]::InputEncoding = [console]::OutputEncoding = New-Object System.Text.UTF8Encoding

# Configuration du logging
$LogDir = Join-Path $PSScriptRoot "..\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$LogFile = Join-Path $LogDir "ingestion.log"
$ErrorLogFile = Join-Path $LogDir "error.log"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Écrire dans le fichier log
    try {
        Add-Content -Path $LogFile -Value $logEntry -ErrorAction SilentlyContinue
    } catch {
        # Si le fichier log est inaccessible, on continue quand même
    }
    
    # Écrire sur la console
    if ($Level -eq "WARN") {
        Write-Host $logEntry -ForegroundColor Yellow
    } elseif ($Level -eq "ERROR") {
        Write-Host $logEntry -ForegroundColor Red
    } elseif ($Message -match "✅|SUCCESS|trouvés") {
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
    } catch {
        # Si le fichier error log est inaccessible, on continue quand même
    }
    
    Write-Host $logEntry -ForegroundColor Red
}

function Resolve-SqliteExe {
    $sqliteFromEnv = $env:SQLITE3_PATH
    if (-not [string]::IsNullOrWhiteSpace($sqliteFromEnv) -and (Test-Path $sqliteFromEnv)) {
        return $sqliteFromEnv
    }

    $sqliteCmd = Get-Command sqlite3 -ErrorAction SilentlyContinue
    if ($sqliteCmd) {
        return $sqliteCmd.Source
    }

    $commonPaths = @(
        "D:\DATA-WEBMAN\tools\sqlite3.exe",
        "C:\tools\sqlite3.exe",
        "C:\sqlite\sqlite3.exe"
    )

    foreach ($candidate in $commonPaths) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return "python"
    }

    throw "sqlite3 et Python introuvables. Veuillez installer Python ou sqlite3."
}

$script:SqliteExe = Resolve-SqliteExe
Write-Log "sqlite3 utilisé: $script:SqliteExe"

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $PSScriptRoot "ingestion.config.json"
}

function Get-Config {
    param([string]$Path)
    if (-not (Test-Path $Path)) { throw "Config file not found: $Path" }
    return Get-Content $Path -Raw | ConvertFrom-Json
}

function Test-Exclusion {
    param($Path, $Excludes)
    if ($Path -match "ingestion\.log$") { return $true }
    if ($Path -match "\.db$") { return $true }
    if ($Path -match "\.db-(shm|wal)$") { return $true }
    if ($Path -match "[\\\\/]\.trae[\\\\/]") { return $true }
if ($Path -match "[\\\\/]\.agent[\\\\/]") { return $true }
    if ($Path -match "[\\\\/]\.windsurf[\\\\/]") { return $true }
    # Exclure memory-database SAUF le dossier logs pour le RAG
    if ($Path -match "[\\\\/]memory-database[\\\\/]") { 
        if ($Path -match "[\\\\/]logs[\\\\/]") { return $false }
        return $true 
    }
    if ($Path -match "[\\\\/]semantic-cache-data[\\\\/]") { return $true }
    if ($Path -match "[\\\\/]venv[\\\\/]") { return $true }
    if ($Path -match "[\\\\/]__pycache__[\\\\/]") { return $true }
    if ($Path -match "[\\\\/]\.pytest_cache[\\\\/]") { return $true }
    foreach ($pattern in $Excludes) {
        $normalized = $pattern.Replace('**', '*').Replace('/', [IO.Path]::DirectorySeparatorChar)
        if ($Path -like "*$normalized*") { return $true }
    }
    return $false
}

# Fonction centralisée pour les chemins des bases de données - MODE DUAL (LOCAL + GLOBAL)
function Get-DbPaths {
    param()
    
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    
    # --- LECTURE DU FICHIER .ENV ---
    $EnvFile = Join-Path $ProjectRoot.Path ".env"
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            if (-not $_.StartsWith('#')) {
                $parts = $_.Split('=', 2)
                if ($parts.Count -eq 2) {
                    $key = $parts[0].Trim()
                    $value = $parts[1].Trim()
                    if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
                        $value = $matches[1]
                    }
                    if ($key -eq "CASCADE_DB_ROOT" -and -not [string]::IsNullOrWhiteSpace($value)) {
                        $env:CASCADE_DB_ROOT = $value
                    }
                }
            }
        }
    }
    
    # --- MÉMOIRE UNIFIÉE V3 (Global + Local) ---
    # Lecture depuis .env
    $MemoryGlobal = "C:\DATA-WEBMAN\memory"
    $MemoryLocal = "C:\DATA-WEBMAN\memory\current_workspace"
    
    $EnvFile = Join-Path $ProjectRoot ".env"
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
    
    $GlobalDbPath = $MemoryGlobal
    $LocalDbPath = $MemoryLocal
    
    $projectId = Split-Path -Leaf $ProjectRoot.Path
    
    return @{
        # ARCHITECTURE V3: Global (patterns/rules/corrections) + Local (workspace actif)
        # Note: Les bases de données sont maintenant dans LOCAL (current_workspace)
        # GLOBAL (dossiers persistants)
        PatternsDir_Global   = Join-Path $GlobalDbPath "patterns"
        RulesDir_Global      = Join-Path $GlobalDbPath "rules"
        CorrectionsDir_Global= Join-Path $GlobalDbPath "corrections"
        CacheDb_Global       = Join-Path $GlobalDbPath "cache/runtime-cache.db"
        # LOCAL (bases de données du workspace actif)
        MemoryDb_Local       = Join-Path $LocalDbPath "graph/memory_mcp.db"
        GraphDb_Local        = Join-Path $LocalDbPath "graph/graph-memory.db"
        CacheDb_Local        = Join-Path $LocalDbPath "cache/runtime-cache.db"
        ZvecDb_Local         = Join-Path $LocalDbPath "vector/zvec/zvec.db"
        # Compatibilité: pointer vers LOCAL pour les anciens appels
        MemoryDb_Global      = Join-Path $LocalDbPath "graph/memory_mcp.db"
        GraphDb_Global       = Join-Path $LocalDbPath "graph/graph-memory.db"
        ZvecDb_Global        = Join-Path $LocalDbPath "vector/zvec/zvec.db"
        # Meta
        ProjectRoot = $ProjectRoot
        GlobalDbPath = $GlobalDbPath
        LocalDbPath = $LocalDbPath
        ProjectId = $projectId
        UseGlobal = $true
        GlobalRoot = $GlobalDbPath
    }
}

function Get-IngestionFiles {
    param($cfg)
    $root = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
    $maxBytes = $cfg.ingestion.sources.max_file_size_mb * 1MB
    Write-Log "Collecte des fichiers dans : $root"
    $files = Get-ChildItem -Path $root -Recurse -File -Force -ErrorAction SilentlyContinue
    $filtered = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
    foreach ($file in $files) {
        if (-not (Test-Exclusion $file.FullName $cfg.ingestion.sources.exclude) -and $file.Length -le $maxBytes) {
            $filtered.Add($file)
        }
    }
    Write-Log "$($filtered.Count) fichiers trouvés."
    return ,$filtered
}

function Build-Document {
    param($file, $cfg)
    $content = Get-Content $file.FullName -Raw
    $meta = [ordered]@{
        path = $file.FullName
        size_bytes = $file.Length
        modified = $file.LastWriteTimeUtc
        workspace = $cfg.ingestion.metadata.workspace
    }
    return [ordered]@{
        metadata = $meta
        content = $content
    }
}

function Get-StringSha256Hex {
    param([string]$Value)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    return ([System.BitConverter]::ToString($hash)).Replace('-', '').ToLowerInvariant()
}

function Invoke-SqliteScript {
    param(
        [string]$DbPath,
        [string[]]$SqlLines,
        [int]$MaxRetries = 3,
        [int]$RetryDelayMs = 100
    )
    if (-not (Test-Path $DbPath)) {
        $dir = Split-Path -Parent $DbPath
        if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        New-Item -ItemType File -Path $DbPath -Force | Out-Null
    }
    $script = ($SqlLines -join "`n") + "`n"
    
    # Retry mechanism pour les verrous SQLite
    $retryCount = 0
    $success = $false
    while (-not $success -and $retryCount -lt $MaxRetries) {
        try {
            if ($script:SqliteExe -eq "python") {
                python -c "import sqlite3, sys; conn=sqlite3.connect(sys.argv[1]); conn.executescript(sys.argv[2]); conn.commit(); conn.close()" $DbPath $script 2>&1 | Out-Null
            } else {
                $script | & $script:SqliteExe $DbPath 2>&1 | Out-Null
            }
            if ($LASTEXITCODE -eq 0) {
                $success = $true
            } else {
                $retryCount++
                if ($retryCount -lt $MaxRetries) {
                    Write-Log "SQLite verrouillé (retry $retryCount/$MaxRetries): $DbPath"
                    Start-Sleep -Milliseconds $RetryDelayMs
                }
            }
        } catch {
            $retryCount++
            if ($retryCount -lt $MaxRetries) {
                Write-Log "SQLite erreur (retry $retryCount/$MaxRetries): $_"
                Start-Sleep -Milliseconds $RetryDelayMs
            }
        }
    }
    
    if (-not $success) {
        Write-ErrorLog "sqlite3/python a échoué après $MaxRetries retries pour: $DbPath"
        throw "sqlite3/python a échoué pour: $DbPath"
    }
}

function Initialize-DbSchemas {
    param(
        [string]$MemoryDb,
        [string]$GraphDb,
        [string]$CacheDb,
        [string]$ZvecDb
    )

    Invoke-SqliteScript -DbPath $MemoryDb -SqlLines @(
        "PRAGMA journal_mode=WAL;",
        "CREATE TABLE IF NOT EXISTS entities (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, entityType TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);",
        "CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_id INTEGER NOT NULL, content TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE);",
        "CREATE TABLE IF NOT EXISTS relations (id INTEGER PRIMARY KEY AUTOINCREMENT, from_entity TEXT NOT NULL, to_entity TEXT NOT NULL, relationType TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(from_entity, to_entity, relationType));",
        "CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations(entity_id);",
        "CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity);",
        "CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity);"
    )

    Invoke-SqliteScript -DbPath $GraphDb -SqlLines @(
        "PRAGMA journal_mode=WAL;",
        "CREATE TABLE IF NOT EXISTS edges (from_id TEXT NOT NULL, to_id TEXT NOT NULL, type TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(from_id, to_id, type));"
    )

    Invoke-SqliteScript -DbPath $CacheDb -SqlLines @(
        "PRAGMA journal_mode=WAL;",
        "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);"
    )

    $vectorSchema = @(
        "PRAGMA journal_mode=WAL;",
        "CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL, content BLOB NOT NULL, updated_at TEXT NOT NULL);"
    )
    Invoke-SqliteScript -DbPath $ZvecDb -SqlLines $vectorSchema
}

function Get-StateMap {
    param(
        [string]$StatePath
    )

    $map = @{}
    if (-not (Test-Path $StatePath)) { return $map }

    $raw = Get-Content -Path $StatePath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { return $map }

    $state = $raw | ConvertFrom-Json
    if (-not $state) { return $map }
    if (-not $state.files) { return $map }

    foreach ($prop in $state.files.PSObject.Properties) {
        $rel = $prop.Name
        $entry = $prop.Value
        if (-not $entry) { continue }

        $map[$rel] = @{
            size = [int64]$entry.size
            mtime_utc = [int64]$entry.mtime_utc
            sha256 = [string]$entry.sha256
        }
    }

    return $map
}

function Save-StateMap {
    param(
        [string]$StatePath,
        [string]$ProjectId,
        [hashtable]$StateMap
    )

    $filesObj = [ordered]@{}
    foreach ($rel in ($StateMap.Keys | Sort-Object)) {
        $e = $StateMap[$rel]
        $filesObj[$rel] = [ordered]@{
            size = [int64]$e.size
            mtime_utc = [int64]$e.mtime_utc
            sha256 = [string]$e.sha256
        }
    }

    $obj = [ordered]@{
        version = "1.0"
        project_id = $ProjectId
        updated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        files = $filesObj
    }

    $json = $obj | ConvertTo-Json -Depth 8
    Set-Content -Path $StatePath -Value $json -Encoding UTF8
}

function Get-RelPath {
    param(
        [string]$FullPath,
        [string]$ProjectRoot
    )

    if ([string]::IsNullOrWhiteSpace($FullPath)) { return $null }
    if (-not $FullPath.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) { return $null }
    return $FullPath.Substring($ProjectRoot.Length).TrimStart('\','/')
}

function Build-DeletionSql {
    param(
        [string]$WorkspaceEntityId,
        [string[]]$RelPaths
    )

    $memorySql = New-Object System.Collections.Generic.List[string]
    $graphSql = New-Object System.Collections.Generic.List[string]
    $zvecSql = New-Object System.Collections.Generic.List[string]

    $memorySql.Add("BEGIN;")
    $graphSql.Add("BEGIN;")
    $zvecSql.Add("BEGIN;")

    foreach ($rel in $RelPaths) {
        if ([string]::IsNullOrWhiteSpace($rel)) { continue }
        $fileIdHash = Get-StringSha256Hex $rel
        $fileEntityId = "file:$fileIdHash"

        $memorySql.Add("DELETE FROM relations WHERE from_entity='$WorkspaceEntityId' AND to_entity='$fileEntityId' AND relationType='contains';")
        $memorySql.Add("DELETE FROM observations WHERE entity_id=(SELECT id FROM entities WHERE name='$fileEntityId');")
        $memorySql.Add("DELETE FROM entities WHERE name='$fileEntityId';")

        $graphSql.Add("DELETE FROM edges WHERE from_id='$WorkspaceEntityId' AND to_id='$fileEntityId' AND type='contains';")

        $zvecSql.Add("DELETE FROM documents WHERE id='$fileEntityId';")
    }

    $memorySql.Add("COMMIT;")
    $graphSql.Add("COMMIT;")
    $zvecSql.Add("COMMIT;")

    return [ordered]@{
        memory = $memorySql
        graph = $graphSql
        zvec = $zvecSql
    }
}

function Update-CacheKvs {
    param(
        [string]$CacheDb,
        [int]$TotalFileCount
    )

    $nowIso = (Get-Date).ToUniversalTime().ToString('o')
    $cacheSql = @(
        "BEGIN;",
        "INSERT INTO kv (key, value, updated_at) VALUES ('last_ingest_utc', '$nowIso', '$nowIso') ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;",
        "INSERT INTO kv (key, value, updated_at) VALUES ('file_count', '$TotalFileCount', '$nowIso') ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;",
        "COMMIT;"
    )
    Invoke-SqliteScript -DbPath $CacheDb -SqlLines $cacheSql
}

function Sync-Via-Python-Cli {
    param(
        [string]$FilePath
    )
    
    $cliPath = Join-Path $PSScriptRoot "..\\rag\\cli.py"
    if (-not (Test-Path $cliPath)) {
        Write-Log "CLI Python non trouvee a : $cliPath" "WARN"
        return $false
    }

    try {
        # Appel de la CLI Python pour l'ingestion intelligente (Chunking, Tagging, Embedding)
        # IMPORTANT: Non-fatale — un échec vectoriel ne doit pas tuer le watcher SQLite
        $errOutput = python $cliPath ingest $FilePath 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            Write-Log "[WARN] Ingestion vectorielle non-critique échouée pour: $(Split-Path -Leaf $FilePath) (exit $LASTEXITCODE)" "WARN"
            if (-not [string]::IsNullOrWhiteSpace($errOutput)) {
                # Log seulement la dernière ligne pour éviter le spam
                $lastLine = ($errOutput -split "`n" | Where-Object { $_.Trim() } | Select-Object -Last 1)
                Write-Log "[WARN] Détail: $lastLine" "WARN"
            }
            return $false
        }
        return $true
    } catch {
        Write-Log "[WARN] Sync-Via-Python-Cli exception (non-fatale): $_" "WARN"
        return $false
    }
}

function Invoke-IngestionDual {
    param(
        $cfg,
        $incrementalFiles = $null,
        [int]$TotalFileCount = -1,
        $dbPaths = $null
    )
    
    $logFile = Join-Path $PSScriptRoot "ingestion.log"
    
    if (-not $dbPaths) {
        $dbPaths = Get-DbPaths
    }
    
    $ProjectRoot = $dbPaths.ProjectRoot
    $projectId = $dbPaths.ProjectId
    
    # Chemins GLOBAL
    $memoryDbGlobal = $dbPaths.MemoryDb_Global
    $graphDbGlobal = $dbPaths.GraphDb_Global
    $cacheDbGlobal = $dbPaths.CacheDb_Global
    $zvecDbGlobal = $dbPaths.ZvecDb_Global
    
    # Chemins LOCAL
    $memoryDbLocal = $dbPaths.MemoryDb_Local
    $graphDbLocal = $dbPaths.GraphDb_Local
    $cacheDbLocal = $dbPaths.CacheDb_Local
    $zvecDbLocal = $dbPaths.ZvecDb_Local
    
    Write-Log "[ingest] Mode DUAL - Global: $($dbPaths.GlobalDbPath)"
    Write-Log "[ingest] Mode DUAL - Local: $($dbPaths.LocalDbPath)"

    # Assurer les schémas dans les deux bases
    Initialize-DbSchemas -MemoryDb $memoryDbGlobal -GraphDb $graphDbGlobal -CacheDb $cacheDbGlobal -ZvecDb $zvecDbGlobal
    Initialize-DbSchemas -MemoryDb $memoryDbLocal -GraphDb $graphDbLocal -CacheDb $cacheDbLocal -ZvecDb $zvecDbLocal

    $files = if ($incrementalFiles) { $incrementalFiles } else { Get-IngestionFiles $cfg }
    $nowIso = (Get-Date).ToUniversalTime().ToString('o')
    $workspaceEntityId = "workspace:$projectId"
    $maxContentBytes = 262144
    $filesCount = 0
    if ($files -is [array]) { $filesCount = $files.Count }
    elseif ($null -ne $files) { $filesCount = 1 }

    $cacheCount = if ($TotalFileCount -ge 0) { $TotalFileCount } else { $filesCount }

    $stateUpdates = @{}

    # SQL pour GLOBAL
    $memorySqlGlobal = New-Object System.Collections.Generic.List[string]
    $graphSqlGlobal = New-Object System.Collections.Generic.List[string]
    $cacheSqlGlobal = New-Object System.Collections.Generic.List[string]
    $zvecSqlGlobal = New-Object System.Collections.Generic.List[string]

    # SQL pour LOCAL
    $memorySqlLocal = New-Object System.Collections.Generic.List[string]
    $graphSqlLocal = New-Object System.Collections.Generic.List[string]
    $cacheSqlLocal = New-Object System.Collections.Generic.List[string]
    $zvecSqlLocal = New-Object System.Collections.Generic.List[string]

    $memorySqlGlobal.Add("BEGIN;")
    $graphSqlGlobal.Add("BEGIN;")
    $cacheSqlGlobal.Add("BEGIN;")
    $zvecSqlGlobal.Add("BEGIN;")

    $memorySqlLocal.Add("BEGIN;")
    $graphSqlLocal.Add("BEGIN;")
    $cacheSqlLocal.Add("BEGIN;")
    $zvecSqlLocal.Add("BEGIN;")

    $memorySqlGlobal.Add("INSERT OR IGNORE INTO entities (name, entityType) VALUES ('$workspaceEntityId', 'workspace');")
    $memorySqlLocal.Add("INSERT OR IGNORE INTO entities (name, entityType) VALUES ('$workspaceEntityId', 'workspace');")

    # Déterminer quels fichiers traiter
    $filesToProcess = if ($incrementalFiles) { 
        $incrementalFiles 
    } else { 
        Get-IngestionFiles $cfg 
    }

    foreach ($file in $filesToProcess) {
        $full = $file.FullName
        if (-not $full.StartsWith($ProjectRoot.Path, [System.StringComparison]::OrdinalIgnoreCase)) { continue }
        $rel = $full.Substring($ProjectRoot.Path.Length).TrimStart('\','/')
        $fileIdHash = Get-StringSha256Hex $rel
        $fileEntityId = "file:$fileIdHash"

        $bytes = try {
            $stream = [System.IO.File]::Open($full, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $len = $stream.Length
            $data = New-Object byte[] $len
            $readLen = $stream.Read($data, 0, $len)
            $stream.Close()
            if ($readLen -lt $len) { $data = $data[0..($readLen-1)] }
            $data
        } catch {
            Write-Log "Impossible d'accéder au fichier : $rel" "WARN"
            continue
        }
        if ($null -eq $bytes) { continue }
        $bytesLen = 0
        if ($bytes -is [array]) { $bytesLen = $bytes.Count }
        elseif ($null -ne $bytes) { $bytesLen = 1 }

        if ($bytesLen -gt $maxContentBytes) { $bytes = $bytes[0..($maxContentBytes-1)] }
        $contentHex = ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
        $sha256 = try { (Get-FileHash -Algorithm SHA256 -Path $full).Hash.ToLowerInvariant() } catch { continue }

        # Insertions GLOBAL
        $memorySqlGlobal.Add("INSERT OR IGNORE INTO entities (name, entityType) VALUES ('$fileEntityId', 'file');")
        $memorySqlGlobal.Add("DELETE FROM observations WHERE entity_id=(SELECT id FROM entities WHERE name='$fileEntityId');")
        $memorySqlGlobal.Add("INSERT INTO observations (entity_id, content) VALUES ((SELECT id FROM entities WHERE name='$fileEntityId'), '$contentHex');")
        $memorySqlGlobal.Add("INSERT OR IGNORE INTO relations (from_entity, to_entity, relationType) VALUES ('$workspaceEntityId', '$fileEntityId', 'contains');")
        $graphSqlGlobal.Add("INSERT INTO edges (from_id, to_id, type, created_at) VALUES ('$workspaceEntityId', '$fileEntityId', 'contains', '$nowIso') ON CONFLICT(from_id, to_id, type) DO UPDATE SET created_at=excluded.created_at;")

        # Insertions LOCAL (mêmes données)
        $memorySqlLocal.Add("INSERT OR IGNORE INTO entities (name, entityType) VALUES ('$fileEntityId', 'file');")
        $memorySqlLocal.Add("DELETE FROM observations WHERE entity_id=(SELECT id FROM entities WHERE name='$fileEntityId');")
        $memorySqlLocal.Add("INSERT INTO observations (entity_id, content) VALUES ((SELECT id FROM entities WHERE name='$fileEntityId'), '$contentHex');")
        $memorySqlLocal.Add("INSERT OR IGNORE INTO relations (from_entity, to_entity, relationType) VALUES ('$workspaceEntityId', '$fileEntityId', 'contains');")
        $graphSqlLocal.Add("INSERT INTO edges (from_id, to_id, type, created_at) VALUES ('$workspaceEntityId', '$fileEntityId', 'contains', '$nowIso') ON CONFLICT(from_id, to_id, type) DO UPDATE SET created_at=excluded.created_at;")

        $stateUpdates[$rel] = @{
            size = [int64]$file.Length
            mtime_utc = [int64]$file.LastWriteTimeUtc.Ticks
            sha256 = $sha256
        }
    }

    # Cache GLOBAL uniquement (pas besoin de dupliquer le cache)
    $cacheSqlGlobal.Add("INSERT INTO kv (key, value, updated_at) VALUES ('last_ingest_utc', '$nowIso', '$nowIso') ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;")
    $cacheSqlGlobal.Add("INSERT INTO kv (key, value, updated_at) VALUES ('file_count', '$cacheCount', '$nowIso') ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;")

    $memorySqlGlobal.Add("COMMIT;")
    $graphSqlGlobal.Add("COMMIT;")
    $cacheSqlGlobal.Add("COMMIT;")
    $zvecSqlGlobal.Add("COMMIT;")

    $memorySqlLocal.Add("COMMIT;")
    $graphSqlLocal.Add("COMMIT;")
    $cacheSqlLocal.Add("COMMIT;")
    $zvecSqlLocal.Add("COMMIT;")

    # Exécution GLOBAL
    Invoke-SqliteScript -DbPath $memoryDbGlobal -SqlLines $memorySqlGlobal.ToArray()
    Invoke-SqliteScript -DbPath $graphDbGlobal -SqlLines $graphSqlGlobal.ToArray()
    Invoke-SqliteScript -DbPath $cacheDbGlobal -SqlLines $cacheSqlGlobal.ToArray()
    Invoke-SqliteScript -DbPath $zvecDbGlobal -SqlLines $zvecSqlGlobal.ToArray()

    # Exécution LOCAL
    Invoke-SqliteScript -DbPath $memoryDbLocal -SqlLines $memorySqlLocal.ToArray()
    Invoke-SqliteScript -DbPath $graphDbLocal -SqlLines $graphSqlLocal.ToArray()
    Invoke-SqliteScript -DbPath $cacheDbLocal -SqlLines $cacheSqlLocal.ToArray()
    Invoke-SqliteScript -DbPath $zvecDbLocal -SqlLines $zvecSqlLocal.ToArray()

    $elapsed = (Get-Date) - [datetime]$nowIso
    $msg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [ingest] ✅ Synchronisation DUAL reussie. Fichiers modifies=$filesCount / Total=$cacheCount (Duree globale environ $($elapsed.TotalSeconds.ToString('F2'))s)"
    Write-Log $msg
    Add-Content -Path $logFile -Value $msg -ErrorAction SilentlyContinue

    return $stateUpdates
}

function Invoke-Ingestion {
    param(
        $cfg,
        $incrementalFiles = $null,
        [int]$TotalFileCount = -1
    )
    
    $logFile = Join-Path $PSScriptRoot "ingestion.log"
    
    # Utiliser la fonction centralisée pour les chemins
    $dbPaths = Get-DbPaths
    $ProjectRoot = $dbPaths.ProjectRoot
    $projectId = $dbPaths.ProjectId
    
    # Utiliser les chemins LOCAL pour l'ingestion
    $memoryDb = $dbPaths.MemoryDb_Local
    $graphDb = $dbPaths.GraphDb_Local
    $cacheDb = $dbPaths.CacheDb_Local
    $zvecDb = $dbPaths.ZvecDb_Local
    
    if ($dbPaths.UseGlobal) {
        Write-Log "Mode DUAL - GLOBAL: $($dbPaths.GlobalDbPath) LOCAL: $($dbPaths.LocalDbPath)"
    } else {
        Write-Log "Mode LOCAL - DbPath: $($dbPaths.LocalDbPath)"
    }

    # Assurer les schémas
    Initialize-DbSchemas -MemoryDb $memoryDb -GraphDb $graphDb -CacheDb $cacheDb -ZvecDb $zvecDb

    $files = if ($incrementalFiles) { $incrementalFiles } else { Get-IngestionFiles $cfg }
    $nowIso = (Get-Date).ToUniversalTime().ToString('o')
    $workspaceEntityId = "workspace:$projectId"
    $maxContentBytes = 262144
    $filesCount = 0
    if ($files -is [array]) { $filesCount = $files.Count }
    elseif ($null -ne $files) { $filesCount = 1 }

    $cacheCount = if ($TotalFileCount -ge 0) { $TotalFileCount } else { $filesCount }

    $stateUpdates = @{}

    $memorySql = New-Object System.Collections.Generic.List[string]
    $graphSql = New-Object System.Collections.Generic.List[string]
    $cacheSql = New-Object System.Collections.Generic.List[string]
    $zvecSql = New-Object System.Collections.Generic.List[string]

    $memorySql.Add("BEGIN;")
    $graphSql.Add("BEGIN;")
    $cacheSql.Add("BEGIN;")
    $zvecSql.Add("BEGIN;")

    $memorySql.Add("INSERT OR IGNORE INTO entities (name, entityType) VALUES ('$workspaceEntityId', 'workspace');")

    foreach ($file in $files) {
        $full = $file.FullName
        if (-not $full.StartsWith($ProjectRoot.Path, [System.StringComparison]::OrdinalIgnoreCase)) { continue }
        $rel = $full.Substring($ProjectRoot.Path.Length).TrimStart('\','/')
        $fileIdHash = Get-StringSha256Hex $rel
        $fileEntityId = "file:$fileIdHash"

        $bytes = try {
            $stream = [System.IO.File]::Open($full, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $len = $stream.Length
            $data = New-Object byte[] $len
            $readLen = $stream.Read($data, 0, $len)
            $stream.Close()
            if ($readLen -lt $len) { $data = $data[0..($readLen-1)] }
            $data
        } catch {
            Write-Log "Impossible d'accéder au fichier (verrouillé par un autre processus) : $rel" "WARN"
            continue
        }
        if ($null -eq $bytes) { continue }
        $bytesLen = 0
        if ($bytes -is [array]) { $bytesLen = $bytes.Count }
        elseif ($null -ne $bytes) { $bytesLen = 1 } # Cas rare d'un seul octet non wrappé en tableau

        if ($bytesLen -gt $maxContentBytes) { $bytes = $bytes[0..($maxContentBytes-1)] }
        $contentHex = ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
        $sha256 = try { (Get-FileHash -Algorithm SHA256 -Path $full).Hash.ToLowerInvariant() } catch { continue }

        $memorySql.Add("INSERT OR IGNORE INTO entities (name, entityType) VALUES ('$fileEntityId', 'file');")
        $memorySql.Add("DELETE FROM observations WHERE entity_id=(SELECT id FROM entities WHERE name='$fileEntityId');")
        $memorySql.Add("INSERT INTO observations (entity_id, content) VALUES ((SELECT id FROM entities WHERE name='$fileEntityId'), '$contentHex');")
        $memorySql.Add("INSERT OR IGNORE INTO relations (from_entity, to_entity, relationType) VALUES ('$workspaceEntityId', '$fileEntityId', 'contains');")

        $graphSql.Add("INSERT INTO edges (from_id, to_id, type, created_at) VALUES ('$workspaceEntityId', '$fileEntityId', 'contains', '$nowIso') ON CONFLICT(from_id, to_id, type) DO UPDATE SET created_at=excluded.created_at;")
        
        # L'ingestion vectorielle est maintenant gérée globalement ou de manière incrémentale
        # Sync-Via-Python-Cli -FilePath $full (Désactivé ici pour performance)

        $stateUpdates[$rel] = @{
            size = [int64]$file.Length
            mtime_utc = [int64]$file.LastWriteTimeUtc.Ticks
            sha256 = $sha256
        }
    }

    $cacheSql.Add("INSERT INTO kv (key, value, updated_at) VALUES ('last_ingest_utc', '$nowIso', '$nowIso') ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;")
    $cacheSql.Add("INSERT INTO kv (key, value, updated_at) VALUES ('file_count', '$cacheCount', '$nowIso') ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;")

    $memorySql.Add("COMMIT;")
    $graphSql.Add("COMMIT;")
    $cacheSql.Add("COMMIT;")
    $zvecSql.Add("COMMIT;")

    Invoke-SqliteScript -DbPath $memoryDb -SqlLines $memorySql.ToArray()
    Invoke-SqliteScript -DbPath $graphDb -SqlLines $graphSql.ToArray()
    Invoke-SqliteScript -DbPath $cacheDb -SqlLines $cacheSql.ToArray()
    Invoke-SqliteScript -DbPath $zvecDb -SqlLines $zvecSql.ToArray()

    # Ingestion vectorielle GLOBALE si c'est une ingestion complète (performance ++ )
    if (-not $incrementalFiles) {
        Write-Log "Lancement de l'ingestion vectorielle globale (Python CLI)..."
        Sync-Via-Python-Cli -FilePath $ProjectRoot.Path
    } else {
        # Pour les fichiers incrémentaux, on peut soit les faire un par un, soit globalement sur la liste.
        # Ici on reste sur un par un pour la précision du watch mode.
        foreach ($file in $incrementalFiles) {
            Sync-Via-Python-Cli -FilePath $file.FullName
        }
    }

    $msg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [ingest] ✅ Synchronisation reussie. Fichiers modifies=$filesCount / Total=$cacheCount"
    Write-Log $msg
    Add-Content -Path $logFile -Value $msg -ErrorAction SilentlyContinue

    # La synchronisation est maintenant faite fichier par fichier via Sync-Via-Python-Cli

    return $stateUpdates
}

$config = Get-Config $ConfigPath
$global:config = $config

if ($Mode -eq 'watch') {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
    $global:projectRoot = $projectRoot
    $projectId = Split-Path -Leaf $projectRoot
    $statePath = Join-Path $PSScriptRoot "ingestion.state.json"
    $global:stateMap = Get-StateMap -StatePath $statePath

    if ($Force -or $global:stateMap.Count -eq 0) {
        $allFiles = Get-IngestionFiles $config
        $dbPaths = Get-DbPaths
        $updates = Invoke-IngestionDual $config $allFiles $allFiles.Count $dbPaths
        if ($null -ne $updates -and $updates -is [System.Collections.IDictionary]) {
            foreach ($k in $updates.Keys) { $global:stateMap[$k] = $updates[$k] }
        }
        Save-StateMap -StatePath $statePath -ProjectId $projectId -StateMap $global:stateMap
    }

    $global:pendingIngest = $false
    $global:lastEventUtc = (Get-Date).ToUniversalTime()
    $global:pendingChanged = New-Object 'System.Collections.Concurrent.ConcurrentDictionary[string, byte]'
    $global:pendingDeleted = New-Object 'System.Collections.Concurrent.ConcurrentDictionary[string, byte]'

    Write-Log "Mode watch activé pour: $projectRoot"

    $watcher = New-Object System.IO.FileSystemWatcher
    $watcher.Path = $projectRoot
    $watcher.Filter = '*'
    $watcher.IncludeSubdirectories = $true
    $watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName, LastWrite, Size, DirectoryName'
    $watcher.InternalBufferSize = 65536

    $handler = {
        try {
            $fsEventArgs = $Event.SourceEventArgs
            if (-not $fsEventArgs) { return }
            $changeType = [string]$fsEventArgs.ChangeType
            $fullPath = [string]$fsEventArgs.FullPath

            # Empêche la boucle infinie de logs
            if (-not [string]::IsNullOrWhiteSpace($fullPath) -and (Test-Exclusion $fullPath $global:config.ingestion.sources.exclude)) {
                return
            }

            if ($changeType -eq 'Renamed') {
                $old = [string]$fsEventArgs.OldFullPath
                $new = [string]$fsEventArgs.FullPath
                if (-not [string]::IsNullOrWhiteSpace($old)) {
                    $oldRel = Get-RelPath -FullPath $old -ProjectRoot $global:projectRoot
                    if ($oldRel) { 
                        $null = $global:pendingDeleted.TryAdd($oldRel, 1)
                        Write-Log "Deleted (rename): $oldRel"
                    }
                }
                if (-not [string]::IsNullOrWhiteSpace($new)) {
                    $newRel = Get-RelPath -FullPath $new -ProjectRoot $global:projectRoot
                    $null = $global:pendingChanged.TryAdd($new, 1)
                    Write-Log "Changed (rename): $newRel"
                }
            } elseif ($changeType -eq 'Deleted') {
                if (-not [string]::IsNullOrWhiteSpace($fullPath)) {
                    $rel = Get-RelPath -FullPath $fullPath -ProjectRoot $global:projectRoot
                    if ($rel) { 
                        $null = $global:pendingDeleted.TryAdd($rel, 1)
                        Write-Log "Deleted: $rel"
                    }
                }
            } else {
                if ([string]::IsNullOrWhiteSpace($fullPath)) { return }
                $null = $global:pendingChanged.TryAdd($fullPath, 1)
                $rel = Get-RelPath -FullPath $fullPath -ProjectRoot $global:projectRoot
                # Write-Log "Changed: $rel" # Optionnel pour ne pas polluer les logs
            }

            $global:pendingIngest = $true
            $global:lastEventUtc = (Get-Date).ToUniversalTime()
        } catch {
            Write-ErrorLog "ERROR in handler: $_"
        }
    }

    # Error handler pour le watcher
    $errorHandler = {
        Write-ErrorLog "ERROR: FileSystemWatcher error - $_"
    }

    Write-Log "Enregistrement des event handlers..."
    Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $handler -SourceIdentifier "watch.changed" | Out-Null
    Register-ObjectEvent -InputObject $watcher -EventName Created -Action $handler -SourceIdentifier "watch.created" | Out-Null
    Register-ObjectEvent -InputObject $watcher -EventName Deleted -Action $handler -SourceIdentifier "watch.deleted" | Out-Null
    Register-ObjectEvent -InputObject $watcher -EventName Renamed -Action $handler -SourceIdentifier "watch.renamed" | Out-Null
    Register-ObjectEvent -InputObject $watcher -EventName Error -Action $errorHandler -SourceIdentifier "watch.error" | Out-Null
    
    $watcher.EnableRaisingEvents = $true
    Write-Log "FileSystemWatcher actif"

    Write-Log "Démarrage de la boucle de surveillance..."
    while ($true) {
        if ($global:pendingIngest) {
            $sinceLast = (Get-Date).ToUniversalTime() - $global:lastEventUtc
            Write-Log "Pending ingest, sinceLast: $($sinceLast.TotalMilliseconds)ms"
            if ($sinceLast.TotalMilliseconds -ge 1500) {
                $global:pendingIngest = $false
                $changedPaths = @($global:pendingChanged.Keys)
                $deletedRels = @($global:pendingDeleted.Keys)
                Write-Log "Débouncing terminé, traitement de $($changedPaths.Count) fichiers modifiés"

                foreach ($p in $changedPaths) { $null = $global:pendingChanged.TryRemove($p, [ref]([byte]0)) }
                foreach ($r in $deletedRels) { $null = $global:pendingDeleted.TryRemove($r, [ref]([byte]0)) }

                if ($deletedRels.Count -gt 0) {
                    $dbPaths = Get-DbPaths
                    # Suppression GLOBAL
                    Initialize-DbSchemas -MemoryDb $dbPaths.MemoryDb_Global -GraphDb $dbPaths.GraphDb_Global -CacheDb $dbPaths.CacheDb_Global -ZvecDb $dbPaths.ZvecDb_Global
                    $workspaceEntityId = "workspace:$projectId"
                    $delSql = Build-DeletionSql -WorkspaceEntityId $workspaceEntityId -RelPaths $deletedRels
                    Invoke-SqliteScript -DbPath $dbPaths.MemoryDb_Global -SqlLines $delSql.memory.ToArray()
                    Invoke-SqliteScript -DbPath $dbPaths.GraphDb_Global -SqlLines $delSql.graph.ToArray()
                    Invoke-SqliteScript -DbPath $dbPaths.ZvecDb_Global -SqlLines $delSql.zvec.ToArray()
                    # Suppression LOCAL
                    Initialize-DbSchemas -MemoryDb $dbPaths.MemoryDb_Local -GraphDb $dbPaths.GraphDb_Local -CacheDb $dbPaths.CacheDb_Local -ZvecDb $dbPaths.ZvecDb_Local
                    Invoke-SqliteScript -DbPath $dbPaths.MemoryDb_Local -SqlLines $delSql.memory.ToArray()
                    Invoke-SqliteScript -DbPath $dbPaths.GraphDb_Local -SqlLines $delSql.graph.ToArray()
                    Invoke-SqliteScript -DbPath $dbPaths.ZvecDb_Local -SqlLines $delSql.zvec.ToArray()
                    foreach ($rel in $deletedRels) { $null = $global:stateMap.Remove($rel) }
                    Update-CacheKvs -CacheDb $dbPaths.CacheDb_Global -TotalFileCount $global:stateMap.Count
                }

                $fileInfos = New-Object System.Collections.Generic.List[System.IO.FileInfo]
                $maxBytes = $config.ingestion.sources.max_file_size_mb * 1MB
                foreach ($p in $changedPaths) {
                    if (-not (Test-Path $p)) { continue }
                    $item = Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
                    if (-not $item) { continue }
                    if ($item.PSIsContainer) { continue }
                    if ($item.Length -gt $maxBytes) { continue }
                    $rel = Get-RelPath -FullPath $item.FullName -ProjectRoot $projectRoot
                    if (-not $rel) { continue }

                    $prev = $global:stateMap[$rel]
                    $mtimeTicks = [int64]$item.LastWriteTimeUtc.Ticks
                    if ($prev -and [int64]$prev.size -eq [int64]$item.Length -and [int64]$prev.mtime_utc -eq $mtimeTicks) { continue }

                    $fileInfos.Add([System.IO.FileInfo]$item.FullName)
                }

                if ($fileInfos.Count -gt 0) {
                    Write-Log "Ingestion de $($fileInfos.Count) fichiers..."
                    $dbPaths = Get-DbPaths
                    $updates = Invoke-Ingestion $config $fileInfos $global:stateMap.Count
                    if ($null -ne $updates -and $updates -is [System.Collections.IDictionary]) {
                        foreach ($k in $updates.Keys) { $global:stateMap[$k] = $updates[$k] }
                    }
                    Save-StateMap -StatePath $statePath -ProjectId $projectId -StateMap $global:stateMap
                    Write-Log "Ingestion terminée"
                } elseif ($deletedRels.Count -gt 0) {
                    Save-StateMap -StatePath $statePath -ProjectId $projectId -StateMap $global:stateMap
                }
            }
        }
        Start-Sleep -Milliseconds 250
    }
} else {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
    $projectId = Split-Path -Leaf $projectRoot
    $statePath = Join-Path $PSScriptRoot "ingestion.state.json"
    $stateMap = Get-StateMap -StatePath $statePath

    $allFiles = Get-IngestionFiles $config
    $currentRelSet = New-Object 'System.Collections.Generic.HashSet[string]'
    $changedFiles = New-Object System.Collections.Generic.List[System.IO.FileInfo]
    foreach ($file in $allFiles) {
        $rel = Get-RelPath -FullPath $file.FullName -ProjectRoot $projectRoot
        if (-not $rel) { continue }
        $null = $currentRelSet.Add($rel)
        $prev = $stateMap[$rel]
        $mtimeTicks = [int64]$file.LastWriteTimeUtc.Ticks
        if (-not $prev -or [int64]$prev.size -ne [int64]$file.Length -or [int64]$prev.mtime_utc -ne $mtimeTicks) {
            $changedFiles.Add([System.IO.FileInfo]$file.FullName)
        }
    }

    $deletedRels = @()
    foreach ($rel in $stateMap.Keys) {
        if (-not $currentRelSet.Contains($rel)) { $deletedRels += $rel }
    }

    $dbPaths = Get-DbPaths
    # Schémas GLOBAL
    Initialize-DbSchemas -MemoryDb $dbPaths.MemoryDb_Global -GraphDb $dbPaths.GraphDb_Global -CacheDb $dbPaths.CacheDb_Global -ZvecDb $dbPaths.ZvecDb_Global
    # Schémas LOCAL
    Initialize-DbSchemas -MemoryDb $dbPaths.MemoryDb_Local -GraphDb $dbPaths.GraphDb_Local -CacheDb $dbPaths.CacheDb_Local -ZvecDb $dbPaths.ZvecDb_Local

    if ($deletedRels.Count -gt 0) {
        $workspaceEntityId = "workspace:$projectId"
        $delSql = Build-DeletionSql -WorkspaceEntityId $workspaceEntityId -RelPaths $deletedRels
        # Suppression GLOBAL
        Invoke-SqliteScript -DbPath $dbPaths.MemoryDb_Global -SqlLines $delSql.memory.ToArray()
        Invoke-SqliteScript -DbPath $dbPaths.GraphDb_Global -SqlLines $delSql.graph.ToArray()
        Invoke-SqliteScript -DbPath $dbPaths.ZvecDb_Global -SqlLines $delSql.zvec.ToArray()
        # Suppression LOCAL
        Invoke-SqliteScript -DbPath $dbPaths.MemoryDb_Local -SqlLines $delSql.memory.ToArray()
        Invoke-SqliteScript -DbPath $dbPaths.GraphDb_Local -SqlLines $delSql.graph.ToArray()
        Invoke-SqliteScript -DbPath $dbPaths.ZvecDb_Local -SqlLines $delSql.zvec.ToArray()
        foreach ($rel in $deletedRels) { $null = $stateMap.Remove($rel) }
    }

    if ($Force -or $changedFiles.Count -gt 0) {
        # En mode Force, ingérer tous les fichiers, sinon seulement les modifiés
        $filesToIngest = if ($Force) { $allFiles } else { $changedFiles }
        # Ingestion en DUAL-MODE
        $updates = Invoke-IngestionDual $config $filesToIngest $allFiles.Count $dbPaths
        if ($null -ne $updates -and $updates -is [System.Collections.IDictionary]) {
            foreach ($k in $updates.Keys) { $global:stateMap[$k] = $updates[$k] }
        }
    } else {
        Update-CacheKvs -CacheDb $dbPaths.CacheDb_Global -TotalFileCount $allFiles.Count
        Write-Log "Aucun changement détecté. total=$($allFiles.Count)"
    }

    Save-StateMap -StatePath $statePath -ProjectId $projectId -StateMap $stateMap
}
