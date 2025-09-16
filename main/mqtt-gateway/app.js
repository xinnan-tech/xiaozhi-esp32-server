// Description: MQTT+UDP to LiveKit bridge
// Author: terrence@tenclass.com
// Date: 2025-03-12
// Modified by: Gemini

require("dotenv").config();
const JSON5 = require("json5");

const net = require("net");
const debugModule = require("debug");
const debug = debugModule("mqtt-server");
const crypto = require("crypto");
const dgram = require("dgram");
const Emitter = require("events");
const { AccessToken } = require("livekit-server-sdk");
const {
  Room,
  RoomEvent,
  AudioSource,
  AudioFrame,
  AudioStream,
  LocalAudioTrack,
  TrackPublishOptions,
  TrackSource,
  TrackKind,
  AudioResampler,
  AudioResamplerQuality,
} = require("@livekit/rtc-node");
// Import Opus Encoder and Decoder from audify-plus
const { OpusEncoder, OpusDecoder, OpusApplication } = require("@voicehype/audify-plus");

// Initialize Opus encoder and decoder for 16kHz mono (same as before)
let opusEncoder = null;
let opusDecoder = null;
// Define constants for audio parameters
const SAMPLE_RATE = 16000;     // Hz
const CHANNELS = 1;            // Mono
const FRAME_DURATION_MS = 20;  // 20ms frames (standard for Opus)
const FRAME_SIZE_SAMPLES = (SAMPLE_RATE * FRAME_DURATION_MS) / 1000; // 16000 * 20 / 1000 = 320
const FRAME_SIZE_BYTES = FRAME_SIZE_SAMPLES * 2; // 320 samples * 2 bytes/sample = 640 bytes PCM

try {
  // For 24kHz, mono audio (resampled from 48kHz LiveKit audio)
  opusEncoder = new OpusEncoder(24000, 1, OpusApplication.OPUS_APPLICATION_AUDIO);
  opusDecoder = new OpusDecoder(16000, 1);

  console.log(
    "✅ [OPUS] audify-plus encoder/decoder initialized successfully - encoder: 24kHz, decoder: 16kHz mono"
  );
} catch (err) {
  console.error(
    "❌ [OPUS] Failed to initialize audify-plus encoder/decoder:",
    err.message
  );
  // Fallback: Disable Opus if init fails (will fall back to PCM)
}

const mqtt = require("mqtt");
const { MQTTProtocol } = require("./mqtt-protocol");
const { ConfigManager } = require("./utils/config-manager");
const { validateMqttCredentials } = require("./utils/mqtt_config_v2");

function setDebugEnabled(enabled) {
  if (enabled) {
    debugModule.enable("mqtt-server");
  } else {
    debugModule.disable();
  }
}

const configManager = new ConfigManager("mqtt.json");
configManager.on("configChanged", (config) => {
  setDebugEnabled(false);
});
setDebugEnabled(configManager.get("debug"));

class LiveKitBridge extends Emitter {
  constructor(connection, protocolVersion, macAddress, uuid, userData) {
    super();
    this.connection = connection;
    this.macAddress = macAddress;
    this.uuid = uuid;
    this.userData = userData;
    this.room = null;
    this.audioSource = new AudioSource(16000, 1);
    this.protocolVersion = protocolVersion;

    // Initialize audio resampler for 48kHz -> 16kHz conversion
    this.audioResampler = new AudioResampler(48000, 16000, 1); // 48kHz -> 16kHz, mono

    // Frame buffer for accumulating resampled audio into proper frame sizes
    this.frameBuffer = Buffer.alloc(0);
    this.targetFrameSize = 320; // 320 samples = 20ms at 16kHz
    this.targetFrameBytes = this.targetFrameSize * 2; // 640 bytes for 16-bit PCM

    // Initialize Opus decoder for incoming audio (device -> LiveKit)
    // this.opusDecoder = null;
    // Initialize Opus encoder for outgoing audio (LiveKit -> device)
    // this.opusEncoder = null;

    if (OpusEncoder) {
      try {
        // this.opusDecoder = new OpusEncoder(16000, 1); // 16kHz, mono
        console.log(`✅ [OPUS] Decoder initialized for ${this.macAddress}`);

        // this.opusEncoder = new OpusEncoder(16000, 1); // 16kHz, mono
        console.log(`✅ [OPUS] Encoder initialized for ${this.macAddress}`);
      } catch (err) {
        console.error(
          `❌ [OPUS] Failed to initialize encoder/decoder: ${err.message}`
        );
      }
    }

    this.initializeLiveKit();
  }

  initializeLiveKit() {
    const livekitConfig = configManager.get("livekit");
    if (!livekitConfig) {
      throw new Error("LiveKit config not found");
    }
    this.livekitConfig = livekitConfig;
  }

  // Process buffered audio frames and send PCM directly
  processBufferedFrames(timestamp, frameCount, participantIdentity) {
    while (this.frameBuffer.length >= this.targetFrameBytes) {
      // Extract one complete frame
      const frameData = this.frameBuffer.slice(0, this.targetFrameBytes);
      this.frameBuffer = this.frameBuffer.slice(this.targetFrameBytes);

      // Process this complete frame - send PCM directly without Opus encoding
      if (frameData.length > 0) {
        const samples = new Int16Array(frameData.buffer, frameData.byteOffset, frameData.length / 2);
        const isSilent = samples.every(sample => sample === 0);
        const maxAmplitude = Math.max(...samples.map(s => Math.abs(s)));
        const isNearlySilent = maxAmplitude < 10;

        if (isSilent || isNearlySilent) {
          // console.log(`🔇 [PCM] Silent frame detected, skipping`);
          continue;
        }

        if (frameCount <= 3 || frameCount % 100 === 0) {
          // console.log(`✅ [BUFFERED] Frame ${frameCount}: 16kHz PCM ${frameData.length}B sent directly`);
        }

        // Send PCM directly without Opus encoding
        this.connection.sendUdpMessage(frameData, timestamp);

        // Commented out Opus encoding for testing
        /*
        if (opusEncoder) {
          try {
            const alignedBuffer = Buffer.allocUnsafe(frameData.length);
            frameData.copy(alignedBuffer);
            const opusBuffer = opusEncoder.encode(alignedBuffer, this.targetFrameSize);
            this.connection.sendUdpMessage(opusBuffer, timestamp);
          } catch (err) {
            console.error(`❌ [BUFFERED] Encode error: ${err.message}`);
          }
        }
        */
      }
    }
  }

