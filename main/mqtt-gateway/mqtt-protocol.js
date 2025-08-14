const debug = require("debug")("mqtt-server");
const EventEmitter = require("events");

// MQTT fixed header types
const PacketType = {
  CONNECT: 1,
  CONNACK: 2,
  PUBLISH: 3,
  SUBSCRIBE: 8,
  SUBACK: 9,
  PINGREQ: 12,
  PINGRESP: 13,
  DISCONNECT: 14, // Added DISCONNECT
};

/**
 * MQTT protocol handler class
 * Responsible for MQTT protocol parsing and encapsulation, as well as heartbeat maintenance
 */
class MQTTProtocol extends EventEmitter {
  constructor(socket) {
    super();
    this.socket = socket;
    this.buffer = Buffer.alloc(0);
    this.isConnected = false;
    this.keepAliveInterval = 0;
    this.lastActivity = Date.now();
    this.setupSocketHandlers();
  }

  /**
   * Set up Socket event handlers
   */
  setupSocketHandlers() {
    this.socket.on("data", (data) => {
      this.lastActivity = Date.now();
      this.buffer = Buffer.concat([this.buffer, data]);
      this.processBuffer();
    });

    this.socket.on("close", () => {
      this.emit("close");
    });

    this.socket.on("error", (err) => {
      this.emit("error", err);
    });
  }

  /**
   * Process all complete messages in buffer
   */
  processBuffer() {
    // Continue processing data in buffer until no complete messages can be processed
    while (this.buffer.length > 0) {
      // At least 2 bytes needed to start parsing (1 byte fixed header + at least 1 byte remaining length)
      if (this.buffer.length < 2) return;

      try {
        // Get message type
        const firstByte = this.buffer[0];
        const type = firstByte >> 4;

        // Parse remaining length
        const { value: remainingLength, bytesRead } =
          this.decodeRemainingLength(this.buffer);

        // Calculate total message length
        const messageLength = 1 + bytesRead + remainingLength;

        // Check if buffer has complete message
        if (this.buffer.length < messageLength) {
          // Message incomplete, wait for more data
          return;
        }

        // Extract complete message
        const message = this.buffer.subarray(0, messageLength);

        if (!this.isConnected && type !== PacketType.CONNECT) {
          debug(
            "Received non-CONNECT message when not connected, closing connection"
          );
          this.socket.end();
          return;
        }

        // Process based on message type
        switch (type) {
          case PacketType.CONNECT:
            this.parseConnect(message);
            break;
          case PacketType.PUBLISH:
            this.parsePublish(message);
            break;
          case PacketType.SUBSCRIBE:
            this.parseSubscribe(message);
            break;
          case PacketType.PINGREQ:
            this.parsePingReq(message);
            break;
          case PacketType.DISCONNECT:
            this.parseDisconnect(message);
            break;
          default:
            debug("Unhandled packet type:", type, message);
            this.emit(
              "protocolError",
              new Error(`Unhandled packet type: ${type}`)
            );
        }

        // Remove processed message from buffer
        this.buffer = this.buffer.subarray(messageLength);
      } catch (err) {
        // If parsing error, might be incomplete data, wait for more data
        if (err.message === "Malformed Remaining Length") {
          return;
        }

        // Other errors might be protocol errors, clear buffer and emit error event
        this.buffer = Buffer.alloc(0);
        this.emit("protocolError", err);
        return;
      }
    }
  }

  /**
   * Parse Remaining Length field in MQTT packet
   * @param {Buffer} buffer - Message buffer
   * @returns {{value: number, bytesRead: number}} Contains parsed value and bytes read
   */
  decodeRemainingLength(buffer) {
    let multiplier = 1;
    let value = 0;
    let bytesRead = 0;
    let digit;

    do {
      if (bytesRead >= 4 || bytesRead >= buffer.length - 1) {
        throw new Error("Malformed Remaining Length");
      }

      digit = buffer[bytesRead + 1];
      bytesRead++;
      value += (digit & 127) * multiplier;
      multiplier *= 128;
    } while ((digit & 128) !== 0);

    return { value, bytesRead };
  }

  /**
   * Encode Remaining Length field in MQTT packet
   * @param {number} length - Length value to encode
   * @returns {{bytes: Buffer, bytesLength: number}} Contains encoded bytes and byte length
   */
  encodeRemainingLength(length) {
    let digit;
    const bytes = Buffer.alloc(4); // Maximum 4 bytes
    let bytesLength = 0;

    do {
      digit = length % 128;
      length = Math.floor(length / 128);
      // If more bytes remain, set high bit
      if (length > 0) {
        digit |= 0x80;
      }

      bytes[bytesLength++] = digit;
    } while (length > 0 && bytesLength < 4);

    return { bytes, bytesLength };
  }

