// terrence@tenclass.com
// 2024-08-27
// 大模型语音合成双向流式 API
// (https://www.volcengine.com/docs/6561/1329505)

require('dotenv').config();
const { WebSocket } = require('ws');
const { v4: uuidv4 } = require('uuid');
const EventEmitter = require('events');

class TtsSession extends EventEmitter {
  constructor(client, speaker, sampleRate = 24000) {
    super();
    this.client = client;
    this.sessionId = uuidv4();
    this.params = this.initParams(speaker, sampleRate);
  }

  initParams(speaker, sampleRate) {
    return {
      speaker: speaker || 'zh_female_shuangkuaisisi_moon_bigtts',
      audio_params: {
        format: 'pcm',
        sample_rate: sampleRate
      }
    };
  }

  start() {
    this.sendRequest(100, { ...this.params });
  }

  write(text) {
    this.sendRequest(200, { ...this.params, text });
  }

  cancel() {
    this.sendRequest(101, {});
  }

  finish() {
    this.sendRequest(102, {});
  }

  sendRequest(event, reqParams) {
    const payload = {
      namespace: 'BidirectionalTTS',
      event,
      req_params: reqParams
    };
    this.client.sendFullClientRequest(event, payload, this.sessionId);
  }
}

class BytedanceTtsClient extends EventEmitter {
  constructor() {
    super();
    this.sessions = new Map();
    this.reqId = uuidv4();
    this.initWebSocket();
    console.log('reqId', this.reqId);
  }

  initWebSocket() {
    this.socket = new WebSocket('wss://openspeech.bytedance.com/api/v3/tts/bidirection', {
      headers: this.getHeaders()
    });

    this.socket.on('open', this.onOpen.bind(this));
    this.socket.on('message', this.onMessage.bind(this));
    this.socket.on('error', this.onError.bind(this));
    this.socket.on('close', this.onClose.bind(this));
    this.socket.on('upgrade', this.onUpgrade.bind(this));
  }

  close() {
    if (this.connectionReady) {
      this.finishConnection();
    } else {
      this.socket.close();
    }
  }

  onUpgrade(req) {
    console.log('TTS LogId', req.headers['x-tt-logid']);
  }

  getHeaders() {
    return {
      'X-Api-App-Key': process.env.BYTEDANCE_TTS_APP_ID,
      'X-Api-Access-Key': process.env.BYTEDANCE_TTS_APP_KEY,
      'X-Api-Resource-Id': 'volc.service_type.10029',
      'X-Api-Request-Id': this.reqId
    };
  }

  onOpen() {
    this.sendFullClientRequest(1, {});
  }

  onMessage(data) {
    const messageType = data.readUInt8(1);
    const handlers = {
      0xF0: this.parseErrorResponse,
      0x94: this.parseFullServerResponse,
      0xB4: this.parseAudioResponse
    };

    const handler = handlers[messageType];
    if (handler) {
      handler.call(this, data);
    } else {
      console.error('Unknown message type:', messageType, data.toString());
    }
  }

  onError(err) {
    this.emit('error', err);
  }

  onClose() {
    this.sessions.forEach(session => session.emit('cancelled'));
    this.sessions.clear();
    this.emit('close');
  }

  newSession(speaker, sampleRate) {
    const session = new TtsSession(this, speaker, sampleRate);
    this.sessions.set(session.sessionId, session);
    session.start();
    return session;
  }

  parseErrorResponse(data) {
    const errorCode = data.readUInt32BE(4);
    const errorMessageLength = data.readUInt32BE(8);
    const errorMessage = data.toString('utf8', 12, 12 + errorMessageLength);
    console.error(`Error code: ${errorCode}, message: ${errorMessage}`);
  }