  async connect(audio_params, features) {
    const { url, api_key, api_secret } = this.livekitConfig;
    const roomName = this.uuid || this.macAddress;
    const participantName = this.macAddress;

    const at = new AccessToken(api_key, api_secret, {
      identity: participantName,
    });
    at.addGrant({
      room: roomName,
      roomJoin: true,
      roomCreate: true,
      canPublish: true,
      canSubscribe: true,
    });
    const token = await at.toJwt(); // Fixed: Make this async

    this.room = new Room();

    // Add connection state monitoring
    this.room.on("connectionStateChanged", (state) => {
      console.log(`[LiveKitBridge] Connection state changed: ${state}`);
    });

    this.room.on("connected", () => {
      console.log("[LiveKitBridge] Room connected event fired");
    });

    this.room.on("disconnected", (reason) => {
      console.log(`[LiveKitBridge] Room disconnected: ${reason}`);
    });

    this.room.on(
      RoomEvent.DataReceived,
      (payload, participant, kind, topic) => {
        try {
          const str = Buffer.from(payload).toString("utf-8");
          let data;
          try {
            data = JSON5.parse(str);
            // console.log("Data:", data);
          } catch (err) {
            console.error("Invalid JSON5:", err.message);
          }
          switch (data.type) {
            case "agent_state_changed":
              // console.log(`Agent state changed: ${JSON.stringify(data.data)}`);
              if (
                data.data.old_state === "speaking" &&
                data.data.new_state === "listening"
              ) {
                // Send TTS stop message to device
                this.sendTtsStopMessage();
              }
              break;
            case "user_input_transcribed":
              // console.log(`Transcription: ${JSON.stringify(data.data)}`);
              // Send STT result back to device
              this.sendSttMessage(data.data.text || data.data.transcript);
              break;
            case "speech_created":
              // console.log(`Speech created: ${JSON.stringify(data.data)}`);
              // Send TTS start message to device
              this.sendTtsStartMessage(data.data.text);
              break;
            // case "metrics_collected":
            //   console.log(`Metrics: ${JSON.stringify(data.data)}`);
            //   break;
            default:
            //console.log(`Unknown data type: ${data.type}`);
          }
        } catch (error) {
          console.error(`Error processing data packet: ${error}`);
        }
      }
    );

    return new Promise(async (resolve, reject) => {
      try {
        console.log(`[LiveKitBridge] Connecting to LiveKit room: ${roomName}`);
        await this.room.connect(url, token, {
          autoSubscribe: true,
          dynacast: true,
        });
        console.log(`✅ [ROOM] Connected to LiveKit room: ${roomName}`);
        console.log(`🔗 [CONNECTION] State: ${this.room.connectionState}`);
        console.log(`🟢 [STATUS] Is connected: ${this.room.isConnected}`);

        // Log existing participants in the room
        console.log(
          `👥 [PARTICIPANTS] Remote participants in room: ${this.room.remoteParticipants.size}`
        );
        this.room.remoteParticipants.forEach((participant, sid) => {
          console.log(`   - ${participant.identity} (${sid})`);

          // Log existing tracks from participants
          participant.trackPublications.forEach((pub, trackSid) => {
            console.log(
              `     📡 Track: ${trackSid}, kind: ${pub.kind}, subscribed: ${pub.isSubscribed}`
            );
          });
        });

        this.room.on(
          RoomEvent.TrackSubscribed,
          (track, publication, participant) => {
            console.log(
              `🎵 [TRACK] Subscribed to track: ${track.sid} from ${participant.identity}, kind: ${track.kind}`
            );

            // Handle audio track from agent (TTS audio)
            // Check for both string "audio" and TrackKind.KIND_AUDIO constant
            if (track.kind === "audio" || track.kind === TrackKind.KIND_AUDIO) {
              console.log(
                `🔊 [AUDIO TRACK] Starting audio stream processing for ${participant.identity}`
              );


              const stream = new AudioStream(track);
              const reader = stream.getReader();

              let frameCount = 0;
              let totalBytes = 0;
              let lastLogTime = Date.now();

              const readStream = async () => {
                try {
                  console.log(
                    `🎧 [AUDIO STREAM] Starting to read audio frames from ${participant.identity}`
                  );

                  while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                      this.sendTtsStopMessage();
                      console.log(
                        `🏁 [AUDIO STREAM] Stream ended for ${participant.identity}. Total frames: ${frameCount}, Total bytes: ${totalBytes}`
                      );

                      // Flush any remaining resampled data
                      const finalFrames = this.audioResampler.flush();
                      for (const finalFrame of finalFrames) {
                        const finalBuffer = Buffer.from(
                          finalFrame.data.buffer,
                          finalFrame.data.byteOffset,
                          finalFrame.data.byteLength
                        );
                        // Add final frames to buffer
                        this.frameBuffer = Buffer.concat([this.frameBuffer, finalBuffer]);
                      }

                      // Process any remaining complete frames in buffer
                      const finalTimestamp = (Date.now() - this.connection.udp.startTime) & 0xffffffff;
                      this.processBufferedFrames(finalTimestamp, frameCount, participant.identity);

                      // Send any remaining partial frame if it has significant data
                      if (this.frameBuffer.length > 160) { // At least 10ms worth of 16kHz audio (160 samples * 2 bytes = 320B)
                        console.log(`🔄 [FLUSH] Processing partial 16kHz PCM frame: ${this.frameBuffer.length}B`);

                        // Send remaining PCM data directly without Opus encoding
                        this.connection.sendUdpMessage(this.frameBuffer, finalTimestamp);

                        // Commented out Opus encoding for testing
                        /*
                        if (opusEncoder) {
                          try {
                            // Pad to nearest valid frame size for 16kHz
                            const targetSize = this.frameBuffer.length <= 320 ? 320 : 640;
                            const paddedBuffer = Buffer.alloc(targetSize);
                            this.frameBuffer.copy(paddedBuffer);

                            const opusBuffer = opusEncoder.encode(paddedBuffer, targetSize / 2);
                            this.connection.sendUdpMessage(opusBuffer, finalTimestamp);
                          } catch (err) {
                            console.log(`⚠️ [FLUSH] Failed to encode partial frame: ${err.message}`);
                          }
                        }
                        */
                      }

                      // Clear the buffer
                      this.frameBuffer = Buffer.alloc(0);
                      break;
                    }

                    frameCount++;

                    // value is an AudioFrame from LiveKit (48kHz)
                    // Push the frame to resampler and get resampled frames back (16kHz)
                    const resampledFrames = this.audioResampler.push(value);

                    // Add resampled frames to buffer instead of processing directly
                    for (const resampledFrame of resampledFrames) {
                      const resampledBuffer = Buffer.from(
                        resampledFrame.data.buffer,
                        resampledFrame.data.byteOffset,
                        resampledFrame.data.byteLength
                      );

                      // Append to frame buffer
                      this.frameBuffer = Buffer.concat([this.frameBuffer, resampledBuffer]);
                      totalBytes += resampledBuffer.length;
                    }

                    const timestamp = (Date.now() - this.connection.udp.startTime) & 0xffffffff;

                    // Process any complete frames from the buffer
                    this.processBufferedFrames(timestamp, frameCount, participant.identity);

                    // Log every 50 frames or every 5 seconds
                    const now = Date.now();
                    if (frameCount % 50 === 0 || now - lastLogTime > 5000) {
                      // console.log(
                      //   `🎵 [AUDIO FRAMES] Received ${frameCount} frames, ${totalBytes} total bytes from ${participant.identity}`
                      // );
                      lastLogTime = now;
                    }

                  }
                } catch (error) {
                  console.error(
                    `❌ [AUDIO STREAM] Error reading audio stream from ${participant.identity}:`,
                    error
                  );
                } finally {
                  console.log(
                    `🔒 [AUDIO STREAM] Releasing reader lock for ${participant.identity}`
                  );
                  reader.releaseLock();
                }
              };

              readStream();
            } else {
              console.log(
                `⚠️ [TRACK] Non-audio track subscribed: ${track.kind} (type: ${typeof track.kind}) from ${participant.identity}`
              );
            }
          }
        );

        // Add track unsubscription handler
        this.room.on(
          RoomEvent.TrackUnsubscribed,
          (track, publication, participant) => {
            console.log(
              `🔇 [TRACK] Unsubscribed from track: ${track.sid} from ${participant.identity}, kind: ${track.kind}`
            );
          }
        );

        // Add participant connection handlers
        this.room.on(RoomEvent.ParticipantConnected, (participant) => {
          console.log(
            `👤 [PARTICIPANT] Connected: ${participant.identity} (${participant.sid})`
          );
        });

        this.room.on(RoomEvent.ParticipantDisconnected, (participant) => {
          console.log(
            `👤 [PARTICIPANT] Disconnected: ${participant.identity} (${participant.sid})`
          );
        });

        // Fixed: Use proper track publishing method
        const {
          LocalAudioTrack,
          TrackPublishOptions,
          TrackSource,
        } = require("@livekit/rtc-node");
        const track = LocalAudioTrack.createAudioTrack(
          "microphone",
          this.audioSource
        );
        const options = new TrackPublishOptions();
        options.source = TrackSource.SOURCE_MICROPHONE;

        const publication = await this.room.localParticipant.publishTrack(
          track,
          options
        );
        console.log(
          `🎤 [PUBLISH] Published local audio track: ${publication.trackSid}`
        );

        // Use roomName as session_id - this is consistent with how LiveKit rooms work
        // The room.sid might not be immediately available, but roomName is our session identifier
        // Include audio_params that the client expects
        resolve({
          session_id: roomName,
          audio_params: {
            sample_rate: 16000,
            channels: 1,
            frame_duration: 20,
            format: "opus"
          }
        });
      } catch (error) {
        console.error("[LiveKitBridge] Error connecting to LiveKit:", error);
        console.error("[LiveKitBridge] Error name:", error.name);
        console.error("[LiveKitBridge] Error message:", error.message);
        reject(error);
      }
    });
  }

  sendAudio(opusData, timestamp) {
    if (this.audioSource) {
      // Audio format analysis (only log occasionally to reduce spam)
      if (Math.random() < 0.01) {
        // Log 1% of packets
        // this.analyzeAudioFormat(opusData, timestamp);
      }

      // Check if data is Opus and decode it
      const isOpus = this.checkOpusFormat(opusData);

      if (isOpus) {
        if (opusDecoder) {
          try {
            // console.log(
            //   `🎵 [OPUS DECODE] Decoding ${opusData.length}B Opus data to PCM`
            // );

            // Decode Opus to PCM
            const pcmBuffer = opusDecoder.decode(opusData, 480);

            if (pcmBuffer && pcmBuffer.length > 0) {
              // Convert Buffer to Int16Array
              const samples = new Int16Array(
                pcmBuffer.buffer,
                pcmBuffer.byteOffset,
                pcmBuffer.length / 2
              );
              const frame = new AudioFrame(samples, 16000, 1, samples.length);

              // console.log(
              //   `📤 [UDP IN] Opus->PCM->LiveKit: ${opusData.length}B opus -> ${pcmBuffer.length}B pcm -> ${samples.length} samples, ts=${timestamp}, mac=${this.macAddress}`
              // );
              this.audioSource.captureFrame(frame);
            } else {
              // console.warn(
              //   `⚠️  [OPUS] Decoder returned empty buffer for ${opusData.length}B input`
              // );
            }
          } catch (err) {
            console.error(`❌ [OPUS] Decode error: ${err.message}`);
            console.log(
              `🔍 [DEBUG] Opus data: ${opusData.slice(0, 8).toString("hex")}...`
            );
          }
        } else {
          console.error(
            `❌ [ERROR] Opus decoder not available! Install with: npm install @discordjs/opus`
          );
          console.log(
            `💡 [WORKAROUND] Treating Opus as PCM (will sound garbled)`
          );

          // Fallback: treat as PCM (will sound bad but won't crash)
          const samples = new Int16Array(
            opusData.buffer,
            opusData.byteOffset,
            Math.min(opusData.length / 2, 320)
          ); // Limit to reasonable PCM size
          const frame = new AudioFrame(samples, 16000, 1, samples.length);
          this.audioSource.captureFrame(frame);
        }
      } else {
        // Treat as PCM
        console.log(`🎤 [PCM] Processing ${opusData.length}B as raw PCM`);
        const samples = new Int16Array(
          opusData.buffer,
          opusData.byteOffset,
          opusData.length / 2
        );
        const frame = new AudioFrame(samples, 16000, 1, samples.length);
        console.log(
          `📤 [UDP IN] Device->LiveKit: ${opusData.length}B, samples=${samples.length}, ts=${timestamp}, mac=${this.macAddress}`
        );
        this.audioSource.captureFrame(frame);
      }
    }
  }

  analyzeAudioFormat(audioData, timestamp) {
    // Check for Opus magic signature
    const isOpus = this.checkOpusFormat(audioData);
    const isPCM = this.checkPCMFormat(audioData);

    console.log(`🔍 [AUDIO ANALYSIS] Format Detection:`);
    console.log(`   📊 Size: ${audioData.length} bytes`);
    console.log(`   🎵 Timestamp: ${timestamp}`);
    console.log(
      `   📋 First 16 bytes: ${audioData.slice(0, Math.min(16, audioData.length)).toString("hex")}`
    );
    console.log(
      `   🎼 Opus signature: ${isOpus ? "✅ DETECTED" : "❌ NOT FOUND"}`
    );
    console.log(
      `   🎤 PCM characteristics: ${isPCM ? "✅ LIKELY PCM" : "❌ UNLIKELY PCM"}`
    );

    // Additional analysis
    this.analyzeAudioStatistics(audioData);
  }

  checkOpusFormat(data) {
    if (data.length < 8) return false;

    // Check for Opus packet headers
    // Opus packets typically start with specific TOC (Table of Contents) byte patterns
    const firstByte = data[0];

    // Opus TOC byte analysis
    // Bits 7-3: config (0-31), Bits 2: stereo flag, Bits 1-0: frame count code
    const config = (firstByte >> 3) & 0x1f;
    const stereo = (firstByte >> 2) & 0x01;
    const frameCount = firstByte & 0x03;

    // console.log(
    //   `   🔍 Opus TOC Analysis: config=${config}, stereo=${stereo}, frames=${frameCount}`
    // );

    // Valid Opus configurations are 0-31
    // Check if it looks like a valid Opus TOC byte
    const validOpusConfig = config >= 0 && config <= 31;

    // Additional Opus packet characteristics
    const hasOpusMarkers = this.checkOpusMarkers(data);

    return validOpusConfig && hasOpusMarkers;
  }

  checkOpusMarkers(data) {
    // Look for common Opus packet patterns
    if (data.length < 4) return false;

    // Check for Opus frame size patterns (common sizes: 120, 240, 480, 960, 1920, 2880 samples)
    // At 16kHz: 120 samples = 7.5ms, 240 = 15ms, 480 = 30ms, etc.
    const commonOpusSizes = [20, 40, 60, 80, 120, 160, 240, 320, 480, 640, 960];
    const isCommonOpusSize = commonOpusSizes.includes(data.length);

    // console.log(
    //   `   📏 Common Opus size (${data.length}B): ${isCommonOpusSize ? "✅" : "❌"}`
    // );

    return isCommonOpusSize;
  }

  checkPCMFormat(data) {
    if (data.length < 32) return false;

    // PCM characteristics analysis
    const samples = new Int16Array(
      data.buffer,
      data.byteOffset,
      Math.min(data.length / 2, 16)
    );

    // Calculate basic statistics
    let sum = 0;
    let maxAbs = 0;
    let zeroCount = 0;

    for (let i = 0; i < samples.length; i++) {
      const sample = samples[i];
      sum += Math.abs(sample);
      maxAbs = Math.max(maxAbs, Math.abs(sample));
      if (sample === 0) zeroCount++;
    }

    const avgAmplitude = sum / samples.length;
    const zeroRatio = zeroCount / samples.length;

    console.log(`   📈 PCM Statistics:`);
    console.log(`      🔊 Avg amplitude: ${avgAmplitude.toFixed(1)}`);
    console.log(`      📊 Max amplitude: ${maxAbs}`);
    console.log(`      🔇 Zero ratio: ${(zeroRatio * 100).toFixed(1)}%`);
    console.log(`      📐 Sample count: ${samples.length}`);

    // PCM heuristics
    const hasReasonableAmplitude = avgAmplitude > 10 && avgAmplitude < 10000;
    const hasVariation = maxAbs > 100;
    const notTooManyZeros = zeroRatio < 0.8;
    const reasonableSize = data.length >= 160 && data.length <= 3840; // 10ms to 240ms at 16kHz

    console.log(`   ✅ PCM Checks:`);
    console.log(
      `      🔊 Reasonable amplitude: ${hasReasonableAmplitude ? "✅" : "❌"}`
    );
    console.log(`      📊 Has variation: ${hasVariation ? "✅" : "❌"}`);
    console.log(
      `      🔇 Not too many zeros: ${notTooManyZeros ? "✅" : "❌"}`
    );
    console.log(`      📏 Reasonable size: ${reasonableSize ? "✅" : "❌"}`);

    return (
      hasReasonableAmplitude &&
      hasVariation &&
      notTooManyZeros &&
      reasonableSize
    );
  }

  analyzeAudioStatistics(data) {
    // Frame size analysis for common audio formats
    const frameSizeAnalysis = this.analyzeFrameSize(data.length);
    console.log(`   ⏱️  Frame Analysis: ${frameSizeAnalysis}`);

    // Entropy analysis (compressed data has higher entropy)
    const entropy = this.calculateEntropy(data);
    console.log(
      `   🎲 Data entropy: ${entropy.toFixed(3)} (PCM: ~7-11, Opus: ~7.5-8)`
    );
  }

  analyzeFrameSize(size) {
    // Common frame sizes for different formats at 16kHz
    const formats = {
      "PCM 10ms": 320, // 160 samples * 2 bytes
      "PCM 20ms": 640, // 320 samples * 2 bytes
      "PCM 30ms": 960, // 480 samples * 2 bytes
      "PCM 60ms": 1920, // 960 samples * 2 bytes
      "Opus 20ms": 40, // Typical Opus frame
      "Opus 40ms": 80, // Typical Opus frame
      "Opus 60ms": 120, // Typical Opus frame
    };

    for (const [format, expectedSize] of Object.entries(formats)) {
      if (size === expectedSize) {
        return `${format} (exact match)`;
      }
    }

    // Check for close matches
    for (const [format, expectedSize] of Object.entries(formats)) {
      if (Math.abs(size - expectedSize) <= 10) {
        return `${format} (close match, diff: ${size - expectedSize})`;
      }
    }

    return `Unknown format (${size}B)`;
  }

  calculateEntropy(data) {
    const freq = new Array(256).fill(0);

    // Count byte frequencies
    for (let i = 0; i < data.length; i++) {
      freq[data[i]]++;
    }

    // Calculate entropy
    let entropy = 0;
    for (let i = 0; i < 256; i++) {
      if (freq[i] > 0) {
        const p = freq[i] / data.length;
        entropy -= p * Math.log2(p);
      }
    }

    return entropy;
  }

  isAlive() {
    return this.room && this.room.isConnected;
  }

  // Send TTS start message to device
  sendTtsStartMessage(text = "") {
    if (!this.connection) return;

    const message = {
      type: "tts",
      state: "start",
      session_id: this.connection.udp.session_id,
    };

    if (text) {
      message.text = text;
    }

    // console.log(
    //   `📤 [MQTT OUT] Sending TTS start to device: ${this.macAddress}`
    // );
    this.connection.sendMqttMessage(JSON.stringify(message));
  }

  // Send TTS sentence start message to device
  sendTtsSentenceStartMessage(text) {
    if (!this.connection) return;

    const message = {
      type: "tts",
      state: "sentence_start",
      session_id: this.connection.udp.session_id,
      text: text || "",
    };

    console.log(
      `📤 [MQTT OUT] Sending TTS sentence start to device: ${this.macAddress} - "${text}"`
    );
    this.connection.sendMqttMessage(JSON.stringify(message));
  }

  // Send TTS stop message to device
  sendTtsStopMessage() {
    if (!this.connection) return;

    const message = {
      type: "tts",
      state: "stop",
      session_id: this.connection.udp.session_id,
    };

    console.log(`📤 [MQTT OUT] Sending TTS stop to device: ${this.macAddress}`);
    this.connection.sendMqttMessage(JSON.stringify(message));
  }

  // Send STT (Speech-to-Text) result to device
  sendSttMessage(text) {
    if (!this.connection || !text) return;

    const message = {
      type: "stt",
      text: text,
      session_id: this.connection.udp.session_id,
    };

    console.log(
      `📤 [MQTT OUT] Sending STT result to device: ${this.macAddress} - "${text}"`
    );
    this.connection.sendMqttMessage(JSON.stringify(message));
  }

  // Send LLM response to device
  sendLlmMessage(text, emotion = "neutral") {
    if (!this.connection || !text) return;

    const message = {
      type: "llm",
      text: text,
      emotion: emotion,
      session_id: this.connection.udp.session_id,
    };

    console.log(
      `📤 [MQTT OUT] Sending LLM response to device: ${this.macAddress} - "${text}"`
    );
    this.connection.sendMqttMessage(JSON.stringify(message));
  }

  // Send record stop message to device
  sendRecordStopMessage() {
    if (!this.connection) return;

    const message = {
      type: "record_stop",
      session_id: this.connection.udp.session_id,
    };

    console.log(
      `📤 [MQTT OUT] Sending record stop to device: ${this.macAddress}`
    );
    this.connection.sendMqttMessage(JSON.stringify(message));
  }

  close() {
    if (this.room) {
      console.log("[LiveKitBridge] Disconnecting from LiveKit room");
      this.room.disconnect();
      this.room = null;
    }
  }
}

