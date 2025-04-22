// terrence@tenclass.com
// 2024-10-03
// 大模型语音合成双向流式 API （灵积 CosyVoice）

require('dotenv').config();
const { WebSocket } = require('ws');
const { v4: uuidv4 } = require('uuid');
const EventEmitter = require('events');

class TtsSession extends EventEmitter {
  constructor(client, speaker, sampleRate = 22050) {
    super();
    this.client = client;
    this.sessionId = uuidv4();
    this.model = 'cosyvoice-v1';
    this.params = this.initParams(speaker, sampleRate);
    this.texts = [];
  }

  initParams(speaker, sampleRate) {
    return {
      parameters: {
        voice: speaker || 'longjielidou',
        volume: 90,
        text_type: 'PlainText',
        format: 'pcm',
        rate: 1.1,
        pitch: 1.0,
        sample_rate: sampleRate
      }
    };
  }

  start() {
    this.sendRequest("run-task", {
      model: this.model,
      task_group: 'audio',
      task: 'tts',
      function: 'SpeechSynthesizer',
      input: {
        text: ''
      },
      ...this.params
    });
  }

  write(text) {
    this.texts.push(text);
    this.sendRequest("continue-task", {
      model: this.model,
      task_group: 'audio',
      task: 'tts',
      function: 'SpeechSynthesizer',
      input: { text } });
  }

  finish() {
    this.emit('sentence_start', this.texts.join(''));
    this.sendRequest("finish-task", {
      input: { text: '' }
    });
  }

  sendRequest(action, payload) {
    const data = {
      header: {
        action,
        task_id: this.sessionId,
        streaming: 'duplex'
      },
      payload
    };
    this.client.sendRequest(data);
  }
}

class DashscopeTtsClient extends EventEmitter {
  constructor() {
    super();
    this.reqId = uuidv4();
    this.sessions = new Map();
    this.initWebSocket();
    this.cachedAudioPackets = [];
  }

  initWebSocket() {
    this.socket = new WebSocket('wss://dashscope.aliyuncs.com/api-ws/v1/inference', {
      headers: this.getHeaders()
    });

    this.socket.on('open', this.onOpen.bind(this));
    this.socket.on('message', this.onMessage.bind(this));
    this.socket.on('error', this.onError.bind(this));
    this.socket.on('close', this.onClose.bind(this));
  }

  close() {
    this.socket.close();
  }

  getHeaders() {
    return {
      'user-agent': 'xiaozhi/1.0; nodejs/18.16.0; platform/Linux',
      'Authorization': process.env.DASHSCOPE_TTS_APP_KEY
    };
  }

  onOpen() {
    this.connectionReady = true;
    this.emit('ready');
    this.pingInterval = setInterval(() => {
      this.socket.ping();
    }, 10000);
  }

  onMessage(data, isBinary) {
    if (isBinary) {
      this.parseAudioResponse(data);
    } else {
      this.parseJsonResponse(data);
    }
  }

  onError(err) {
    this.emit('error', err);
  }

  onClose() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    this.connectionReady = false;
    this.sessions.forEach(session => session.emit('cancelled'));
    this.sessions.clear();
    this.emit('close');
  }

  newSession(speaker, sampleRate) {
    const session = new TtsSession(this, speaker, 24000);
    this.sessions.set(session.sessionId, session);
    session.start();
    return session;
  }

  sendRequest(data) {
    this.socket.send(JSON.stringify(data));
  }

  parseAudioResponse(data) {
    this.cachedAudioPackets.push(data);
  }

  parseJsonResponse(data) {
    const { header } = JSON.parse(data);
    const { task_id, event } = header;
    const session = this.sessions.get(task_id);
    if (!session) {
      console.error('Session not found:', task_id);
      return;
    }

    const duration = 240;
    const frameSize = session.params.parameters.sample_rate / 1000 * duration;

    if (event === 'result-generated') {
      if (!session.first) {
        if (this.cachedAudioPackets.length >= 1) {
          session.first = true;
        }
        return;
      }
      while (this.cachedAudioPackets.length > 0) {
        session.emit('audio', this.cachedAudioPackets.shift());
      }
    } else if (event === 'task-started') {
      session.emit('started');
    } else if (event === 'task-finished') {
      // add 240ms blank audio to the end of the stream
      const blankAudio = Buffer.alloc(frameSize * 2, 0);
      session.emit('audio', blankAudio);
      session.emit('finished');
      this.sessions.delete(task_id);
    }
  }

  finishConnection() {
    this.socket.close();
  }

  static test() {
    const client = new TtsClient();
    client.on('ready', () => {
      console.log('TTS服务器就绪。');

      const session = client.newSession();
      session.on('started', async () => {
        console.log(new Date(), 'TTS会话已开始。');

        session.write('你好，');
        session.write('我是小智');
        session.write('今天的天气真的不错啊');
        session.finish();
        console.log(new Date(), '已发送 finish');
      });

      let t = Buffer.alloc(0);
      session.on('audio', (audio) => {
        console.log(new Date(), '收到', audio.length, '字节');
        t = Buffer.concat([t, audio]);
      });

      session.on('finished', () => {
        console.log(new Date(), 'TTS会话已结束。');
        client.finishConnection();

        const fs = require('fs');
        fs.writeFileSync('tts.pcm', t);
        console.log('音频数据已写入 tts.pcm，大小:', t.length);
        console.log('要播放音频，请运行: ffplay -f s16le -ar 24000 -ac 1 tts.pcm');
      });

      session.on('sentence_start', (text) => {
        console.log('句子开始', text);
      });

      session.on('sentence_end', (text) => {
        console.log('句子结束', text);
      });

      session.on('error', (err) => {
        console.error('TTS会话错误:', err);
      });

      session.on('cancelled', () => {
        console.log('TTS会话已取消。');
      });

      session.on('finished', () => {
        console.log('TTS会话已结束。');
        client.finishConnection();
      });
    });

    client.on('error', (err) => console.error(new Date(), 'TTS客户端错误:', err));
    client.on('close', () => console.log('TTS客户端已关闭'));
  }
}

module.exports = { DashscopeTtsClient };

if (require.main === module) {
  DashscopeTtsClient.test();
}