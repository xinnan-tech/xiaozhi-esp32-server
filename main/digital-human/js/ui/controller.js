// UI controller module
import { loadConfig, saveConfig } from '../config/manager.js?v=0205';
import { getAudioPlayer } from '../core/audio/player.js?v=0205';
import { getAudioRecorder } from '../core/audio/recorder.js?v=0205';
import { requestWakewordBridge, stopWakewordBridgeListener, startWakewordBridgeListener, getWakewordBridgeUrl, onNextBridgeConnected } from '../core/network/wakeword-bridge.js?v=0205';
import { getWebSocketHandler } from '../core/network/websocket.js?v=0205';
import { log } from '../utils/logger.js?v=0205';

// UI controller class
class UIController {
    constructor() {
        this.isEditing = false;
        this.visualizerCanvas = null;
        this.visualizerContext = null;
        this.audioStatsTimer = null;
        this.currentBackgroundIndex = localStorage.getItem('backgroundIndex') ? parseInt(localStorage.getItem('backgroundIndex')) : 0;
        this.backgroundImages = ['1.png', '2.png', '3.png'];
        this.dialBtnDisabled = false;
        this.isConnecting = false;
        this.lastWakewordDialTime = 0;

        // Bind methods
        this.init = this.init.bind(this);
        this.initEventListeners = this.initEventListeners.bind(this);
        this.updateDialButton = this.updateDialButton.bind(this);
        this.addChatMessage = this.addChatMessage.bind(this);
        this.switchBackground = this.switchBackground.bind(this);
        this.switchLive2DModel = this.switchLive2DModel.bind(this);
        this.showModal = this.showModal.bind(this);
        this.hideModal = this.hideModal.bind(this);
        this.switchTab = this.switchTab.bind(this);
        this.applyWakewordConfig = this.applyWakewordConfig.bind(this);
        this.handleApplyWakeword = this.handleApplyWakeword.bind(this);
        this.triggerWakewordDial = this.triggerWakewordDial.bind(this);
    }

    // Initialize
    init() {
        console.log('UIController init started');

        this.visualizerCanvas = document.getElementById('audioVisualizer');
        if (this.visualizerCanvas) {
            this.visualizerContext = this.visualizerCanvas.getContext('2d');
            this.initVisualizer();
        }

        // Check if connect button exists during initialization
        const connectBtn = document.getElementById('connectBtn');
        console.log('connectBtn during init:', connectBtn);

        this.initEventListeners();
        this.startAudioStatsMonitor();
        loadConfig();

        // Register recording callback
        const audioRecorder = getAudioRecorder();
        audioRecorder.onRecordingStart = (seconds) => {
            this.updateRecordButtonState(true, seconds);
        };

        // Initialize status display
        this.updateConnectionUI(false);
        // Apply saved background
        const backgroundContainer = document.querySelector('.background-container');
        if (backgroundContainer) {
            backgroundContainer.style.backgroundImage = `url('./images/${this.backgroundImages[this.currentBackgroundIndex]}')`;
        }

        this.updateDialButton(false);

        console.log('UIController init completed');
    }

    // Initialize visualizer
    initVisualizer() {
        if (this.visualizerCanvas) {
            this.visualizerCanvas.width = this.visualizerCanvas.clientWidth;
            this.visualizerCanvas.height = this.visualizerCanvas.clientHeight;
            this.visualizerContext.fillStyle = '#fafafa';
            this.visualizerContext.fillRect(0, 0, this.visualizerCanvas.width, this.visualizerCanvas.height);
        }
    }

