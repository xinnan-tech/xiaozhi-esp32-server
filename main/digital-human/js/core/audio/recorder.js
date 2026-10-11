// Audio recording module
import { log } from '../../utils/logger.js?v=0205';
import { initOpusEncoder } from './opus-codec.js?v=0205';
import { getAudioPlayer } from './player.js?v=0205';

// Audio recorder class
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
        // Callback functions
        this.onRecordingStart = null;
        this.onRecordingStop = null;
        this.onVisualizerUpdate = null;
    }

    // Set WebSocket instance
    setWebSocket(ws) {
        this.websocket = ws;
    }

    // Get AudioContext instance
    getAudioContext() {
        return getAudioPlayer().getAudioContext();
    }

    // Initialize encoder
    initEncoder() {
        if (!this.opusEncoder) {
            this.opusEncoder = initOpusEncoder();
        }
        return this.opusEncoder;
    }

    // PCM processor code
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
                                this.port.postMessage({ type: 'buffer', buffer: finalBuffer });
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
                            this.port.postMessage({ type: 'buffer', buffer: this.buffer.slice(0) });
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

    // Create audio processor
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
                log('Processing audio with AudioWorklet', 'success');
                const silent = this.audioContext.createGain();
                silent.gain.value = 0;
                audioProcessor.connect(silent);
                silent.connect(this.audioContext.destination);
                return { node: audioProcessor, type: 'worklet' };
            } else {
                log('AudioWorklet unavailable, falling back to ScriptProcessorNode', 'warning');
                return this.createScriptProcessor();
            }
        } catch (error) {
            log(`Failed to create audio processor: ${error.message}, trying fallback`, 'error');
            return this.createScriptProcessor();
        }
    }

    // Create ScriptProcessor as fallback
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
            log('Successfully used ScriptProcessorNode as fallback', 'warning');
            return { node: scriptProcessor, type: 'processor' };
        } catch (fallbackError) {
            log(`Fallback also failed: ${fallbackError.message}`, 'error');
            return null;
        }
    }

    // Process PCM buffer data
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

    // Encode and send Opus data
    encodeAndSendOpus(pcmData = null) {
        if (!this.opusEncoder) {
            log('Opus encoder not initialized', 'error');
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
                        } catch (error) {
                            log(`WebSocket send error: ${error.message}`, 'error');
                        }
                    }
                } else {
                    log('Opus encoding failed, no valid data returned', 'error');
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
            log(`Opus encoding error: ${error.message}`, 'error');
        }
    }

    // Start recording
    async start() {
        if (this.isRecording) return false;
        try {
            if (!this.initEncoder()) {
                log('Cannot start recording: Opus encoder initialization failed', 'error');
                return false;
            }
            log('Record at least 1-2 seconds to ensure sufficient data collection', 'info');
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000, channelCount: 1 } });
            this.audioContext = this.getAudioContext();
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            const processorResult = await this.createAudioProcessor();
            if (!processorResult) {
                log('Failed to create audio processor', 'error');
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
            // Send listening start message
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                log(`Sent recording start message`, 'info');
            } else {
                log('WebSocket not connected, cannot send start message', 'error');
                return false;
            }
            // Start visualization
            if (this.onVisualizerUpdate) {
                const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
                this.startVisualization(dataArray);
            }
            // Immediately notify recording start, update button state
            if (this.onRecordingStart) {
                this.onRecordingStart(0);
            }
            // Start recording timer
            let recordingSeconds = 0;
            this.recordingTimer = setInterval(() => {
                recordingSeconds += 0.1;
                if (this.onRecordingStart) {
                    this.onRecordingStart(recordingSeconds);
                }
            }, 100);
            log('PCM direct recording started', 'success');
            return true;
        } catch (error) {
            log(`Direct recording start error: ${error.message}`, 'error');
            this.isRecording = false;
            return false;
        }
    }

    // Start visualization
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

    // Stop recording
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
            // Encode and send remaining data
            this.encodeAndSendOpus();
            // Send end signal
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                const emptyOpusFrame = new Uint8Array(0);
                this.websocket.send(emptyOpusFrame);
                log('Recording stop signal sent', 'info');
            }
            if (this.onRecordingStop) {
                this.onRecordingStop();
            }
            log('PCM direct recording stopped', 'success');
            return true;
        } catch (error) {
            log(`Direct recording stop error: ${error.message}`, 'error');
            return false;
        }
    }

    // Get analyser
    getAnalyser() {
        return this.analyser;
    }
}

// Create singleton instance
let audioRecorderInstance = null;

export function getAudioRecorder() {
    if (!audioRecorderInstance) {
        audioRecorderInstance = new AudioRecorder();
    }
    return audioRecorderInstance;
}

/**
 * Check if microphone is available
 * @returns {Promise<boolean>} Returns true if available, false if not available
 */
export async function checkMicrophoneAvailability() {
    // Check if browser supports getUserMedia API
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        log('Browser does not support getUserMedia API', 'warning');
        return false;
    }
    try {
        // Try to access microphone
        const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000, channelCount: 1 } });
        // Immediately stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
        log('Microphone availability check succeeded', 'success');
        return true;
    } catch (error) {
        log(`Microphone unavailable: ${error.message}`, 'warning');
        return false;
    }
}

/**
 * Check if it is HTTP non-localhost access
 * @returns {boolean} Returns true if it is HTTP non-localhost access
 */
export function isHttpNonLocalhost() {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    // Check if it is HTTP protocol
    if (protocol !== 'http:') {
        return false;
    }
    // localhost and 127.0.0.1 can use microphone
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return false;
    }
    // Private IP addresses can also use microphone (browser allows)
    if (hostname.startsWith('192.168.') || hostname.startsWith('10.') || hostname.startsWith('172.')) {
        return false;
    }
    // Other HTTP access is considered non-localhost
    return true;
}
