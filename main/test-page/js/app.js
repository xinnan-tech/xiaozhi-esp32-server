/**
 * 小智语音测试页
 * 通过 WebSocket 直连 xiaozhi-server，支持文字与语音对话。
 * 协议：hello 握手 -> listen detect（文字）/ 二进制 Opus（语音）-> tts 音频与状态
 */
(function () {
    'use strict';

    const INPUT_SAMPLE_RATE = 16000;   // 上行 Opus 采样率
    const FRAME_SAMPLES = 960;         // 60ms @ 16kHz
    const MAX_FRAME_SAMPLES = 5760;    // 解码缓冲区上限（120ms @ 48kHz）
    const MAX_PACKET_SIZE = 4000;

    const $ = (id) => document.getElementById(id);

    const els = {
        otaUrl: $('otaUrl'),
        wsUrl: $('wsUrl'),
        deviceId: $('deviceId'),
        token: $('token'),
        connectBtn: $('connectBtn'),
        disconnectBtn: $('disconnectBtn'),
        statusDot: $('statusDot'),
        statusText: $('statusText'),
        chat: $('chat'),
        micBtn: $('micBtn'),
        micLabel: $('micLabel'),
        textInput: $('textInput'),
        sendBtn: $('sendBtn'),
        log: $('log'),
        logCount: $('logCount')
    };

    const state = {
        ws: null,
        connected: false,
        sessionId: null,
        outputSampleRate: 24000,
        speaking: false,
        recording: false,
        manualClose: false,
        otaLoading: false,
        lastUserText: '',
        currentAssistantEl: null,
        autoStopTimer: null
    };

    // ---------------- 工具函数 ----------------

    function sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    function nowText() {
        const d = new Date();
        const p = (n) => String(n).padStart(2, '0');
        return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
    }

    let logCount = 0;
    function log(message) {
        logCount += 1;
        els.logCount.textContent = String(logCount);
        const line = document.createElement('div');
        line.textContent = `[${nowText()}] ${message}`;
        els.log.appendChild(line);
        while (els.log.childElementCount > 200) {
            els.log.removeChild(els.log.firstChild);
        }
        els.log.scrollTop = els.log.scrollHeight;
    }

    function normalizeText(text) {
        return (text || '').replace(/[\s，。！？、,.!?;；:：""''（）()\[\]【】]/g, '');
    }

    function setStatus(kind, text) {
        els.statusDot.classList.remove('on', 'error');
        if (kind === 'connected') {
            els.statusDot.classList.add('on');
        } else if (kind === 'error') {
            els.statusDot.classList.add('error');
        }
        els.statusText.textContent = text;
    }

    function addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'system-msg';
        div.textContent = text;
        els.chat.appendChild(div);
        scrollToBottom();
        return div;
    }

    function addMessage(role, text) {
        const wrap = document.createElement('div');
        wrap.className = `msg ${role}`;

        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = role === 'user' ? '我' : '小智';

        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.textContent = text;

        wrap.appendChild(meta);
        wrap.appendChild(bubble);
        els.chat.appendChild(wrap);
        scrollToBottom();
        return bubble;
    }

    function scrollToBottom() {
        els.chat.scrollTop = els.chat.scrollHeight;
    }

    // ---------------- Opus 编解码 ----------------

    function getOpusModule() {
        if (window.ModuleInstance) {
            return window.ModuleInstance;
        }
        if (typeof window.Module !== 'undefined') {
            const instance = window.Module.instance || window.Module;
            if (instance && typeof instance._opus_encoder_get_size === 'function') {
                window.ModuleInstance = instance;
                return instance;
            }
        }
        return null;
    }

    class OpusEncoder {
        constructor() {
            this.module = getOpusModule();
            this.encoderPtr = null;
            this.inited = false;
            this.maxPacketSize = MAX_PACKET_SIZE;
        }

        init() {
            if (this.inited) {
                return true;
            }
            if (!this.module) {
                log('Opus 库未加载，无法创建编码器');
                return false;
            }
            const mod = this.module;
            const size = mod._opus_encoder_get_size(1);
            this.encoderPtr = mod._malloc(size);
            const err = mod._opus_encoder_init(this.encoderPtr, INPUT_SAMPLE_RATE, 1, 2048);
            if (err < 0) {
                mod._free(this.encoderPtr);
                this.encoderPtr = null;
                log(`Opus 编码器初始化失败: ${err}`);
                return false;
            }
            mod._opus_encoder_ctl(this.encoderPtr, 4002, 16000); // 码率
            mod._opus_encoder_ctl(this.encoderPtr, 4010, 5);     // 复杂度
            this.inited = true;
            return true;
        }

        encode(int16) {
            if (!this.init()) {
                return null;
            }
            const mod = this.module;
            const pcmPtr = mod._malloc(int16.length * 2);
            const outPtr = mod._malloc(this.maxPacketSize);
            try {
                mod.HEAP16.set(int16, pcmPtr >> 1);
                const len = mod._opus_encode(this.encoderPtr, pcmPtr, FRAME_SAMPLES, outPtr, this.maxPacketSize);
                if (len < 0) {
                    log(`Opus 编码失败: ${len}`);
                    return null;
                }
                const out = new Uint8Array(len);
                out.set(mod.HEAPU8.subarray(outPtr, outPtr + len));
                return out;
            } finally {
                mod._free(pcmPtr);
                mod._free(outPtr);
            }
        }
    }

    class OpusDecoder {
        constructor(sampleRate) {
            this.module = getOpusModule();
            this.rate = sampleRate || 24000;
            this.frameSamples = Math.round(this.rate * 0.06);
            this.decoderPtr = null;
        }

        init() {
            if (this.decoderPtr) {
                return true;
            }
            if (!this.module) {
                log('Opus 库未加载，无法创建解码器');
                return false;
            }
            const mod = this.module;
            const size = mod._opus_decoder_get_size(1);
            this.decoderPtr = mod._malloc(size);
            const err = mod._opus_decoder_init(this.decoderPtr, this.rate, 1);
            if (err < 0) {
                mod._free(this.decoderPtr);
                this.decoderPtr = null;
                log(`Opus 解码器初始化失败: ${err}`);
                return false;
            }
            return true;
        }

        decode(data) {
            if (!this.init()) {
                return new Int16Array(0);
            }
            const mod = this.module;
            const opusPtr = mod._malloc(data.length);
            const pcmPtr = mod._malloc(MAX_FRAME_SAMPLES * 2);
            try {
                mod.HEAPU8.set(data, opusPtr);
                const samples = mod._opus_decode(
                    this.decoderPtr,
                    opusPtr,
                    data.length,
                    pcmPtr,
                    MAX_FRAME_SAMPLES,
                    0
                );
                if (samples < 0) {
                    log(`Opus 解码失败: ${samples}`);
                    return new Int16Array(0);
                }
                const pcm = new Int16Array(samples);
                pcm.set(mod.HEAP16.subarray(pcmPtr >> 1, (pcmPtr >> 1) + samples));
                return pcm;
            } finally {
                mod._free(opusPtr);
                mod._free(pcmPtr);
            }
        }
    }

    // ---------------- 播放器 ----------------

    const player = {
        ctx: null,
        decoder: null,
        nextTime: 0,
        sources: new Set(),

        ensureContext() {
            if (!this.ctx) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                this.ctx = new Ctx({ latencyHint: 'interactive' });
            }
            if (this.ctx.state === 'suspended') {
                this.ctx.resume().catch(() => {});
            }
            return this.ctx;
        },

        setSampleRate(rate) {
            if (!rate || rate === this.rate) {
                return;
            }
            this.rate = rate;
            this.decoder = null;
        },

        clear() {
            this.sources.forEach((src) => {
                try {
                    src.stop();
                } catch (e) {
                    // 已停止的音频源忽略
                }
            });
            this.sources.clear();
            if (this.ctx) {
                this.nextTime = this.ctx.currentTime;
            } else {
                this.nextTime = 0;
            }
        },

        beginTurn() {
            const ctx = this.ensureContext();
            if (this.nextTime < ctx.currentTime + 0.05) {
                this.nextTime = ctx.currentTime + 0.18;
            }
        },

        enqueue(data) {
            const ctx = this.ensureContext();
            if (!this.decoder) {
                this.decoder = new OpusDecoder(this.rate || state.outputSampleRate);
            }
            const pcm = this.decoder.decode(data);
            if (!pcm.length) {
                return;
            }
            const buffer = ctx.createBuffer(1, pcm.length, this.decoder.rate);
            const channel = buffer.getChannelData(0);
            for (let i = 0; i < pcm.length; i += 1) {
                channel[i] = pcm[i] / 32768;
            }
            const src = ctx.createBufferSource();
            src.buffer = buffer;
            src.connect(ctx.destination);
            const startAt = Math.max(this.nextTime, ctx.currentTime + 0.02);
            src.start(startAt);
            this.nextTime = startAt + buffer.duration;
            this.sources.add(src);
            src.onended = () => this.sources.delete(src);
        }
    };

    // ---------------- 麦克风采集与编码 ----------------

    const WORKLET_CODE = `
        class PcmRecorderProcessor extends AudioWorkletProcessor {
            constructor() {
                super();
                this.buffer = new Float32Array(2048);
                this.index = 0;
                this.active = false;
                this.port.onmessage = (event) => {
                    if (event.data.command === 'start') {
                        this.active = true;
                    } else if (event.data.command === 'stop') {
                        this.active = false;
                        if (this.index > 0) {
                            this.port.postMessage({ type: 'chunk', buffer: this.buffer.slice(0, this.index) });
                            this.index = 0;
                        }
                    }
                };
            }
            process(inputs) {
                if (!this.active) {
                    return true;
                }
                const input = inputs[0] && inputs[0][0];
                if (!input) {
                    return true;
                }
                for (let i = 0; i < input.length; i += 1) {
                    this.buffer[this.index] = input[i];
                    this.index += 1;
                    if (this.index >= this.buffer.length) {
                        this.port.postMessage({ type: 'chunk', buffer: this.buffer.slice(0) });
                        this.index = 0;
                    }
                }
                return true;
            }
        }
        registerProcessor('pcm-recorder', PcmRecorderProcessor);
    `;

    const recorder = {
        ctx: null,
        node: null,
        source: null,
        gain: null,
        stream: null,
        workletUrl: null,
        resampler: null,
        pending: new Int16Array(0),
        encoder: new OpusEncoder(),
        starting: false,
        active: false,
        nodeType: '',
        workletReady: false,

        async ensureContext() {
            if (!this.ctx) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                this.ctx = new Ctx({ sampleRate: INPUT_SAMPLE_RATE, latencyHint: 'interactive' });
                // file:// 下浏览器不允许加载 blob Worklet，直接使用 ScriptProcessor；
                // http/https 下优先使用 AudioWorklet，失败时自动降级
                const isFilePage = window.location.protocol === 'file:';
                try {
                    if (!isFilePage && this.ctx.audioWorklet && typeof AudioWorkletNode !== 'undefined') {
                        if (!this.workletUrl) {
                            this.workletUrl = URL.createObjectURL(new Blob([WORKLET_CODE], { type: 'application/javascript' }));
                        }
                        await this.ctx.audioWorklet.addModule(this.workletUrl);
                        this.workletReady = true;
                    }
                } catch (e) {
                    this.workletReady = false;
                }
            }
            if (this.ctx.state === 'suspended') {
                await this.ctx.resume();
            }
            return this.ctx;
        },

        createResampler(fromRate, toRate) {
            if (fromRate === toRate) {
                return null;
            }
            const ratio = fromRate / toRate;
            let leftover = new Float32Array(0);
            let position = 0;
            return (input) => {
                const buffer = new Float32Array(leftover.length + input.length);
                buffer.set(leftover);
                buffer.set(input, leftover.length);
                if (buffer.length < 2) {
                    leftover = buffer;
                    return new Float32Array(0);
                }
                const count = Math.max(0, Math.floor((buffer.length - 1 - position) / ratio) + 1);
                const output = new Float32Array(count);
                let pos = position;
                for (let i = 0; i < count; i += 1) {
                    const idx = Math.floor(pos);
                    const frac = pos - idx;
                    const a = buffer[idx];
                    const b = buffer[Math.min(idx + 1, buffer.length - 1)];
                    output[i] = a * (1 - frac) + b * frac;
                    pos += ratio;
                }
                const keepFrom = Math.min(Math.floor(pos), buffer.length - 1);
                leftover = buffer.slice(keepFrom);
                position = pos - keepFrom;
                return output;
            };
        },

        handleChunk(float32) {
            const resampled = this.resampler ? this.resampler(float32) : float32;
            if (!resampled.length) {
                return;
            }
            const int16 = new Int16Array(resampled.length);
            for (let i = 0; i < resampled.length; i += 1) {
                const value = Math.max(-1, Math.min(1, resampled[i]));
                int16[i] = value < 0 ? value * 32768 : value * 32767;
            }
            const merged = new Int16Array(this.pending.length + int16.length);
            merged.set(this.pending);
            merged.set(int16, this.pending.length);
            this.pending = merged;

            while (this.pending.length >= FRAME_SAMPLES) {
                const frame = this.pending.slice(0, FRAME_SAMPLES);
                this.pending = this.pending.slice(FRAME_SAMPLES);
                this.sendFrame(frame);
            }
        },

        sendFrame(frame) {
            if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
                return;
            }
            const encoded = this.encoder.encode(frame);
            if (encoded && encoded.length) {
                state.ws.send(encoded);
            }
        },

        flush() {
            if (this.pending.length > 0) {
                const frame = new Int16Array(FRAME_SAMPLES);
                frame.set(this.pending.slice(0, FRAME_SAMPLES));
                this.pending = new Int16Array(0);
                this.sendFrame(frame);
            }
        },

        async start() {
            if (state.recording || this.starting) {
                return;
            }
            this.starting = true;
            try {
                const ctx = await this.ensureContext();
                this.stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        channelCount: 1,
                        sampleRate: INPUT_SAMPLE_RATE
                    }
                });
                this.source = ctx.createMediaStreamSource(this.stream);
                this.gain = ctx.createGain();
                this.gain.gain.value = 0;
                this.pending = new Int16Array(0);
                this.resampler = this.createResampler(ctx.sampleRate, INPUT_SAMPLE_RATE);
                this.active = true;

                if (this.workletReady) {
                    this.nodeType = 'worklet';
                    this.node = new AudioWorkletNode(ctx, 'pcm-recorder');
                    this.node.port.onmessage = (event) => {
                        if (event.data && event.data.type === 'chunk') {
                            this.handleChunk(event.data.buffer);
                        }
                    };
                    this.node.port.postMessage({ command: 'start' });
                } else {
                    this.nodeType = 'processor';
                    this.node = ctx.createScriptProcessor(4096, 1, 1);
                    this.node.onaudioprocess = (event) => {
                        if (!this.active) {
                            return;
                        }
                        this.handleChunk(event.inputBuffer.getChannelData(0).slice());
                    };
                }

                this.source.connect(this.node);
                this.node.connect(this.gain);
                this.gain.connect(ctx.destination);
            } finally {
                this.starting = false;
            }
        },

        async stop() {
            this.active = false;
            if (this.node && this.nodeType === 'worklet') {
                this.node.port.postMessage({ command: 'stop' });
            }
            // 等待音频处理器把最后一帧回传
            await sleep(this.nodeType === 'worklet' ? 120 : 60);
            this.flush();
            this.teardown();
        },

        teardown() {
            this.active = false;
            if (this.node) {
                try {
                    if (this.node.port) {
                        this.node.port.onmessage = null;
                    }
                    this.node.onaudioprocess = null;
                    this.node.disconnect();
                } catch (e) {
                    // 忽略断开异常
                }
                this.node = null;
                this.nodeType = '';
            }
            if (this.source) {
                try {
                    this.source.disconnect();
                } catch (e) {
                    // 忽略断开异常
                }
                this.source = null;
            }
            if (this.gain) {
                try {
                    this.gain.disconnect();
                } catch (e) {
                    // 忽略断开异常
                }
                this.gain = null;
            }
            if (this.stream) {
                this.stream.getTracks().forEach((track) => track.stop());
                this.stream = null;
            }
        }
    };

    // ---------------- WebSocket 通信 ----------------

    function sendJson(payload) {
        if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
            return false;
        }
        state.ws.send(JSON.stringify(payload));
        log(`→ ${JSON.stringify(payload)}`);
        return true;
    }

    function buildUrl() {
        const base = els.wsUrl.value.trim();
        if (!base) {
            throw new Error('请填写 WebSocket 地址');
        }
        const url = new URL(base);
        const deviceId = els.deviceId.value.trim() || VIRTUAL_FIXED_MAC;
        if (!url.searchParams.has('device-id')) {
            url.searchParams.set('device-id', deviceId);
        }
        if (!url.searchParams.has('client-id')) {
            url.searchParams.set('client-id', deviceId);
        }
        const token = els.token.value.trim();
        if (token) {
            url.searchParams.set('authorization', token.startsWith('Bearer ') ? token : `Bearer ${token}`);
        }
        return url.toString();
    }

    function sendHello() {
        sendJson({
            type: 'hello',
            version: 1,
            transport: 'websocket',
            audio_params: {
                format: 'opus',
                sample_rate: INPUT_SAMPLE_RATE,
                channels: 1,
                frame_duration: 60
            },
            features: {
                mcp: false,
                emoji: true
            }
        });
    }

    // ---------------- OTA 获取 WebSocket 地址与 Token ----------------

    function buildOtaPayload(deviceId) {
        return {
            version: 0,
            uuid: '',
            application: {
                name: 'xiaozhi-web-test',
                version: '1.0.0',
                compile_time: '2026-01-01 00:00:00',
                idf_version: '4.4.3',
                elf_sha256: '0000000000000000000000000000000000000000000000000000000000000000'
            },
            ota: { label: 'xiaozhi-web-test' },
            board: {
                type: 'xiaozhi-web-test',
                ssid: 'xiaozhi-web-test',
                rssi: 0,
                channel: 0,
                ip: '192.168.1.1',
                mac: deviceId
            },
            flash_size: 0,
            minimum_free_heap_size: 0,
            mac_address: deviceId,
            chip_model_name: '',
            chip_info: { model: 0, cores: 0, revision: 0, features: 0 },
            partition_table: [{ label: '', type: 0, subtype: 0, address: 0, size: 0 }]
        };
    }

    function otaCandidates() {
        const scheme = window.location.protocol === 'https:' ? 'https' : 'http';
        const host = window.location.hostname || '127.0.0.1';
        const list = [];
        const explicit = els.otaUrl.value.trim();
        if (explicit) {
            list.push(explicit);
        }
        // 8002 为智控台（manager-api）OTA，8003 为本地 xiaozhi-server OTA
        [8002, 8003].forEach((port) => {
            const candidate = `${scheme}://${host}:${port}/xiaozhi/ota/`;
            if (!list.includes(candidate)) {
                list.push(candidate);
            }
        });
        return list;
    }

    async function postOta(url, deviceId) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 5000);
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Device-Id': deviceId,
                    'Client-Id': deviceId
                },
                body: JSON.stringify(buildOtaPayload(deviceId)),
                signal: controller.signal,
                cache: 'no-store'
            });
            const text = await res.text();
            if (!res.ok) {
                log(`OTA 返回 HTTP ${res.status}：${text.slice(0, 120)}`);
                return null;
            }
            try {
                return JSON.parse(text);
            } catch (e) {
                log(`OTA 响应不是 JSON：${text.slice(0, 120)}`);
                return null;
            }
        } finally {
            clearTimeout(timer);
        }
    }

    async function requestOta(deviceId) {
        const candidates = otaCandidates();
        for (const url of candidates) {
            try {
                log(`OTA 请求：${url}`);
                const data = await postOta(url, deviceId);
                if (!data) {
                    continue;
                }
                const websocket = data.websocket || null;
                const token = websocket && websocket.token ? websocket.token : '';
                log(`OTA 响应：${JSON.stringify({
                    websocket: websocket ? { url: websocket.url, token: token ? `${token.slice(0, 8)}...` : '' } : null,
                    activation: data.activation || null,
                    error: data.error || null
                })}`);
                if (data.error) {
                    continue;
                }
                if (websocket && websocket.url) {
                    return { otaUrl: url, websocket: websocket, activation: data.activation || null };
                }
                if (data.mqtt && !websocket) {
                    return { otaUrl: url, mqtt: data.mqtt, activation: data.activation || null };
                }
            } catch (error) {
                log(`OTA 请求失败：${url} -> ${error.name === 'AbortError' ? '超时' : error.message}`);
            }
        }
        return null;
    }

    async function applyOtaConfig(deviceId) {
        const result = await requestOta(deviceId);
        if (!result) {
            addSystemMessage('未能从 OTA 获取连接信息，将使用页面中填写的地址与 Token 连接。若服务端开启认证，请手动填写 Token。');
            return;
        }
        if (result.mqtt && !result.websocket) {
            addSystemMessage('OTA 返回的是 MQTT 网关配置，网页测试页只能使用 WebSocket，已改用页面地址连接。');
            return;
        }
        const websocket = result.websocket || {};
        if (websocket.token) {
            els.token.value = websocket.token;
            log('OTA 已下发 WebSocket Token');
        }
        if (websocket.url) {
            if (websocket.url.indexOf('xiaozhi.server.com') >= 0) {
                log(`OTA 下发的 WebSocket 地址为占位地址（${websocket.url}），沿用页面地址`);
            } else {
                els.wsUrl.value = websocket.url;
                log(`OTA 下发 WebSocket 地址：${websocket.url}`);
            }
        }
        if (result.activation && result.activation.code) {
            addSystemMessage(`设备未绑定，OTA 返回激活码：${result.activation.code}。请在智控台完成设备绑定后再对话。`);
        }
    }

    async function connect() {
        if (state.ws || state.otaLoading) {
            return;
        }
        state.otaLoading = true;
        els.connectBtn.disabled = true;
        setStatus('connecting', '获取 OTA 信息');
        const deviceId = els.deviceId.value.trim() || VIRTUAL_FIXED_MAC;
        try {
            await applyOtaConfig(deviceId);
        } catch (error) {
            log(`OTA 处理异常：${error.message}`);
        } finally {
            state.otaLoading = false;
        }

        let url;
        try {
            url = buildUrl();
        } catch (error) {
            setStatus('idle', '未连接');
            els.connectBtn.disabled = false;
            addSystemMessage(`连接失败：${error.message}`);
            return;
        }
        els.wsUrl.value = url.split('?')[0];
        localStorage.setItem('xiaozhi_test_ws_url', els.wsUrl.value);
        localStorage.setItem('xiaozhi_test_ota_url', els.otaUrl.value.trim());

        setStatus('connecting', '连接中');
        els.connectBtn.disabled = true;

        player.ensureContext();

        let ws;
        try {
            ws = new WebSocket(url);
        } catch (error) {
            setStatus('error', '连接失败');
            els.connectBtn.disabled = false;
            addSystemMessage(`连接失败：${error.message}`);
            return;
        }
        ws.binaryType = 'arraybuffer';
        state.ws = ws;
        log(`正在连接 ${url}`);

        ws.onopen = () => {
            state.connected = true;
            setStatus('connected', '已连接');
            els.disconnectBtn.disabled = false;
            els.micBtn.disabled = false;
            els.textInput.disabled = false;
            els.sendBtn.disabled = false;
            sendHello();
            setTimeout(() => {
                if (state.connected && !state.sessionId) {
                    addSystemMessage('已建立连接，正在等待服务端握手响应。若长时间无响应，请检查服务端是否已完成初始化。');
                }
            }, 6000);
        };

        ws.onmessage = (event) => {
            if (typeof event.data === 'string') {
                handleServerText(event.data);
                return;
            }
            handleServerBinary(event.data);
        };

        ws.onerror = () => {
            log('WebSocket 发生错误');
            setStatus('error', '连接异常');
        };

        ws.onclose = (event) => {
            const wasConnected = state.connected;
            const manual = state.manualClose;
            state.connected = false;
            state.ws = null;
            state.sessionId = null;
            state.speaking = false;
            state.manualClose = false;
            removePendingAssistant();
            player.clear();
            stopMic(false).catch(() => {});
            setStatus(manual ? 'idle' : 'error', manual ? '未连接' : '已断开');
            els.connectBtn.disabled = false;
            els.disconnectBtn.disabled = true;
            els.micBtn.disabled = true;
            els.textInput.disabled = true;
            els.sendBtn.disabled = true;
            log(`连接已关闭（code=${event.code}）`);
            if (wasConnected && !manual) {
                addSystemMessage(`连接已断开（code=${event.code}）。`);
            }
        };
    }

    function disconnect() {
        state.manualClose = true;
        if (state.ws) {
            state.ws.close();
        }
    }

    function handleServerText(raw) {
        let message;
        try {
            message = JSON.parse(raw);
        } catch (error) {
            log(`← ${raw}`);
            // 服务端在认证失败、缺少设备 ID 等场景会直接返回纯文本
            if (raw && raw.trim()) {
                addSystemMessage(`服务端：${raw.trim()}`);
            }
            return;
        }
        log(`← ${raw.length > 600 ? `${raw.slice(0, 600)}…` : raw}`);

        if (message.type === 'hello') {
            state.sessionId = message.session_id || null;
            const params = message.audio_params || {};
            state.outputSampleRate = params.sample_rate || state.outputSampleRate;
            player.setSampleRate(state.outputSampleRate);
            addSystemMessage(`连接成功，会话已建立。服务端输出音频采样率 ${state.outputSampleRate} Hz。现在可以输入文字或按住麦克风说话。`);
            return;
        }

        if (message.type === 'stt') {
            const text = message.text || '';
            if (!text) {
                return;
            }
            if (state.lastUserText && normalizeText(text) === normalizeText(state.lastUserText)) {
                state.lastUserText = '';
            } else {
                addMessage('user', text);
            }
            state.lastUserText = '';
            return;
        }

        if (message.type === 'tts') {
            handleTtsMessage(message);
            return;
        }

        if (message.type === 'llm') {
            // 服务端下发的情绪表情，测试页无需展示
            return;
        }

        if (message.type === 'server') {
            addSystemMessage(`服务端消息：${message.message || message.status || ''}`);
            return;
        }

        log(`未知消息类型：${message.type}`);
    }

    function removePendingAssistant() {
        if (!state.currentAssistantEl) {
            return;
        }
        const wrap = state.currentAssistantEl.closest('.msg');
        if (wrap && !state.currentAssistantEl.textContent.trim()) {
            wrap.remove();
        }
        state.currentAssistantEl = null;
    }

    function handleTtsMessage(message) {
        if (message.state === 'start') {
            state.speaking = true;
            setStatus('connected', '小智正在说话');
            const bubble = addMessage('assistant', '');
            bubble.classList.add('pending');
            bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
            state.currentAssistantEl = bubble;
            player.beginTurn();
            return;
        }

        if (message.state === 'sentence_start') {
            const text = message.text || '';
            if (!state.currentAssistantEl) {
                const bubble = addMessage('assistant', '');
                state.currentAssistantEl = bubble;
            }
            const bubble = state.currentAssistantEl;
            bubble.classList.remove('pending');
            if (bubble.querySelector('.typing')) {
                bubble.textContent = '';
            }
            bubble.textContent += text;
            scrollToBottom();
            return;
        }

        if (message.state === 'stop') {
            state.speaking = false;
            removePendingAssistant();
            setStatus('connected', '已连接');
            return;
        }
    }

    function handleServerBinary(data) {
        if (data instanceof Blob) {
            data.arrayBuffer().then((buffer) => player.enqueue(new Uint8Array(buffer))).catch(() => {});
            return;
        }
        if (data instanceof ArrayBuffer) {
            log(`← 二进制音频包 ${data.byteLength} 字节`);
            player.enqueue(new Uint8Array(data));
        }
    }

    // ---------------- 文字 / 语音交互 ----------------

    async function sendText() {
        const text = els.textInput.value.trim();
        if (!text || !state.connected) {
            return;
        }
        if (state.recording) {
            await stopMic(true);
        }
        if (state.speaking) {
            sendJson({ type: 'abort', session_id: state.sessionId });
            player.clear();
            state.speaking = false;
            removePendingAssistant();
            setStatus('connected', '已连接');
        }
        state.lastUserText = text;
        addMessage('user', text);
        sendJson({ type: 'listen', state: 'detect', text: text });
        els.textInput.value = '';
        els.textInput.focus();
    }

    async function startMic() {
        if (!state.connected || state.recording) {
            return;
        }
        if (state.speaking) {
            sendJson({ type: 'abort', session_id: state.sessionId });
            player.clear();
            state.speaking = false;
            removePendingAssistant();
        }
        try {
            await recorder.start();
            state.recording = true;
            els.micBtn.classList.add('recording');
            els.micLabel.textContent = '停止说话';
            els.sendBtn.disabled = true;
            setStatus('connected', '正在录音');
            sendJson({ type: 'listen', state: 'start', mode: 'manual', session_id: state.sessionId });
            state.autoStopTimer = setTimeout(() => {
                stopMic(true).catch(() => {});
            }, 60000);
        } catch (error) {
            recorder.teardown();
            state.recording = false;
            addSystemMessage(`无法开始录音：${error.message}。请确认已授予麦克风权限，并通过 localhost 或 https 访问页面。`);
            log(`麦克风启动失败：${error.message}`);
        }
    }

    async function stopMic(sendStop) {
        if (!state.recording) {
            return;
        }
        state.recording = false;
        if (state.autoStopTimer) {
            clearTimeout(state.autoStopTimer);
            state.autoStopTimer = null;
        }
        els.micBtn.classList.remove('recording');
        els.micLabel.textContent = '开始说话';
        els.sendBtn.disabled = false;
        await recorder.stop();
        if (sendStop) {
            sendJson({ type: 'listen', state: 'stop', session_id: state.sessionId });
        }
        setStatus('connected', '已连接');
    }

    // ---------------- 初始化 ----------------

    function defaultWsUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname || '127.0.0.1';
        return `${protocol}//${host}:8000/xiaozhi/v1/`;
    }

    function defaultOtaUrl() {
        const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
        const host = window.location.hostname || '127.0.0.1';
        return `${protocol}//${host}:8002/xiaozhi/ota/`;
    }

    const DEVICE_MAC_KEY = 'xiaozhi_test_device_mac';
    const VIRTUAL_FIXED_MAC = '02:00:00:00:00:01';
    const MAC_PATTERN = /^([0-9a-f]{2}:){5}[0-9a-f]{2}$/;

    function normalizeMac(value) {
        const mac = String(value || '').trim().toLowerCase();
        return MAC_PATTERN.test(mac) ? mac : '';
    }

    // 读取不到本机 MAC 时，生成一个本地管理地址并持久化，保证每次访问固定不变
    function getVirtualMac() {
        try {
            const saved = normalizeMac(localStorage.getItem(DEVICE_MAC_KEY));
            if (saved) {
                return saved;
            }
        } catch (e) {
            // localStorage 不可用时继续使用固定虚拟地址
        }
        let mac = VIRTUAL_FIXED_MAC;
        try {
            const bytes = new Uint8Array(6);
            if (window.crypto && window.crypto.getRandomValues) {
                window.crypto.getRandomValues(bytes);
            } else {
                for (let i = 0; i < bytes.length; i += 1) {
                    bytes[i] = Math.floor(Math.random() * 256);
                }
            }
            // 首字节设置本地管理位，符合虚拟 MAC 地址规范
            bytes[0] = (bytes[0] & 0xfc) | 0x02;
            mac = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join(':');
            localStorage.setItem(DEVICE_MAC_KEY, mac);
        } catch (e) {
            // 无法持久化时使用固定虚拟地址
        }
        return mac;
    }

    function loadDeviceId() {
        // 浏览器出于隐私限制无法直接读取网卡 MAC，直接打开页面时使用虚拟固定地址
        const mac = getVirtualMac();
        els.deviceId.value = mac;
        els.deviceId.title = `虚拟固定设备 ID：${mac}`;
        log(`设备 ID：${mac}（虚拟固定地址）`);
    }

    function init() {
        els.wsUrl.value = localStorage.getItem('xiaozhi_test_ws_url') || defaultWsUrl();
        els.otaUrl.value = localStorage.getItem('xiaozhi_test_ota_url') || defaultOtaUrl();
        els.deviceId.addEventListener('input', () => {
            els.deviceId.dataset.edited = '1';
        });
        loadDeviceId();

        if (!getOpusModule()) {
            addSystemMessage('Opus 编解码库加载失败，语音功能不可用；文字对话仍可正常使用。');
        }

        els.connectBtn.addEventListener('click', connect);
        els.disconnectBtn.addEventListener('click', disconnect);
        els.sendBtn.addEventListener('click', sendText);
        els.textInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                sendText();
            }
        });
        els.micBtn.addEventListener('click', () => {
            if (state.recording) {
                stopMic(true).catch(() => {});
            } else {
                startMic().catch(() => {});
            }
        });

        document.addEventListener('click', () => {
            if (player.ctx && player.ctx.state === 'suspended') {
                player.ctx.resume().catch(() => {});
            }
        });

        window.addEventListener('beforeunload', () => {
            if (state.ws) {
                state.ws.close();
            }
        });

        log('页面初始化完成');
    }

    init();
})();
