const SAMPLE_RATE = 16000;
const CHANNELS = 1;
const FRAME_SIZE = 960;  // 对应于60ms帧大小 (16000Hz * 0.06s = 960 samples)
const OPUS_APPLICATION = 2049; // OPUS_APPLICATION_AUDIO
const BUFFER_SIZE = 4096;

// WebSocket相关变量
let websocket = null;
let isConnected = false;

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

// 添加WebSocket界面元素引用
const connectButton = document.getElementById("connectButton") || document.createElement("button");
const serverUrlInput = document.getElementById("serverUrl") || document.createElement("input");
const connectionStatus = document.getElementById("connectionStatus") || document.createElement("span");
const sendTextButton = document.getElementById("sendTextButton") || document.createElement("button");
const messageInput = document.getElementById("messageInput") || document.createElement("input");
const conversationDiv = document.getElementById("conversation") || document.createElement("div");

// 添加连接和发送事件监听
if(connectButton.id === "connectButton") {
    connectButton.addEventListener("click", connectToServer);
}
if(sendTextButton.id === "sendTextButton") {
    sendTextButton.addEventListener("click", sendTextMessage);
}

startButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);
playButton.addEventListener("click", playRecording);

// 音频缓冲和播放管理
let audioBufferQueue = [];     // 存储接收到的音频包
let isAudioBuffering = false;  // 是否正在缓冲音频
let isAudioPlaying = false;    // 是否正在播放音频
const BUFFER_THRESHOLD = 3;    // 缓冲包数量阈值，至少累积5个包再开始播放
const MIN_AUDIO_DURATION = 0.1; // 最小音频长度(秒)，小于这个长度的音频会被合并
let streamingContext = null;   // 音频流上下文

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
        
        // 如果WebSocket已连接，发送开始录音信号
        if (isConnected && websocket && websocket.readyState === WebSocket.OPEN) {
            sendVoiceControlMessage('start');
        }
        
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
                
                // 如果WebSocket已连接，发送编码后的数据
                if (isConnected && websocket && websocket.readyState === WebSocket.OPEN) {
                    sendOpusDataToServer(encodedData);
                }
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
                    
                    // 如果WebSocket已连接，发送最后一帧
                    if (isConnected && websocket && websocket.readyState === WebSocket.OPEN) {
                        sendOpusDataToServer(encodedData);
                    }
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
    
    // 如果WebSocket已连接，发送停止录音信号
    if (isConnected && websocket && websocket.readyState === WebSocket.OPEN) {
        // 发送一个空帧作为结束标记
        const emptyFrame = new Uint8Array(0);
        websocket.send(emptyFrame);
        
        // 发送停止录音控制消息
        sendVoiceControlMessage('stop');
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

// 处理二进制消息的修改版本
async function handleBinaryMessage(data) {
    try {
        let arrayBuffer;

        // 根据数据类型进行处理
        if (data instanceof ArrayBuffer) {
            arrayBuffer = data;
            console.log(`收到ArrayBuffer音频数据，大小: ${data.byteLength}字节`);
        } else if (data instanceof Blob) {
            // 如果是Blob类型，转换为ArrayBuffer
            arrayBuffer = await data.arrayBuffer();
            console.log(`收到Blob音频数据，大小: ${arrayBuffer.byteLength}字节`);
        } else {
            console.warn(`收到未知类型的二进制数据: ${typeof data}`);
            return;
        }

        // 创建Uint8Array用于处理
        const opusData = new Uint8Array(arrayBuffer);

        if (opusData.length > 0) {
            // 将数据添加到缓冲队列
            audioBufferQueue.push(opusData);
            
            // 如果收到的是第一个音频包，开始缓冲过程
            if (audioBufferQueue.length === 1 && !isAudioBuffering && !isAudioPlaying) {
                startAudioBuffering();
            }
        } else {
            console.warn('收到空音频数据帧，可能是结束标志');
            
            // 如果缓冲队列中有数据且没有在播放，立即开始播放
            if (audioBufferQueue.length > 0 && !isAudioPlaying) {
                playBufferedAudio();
            }
            
            // 如果正在播放，发送结束信号
            if (isAudioPlaying && streamingContext) {
                streamingContext.endOfStream = true;
            }
        }
    } catch (error) {
        console.error(`处理二进制消息出错:`, error);
    }
}

// 开始音频缓冲过程
function startAudioBuffering() {
    if (isAudioBuffering || isAudioPlaying) return;
    
    isAudioBuffering = true;
    console.log("开始音频缓冲...");
    
    // 设置超时，如果在一定时间内没有收集到足够的音频包，就开始播放
    setTimeout(() => {
        if (isAudioBuffering && audioBufferQueue.length > 0) {
            console.log(`缓冲超时，当前缓冲包数: ${audioBufferQueue.length}，开始播放`);
            playBufferedAudio();
        }
    }, 300); // 300ms超时
    
    // 监控缓冲进度
    const bufferCheckInterval = setInterval(() => {
        if (!isAudioBuffering) {
            clearInterval(bufferCheckInterval);
            return;
        }
        
        // 当累积了足够的音频包，开始播放
        if (audioBufferQueue.length >= BUFFER_THRESHOLD) {
            clearInterval(bufferCheckInterval);
            console.log(`已缓冲 ${audioBufferQueue.length} 个音频包，开始播放`);
            playBufferedAudio();
        }
    }, 50);
}

// 播放已缓冲的音频
function playBufferedAudio() {
    if (isAudioPlaying || audioBufferQueue.length === 0) return;
    
    isAudioPlaying = true;
    isAudioBuffering = false;
    
    // 创建流式播放上下文
    if (!streamingContext) {
        streamingContext = {
            queue: [],          // 已解码的PCM队列
            playing: false,     // 是否正在播放
            endOfStream: false, // 是否收到结束信号
            source: null,       // 当前音频源
            totalSamples: 0,    // 累积的总样本数
            lastPlayTime: 0,    // 上次播放的时间戳
            // 将Opus数据解码为PCM
            decodeOpusFrames: async function(opusFrames) {
                let decodedSamples = [];
                
                for (const frame of opusFrames) {
                    try {
                        // 使用Opus解码器解码
                        const frameData = opusDecoder.decode(frame);
                        if (frameData && frameData.length > 0) {
                            // 转换为Float32
                            const floatData = convertInt16ToFloat32(frameData);
                            decodedSamples.push(...floatData);
                        }
                    } catch (error) {
                        console.error("Opus解码失败:", error);
                    }
                }
                
                if (decodedSamples.length > 0) {
                    // 添加到解码队列
                    this.queue.push(...decodedSamples);
                    this.totalSamples += decodedSamples.length;
                    
                    // 如果累积了至少0.2秒的音频，开始播放
                    const minSamples = SAMPLE_RATE * MIN_AUDIO_DURATION;
                    if (!this.playing && this.queue.length >= minSamples) {
                        this.startPlaying();
                    }
                }
            },
            // 开始播放音频
            startPlaying: function() {
                if (this.playing || this.queue.length === 0) return;
                
                this.playing = true;
                
                // 创建新的音频缓冲区
                const minPlaySamples = Math.min(this.queue.length, SAMPLE_RATE); // 最多播放1秒
                const currentSamples = this.queue.splice(0, minPlaySamples);
                
                const audioBuffer = audioContext.createBuffer(CHANNELS, currentSamples.length, SAMPLE_RATE);
                audioBuffer.copyToChannel(new Float32Array(currentSamples), 0);
                
                // 创建音频源
                this.source = audioContext.createBufferSource();
                this.source.buffer = audioBuffer;
                
                // 创建增益节点用于平滑过渡
                const gainNode = audioContext.createGain();
                
                // 应用淡入淡出效果避免爆音
                const fadeDuration = 0.02; // 20毫秒
                gainNode.gain.setValueAtTime(0, audioContext.currentTime);
                gainNode.gain.linearRampToValueAtTime(1, audioContext.currentTime + fadeDuration);
                
                const duration = audioBuffer.duration;
                if (duration > fadeDuration * 2) {
                    gainNode.gain.setValueAtTime(1, audioContext.currentTime + duration - fadeDuration);
                    gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + duration);
                }
                
                // 连接节点并开始播放
                this.source.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                this.lastPlayTime = audioContext.currentTime;
                console.log(`开始播放 ${currentSamples.length} 个样本，约 ${(currentSamples.length / SAMPLE_RATE).toFixed(2)} 秒`);
                
                // 播放结束后的处理
                this.source.onended = () => {
                    this.source = null;
                    this.playing = false;
                    
                    // 如果队列中还有数据或者缓冲区有新数据，继续播放
                    if (this.queue.length > 0) {
                        setTimeout(() => this.startPlaying(), 10);
                    } else if (audioBufferQueue.length > 0) {
                        // 缓冲区有新数据，进行解码
                        const frames = [...audioBufferQueue];
                        audioBufferQueue = [];
                        this.decodeOpusFrames(frames);
                    } else if (this.endOfStream) {
                        // 流已结束且没有更多数据
                        console.log("音频播放完成");
                        isAudioPlaying = false;
                        streamingContext = null;
                    } else {
                        // 等待更多数据
                        setTimeout(() => {
                            // 如果仍然没有新数据，但有更多的包到达
                            if (this.queue.length === 0 && audioBufferQueue.length > 0) {
                                const frames = [...audioBufferQueue];
                                audioBufferQueue = [];
                                this.decodeOpusFrames(frames);
                            } else if (this.queue.length === 0 && audioBufferQueue.length === 0) {
                                // 真的没有更多数据了
                                console.log("音频播放完成 (超时)");
                                isAudioPlaying = false;
                                streamingContext = null;
                            }
                        }, 500); // 500ms超时
                    }
                };
                
                this.source.start();
            }
        };
    }
    
    // 开始处理缓冲的数据
    const frames = [...audioBufferQueue];
    audioBufferQueue = []; // 清空缓冲队列
    
    // 解码并播放
    streamingContext.decodeOpusFrames(frames);
}

