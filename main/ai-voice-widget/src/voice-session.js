// AI Voice Widget - WebSocket session scaffold
// 预留给 xiaozhi/后端长连接语音通道使用。

export class VoiceSession {
    constructor({ url, onOpen, onClose, onText, onAudio, onError } = {}) {
        this.url = url;
        this.ws = null;
        this.onOpen = onOpen;
        this.onClose = onClose;
        this.onText = onText;
        this.onAudio = onAudio;
        this.onError = onError;
    }

    connect() {
        if (!this.url) throw new Error('VoiceSession url is required');
        this.ws = new WebSocket(this.url);
        this.ws.binaryType = 'arraybuffer';
        this.ws.onopen = () => this.onOpen?.();
        this.ws.onclose = (e) => this.onClose?.(e);
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
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    sendBinary(data) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(data);
        }
    }

    close() {
        try { this.ws?.close(); } catch (e) {}
        this.ws = null;
    }
}