    // Initialize event listeners
    initEventListeners() {
        // Settings button
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.showModal('settingsModal');
            });
        }

        // Background switch button
        const backgroundBtn = document.getElementById('backgroundBtn');
        if (backgroundBtn) {
            backgroundBtn.addEventListener('click', this.switchBackground);
        }

        // Model select change event
        const modelSelect = document.getElementById('live2dModelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                this.switchLive2DModel();
            });
        }

        // Camera switch button
        const cameraSwitch = document.getElementById('cameraSwitch');
        const cameraSwitchMask = document.getElementById('cameraSwitchMask');
        if (cameraSwitchMask) {
            cameraSwitchMask.addEventListener('click', () => {
                const isCameraActive = cameraSwitch.classList.contains('active');
                if (isCameraActive) {
                    window.switchCamera();
                }
            })
        }

        // Dial button
        const dialBtn = document.getElementById('dialBtn');
        if (dialBtn) {
            dialBtn.addEventListener('click', () => {
                dialBtn.disabled = true;
                this.dialBtnDisabled = true;
                setTimeout(() => {
                    dialBtn.disabled = false;
                    this.dialBtnDisabled = false;
                }, 3000);

                const wsHandler = getWebSocketHandler();
                const isConnected = wsHandler.isConnected();

                if (isConnected) {
                    wsHandler.disconnect();
                    this.updateDialButton(false);
                    if (cameraSwitch) cameraSwitch.classList.remove('active');
                    this.addChatMessage('Disconnected, see you next time~😊', false);
                } else {
                    // Check if OTA URL is filled
                    const otaUrlInput = document.getElementById('otaUrl');
                    if (!otaUrlInput || !otaUrlInput.value.trim()) {
                        // If OTA URL is not filled, show settings modal and switch to device tab
                        this.showModal('settingsModal');
                        this.switchTab('device');
                        this.addChatMessage('Please fill in OTA server URL', false);
                        return;
                    }

                    // Start connection process
                    this.handleConnect();
                }
            });
        }

        // Camera button
        const cameraBtn = document.getElementById('cameraBtn');
        let cameraTimer = null;
        if (cameraBtn) {
            cameraBtn.addEventListener('click', () => {
                if (cameraTimer) {
                    clearTimeout(cameraTimer);
                    cameraTimer = null;
                }
                cameraTimer = setTimeout(() => {
                    const cameraContainer = document.getElementById('cameraContainer');
                    if (!cameraContainer) {
                        log('Camera container does not exist', 'warning');
                        return;
                    }

                    const isActive = cameraContainer.classList.contains('active');
                    if (isActive) {
                        // Close camera
                        if (typeof window.stopCamera === 'function') {
                            if (cameraSwitch) cameraSwitch.classList.remove('active');
                            window.stopCamera();
                        }
                        cameraContainer.classList.remove('active');
                        cameraBtn.classList.remove('camera-active');
                        cameraBtn.querySelector('.btn-text').textContent = 'Camera';
                        log('Camera closed', 'info');
                    } else {
                        // Open camera
                        if (typeof window.startCamera === 'function') {
                            window.startCamera().then(success => {
                                if (success) {
                                    cameraBtn.classList.add('camera-active');
                                    cameraBtn.querySelector('.btn-text').textContent = 'Close';
                                } else {
                                    this.addChatMessage('⚠️ Camera startup failed, check browser permissions', false);
                                }
                            }).catch(error => {
                                log(`Camera startup exception: ${error.message}`, 'error');
                            });
                        } else {
                            log('startCamera function undefined', 'warning');
                        }
                    }
                }, 300);
            });
        }

        // Record button
        const recordBtn = document.getElementById('recordBtn');
        if (recordBtn) {
            let recordTimer = null;
            recordBtn.addEventListener('click', () => {
                if (recordTimer) {
                    clearTimeout(recordTimer);
                    recordTimer = null;
                }
                recordTimer = setTimeout(() => {
                    const audioRecorder = getAudioRecorder();
                    if (audioRecorder.isRecording) {
                        audioRecorder.stop();
                        // Restore record button to normal state
                        recordBtn.classList.remove('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Record';
                    } else {
                        // Update button state to recording
                        recordBtn.classList.add('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Recording';

                        // Start recording, update button state after delay
                        setTimeout(() => {
                            audioRecorder.start();
                        }, 100);
                    }
                }, 300);
            });
        }

        // Chat input event listener
        const chatIpt = document.getElementById('chatIpt');
        if (chatIpt) {
            const wsHandler = getWebSocketHandler();
            chatIpt.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    if (e.target.value) {
                        wsHandler.sendTextMessage(e.target.value);
                        e.target.value = '';
                        return;
                    }
                }
            });
        }

        // Close button
        const closeButtons = document.querySelectorAll('.close-btn');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const modal = e.target.closest('.modal');
                if (modal) {
                    if (modal.id === 'settingsModal') {
                        saveConfig();
                    }
                    this.hideModal(modal.id);
                }
            });
        });

        // Settings tab switch
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        const applyWakewordBtn = document.getElementById('applyWakewordBtn');
        if (applyWakewordBtn) {
            applyWakewordBtn.addEventListener('click', this.handleApplyWakeword);
        }

        // Close modal by clicking background (disabled for specific modals)
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    // settingsModal, mcpToolModal, and mcpPropertyModal can only be closed by clicking X
                    const nonClosableModals = ['settingsModal', 'mcpToolModal', 'mcpPropertyModal'];
                    if (nonClosableModals.includes(modal.id)) {
                        return; // Prevent closing by clicking background
                    }
                    this.hideModal(modal.id);
                }
            });
        });

        // Add MCP tool button
        const addMCPToolBtn = document.getElementById('addMCPToolBtn');
        if (addMCPToolBtn) {
            addMCPToolBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.addMCPTool();
            });
        }

        // Connect button and send button are not removed, can be added to dial button later
    }

    // Update connection status UI
    updateConnectionUI(isConnected) {
        const connectionStatus = document.getElementById('connectionStatus');
        const statusDot = document.querySelector('.status-dot');

        if (connectionStatus) {
            if (isConnected) {
                connectionStatus.textContent = 'Connected';
                if (statusDot) {
                    statusDot.className = 'status-dot status-connected';
                }
            } else {
                connectionStatus.textContent = 'Offline';
                if (statusDot) {
                    statusDot.className = 'status-dot status-disconnected';
                }
            }
        }
    }

    // Update dial button state
    updateDialButton(isConnected) {
        const dialBtn = document.getElementById('dialBtn');
        const recordBtn = document.getElementById('recordBtn');
        const cameraBtn = document.getElementById('cameraBtn');

        if (dialBtn) {
            if (isConnected) {
                dialBtn.classList.add('dial-active');
                dialBtn.querySelector('.btn-text').textContent = 'Hang up';
                // Update dial button icon to hang up icon
                dialBtn.querySelector('svg').innerHTML = `
                    <path d="M12,9C10.4,9 9,10.4 9,12C9,13.6 10.4,15 12,15C13.6,15 15,13.6 15,12C15,10.4 13.6,9 12,9M12,17C9.2,17 7,14.8 7,12C7,9.2 9.2,7 12,7C14.8,7 17,9.2 17,12C17,14.8 14.8,17 12,17M12,4.5C7,4.5 2.7,7.6 1,12C2.7,16.4 7,19.5 12,19.5C17,19.5 21.3,16.4 23,12C21.3,7.6 17,4.5 12,4.5Z"/>
                `;
            } else {
                dialBtn.classList.remove('dial-active');
                dialBtn.querySelector('.btn-text').textContent = 'Dial';
                // Restore dial button icon
                dialBtn.querySelector('svg').innerHTML = `
                    <path d="M6.62,10.79C8.06,13.62 10.38,15.94 13.21,17.38L15.41,15.18C15.69,14.9 16.08,14.82 16.43,14.93C17.55,15.3 18.75,15.5 20,15.5A1,1 0 0,1 21,16.5V20A1,1 0 0,1 20,21A17,17 0 0,1 3,4A1,1 0 0,1 4,3H7.5A1,1 0 0,1 8.5,4C8.5,5.25 8.7,6.45 9.07,7.57C9.18,7.92 9.1,8.31 8.82,8.59L6.62,10.79Z"/>
                `;
            }
        }

        // Update camera button state - reset to default when disconnected
        if (cameraBtn && !isConnected) {
            const cameraContainer = document.getElementById('cameraContainer');
            if (cameraContainer && cameraContainer.classList.contains('active')) {
                cameraContainer.classList.remove('active');
            }
            cameraBtn.classList.remove('camera-active');
            cameraBtn.querySelector('.btn-text').textContent = 'Camera';
            cameraBtn.disabled = true;
            cameraBtn.title = 'Connect to server first';
            // Close camera
            if (typeof window.stopCamera === 'function') {
                window.stopCamera();
            }
        }

        // Update camera button state - enable when connected and camera is available
        if (cameraBtn && isConnected) {
            if (window.cameraAvailable) {
                cameraBtn.disabled = false;
                cameraBtn.title = 'Toggle camera';
            } else {
                cameraBtn.disabled = true;
                cameraBtn.title = 'Bind verification code first';
            }
        }

        // Update record button state
        if (recordBtn) {
            const microphoneAvailable = window.microphoneAvailable !== false;
            if (isConnected && microphoneAvailable) {
                recordBtn.disabled = false;
                recordBtn.title = 'Start Recording';
                // Restore record button to normal state
                recordBtn.querySelector('.btn-text').textContent = 'Record';
                recordBtn.classList.remove('recording');
            } else {
                recordBtn.disabled = true;
                if (!microphoneAvailable) {
                    recordBtn.title = window.isHttpNonLocalhost ? 'Recording unavailable due to HTTP access; text interaction only' : 'Microphone unavailable';
                } else {
                    recordBtn.title = 'Please connect to server first';
                }
                // Restore record button to normal state
                recordBtn.querySelector('.btn-text').textContent = 'Record';
                recordBtn.classList.remove('recording');
            }
        }
    }

    // Update record button state
    updateRecordButtonState(isRecording, seconds = 0) {
        const recordBtn = document.getElementById('recordBtn');
        if (recordBtn) {
            if (isRecording) {
                recordBtn.querySelector('.btn-text').textContent = `Recording`;
                recordBtn.classList.add('recording');
            } else {
                recordBtn.querySelector('.btn-text').textContent = 'Record';
                recordBtn.classList.remove('recording');
            }
            // Only enable button when microphone is available
            recordBtn.disabled = window.microphoneAvailable === false;
        }
    }

    /**
     * Update microphone availability state
     * @param {boolean} isAvailable - Whether microphone is available
     * @param {boolean} isHttpNonLocalhost - Whether it is HTTP non-localhost access
     */
    updateMicrophoneAvailability(isAvailable, isHttpNonLocalhost) {
        const recordBtn = document.getElementById('recordBtn');
        if (!recordBtn) return;
        if (!isAvailable) {
            // Disable record button
            recordBtn.disabled = true;
            // Update button text and title
            recordBtn.querySelector('.btn-text').textContent = 'Record';
            recordBtn.title = isHttpNonLocalhost ? 'Recording unavailable over HTTP; use text input only' : 'Microphone unavailable';

        } else {
            // If connected, enable record button
            const wsHandler = getWebSocketHandler();
            if (wsHandler && wsHandler.isConnected()) {
                recordBtn.disabled = false;
                recordBtn.title = 'Start Recording';
            }
        }
    }

    // Add chat message
    addChatMessage(content, isUser = false) {
        const chatStream = document.getElementById('chatStream');
        if (!chatStream) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user' : 'ai'}`;
        messageDiv.innerHTML = `<div class="message-bubble">${content}</div>`;
        chatStream.appendChild(messageDiv);

        // Scroll to bottom
        chatStream.scrollTop = chatStream.scrollHeight;
    }

    // Switch background
    switchBackground() {
        this.currentBackgroundIndex = (this.currentBackgroundIndex + 1) % this.backgroundImages.length;
        const backgroundContainer = document.querySelector('.background-container');
        if (backgroundContainer) {
            backgroundContainer.style.backgroundImage = `url('./images/${this.backgroundImages[this.currentBackgroundIndex]}')`;
        }
        localStorage.setItem('backgroundIndex', this.currentBackgroundIndex);
    }

    // Switch Live2D model
    switchLive2DModel() {
        const modelSelect = document.getElementById('live2dModelSelect');
        if (!modelSelect) {
            console.error('Model selection dropdown not found');
            return;
        }

        const selectedModel = modelSelect.value;
        const app = window.chatApp;

        if (app && app.live2dManager) {
            app.live2dManager.switchModel(selectedModel)
                .then(success => {
                    if (success) {
                        this.addChatMessage(`Switched to model: ${selectedModel}`, false);
                    } else {
                        this.addChatMessage('Model switch failed', false);
                    }
                })
                .catch(error => {
                    console.error('Model switch error:', error);
                    this.addChatMessage('Model switch error', false);
                });
        } else {
            this.addChatMessage('Live2D manager not initialized', false);
        }
    }

    // Show modal
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    // Hide modal
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Switch tab
    switchTab(tabName) {
        // Remove active class from all tabs
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        // Activate selected tab
        const activeTabBtn = document.querySelector(`[data-tab="${tabName}"]`);
        const activeTabContent = document.getElementById(`${tabName}Tab`);

        if (activeTabBtn && activeTabContent) {
            activeTabBtn.classList.add('active');
            activeTabContent.classList.add('active');
        }
    }

    applyWakewordConfig(config = {}) {
        const wakewordEnabledInput = document.getElementById('wakewordEnabled');
        const wakewordListInput = document.getElementById('wakewordList');

        if (!wakewordEnabledInput || !wakewordListInput) {
            return;
        }

        const wakeWords = Array.isArray(config.wakeWords)
            ? config.wakeWords.filter(item => typeof item === 'string' && item.trim())
            : [];

        wakewordEnabledInput.value = config.enabled === false ? 'false' : 'true';
        wakewordListInput.value = wakeWords.join('\n');
        saveConfig();
    }

    async handleApplyWakeword() {
        const wakewordEnabledInput = document.getElementById('wakewordEnabled');
        const wakewordListInput = document.getElementById('wakewordList');
        const wakewordWsUrlInput = document.getElementById('wakewordWsUrl');
        if (!wakewordEnabledInput || !wakewordListInput) {
            return;
        }

        const wakeWords = wakewordListInput.value
            .split(/\r?\n/u)
            .map(item => item.trim())
            .filter(Boolean)
            .filter((item, index, items) => items.indexOf(item) === index);

        const payload = {
            enabled: wakewordEnabledInput.value !== 'false',
            wakeWords,
        };

        if (payload.enabled && payload.wakeWords.length === 0) {
            this.addChatMessage('At least one wake word is required when enabling wake word detection.', false);
            return;
        }

        const applyWakewordBtn = document.getElementById('applyWakewordBtn');
        if (applyWakewordBtn) {
            applyWakewordBtn.disabled = true;
            applyWakewordBtn.textContent = 'Applying...';
        }

        try {
            // Save address to localStorage
            if (wakewordWsUrlInput && wakewordWsUrlInput.value.trim()) {
                localStorage.setItem('xz_tester_wakewordWsUrl', wakewordWsUrlInput.value.trim());
            }

            // Compare new address with current connection address
            const newWsUrl = localStorage.getItem('xz_tester_wakewordWsUrl');
            const currentWsUrl = getWakewordBridgeUrl();
            const urlChanged = newWsUrl !== currentWsUrl;

            if (urlChanged) {
                // Address changed, please confirm
                const shouldRestart = window.confirm('Address changed. Continue? (This will disconnect the old connection and reconnect)');
                if (!shouldRestart) {
                    // Restore old address from localStorage
                    localStorage.setItem('xz_tester_wakewordWsUrl', currentWsUrl);
                    this.addChatMessage('Address change cancelled.', false);
                    return;
                }

                // Disconnect old connection
                stopWakewordBridgeListener();

                // Start new connection (automatically use new address)
                startWakewordBridgeListener();

                // Wait for bridge_connected
                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Connection to new server timed out'));
                    }, 5000);

                    onNextBridgeConnected(() => {
                        clearTimeout(timeout);
                        resolve();
                    });
                });

                // Send config and restart
                await requestWakewordBridge('set_wakeword_config', payload);
                this.applyWakewordConfig(payload);
                await requestWakewordBridge('restart_wakeword_service');
                this.addChatMessage('Wake word config saved, restarting wake word service.', false);
            } else {
                // Address unchanged: operate on current connection
                const response = await requestWakewordBridge('set_wakeword_config', payload);
                this.applyWakewordConfig(response.payload || payload);

                const shouldRestart = window.confirm('Wake word saved. Restart the wake word service now to apply changes?');
                if (!shouldRestart) {
                    this.addChatMessage('Wake word config saved. Restart the service manually later for changes to take effect.', false);
                    return;
                }

                await requestWakewordBridge('restart_wakeword_service');
                this.addChatMessage('Wake word config saved, restarting wake word service.', false);
            }
        } catch (error) {
            this.addChatMessage(`Failed to apply wake word: ${error.message}`, false);
        } finally {
            if (applyWakewordBtn) {
                applyWakewordBtn.disabled = false;
                applyWakewordBtn.textContent = 'Apply Wake Word';
            }
        }
    }

    // Start AI chat session after connection
    startAIChatSession() {
        this.addChatMessage('Connection successful, start chatting~😊', false);
        // Check microphone availability and show error messages if needed
        if (!window.microphoneAvailable) {
            if (window.isHttpNonLocalhost) {
                this.addChatMessage('⚠️ Recording is unavailable over HTTP; text interaction only', false);
            } else {
                this.addChatMessage('⚠️ Microphone unavailable. Check permissions. Text-only interaction enabled.', false);
            }
        }
        // Start recording only if microphone is available
        if (window.microphoneAvailable) {
            const recordBtn = document.getElementById('recordBtn');
            if (recordBtn) {
                recordBtn.click();
            }
        }
        // Start camera only if camera is available (bound with verification code)
        if (window.cameraAvailable && typeof window.startCamera === 'function') {
            window.startCamera().then(success => {
                if (success) {
                    const cameraBtn = document.getElementById('cameraBtn');
                    if (cameraBtn) {
                        cameraBtn.classList.add('camera-active');
                        cameraBtn.querySelector('.btn-text').textContent = 'Close';
                    }
                } else {
                    this.addChatMessage('⚠️ Camera startup failed, possibly denied by browser', false);
                }
            }).catch(error => {
                log(`Camera startup exception: ${error.message}`, 'error');
            });
        }
    }

    // Handle connect button click
    async handleConnect() {
        const wsHandler = getWebSocketHandler();
        if (this.isConnecting || (wsHandler && wsHandler.isConnected())) {
            log('Connection exists or is in progress, ignoring this dial request', 'info');
            return;
        }

        this.isConnecting = true;
        console.log('handleConnect called');

        try {
            // Switch to device settings tab
            this.switchTab('device');

            // Wait for DOM update
            await new Promise(resolve => setTimeout(resolve, 50));

            const otaUrlInput = document.getElementById('otaUrl');

            console.log('otaUrl element:', otaUrlInput);

            if (!otaUrlInput || !otaUrlInput.value) {
                this.addChatMessage('Please enter the OTA server address', false);
                return;
            }

            const otaUrl = otaUrlInput.value;
            console.log('otaUrl value:', otaUrl);

            // Update dial button state to connecting
            const dialBtn = document.getElementById('dialBtn');
            if (dialBtn) {
                dialBtn.classList.add('dial-active');
                dialBtn.querySelector('.btn-text').textContent = 'Connecting...';
                dialBtn.disabled = true;
            }

            // Show connecting message
            this.addChatMessage('Connecting to server...', false);

            const chatIpt = document.getElementById('chatIpt');
            if (chatIpt) {
                chatIpt.style.display = 'flex';
            }

            // Get WebSocket handler instance
            // Register connection state callback BEFORE connecting
            wsHandler.onConnectionStateChange = (isConnected) => {
                this.updateConnectionUI(isConnected);
                this.updateDialButton(isConnected);
            };

            // Register chat message callback BEFORE connecting
            wsHandler.onChatMessage = (text, isUser) => {
                this.addChatMessage(text, isUser);
            };

            // Register record button state callback BEFORE connecting
            wsHandler.onRecordButtonStateChange = (isRecording) => {
                const recordBtn = document.getElementById('recordBtn');
                if (recordBtn) {
                    if (isRecording) {
                        recordBtn.classList.add('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Recording';
                    } else {
                        recordBtn.classList.remove('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Record';
                    }
                }
            };

            const isConnected = await wsHandler.connect();

            if (isConnected) {
                // Check microphone availability (check again after connection)
                const { checkMicrophoneAvailability } = await import('../core/audio/recorder.js?v=0205');
                const micAvailable = await checkMicrophoneAvailability();

                if (!micAvailable) {
                    const isHttp = window.isHttpNonLocalhost;
                    if (isHttp) {
                        this.addChatMessage('⚠️ Recording is unavailable over HTTP; text interaction only', false);
                    }
                    // Update global state
                    window.microphoneAvailable = false;
                }

                // Update dial button state
                const dialBtn = document.getElementById('dialBtn');
                if (dialBtn) {
                    if (!this.dialBtnDisabled) {
                        dialBtn.disabled = false;
                    }
                    dialBtn.querySelector('.btn-text').textContent = 'Hang up';
                    dialBtn.classList.add('dial-active');
                }

                this.hideModal('settingsModal');
            } else {
                throw new Error('OTA connection failed');
            }
        } catch (error) {
            console.error('Connection error details:', {
                message: error.message,
                stack: error.stack,
                name: error.name
            });

            // Show error message
            const errorMessage = error.message.includes('Cannot set properties of null')
                ? 'Connection failed: check device connection'
                : `Connection failed: ${error.message}`;

            this.addChatMessage(errorMessage, false);

            // Restore dial button state
            const dialBtn = document.getElementById('dialBtn');
            if (dialBtn) {
                if (!this.dialBtnDisabled) {
                    dialBtn.disabled = false;
                }
                dialBtn.querySelector('.btn-text').textContent = 'Dial';
                dialBtn.classList.remove('dial-active');
                console.log('Dial button state restored successfully');
            }
        } finally {
            this.isConnecting = false;
        }
    }

    async triggerWakewordDial(wakeWord = 'wake word') {
        const wsHandler = getWebSocketHandler();
        const now = Date.now();

        if (wsHandler && wsHandler.isConnected()) {
            log('Page already connected, ignoring auto-dial', 'info');
            return false;
        }

        if (this.isConnecting || this.dialBtnDisabled) {
            log('Page is connecting, ignoring duplicate wake', 'info');
            return false;
        }

        if (now - this.lastWakewordDialTime < 3000) {
            log('Wake trigger too frequent, ignoring this auto-dial', 'warning');
            return false;
        }

        this.lastWakewordDialTime = now;
        this.addChatMessage(`Wake word "${wakeWord}" detected, connecting to server...`, false);
        await this.handleConnect();
        return true;
    }

    // Add MCP tool
    addMCPTool() {
        const mcpToolsList = document.getElementById('mcpToolsList');
        if (!mcpToolsList) return;

        const toolId = `mcp-tool-${Date.now()}`;
        const toolDiv = document.createElement('div');
        toolDiv.className = 'properties-container';
        toolDiv.innerHTML = `
            <div class="property-item">
                <input type="text" placeholder="Tool Name" value="New Tool">
                <input type="text" placeholder="Tool description" value="Tool description">
                <button class="remove-property" onclick="uiController.removeMCPTool('${toolId}')">Delete </button>
            </div>
        `;

        mcpToolsList.appendChild(toolDiv);
    }

    // Remove MCP tool
    removeMCPTool(toolId) {
        const toolElement = document.getElementById(toolId);
        if (toolElement) {
            toolElement.remove();
        }
    }

    // Update audio statistics display
    updateAudioStats() {
        const audioPlayer = getAudioPlayer();
        if (!audioPlayer) return;

        const stats = audioPlayer.getAudioStats();
        // Here can add audio statistics UI update logic
    }

    // Start audio statistics monitor
    startAudioStatsMonitor() {
        // Update audio statistics every 100ms
        this.audioStatsTimer = setInterval(() => {
            this.updateAudioStats();
        }, 100);
    }

    // Stop audio statistics monitor
    stopAudioStatsMonitor() {
        if (this.audioStatsTimer) {
            clearInterval(this.audioStatsTimer);
            this.audioStatsTimer = null;
        }
    }

    // Draw audio visualizer waveform
    drawVisualizer(dataArray) {
        if (!this.visualizerContext || !this.visualizerCanvas) return;

        this.visualizerContext.fillStyle = '#fafafa';
        this.visualizerContext.fillRect(0, 0, this.visualizerCanvas.width, this.visualizerCanvas.height);

        const barWidth = (this.visualizerCanvas.width / dataArray.length) * 2.5;
        let barHeight;
        let x = 0;

        for (let i = 0; i < dataArray.length; i++) {
            barHeight = dataArray[i] / 2;

            // Create gradient color: from purple to blue to green
            const gradient = this.visualizerContext.createLinearGradient(0, 0, 0, this.visualizerCanvas.height);
            gradient.addColorStop(0, '#8e44ad');
            gradient.addColorStop(0.5, '#3498db');
            gradient.addColorStop(1, '#1abc9c');

            this.visualizerContext.fillStyle = gradient;
            this.visualizerContext.fillRect(x, this.visualizerCanvas.height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
        }
    }

    // Update session status UI
    updateSessionStatus(isSpeaking) {
        // Here can add session status UI update logic
        // For example: update Live2D model's mouth movement status
    }

    // Update session emotion
    updateSessionEmotion(emoji) {
        // Here can add emotion update logic
        // For example: display emoji in status indicator
    }
}

// Create singleton instance
export const uiController = new UIController();

// Export class for module usage
export { UIController };
