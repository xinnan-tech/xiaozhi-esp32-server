const WebSocket = require('ws');
const config = require('./config');
const { OpusEncoder } = require('@discordjs/opus');
const { ttsList } = require('./tts-list');
const { BytedanceTtsClient } = require('./bytedance_tts');
const { DashscopeTtsClient } = require('./dashscope_tts');

const ttsClients = {
  volcengine: BytedanceTtsClient,
  dashscope: DashscopeTtsClient,
};

const DEFAULT_SAMPLE_RATE = 24000;
const DEFAULT_FRAME_DURATION = 60;

class RateControlSender {
  constructor(ws) {
    this.ws = ws;
    this.sampleRate = DEFAULT_SAMPLE_RATE;
    this.frameDuration = DEFAULT_FRAME_DURATION;
    this.queue = [];
  }

  setSampleRate(sampleRate) {
    this.sampleRate = sampleRate;
  }

  setFrameDuration(frameDuration) {
    this.frameDuration = frameDuration;
  }

  reset() {
    if (this.rateControlTimeout) {
      clearTimeout(this.rateControlTimeout);
      this.rateControlTimeout = null;
    }
    if (this.queue.length > 0) {
      this.queue = [];
      this.sendStop();
    }

    this.encoder = new OpusEncoder(this.sampleRate, 1);
    this.encoder.applyEncoderCTL(4000, 2048); // VOIP
    this.encodeFrameSize = this.sampleRate / 1000 * this.frameDuration;
    this.audioBuffer = Buffer.alloc(0);
    this.audioPosition = 0;
    this.startTimestamp = Date.now();
  }

  encodeAudio() {
    const pieceLength = this.encodeFrameSize * 2;
    while (this.audioBuffer.length - this.audioPosition >= pieceLength) {
      const frame = this.audioBuffer.subarray(this.audioPosition, this.audioPosition + pieceLength);
      this.audioPosition += pieceLength;
      const opus = this.encoder.encode(frame);
      this.ws.send(opus, { binary: true });
    }
  }

  checkQueue() {
    if (this.ws.readyState !== WebSocket.OPEN) {
      return;
    }
    while (this.queue.length > 0) {
      // check if the first item is JSON object or Buffer
      if (this.queue[0] instanceof Buffer) {
        // check if it's time to send audio
        if (this.rateControlTimeout) {
          break;
        }
        const elapsedMs = Date.now() - this.startTimestamp;
        const outputMs = this.audioPosition / 2 * 1000 / this.sampleRate;
        if (elapsedMs < outputMs) {
          if (false) {
            console.log('[TTS] rate control, waiting', outputMs - elapsedMs, 'ms');
          }
          this.rateControlTimeout = setTimeout(() => {
            this.rateControlTimeout = null;
            this.checkQueue();
          }, outputMs - elapsedMs);
          break;
        }
        const pcm = this.queue.shift();
        this.audioBuffer = Buffer.concat([this.audioBuffer, pcm]);
        this.encodeAudio();
      } else {
        this.ws.send(JSON.stringify(this.queue.shift()));
      }
    }
  }

  sendAudio(audio) {
    this.queue.push(audio);
    this.checkQueue();
  }

  sendSentenceStart(text) {
    this.queue.push({ type: 'tts', state: 'sentence_start', text });
    this.checkQueue();
  }

  sendSentenceEnd(text) {
    this.queue.push({ type: 'tts', state: 'sentence_end', text });
    this.checkQueue();
  }

  sendStart(sampleRate) {
    this.queue.push({ type: 'tts', state: 'start', sample_rate: sampleRate });
    this.checkQueue();
  }

  sendStop() {
    this.queue.push({ type: 'tts', state: 'stop' });
    this.checkQueue();
  }

  close() {
    this.ws.close();
  }
}

class TtsSessionHandler {
  constructor(sender) {
    this.sender = sender;
    this.queueEvents = [];
    this.voice = null;
  }

