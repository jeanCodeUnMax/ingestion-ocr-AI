const http = require('http');
const path = require('path');
const fs = require('fs').promises;
const { spawn } = require('child_process');
const { EventEmitter } = require('events');

class CascadeMonitor extends EventEmitter {
    constructor() {
        super();
        this.projectRoot = path.resolve(__dirname, '../..');
        this.port = 3055;
        this.metrics = new Map();
        this.mcpServers = [
            { name: 'cache', healthEndpoint: null },
            { name: 'filesystem', healthEndpoint: null },
            { name: 'memory', healthEndpoint: null },
            { name: 'sqlite', healthEndpoint: null },
            { name: 'zvec', healthEndpoint: null }
        ];
        this.ingestProcess = null;
        this.lastIngestTime = null;
        this.watcherActive = false;
    }

    async getStatus() {
        return {
            status: 'healthy',
            uptime: process.uptime(),
            timestamp: new Date(),
            watcherActive: this.watcherActive,
            lastIngestTime: this.lastIngestTime
        };
    }

    async checkMcpServer(server) {
        if (!server.healthEndpoint) {
            // Pas d'endpoint de santé, vérifier si le processus MCP tourne via ps
            try {
                const result = await this.execCommand('tasklist', ['/FI', `IMAGENAME eq node.exe`, '/FO', 'CSV']);
                const lines = result.split('\n').filter(l => l.includes('node.exe'));
                return { running: lines.length > 0, responseTime: 0 };
            } catch {
                return { running: false, responseTime: 0 };
            }
        }

        const startTime = Date.now();
        try {
            const response = await fetch(server.healthEndpoint, {
                method: 'GET',
                timeout: 2000
            });
            const responseTime = Date.now() - startTime;
            return { running: response.ok, responseTime };
        } catch {
            return { running: false, responseTime: Date.now() - startTime };
        }
    }

    async collectMetrics() {
        for (const server of this.mcpServers) {
            const result = await this.checkMcpServer(server);
            this.metrics.set(`mcp.${server.name}.running`, result.running);
            this.metrics.set(`mcp.${server.name}.responseTime`, result.responseTime);
        }
    }

    async checkIngestProcess() {
        // Vérifier si le processus d'ingestion watch tourne
        try {
            const result = await this.execCommand('tasklist', ['/FI', `IMAGENAME eq pwsh.exe`, '/FO', 'CSV']);
            const lines = result.split('\n');
            const pwshCount = lines.filter(l => l.includes('pwsh.exe')).length;
            this.metrics.set('ingest.watch.active', pwshCount >= 2); // Au moins 2 processus pwsh (un pour watch, un pour auto-ingest)
        } catch {
            this.metrics.set('ingest.watch.active', false);
        }
    }

    async execCommand(cmd, args) {
        return new Promise((resolve, reject) => {
            const child = spawn(cmd, args);
            let stdout = '';
            let stderr = '';
            child.stdout.on('data', (data) => stdout += data.toString());
            child.stderr.on('data', (data) => stderr += data.toString());
            child.on('close', (code) => {
                if (code === 0) resolve(stdout);
                else reject(new Error(stderr));
            });
            child.on('error', reject);
            setTimeout(() => {
                child.kill();
                reject(new Error('Command timeout'));
            }, 5000);
        });
    }

    async printDashboard() {
        console.clear();
        console.log('🎯 CASCADE System Monitor Dashboard');
        console.log('='.repeat(60));
        const status = await this.getStatus();
        
        console.log(`Status: ${status.watcherActive ? '🟢' : '🔴'} ${status.status.toUpperCase()}`);
        console.log(`Port: ${this.port}`);
        console.log(`Uptime: ${Math.floor(status.uptime / 60)}m ${Math.floor(status.uptime % 60)}s`);
        console.log(`Last Ingest: ${this.lastIngestTime ? this.lastIngestTime.toLocaleTimeString() : 'Never'}`);
        console.log('');
        
        console.log('🚀 MCP Servers:');
        for (const server of this.mcpServers) {
            const running = this.metrics.get(`mcp.${server.name}.running`);
            const responseTime = this.metrics.get(`mcp.${server.name}.responseTime`);
            console.log(`  ${server.name.padEnd(12)}: ${running ? '🟢' : '🔴'} ${responseTime}ms`);
        }
        console.log('');
        
        const ingestActive = this.metrics.get('ingest.watch.active');
        console.log('📡 Ingest Watchdog:');
        console.log(`  ${'Watch Mode'.padEnd(12)}: ${ingestActive ? '🟢 Active' : '🔴 Inactive'}`);
        console.log('');
        
        console.log(`Last updated: ${new Date().toLocaleTimeString()}`);
        console.log('Press Ctrl+C to stop');
    }

    async start() {
        await this.collectMetrics();
        await this.checkIngestProcess();
        
        this.server = http.createServer(async (req, res) => {
            if (req.url === '/health') {
                const status = await this.getStatus();
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(status));
            } else if (req.url === '/metrics') {
                await this.collectMetrics();
                await this.checkIngestProcess();
                const metricsObj = Object.fromEntries(this.metrics);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(metricsObj));
            } else {
                res.writeHead(200, { 'Content-Type': 'text/plain' });
                res.end('CASCADE Monitor active on port ' + this.port);
            }
        });
        
        this.server.listen(this.port);
        console.log('✅ Monitor started on port ' + this.port);
        
        // Update dashboard every 5 seconds
        setInterval(async () => {
            await this.collectMetrics();
            await this.checkIngestProcess();
            await this.printDashboard();
        }, 5000);
        
        // Initial dashboard
        await this.printDashboard();
    }
}

if (require.main === module) {
    const monitor = new CascadeMonitor();
    
    process.on('SIGINT', () => {
        console.log('\n🛑 Monitor stopped');
        process.exit(0);
    });
    
    monitor.start().catch(console.error);
}

module.exports = CascadeMonitor;
