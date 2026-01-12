// UI控制模块
import { loadConfig, saveConfig, getConfig } from '../config/manager.js';
import { getAudioRecorder } from '../core/audio/recorder.js';
import { getWebSocketHandler } from '../core/network/websocket.js';
import { getAudioPlayer } from '../core/audio/player.js';

// UI控制器类
class UIController {
    constructor() {
        this.isEditing = false;
        this.visualizerCanvas = null;
        this.visualizerContext = null;
        this.audioStatsTimer = null;
        this.currentBackgroundIndex = 0;
        this.backgroundImages = ['1.png', '2.png', '3.png'];

        // 绑定方法
        this.init = this.init.bind(this);
        this.initEventListeners = this.initEventListeners.bind(this);
        this.updateDialButton = this.updateDialButton.bind(this);
        this.addChatMessage = this.addChatMessage.bind(this);
        this.switchBackground = this.switchBackground.bind(this);
        this.showModal = this.showModal.bind(this);
        this.hideModal = this.hideModal.bind(this);
        this.switchTab = this.switchTab.bind(this);
    }

    // 初始化
    init() {
        console.log('UIController init started');

        this.visualizerCanvas = document.getElementById('audioVisualizer');
        if (this.visualizerCanvas) {
            this.visualizerContext = this.visualizerCanvas.getContext('2d');
            this.initVisualizer();
        }

        // 检查连接按钮在初始化时是否存在
        const connectBtn = document.getElementById('connectBtn');
        console.log('connectBtn during init:', connectBtn);

        this.initEventListeners();
        this.startAudioStatsMonitor();
        loadConfig();

        // 设置录音器回调
        const audioRecorder = getAudioRecorder();
        audioRecorder.onRecordingStart = (seconds) => {
            this.updateRecordButtonState(true, seconds);
        };

        // 初始化状态显示
        this.updateConnectionUI(false);
        this.updateDialButton(false);

        console.log('UIController init completed');
    }

    // 初始化可视化器
    initVisualizer() {
        if (this.visualizerCanvas) {
            this.visualizerCanvas.width = this.visualizerCanvas.clientWidth;
            this.visualizerCanvas.height = this.visualizerCanvas.clientHeight;
            this.visualizerContext.fillStyle = '#fafafa';
            this.visualizerContext.fillRect(0, 0, this.visualizerCanvas.width, this.visualizerCanvas.height);
        }
    }

