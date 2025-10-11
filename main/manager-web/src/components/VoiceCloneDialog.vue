<template>
    <el-dialog :title="$t('voiceClone.dialogTitle')" :visible.sync="visible" width="900px" top="10vh"
        :before-close="handleClose" class="voice-clone-dialog">
        <div class="dialog-content">
            <!-- 步骤指示器 -->
            <div class="steps-header">
                <div class="step-item" :class="{ 'active': currentStep === 1, 'completed': currentStep > 1 }">
                    <div class="step-number">
                        <i class="el-icon-check" v-if="currentStep > 1"></i>
                        <span v-else>1</span>
                    </div>
                    <div class="step-label">{{ $t('voiceClone.stepUpload') }}</div>
                    <div class="step-line"></div>
                </div>
                <div class="step-item" :class="{ 'active': currentStep === 2, 'completed': currentStep > 2 }">
                    <div class="step-number">
                        <i class="el-icon-check" v-if="currentStep > 2"></i>
                        <span v-else>2</span>
                    </div>
                    <div class="step-label">{{ $t('voiceClone.stepEdit') }}</div>
                </div>
            </div>

            <!-- 步骤1: 音频上传 -->
            <div v-if="currentStep === 1" class="step-content">
                <div class="upload-area">
                    <el-upload class="audio-uploader" drag :action="uploadAction" :auto-upload="false"
                        :on-change="handleFileChange" :show-file-list="false" accept="audio/*">
                        <i class="el-icon-upload"></i>
                        <div class="el-upload__text">{{ $t('voiceClone.dragOrClick') }}</div>
                        <div class="el-upload__tip">{{ $t('voiceClone.uploadTip') }}</div>
                    </el-upload>
                </div>
            </div>

            <!-- 步骤2: 音频编辑 -->
            <div v-if="currentStep === 2" class="step-content">
                <div class="audio-edit-area">
                    <div class="edit-tips">
                        <p>{{ $t('voiceClone.editTip1') }}</p>
                        <p>{{ $t('voiceClone.editTip2') }}</p>
                    </div>

                    <!-- 波形显示区域 -->
                    <div class="waveform-container">
                        <canvas ref="waveformCanvas" class="waveform-canvas" @mousedown="handleWaveformMouseDown"
                            @mousemove="handleWaveformMouseMove" @mouseup="handleWaveformMouseUp"></canvas>
                        <div class="selection-overlay" v-if="isSelecting || selectionStart !== null"
                            :style="selectionStyle"></div>
                        <div class="duration-display">
                            {{ $t('voiceClone.selectedDuration', { duration: selectedDuration.toFixed(1) }) }}
                        </div>
                    </div>

                    <!-- 音频控制按钮 -->
                    <div class="audio-controls">
                        <el-button size="small" :icon="isPlaying ? 'el-icon-video-pause' : 'el-icon-video-play'"
                            @click="togglePlay" type="primary">
                            {{ isPlaying ? $t('voiceClone.pause') : $t('voiceClone.play') }}
                        </el-button>
                        <el-button size="small" icon="el-icon-scissors" @click="handleTrim"
                            :disabled="selectionStart === null">
                            {{ $t('voiceClone.trim') }}
                        </el-button>
                        <el-button size="small" icon="el-icon-refresh-left" @click="handleReset">
                            {{ $t('voiceClone.reset') }}
                        </el-button>
                    </div>

                    <!-- 音频元素 -->
                    <audio ref="audioPlayer" @timeupdate="handleTimeUpdate" @ended="handleAudioEnded"
                        style="display: none;"></audio>
                </div>
            </div>
        </div>

        <span slot="footer" class="dialog-footer">
            <el-button @click="handleClose">{{ currentStep === 1 ? $t('voiceClone.cancel') : $t('voiceClone.prevStep')
                }}</el-button>
            <el-button type="primary" @click="handleNext" :loading="uploading">
                {{ currentStep === 1 ? $t('voiceClone.nextStep') : $t('voiceClone.upload') }}
            </el-button>
        </span>
    </el-dialog>
</template>

<script>
import Api from "@/apis/api";

