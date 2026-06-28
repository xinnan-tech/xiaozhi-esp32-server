// AI Voice Widget - lightweight voice interaction component
// 当前版本：浏览器 ASR + speechSynthesis TTS + 状态回调；预留 VoiceSession 长连接。

import { VoiceSession } from './voice-session.js';

export function createVoiceWidget(options = {}) {
    return new VoiceWidget(options);
}

export class VoiceWidget {
    constructor({ onUserText, onStatus, onReplyStart, onReplyEnd, onError, voiceEnabled = true, sessionUrl = '' } = {}) {
        this.onUserText = onUserText;
        this.onStatus = onStatus;
        this.onReplyStart = onReplyStart;
        this.onReplyEnd = onReplyEnd;
        this.onError = onError;
        this.voiceEnabled = voiceEnabled;
        this.sessionUrl = sessionUrl;
        this.recognition = null;
        this.listening = false;
        this.session = null;
    }

    setVoiceEnabled(enabled) {
        this.voiceEnabled = !!enabled;
        if (!this.voiceEnabled) this.stopSpeaking();
    }

    async startListening() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            const err = new Error('当前浏览器不支持语音输入，请使用 Chrome/Edge，或先用文字输入。');
            this.onError?.(err);
            throw err;
        }
        if (this.listening && this.recognition) {
            this.recognition.stop();
            return;
        }
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'zh-CN';
        this.recognition.interimResults = true;
        this.recognition.continuous = false;
        this.recognition.maxAlternatives = 1;
        this.listening = true;
        this.onStatus?.('listening', '正在听你说话...');
        let finalText = '';
        this.recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) finalText += transcript;
                else interim += transcript;
            }
            this.onStatus?.('listening', finalText || interim || '正在听你说话...');
        };
        this.recognition.onerror = (event) => {
            this.onError?.(new Error(event.error || '语音识别失败'));
        };
        this.recognition.onend = () => {
            this.listening = false;
            this.onStatus?.('', '待命中 · 可语音或打字');
            const text = finalText.trim();
            if (text) this.onUserText?.(text);
        };
        this.recognition.start();
    }

    speak(text) {
        if (!this.voiceEnabled || !window.speechSynthesis || !text) return;
        this.stopSpeaking();
        const utter = new SpeechSynthesisUtterance(String(text).replace(/<[^>]+>/g, '').slice(0, 220));
        utter.lang = 'zh-CN';
        utter.rate = 1.05;
        utter.pitch = 1.0;
        utter.onstart = () => {
            this.onStatus?.('speaking', '正在回复...');
            this.onReplyStart?.();
        };
        utter.onend = () => {
            this.onStatus?.('', '待命中 · 可语音或打字');
            this.onReplyEnd?.();
        };
        window.speechSynthesis.speak(utter);
    }

    stopSpeaking() {
        try { window.speechSynthesis?.cancel(); } catch (e) {}
    }

    connectSession() {
        if (!this.sessionUrl) return null;
        this.session = new VoiceSession({
            url: this.sessionUrl,
            onOpen: () => this.onStatus?.('connected', '语音长连接已建立'),
            onClose: () => this.onStatus?.('', '语音长连接已关闭'),
            onText: (data) => this.onUserText?.(typeof data === 'string' ? data : (data.text || '')),
            onError: (e) => this.onError?.(e),
        });
        this.session.connect();
        return this.session;
    }

    destroy() {
        try { this.recognition?.stop(); } catch (e) {}
        this.stopSpeaking();
        this.session?.close();
    }
}
