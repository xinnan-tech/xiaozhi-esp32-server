// 主应用入口
import { log } from './utils/logger.js';
import { checkOpusLoaded, initOpusEncoder } from './core/audio/opus-codec.js';
import { getUIController } from './ui/controller.js';
import { getAudioPlayer } from './core/audio/player.js';
import { initMcpTools } from './core/mcp/tools.js';

// 应用类
class App {
    constructor() {
        this.uiController = null;
        this.audioPlayer = null;
    }

    // 初始化应用
    async init() {
        log('正在初始化应用...', 'info');

        // 初始化UI控制器
        this.uiController = getUIController();
        this.uiController.init();

        // 检查Opus库
        checkOpusLoaded();

        // 初始化Opus编码器
        initOpusEncoder();

        // 初始化音频播放器
        this.audioPlayer = getAudioPlayer();
        await this.audioPlayer.start();

        // 初始化MCP工具
        initMcpTools();

        log('应用初始化完成', 'success');
    }
}

// 创建并启动应用
const app = new App();

// DOM加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => app.init());
} else {
    app.init();
}

export default app;
