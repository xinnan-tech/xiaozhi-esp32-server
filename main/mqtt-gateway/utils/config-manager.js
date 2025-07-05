const fs = require('fs');
const path = require('path');
const EventEmitter = require('events');

class ConfigManager extends EventEmitter {
  constructor(fileName) {
    super();
    this.config = {};  // 移除默认的 apiKeys 配置
    this.configPath = path.join(__dirname, "..", "config", fileName);
    this.loadConfig();
    this.watchConfig();
    // 添加防抖计时器变量
    this.watchDebounceTimer = null;
  }

  loadConfig() {
    try {
      const data = fs.readFileSync(this.configPath, 'utf8');
      const newConfig = JSON.parse(data);
      
      // 检测配置是否发生变化
      if (JSON.stringify(this.config) !== JSON.stringify(newConfig)) {
        console.log('配置已更新', this.configPath);
        this.config = newConfig;
        // 发出配置更新事件
        this.emit('configChanged', this.config);
      }
    } catch (error) {
      console.error('加载配置出错:', error, this.configPath);
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
      const defaultConfig = {};  // 空配置对象
      fs.writeFileSync(this.configPath, JSON.stringify(defaultConfig, null, 2));
      console.log('已创建空配置文件', this.configPath);
    } catch (error) {
      console.error('创建空配置文件出错:', error, this.configPath);
    }
  }

  watchConfig() {
    fs.watch(path.dirname(this.configPath), (eventType, filename) => {
      if (filename === path.basename(this.configPath) && eventType === 'change') {
        // 清除之前的计时器
        if (this.watchDebounceTimer) {
          clearTimeout(this.watchDebounceTimer);
        }
        // 设置新的计时器，300ms 后执行
        this.watchDebounceTimer = setTimeout(() => {
          this.loadConfig();
        }, 300);
      }
    });
  }

  // 获取配置的方法
  getConfig() {
    return this.config;
  }

  // 获取特定配置项的方法
  get(key) {
    return this.config[key];
  }
}

module.exports = {
    ConfigManager
};