const MacAddressRegex = /^[0-9a-f]{2}(:[0-9a-f]{2}){5}$/;

/**
 * MQTT connection class
 * Responsible for application layer logic processing
 */
class MQTTConnection {
  constructor(socket, connectionId, server) {
    this.server = server;
    this.connectionId = connectionId;
    this.clientId = null;
    this.username = null;
    this.password = null;
    this.bridge = null;
    this.udp = {
      remoteAddress: null,
      cookie: null,
      localSequence: 0,
      remoteSequence: 0,
    };
    this.headerBuffer = Buffer.alloc(16);

    // Create protocol handler and pass in socket
    this.protocol = new MQTTProtocol(socket);
    this.setupProtocolHandlers();
  }

  setupProtocolHandlers() {
    // Set protocol event handlers
    this.protocol.on("connect", (connectData) => {
      // console.log("Received CONNECT packet");
      this.handleConnect(connectData);
    });

    this.protocol.on("publish", (publishData) => {
      this.handlePublish(publishData);
    });

    this.protocol.on("subscribe", (subscribeData) => {
      this.handleSubscribe(subscribeData);
    });

    this.protocol.on("disconnect", () => {
      this.handleDisconnect();
    });

    this.protocol.on("close", () => {
      debug(`${this.clientId} client disconnected`);
      this.server.removeConnection(this);
    });

    this.protocol.on("error", (err) => {
      debug(`${this.clientId} connection error:`, err);
      this.close();
    });

    this.protocol.on("protocolError", (err) => {
      debug(`${this.clientId} protocol error:`, err);
      this.close();
    });
  }

