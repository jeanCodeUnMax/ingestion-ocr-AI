<#
.SYNOPSIS
    Injection complète d'un nouveau projet avec brainstorming
.DESCRIPTION
    Crée la structure projet, MANIFEST, roadmap après une phase de définition
.PARAMETER ProjectName
    Nom du projet
.PARAMETER ProjectType
    Type: web, mobile, backend, cli, game, library
.PARAMETER Description
    Description courte du projet
.EXAMPLE
    ./init-project.ps1 -ProjectName "MonJeu" -ProjectType "game" -Description "Jeu Pacman en HTML"
#>

Param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    
    [ValidateSet('web', 'mobile', 'backend', 'cli', 'game', 'library', 'fullstack')]
    [string]$ProjectType = 'web',
    
    [string]$Description = "",
    
    [switch]$Interactive = $false
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PWD.Path

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  INJECTION PROJET: $ProjectName" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# === PHASE 1: BRAINSTORMING ===
Write-Host "[PHASE 1] Définition du projet" -ForegroundColor Yellow

if ($Interactive -or [string]::IsNullOrEmpty($Description)) {
    Write-Host "`nRépondez aux questions suivantes pour définir le projet:`n" -ForegroundColor White
    
    $Description = Read-Host "1. Description du projet (quoi?)"
    $Objectives = Read-Host "2. Objectifs principaux (pourquoi?)"
    $Constraints = Read-Host "3. Contraintes techniques (comment?)"
    $TargetUsers = Read-Host "4. Utilisateurs cibles (pour qui?)"
    $TechStack = Read-Host "5. Stack technique préférée (langages, frameworks)"
    $Timeline = Read-Host "6. Timeline estimée (semaines)"
    $Priority = Read-Host "7. Priorité (haute/moyenne/basse)"
} else {
    $Objectives = "À définir"
    $Constraints = "À définir"
    $TargetUsers = "À définir"
    $TechStack = "À définir selon le type: $ProjectType"
    $Timeline = "À définir"
    $Priority = "moyenne"
}

# === PHASE 2: STRUCTURE PROJET ===
Write-Host "`n[PHASE 2] Création de la structure" -ForegroundColor Yellow

# Dossiers selon le type
$Folders = switch ($ProjectType) {
    'web' { @('src/components', 'src/pages', 'src/styles', 'src/utils', 'public', 'tests') }
    'mobile' { @('src/screens', 'src/components', 'src/navigation', 'src/services', 'assets', 'tests') }
    'backend' { @('src/routes', 'src/controllers', 'src/models', 'src/middleware', 'src/utils', 'tests') }
    'cli' { @('src/commands', 'src/utils', 'src/config', 'tests') }
    'game' { @('src/game', 'src/assets', 'src/levels', 'src/utils', 'public', 'tests') }
    'library' { @('src', 'dist', 'docs', 'tests') }
    'fullstack' { @('frontend/src', 'backend/src', 'shared', 'tests') }
    default { @('src', 'tests') }
}

foreach ($folder in $Folders) {
    $path = Join-Path $ProjectRoot $folder
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "  ✓ $folder" -ForegroundColor Green
    }
}

# === PHASE 3: MANIFEST ===
Write-Host "`n[PHASE 3] Création du MANIFEST" -ForegroundColor Yellow

$ManifestContent = @"
# MANIFEST - $ProjectName

> Créé le: $(Get-Date -Format 'yyyy-MM-dd')
> Version: 0.1.0
> Type: $ProjectType

## 📋 DÉFINITION DU PROJET

### Description
$Description

### Objectifs
$Objectives

### Contraintes
$Constraints

### Utilisateurs cibles
$TargetUsers

---

## 🏗️ ARCHITECTURE

### Type de projet
**$ProjectType**

### Structure dossiers
``````
$ProjectRoot/
$(foreach ($f in $Folders) { "├── $f/" })
├── .agent/           ← Configuration et scripts
└── MANIFEST.md       ← Ce fichier
``````

### Stack technique
$TechStack

---

## 🎯 ROADMAP

### Sprint 1: Initialisation
- [ ] Setup environnement
- [ ] Configuration base
- [ ] Tests infrastructure

### Sprint 2: MVP
- [ ] Fonctionnalités core
- [ ] Tests unitaires
- [ ] Documentation

### Timeline estimée
$Timeline semaines

### Priorité
$Priority

---

## 📊 MÉTRIQUES

| Métrique | Valeur initiale |
|----------|-----------------|
| Progression | 0% |
| Tests | 0 |
| Documentation | MANIFEST.md |

---

## 🚧 CONTRAINTES TECHNIQUES

### Règles projet
1. **Clean Garden**: Chaque chose à sa place
2. **5S**: Trier, Ranger, Nettoyer, Standardiser, Suivre
3. **Tests**: TDD obligatoire pour nouvelles fonctionnalités
4. **Docs**: Mettre à jour MANIFEST après chaque sprint

### Limitations
- À définir selon l'avancement

---

## 📝 DÉCISIONS ARCHITECTURALES

### ADR-001: Choix du type projet
**Date**: $(Get-Date -Format 'yyyy-MM-dd')
**Décision**: Type `$ProjectType`
**Raison**: $Description

---

## 🔄 PROCHAINES ÉTAPES

1. Finaliser la stack technique
2. Créer les premiers fichiers de code
3. Configurer l'environnement de dev
4. Écrire les premiers tests

---

*Ce manifeste est versionné dans Git. Mettre à jour à chaque changement majeur.*
"@

$ManifestPath = Join-Path $ProjectRoot "MANIFEST.md"
$ManifestContent | Set-Content $ManifestPath -Encoding UTF8
Write-Host "  ✓ MANIFEST.md créé" -ForegroundColor Green

# === RÉSUMÉ ===
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  INJECTION TERMINÉE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Projet: $ProjectName" -ForegroundColor White
Write-Host "Type: $ProjectType" -ForegroundColor White
Write-Host "Description: $Description" -ForegroundColor White
Write-Host "`nFichiers créés:" -ForegroundColor White
Write-Host "  - MANIFEST.md" -ForegroundColor Green
Write-Host "  - Structure dossiers ($($Folders.Count) dossiers)" -ForegroundColor Green
Write-Host "  - .agent/ (configuration)" -ForegroundColor Green

Write-Host "`nProchaines étapes:" -ForegroundColor Yellow
Write-Host "  1. Éditer MANIFEST.md pour compléter la définition" -ForegroundColor White
Write-Host "  2. Sync IDE: pwsh -File .agent\scripts\sync-ide-config.ps1 -IDE all" -ForegroundColor White
Write-Host "  3. Commencer le développement" -ForegroundColor White
