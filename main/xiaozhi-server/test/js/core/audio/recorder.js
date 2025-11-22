// 音频录制模块
import { log } from '../../utils/logger.js';
import { initOpusEncoder } from './opus-codec.js';
import { getAudioPlayer } from './player.js';

// 音频录制器类
export class AudioRecorder {
    constructor() {
        this.isRecording = false;
        this.audioContext = null;
        this.analyser = null;
        this.audioProcessor = null;
        this.audioProcessorType = null;
        this.audioSource = null;
        this.opusEncoder = null;
        this.pcmDataBuffer = new Int16Array();
        this.audioBuffers = [];
        this.totalAudioSize = 0;
        this.visualizationRequest = null;
        this.recordingTimer = null;
        this.websocket = null;

        // 回调函数
        this.onRecordingStart = null;
        this.onRecordingStop = null;
        this.onVisualizerUpdate = null;
    }

    // 设置WebSocket实例
    setWebSocket(ws) {
        this.websocket = ws;
    }

    // 获取AudioContext实例
    getAudioContext() {
        const audioPlayer = getAudioPlayer();
        return audioPlayer.getAudioContext();
    }

    // 初始化编码器
    initEncoder() {
        if (!this.opusEncoder) {
            this.opusEncoder = initOpusEncoder();
        }
        return this.opusEncoder;
    }

    // PCM处理器代码
    getAudioProcessorCode() {
        return `
            class AudioRecorderProcessor extends AudioWorkletProcessor {
                constructor() {
                    super();
                    this.buffers = [];
                    this.frameSize = 960;
                    this.buffer = new Int16Array(this.frameSize);
                    this.bufferIndex = 0;
                    this.isRecording = false;

                    this.port.onmessage = (event) => {
                        if (event.data.command === 'start') {
                            this.isRecording = true;
                            this.port.postMessage({ type: 'status', status: 'started' });
                        } else if (event.data.command === 'stop') {
                            this.isRecording = false;

                            if (this.bufferIndex > 0) {
                                const finalBuffer = this.buffer.slice(0, this.bufferIndex);
                                this.port.postMessage({
                                    type: 'buffer',
                                    buffer: finalBuffer
                                });
                                this.bufferIndex = 0;
                            }

                            this.port.postMessage({ type: 'status', status: 'stopped' });
                        }
                    };
                }

                process(inputs, outputs, parameters) {
                    if (!this.isRecording) return true;

                    const input = inputs[0][0];
                    if (!input) return true;

                    for (let i = 0; i < input.length; i++) {
                        if (this.bufferIndex >= this.frameSize) {
                            this.port.postMessage({
                                type: 'buffer',
                                buffer: this.buffer.slice(0)
                            });
                            this.bufferIndex = 0;
                        }

                        this.buffer[this.bufferIndex++] = Math.max(-32768, Math.min(32767, Math.floor(input[i] * 32767)));
                    }

                    return true;
                }
            }

            registerProcessor('audio-recorder-processor', AudioRecorderProcessor);
        `;
    }

    // 创建音频处理器
    async createAudioProcessor() {
        this.audioContext = this.getAudioContext();

        try {
            if (this.audioContext.audioWorklet) {
                const blob = new Blob([this.getAudioProcessorCode()], { type: 'application/javascript' });
                const url = URL.createObjectURL(blob);
                await this.audioContext.audioWorklet.addModule(url);
                URL.revokeObjectURL(url);

                const audioProcessor = new AudioWorkletNode(this.audioContext, 'audio-recorder-processor');

                audioProcessor.port.onmessage = (event) => {
                    if (event.data.type === 'buffer') {
                        this.processPCMBuffer(event.data.buffer);
                    }
                };

                log('使用AudioWorklet处理音频', 'success');

                const silent = this.audioContext.createGain();
                silent.gain.value = 0;
                audioProcessor.connect(silent);
                silent.connect(this.audioContext.destination);
                return { node: audioProcessor, type: 'worklet' };
            } else {
                log('AudioWorklet不可用，使用ScriptProcessorNode作为回退方案', 'warning');
                return this.createScriptProcessor();
            }
        } catch (error) {
            log(`创建音频处理器失败: ${error.message}，尝试回退方案`, 'error');
            return this.createScriptProcessor();
        }
    }

