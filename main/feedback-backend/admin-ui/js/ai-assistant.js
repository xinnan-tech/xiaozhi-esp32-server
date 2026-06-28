// AI 数字人助手 - 长连接持续对话数字人
import { api } from './api.js';
import { createVoiceWidget } from './voice-widget/voice-widget.js?v=20260625-longchat-default';

let lastUserMessage = '';
let lastAgentResult = null;
let voiceEnabled = true;
let voiceWidget = null;
let longChatEnabled = true;
let sending = false;
let live2dReady = false;
let live2dInitializing = false;
let sessionConnected = false;
let reconnectTimer = null;
let reconnectAttempts = 0;
const pendingMessages = [];
const conversationHistory = [];

export function initAiAssistant() {
    if (document.getElementById('aiAssistantFab')) return;
    const box = document.createElement('div');
    box.innerHTML = `
    <button id="aiAssistantFab" class="ai-fab" title="AI数字人助手"><span>AI</span></button>
    <div id="aiAssistantPanel" class="ai-panel ai-voice-panel">
        <div class="ai-head">
            <div>
                <strong>AI门店数字人</strong>
                <div class="muted" id="aiStatusText">待命中 · 可语音或打字</div>
            </div>
            <div class="ai-head-actions">
                <button id="aiAssistantExpand" class="ai-icon-btn" title="切换大屏数字人">⛶</button>
                <button id="aiAssistantClose" class="modal-close">&times;</button>
            </div>
        </div>
        <div class="ai-stage">
            <canvas id="live2d-stage" class="ai-live2d-canvas"></canvas>
            <div class="ai-stage-bg"></div>
            <div class="ai-face" id="aiFallbackFace">🤖</div>
            <div id="aiAvatar" class="ai-avatar live2d-avatar">
                <div class="ai-avatar-ring"></div>
                <div class="ai-wave"><span></span><span></span><span></span></div>
            </div>
            <div class="ai-stage-status">
                <span class="ai-status-dot"></span>
                <span id="aiStageStatusText">像客户反馈数字人一样，持续听你说话并帮你操作 CRM</span>
            </div>
        </div>
        <div class="ai-body">
            <div id="aiMessages" class="ai-messages">
                <div class="ai-msg ai-msg-bot">你好，我是门店AI数字人。你可以直接说：<br>创建客户常玉亮手机号13020109833<br>创建产品冰蚕乌酒价格50<br>明天下午2点约李爱媛做乌蛇<br>查客户尾号9833套餐还剩几次</div>
            </div>
            <div class="ai-quick">
                <button data-q="CRM概览">CRM概览</button>
                <button data-q="员工KPI">员工KPI</button>
                <button data-q="预约日历">预约日历</button>
                <button data-q="查客户尾号9833">查客户</button>
            </div>
            <div class="ai-input-row">
                <input id="aiInput" class="form-input" placeholder="输入或语音说出你的需求">
                <button id="aiMic" class="btn btn-secondary btn-sm" title="按一下说话">🎙️</button>
                <button id="aiLongChat" class="btn btn-secondary btn-sm active" title="长聊默认开启，点击暂停">长聊中</button>
                <button id="aiVoiceToggle" class="btn btn-secondary btn-sm" title="语音播报开关">🔊</button>
                <button id="aiSend" class="btn btn-primary btn-sm">发送</button>
            </div>
        </div>
    </div>`;
    document.body.appendChild(box);

    const panel = document.getElementById('aiAssistantPanel');
    const fab = document.getElementById('aiAssistantFab');
    fab.onclick = () => {
        panel.classList.toggle('open');
        if (panel.classList.contains('open')) initLive2DAvatar();
    };
    document.getElementById('aiAssistantClose').onclick = () => panel.classList.remove('open');
    document.getElementById('aiAssistantExpand').onclick = () => {
        panel.classList.toggle('expanded');
        setTimeout(() => window.aiLive2dManager?.resize?.(), 80);
    };
    document.getElementById('aiSend').onclick = sendAiMessage;
    document.getElementById('aiMic').onclick = startSpeechInput;
    document.getElementById('aiLongChat').onclick = toggleLongChat;
    document.getElementById('aiVoiceToggle').onclick = () => {
        voiceEnabled = !voiceEnabled;
        voiceWidget?.setVoiceEnabled(voiceEnabled);
        document.getElementById('aiVoiceToggle').textContent = voiceEnabled ? '🔊' : '🔇';
    };
    document.getElementById('aiInput').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') sendAiMessage();
    });
    document.querySelectorAll('.ai-quick button').forEach(btn => {
        btn.onclick = () => {
            document.getElementById('aiInput').value = btn.dataset.q;
            sendAiMessage();
        };
    });
    voiceWidget = createVoiceWidget({
        voiceEnabled,
        sessionUrl: buildAgentWsUrl(),
        onUserText(text) {
            if (!text) return;
            document.getElementById('aiInput').value = text;
            sendAiMessage(text, { fromVoice: true });
        },
        onSessionOpen() {
            sessionConnected = true;
            reconnectAttempts = 0;
        },
        onSessionClose() {
            sessionConnected = false;
            scheduleSessionReconnect();
        },
        onSessionMessage(data) { handleSessionMessage(data); },
        onStatus(state, text) { setAiState(state, text); },
        onReplyStart() {
            try { window.aiLive2dManager?.startTalking?.(); window.aiLive2dManager?.motion?.('Tap'); } catch(e) {}
        },
        onReplyEnd() { try { window.aiLive2dManager?.stopTalking?.(); } catch(e) {} },
        onError(err) { showVoiceError(err); },
    });
    connectLongSession();
    initLive2DAvatar();
    startDefaultLongChat();
}