  sendFullClientRequest(eventCode, payload, sessionId) {
    const header = Buffer.from('11141000', 'hex');
    const optional = Buffer.alloc(4);
    optional.writeUInt32BE(eventCode);
    const payloadBuffer = Buffer.from(JSON.stringify(payload));
    const payloadLengthBuffer = Buffer.alloc(4);
    payloadLengthBuffer.writeUInt32BE(payloadBuffer.length);

    let fullRequest;
    if (sessionId) {
      const sessionIdBuffer = Buffer.alloc(4 + sessionId.length);
      sessionIdBuffer.writeUInt32BE(sessionId.length);
      sessionIdBuffer.write(sessionId, 4);
      fullRequest = Buffer.concat([header, optional, sessionIdBuffer, payloadLengthBuffer, payloadBuffer]);
    } else {
      fullRequest = Buffer.concat([header, optional, payloadLengthBuffer, payloadBuffer]);
    }

    this.socket.send(fullRequest);
  }

  parseFullServerResponse(data) {
    const eventCode = data.readUInt32BE(4);
    if (eventCode <= 52) {
      this.handleConnectionEvents(eventCode);
    } else {
      this.handleSessionEvents(data, eventCode);
    }
  }

  handleConnectionEvents(eventCode) {
    switch (eventCode) {
      case 50:
        this.connectionReady = true;
        this.emit('ready');
        break;
      case 51:
        this.connectionReady = false;
        this.emit('error', 'Failed to connect to TTS server.');
        break;
      case 52:
        this.connectionReady = false;
        this.sessions.clear();
        this.socket.close();
        break;
    }
  }

  handleSessionEvents(data, eventCode) {
    let offset = 8;
    const sessionIdLength = data.readUInt32BE(offset);
    offset += 4;
    const sessionId = data.toString('utf8', offset, offset + sessionIdLength);
    offset += sessionIdLength;
    const payloadLength = data.readUInt32BE(offset);
    offset += 4;
    const payload = JSON.parse(data.toString('utf8', offset, offset + payloadLength));

    const session = this.sessions.get(sessionId);
    if (!session) {
      console.error('Session not found:', sessionId);
      return;
    }

    const eventHandlers = {
      150: () => session.emit('started'),
      151: () => {
        session.emit('cancelled');
        this.sessions.delete(sessionId);
      },
      152: () => {
        session.emit('finished');
        this.sessions.delete(sessionId);
      },
      153: () => session.emit('error', payload),
      350: () => session.emit('sentence_start', payload.text),
      351: () => session.emit('sentence_end', payload.text)
    };

    const handler = eventHandlers[eventCode];
    if (handler) {
      handler();
    } else {
      console.error('Unknown event code:', eventCode);
    }
  }

  parseAudioResponse(data) {
    let offset = 8;
    const sessionIdLength = data.readUInt32BE(offset);
    offset += 4;
    const sessionId = data.toString('utf8', offset, offset + sessionIdLength);
    offset += sessionIdLength;
    const audioLength = data.readUInt32BE(offset);
    offset += 4;
    const audio = data.slice(offset, offset + audioLength);
    
    const session = this.sessions.get(sessionId);
    if (session) {
      session.emit('audio', audio);
    }
  }

  finishConnection() {
    this.sendFullClientRequest(2, {});
  }

  static test() {
    const client = new BytedanceTtsClient();
    client.on('ready', () => {
      console.log('TTS服务器就绪。');

      const session = client.newSession();
      session.on('started', async () => {
        console.log(new Date(), 'TTS会话已开始。');

        session.write('你好！');
        console.log(new Date(), '已发送“你好”');
        await new Promise(resolve => setTimeout(resolve, 500));
        session.write('世界。');
        console.log(new Date(), '已发送“世界”');
        await new Promise(resolve => setTimeout(resolve, 500));
        session.finish();
        console.log(new Date(), '已发送 finish');
      });

      let t = Buffer.alloc(0);
      session.on('audio', (audio) => {
        console.log('收到', audio.length, '字节');
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

module.exports = { BytedanceTtsClient };

if (require.main === module) {
  BytedanceTtsClient.test();
}