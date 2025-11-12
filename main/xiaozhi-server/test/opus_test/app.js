const SAMPLE_RATE = 16000;
const CHANNELS = 1;
const FRAME_SIZE = 960;  // 对应于60ms帧大小 (16000Hz * 0.06s = 960 samples)
const OPUS_APPLICATION = 2049; // OPUS_APPLICATION_AUDIO
const BUFFER_SIZE = 4096;

let audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
let mediaStream, mediaSource, audioProcessor;
let recordedPcmData = []; // 存储原始PCM数据
let recordedOpusData = []; // 存储Opus编码后的数据
let opusEncoder, opusDecoder;
let isRecording = false;

const startButton = document.getElementById("start");
const stopButton = document.getElementById("stop");
const playButton = document.getElementById("play");
const statusLabel = document.getElementById("status");

startButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);
playButton.addEventListener("click", playRecording);

// 初始化Opus编码器与解码器
async function initOpus() {
    if (typeof window.ModuleInstance === 'undefined') {
        if (typeof Module !== 'undefined') {
            // 尝试使用全局Module
            window.ModuleInstance = Module;
            console.log('使用全局Module作为ModuleInstance');
        } else {
            console.error("Opus库未加载，ModuleInstance和Module对象都不存在");
            return false;
        }
    }
    
    try {
        const mod = window.ModuleInstance;
        
        // 创建编码器
        opusEncoder = {
            channels: CHANNELS,
            sampleRate: SAMPLE_RATE,
            frameSize: FRAME_SIZE,
            maxPacketSize: 4000,
            module: mod,
            
            // 初始化编码器
            init: function() {
                // 获取编码器大小
                const encoderSize = mod._opus_encoder_get_size(this.channels);
                console.log(`Opus编码器大小: ${encoderSize}字节`);
                
                // 分配内存
                this.encoderPtr = mod._malloc(encoderSize);
                if (!this.encoderPtr) {
                    throw new Error("无法分配编码器内存");
                }
                
                // 初始化编码器
                const err = mod._opus_encoder_init(
                    this.encoderPtr,
                    this.sampleRate,
                    this.channels,
                    OPUS_APPLICATION
                );
                
                if (err < 0) {
                    throw new Error(`Opus编码器初始化失败: ${err}`);
                }
                
                return true;
            },
            
            // 编码方法
            encode: function(pcmData) {
                const mod = this.module;
                
                // 为PCM数据分配内存
                const pcmPtr = mod._malloc(pcmData.length * 2); // Int16 = 2字节
                
                // 将数据复制到WASM内存
                for (let i = 0; i < pcmData.length; i++) {
                    mod.HEAP16[(pcmPtr >> 1) + i] = pcmData[i];
                }
                
                // 为Opus编码数据分配内存
                const maxEncodedSize = this.maxPacketSize;
                const encodedPtr = mod._malloc(maxEncodedSize);
                
                // 编码
                const encodedBytes = mod._opus_encode(
                    this.encoderPtr,
                    pcmPtr,
                    this.frameSize,
                    encodedPtr,
                    maxEncodedSize
                );
                
                if (encodedBytes < 0) {
                    mod._free(pcmPtr);
                    mod._free(encodedPtr);
                    throw new Error(`Opus编码失败: ${encodedBytes}`);
                }
                
                // 复制编码后的数据
                const encodedData = new Uint8Array(encodedBytes);
                for (let i = 0; i < encodedBytes; i++) {
                    encodedData[i] = mod.HEAPU8[encodedPtr + i];
                }
                
                // 释放内存
                mod._free(pcmPtr);
                mod._free(encodedPtr);
                
                return encodedData;
            },
            
            // 销毁方法
            destroy: function() {
                if (this.encoderPtr) {
                    this.module._free(this.encoderPtr);
                    this.encoderPtr = null;
                }
            }
        };
        
        // 创建解码器
        opusDecoder = {
            channels: CHANNELS,
            rate: SAMPLE_RATE,
            frameSize: FRAME_SIZE,
            module: mod,
            
            // 初始化解码器
            init: function() {
                // 获取解码器大小
                const decoderSize = mod._opus_decoder_get_size(this.channels);
                console.log(`Opus解码器大小: ${decoderSize}字节`);
                
                // 分配内存
                this.decoderPtr = mod._malloc(decoderSize);
                if (!this.decoderPtr) {
                    throw new Error("无法分配解码器内存");
                }
                
                // 初始化解码器
                const err = mod._opus_decoder_init(
                    this.decoderPtr,
                    this.rate,
                    this.channels
                );
                
                if (err < 0) {
                    throw new Error(`Opus解码器初始化失败: ${err}`);
                }
                
                return true;
            },
            
            // 解码方法
            decode: function(opusData) {
                const mod = this.module;
                
                // 为Opus数据分配内存
                const opusPtr = mod._malloc(opusData.length);
                mod.HEAPU8.set(opusData, opusPtr);
                
                // 为PCM输出分配内存
                const pcmPtr = mod._malloc(this.frameSize * 2); // Int16 = 2字节
                
                // 解码
                const decodedSamples = mod._opus_decode(
                    this.decoderPtr,
                    opusPtr,
                    opusData.length,
                    pcmPtr,
                    this.frameSize,
                    0 // 不使用FEC
                );
                
                if (decodedSamples < 0) {
                    mod._free(opusPtr);
                    mod._free(pcmPtr);
                    throw new Error(`Opus解码失败: ${decodedSamples}`);
                }
                
                // 复制解码后的数据
                const decodedData = new Int16Array(decodedSamples);
                for (let i = 0; i < decodedSamples; i++) {
                    decodedData[i] = mod.HEAP16[(pcmPtr >> 1) + i];
                }
                
                // 释放内存
                mod._free(opusPtr);
                mod._free(pcmPtr);
                
                return decodedData;
            },
            
            // 销毁方法
            destroy: function() {
                if (this.decoderPtr) {
                    this.module._free(this.decoderPtr);
                    this.decoderPtr = null;
                }
            }
        };
        
        // 初始化编码器和解码器
        if (opusEncoder.init() && opusDecoder.init()) {
            console.log("Opus 编码器和解码器初始化成功。");
            return true;
        } else {
            console.error("Opus 初始化失败");
            return false;
        }
    } catch (error) {
        console.error("Opus 初始化失败:", error);
        return false;
    }
}