export default {
    name: 'VoiceCloneDialog',
    props: {
        visible: {
            type: Boolean,
            default: false
        },
        voiceCloneData: {
            type: Object,
            default: () => ({})
        }
    },
    data() {
        return {
            currentStep: 1,
            uploadAction: '',
            audioFile: null,
            originalAudioFile: null,
            audioBuffer: null,
            originalAudioBuffer: null,
            isPlaying: false,
            uploading: false,
            // 波形相关
            waveformData: [],
            // 选择相关
            isSelecting: false,
            selectionStart: null,
            selectionEnd: null,
            mouseStartX: 0,
            // 音频上下文
            audioContext: null,
            audioSource: null,
        };
    },
    computed: {
        selectedDuration() {
            if (this.selectionStart !== null && this.selectionEnd !== null && this.audioBuffer) {
                const duration = this.audioBuffer.duration;
                const start = Math.min(this.selectionStart, this.selectionEnd) * duration;
                const end = Math.max(this.selectionStart, this.selectionEnd) * duration;
                return end - start;
            }
            return this.audioBuffer ? this.audioBuffer.duration : 0;
        },
        selectionStyle() {
            if (this.selectionStart === null) return {};
            const canvas = this.$refs.waveformCanvas;
            if (!canvas) return {};

            const start = Math.min(this.selectionStart, this.selectionEnd || this.selectionStart);
            const end = Math.max(this.selectionStart, this.selectionEnd || this.selectionStart);

            return {
                left: `${start * 100}%`,
                width: `${(end - start) * 100}%`
            };
        }
    },
    methods: {
        handleClose() {
            if (this.currentStep === 2) {
                this.currentStep = 1;
            } else {
                this.resetDialog();
                this.$emit('update:visible', false);
            }
        },
        resetDialog() {
            this.currentStep = 1;
            this.audioFile = null;
            this.originalAudioFile = null;
            this.audioBuffer = null;
            this.originalAudioBuffer = null;
            this.isPlaying = false;
            this.uploading = false;
            this.waveformData = [];
            this.selectionStart = null;
            this.selectionEnd = null;
            if (this.audioSource) {
                this.audioSource.stop();
                this.audioSource = null;
            }
        },
        async handleFileChange(file) {
            if (!file || !file.raw) return;

            this.audioFile = file.raw;
            this.originalAudioFile = file.raw;

            // 先进入第二步,确保DOM已渲染
            this.currentStep = 2;

            // 等待DOM更新后再加载音频
            await this.$nextTick();
            await this.loadAudio(file.raw);
        },
        async loadAudio(file) {
            try {
                const arrayBuffer = await file.arrayBuffer();
                if (!this.audioContext) {
                    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }
                this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer.slice(0));
                this.originalAudioBuffer = await this.audioContext.decodeAudioData(await file.arrayBuffer());

                // 设置音频播放器
                if (this.$refs.audioPlayer) {
                    const audioUrl = URL.createObjectURL(file);
                    this.$refs.audioPlayer.src = audioUrl;
                    // 加载音频元数据
                    this.$refs.audioPlayer.load();
                }

                // 生成波形数据
                await this.generateWaveform();
            } catch (error) {
                console.error('加载音频失败:', error);
                this.$message.error(this.$t('voiceClone.loadAudioFailed'));
            }
        },
        async generateWaveform() {
            if (!this.audioBuffer) return;

            await this.$nextTick();
            const canvas = this.$refs.waveformCanvas;
            if (!canvas) {
                console.error('Canvas元素不存在');
                return;
            }

            // 设置canvas大小
            const containerWidth = canvas.parentElement.offsetWidth;
            const containerHeight = canvas.parentElement.offsetHeight;
            canvas.width = containerWidth || 800;
            canvas.height = containerHeight || 200;

            const canvasWidth = canvas.width;
            const channelData = this.audioBuffer.getChannelData(0);
            const step = Math.floor(channelData.length / canvasWidth);
            const waveformData = [];

            for (let i = 0; i < canvasWidth; i++) {
                let sum = 0;
                for (let j = 0; j < step; j++) {
                    sum += Math.abs(channelData[i * step + j] || 0);
                }
                waveformData.push(sum / step);
            }

            this.waveformData = waveformData;
            this.drawWaveform();
        },
        drawWaveform() {
            const canvas = this.$refs.waveformCanvas;
            if (!canvas) {
                console.error('绘制波形时Canvas不存在');
                return;
            }

            const ctx = canvas.getContext('2d');
            const width = canvas.width;
            const height = canvas.height;

            // 清空画布
            ctx.clearRect(0, 0, width, height);

            // 绘制背景
            ctx.fillStyle = '#e0f2ff';
            ctx.fillRect(0, 0, width, height);

            if (this.waveformData.length === 0) {
                console.error('波形数据为空');
                return;
            }

            // 找到最大值用于归一化
            const maxValue = Math.max(...this.waveformData);

            // 绘制波形
            ctx.fillStyle = '#4ade80';
            ctx.strokeStyle = '#4ade80';
            ctx.lineWidth = 1;

            const barWidth = width / this.waveformData.length;

            this.waveformData.forEach((value, index) => {
                // 归一化并放大，使用80%的高度
                const normalizedValue = maxValue > 0 ? value / maxValue : 0;
                const barHeight = Math.max(1, normalizedValue * height * 0.8);
                const x = index * barWidth;
                const y = (height - barHeight) / 2;

                ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
            });
        },
        handleWaveformMouseDown(e) {
            const canvas = this.$refs.waveformCanvas;
            const rect = canvas.getBoundingClientRect();
            this.mouseStartX = e.clientX - rect.left;
            this.selectionStart = this.mouseStartX / rect.width;
            this.selectionEnd = this.selectionStart;
            this.isSelecting = true;
        },
        handleWaveformMouseMove(e) {
            if (!this.isSelecting) return;

            const canvas = this.$refs.waveformCanvas;
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            this.selectionEnd = Math.max(0, Math.min(1, x / rect.width));
        },
        handleWaveformMouseUp() {
            this.isSelecting = false;
        },
        async handleTrim() {
            if (this.selectionStart === null || this.selectionEnd === null || !this.audioBuffer) return;

            const start = Math.min(this.selectionStart, this.selectionEnd);
            const end = Math.max(this.selectionStart, this.selectionEnd);

            // 创建新的音频buffer
            const duration = this.audioBuffer.duration;
            const startTime = start * duration;
            const endTime = end * duration;
            const startOffset = Math.floor(startTime * this.audioBuffer.sampleRate);
            const endOffset = Math.floor(endTime * this.audioBuffer.sampleRate);
            const newLength = endOffset - startOffset;

            const newBuffer = this.audioContext.createBuffer(
                this.audioBuffer.numberOfChannels,
                newLength,
                this.audioBuffer.sampleRate
            );

            for (let channel = 0; channel < this.audioBuffer.numberOfChannels; channel++) {
                const oldData = this.audioBuffer.getChannelData(channel);
                const newData = newBuffer.getChannelData(channel);
                for (let i = 0; i < newLength; i++) {
                    newData[i] = oldData[startOffset + i];
                }
            }

            this.audioBuffer = newBuffer;

            // 更新音频文件
            await this.bufferToFile(newBuffer);

            // 重置选择
            this.selectionStart = null;
            this.selectionEnd = null;

            // 重新生成波形
            this.generateWaveform();

            this.$message.success(this.$t('voiceClone.trimSuccess'));
        },
        async handleReset() {
            if (!this.originalAudioFile) return;

            this.audioFile = this.originalAudioFile;
            await this.loadAudio(this.originalAudioFile);
            this.selectionStart = null;
            this.selectionEnd = null;

            this.$message.success(this.$t('voiceClone.resetSuccess'));
        },
        togglePlay() {
            const audio = this.$refs.audioPlayer;
            if (this.isPlaying) {
                audio.pause();
                this.isPlaying = false;
            } else {
                audio.play();
                this.isPlaying = true;
            }
        },
        handleTimeUpdate() {
            // 可以在这里更新播放进度
        },
        handleAudioEnded() {
            this.isPlaying = false;
        },
        async bufferToFile(buffer) {
            // 将AudioBuffer转换为WAV文件
            const wav = this.audioBufferToWav(buffer);
            const blob = new Blob([wav], { type: 'audio/wav' });
            this.audioFile = new File([blob], 'audio.wav', { type: 'audio/wav' });

            // 更新播放器
            await this.$nextTick();
            if (this.$refs.audioPlayer) {
                const audioUrl = URL.createObjectURL(blob);
                this.$refs.audioPlayer.src = audioUrl;
            }
        },
        audioBufferToWav(buffer) {
            const length = buffer.length * buffer.numberOfChannels * 2 + 44;
            const arrayBuffer = new ArrayBuffer(length);
            const view = new DataView(arrayBuffer);
            const channels = [];
            let offset = 0;
            let pos = 0;

            // 写入WAV文件头
            const setUint16 = (data) => {
                view.setUint16(pos, data, true);
                pos += 2;
            };
            const setUint32 = (data) => {
                view.setUint32(pos, data, true);
                pos += 4;
            };

            // "RIFF" chunk descriptor
            setUint32(0x46464952); // "RIFF"
            setUint32(length - 8); // file length - 8
            setUint32(0x45564157); // "WAVE"

            // "fmt " sub-chunk
            setUint32(0x20746d66); // "fmt "
            setUint32(16); // SubChunk1Size = 16
            setUint16(1); // AudioFormat = 1 (PCM)
            setUint16(buffer.numberOfChannels);
            setUint32(buffer.sampleRate);
            setUint32(buffer.sampleRate * 2 * buffer.numberOfChannels); // byte rate
            setUint16(buffer.numberOfChannels * 2); // block align
            setUint16(16); // bits per sample

            // "data" sub-chunk
            setUint32(0x61746164); // "data"
            setUint32(length - pos - 4); // SubChunk2Size

            // 写入音频数据
            for (let i = 0; i < buffer.numberOfChannels; i++) {
                channels.push(buffer.getChannelData(i));
            }

            while (pos < length) {
                for (let i = 0; i < buffer.numberOfChannels; i++) {
                    let sample = Math.max(-1, Math.min(1, channels[i][offset]));
                    sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
                    view.setInt16(pos, sample, true);
                    pos += 2;
                }
                offset++;
            }

            return arrayBuffer;
        },
        async handleNext() {
            if (this.currentStep === 1) {
                // 验证是否已选择文件
                if (!this.audioFile) {
                    this.$message.warning(this.$t('voiceClone.pleaseSelectAudio'));
                    return;
                }
                this.currentStep = 2;
            } else {
                // 上传音频
                await this.uploadAudio();
            }
        },
        async uploadAudio() {
            if (!this.audioFile) {
                this.$message.warning(this.$t('voiceClone.pleaseSelectAudio'));
                return;
            }

            // 验证音频时长（8-60秒）
            if (this.audioBuffer) {
                const duration = this.audioBuffer.duration;
                if (duration < 8 || duration > 60) {
                    this.$message.warning(this.$t('voiceClone.durationError'));
                    return;
                }
            }

            this.uploading = true;

            try {
                const formData = new FormData();
                formData.append('voiceFile', this.audioFile);
                formData.append('id', this.voiceCloneData.id);

                await Api.voiceClone.uploadVoice(formData, (res) => {
                    this.uploading = false;
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success(this.$t('voiceClone.uploadSuccess'));
                        this.resetDialog();
                        this.$emit('update:visible', false);
                        this.$emit('success');
                    } else {
                        this.$message.error(res.msg || this.$t('voiceClone.uploadFailed'));
                    }
                });
            } catch (error) {
                this.uploading = false;
                console.error('上传音频失败:', error);
                this.$message.error(this.$t('voiceClone.uploadFailed'));
            }
        }
    },
    mounted() {
        // 设置canvas大小
        this.$nextTick(() => {
            const canvas = this.$refs.waveformCanvas;
            if (canvas) {
                canvas.width = canvas.offsetWidth;
                canvas.height = canvas.offsetHeight;
            }
        });
    },
    beforeDestroy() {
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
};
</script>