    // 创建ScriptProcessor作为回退
    createScriptProcessor() {
        try {
            const frameSize = 4096;
            const scriptProcessor = this.audioContext.createScriptProcessor(frameSize, 1, 1);

            scriptProcessor.onaudioprocess = (event) => {
                if (!this.isRecording) return;

                const input = event.inputBuffer.getChannelData(0);
                const buffer = new Int16Array(input.length);

                for (let i = 0; i < input.length; i++) {
                    buffer[i] = Math.max(-32768, Math.min(32767, Math.floor(input[i] * 32767)));
                }

                this.processPCMBuffer(buffer);
            };

            const silent = this.audioContext.createGain();
            silent.gain.value = 0;
            scriptProcessor.connect(silent);
            silent.connect(this.audioContext.destination);

            log('使用ScriptProcessorNode作为回退方案成功', 'warning');
            return { node: scriptProcessor, type: 'processor' };
        } catch (fallbackError) {
            log(`回退方案也失败: ${fallbackError.message}`, 'error');
            return null;
        }
    }

    // 处理PCM缓冲数据
    processPCMBuffer(buffer) {
        if (!this.isRecording) return;

        const newBuffer = new Int16Array(this.pcmDataBuffer.length + buffer.length);
        newBuffer.set(this.pcmDataBuffer);
        newBuffer.set(buffer, this.pcmDataBuffer.length);
        this.pcmDataBuffer = newBuffer;

        const samplesPerFrame = 960;

        while (this.pcmDataBuffer.length >= samplesPerFrame) {
            const frameData = this.pcmDataBuffer.slice(0, samplesPerFrame);
            this.pcmDataBuffer = this.pcmDataBuffer.slice(samplesPerFrame);

            this.encodeAndSendOpus(frameData);
        }
    }