    // 初始化事件监听器
    initEventListeners() {
        // 设置按钮
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.showModal('settingsModal');
            });
        }

        // 背景切换按钮
        const backgroundBtn = document.getElementById('backgroundBtn');
        if (backgroundBtn) {
            backgroundBtn.addEventListener('click', this.switchBackground);
        }

        // 拨号按钮
        const dialBtn = document.getElementById('dialBtn');
        if (dialBtn) {
            dialBtn.addEventListener('click', () => {
                const wsHandler = getWebSocketHandler();
                const isConnected = wsHandler.isConnected();

                if (isConnected) {
                    wsHandler.disconnect();
                    this.updateDialButton(false);
                } else {
                    // 检查OTA地址是否已填写
                    const otaUrlInput = document.getElementById('otaUrl');
                    if (!otaUrlInput || !otaUrlInput.value.trim()) {
                        // 如果OTA地址未填写，显示设置弹窗并切换到设备配置页
                        this.showModal('settingsModal');
                        this.switchTab('device');
                        this.addChatMessage('请先填写OTA服务器地址', false);
                        return;
                    }

                    // 执行连接操作
                    this.handleConnect();
                }
            });
        }

        // 录音按钮
        const recordBtn = document.getElementById('recordBtn');
        if (recordBtn) {
            recordBtn.addEventListener('click', () => {
                const audioRecorder = getAudioRecorder();
                if (audioRecorder.isRecording) {
                    audioRecorder.stop();
                    // 停止录音时移除录音样式
                    recordBtn.classList.remove('recording');
                    recordBtn.querySelector('.btn-text').textContent = '录音';
                } else {
                    // 先更新按钮状态为录音中
                    recordBtn.classList.add('recording');
                    recordBtn.querySelector('.btn-text').textContent = '录音中';

                    // 延迟开始录音，确保按钮状态已更新
                    setTimeout(() => {
                        audioRecorder.start();
                    }, 100);
                }
            });
        }

        // 关闭按钮
        const closeButtons = document.querySelectorAll('.close-btn');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    this.hideModal(modal.id);
                }
            });
        });

        // 设置标签页切换
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // 点击模态框外部关闭
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });

        // 保存配置按钮
        const saveConfigBtn = document.getElementById('saveConfigBtn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', () => {
                this.saveConfig();
            });
        }

        // 添加MCP工具按钮
        const addMCPToolBtn = document.getElementById('addMCPToolBtn');
        if (addMCPToolBtn) {
            addMCPToolBtn.addEventListener('click', () => {
                this.addMCPTool();
            });
        }

        // 连接按钮和取消按钮已被移除，功能已集成到拨号按钮中
    }

    // 更新连接状态UI
    updateConnectionUI(isConnected) {
        const connectionStatus = document.getElementById('connectionStatus');
        const statusDot = document.querySelector('.status-dot');

        if (connectionStatus) {
            if (isConnected) {
                connectionStatus.textContent = '已连接';
                if (statusDot) {
                    statusDot.className = 'status-dot status-connected';
                }
            } else {
                connectionStatus.textContent = '离线';
                if (statusDot) {
                    statusDot.className = 'status-dot status-disconnected';
                }
            }
        }
    }

    // 更新拨号按钮状态
    updateDialButton(isConnected) {
        const dialBtn = document.getElementById('dialBtn');
        const recordBtn = document.getElementById('recordBtn');

        if (dialBtn) {
            if (isConnected) {
                dialBtn.classList.add('dial-active');
                dialBtn.querySelector('.btn-text').textContent = '挂断';
                // 更新拨号按钮图标为挂断图标
                dialBtn.querySelector('svg').innerHTML = `
                    <path d="M12,9C10.4,9 9,10.4 9,12C9,13.6 10.4,15 12,15C13.6,15 15,13.6 15,12C15,10.4 13.6,9 12,9M12,17C9.2,17 7,14.8 7,12C7,9.2 9.2,7 12,7C14.8,7 17,9.2 17,12C17,14.8 14.8,17 12,17M12,4.5C7,4.5 2.7,7.6 1,12C2.7,16.4 7,19.5 12,19.5C17,19.5 21.3,16.4 23,12C21.3,7.6 17,4.5 12,4.5Z"/>
                `;
            } else {
                dialBtn.classList.remove('dial-active');
                dialBtn.querySelector('.btn-text').textContent = '拨号';
                // 恢复拨号按钮图标
                dialBtn.querySelector('svg').innerHTML = `
                    <path d="M6.62,10.79C8.06,13.62 10.38,15.94 13.21,17.38L15.41,15.18C15.69,14.9 16.08,14.82 16.43,14.93C17.55,15.3 18.75,15.5 20,15.5A1,1 0 0,1 21,16.5V20A1,1 0 0,1 20,21A17,17 0 0,1 3,4A1,1 0 0,1 4,3H7.5A1,1 0 0,1 8.5,4C8.5,5.25 8.7,6.45 9.07,7.57C9.18,7.92 9.1,8.31 8.82,8.59L6.62,10.79Z"/>
                `;
            }
        }

        // 更新录音按钮状态
        if (recordBtn) {
            if (isConnected) {
                recordBtn.disabled = false;
                recordBtn.title = '开始录音';
                // 确保录音按钮恢复到正常状态
                recordBtn.querySelector('.btn-text').textContent = '录音';
                recordBtn.classList.remove('recording');
            } else {
                recordBtn.disabled = true;
                recordBtn.title = '请先连接服务器';
                // 确保录音按钮恢复到正常状态
                recordBtn.querySelector('.btn-text').textContent = '录音';
                recordBtn.classList.remove('recording');
            }
        }
    }

    // 更新录音按钮状态
    updateRecordButtonState(isRecording, seconds = 0) {
        const recordBtn = document.getElementById('recordBtn');
        if (recordBtn) {
            if (isRecording) {
                recordBtn.querySelector('.btn-text').textContent = `录音中 ${seconds.toFixed(1)}秒`;
                recordBtn.classList.add('recording');
            } else {
                recordBtn.querySelector('.btn-text').textContent = '录音';
                recordBtn.classList.remove('recording');
            }
            recordBtn.disabled = false;
        }
    }

    // 添加聊天消息
    addChatMessage(content, isUser = false) {
        const chatStream = document.getElementById('chatStream');
        if (!chatStream) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user' : 'ai'}`;
        messageDiv.innerHTML = `<div class="message-bubble">${content}</div>`;
        chatStream.appendChild(messageDiv);

        // 自动滚动到底部
        chatStream.scrollTop = chatStream.scrollHeight;
    }

    // 切换背景
    switchBackground() {
        this.currentBackgroundIndex = (this.currentBackgroundIndex + 1) % this.backgroundImages.length;
        const backgroundContainer = document.querySelector('.background-container');
        if (backgroundContainer) {
            backgroundContainer.style.backgroundImage = `url('../images/${this.backgroundImages[this.currentBackgroundIndex]}')`;
        }
    }

    // 显示模态框
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    // 隐藏模态框
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // 切换标签页
    switchTab(tabName) {
        // 移除所有标签页的active类
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        // 激活选中的标签页
        const activeTabBtn = document.querySelector(`[data-tab="${tabName}"]`);
        const activeTabContent = document.getElementById(`${tabName}Tab`);

        if (activeTabBtn && activeTabContent) {
            activeTabBtn.classList.add('active');
            activeTabContent.classList.add('active');
        }
    }

    // 保存配置
    saveConfig() {
        const config = {
            serverUrl: document.getElementById('serverUrl').value,
            serverPort: document.getElementById('serverPort').value,
            audioDevice: document.getElementById('audioDevice').value,
            audioSampleRate: document.getElementById('audioSampleRate').value,
            audioChannels: document.getElementById('audioChannels').value
        };

        saveConfig(config);
        this.hideModal('settingsModal');

        // 显示保存成功消息
        this.addChatMessage('配置已保存', false);
    }

    // 处理连接按钮点击
    async handleConnect() {
        console.log('handleConnect called');

        // 确保切换到设备配置标签页
        this.switchTab('device');

        // 等待DOM更新
        await new Promise(resolve => setTimeout(resolve, 50));

        const otaUrlInput = document.getElementById('otaUrl');

        console.log('otaUrl element:', otaUrlInput);

        if (!otaUrlInput || !otaUrlInput.value) {
            this.addChatMessage('请输入OTA服务器地址', false);
            return;
        }

        const otaUrl = otaUrlInput.value;
        console.log('otaUrl value:', otaUrl);

        // 更新拨号按钮状态为连接中
        const dialBtn = document.getElementById('dialBtn');
        if (dialBtn) {
            dialBtn.classList.add('dial-active');
            dialBtn.querySelector('.btn-text').textContent = '连接中...';
            dialBtn.disabled = true;
        }

        // 显示连接中消息
        this.addChatMessage('正在连接服务器...', false);

        try {
            // 获取配置信息
            const config = getConfig();

            // 导入OTA连接器
            const { webSocketConnect } = await import('../core/network/ota-connector.js');

            // 建立OTA连接
            const websocket = await webSocketConnect(otaUrl, config);

            if (websocket) {
                // 获取WebSocket处理器
                const wsHandler = getWebSocketHandler();

                // 设置WebSocket连接
                wsHandler.websocket = websocket;

                // 设置连接状态回调
                wsHandler.onConnectionStateChange = (isConnected) => {
                    this.updateConnectionUI(isConnected);
                    this.updateDialButton(isConnected);
                };

                // 设置聊天消息回调
                wsHandler.onChatMessage = (text, isUser) => {
                    this.addChatMessage(text, isUser);
                };

                // 设置录音按钮状态回调
                wsHandler.onRecordButtonStateChange = (isRecording) => {
                    const recordBtn = document.getElementById('recordBtn');
                    if (recordBtn) {
                        if (isRecording) {
                            recordBtn.classList.add('recording');
                            recordBtn.querySelector('.btn-text').textContent = '录音中';
                        } else {
                            recordBtn.classList.remove('recording');
                            recordBtn.querySelector('.btn-text').textContent = '录音';
                        }
                    }
                };

                // 连接成功
                this.addChatMessage('OTA连接成功，正在建立WebSocket连接...', false);

                // 更新拨号按钮状态
                const dialBtn = document.getElementById('dialBtn');
                if (dialBtn) {
                    dialBtn.disabled = false;
                    dialBtn.querySelector('.btn-text').textContent = '挂断';
                    dialBtn.classList.add('dial-active');
                }

                this.hideModal('settingsModal');

                // 自动尝试建立WebSocket连接
                setTimeout(() => {
                    wsHandler.connect();
                }, 1000);
            } else {
                throw new Error('OTA连接失败');
            }
        } catch (error) {
            console.error('Connection error details:', {
                message: error.message,
                stack: error.stack,
                name: error.name
            });

            // 显示错误消息
            const errorMessage = error.message.includes('Cannot set properties of null')
                ? '连接失败：请刷新页面重试'
                : `连接失败: ${error.message}`;

            this.addChatMessage(errorMessage, false);

            // 恢复拨号按钮状态
            const dialBtn = document.getElementById('dialBtn');
            if (dialBtn) {
                dialBtn.disabled = false;
                dialBtn.querySelector('.btn-text').textContent = '拨号';
                dialBtn.classList.remove('dial-active');
                console.log('Dial button state restored successfully');
            }
        }
    }

    // 添加MCP工具
    addMCPTool() {
        const mcpToolsList = document.getElementById('mcpToolsList');
        if (!mcpToolsList) return;

        const toolId = `mcp-tool-${Date.now()}`;
        const toolDiv = document.createElement('div');
        toolDiv.className = 'properties-container';
        toolDiv.innerHTML = `
            <div class="property-item">
                <input type="text" placeholder="工具名称" value="新工具">
                <input type="text" placeholder="工具描述" value="工具描述">
                <button class="remove-property" onclick="uiController.removeMCPTool('${toolId}')">删除</button>
            </div>
        `;

        mcpToolsList.appendChild(toolDiv);
    }

    // 移除MCP工具
    removeMCPTool(toolId) {
        const toolElement = document.getElementById(toolId);
        if (toolElement) {
            toolElement.remove();
        }
    }

    // 更新音频统计信息
    updateAudioStats() {
        const audioPlayer = getAudioPlayer();
        if (!audioPlayer) return;

        const stats = audioPlayer.getAudioStats();
        // 这里可以添加音频统计的UI更新逻辑
    }

    // 启动音频统计监控
    startAudioStatsMonitor() {
        // 每100ms更新一次音频统计
        this.audioStatsTimer = setInterval(() => {
            this.updateAudioStats();
        }, 100);
    }

    // 停止音频统计监控
    stopAudioStatsMonitor() {
        if (this.audioStatsTimer) {
            clearInterval(this.audioStatsTimer);
            this.audioStatsTimer = null;
        }
    }

    // 绘制音频可视化效果
    drawVisualizer(dataArray) {
        if (!this.visualizerContext || !this.visualizerCanvas) return;

        this.visualizerContext.fillStyle = '#fafafa';
        this.visualizerContext.fillRect(0, 0, this.visualizerCanvas.width, this.visualizerCanvas.height);

        const barWidth = (this.visualizerCanvas.width / dataArray.length) * 2.5;
        let barHeight;
        let x = 0;

        for (let i = 0; i < dataArray.length; i++) {
            barHeight = dataArray[i] / 2;

            // 创建渐变色：从紫色到蓝色到青色
            const gradient = this.visualizerContext.createLinearGradient(0, 0, 0, this.visualizerCanvas.height);
            gradient.addColorStop(0, '#8e44ad');
            gradient.addColorStop(0.5, '#3498db');
            gradient.addColorStop(1, '#1abc9c');

            this.visualizerContext.fillStyle = gradient;
            this.visualizerContext.fillRect(x, this.visualizerCanvas.height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
        }
    }

    // 更新会话状态UI
    updateSessionStatus(isSpeaking) {
        // 这里可以添加会话状态的UI更新逻辑
        // 例如：更新Live2D角色的表情或状态指示器
    }

    // 更新会话表情
    updateSessionEmotion(emoji) {
        // 这里可以添加表情更新的逻辑
        // 例如：在状态指示器中显示表情
    }
}

// 创建全局实例
export const uiController = new UIController();

// 导出类供其他模块使用
export { UIController };