  reset(force=false) {
    this.sender.reset();
    if (this.session) {
      if (!this.finished) {
        if (this.session.cancel) {
          this.session.cancel();
        } else {
          this.session.finish(force);
        }
      }
      this.session = null;
    }
    this.ttsErrorCount = 0;
    this.finished = false;
    this.replyText = '';
  }

  async setupTtsSession() {
    const session = this.client.newSession(this.voice, this.sender.sampleRate);
    session.on('sentence_start', (text) => {
      console.log('[TTS]', text);
      this.sender.sendSentenceStart(text);
    });
    session.on('sentence_end', (text) => {
      this.sender.sendSentenceEnd(text);
    });
    session.on('audio', (pcm) => {
      this.sender.sendAudio(pcm);
    });
    session.on('finished', () => {
      this.sender.sendStop();
      console.log('[TTS] finished voice_id', this.voice, 'sample_rate', this.sender.sampleRate);
      this.session = null;
    });

    if (this.replyText.length > 0) {
      console.log('[TTS] setup with text:', this.replyText);
      session.write(this.replyText);
      if (this.finished) {
        session.finish();
        return;
      }
    }
    this.session = session;
  }

  handleMessage(message) {
    const data = JSON.parse(message);
    if (data.type === 'start') {
      this.reset();
      this.sender.sendStart();
      if (this.client && this.client.connectionReady) {
        this.setupTtsSession();
      } else {
        this.queueEvents.push({
          resolve: () => this.setupTtsSession(),
        });
      }
    } else if (data.type === 'text') {
      this.replyText += data.text;
      if (this.session) {
        this.session.write(data.text);
      }
    } else if (data.type === 'finish') {
      this.finished = true;
      if (this.session) {
        this.session.finish();
      }
    } else if (data.type === 'config') {
      const ttsItem = ttsList.find(item => item.voice_id === data.voice);
      if (!ttsItem) {
        console.error(`无效的语音: ${data.voice}`);
        this.sender.close();
        return;
      }

      this.ttsItem = ttsItem;
      this.voice = data.voice;
      this.sender.setSampleRate(data.sampleRate || DEFAULT_SAMPLE_RATE);
      this.sender.setFrameDuration(data.frameDuration || DEFAULT_FRAME_DURATION);
      this.startClient();
    } else if (data.type === 'abort') {
      if (this.session) {
        this.reset(true);
        if (this.client) {
          this.client.close();
        }
        console.log('[TTS] aborted, starting new client');
        this.startClient();
      } else {
        this.reset(true);
      }
    }
  }

  startClient() {
    this.client = new ttsClients[this.ttsItem.voice_source]();
    this.client.on('ready', () => {
      while (this.queueEvents.length > 0) {
        const event = this.queueEvents.shift();
        event.resolve();
      }
    });
    this.client.on('error', (error) => {
      console.error('[TTS] client error', error);
    });
    this.client.on('close', () => {
      console.log('[TTS] client closed');
    });
    this.client.on('error', () => {
      this.ttsErrorCount++;
      if (this.ttsErrorCount > 3) {
        this.sender.close();
        return;
      }
      // 如果 TTS session 出错，重新创建 TTS 会话，并重新发送文本
      if (this.client && this.client.connectionReady && this.session) {
        console.log('[TTS] client error, retrying');
        this.queueEvents.push({
          resolve: () => this.setupTtsSession(),
        });
        this.startClient();
      }
    });
  }

  handleClose() {
    this.reset();
    if (this.client) {
      this.client.close();
    }
  }
}

const wss = new WebSocket.Server({ port: config.ttsFrontendPort , host: '0.0.0.0' });

wss.on('connection', (ws) => {
  const sender = new RateControlSender(ws);
  const handler = new TtsSessionHandler(sender);

  ws.on('message', (message) => handler.handleMessage(message));
  ws.on('close', () => handler.handleClose());
});

wss.on('listening', () => {
  console.log(`TTS 前端服务已启动，监听端口 ${config.ttsFrontendPort}`);
});