// 将Float32音频数据转换为Int16音频数据
function convertFloat32ToInt16(float32Data) {
    const int16Data = new Int16Array(float32Data.length);
    for (let i = 0; i < float32Data.length; i++) {
        // 将[-1,1]范围转换为[-32768,32767]
        const s = Math.max(-1, Math.min(1, float32Data[i]));
        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Data;
}

// 将Int16音频数据转换为Float32音频数据
function convertInt16ToFloat32(int16Data) {
    const float32Data = new Float32Array(int16Data.length);
    for (let i = 0; i < int16Data.length; i++) {
        // 将[-32768,32767]范围转换为[-1,1]
        float32Data[i] = int16Data[i] / (int16Data[i] < 0 ? 0x8000 : 0x7FFF);
    }
    return float32Data;
}

function startRecording() {
    if (isRecording) return;
    
    // 确保有权限并且AudioContext是活跃的
    if (audioContext.state === 'suspended') {
        audioContext.resume().then(() => {
            console.log("AudioContext已恢复");
            continueStartRecording();
        }).catch(err => {
            console.error("恢复AudioContext失败:", err);
            statusLabel.textContent = "无法激活音频上下文，请再次点击";
        });
    } else {
        continueStartRecording();
    }
}

// 实际开始录音的逻辑
function continueStartRecording() {
    // 重置录音数据
    recordedPcmData = [];
    recordedOpusData = [];
    window.audioDataBuffer = new Int16Array(0); // 重置缓冲区
    
    // 初始化Opus
    initOpus().then(success => {
        if (!success) {
            statusLabel.textContent = "Opus初始化失败";
            return;
        }
        
        console.log("开始录音，参数：", {
            sampleRate: SAMPLE_RATE,
            channels: CHANNELS,
            frameSize: FRAME_SIZE,
            bufferSize: BUFFER_SIZE
        });
        
        // 请求麦克风权限
        navigator.mediaDevices.getUserMedia({ 
            audio: {
                sampleRate: SAMPLE_RATE,
                channelCount: CHANNELS,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            } 
        })
        .then(stream => {
            console.log("获取到麦克风流，实际参数：", stream.getAudioTracks()[0].getSettings());
            
            // 检查流是否有效
            if (!stream || !stream.getAudioTracks().length || !stream.getAudioTracks()[0].enabled) {
                throw new Error("获取到的音频流无效");
            }
            
            mediaStream = stream;
            mediaSource = audioContext.createMediaStreamSource(stream);
            
            // 创建ScriptProcessor(虽然已弃用，但兼容性好)
            // 在降级到ScriptProcessor之前尝试使用AudioWorklet
            createAudioProcessor().then(processor => {
                if (processor) {
                    console.log("使用AudioWorklet处理音频");
                    audioProcessor = processor;
                    // 连接音频处理链
                    mediaSource.connect(audioProcessor);
                    audioProcessor.connect(audioContext.destination);
                } else {
                    console.log("回退到ScriptProcessor");
                    // 创建ScriptProcessor节点
                    audioProcessor = audioContext.createScriptProcessor(BUFFER_SIZE, CHANNELS, CHANNELS);
                    
                    // 处理音频数据
                    audioProcessor.onaudioprocess = processAudioData;
                    
                    // 连接音频处理链
                    mediaSource.connect(audioProcessor);
                    audioProcessor.connect(audioContext.destination);
                }
                
                // 更新UI
                isRecording = true;
                statusLabel.textContent = "录音中...";
                startButton.disabled = true;
                stopButton.disabled = false;
                playButton.disabled = true;
            }).catch(error => {
                console.error("创建音频处理器失败:", error);
                statusLabel.textContent = "创建音频处理器失败";
            });
        })
        .catch(error => {
            console.error("获取麦克风失败:", error);
            statusLabel.textContent = "获取麦克风失败: " + error.message;
        });
    });
}

// 创建AudioWorklet处理器
async function createAudioProcessor() {
    try {
        // 尝试使用更现代的AudioWorklet API
        if ('AudioWorklet' in window && 'AudioWorkletNode' in window) {
            // 定义AudioWorklet处理器代码
            const workletCode = `
                class OpusRecorderProcessor extends AudioWorkletProcessor {
                    constructor() {
                        super();
                        this.buffers = [];
                        this.frameSize = ${FRAME_SIZE};
                        this.buffer = new Float32Array(this.frameSize);
                        this.bufferIndex = 0;
                        this.isRecording = false;
                        
                        this.port.onmessage = (event) => {
                            if (event.data.command === 'start') {
                                this.isRecording = true;
                            } else if (event.data.command === 'stop') {
                                this.isRecording = false;
                                // 发送最后的缓冲区
                                if (this.bufferIndex > 0) {
                                    const finalBuffer = this.buffer.slice(0, this.bufferIndex);
                                    this.port.postMessage({ buffer: finalBuffer });
                                }
                            }
                        };
                    }
                    
                    process(inputs, outputs) {
                        if (!this.isRecording) return true;
                        
                        // 获取输入数据
                        const input = inputs[0][0]; // mono channel
                        if (!input || input.length === 0) return true;
                        
                        // 将输入数据添加到缓冲区
                        for (let i = 0; i < input.length; i++) {
                            this.buffer[this.bufferIndex++] = input[i];
                            
                            // 当缓冲区填满时，发送给主线程
                            if (this.bufferIndex >= this.frameSize) {
                                this.port.postMessage({ buffer: this.buffer.slice() });
                                this.bufferIndex = 0;
                            }
                        }
                        
                        return true;
                    }
                }
                
                registerProcessor('opus-recorder-processor', OpusRecorderProcessor);
            `;
            
            // 创建Blob URL
            const blob = new Blob([workletCode], { type: 'application/javascript' });
            const url = URL.createObjectURL(blob);
            
            // 加载AudioWorklet模块
            await audioContext.audioWorklet.addModule(url);
            
            // 创建AudioWorkletNode
            const workletNode = new AudioWorkletNode(audioContext, 'opus-recorder-processor');
            
            // 处理从AudioWorklet接收的消息
            workletNode.port.onmessage = (event) => {
                if (event.data.buffer) {
                    // 使用与ScriptProcessor相同的处理逻辑
                    processAudioData({
                        inputBuffer: {
                            getChannelData: () => event.data.buffer
                        }
                    });
                }
            };
            
            // 启动录音
            workletNode.port.postMessage({ command: 'start' });
            
            // 保存停止函数
            workletNode.stopRecording = () => {
                workletNode.port.postMessage({ command: 'stop' });
            };
            
            console.log("AudioWorklet 音频处理器创建成功");
            return workletNode;
        }
    } catch (error) {
        console.error("创建AudioWorklet失败，将使用ScriptProcessor:", error);
    }
    
    // 如果AudioWorklet不可用或失败，返回null以便回退到ScriptProcessor
    return null;
}

// 处理音频数据
function processAudioData(e) {
    // 获取输入缓冲区
    const inputBuffer = e.inputBuffer;
    
    // 获取第一个通道的Float32数据
    const inputData = inputBuffer.getChannelData(0);
    
    // 添加调试信息
    const nonZeroCount = Array.from(inputData).filter(x => Math.abs(x) > 0.001).length;
    console.log(`接收到音频数据: ${inputData.length} 个样本, 非零样本数: ${nonZeroCount}`);
    
    // 如果全是0，可能是麦克风没有正确获取声音
    if (nonZeroCount < 5) {
        console.warn("警告: 检测到大量静音样本，请检查麦克风是否正常工作");
        // 继续处理，以防有些样本确实是静音
    }
    
    // 存储PCM数据用于调试
    recordedPcmData.push(new Float32Array(inputData));
    
    // 转换为Int16数据供Opus编码
    const int16Data = convertFloat32ToInt16(inputData);
    
    // 如果收集到的数据不是FRAME_SIZE的整数倍，需要进行处理
    // 创建静态缓冲区来存储不足一帧的数据
    if (!window.audioDataBuffer) {
        window.audioDataBuffer = new Int16Array(0);
    }
    
    // 合并之前缓存的数据和新数据
    const combinedData = new Int16Array(window.audioDataBuffer.length + int16Data.length);
    combinedData.set(window.audioDataBuffer);
    combinedData.set(int16Data, window.audioDataBuffer.length);
    
    // 处理完整帧
    const frameCount = Math.floor(combinedData.length / FRAME_SIZE);
    console.log(`可编码的完整帧数: ${frameCount}, 缓冲区总大小: ${combinedData.length}`);
    
    for (let i = 0; i < frameCount; i++) {
        const frameData = combinedData.subarray(i * FRAME_SIZE, (i + 1) * FRAME_SIZE);
        
        try {
            console.log(`编码第 ${i+1}/${frameCount} 帧, 帧大小: ${frameData.length}`);
            const encodedData = opusEncoder.encode(frameData);
            if (encodedData) {
                console.log(`编码成功: ${encodedData.length} 字节`);
                recordedOpusData.push(encodedData);
            }
        } catch (error) {
            console.error(`Opus编码帧 ${i+1} 失败:`, error);
        }
    }
    
    // 保存剩余不足一帧的数据
    const remainingSamples = combinedData.length % FRAME_SIZE;
    if (remainingSamples > 0) {
        window.audioDataBuffer = combinedData.subarray(frameCount * FRAME_SIZE);
        console.log(`保留 ${remainingSamples} 个样本到下一次处理`);
    } else {
        window.audioDataBuffer = new Int16Array(0);
    }
}

function stopRecording() {
    if (!isRecording) return;
    
    // 处理剩余的缓冲数据
    if (window.audioDataBuffer && window.audioDataBuffer.length > 0) {
        console.log(`停止录音，处理剩余的 ${window.audioDataBuffer.length} 个样本`);
        // 如果剩余数据不足一帧，可以通过补零的方式凑成一帧
        if (window.audioDataBuffer.length < FRAME_SIZE) {
            const paddedFrame = new Int16Array(FRAME_SIZE);
            paddedFrame.set(window.audioDataBuffer);
            // 剩余部分填充为0
            for (let i = window.audioDataBuffer.length; i < FRAME_SIZE; i++) {
                paddedFrame[i] = 0;
            }
            try {
                console.log(`编码最后一帧(补零): ${paddedFrame.length} 样本`);
                const encodedData = opusEncoder.encode(paddedFrame);
                if (encodedData) {
                    recordedOpusData.push(encodedData);
                }
            } catch (error) {
                console.error("最后一帧Opus编码失败:", error);
            }
        } else {
            // 如果数据超过一帧，按正常流程处理
            processAudioData({
                inputBuffer: {
                    getChannelData: () => convertInt16ToFloat32(window.audioDataBuffer)
                }
            });
        }
        window.audioDataBuffer = null;
    }
    
    // 如果使用的是AudioWorklet，调用其特定的停止方法
    if (audioProcessor && typeof audioProcessor.stopRecording === 'function') {
        audioProcessor.stopRecording();
    }
    
    // 停止麦克风
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
    }
    
    // 断开音频处理链
    if (audioProcessor) {
        try {
            audioProcessor.disconnect();
            if (mediaSource) mediaSource.disconnect();
        } catch (error) {
            console.warn("断开音频处理链时出错:", error);
        }
    }
    
    // 更新UI
    isRecording = false;
    statusLabel.textContent = "已停止录音，收集了 " + recordedOpusData.length + " 帧Opus数据";
    startButton.disabled = false;
    stopButton.disabled = true;
    playButton.disabled = recordedOpusData.length === 0;
    
    console.log("录制完成:", 
                "PCM帧数:", recordedPcmData.length, 
                "Opus帧数:", recordedOpusData.length);
}

