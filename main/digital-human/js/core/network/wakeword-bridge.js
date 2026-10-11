import { uiController } from '../../ui/controller.js?v=0205';
import { log } from '../../utils/logger.js?v=0205';

let wakewordSocket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let shouldReconnect = true;
let wakewordRequestSeq = 0;
let onNextBridgeConnectedCallback = null;

const pendingWakewordRequests = new Map();

export function startWakewordBridgeListener() {
    if (wakewordSocket) {
        return wakewordSocket;
    }

    shouldReconnect = true;
    log('Connecting to local wake event bridge...', 'info');
    tryConnect();
    return wakewordSocket;
}

function tryConnect() {
    const bridgeUrl = buildWakewordBridgeUrl();

    try {
        wakewordSocket = new WebSocket(bridgeUrl);
        wakewordSocket.onopen = () => {
            reconnectAttempts = 0;
            log(`Local wake event bridge connected: ${bridgeUrl}`, 'success');
            // Auto-save address after successful connection, persists after refresh
            localStorage.setItem('xz_tester_wakewordWsUrl', bridgeUrl);
            const urlInput = document.getElementById('wakewordWsUrl');
            if (urlInput) urlInput.value = bridgeUrl;
        };

        wakewordSocket.onerror = () => {
            log(`Local wake event bridge connection failed: ${bridgeUrl}`, 'error');
        };

        wakewordSocket.onmessage = async (event) => {
            try {
                const message = parseWakewordBridgeMessage(event.data);
                if (message.requestId && pendingWakewordRequests.has(message.requestId)) {
                    settleWakewordRequest(message);
                    return;
                }

                if (message.success === false) {
                    log(`Local wake event bridge returned error: ${message.error || 'Unknown error'}`, 'error');
                    return;
                }

                if (message.type === 'bridge_connected') {
                    log('Local wake word listener ready', 'info');
                    if (onNextBridgeConnectedCallback) {
                        const cb = onNextBridgeConnectedCallback;
                        onNextBridgeConnectedCallback = null;
                        cb(message);
                    }
                    return;
                }

                if (message.type === 'service_ready') {
                    log('Local wake word service started', 'info');
                    return;
                }

                if (message.type === 'wakeword_config') {
                    uiController.applyWakewordConfig(message.payload || {});
                    log('Local wake word configuration synced', 'info');
                    return;
                }

                if (message.type === 'service_stopping') {
                    log('Local wake word service stopping', 'warning');
                    return;
                }

                if (message.type === 'wake_word_detected') {
                    const wakeWord = message.payload?.wake_word || 'wake word';
                    log(`Local wake event detected: ${wakeWord}`, 'info');
                    await uiController.triggerWakewordDial(wakeWord);
                }
            } catch (error) {
                log(`Failed to parse local wake word event: ${error.message}`, 'error');
            }
        };

        wakewordSocket.onclose = () => {
            if (wakewordSocket) {
                wakewordSocket = null;
            }

            rejectAllWakewordRequests('Local wake event bridge disconnected');

            if (!shouldReconnect) {
                return;
            }

            if (reconnectTimer) {
                return;
            }

            reconnectAttempts += 1;
            const delay = Math.min(1000 * reconnectAttempts, 5000);
            log(`Local wake event bridge will reconnect in ${delay}ms: ${bridgeUrl}`, 'warning');
            reconnectTimer = window.setTimeout(() => {
                reconnectTimer = null;
                tryConnect();
            }, delay);
        };

        return wakewordSocket;
    } catch (error) {
        log(`Failed to start local wake word listener: ${error.message}`, 'error');
        return null;
    }
}

export function stopWakewordBridgeListener() {
    shouldReconnect = false;

    if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    if (!wakewordSocket) {
        return;
    }

    wakewordSocket.onclose = null;
    wakewordSocket.close();
    wakewordSocket = null;
}

export function sendWakewordBridgeMessage(type, payload = {}, requestId = null) {
    if (!wakewordSocket || wakewordSocket.readyState !== WebSocket.OPEN) {
        log('Local wake event bridge not connected, cannot send message', 'warning');
        return false;
    }

    wakewordSocket.send(JSON.stringify({
        type,
        requestId,
        payload,
    }));
    return true;
}

export function requestWakewordBridge(type, payload = {}, timeout = 5000) {
    const requestId = `wakeword-${Date.now()}-${++wakewordRequestSeq}`;

    return new Promise((resolve, reject) => {
        const timer = window.setTimeout(() => {
            pendingWakewordRequests.delete(requestId);
            reject(new Error('Local wake service response timed out'));
        }, timeout);

        pendingWakewordRequests.set(requestId, { resolve, reject, timer });

        if (!sendWakewordBridgeMessage(type, payload, requestId)) {
            window.clearTimeout(timer);
            pendingWakewordRequests.delete(requestId);
            reject(new Error('Local wake event bridge not connected'));
        }
    });
}

export function getWakewordBridgeUrl() {
    if (wakewordSocket && wakewordSocket.url) {
        return wakewordSocket.url;
    }
    return buildWakewordBridgeUrl();
}

export function onNextBridgeConnected(callback) {
    onNextBridgeConnectedCallback = callback;
}

function buildWakewordBridgeUrl() {
    const configured = localStorage.getItem('xz_tester_wakewordWsUrl');
    if (configured && configured.trim()) {
        return configured.trim();
    }
    return 'ws://127.0.0.1:8006/wakeword-ws';
}

function parseWakewordBridgeMessage(rawData) {
    const message = JSON.parse(rawData);
    return {
        type: message.type || '',
        requestId: message.requestId || null,
        success: message.success !== false,
        payload: message.payload || {},
        error: message.error || null,
    };
}

function settleWakewordRequest(message) {
    const pendingRequest = pendingWakewordRequests.get(message.requestId);
    if (!pendingRequest) {
        return;
    }

    window.clearTimeout(pendingRequest.timer);
    pendingWakewordRequests.delete(message.requestId);

    if (message.success === false) {
        pendingRequest.reject(new Error(message.error || 'Local wake service returned failure'));
        return;
    }

    pendingRequest.resolve(message);
}

function rejectAllWakewordRequests(errorMessage) {
    pendingWakewordRequests.forEach((pendingRequest) => {
        window.clearTimeout(pendingRequest.timer);
        pendingRequest.reject(new Error(errorMessage));
    });
    pendingWakewordRequests.clear();
}