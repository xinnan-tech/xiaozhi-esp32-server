// AI Voice Widget - lightweight continuous voice interaction component
// 当前版本：浏览器 ASR + speechSynthesis TTS + 状态回调；可配合后台 WebSocket 长连接使用。

import { VoiceSession } from './voice-session.js';

export function createVoiceWidget(options = {}) {
    return new VoiceWidget(options);
}

export class VoiceWidget {
    constructor({ onUserText, onSessionMessage, onSessionOpen, onSessionClose, onStatus, onReplyStart, onReplyEnd, onError, voiceEnabled = true, sessionUrl = '' } = {}) {
        this.onUserText = onUserText;
        this.onSessionMessage = onSessionMessage;
        this.onSessionOpen = onSessionOpen;
        this.onSessionClose = onSessionClose;
        this.onStatus = onStatus;
        this.onReplyStart = onReplyStart;
        this.onReplyEnd = onReplyEnd;
        this.onError = onError;
        this.voiceEnabled = voiceEnabled;
        this.sessionUrl = sessionUrl;
        this.recognition = null;
        this.listening = false;
        this.session = null;
        this.continuousMode = false;
        this.manualStop = false;
        this.paused = false;
        this.speaking = false;
        this.restartTimer = null;
        this.restartDelay = 450;
    }

    setVoiceEnabled(enabled) {
        this.voiceEnabled = !!enabled;
        if (!this.voiceEnabled) this.stopSpeaking();
    }

    isContinuous() {
        return this.continuousMode && !this.manualStop;
    }

    async startListening(options = {}) {
        const continuous = !!options.continuous;
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            const err = new Error('当前浏览器不支持语音输入，请使用 Chrome/Edge，或先用文字输入。');
            this.onError?.(err);
            throw err;
        }
        if (this.listening && this.recognition) {
            if (continuous && this.continuousMode) return true;
            this.stopListening(false);
        }
        this._clearRestartTimer();
        this.manualStop = false;
        this.paused = false;

        const recognition = new SpeechRecognition();
        this.recognition = recognition;
        recognition.lang = 'zh-CN';
        recognition.interimResults = true;
        recognition.continuous = continuous;
        recognition.maxAlternatives = 1;
        this.listening = true;
        this.onStatus?.('listening', continuous ? '长聊中 · 我会持续听你说话' : '正在听你说话...');
        let finalText = '';

        recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    if (continuous) {
                        const text = transcript.trim();
                        if (text) this.onUserText?.(text);
                    } else {
                        finalText += transcript;
                    }
                } else {
                    interim += transcript;
                }
            }
            this.onStatus?.('listening', finalText || interim || (continuous ? '长聊中 · 我会持续听你说话' : '正在听你说话...'));
        };
        recognition.onstart = () => {
            this.listening = true;
            this.onStatus?.('listening', continuous ? '长聊中 · 我会持续听你说话' : '正在听你说话...');
        };
        recognition.onerror = (event) => {
            const error = event.error || '语音识别失败';
            // Chrome 在 stop()/切换页面/播放 TTS 时经常抛 aborted/no-speech，属于可恢复状态，不展示成聊天消息。
            if (['aborted', 'no-speech'].includes(error)) {
                this.onStatus?.('listening', this.continuousMode ? '长聊中 · 我会持续听你说话' : '待命中 · 可语音或打字');
                if (!this.manualStop && this.continuousMode && !this.paused && !this.speaking) {
                    this._scheduleRestart();
                }
                return;
            }
            this.onError?.(new Error(error));
        };
        recognition.onend = () => {
            this.listening = false;
            this.recognition = null;
            if (!continuous) {
                const text = finalText.trim();
                if (text) this.onUserText?.(text);
            }
            if (this.continuousMode && !this.manualStop && !this.paused && !this.speaking) {
                this._scheduleRestart();
            } else if (!this.speaking && !this.paused) {
                this.onStatus?.('', this.continuousMode ? '长聊已暂停' : '待命中 · 可语音或打字');
            }
        };
        try {
            recognition.start();
        } catch (err) {
            this.listening = false;
            this.recognition = null;
            if (continuous && !this.manualStop) this._scheduleRestart();
            else this.onError?.(err);
            return false;
        }
        return true;
    }

    async startContinuous() {
        this.continuousMode = true;
        this.manualStop = false;
        this.paused = false;
        return this.startListening({ continuous: true });
    }

    stopListening(manual = true) {
        this.manualStop = manual;
        if (manual) this.continuousMode = false;
        this._clearRestartTimer();
        try { this.recognition?.stop(); } catch (e) {}
        this.recognition = null;
        this.listening = false;
        if (manual) this.onStatus?.('', '待命中 · 可语音或打字');
    }

    pauseContinuous(text = '正在思考...') {
        if (!this.continuousMode) return;
        this.paused = true;
        this._clearRestartTimer();
        try { this.recognition?.stop(); } catch (e) {}
        this.onStatus?.('thinking', text);
    }

    resumeContinuous() {
        if (!this.continuousMode || this.manualStop || this.speaking) return;
        this.paused = false;
        this._scheduleRestart();
    }

    speak(text) {
        if (!this.voiceEnabled || !window.speechSynthesis || !text) {
            this.resumeContinuous();
            return;
        }
        this.stopSpeaking();
        this.speaking = true;
        this.pauseContinuous('AI正在回复...');
        const utter = new SpeechSynthesisUtterance(String(text).replace(/<[^>]+>/g, '').slice(0, 260));
        utter.lang = 'zh-CN';
        utter.rate = 1.05;
        utter.pitch = 1.0;
        utter.onstart = () => {
            this.onStatus?.('speaking', 'AI正在回复...');
            this.onReplyStart?.();
        };
        utter.onend = () => {
            this.speaking = false;
            this.paused = false;
            this.onStatus?.(this.continuousMode ? 'listening' : '', this.continuousMode ? '长聊中 · 我会持续听你说话' : '待命中 · 可语音或打字');
            this.onReplyEnd?.();
            this.resumeContinuous();
        };
        utter.onerror = () => {
            this.speaking = false;
            this.paused = false;
            this.onReplyEnd?.();
            this.resumeContinuous();
        };
        window.speechSynthesis.speak(utter);
    }

    stopSpeaking() {
        try { window.speechSynthesis?.cancel(); } catch (e) {}
        this.speaking = false;
    }

    connectSession(url = '') {
        if (url) this.sessionUrl = url;
        if (!this.sessionUrl) return null;
        if (this.session?.isOpen) return this.session;
        this.session = new VoiceSession({
            url: this.sessionUrl,
            onOpen: () => {
                this.onStatus?.('connected', '长连接已建立 · 可持续对话');
                this.onSessionOpen?.();
            },
            onClose: (event) => {
                this.onStatus?.('', this.continuousMode ? '长连接已断开 · 语音长聊仍可使用' : '长连接已关闭');
                this.onSessionClose?.(event);
            },
            onText: (data) => this.onSessionMessage?.(data),
            onError: (e) => this.onError?.(e),
        });
        this.session.connect();
        return this.session;
    }

    sendText(text) {
        return this.session?.sendText(text) || false;
    }

    destroy() {
        this.stopListening(true);
        this.stopSpeaking();
        this.session?.close();
    }

    _scheduleRestart() {
        if (!this.continuousMode || this.manualStop || this.paused || this.speaking || this.listening) return;
        this._clearRestartTimer();
        this.restartTimer = window.setTimeout(() => {
            this.restartTimer = null;
            if (this.continuousMode && !this.manualStop && !this.paused && !this.speaking && !this.listening) {
                this.startListening({ continuous: true }).catch(err => this.onError?.(err));
            }
        }, this.restartDelay);
    }

    _clearRestartTimer() {
        if (this.restartTimer) {
            window.clearTimeout(this.restartTimer);
            this.restartTimer = null;
        }
    }
}
