// DOM元素
const connectButton = document.getElementById('connectButton');
const serverUrlInput = document.getElementById('serverUrl');
const connectionStatus = document.getElementById('connectionStatus');
const messageInput = document.getElementById('messageInput');
const sendTextButton = document.getElementById('sendTextButton');
const recordButton = document.getElementById('recordButton');
const stopButton = document.getElementById('stopButton');
// 会话记录
const conversationDiv = document.getElementById('conversation');
const logContainer = document.getElementById('logContainer');
let visualizerCanvas = document.getElementById('audioVisualizer');

// ota 是否连接成功，修改成对应的样式
export function otaStatusStyle(flan) {
    if (flan) {
        document.getElementById('otaStatus').textContent = 'OTA已连接';
        document.getElementById('otaStatus').style.color = 'green';
    } else {
        document.getElementById('otaStatus').textContent = 'OTA未连接';
        document.getElementById('otaStatus').style.color = 'red';
    }
}

// ota 是否连接成功，修改成对应的样式
export function getLogContainer(flan) {
    return logContainer;
}

// 更新Opus库状态显示
export function updateScriptStatus(message, type) {
    const statusElement = document.getElementById('scriptStatus');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.className = `script-status ${type}`;
        statusElement.style.display = 'block';
        statusElement.style.width = 'auto';
    }
}

// 添加消息到会话记录
export function addMessage(text, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'server'}`;
    messageDiv.textContent = text;
    conversationDiv.appendChild(messageDiv);
    conversationDiv.scrollTop = conversationDiv.scrollHeight;
}