  handleConnect(connectData) {
    this.clientId = connectData.clientId;
    this.username = connectData.username;
    this.password = connectData.password;

    debug("Client connected:", {
      clientId: this.clientId,
      username: this.username,
      password: this.password,
      protocol: connectData.protocol,
      protocolLevel: connectData.protocolLevel,
      keepAlive: connectData.keepAlive,
    });

    const parts = this.clientId.split("@@@");
    if (parts.length === 3) {
      // GID_test@@@mac_address@@@uuid
      try {
        const validated = validateMqttCredentials(
          this.clientId,
          this.username,
          this.password
        );
        this.groupId = validated.groupId;
        this.macAddress = validated.macAddress;
        this.uuid = validated.uuid;
        this.userData = validated.userData;
      } catch (error) {
        debug("MQTT credentials validation failed:", error.message);
        this.close();
        return;
      }
    } else if (parts.length === 2) {
      // GID_test@@@mac_address
      this.groupId = parts[0];
      this.macAddress = parts[1].replace(/_/g, ":");
      if (!MacAddressRegex.test(this.macAddress)) {
        debug("Invalid macAddress:", this.macAddress);
        this.close();
        return;
      }
    } else {
      debug("Invalid clientId:", this.clientId);
      this.close();
      return;
    }

    this.replyTo = `devices/p2p/${parts[1]}`;
    this.server.addConnection(this);
  }

  handleSubscribe(subscribeData) {
    debug("Client subscribed to topic:", {
      clientId: this.clientId,
      topic: subscribeData.topic,
      packetId: subscribeData.packetId,
    });
    // Send SUBACK
    this.protocol.sendSuback(subscribeData.packetId, 0);
  }

