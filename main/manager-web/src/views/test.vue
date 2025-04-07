<template>
  <div class="container">
    <h1 class="title">XiaoZhi ESP32 Server 测试助手</h1>
    <div class="chat-container" ref="chatContainer">
      <div v-for="(message, index) in messages" :key="index"
        :class="['message', message.role === 'user' ? 'user' : 'assistant']">
        <span>{{ message.content }}</span>
      </div>
    </div>
    <div class="controls">
      <button @click="toggleRecording" :disabled="wsStatus !== 'connected'" :class="{ recording: isRecording }">
        {{ isRecording ? '停止录音' : '开始录音' }}
      </button>
      <p>WebSocket: {{ wsStatus }}</p>
    </div>
  </div>
</template>

<script>
import { OpusDecoder } from 'opus-decoder';
import Recorder from 'opus-recorder';

export default {
  name: 'TestPage',
  data() {
    return {
      messages: [],
      wsStatus: 'disconnected',
      isRecording: false,
      ws: null,
      recorder: null,
      stream: null,
      audioContext: null,
      sourceNode: null,
      audioDecoder: null,
      audioBufferQueue: [], // 当前句子的音频缓冲区
      playbackQueue: [], // 播放队列，存储待播放的句子
      isPlaying: false,
    }
  },
  methods: {
    connectWebSocket() {
      this.ws = new WebSocket('ws://192.168.3.97:8000');//修改服务端地址
      this.ws.binaryType = 'arraybuffer';
      this.ws.onopen = () => {
        this.wsStatus = 'connected';
        console.log('WebSocket 连接成功');
        this.ws.send(JSON.stringify({ type: 'auth', 'device-id': 'test-device' }));
        this.audioDecoder = new OpusDecoder({ sampleRate: 16000, channels: 1 });
      };
      this.ws.onmessage = async (event) => {
        if (typeof event.data === 'string') {
          const msg = JSON.parse(event.data);
          console.log('收到文本消息:', msg);

          if (msg.type === 'stt') {
            this.messages.push({ role: 'user', content: msg.text });
            this.scrollToBottom();
          } else if (msg.type === 'llm') {
            this.messages.push({ role: 'assistant', content: msg.text });
            this.scrollToBottom();
          } else if (msg.type === 'tts') {
            if (msg.state === 'sentence_start') {
              this.audioBufferQueue = [];
              const lastMessage = this.messages[this.messages.length - 1];
              if (!lastMessage || lastMessage.content !== msg.text) {
                this.messages.push({ role: 'assistant', content: msg.text });
                this.scrollToBottom();
              }
            } else if (msg.state === 'sentence_end') {
              if (this.audioBufferQueue.length > 0) {
                this.playbackQueue.push([...this.audioBufferQueue]);
                this.audioBufferQueue = [];
                this.playNextInQueue();
              }
            } else if (msg.state === 'stop') {
              console.log('TTS 任务结束');
              if (this.audioBufferQueue.length > 0) {
                this.playbackQueue.push([...this.audioBufferQueue]);
                this.audioBufferQueue = [];
                this.playNextInQueue();
              }
            }
          } else if (msg.type === 'hello') {
            console.log('收到服务器初始化消息:', msg);
          }
        } else if (event.data instanceof ArrayBuffer) {
          console.log('收到音频帧，大小:', event.data.byteLength, '字节');
          const opusFrame = new Uint8Array(event.data);
          const frameHead = Array.from(opusFrame.slice(0, 8))
            .map(b => b.toString(16).padStart(2, '0'))
            .join(' ');
          console.log('音频帧前8字节:', frameHead);

          try {
            const decoded = this.audioDecoder.decodeFrame(opusFrame);
            console.log('解码结果:', decoded);
            if (decoded && decoded.channelData && decoded.channelData[0]) {
              const pcmData = decoded.channelData[0];
              if (pcmData.length > 0) {
                this.audioBufferQueue.push(pcmData);
                console.log('解码音频帧，PCM 数据长度:', pcmData.length);
                if (this.audioBufferQueue.length >= 5 && this.playbackQueue.length === 0 && !this.isPlaying) {
                  this.playbackQueue.push([...this.audioBufferQueue]);
                  this.audioBufferQueue = [];
                  this.playNextInQueue();
                }
              } else {
                console.warn('解码成功，但 PCM 数据长度为 0');
              }
            } else {
              console.warn('解码结果无效:', decoded);
            }
          } catch (e) {
            console.error('Opus 解码错误:', e);
          }
        }
      };
      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        this.wsStatus = 'error';
      };
      this.ws.onclose = () => {
        this.wsStatus = 'disconnected';
        console.log('WebSocket 断开');
        setTimeout(this.connectWebSocket, 1000);
      };
    },
    scrollToBottom() {
      this.$nextTick(() => {
        if (this.$refs.chatContainer) {
          this.$refs.chatContainer.scrollTop = this.$refs.chatContainer.scrollHeight;
        }
      });
    },
    async playNextInQueue() {
      if (this.isPlaying || this.playbackQueue.length === 0) {
        return;
      }
      this.isPlaying = true;

      if (!this.audioContext || this.audioContext.state === 'closed') {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      }

      const pcmBuffers = this.playbackQueue.shift();
      const totalLength = pcmBuffers.reduce((sum, pcm) => sum + pcm.length, 0);
      if (totalLength === 0) {
        console.error('音频缓冲区总长度为 0，无法播放');
        this.isPlaying = false;
        this.playNextInQueue();
        return;
      }

      const mergedPcm = new Float32Array(totalLength);
      let offset = 0;
      for (const pcm of pcmBuffers) {
        mergedPcm.set(pcm, offset);
        offset += pcm.length;
      }

      const audioBuffer = this.audioContext.createBuffer(1, totalLength, 16000);
      audioBuffer.getChannelData(0).set(mergedPcm);

      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      source.onended = () => {
        this.isPlaying = false;
        console.log('音频播放结束');
        this.playNextInQueue();
      };
      source.start();
      console.log('开始播放音频，总长度:', totalLength);
    },
    stripOggContainer(data) {
      let arrayBuffer;
      if (data instanceof ArrayBuffer) {
        arrayBuffer = data;
      } else if (data.buffer instanceof ArrayBuffer) {
        arrayBuffer = data.buffer;
      } else {
        console.error('输入数据类型不支持:', data);
        return [data];
      }

      const dataView = new DataView(arrayBuffer);
      const frames = [];
      let offset = 0;

      while (offset < arrayBuffer.byteLength) {
        if (dataView.getUint32(offset) === 0x4F676753) { // 'OggS'
          const segmentTableLength = dataView.getUint8(offset + 26);
          const segmentTableOffset = offset + 27;
          let segmentOffset = segmentTableOffset + segmentTableLength;

          for (let i = 0; i < segmentTableLength; i++) {
            const segmentLength = dataView.getUint8(segmentTableOffset + i);
            const segmentData = arrayBuffer.slice(segmentOffset, segmentOffset + segmentLength);
            segmentOffset += segmentLength;

            const header = new TextDecoder().decode(segmentData.slice(0, 8));
            if (header === 'OpusHead' || header === 'OpusTags') {
              console.log(`跳过 ${header}，大小: ${segmentLength} 字节`);
            } else if (segmentLength >= 50 && segmentLength <= 300) {
              frames.push(segmentData);
            }
          }
          offset = segmentOffset;
        } else {
          const remainingLength = arrayBuffer.byteLength - offset;
          if (remainingLength >= 50 && remainingLength <= 300) {
            frames.push(arrayBuffer.slice(offset));
          }
          break;
        }
      }

      if (frames.length === 0) {
        console.warn('未找到有效裸 Opus 帧，返回原始数据');
        return [arrayBuffer];
      }
      console.log('剥离后找到', frames.length, '个裸 Opus 帧');
      return frames;
    },
    async initRecorder() {
      console.log('开始初始化录音');
      try {
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
        }
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('获取麦克风权限成功，stream:', this.stream);

        if (!this.audioContext || this.audioContext.state === 'closed') {
          this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        }
        this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);

        this.recorder = new Recorder({
          encoderPath: '/encoderWorker.min.js',
          sampleRate: 16000,
          numberOfChannels: 1,
          frameSize: 960,
          encoderApplication: 2048,
          encoderFrameSize: 60,
          encoderBitRate: 24000,
          monitorGain: 0,
          sourceNode: this.sourceNode,
          ogg: false,
          streamPages: false,
          maxFramesPerPage: 1,
        });

        this.recorder.ondataavailable = (data) => {
          console.log('录音数据可用:', data.byteLength, '类型:', data.constructor.name);
          const frames = this.stripOggContainer(data);
          frames.forEach((frame, index) => {
            const frameHead = Array.from(new Uint8Array(frame.slice(0, 8)))
              .map(b => b.toString(16).padStart(2, '0'))
              .join(' ');
            console.log(`帧 ${index} 大小: ${frame.byteLength} 字节，前8字节: ${frameHead}`);

            if (frame.byteLength < 50 || frame.byteLength > 300) {
              console.warn(`帧 ${index} 大小异常: ${frame.byteLength} 字节，预期 50-300 字节`);
              return;
            }

            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
              this.ws.send(frame);
              console.log('发送裸 Opus 帧:', frame.byteLength);
            } else {
              console.warn('WebSocket 未连接，跳过发送');
            }
          });
        };

        this.recorder.onstart = () => {
          console.log('录音已启动');
        };

        this.recorder.onstop = () => {
          console.log('录音停止');
          this.stream.getTracks().forEach(track => track.stop());
          this.stream = null;
          this.sourceNode = null;
          this.scrollToBottom();
        };

        console.log('Recorder 初始化成功');
      } catch (err) {
        console.error('初始化录音失败:', err);
        alert('无法访问麦克风或录音初始化失败，请检查权限');
      }
    },
    async toggleRecording() {
      console.log('点击 toggleRecording，当前状态:', this.isRecording, 'WebSocket 状态:', this.wsStatus);
      if (!this.recorder) {
        await this.initRecorder();
        if (!this.recorder) {
          console.error('recorder 初始化失败');
          return;
        }
      }
      if (this.isRecording) {
        console.log('停止录音');
        this.recorder.stop();
        this.isRecording = false;
      } else {
        try {
          console.log('开始录音');
          await this.initRecorder();
          await this.recorder.start();
          console.log('录音开始后，状态:', this.recorder.state);
          this.isRecording = true;
        } catch (err) {
          console.error('录音启动失败:', err);
        }
      }
    },
  },
  mounted() {
    console.log('组件挂载，初始化 WebSocket');
    this.connectWebSocket();
  },
  destroyed() {
    if (this.ws) this.ws.close();
    if (this.stream) this.stream.getTracks().forEach(track => track.stop());
    if (this.recorder) this.recorder.stop();
    if (this.audioContext) this.audioContext.close();
    if (this.audioDecoder) this.audioDecoder.destroy();
  }
};
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

.title {
  text-align: center;
  font-size: 24px;
  margin-bottom: 20px;
}

.chat-container {
  height: 60vh;
  overflow-y: auto;
  border: 1px solid #ccc;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 5px;
}

.message {
  margin: 10px 0;
  padding: 8px 12px;
  border-radius: 5px;
  max-width: 70%;
}

.user {
  background: #007bff;
  color: white;
  margin-left: auto;
}

.assistant {
  background: #e9ecef;
  color: black;
}

.controls {
  text-align: center;
  margin-top: 20px;
}

button {
  padding: 10px 20px;
  font-size: 16px;
  cursor: pointer;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

button.recording {
  background: #dc3545;
}
</style>