<style lang="scss" scoped>
.voice-clone-dialog {
    ::v-deep .el-dialog__body {
        padding: 20px 30px;
    }
}


.steps-header {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 0 50px;
}

.step-item {
    display: flex;
    align-items: center;
    position: relative;

    &.active {
        .step-number {
            background: #6b8cff;
            color: white;
        }

        .step-label {
            color: #333;
            font-weight: 600;
        }
    }

    &.completed {
        .step-number {
            background: #67c23a;
            color: white;
        }

        .step-line {
            background: #67c23a;
        }
    }
}

.step-number {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #e4e7ed;
    color: #909399;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 16px;
    z-index: 1;
}

.step-label {
    margin-left: 12px;
    color: #909399;
    font-size: 14px;
}

.step-line {
    width: 200px;
    height: 2px;
    background: #e4e7ed;
    margin-left: 12px;
}

.step-content {
    padding: 20px 0;
}

.upload-area {
    padding: 40px 0;
}

.audio-uploader {
    ::v-deep .el-upload {
        width: 100%;
    }

    ::v-deep .el-upload-dragger {
        width: 100%;
        height: 280px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;

        .el-icon-upload {
            font-size: 67px;
            color: #c0c4cc;
            margin: 0 0 16px;
            line-height: 50px;
        }
    }

    .el-upload__text {
        color: #606266;
        font-size: 14px;
        margin-bottom: 8px;
    }

    .el-upload__tip {
        font-size: 12px;
        color: #909399;
        margin-top: 7px;
    }
}

.audio-edit-area {
    padding: 0 20px;
}

.edit-tips {
    margin-bottom: 20px;
    padding: 12px;
    background: #f0f9ff;
    border-radius: 4px;
    border-left: 3px solid #1890ff;

    p {
        margin: 4px 0;
        font-size: 13px;
        color: #606266;

        &:first-child {
            font-weight: 500;
        }
    }
}

.waveform-container {
    position: relative;
    width: 100%;
    height: 200px;
    margin-bottom: 20px;
    border: 1px solid #e4e7ed;
    border-radius: 4px;
    overflow: hidden;
    cursor: crosshair;
}

.waveform-canvas {
    width: 100%;
    height: 100%;
}

.selection-overlay {
    position: absolute;
    top: 0;
    bottom: 0;
    background: rgba(107, 140, 255, 0.3);
    border: 1px solid #6b8cff;
    pointer-events: none;
}

.duration-display {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}

.audio-controls {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 20px;
}

.dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}
</style>