  /**
   * Parse CONNECT message
   * @param {Buffer} message - Complete CONNECT message
   */
  parseConnect(message) {
    // Parse remaining length
    const { value: remainingLength, bytesRead } =
      this.decodeRemainingLength(message);
    // Position after fixed header (MQTT fixed header first byte + Remaining Length field bytes)
    const headerLength = 1 + bytesRead;

    // Read protocol name length from variable header start position
    const protocolLength = message.readUInt16BE(headerLength);
    const protocol = message.toString(
      "utf8",
      headerLength + 2,
      headerLength + 2 + protocolLength
    );

    // Update position pointer, skip protocol name
    let pos = headerLength + 2 + protocolLength;

    // Protocol level, 4 for MQTT 3.1.1
    const protocolLevel = message[pos];

    // Check protocol version
    if (protocolLevel !== 4) {
      // 4 represents MQTT 3.1.1
      debug("Unsupported protocol version:", protocolLevel);
      // Send CONNACK with unsupported protocol version return code (0x01)
      this.sendConnack(1, false);
      // Close connection
      this.socket.end();
      return;
    }

    pos += 1;
    // Connection flags
    const connectFlags = message[pos];
    const hasUsername = (connectFlags & 0x80) !== 0;
    const hasPassword = (connectFlags & 0x40) !== 0;
    const cleanSession = (connectFlags & 0x02) !== 0;
    pos += 1;

    // Keep alive time
    const keepAlive = message.readUInt16BE(pos);
    pos += 2;

    // Parse clientId
    const clientIdLength = message.readUInt16BE(pos);
    pos += 2;
    const clientId = message.toString("utf8", pos, pos + clientIdLength);
    pos += clientIdLength;

    // Parse username (if exists)
    let username = "";
    if (hasUsername) {
      const usernameLength = message.readUInt16BE(pos);
      pos += 2;
      username = message.toString("utf8", pos, pos + usernameLength);
      pos += usernameLength;
    }

    // Parse password (if exists)
    let password = "";
    if (hasPassword) {
      const passwordLength = message.readUInt16BE(pos);
      pos += 2;
      password = message.toString("utf8", pos, pos + passwordLength);
      pos += passwordLength;
    }

    // Set heartbeat interval (1.5 times client-specified keepAlive value, in seconds)
    this.keepAliveInterval = keepAlive * 1000 * 1.5;

    // Send CONNACK
    this.sendConnack(0, false);

    // Mark as connected
    this.isConnected = true;

    // Emit connection event
    this.emit("connect", {
      clientId,
      protocol,
      protocolLevel,
      keepAlive,
      username,
      password,
      cleanSession,
    });
  }

  /**
   * Parse PUBLISH message
   * @param {Buffer} message - Complete PUBLISH message
   */
  parsePublish(message) {
    // Extract QoS level from first byte (bits 1-2)
    const firstByte = message[0];
    const qos = (firstByte & 0x06) >> 1; // 0x06 is binary 00000110, used as mask to extract QoS bits
    const dup = (firstByte & 0x08) !== 0; // 0x08 is binary 00001000, used as mask to extract DUP flag
    const retain = (firstByte & 0x01) !== 0; // 0x01 is binary 00000001, used as mask to extract RETAIN flag

    // Use common method to parse remaining length
    const { value: remainingLength, bytesRead } =
      this.decodeRemainingLength(message);
    // Position after fixed header (MQTT fixed header first byte + Remaining Length field bytes)
    const headerLength = 1 + bytesRead;

    // Parse topic
    const topicLength = message.readUInt16BE(headerLength);
    const topic = message.toString(
      "utf8",
      headerLength + 2,
      headerLength + 2 + topicLength
    );

    // For QoS > 0, includes message ID
    let packetId = null;
    let payloadStart = headerLength + 2 + topicLength;
    if (qos > 0) {
      packetId = message.readUInt16BE(payloadStart);
      payloadStart += 2;
    }

    // Parse payload
    const payload = message.slice(payloadStart).toString("utf8");

    // Emit publish event
    this.emit("publish", {
      topic,
      payload,
      qos,
      dup,
      retain,
      packetId,
    });
  }

  /**
   * Parse SUBSCRIBE message
   * @param {Buffer} message - Complete SUBSCRIBE message
   */
  parseSubscribe(message) {
    const packetId = message.readUInt16BE(2);
    const topicLength = message.readUInt16BE(4);
    const topic = message.toString("utf8", 6, 6 + topicLength);
    const qos = message[6 + topicLength]; // QoS value

    // Emit subscribe event
    this.emit("subscribe", {
      packetId,
      topic,
      qos,
    });
  }

