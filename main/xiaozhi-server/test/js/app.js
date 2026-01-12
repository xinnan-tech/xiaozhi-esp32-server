// 主应用入口
import { log } from './utils/logger.js';
import { checkOpusLoaded, initOpusEncoder } from './core/audio/opus-codec.js';
import { uiController } from './ui/controller.js';
import { getAudioPlayer } from './core/audio/player.js';
import { initMcpTools } from './core/mcp/tools.js';

// 应用类
class App {
    constructor() {
        this.uiController = null;
        this.audioPlayer = null;
        this.live2dManager = null;
    }

    // 初始化应用
    async init() {
        log('正在初始化应用...', 'info');

        // 初始化UI控制器
        this.uiController = uiController;
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

        // 初始化Live2D
        await this.initLive2D();

        log('应用初始化完成', 'success');
    }

    // 初始化Live2D
    async initLive2D() {
        try {
            // 检查Live2DManager是否已加载
            if (typeof window.Live2DManager === 'undefined') {
                throw new Error('Live2DManager未加载，请检查脚本引入顺序');
            }

            this.live2dManager = new window.Live2DManager();
            await this.live2dManager.initializeLive2D();

            // 更新UI状态
            const live2dStatus = document.getElementById('live2dStatus');
            if (live2dStatus) {
                live2dStatus.textContent = '● 已加载';
                live2dStatus.className = 'status loaded';
            }

            log('Live2D初始化完成', 'success');
        } catch (error) {
            log(`Live2D初始化失败: ${error.message}`, 'error');

            // 更新UI状态
            const live2dStatus = document.getElementById('live2dStatus');
            if (live2dStatus) {
                live2dStatus.textContent = '● 加载失败';
                live2dStatus.className = 'status error';
            }
        }
    }
}

// 创建并启动应用
const app = new App();

// 将应用实例暴露到全局，供其他模块访问
window.chatApp = app;

// DOM加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => app.init());
} else {
    app.init();
}

export default app;