function startDefaultLongChat() {
    const btn = document.getElementById('aiLongChat');
    longChatEnabled = true;
    if (btn) {
        btn.textContent = '长聊中';
        btn.classList.add('active');
        btn.title = '长聊默认开启，点击暂停';
    }
    setAiState('listening', '长聊中 · 我会持续听你说话');
    if (typeof voiceWidget?.startContinuous === 'function') {
        voiceWidget.startContinuous().catch((e) => {
            longChatEnabled = false;
            if (btn) {
                btn.textContent = '长聊';
                btn.classList.remove('active');
                btn.title = '开启长聊';
            }
            showVoiceError(e);
        });
    } else {
        longChatEnabled = false;
        const msg = '语音组件版本过旧，请强制刷新页面后重试';
        if (btn) {
            btn.textContent = '长聊';
            btn.classList.remove('active');
            btn.title = msg;
        }
        showVoiceError(new Error(msg));
    }
}

function buildAgentWsUrl() {
    const token = localStorage.getItem('feedback_admin_token') || '';
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'feedback-admin.new123.vip'
        ? 'feedback-admin.new123.vip:8443'
        : window.location.host;
    const url = new URL(`${scheme}//${host}/api/v1/agent/chat/ws`);
    if (token) url.searchParams.set('token', token);
    return url.toString();
}

function connectLongSession() {
    if (!voiceWidget) return;
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
    try {
        voiceWidget.connectSession(buildAgentWsUrl());
    } catch (e) {
        showVoiceError(e);
        scheduleSessionReconnect();
    }
}

function scheduleSessionReconnect() {
    if (reconnectTimer || !voiceWidget) return;
    const delay = Math.min(10000, 1000 * Math.max(1, ++reconnectAttempts));
    reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        connectLongSession();
    }, delay);
}

function handleSessionMessage(data) {
    if (!data) return;
    if (typeof data === 'string') {
        appendMessage(data, 'bot', false, true);
        voiceWidget?.speak(data);
        return;
    }
    if (data.type === 'hello') {
        setAiState('', '长连接已就绪 · 可语音或打字');
        return;
    }
    if (data.type === 'thinking') {
        removeThinking();
        appendMessage(data.text || '正在思考和查询...', 'bot', true);
        setAiState('thinking', data.text || '正在思考...');
        voiceWidget?.pauseContinuous(data.text || '正在思考...');
        return;
    }
    if (data.type === 'reply') {
        removeThinking();
        const result = data.data || {};
        lastAgentResult = result;
        const reply = data.text || result.reply || '已处理';
        conversationHistory.push({ role: 'assistant', text: reply });
        appendMessage(reply, 'bot', false, true);
        voiceWidget?.speak(reply);
        if (result.action && window.FormCopilot?.execute(result.action)) {
            const msg = '我已打开对应表单，并填入已识别的信息。请确认后保存。';
            conversationHistory.push({ role: 'assistant', text: msg });
            appendMessage(msg, 'bot');
            voiceWidget?.speak(msg);
        } else if (result.route) {
            appendRoute(result.route);
        }
        sending = false;
        if (!voiceWidget?.speaking) {
            setAiState(longChatEnabled ? 'listening' : '', longChatEnabled ? '长聊中 · 我会持续听你说话' : '待命中 · 可语音或打字');
            voiceWidget?.resumeContinuous();
        }
        flushPendingMessages();
        return;
    }
    if (data.type === 'error') {
        removeThinking();
        const msg = data.text || '长连接处理失败';
        appendMessage(msg, 'bot', false, true);
        voiceWidget?.speak(msg);
        sending = false;
        flushPendingMessages();
    }
}

