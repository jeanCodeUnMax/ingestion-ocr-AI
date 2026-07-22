# Jiminy Watchdog Hook
# Intercepte Python, Git, Curl, Wget pour forcer un audit de securite

function Audit-CliCommand {
    param (
        [string]$CmdName,
        [string[]]$CmdArgs
    )
    $jiminyScript = "d:\DATA-WEBMAN\projet-DEV\test\core\conscience\jiminy_watchdog.py"
    $realPython = "C:\Python314\python.exe"
    
    $auditArgs = @("--quiet", "--audit-cmd", $CmdName) + $CmdArgs
    $auditOutput = & $realPython $jiminyScript $auditArgs 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[BLOCKED] ACCES BLOQUE PAR JIMINY WATCHDOG [BLOCKED]" -ForegroundColor Red
        Write-Host "La commande '$CmdName' a ete identifiee comme dangereuse (Risque CRITIQUE)." -ForegroundColor Red
        Write-Host "`n--- Rapport et Conseils ---" -ForegroundColor Yellow
        Write-Host $auditOutput -ForegroundColor Yellow
        Write-Host "---------------------------`n" -ForegroundColor Yellow
        
        $response = Read-Host "[WARNING] Voulez-vous VRAIMENT forcer l'execution de cette commande ? [o/N]"
        if ($response -match '^o$|^oui$') {
            Write-Host "[UNLOCKED] Contournement autorise par l'utilisateur. Execution en cours...`n" -ForegroundColor Cyan
            return $true
        } else {
            Write-Host "[LOCKED] Execution annulee.`n" -ForegroundColor Green
            return $false
        }
    }
    return $true
}

function python {
    $realPython = "C:\Python314\python.exe"
    if ($args.Count -eq 0) {
        & $realPython $args
        return
    }
    $firstArg = $args[0]
    if ($firstArg -match '\.py$') {
        if ($firstArg -notmatch 'jiminy_watchdog\.py$') {
            $jiminyScript = "d:\DATA-WEBMAN\projet-DEV\test\core\conscience\jiminy_watchdog.py"
            $auditOutput = & $realPython $jiminyScript --quiet --audit $firstArg 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "`n[BLOCKED] SCRIPT BLOQUE PAR JIMINY WATCHDOG [BLOCKED]" -ForegroundColor Red
                Write-Host "Le script a ete identifie comme dangereux (Risque CRITIQUE)." -ForegroundColor Red
                Write-Host "`n--- Rapport et Conseils ---" -ForegroundColor Yellow
                Write-Host $auditOutput -ForegroundColor Yellow
                Write-Host "---------------------------`n" -ForegroundColor Yellow
                
                $response = Read-Host "[WARNING] Voulez-vous VRAIMENT forcer l'execution de ce script ? [o/N]"
                if ($response -match '^o$|^oui$') {
                    Write-Host "[UNLOCKED] Contournement autorise par l'utilisateur. Execution en cours...`n" -ForegroundColor Cyan
                } else {
                    Write-Host "[LOCKED] Execution annulee.`n" -ForegroundColor Green
                    return
                }
            }
        }
    }
    & $realPython $args
}

function git {
    if (Audit-CliCommand -CmdName "git" -CmdArgs $args) {
        & (Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1) $args
    }
}

function curl {
    if (Audit-CliCommand -CmdName "curl" -CmdArgs $args) {
        & (Get-Command curl -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1) $args
    }
}

function wget {
    if (Audit-CliCommand -CmdName "wget" -CmdArgs $args) {
        & (Get-Command wget -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1) $args
    }
}

function Remove-Item {
    if (Audit-CliCommand -CmdName "Remove-Item" -CmdArgs $args) {
        & (Get-Command Remove-Item -CommandType Cmdlet -ErrorAction SilentlyContinue | Select-Object -First 1) @args
    }
}

function rm {
    if (Audit-CliCommand -CmdName "rm" -CmdArgs $args) {
        & (Get-Command Remove-Item -CommandType Cmdlet -ErrorAction SilentlyContinue | Select-Object -First 1) @args
    }
}

function del {
    if (Audit-CliCommand -CmdName "del" -CmdArgs $args) {
        & (Get-Command Remove-Item -CommandType Cmdlet -ErrorAction SilentlyContinue | Select-Object -First 1) @args
    }
}

Write-Host "[SHIELD] Jiminy Hook (Python, Git, Curl, Wget, Rm, Del) active." -ForegroundColor Cyan