  handleDisconnect() {
    debug("Received disconnect request:", { clientId: this.clientId });
    // Clean up connection
    this.server.removeConnection(this);
  }

  close() {
    this.closing = true;
    if (this.bridge) {
      this.bridge.close();
      this.bridge = null;
    } else {
      this.protocol.close();
    }
  }

  checkKeepAlive() {
    const now = Date.now();
    const keepAliveInterval = this.protocol.getKeepAliveInterval();
    // If keepAliveInterval is 0, heartbeat check is not needed
    if (keepAliveInterval === 0 || !this.protocol.isConnected) return;

    const lastActivity = this.protocol.getLastActivity();
    const timeSinceLastActivity = now - lastActivity;

    // If heartbeat interval is exceeded, close connection
    if (timeSinceLastActivity > keepAliveInterval) {
      debug("Heartbeat timeout, closing connection:", this.clientId);
      this.close();
    }
  }

  handlePublish(publishData) {
    debug("Received publish message:", {
      clientId: this.clientId,
      topic: publishData.topic,
      payload: publishData.payload,
      qos: publishData.qos,
    });

    if (publishData.qos !== 0) {
      debug("Unsupported QoS level:", publishData.qos, "closing connection");
      this.close();
      return;
    }

    const json = JSON.parse(publishData.payload);
    if (json.type === "hello") {
      if (json.version !== 3) {
        debug(
          "Unsupported protocol version:",
          json.version,
          "closing connection"
        );
        this.close();
        return;
      }

      this.parseHelloMessage(json).catch((error) => {
        debug("Failed to process hello message:", error);
        this.close();
      });
    } else {
      this.parseOtherMessage(json).catch((error) => {
        debug("Failed to process other message:", error);
        this.close();
      });
    }
  }

  sendMqttMessage(payload) {
    debug(`Sending message to ${this.replyTo}: ${payload}`);
    this.protocol.sendPublish(this.replyTo, payload, 0, false, false);
  }

  sendUdpMessage(payload, timestamp) {
    if (!this.udp.remoteAddress) {
      debug(`Device ${this.clientId} not connected, cannot send UDP message`);
      return;
    }

    this.udp.localSequence++;
    const header = this.generateUdpHeader(
      payload.length,
      timestamp,
      this.udp.localSequence
    );
    // console.log(
    //   `📡 [UDP SEND] To ${this.udp.remoteAddress.address}:${this.udp.remoteAddress.port} - payload=${payload.length}B, ts=${timestamp}, seq=${this.udp.localSequence}`
    // );
    // console.log(
    //   `🔐 Encrypting: payload=${payload.length}B, timestamp=${timestamp}, seq=${this.udp.localSequence}`
    // );
    // console.log(`🔐 Header: ${header.toString("hex")}`);
    // console.log(`🔐 Key: ${this.udp.key.toString("hex")}`);
    // console.log(
    //   `🔐 Payload first 8 bytes: ${payload.subarray(0, 8).toString("hex")}`
    // );
    const cipher = crypto.createCipheriv(
      this.udp.encryption,
      this.udp.key,
      header
    );
    const encryptedPayload = Buffer.concat([
      cipher.update(payload),
      cipher.final(),
    ]);
    // console.log(
    //   `🔐 Encrypted first 8 bytes: ${encryptedPayload
    //     .subarray(0, 8)
    //     .toString("hex")}`
    // );
    const message = Buffer.concat([header, encryptedPayload]);
    this.server.sendUdpMessage(message, this.udp.remoteAddress);
  }

  generateUdpHeader(length, timestamp, sequence) {
    // Reuse pre-allocated buffer
    this.headerBuffer.writeUInt8(1, 0); // packet_type
    this.headerBuffer.writeUInt8(0, 1); // flags
    this.headerBuffer.writeUInt16BE(length, 2); // payload_len
    this.headerBuffer.writeUInt32BE(this.connectionId, 4); // ssrc/connection_id
    this.headerBuffer.writeUInt32BE(timestamp, 8); // timestamp
    this.headerBuffer.writeUInt32BE(sequence, 12); // sequence
    return Buffer.from(this.headerBuffer); // Return copy to avoid concurrency issues
  }

  async parseHelloMessage(json) {
    this.udp = {
      ...this.udp,
      key: crypto.randomBytes(16),
      nonce: this.generateUdpHeader(0, 0, 0),
      encryption: "aes-128-ctr",
      remoteSequence: 0,
      localSequence: 0,
      startTime: Date.now(),
    };

    if (this.bridge) {
      debug(
        `${this.clientId} received duplicate hello message, closing previous bridge`
      );
      this.bridge.close();
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    this.bridge = new LiveKitBridge(
      this,
      json.version,
      this.macAddress,
      this.uuid,
      this.userData
    );
    this.bridge.on("close", () => {
      const seconds = (Date.now() - this.udp.startTime) / 1000;
      console.log(
        `Call ended: ${this.clientId} Session: ${this.udp.session_id} Duration: ${seconds}s`
      );
      this.sendMqttMessage(
        JSON.stringify({ type: "goodbye", session_id: this.udp.session_id })
      );
      this.bridge = null;
      if (this.closing) {
        this.protocol.close();
      }
    });

    try {
      console.log(`Call started: ${this.clientId} Protocol: ${json.version}`);
      const helloReply = await this.bridge.connect(
        json.audio_params,
        json.features
      );
      this.udp.session_id = helloReply.session_id;

      this.sendMqttMessage(
        JSON.stringify({
          type: "hello",
          version: json.version,
          session_id: this.udp.session_id,
          transport: "udp",
          udp: {
            server: this.server.publicIp,
            port: this.server.udpPort,
            encryption: this.udp.encryption,
            key: this.udp.key.toString("hex"),
            nonce: this.udp.nonce.toString("hex"),
          },
          audio_params: helloReply.audio_params,
        })
      );
    } catch (error) {
      this.sendMqttMessage(
        JSON.stringify({
          type: "error",
          message: "Failed to process hello message",
        })
      );
      console.error(
        `${this.clientId} failed to process hello message: ${error}`
      );
    }
  }

  async parseOtherMessage(json) {
    if (!this.bridge) {
      if (json.type !== "goodbye") {
        this.sendMqttMessage(
          JSON.stringify({ type: "goodbye", session_id: json.session_id })
        );
      }
      return;
    }

    if (json.type === "goodbye") {
      this.bridge.close();
      this.bridge = null;
      return;
    }

    // Not sending other messages to LiveKit for now
    debug("Received other message, not forwarding to LiveKit:", json);
  }

  onUdpMessage(rinfo, message, payloadLength, timestamp, sequence) {
    if (!this.bridge) {
      // console.log(
      //   `📡 [UDP RECV] No bridge available for ${this.clientId}, dropping message`
      // );
      return;
    }

    if (this.udp.remoteAddress !== rinfo) {
      // console.log(
      //   `📡 [UDP RECV] New remote address: ${rinfo.address}:${rinfo.port} for ${this.clientId}`
      // );
      this.udp.remoteAddress = rinfo;
    }

    if (sequence < this.udp.remoteSequence) {
      // console.log(
      //   `📡 [UDP RECV] Out of order packet: seq=${sequence}, expected>=${this.udp.remoteSequence}, dropping`
      // );
      return;
    }

    // console.log(
    //   `📡 [UDP RECV] From ${rinfo.address}:${rinfo.port} - payload=${payloadLength}B, ts=${timestamp}, seq=${sequence}`
    // );

    // Process encrypted data
    const header = message.slice(0, 16);
    const encryptedPayload = message.slice(16, 16 + payloadLength);
    const cipher = crypto.createDecipheriv(
      this.udp.encryption,
      this.udp.key,
      header
    );
    const payload = Buffer.concat([
      cipher.update(encryptedPayload),
      cipher.final(),
    ]);

    // Check if this is a ping message
    const payloadStr = payload.toString();
    if (payloadStr.startsWith("ping:")) {
      console.log(
        `🏓 [UDP PING] Received ping: ${payloadStr} from ${rinfo.address}:${rinfo.port}`
      );
      // Ping message received, connection is now established
      return;
    }

    //console.log(
    // `🔊 [AUDIO RECV] Decrypted ${payload.length}B audio data, forwarding to LiveKit`
    //);
    this.bridge.sendAudio(payload, timestamp);
    this.udp.remoteSequence = sequence;
  }

  isAlive() {
    return this.bridge && this.bridge.isAlive();
  }
}

/**
 * Virtual MQTT connection class for EMQX broker connections
 * Simulates the original MQTTConnection interface but works through EMQX
 */
class VirtualMQTTConnection {
  constructor(deviceId, connectionId, gateway, helloPayload) {
    this.deviceId = deviceId;
    this.connectionId = connectionId;
    this.gateway = gateway;
    this.clientId = helloPayload.clientId || deviceId;
    this.username = helloPayload.username;
    this.password = helloPayload.password;
     this.fullClientId = helloPayload.clientId;

    this.bridge = null;
    this.udp = {
      remoteAddress: null,
      cookie: null,
      localSequence: 0,
      remoteSequence: 0,
    };
    this.headerBuffer = Buffer.alloc(16);
    this.closing = false;

    // Parse device info from hello message
    if (helloPayload.clientId) {
      const parts = helloPayload.clientId.split("@@@");
      if (parts.length === 3) {
        // GID_test@@@mac_address@@@uuid format
        this.groupId = parts[0];
        this.macAddress = parts[1].replace(/_/g, ":");
        this.uuid = parts[2];
        this.userData = null; // Set to null since we don't have user data

        console.log(`📱 [VIRTUAL] Parsed client info:`);
        console.log(`   - Group ID: ${this.groupId}`);
        console.log(`   - MAC Address: ${this.macAddress}`);
        console.log(`   - UUID: ${this.uuid}`);

        // Validate MAC address format
        if (!MacAddressRegex.test(this.macAddress)) {
          console.error(`❌ [VIRTUAL] Invalid macAddress: ${this.macAddress}`);
          this.close();
          return;
        }

        // For virtual connections, we can skip the full credential validation
        // since we're working with EMQX and not the original MQTT protocol

      } else if (parts.length === 2) {
        this.groupId = parts[0];
        this.macAddress = parts[1].replace(/_/g, ":");
        this.uuid = `virtual-${Date.now()}`; // Generate a virtual UUID
        this.userData = null;

        if (!MacAddressRegex.test(this.macAddress)) {
          console.error(`❌ [VIRTUAL] Invalid macAddress: ${this.macAddress}`);
          this.close();
          return;
        }
      } else {
        console.error(`❌ [VIRTUAL] Invalid clientId format: ${helloPayload.clientId}`);
        this.close();
        return;
      }

      this.replyTo = `devices/p2p/${parts[1]}`;
      console.log(`📱 [VIRTUAL] Reply topic set to: ${this.replyTo}`);
    } else {
      console.error(`❌ [VIRTUAL] No clientId provided in hello payload`);
      this.close();
      return;
    }

    debug(`Virtual connection created for device: ${this.deviceId}`);
  }