function playRecording() {
    if (!recordedOpusData.length) {
        statusLabel.textContent = "没有可播放的录音";
        return;
    }
    
    // 将所有Opus数据解码为PCM
    let allDecodedData = [];
    
    for (const opusData of recordedOpusData) {
        try {
            // 解码为Int16数据
            const decodedData = opusDecoder.decode(opusData);
            
            if (decodedData && decodedData.length > 0) {
                // 将Int16数据转换为Float32
                const float32Data = convertInt16ToFloat32(decodedData);
                
                // 添加到总解码数据中
                allDecodedData.push(...float32Data);
            }
        } catch (error) {
            console.error("Opus解码失败:", error);
        }
    }
    
    // 如果没有解码出数据，返回
    if (allDecodedData.length === 0) {
        statusLabel.textContent = "解码失败，无法播放";
        return;
    }
    
    // 创建音频缓冲区
    const audioBuffer = audioContext.createBuffer(CHANNELS, allDecodedData.length, SAMPLE_RATE);
    audioBuffer.copyToChannel(new Float32Array(allDecodedData), 0);
    
    // 创建音频源并播放
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();
    
    // 更新UI
    statusLabel.textContent = "正在播放...";
    playButton.disabled = true;
    
    // 播放结束后恢复UI
    source.onended = () => {
        statusLabel.textContent = "播放完毕";
        playButton.disabled = false;
    };
}

