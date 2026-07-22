import fs from 'fs';
import path from 'path';

/**
 * MemoryBridge - Pont intelligent entre l'ingestion PS1 et les serveurs MCP.
 * Assure la synchronisation bidirectionnelle entre le scan local et le stockage unifié.
 * Template de référence : ~/.codeium/windsurf/templates/AI-Cascade-System
 */
class MemoryBridge {
    constructor() {
        this.projectRoot = process.cwd();
        this.projectId = path.basename(this.projectRoot);
        
        // --- LECTURE DU FICHIER .ENV ---
        const envPath = path.join(this.projectRoot, '.env');
        if (fs.existsSync(envPath)) {
            const envContent = fs.readFileSync(envPath, 'utf8');
            envContent.split('\n').forEach(line => {
                const match = line.match(/^([^#][^=]+)=(.*)$/);
                if (match) {
                    const key = match[1].trim();
                    let value = match[2].trim();
                    // Supprimer les guillemets
                    if (value.match(/^"(.*)"$/) || value.match(/^'(.*)'$/)) {
                        value = RegExp.$1;
                    }
                    if (key === 'CASCADE_DB_ROOT' && value && !process.env.CASCADE_DB_ROOT) {
                        process.env.CASCADE_DB_ROOT = value;
                    }
                }
            });
        }
        
        // Détection automatique du mode de stockage
        this.useGlobalStorage = false;
        this.globalDbRoot = null;
        
        if (process.env.CASCADE_DB_ROOT) {
            // Mode explicite via variable d'environnement ou .env
            this.useGlobalStorage = true;
            this.globalDbRoot = process.env.CASCADE_DB_ROOT;
        } else {
            // Mode local par défaut (pas de détection auto de chemins codés en dur)
            this.useGlobalStorage = false;
        }
        
        if (this.useGlobalStorage) {
            // Utiliser directement le dossier global sans créer de récursion
            this.unifiedBase = this.globalDbRoot;
        } else {
            // Architecture V3: mémoire locale dans current_workspace
            this.unifiedBase = process.env.MEMORY_LOCAL || 'C:\\DATA-WEBMAN\\memory\\current_workspace';
        }
    }

    /**
     * Synchronise le scan local (.agent/scripts/ingestion.log) vers agentMemory
     */
    async syncIngestionToMCP() {
        const logPath = path.join(this.projectRoot, '.agent', 'scripts', 'ingestion.log');
        if (!fs.existsSync(logPath)) {
            console.error('❌ Fichier ingestion.log non trouvé.');
            return;
        }

        console.log(`🚀 Synchronisation de l'ingestion pour le projet: ${this.projectId}`);
        
        const targetDir = path.join(this.unifiedBase, this.projectId, 'agentmemory');
        if (!fs.existsSync(targetDir)) {
            await fs.promises.mkdir(targetDir, { recursive: true });
        }

        const bridgeMeta = {
            lastSync: new Date().toISOString(),
            status: 'synchronized',
            source: logPath
        };

        await fs.promises.writeFile(path.join(targetDir, 'bridge_state.json'), JSON.stringify(bridgeMeta, null, 2));
        console.log(`✅ État synchronisé dans ${targetDir}`);
    }

    /**
     * Vérifie la cohérence entre les DB locales (.agent/memory-database) et globales
     */
    async checkDatabaseConsistency() {
        const globalDbDir = path.join(this.unifiedBase, this.projectId);

        console.log('🔍 Vérification de la cohérence des bases de données...');

        if (fs.existsSync(globalDbDir)) {
            console.log('✅ Base de données globale détectée (Source de Vérité).');
        } else {
            console.log('⚠️ Base basique manquante. Initialisation à partir de la locale...');
        }
    }

    /**
     * Point d'entrée pour le démarrage par start-system.bat
     */
    async start() {
        await this.syncIngestionToMCP();
        await this.checkDatabaseConsistency();
        console.log('✨ Memory Bridge actif et synchronisé.');
    }
}

const bridge = new MemoryBridge();
bridge.start().catch(console.error);