  handlePublish(publishData) {
    try {
      const json = JSON.parse(publishData.payload);
      if (json.type === "hello") {
        if (json.version !== 3) {
          debug(
            "Unsupported protocol version:",
            json.version,
            "closing connection"
          );
          this.close();
          return;
        }

        this.parseHelloMessage(json).catch((error) => {
          debug("Failed to process hello message:", error);
          this.close();
        });
      } else {
        this.parseOtherMessage(json).catch((error) => {
          debug("Failed to process other message:", error);
          this.close();
        });
      }
    } catch (error) {
      debug("Error parsing message:", error);
    }
  }

  sendMqttMessage(payload) {
    console.log(`📤 [VIRTUAL] sendMqttMessage called for device: ${this.deviceId}`);
    console.log(`📤 [VIRTUAL] Payload: ${payload}`);
    debug(`Sending message to ${this.deviceId}: ${payload}`);

    try {
      const parsedPayload = JSON.parse(payload);
      console.log(`📤 [VIRTUAL] Parsed payload:`, parsedPayload);
      this.gateway.publishToDevice(this.fullClientId, parsedPayload)
      console.log(`📤 [VIRTUAL] Called publishToDevice for device: ${this.deviceId}`);
    } catch (error) {
      console.error(`❌ [VIRTUAL] Error in sendMqttMessage for device ${this.deviceId}:`, error);
    }
  }

  sendUdpMessage(payload, timestamp) {
    if (!this.udp.remoteAddress) {
      debug(`Device ${this.deviceId} not connected, cannot send UDP message`);
      return;
    }

    this.udp.localSequence++;
    const header = this.generateUdpHeader(
      payload.length,
      timestamp,
      this.udp.localSequence
    );

    const cipher = crypto.createCipheriv(
      this.udp.encryption,
      this.udp.key,
      header
    );
    const encryptedPayload = Buffer.concat([
      cipher.update(payload),
      cipher.final(),
    ]);
    const message = Buffer.concat([header, encryptedPayload]);
    this.gateway.sendUdpMessage(message, this.udp.remoteAddress);
  }

  generateUdpHeader(length, timestamp, sequence) {
    this.headerBuffer.writeUInt8(1, 0);
    this.headerBuffer.writeUInt8(0, 1);
    this.headerBuffer.writeUInt16BE(length, 2);
    this.headerBuffer.writeUInt32BE(this.connectionId, 4);
    this.headerBuffer.writeUInt32BE(timestamp, 8);
    this.headerBuffer.writeUInt32BE(sequence, 12);
    return Buffer.from(this.headerBuffer);
  }