async function initLive2DAvatar() {
    if (live2dReady || live2dInitializing) return;
    if (!window.Live2DManager || !window.PIXI?.live2d) return;
    live2dInitializing = true;
    try {
        window.chatApp = window.chatApp || {};
        window.chatApp.audioPlayer = null;
        const manager = new window.Live2DManager();
        window.aiLive2dManager = manager;
        await manager.initializeLive2D();
        live2dReady = true;
        document.getElementById('aiFallbackFace')?.classList.add('hidden');
        document.getElementById('aiAvatar')?.classList.add('live2d-ready');
        setAiState('', '数字人已就绪 · 可语音或打字');
    } catch (e) {
        console.warn('[AI Live2D] 初始化失败，使用轻量头像', e);
    } finally {
        live2dInitializing = false;
    }
}

function setAiState(state, text) {
    const avatar = document.getElementById('aiAvatar');
    const status = document.getElementById('aiStatusText');
    const stageStatus = document.getElementById('aiStageStatusText');
    if (!avatar) return;
    avatar.classList.remove('listening', 'thinking', 'speaking');
    if (state) avatar.classList.add(state);
    const statusText = text || (longChatEnabled ? '长聊中 · 我会持续听你说话' : '待命中 · 可语音或打字');
    if (status) status.textContent = statusText;
    if (stageStatus) stageStatus.textContent = statusText;
}

function showVoiceError(err) {
    const msg = err?.message || String(err || '语音输入异常');
    if (['aborted', 'no-speech'].includes(msg)) return;
    appendMessage(msg, 'bot', false, true);
}

async function toggleLongChat() {
    const btn = document.getElementById('aiLongChat');
    try {
        if (longChatEnabled) {
            longChatEnabled = false;
            voiceWidget?.stopListening?.(true);
            if (btn) {
                btn.textContent = '长聊';
                btn.classList.remove('active');
                btn.title = '开启长聊';
            }
            setAiState('', '长聊已暂停 · 可打字或点长聊继续');
            return;
        }
        longChatEnabled = true;
        if (btn) {
            btn.textContent = '长聊中';
            btn.classList.add('active');
            btn.title = '长聊默认开启，点击暂停';
        }
        setAiState('listening', '长聊中 · 我会持续听你说话');
        if (typeof voiceWidget?.startContinuous !== 'function') {
            throw new Error('语音组件版本过旧，请强制刷新页面后重试');
        }
        await voiceWidget.startContinuous();
    } catch (e) {
        longChatEnabled = false;
        if (btn) {
            btn.textContent = '长聊';
            btn.classList.remove('active');
            btn.title = '开启长聊';
        }
        showVoiceError(e);
        voiceWidget?.speak(e.message || '语音输入不可用');
    }
}

async function startSpeechInput() {
    if (longChatEnabled) {
        toggleLongChat();
        return;
    }
    const mic = document.getElementById('aiMic');
    try {
        mic.textContent = '⏺';
        await voiceWidget?.startListening();
    } catch (e) {
        showVoiceError(e);
        voiceWidget?.speak(e.message || '语音输入不可用');
    } finally {
        setTimeout(() => { mic.textContent = '🎙️'; }, 500);
    }
}