// 模拟服务端返回的Opus数据进行解码播放
function playOpusFromServer(opusData) {
    // 这个函数展示如何处理服务端返回的opus数据
    // opusData应该是一个包含opus帧的数组
    
    if (!opusDecoder) {
        initOpus().then(success => {
            if (success) {
                decodeAndPlayOpusData(opusData);
            } else {
                statusLabel.textContent = "Opus解码器初始化失败";
            }
        });
    } else {
        decodeAndPlayOpusData(opusData);
    }
}

function decodeAndPlayOpusData(opusData) {
    let allDecodedData = [];
    
    for (const frame of opusData) {
        try {
            const decodedData = opusDecoder.decode(frame);
            if (decodedData && decodedData.length > 0) {
                const float32Data = convertInt16ToFloat32(decodedData);
                allDecodedData.push(...float32Data);
            }
        } catch (error) {
            console.error("服务端Opus数据解码失败:", error);
        }
    }
    
    if (allDecodedData.length === 0) {
        statusLabel.textContent = "服务端数据解码失败";
        return;
    }
    
    const audioBuffer = audioContext.createBuffer(CHANNELS, allDecodedData.length, SAMPLE_RATE);
    audioBuffer.copyToChannel(new Float32Array(allDecodedData), 0);
    
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();
    
    statusLabel.textContent = "正在播放服务端数据...";
    source.onended = () => statusLabel.textContent = "服务端数据播放完毕";
}