  async parseHelloMessage(json) {
    this.udp = {
      ...this.udp,
      key: crypto.randomBytes(16),
      nonce: this.generateUdpHeader(0, 0, 0),
      encryption: "aes-128-ctr",
      remoteSequence: 0,
      localSequence: 0,
      startTime: Date.now(),
    };

    if (this.bridge) {
      debug(
        `${this.deviceId} received duplicate hello message, closing previous bridge`
      );
      this.bridge.close();
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    this.bridge = new LiveKitBridge(
      this,
      json.version,
      this.macAddress,
      this.uuid,
      this.userData
    );
    this.bridge.on("close", () => {
      const seconds = (Date.now() - this.udp.startTime) / 1000;
      console.log(
        `Call ended: ${this.deviceId} Session: ${this.udp.session_id} Duration: ${seconds}s`
      );
      this.sendMqttMessage(
        JSON.stringify({ type: "goodbye", session_id: this.udp.session_id })
      );
      this.bridge = null;
      if (this.closing) {
        // Remove from gateway connections
        this.gateway.connections.delete(this.connectionId);
        this.gateway.deviceConnections.delete(this.deviceId);
      }
    });

    try {
      console.log(`Call started: ${this.deviceId} Protocol: ${json.version}`);
      const helloReply = await this.bridge.connect(
        json.audio_params,
        json.features
      );
      console.log(`📡 [HELLO REPLY] Bridge connect response:`, helloReply);

      this.udp.session_id = helloReply.session_id;
      console.log(`📡 [SESSION ID] Set session_id to: ${this.udp.session_id}`);

      this.sendMqttMessage(
        JSON.stringify({
          type: "hello",
          version: json.version,
          session_id: this.udp.session_id,
          transport: "udp",
          udp: {
            server: this.gateway.publicIp,
            port: this.gateway.udpPort,
            encryption: this.udp.encryption,
            key: this.udp.key.toString("hex"),
            nonce: this.udp.nonce.toString("hex"),
          },
          audio_params: helloReply.audio_params,
        })
      );
    } catch (error) {
      this.sendMqttMessage(
        JSON.stringify({
          type: "error",
          message: "Failed to process hello message",
        })
      );
      console.error(
        `${this.deviceId} failed to process hello message: ${error}`
      );
    }
  }

  async parseOtherMessage(json) {
    if (!this.bridge) {
      if (json.type !== "goodbye") {
        this.sendMqttMessage(
          JSON.stringify({ type: "goodbye", session_id: json.session_id })
        );
      }
      return;
    }

    if (json.type === "goodbye") {
      this.bridge.close();
      this.bridge = null;
      return;
    }

    debug("Received other message, not forwarding to LiveKit:", json);
  }

  onUdpMessage(rinfo, message, payloadLength, timestamp, sequence) {
    if (!this.bridge) {
      return;
    }

    if (this.udp.remoteAddress !== rinfo) {
      this.udp.remoteAddress = rinfo;
    }

    if (sequence < this.udp.remoteSequence) {
      return;
    }

    const header = message.slice(0, 16);
    const encryptedPayload = message.slice(16, 16 + payloadLength);
    const cipher = crypto.createDecipheriv(
      this.udp.encryption,
      this.udp.key,
      header
    );
    const payload = Buffer.concat([
      cipher.update(encryptedPayload),
      cipher.final(),
    ]);

    const payloadStr = payload.toString();
    if (payloadStr.startsWith("ping:")) {
      console.log(
        `🏓 [UDP PING] Received ping: ${payloadStr} from ${rinfo.address}:${rinfo.port}`
      );
      return;
    }

    this.bridge.sendAudio(payload, timestamp);
    this.udp.remoteSequence = sequence;
  }

  checkKeepAlive() {
    // Virtual connections don't need traditional keep-alive since EMQX handles it
  }

  close() {
    this.closing = true;
    if (this.bridge) {
      this.bridge.close();
      this.bridge = null;
    }
    // Remove from gateway maps
    this.gateway.connections.delete(this.connectionId);
    this.gateway.deviceConnections.delete(this.deviceId);
  }

  isAlive() {
    return this.bridge && this.bridge.isAlive();
  }
}

class MQTTGateway {
  constructor() {
    this.udpPort = parseInt(process.env.UDP_PORT) || 1883;
    this.publicIp = process.env.PUBLIC_IP || "127.0.0.1";
    this.connections = new Map(); // clientId -> MQTTConnection
    this.keepAliveTimer = null;
    this.keepAliveCheckInterval = 1000; // Check every 1 second by default
    this.headerBuffer = Buffer.alloc(16);
    this.mqttClient = null;
    this.deviceConnections = new Map(); // deviceId -> connection info
    this.clientConnections = new Map(); // clientId -> device info (for tracking EMQX clients)
  }

  generateNewConnectionId() {
    // Generate a unique 32-bit integer
    let id;
    do {
      id = Math.floor(Math.random() * 0xffffffff);
    } while (this.connections.has(id));
    return id;
  }

  start() {
    // Connect to EMQX broker
    this.connectToEmqxBroker();

    this.udpServer = dgram.createSocket("udp4");
    this.udpServer.on("message", this.onUdpMessage.bind(this));
    this.udpServer.on("error", (err) => {
      console.error("UDP error", err);
      setTimeout(() => {
        process.exit(1);
      }, 1000);
    });

    this.udpServer.bind(this.udpPort, () => {
      console.warn(`UDP server listening on ${this.publicIp}:${this.udpPort}`);
    });

    // Start global heartbeat check timer
    this.setupKeepAliveTimer();
  }

  connectToEmqxBroker() {
    const brokerConfig = configManager.get("mqtt_broker");
    if (!brokerConfig) {
      console.error("MQTT broker configuration not found in config");
      process.exit(1);
    }

    const clientId = `mqtt-gateway-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const brokerUrl = `${brokerConfig.protocol}://${brokerConfig.host}:${brokerConfig.port}`;

    console.log(`Connecting to EMQX broker: ${brokerUrl}`);

    this.mqttClient = mqtt.connect(brokerUrl, {
      clientId: clientId,
      keepalive: brokerConfig.keepalive || 60,
      clean: brokerConfig.clean !== false,
      reconnectPeriod: brokerConfig.reconnectPeriod || 1000,
      connectTimeout: brokerConfig.connectTimeout || 30000
    });

    this.mqttClient.on('connect', () => {
      console.log(`✅ Connected to EMQX broker: ${brokerUrl}`);
      // Subscribe to gateway control topics
      this.mqttClient.subscribe('devices/+/hello', (err) => {
        if (err) {
          console.error('Failed to subscribe to device hello topic:', err);
        } else {
          console.log('📡 Subscribed to devices/+/hello');
        }
      });
      this.mqttClient.subscribe('devices/+/data', (err) => {
        if (err) {
          console.error('Failed to subscribe to device data topic:', err);
        } else {
          console.log('📡 Subscribed to devices/+/data');
        }
      });
      // Subscribe to the internal topic where EMQX republishes with client info
      this.mqttClient.subscribe('internal/server-ingest', (err) => {
        if (err) {
          console.error('Failed to subscribe to internal/server-ingest topic:', err);
        } else {
          console.log('📡 Subscribed to internal/server-ingest');
        }
      });
    });

    this.mqttClient.on('error', (err) => {
      console.error('MQTT connection error:', err);
    });

    this.mqttClient.on('offline', () => {
      console.warn('MQTT client went offline');
    });

    this.mqttClient.on('reconnect', () => {
      console.log('MQTT client reconnecting...');
    });

    this.mqttClient.on('message', (topic, message) => {
      this.handleMqttMessage(topic, message);
    });
  }

  handleMqttMessage(topic, message) {
    // Add detailed logging for all incoming MQTT messages
    console.log(`📨 [MQTT IN] Received message on topic: ${topic}`);
    console.log(`📨 [MQTT IN] Message length: ${message.length} bytes`);

    try {
      const payload = JSON.parse(message.toString());
      const topicParts = topic.split('/');

      console.log(`📨 [MQTT IN] Parsed payload:`, JSON.stringify(payload, null, 2));
      console.log(`📨 [MQTT IN] Topic parts:`, topicParts);

      if (topic === 'internal/server-ingest') {
        // Handle messages republished by EMQX with client ID info
        console.log(`📨 [MQTT IN] Message from internal/server-ingest topic`);

        // Extract client ID and original payload from EMQX republish rule
        const clientId = payload.sender_client_id;
        const originalPayload = payload.orginal_payload;

        if (!clientId || !originalPayload) {
          console.error(`❌ [MQTT IN] Invalid republished message format - missing clientId or originalPayload`);
          return;
        }

        console.log(`📨 [MQTT IN] Client ID: ${clientId}`);
        console.log(`📨 [MQTT IN] Original payload:`, JSON.stringify(originalPayload, null, 2));

        // Extract device MAC from client ID
        let deviceId = 'unknown-device';
        const parts = clientId.split('@@@');
        if (parts.length >= 2) {
          deviceId = parts[1].replace(/_/g, ':'); // Convert MAC format
        }

        console.log(`📨 [MQTT IN] Device message from internal/server-ingest - Device: ${deviceId}, Message type: ${originalPayload.type}`);

        // Create enhanced payload with client connection info for VirtualMQTTConnection
        const enhancedPayload = {
          ...originalPayload,
          clientId: clientId,
          username: 'extracted_from_emqx',
          password: 'extracted_from_emqx'
        };

        if (originalPayload.type === 'hello') {
          console.log(`👋 [HELLO] Processing hello message from internal/server-ingest: ${deviceId}`);
          this.handleDeviceHello(deviceId, enhancedPayload);
        } else {
          console.log(`📊 [DATA] Processing data message from internal/server-ingest: ${deviceId}`);
          this.handleDeviceData(deviceId, enhancedPayload);
        }
      } else if (topicParts.length >= 3 && topicParts[0] === 'devices') {
        const deviceId = topicParts[1];
        const messageType = topicParts[2];

        console.log(`📨 [MQTT IN] Device message - Device: ${deviceId}, Type: ${messageType}`);
        debug(`📨 Received MQTT message from device ${deviceId}: ${messageType}`);

        if (messageType === 'hello') {
          console.log(`👋 [HELLO] Processing hello message from device: ${deviceId}`);
          this.handleDeviceHello(deviceId, payload);
        } else if (messageType === 'data') {
          console.log(`📊 [DATA] Processing data message from device: ${deviceId}`);
          this.handleDeviceData(deviceId, payload);
        } else {
          console.log(`❓ [UNKNOWN] Unknown message type '${messageType}' from device: ${deviceId}`);
        }
      } else {
        console.log(`❓ [MQTT IN] Message on unexpected topic format: ${topic}`);
      }
    } catch (error) {
      console.error('❌ [MQTT IN] Error processing MQTT message:', error);
      console.log(`📨 [MQTT IN] Raw message:`, message.toString());
    }
  }