  /**
   * Parse PINGREQ message
   * @param {Buffer} message - Complete PINGREQ message
   */
  parsePingReq(message) {
    debug("Received heartbeat request");
    // Send PINGRESP
    this.sendPingResp();
    debug("Sent heartbeat response");
  }

  /**
   * Parse DISCONNECT message
   * @param {Buffer} message - Complete DISCONNECT message
   */
  parseDisconnect(message) {
    // Mark as disconnected
    this.isConnected = false;
    // Emit disconnect event
    this.emit("disconnect");
    // Close socket
    this.socket.end();
  }

  /**
   * Send CONNACK message
   * @param {number} returnCode - Return code
   * @param {boolean} sessionPresent - Session present flag
   */
  sendConnack(returnCode = 0, sessionPresent = false) {
    if (!this.socket.writable) return;

    const packet = Buffer.from([
      PacketType.CONNACK << 4,
      2, // Remaining length
      sessionPresent ? 1 : 0, // Connect acknowledge flags
      returnCode, // Return code
    ]);

    this.socket.write(packet);
  }

  /**
   * Send PUBLISH message
   * @param {string} topic - Topic
   * @param {string} payload - Payload
   * @param {number} qos - QoS level
   * @param {boolean} dup - Duplicate flag
   * @param {boolean} retain - Retain flag
   * @param {number} packetId - Packet ID (only needed when QoS > 0)
   */
  sendPublish(
    topic,
    payload,
    qos = 0,
    dup = false,
    retain = false,
    packetId = null
  ) {
    if (!this.isConnected || !this.socket.writable) return;

    const topicLength = Buffer.byteLength(topic);
    const payloadLength = Buffer.byteLength(payload);

    // Calculate remaining length
    let remainingLength = 2 + topicLength + payloadLength;
    // If QoS > 0, need to include packet ID
    if (qos > 0 && packetId) {
      remainingLength += 2;
    }

    // Encode variable length
    const { bytes: remainingLengthBytes, bytesLength: remainingLengthSize } =
      this.encodeRemainingLength(remainingLength);

    // Allocate buffer: fixed header(1 byte) + variable length field + remaining length value
    const packet = Buffer.alloc(1 + remainingLengthSize + remainingLength);

    // Write fixed header
    let firstByte = PacketType.PUBLISH << 4;
    if (dup) firstByte |= 0x08;
    if (qos > 0) firstByte |= qos << 1;
    if (retain) firstByte |= 0x01;
    packet[0] = firstByte;

    // Write variable length field
    remainingLengthBytes.copy(packet, 1, 0, remainingLengthSize);

    // Write topic length and topic
    const variableHeaderStart = 1 + remainingLengthSize;
    packet.writeUInt16BE(topicLength, variableHeaderStart);
    packet.write(topic, variableHeaderStart + 2);

    // If QoS > 0, write packet ID
    let payloadStart = variableHeaderStart + 2 + topicLength;
    if (qos > 0 && packetId) {
      packet.writeUInt16BE(packetId, payloadStart);
      payloadStart += 2;
    }

    // Write payload
    packet.write(payload, payloadStart);

    this.socket.write(packet);
    this.lastActivity = Date.now();
  }

  /**
   * Send SUBACK message
   * @param {number} packetId - Packet ID
   * @param {number} returnCode - Return code
   */
  sendSuback(packetId, returnCode = 0) {
    if (!this.isConnected || !this.socket.writable) return;

    const packet = Buffer.from([
      PacketType.SUBACK << 4,
      3, // Remaining length
      packetId >> 8, // Packet ID MSB
      packetId & 0xff, // Packet ID LSB
      returnCode, // Return code
    ]);

    this.socket.write(packet);
    this.lastActivity = Date.now();
  }

  /**
   * Send PINGRESP message
   */
  sendPingResp() {
    if (!this.isConnected || !this.socket.writable) return;

    const packet = Buffer.from([
      PacketType.PINGRESP << 4, // Fixed header
      0, // Remaining length
    ]);

    this.socket.write(packet);
    this.lastActivity = Date.now();
  }

  /**
   * Get last activity time
   */
  getLastActivity() {
    return this.lastActivity;
  }

  /**
   * Get heartbeat interval
   */
  getKeepAliveInterval() {
    return this.keepAliveInterval;
  }

  /**
   * Clear buffer
   */
  clearBuffer() {
    this.buffer = Buffer.alloc(0);
  }

  /**
   * Close connection
   */
  close() {
    if (this.socket.writable) {
      this.socket.end();
    }
  }
}

// Export PacketType and MQTTProtocol class
module.exports = {
  PacketType,
  MQTTProtocol,
};
