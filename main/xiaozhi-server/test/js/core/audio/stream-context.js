import BlockingQueue from '../../utils/blocking-queue.js';
import { log } from '../../utils/logger.js';

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
        this.scheduledEndTime = 0; // 已调度音频的结束时间

        // 初始化分析器节点（供Live2D使用）
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
    }

    // 缓存音频数组
    pushAudioBuffer(item) {
        this.audioBufferQueue.enqueue(...item);
    }

    // 获取需要处理缓存队列，单线程：在audioBufferQueue一直更新的状态下不会出现安全问题
    async getPendingAudioBufferQueue() {
        // 等待数据到达并获取
        const data = await this.audioBufferQueue.dequeue();
        // 赋值给待处理队列
        this.pendingAudioBufferQueue = data;
    }

    // 获取正在播放已解码的PCM队列，单线程：在activeQueue一直更新的状态下不会出现安全问题
    async getQueue(minSamples) {
        const num = minSamples - this.queue.length > 0 ? minSamples - this.queue.length : 1;

        // 等待数据并获取
        const tempArray = await this.activeQueue.dequeue(num);
        this.queue.push(...tempArray);
    }

    // 将Int16音频数据转换为Float32音频数据
    convertInt16ToFloat32(int16Data) {
        const float32Data = new Float32Array(int16Data.length);
        for (let i = 0; i < int16Data.length; i++) {
            // 将[-32768,32767]范围转换为[-1,1]，统一使用32768.0避免不对称失真
            float32Data[i] = int16Data[i] / 32768.0;
        }
        return float32Data;
    }

    // 获取待解码包数
    getPendingDecodeCount() {
        return this.audioBufferQueue.length + this.pendingAudioBufferQueue.length;
    }

    // 获取待播放样本数（转换为包数，每包960样本）
    getPendingPlayCount() {
        // 计算已在队列中的样本
        const queuedSamples = this.activeQueue.length + this.queue.length;

        // 计算已调度但未播放的样本（在Web Audio缓冲区中）
        let scheduledSamples = 0;
        if (this.playing && this.scheduledEndTime) {
            const currentTime = this.audioContext.currentTime;
            const remainingTime = Math.max(0, this.scheduledEndTime - currentTime);
            scheduledSamples = Math.floor(remainingTime * this.sampleRate);
        }

        const totalSamples = queuedSamples + scheduledSamples;
        return Math.ceil(totalSamples / 960);
    }

    // 清空所有音频缓冲
    clearAllBuffers() {
        log('清空所有音频缓冲', 'info');

        // 清空所有队列（使用clear方法保持对象引用）
        this.audioBufferQueue.clear();
        this.pendingAudioBufferQueue = [];
        this.activeQueue.clear();
        this.queue = [];

        // 停止当前播放的音频源
        if (this.source) {
            try {
                this.source.stop();
                this.source.disconnect();
            } catch (e) {
                // 忽略已经停止的错误
            }
            this.source = null;
        }

        // 重置状态
        this.playing = false;
        this.scheduledEndTime = this.audioContext.currentTime;
        this.totalSamples = 0;

        log('音频缓冲已清空', 'success');
    }

    // 获取分析器节点（供Live2D使用）
    getAnalyser() {
        return this.analyser;
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
        this.scheduledEndTime = this.audioContext.currentTime; // 跟踪已调度音频的结束时间

        while (true) {
            // 初始缓冲：等待足够的样本再开始播放
            const minSamples = this.sampleRate * this.minAudioDuration * 2;
            if (!this.playing && this.queue.length < minSamples) {
                await this.getQueue(minSamples);
            }
            this.playing = true;

            // 持续播放队列中的音频，每次播放一个小块
            while (this.playing && this.queue.length > 0) {
                // 每次播放120ms的音频（2个Opus包）
                const playDuration = 0.12;
                const targetSamples = Math.floor(this.sampleRate * playDuration);
                const actualSamples = Math.min(this.queue.length, targetSamples);

                if (actualSamples === 0) break;

                const currentSamples = this.queue.splice(0, actualSamples);
                const audioBuffer = this.audioContext.createBuffer(this.channels, currentSamples.length, this.sampleRate);
                audioBuffer.copyToChannel(new Float32Array(currentSamples), 0);

                // 创建音频源
                this.source = this.audioContext.createBufferSource();
                this.source.buffer = audioBuffer;

                // 精确调度播放时间
                const currentTime = this.audioContext.currentTime;
                const startTime = Math.max(this.scheduledEndTime, currentTime);

                // 连接到分析器和输出
                this.source.connect(this.analyser);
                this.source.connect(this.audioContext.destination);

                log(`调度播放 ${currentSamples.length} 个样本，约 ${(currentSamples.length / this.sampleRate).toFixed(2)} 秒`, 'debug');
                this.source.start(startTime);

                // 更新下一个音频块的调度时间
                const duration = audioBuffer.duration;
                this.scheduledEndTime = startTime + duration;
                this.lastPlayTime = startTime;

                // 如果队列中数据不足，等待新数据
                if (this.queue.length < targetSamples) {
                    break;
                }
            }

            // 等待新数据
            await this.getQueue(minSamples);
        }
    }
}

// 创建streamingContext实例的工厂函数
export function createStreamingContext(opusDecoder, audioContext, sampleRate, channels, minAudioDuration) {
    return new StreamingContext(opusDecoder, audioContext, sampleRate, channels, minAudioDuration);
}