    // 编码并发送Opus数据
    encodeAndSendOpus(pcmData = null) {
        if (!this.opusEncoder) {
            log('Opus编码器未初始化', 'error');
            return;
        }

        try {
            if (pcmData) {
                const opusData = this.opusEncoder.encode(pcmData);

                if (opusData && opusData.length > 0) {
                    this.audioBuffers.push(opusData.buffer);
                    this.totalAudioSize += opusData.length;

                    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                        try {
                            this.websocket.send(opusData.buffer);
                            log(`发送Opus帧，大小：${opusData.length}字节`, 'debug');
                        } catch (error) {
                            log(`WebSocket发送错误: ${error.message}`, 'error');
                        }
                    }
                } else {
                    log('Opus编码失败，无有效数据返回', 'error');
                }
            } else {
                if (this.pcmDataBuffer.length > 0) {
                    const samplesPerFrame = 960;
                    if (this.pcmDataBuffer.length < samplesPerFrame) {
                        const paddedBuffer = new Int16Array(samplesPerFrame);
                        paddedBuffer.set(this.pcmDataBuffer);
                        this.encodeAndSendOpus(paddedBuffer);
                    } else {
                        this.encodeAndSendOpus(this.pcmDataBuffer.slice(0, samplesPerFrame));
                    }
                    this.pcmDataBuffer = new Int16Array(0);
                }
            }
        } catch (error) {
            log(`Opus编码错误: ${error.message}`, 'error');
        }
    }

    // 开始录音
    async start() {
        if (this.isRecording) return false;

        try {
            if (!this.initEncoder()) {
                log('无法启动录音: Opus编码器初始化失败', 'error');
                return false;
            }

            log('请至少录制1-2秒钟的音频，确保采集到足够数据', 'info');

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000,
                    channelCount: 1
                }
            });

            this.audioContext = this.getAudioContext();

            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            const processorResult = await this.createAudioProcessor();
            if (!processorResult) {
                log('无法创建音频处理器', 'error');
                return false;
            }

            this.audioProcessor = processorResult.node;
            this.audioProcessorType = processorResult.type;

            this.audioSource = this.audioContext.createMediaStreamSource(stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;

            this.audioSource.connect(this.analyser);
            this.audioSource.connect(this.audioProcessor);

            this.pcmDataBuffer = new Int16Array();
            this.audioBuffers = [];
            this.totalAudioSize = 0;
            this.isRecording = true;

            if (this.audioProcessorType === 'worklet' && this.audioProcessor.port) {
                this.audioProcessor.port.postMessage({ command: 'start' });
            }

            // 发送监听开始消息
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                const listenMessage = {
                    type: 'listen',
                    mode: 'manual',
                    state: 'start'
                };

                log(`发送录音开始消息: ${JSON.stringify(listenMessage)}`, 'info');
                this.websocket.send(JSON.stringify(listenMessage));
            } else {
                log('WebSocket未连接，无法发送开始消息', 'error');
                return false;
            }

            // 开始可视化
            if (this.onVisualizerUpdate) {
                const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
                this.startVisualization(dataArray);
            }

            // 启动录音计时器
            let recordingSeconds = 0;
            this.recordingTimer = setInterval(() => {
                recordingSeconds += 0.1;
                if (this.onRecordingStart) {
                    this.onRecordingStart(recordingSeconds);
                }
            }, 100);

            log('开始PCM直接录音', 'success');
            return true;
        } catch (error) {
            log(`直接录音启动错误: ${error.message}`, 'error');
            this.isRecording = false;
            return false;
        }
    }

    // 开始可视化
    startVisualization(dataArray) {
        const draw = () => {
            this.visualizationRequest = requestAnimationFrame(() => draw());

            if (!this.isRecording) return;

            this.analyser.getByteFrequencyData(dataArray);

            if (this.onVisualizerUpdate) {
                this.onVisualizerUpdate(dataArray);
            }
        };
        draw();
    }

    // 停止录音
    stop() {
        if (!this.isRecording) return false;

        try {
            this.isRecording = false;

            if (this.audioProcessor) {
                if (this.audioProcessorType === 'worklet' && this.audioProcessor.port) {
                    this.audioProcessor.port.postMessage({ command: 'stop' });
                }

                this.audioProcessor.disconnect();
                this.audioProcessor = null;
            }

            if (this.audioSource) {
                this.audioSource.disconnect();
                this.audioSource = null;
            }

            if (this.visualizationRequest) {
                cancelAnimationFrame(this.visualizationRequest);
                this.visualizationRequest = null;
            }

            if (this.recordingTimer) {
                clearInterval(this.recordingTimer);
                this.recordingTimer = null;
            }

            // 编码并发送剩余的数据
            this.encodeAndSendOpus();

            // 发送结束信号
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                const emptyOpusFrame = new Uint8Array(0);
                this.websocket.send(emptyOpusFrame);

                const stopMessage = {
                    type: 'listen',
                    mode: 'manual',
                    state: 'stop'
                };

                this.websocket.send(JSON.stringify(stopMessage));
                log('已发送录音停止信号', 'info');
            }

            if (this.onRecordingStop) {
                this.onRecordingStop();
            }

            log('停止PCM直接录音', 'success');
            return true;
        } catch (error) {
            log(`直接录音停止错误: ${error.message}`, 'error');
            return false;
        }
    }

    // 获取分析器
    getAnalyser() {
        return this.analyser;
    }
}

// 创建单例
let audioRecorderInstance = null;

export function getAudioRecorder() {
    if (!audioRecorderInstance) {
        audioRecorderInstance = new AudioRecorder();
    }
    return audioRecorderInstance;
}
