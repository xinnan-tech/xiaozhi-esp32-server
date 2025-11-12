import BlockingQueue from './utils/BlockingQueue.js';
import { log } from './utils/logger.js';

// 音频流播放上下文类
export class StreamingContext {
    constructor(opusDecoder, audioContext, sampleRate, channels, minAudioDuration) {
        this.opusDecoder = opusDecoder;
        this.audioContext = audioContext;

        // 音频参数
        this.sampleRate = sampleRate;
        this.channels = channels;
        this.minAudioDuration = minAudioDuration;

        // 初始化队列和状态
        this.queue = [];          // 已解码的PCM队列。正在播放
        this.activeQueue = new BlockingQueue(); // 已解码的PCM队列。准备播放
        this.pendingAudioBufferQueue = [];  // 待处理的缓存队列
        this.audioBufferQueue = new BlockingQueue();  // 缓存队列
        this.playing = false;     // 是否正在播放
        this.endOfStream = false; // 是否收到结束信号
        this.source = null;       // 当前音频源
        this.totalSamples = 0;    // 累积的总样本数
        this.lastPlayTime = 0;    // 上次播放的时间戳
    }

    // 缓存音频数组
    pushAudioBuffer(item) {
        this.audioBufferQueue.enqueue(...item);
    }

    // 获取需要处理缓存队列，单线程：在audioBufferQueue一直更新的状态下不会出现安全问题
    async getPendingAudioBufferQueue() {
        // 原子交换 + 清空
        [this.pendingAudioBufferQueue, this.audioBufferQueue] = [await this.audioBufferQueue.dequeue(), new BlockingQueue()];
    }

    // 获取正在播放已解码的PCM队列，单线程：在activeQueue一直更新的状态下不会出现安全问题
    async getQueue(minSamples) {
        let TepArray = [];
        const num = minSamples - this.queue.length > 0 ? minSamples - this.queue.length : 1;
        // 原子交换 + 清空
        [TepArray, this.activeQueue] = [await this.activeQueue.dequeue(num), new BlockingQueue()];
        this.queue.push(...TepArray);
    }

    // 将Int16音频数据转换为Float32音频数据
    convertInt16ToFloat32(int16Data) {
        const float32Data = new Float32Array(int16Data.length);
        for (let i = 0; i < int16Data.length; i++) {
            // 将[-32768,32767]范围转换为[-1,1]
            float32Data[i] = int16Data[i] / (int16Data[i] < 0 ? 0x8000 : 0x7FFF);
        }
        return float32Data;
    }

    // 将Opus数据解码为PCM
    async decodeOpusFrames() {
        if (!this.opusDecoder) {
            log('Opus解码器未初始化，无法解码', 'error');
            return;
        } else {
            log('Opus解码器启动', 'info');
        }

        while (true) {
            let decodedSamples = [];
            for (const frame of this.pendingAudioBufferQueue) {
                try {
                    // 使用Opus解码器解码
                    const frameData = this.opusDecoder.decode(frame);
                    if (frameData && frameData.length > 0) {
                        // 转换为Float32
                        const floatData = this.convertInt16ToFloat32(frameData);
                        // 使用循环替代展开运算符
                        for (let i = 0; i < floatData.length; i++) {
                            decodedSamples.push(floatData[i]);
                        }
                    }
                } catch (error) {
                    log("Opus解码失败: " + error.message, 'error');
                }
            }

            if (decodedSamples.length > 0) {
                // 使用循环替代展开运算符
                for (let i = 0; i < decodedSamples.length; i++) {
                    this.activeQueue.enqueue(decodedSamples[i]);
                }
                this.totalSamples += decodedSamples.length;
            } else {
                log('没有成功解码的样本', 'warning');
            }
            await this.getPendingAudioBufferQueue();
        }
    }

    // 开始播放音频
    async startPlaying() {
        while (true) {
            // 如果累积了至少0.3秒的音频，开始播放
            const minSamples = this.sampleRate * this.minAudioDuration * 3;
            if (!this.playing && this.queue.length < minSamples) {
                await this.getQueue(minSamples);
            }
            this.playing = true;
            while (this.playing && this.queue.length) {
                // 创建新的音频缓冲区
                const minPlaySamples = Math.min(this.queue.length, this.sampleRate);
                const currentSamples = this.queue.splice(0, minPlaySamples);

                const audioBuffer = this.audioContext.createBuffer(this.channels, currentSamples.length, this.sampleRate);
                audioBuffer.copyToChannel(new Float32Array(currentSamples), 0);

                // 创建音频源
                this.source = this.audioContext.createBufferSource();
                this.source.buffer = audioBuffer;

                // 创建增益节点用于平滑过渡
                const gainNode = this.audioContext.createGain();

                // 应用淡入淡出效果避免爆音
                const fadeDuration = 0.02; // 20毫秒
                gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
                gainNode.gain.linearRampToValueAtTime(1, this.audioContext.currentTime + fadeDuration);

                const duration = audioBuffer.duration;
                if (duration > fadeDuration * 2) {
                    gainNode.gain.setValueAtTime(1, this.audioContext.currentTime + duration - fadeDuration);
                    gainNode.gain.linearRampToValueAtTime(0, this.audioContext.currentTime + duration);
                }

                // 连接节点并开始播放
                this.source.connect(gainNode);
                gainNode.connect(this.audioContext.destination);

                this.lastPlayTime = this.audioContext.currentTime;
                log(`开始播放 ${currentSamples.length} 个样本，约 ${(currentSamples.length / this.sampleRate).toFixed(2)} 秒`, 'info');
                this.source.start();
            }
            await this.getQueue(minSamples);
        }
    }
}

// 创建streamingContext实例的工厂函数
export function createStreamingContext(opusDecoder, audioContext, sampleRate, channels, minAudioDuration) {
    return new StreamingContext(opusDecoder, audioContext, sampleRate, channels, minAudioDuration);
}