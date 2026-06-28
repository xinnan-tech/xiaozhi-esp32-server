// AI Voice Widget - WebSocket session scaffold
// 后台数字人长连接通道：文本持续会话 + 心跳 + 自动重连由上层控制。

export class VoiceSession {
    constructor({ url, onOpen, onClose, onText, onAudio, onError } = {}) {
        this.url = url;
        this.ws = null;
        this.onOpen = onOpen;
        this.onClose = onClose;
        this.onText = onText;
        this.onAudio = onAudio;
        this.onError = onError;
        this.heartbeatTimer = null;
    }

    get isOpen() {
        return this.ws?.readyState === WebSocket.OPEN;
    }

    connect() {
        if (!this.url) throw new Error('VoiceSession url is required');
        if (this.ws && [WebSocket.CONNECTING, WebSocket.OPEN].includes(this.ws.readyState)) return;
        this.ws = new WebSocket(this.url);
        this.ws.binaryType = 'arraybuffer';
        this.ws.onopen = () => {
            this._startHeartbeat();
            this.onOpen?.();
        };
        this.ws.onclose = (e) => {
            this._stopHeartbeat();
            this.onClose?.(e);
        };
        this.ws.onerror = (e) => this.onError?.(e);
        this.ws.onmessage = (event) => {
            if (typeof event.data === 'string') {
                let data = event.data;
                try { data = JSON.parse(event.data); } catch (e) {}
                this.onText?.(data);
            } else {
                this.onAudio?.(event.data);
            }
        };
    }

    sendJson(data) {
        if (this.isOpen) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    sendText(text) {
        return this.sendJson({ type: 'message', text });
    }

    sendBinary(data) {
        if (this.isOpen) {
            this.ws.send(data);
            return true;
        }
        return false;
    }

    close(code = 1000, reason = 'client close') {
        this._stopHeartbeat();
        try { this.ws?.close(code, reason); } catch (e) {}
        this.ws = null;
    }

    _startHeartbeat() {
        this._stopHeartbeat();
        this.heartbeatTimer = window.setInterval(() => {
            this.sendJson({ type: 'ping' });
        }, 25000);
    }

    _stopHeartbeat() {
        if (this.heartbeatTimer) {
            window.clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
}