async function sendAiMessage(forcedText = '', options = {}) {
    const input = document.getElementById('aiInput');
    const text = (forcedText || input.value || '').trim();
    if (!text) return;
    if (input.value.trim() === text) input.value = '';
    if (sending) {
        pendingMessages.push({ text, options });
        setAiState('thinking', '已收到，上一条处理完马上继续...');
        return;
    }
    sending = true;
    lastUserMessage = text;
    conversationHistory.push({ role: 'user', text });
    appendMessage(text, 'user');
    const localReply = window.FormCopilot?.handleUserMessage(text);
    if (localReply) {
        conversationHistory.push({ role: 'assistant', text: localReply });
        appendMessage(localReply, 'bot', false, true);
        voiceWidget?.speak(localReply);
        sending = false;
        flushPendingMessages();
        return;
    }
    voiceWidget?.pauseContinuous('正在思考...');
    setAiState('thinking', sessionConnected ? '正在通过长连接思考...' : '长连接重连中，先用普通接口处理...');

    if (sessionConnected && voiceWidget?.sendText(text)) {
        appendMessage('正在思考和查询...', 'bot', true);
        return;
    }

    appendMessage('正在思考和查询...', 'bot', true);
    try {
        const res = await api.agentChat(text, conversationHistory.slice(-12));
        removeThinking();
        const data = res.data || {};
        lastAgentResult = data;
        const reply = data.reply || '已处理';
        conversationHistory.push({ role: 'assistant', text: reply });
        appendMessage(reply, 'bot', false, true);
        voiceWidget?.speak(reply);
        if (data.action && window.FormCopilot?.execute(data.action)) {
            const msg = '我已打开对应表单，并填入已识别的信息。请确认后保存。';
            conversationHistory.push({ role: 'assistant', text: msg });
            appendMessage(msg, 'bot');
            voiceWidget?.speak(msg);
        } else if (data.route) {
            appendRoute(data.route);
        }
    } catch (e) {
        removeThinking();
        const msg = `操作失败：${e.message || e}`;
        appendMessage(msg, 'bot', false, true);
        voiceWidget?.speak(msg);
    } finally {
        sending = false;
        if (!voiceWidget?.speaking) {
            setAiState(longChatEnabled ? 'listening' : '', longChatEnabled ? '长聊中 · 我会持续听你说话' : '待命中 · 可语音或打字');
            voiceWidget?.resumeContinuous();
        }
        flushPendingMessages();
    }
}

function flushPendingMessages() {
    if (sending || pendingMessages.length === 0) return;
    const next = pendingMessages.shift();
    setTimeout(() => sendAiMessage(next.text, next.options), 80);
}

function appendMessage(text, who, thinking = false, feedback = false) {
    const el = document.getElementById('aiMessages');
    const div = document.createElement('div');
    div.className = `ai-msg ai-msg-${who}` + (thinking ? ' ai-thinking' : '');
    div.innerHTML = escapeHtml(text).replace(/\n/g, '<br>') + (feedback ? '<div class="ai-feedback"><button data-rate="like">👍</button><button data-rate="dislike">👎</button></div>' : '');
    el.appendChild(div);
    div.querySelectorAll('[data-rate]').forEach(btn => btn.onclick = () => submitAiFeedback(btn.dataset.rate, btn));
    el.scrollTop = el.scrollHeight;
}

async function submitAiFeedback(rating, btn) {
    try {
        await api.agentFeedback({
            message: lastUserMessage,
            reply: lastAgentResult?.reply || '',
            intent: lastAgentResult?.intent || '',
            trace: lastAgentResult?.trace || [],
            rating,
        });
        btn.parentElement.innerHTML = rating === 'like' ? '已点赞，感谢反馈' : '已记录失败案例，我会用于复盘修复';
    } catch (e) {
        btn.parentElement.innerHTML = '反馈提交失败';
    }
}

function removeThinking() {
    document.querySelectorAll('.ai-thinking').forEach(el => el.remove());
}

function appendRoute(route) {
    const el = document.getElementById('aiMessages');
    const div = document.createElement('div');
    div.className = 'ai-msg ai-msg-bot';
    div.innerHTML = `<button class="btn btn-secondary btn-sm">打开${route}</button>`;
    div.querySelector('button').onclick = () => { window.location.hash = `#/${route}`; };
    el.appendChild(div);
    el.scrollTop = el.scrollHeight;
}
