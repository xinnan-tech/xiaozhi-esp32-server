const fs = require('fs');
const path = require('path');
const EventEmitter = require('events');

class ConfigManager extends EventEmitter {
    constructor(fileName) {
        super();
        this.config = {}; // Remove default apiKeys configuration
        this.configPath = path.join(__dirname, "..", "config", fileName);
        this.loadConfig();
        this.watchConfig();
        // Add debounce timer variable
        this.watchDebounceTimer = null;
    }

    loadConfig() {
        try {
            const data = fs.readFileSync(this.configPath, 'utf8');
            const newConfig = JSON.parse(data);
            // Check if configuration has changed
            if (JSON.stringify(this.config) !== JSON.stringify(newConfig)) {
                console.log('Configuration updated', this.configPath);
                this.config = newConfig;
                // Emit configuration update event
                this.emit('configChanged', this.config);
            }
        } catch (error) {
            console.error('Error loading configuration:', error, this.configPath);
            if (error.code === 'ENOENT') {
                this.createEmptyConfig();
            }
        }
    }

    createEmptyConfig() {
        try {
            const dir = path.dirname(this.configPath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            const defaultConfig = {}; // Empty configuration object
            fs.writeFileSync(this.configPath, JSON.stringify(defaultConfig, null, 2));
            console.log('Created empty configuration file', this.configPath);
        } catch (error) {
            console.error('Error creating empty configuration file:', error, this.configPath);
        }
    }

    watchConfig() {
        fs.watch(path.dirname(this.configPath), (eventType, filename) => {
            if (filename === path.basename(this.configPath) && eventType === 'change') {
                // Clear previous timer
                if (this.watchDebounceTimer) {
                    clearTimeout(this.watchDebounceTimer);
                }
                // Set new timer, execute after 300ms
                this.watchDebounceTimer = setTimeout(() => {
                    this.loadConfig();
                }, 300);
            }
        });
    }

    // Method to get configuration
    getConfig() {
        return this.config;
    }

    // Method to get specific configuration item
    get(key) {
        return this.config[key];
    }
}

module.exports = {
    ConfigManager
};