// 将旧的playOpusFromServer函数保留为备用方法
function playOpusFromServerOld(opusData) {
    if (!opusDecoder) {
        initOpus().then(success => {
            if (success) {
                decodeAndPlayOpusDataOld(opusData);
            } else {
                statusLabel.textContent = "Opus解码器初始化失败";
            }
        });
    } else {
        decodeAndPlayOpusDataOld(opusData);
    }
}

// 旧的解码和播放函数作为备用
function decodeAndPlayOpusDataOld(opusData) {
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

// 更新playOpusFromServer函数为Promise版本
function playOpusFromServer(opusData) {
    // 为了兼容，我们将opusData添加到audioBufferQueue并触发播放
    if (Array.isArray(opusData) && opusData.length > 0) {
        for (const frame of opusData) {
            audioBufferQueue.push(frame);
        }
        
        // 如果没有在播放和缓冲，启动流程
        if (!isAudioBuffering && !isAudioPlaying) {
            startAudioBuffering();
        }
        
        return new Promise(resolve => {
            // 我们无法准确知道何时播放完成，所以设置一个合理的超时
            setTimeout(resolve, 1000); // 1秒后认为已处理
        });
    } else {
        // 如果不是数组或为空，使用旧方法
        return new Promise(resolve => {
            playOpusFromServerOld(opusData);
            setTimeout(resolve, 1000);
        });
    }
}

// 连接WebSocket服务器
function connectToServer() {
    let url = serverUrlInput.value || "ws://127.0.0.1:8000/xiaozhi/v1/";
    
    try {
        // 检查URL格式
        if (!url.startsWith('ws://') && !url.startsWith('wss://')) {
            console.error('URL格式错误，必须以ws://或wss://开头');
            updateStatus('URL格式错误，必须以ws://或wss://开头', 'error');
            return;
        }

        // 添加认证参数
        let connUrl = new URL(url);
        connUrl.searchParams.append('device_id', 'web_test_device');
        connUrl.searchParams.append('device_mac', '00:11:22:33:44:55');

        console.log(`正在连接: ${connUrl.toString()}`);
        updateStatus(`正在连接: ${connUrl.toString()}`, 'info');
        
        websocket = new WebSocket(connUrl.toString());

        // 设置接收二进制数据的类型为ArrayBuffer
        websocket.binaryType = 'arraybuffer';

        websocket.onopen = async () => {
            console.log(`已连接到服务器: ${url}`);
            updateStatus(`已连接到服务器: ${url}`, 'success');
            isConnected = true;

            // 连接成功后发送hello消息
            await sendHelloMessage();

            if(connectButton.id === "connectButton") {
                connectButton.textContent = '断开';
                connectButton.onclick = disconnectFromServer;
            }
            
            if(messageInput.id === "messageInput") {
                messageInput.disabled = false;
            }
            
            if(sendTextButton.id === "sendTextButton") {
                sendTextButton.disabled = false;
            }
        };

        websocket.onclose = () => {
            console.log('已断开连接');
            updateStatus('已断开连接', 'info');
            isConnected = false;

            if(connectButton.id === "connectButton") {
                connectButton.textContent = '连接';
                connectButton.onclick = connectToServer;
            }
            
            if(messageInput.id === "messageInput") {
                messageInput.disabled = true;
            }
            
            if(sendTextButton.id === "sendTextButton") {
                sendTextButton.disabled = true;
            }
        };

        websocket.onerror = (error) => {
            console.error(`WebSocket错误:`, error);
            updateStatus(`WebSocket错误`, 'error');
        };

        websocket.onmessage = function (event) {
            try {
                // 检查是否为文本消息
                if (typeof event.data === 'string') {
                    const message = JSON.parse(event.data);
                    handleTextMessage(message);
                } else {
                    // 处理二进制数据
                    handleBinaryMessage(event.data);
                }
            } catch (error) {
                console.error(`WebSocket消息处理错误:`, error);
                // 非JSON格式文本消息直接显示
                if (typeof event.data === 'string') {
                    addMessage(event.data);
                }
            }
        };

        updateStatus('正在连接...', 'info');
    } catch (error) {
        console.error(`连接错误:`, error);
        updateStatus(`连接失败: ${error.message}`, 'error');
    }
}

// 断开WebSocket连接
function disconnectFromServer() {
    if (!websocket) return;

    websocket.close();
    if (isRecording) {
        stopRecording();
    }
}

// 发送hello握手消息
async function sendHelloMessage() {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;

    try {
        // 设置设备信息
        const helloMessage = {
            type: 'hello',
            device_id: 'web_test_device',
            device_name: 'Web测试设备',
            device_mac: '00:11:22:33:44:55',
            token: 'your-token1' // 使用config.yaml中配置的token
        };

        console.log('发送hello握手消息');
        websocket.send(JSON.stringify(helloMessage));

        // 等待服务器响应
        return new Promise(resolve => {
            // 5秒超时
            const timeout = setTimeout(() => {
                console.error('等待hello响应超时');
                resolve(false);
            }, 5000);

            // 临时监听一次消息，接收hello响应
            const onMessageHandler = (event) => {
                try {
                    const response = JSON.parse(event.data);
                    if (response.type === 'hello' && response.session_id) {
                        console.log(`服务器握手成功，会话ID: ${response.session_id}`);
                        clearTimeout(timeout);
                        websocket.removeEventListener('message', onMessageHandler);
                        resolve(true);
                    }
                } catch (e) {
                    // 忽略非JSON消息
                }
            };

            websocket.addEventListener('message', onMessageHandler);
        });
    } catch (error) {
        console.error(`发送hello消息错误:`, error);
        return false;
    }
}

// 发送文本消息
function sendTextMessage() {
    const message = messageInput ? messageInput.value.trim() : "";
    if (message === '' || !websocket || websocket.readyState !== WebSocket.OPEN) return;

    try {
        // 发送listen消息
        const listenMessage = {
            type: 'listen',
            mode: 'manual',
            state: 'detect',
            text: message
        };

        websocket.send(JSON.stringify(listenMessage));
        addMessage(message, true);
        console.log(`发送文本消息: ${message}`);

        if (messageInput) {
            messageInput.value = '';
        }
    } catch (error) {
        console.error(`发送消息错误:`, error);
    }
}

// 添加消息到会话记录
function addMessage(text, isUser = false) {
    if (!conversationDiv) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'server'}`;
    messageDiv.textContent = text;
    conversationDiv.appendChild(messageDiv);
    conversationDiv.scrollTop = conversationDiv.scrollHeight;
}

// 更新状态信息
function updateStatus(message, type = 'info') {
    console.log(`[${type}] ${message}`);
    if (statusLabel) {
        statusLabel.textContent = message;
    }
    if (connectionStatus) {
        connectionStatus.textContent = message;
        switch(type) {
            case 'success':
                connectionStatus.style.color = 'green';
                break;
            case 'error':
                connectionStatus.style.color = 'red';
                break;
            case 'info':
            default:
                connectionStatus.style.color = 'black';
                break;
        }
    }
}

// 处理文本消息
function handleTextMessage(message) {
    if (message.type === 'hello') {
        console.log(`服务器回应：${message.message}`);
    } else if (message.type === 'tts') {
        // TTS状态消息
        if (message.state === 'start') {
            console.log('服务器开始发送语音');
        } else if (message.state === 'sentence_start') {
            console.log(`服务器发送语音段: ${message.text}`);
            // 添加文本到会话记录
            if (message.text) {
                addMessage(message.text);
            }
        } else if (message.state === 'sentence_end') {
            console.log(`语音段结束: ${message.text}`);
        } else if (message.state === 'stop') {
            console.log('服务器语音传输结束');
        }
    } else if (message.type === 'audio') {
        // 音频控制消息
        console.log(`收到音频控制消息: ${JSON.stringify(message)}`);
    } else if (message.type === 'stt') {
        // 语音识别结果
        console.log(`识别结果: ${message.text}`);
        // 添加识别结果到会话记录
        addMessage(`[语音识别] ${message.text}`, true);
    } else if (message.type === 'llm') {
        // 大模型回复
        console.log(`大模型回复: ${message.text}`);
        // 添加大模型回复到会话记录
        if (message.text && message.text !== '😊') {
            addMessage(message.text);
        }
    } else {
        // 未知消息类型
        console.log(`未知消息类型: ${message.type}`);
        addMessage(JSON.stringify(message, null, 2));
    }
}

// 发送语音数据到WebSocket
function sendOpusDataToServer(opusData) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket未连接，无法发送音频数据');
        return false;
    }

    try {
        // 发送二进制数据
        websocket.send(opusData.buffer);
        console.log(`已发送Opus音频数据: ${opusData.length}字节`);
        return true;
    } catch (error) {
        console.error(`发送音频数据失败:`, error);
        return false;
    }
}

// 发送语音开始和结束信号
function sendVoiceControlMessage(state) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;

    try {
        const message = {
            type: 'listen',
            mode: 'manual',
            state: state  // 'start' 或 'stop'
        };

        websocket.send(JSON.stringify(message));
        console.log(`发送语音${state === 'start' ? '开始' : '结束'}控制消息`);
    } catch (error) {
        console.error(`发送语音控制消息失败:`, error);
    }
}