  handleDeviceHello(deviceId, payload) {
    console.log(`📱 [HELLO] handleDeviceHello called for device: ${deviceId}`);

    // Create a virtual connection for this device
    const connectionId = this.generateNewConnectionId();
    console.log(`📱 [HELLO] Generated connection ID: ${connectionId}`);

    const virtualConnection = new VirtualMQTTConnection(deviceId, connectionId, this, payload);
    console.log(`📱 [HELLO] Created VirtualMQTTConnection for device: ${deviceId}`);

    this.connections.set(connectionId, virtualConnection);
    this.deviceConnections.set(deviceId, { connectionId, connection: virtualConnection });

    console.log(`📱 [HELLO] Device ${deviceId} connected via EMQX`);
    console.log(`📱 [HELLO] Now calling handlePublish to process hello message...`);

    // Manually trigger the hello message processing
    try {
      virtualConnection.handlePublish({ payload: JSON.stringify(payload) });
      console.log(`📱 [HELLO] Successfully called handlePublish for device: ${deviceId}`);
    } catch (error) {
      console.error(`❌ [HELLO] Error in handlePublish for device ${deviceId}:`, error);
    }
  }

  handleDeviceData(deviceId, payload) {
    const deviceInfo = this.deviceConnections.get(deviceId);
    if (deviceInfo && deviceInfo.connection) {
      deviceInfo.connection.handlePublish({ payload: JSON.stringify(payload) });
    } else {
      console.warn(`📱 Received data from unknown device: ${deviceId}`);
    }
  }

  publishToDevice(clientIdOrDeviceId, message) {
  console.log(`📤 [MQTT OUT] publishToDevice called - Client/Device: ${clientIdOrDeviceId}`);
  console.log(`📤 [MQTT OUT] Message:`, JSON.stringify(message, null, 2));

  if (this.mqttClient && this.mqttClient.connected) {
    // Use the full client ID directly in the topic
    const topic = `devices/p2p/${clientIdOrDeviceId}`;
    console.log(`📤 [MQTT OUT] Publishing to topic: ${topic}`);

    this.mqttClient.publish(topic, JSON.stringify(message), (err) => {
      if (err) {
        console.error(`❌ [MQTT OUT] Failed to publish to client ${clientIdOrDeviceId}:`, err);
      } else {
        console.log(`✅ [MQTT OUT] Successfully published to client ${clientIdOrDeviceId} on topic ${topic}`);
        debug(`📤 Published to client ${clientIdOrDeviceId}: ${JSON.stringify(message)}`);
      }
    });
  } else {
    console.error('❌ [MQTT OUT] MQTT client not connected, cannot publish message');
    console.log(`📊 [MQTT OUT] Client connected: ${this.mqttClient ? this.mqttClient.connected : 'null'}`);
  }
}

  /**
   * Set up global heartbeat check timer
   */
  setupKeepAliveTimer() {
    // Clear existing timer
    this.clearKeepAliveTimer();
    this.lastConnectionCount = 0;
    this.lastActiveConnectionCount = 0;

    // Set new timer
    this.keepAliveTimer = setInterval(() => {
      // Check heartbeat status of all connections
      for (const connection of this.connections.values()) {
        connection.checkKeepAlive();
      }

      const activeCount = Array.from(this.connections.values()).filter(
        (connection) => connection.isAlive()
      ).length;
      if (
        activeCount !== this.lastActiveConnectionCount ||
        this.connections.size !== this.lastConnectionCount
      ) {
        // console.log(
        //   `Connections: ${this.connections.size}, Active: ${activeCount}`
        // );
        this.lastActiveConnectionCount = activeCount;
        this.lastConnectionCount = this.connections.size;
      }
    }, this.keepAliveCheckInterval);
  }

  /**
   * Clear heartbeat check timer
   */
  clearKeepAliveTimer() {
    if (this.keepAliveTimer) {
      clearInterval(this.keepAliveTimer);
      this.keepAliveTimer = null;
    }
  }

  addConnection(connection) {
    // Check if a connection with the same clientId already exists
    for (const [key, value] of this.connections.entries()) {
      if (value.clientId === connection.clientId) {
        debug(
          `${connection.clientId} connection already exists, closing old connection`
        );
        value.close();
      }
    }
    this.connections.set(connection.connectionId, connection);
  }

  removeConnection(connection) {
    debug(`Closing connection: ${connection.connectionId}`);
    if (this.connections.has(connection.connectionId)) {
      this.connections.delete(connection.connectionId);
    }
  }

  sendUdpMessage(message, remoteAddress) {
    this.udpServer.send(message, remoteAddress.port, remoteAddress.address);
  }

  onUdpMessage(message, rinfo) {
    // message format: [type: 1u, flag: 1u, payloadLength: 2u, cookie: 4u, timestamp: 4u, sequence: 4u, payload: n]
    if (message.length < 16) {
      //console.warn(
      //`📡 [UDP SERVER] Received incomplete UDP header from ${rinfo.address}:${rinfo.port}, length=${message.length}`
      // );
      return;
    }

    try {
      const type = message.readUInt8(0);
      if (type !== 1) {
        // console.warn(
        //   `📡 [UDP SERVER] Invalid packet type: ${type} from ${rinfo.address}:${rinfo.port}`
        // );
        return;
      }

      const payloadLength = message.readUInt16BE(2);
      if (message.length < 16 + payloadLength) {
        // console.warn(
        //   `📡 [UDP SERVER] Incomplete message from ${rinfo.address}:${rinfo.port}, expected=${16 + payloadLength}, got=${message.length}`
        // );
        return;
      }

      const connectionId = message.readUInt32BE(4);
      const connection = this.connections.get(connectionId);
      if (!connection) {
        // console.warn(`📡 [UDP SERVER] No connection found for ID: ${connectionId} from ${rinfo.address}:${rinfo.port}`);
        return;
      }

      const timestamp = message.readUInt32BE(8);
      const sequence = message.readUInt32BE(12);

      // console.log(
      //   `📡 [UDP SERVER] Routing message to connection ${connectionId} (${connection.clientId})`
      // );
      connection.onUdpMessage(
        rinfo,
        message,
        payloadLength,
        timestamp,
        sequence
      );
    } catch (error) {
      // console.error(
      //   `📡 [UDP SERVER] Message processing error from ${rinfo.address}:${rinfo.port}:`,
      //   error
      // );
    }
  }

  /**
   * Stop server
   */
  async stop() {
    if (this.stopping) {
      return;
    }

    this.stopping = true;
    // Clear heartbeat check timer
    this.clearKeepAliveTimer();

    if (this.connections.size > 0) {
      console.warn(`Waiting for ${this.connections.size} connections to close`);
      for (const connection of this.connections.values()) {
        connection.close();
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 300));
    debug("Waiting for connections to close");
    this.connections.clear();
    this.deviceConnections.clear();

    if (this.udpServer) {
      this.udpServer.close();
      this.udpServer = null;
      console.warn("UDP server stopped");
    }

    // Close MQTT client
    if (this.mqttClient) {
      this.mqttClient.end();
      this.mqttClient = null;
      console.warn("MQTT client disconnected");
    }

    process.exit(0);
  }
}

// Create and start gateway
const gateway = new MQTTGateway();
gateway.start();

process.on("SIGINT", () => {
  console.warn("Received SIGINT signal, starting shutdown");
  gateway.stop();
});
