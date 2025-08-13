// Description: MQTT+UDP to WebSocket bridge
// Author: terrence@tenclass.com
// Date: 2025-03-12

require("dotenv").config();

const net = require("net");
const debugModule = require("debug");
const debug = debugModule("mqtt-server");
const crypto = require("crypto");
const dgram = require("dgram");
const Emitter = require("events");
const WebSocket = require("ws");
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
  setDebugEnabled(config.debug);
});
setDebugEnabled(configManager.get("debug"));

class WebSocketBridge extends Emitter {
  constructor(connection, protocolVersion, macAddress, uuid, userData) {
    super();
    this.connection = connection;
    this.macAddress = macAddress;
    this.uuid = uuid;
    this.userData = userData;
    this.wsClient = null;
    this.protocolVersion = protocolVersion;
    this.deviceSaidGoodbye = false;
    this.initializeChatServer();
  }

  initializeChatServer() {
    const devMacAddresss = configManager.get("development")?.mac_addresss || [];
    let chatServers;
    if (devMacAddresss.includes(this.macAddress)) {
      chatServers = configManager.get("development")?.chat_servers;
    } else {
      chatServers = configManager.get("production")?.chat_servers;
    }

    if (!chatServers) {
      throw new Error(`Chat server not found for ${this.macAddress}`);
    }

    this.chatServer =
      chatServers[Math.floor(Math.random() * chatServers.length)];
  }

  async connect(audio_params, features) {
    return new Promise((resolve, reject) => {
      const headers = {
        "device-id": this.macAddress,
        "protocol-version": "2",
        authorization: `Bearer test-token`,
      };
      if (this.uuid) {
        headers["client-id"] = this.uuid;
      }

      if (this.userData && this.userData.ip) {
        headers["x-forwarded-for"] = this.userData.ip;
      }

      this.wsClient = new WebSocket(this.chatServer, { headers });

      this.wsClient.on("open", () => {
        this.sendJson({
          type: "hello",
          version: 2,
          transport: "websocket",
          audio_params,
          features,
        });
      });

      this.wsClient.on("message", (data, isBinary) => {
        if (isBinary) {
          // xiaozhi-server sends raw Opus data directly as binary WebSocket messages
          // No header parsing needed - the entire binary message is the Opus payload
          console.log(
            `📦 WebSocket binary message: ${data.length} bytes of raw Opus data`
          );
          console.log(
            `📦 First 8 bytes: ${data
              .subarray(0, Math.min(8, data.length))
              .toString("hex")}`
          );
          // Generate timestamp for UDP packet (use relative timestamp to fit in 32-bit)
          const timestamp =
            (Date.now() - this.connection.udp.startTime) & 0xffffffff;
          // Send the raw Opus data directly via UDP
          this.connection.sendUdpMessage(data, timestamp);
        } else {
          // JSON data sent via MQTT
          const message = JSON.parse(data.toString());
          if (message.type === "hello") {
            resolve(message);
          } else {
            this.connection.sendMqttMessage(JSON.stringify(message));
          }
        }
      });

      this.wsClient.on("error", (error) => {
        console.error(`WebSocket error for device ${this.macAddress}:`, error);
        this.emit("close");
        reject(error);
      });

      this.wsClient.on("close", () => {
        this.emit("close");
      });
    });
  }

  sendJson(message) {
    if (this.wsClient && this.wsClient.readyState === WebSocket.OPEN) {
      this.wsClient.send(JSON.stringify(message));
    }
  }

  sendAudio(opus, timestamp) {
    if (this.wsClient && this.wsClient.readyState === WebSocket.OPEN) {
      // Send raw Opus data directly without header
      // This avoids the need to strip headers in xiaozhi-server
      this.wsClient.send(opus, { binary: true });
    }
  }

  isAlive() {
    return this.wsClient && this.wsClient.readyState === WebSocket.OPEN;
  }

  close() {
    if (this.wsClient) {
      this.wsClient.close();
      this.wsClient = null;
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
    console.log(
      `🔐 Encrypting: payload=${payload.length}B, timestamp=${timestamp}, seq=${this.udp.localSequence}`
    );
    console.log(`🔐 Header: ${header.toString("hex")}`);
    console.log(`🔐 Key: ${this.udp.key.toString("hex")}`);
    console.log(
      `🔐 Payload first 8 bytes: ${payload.subarray(0, 8).toString("hex")}`
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
    console.log(
      `🔐 Encrypted first 8 bytes: ${encryptedPayload
        .subarray(0, 8)
        .toString("hex")}`
    );
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

    this.bridge = new WebSocketBridge(
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
      console.log(
        `Call started: ${this.clientId} Protocol: ${json.version} ${this.bridge.chatServer}`
      );
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

    this.bridge.sendJson(json);
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
      debug(
        `Received UDP ping message: ${payloadStr} from ${rinfo.address}:${rinfo.port}`
      );
      // Ping message received, connection is now established
      return;
    }

    this.bridge.sendAudio(payload, timestamp);
    this.udp.remoteSequence = sequence;
  }

  isAlive() {
    return this.bridge && this.bridge.isAlive();
  }
}

class MQTTServer {
  constructor() {
    this.mqttPort = parseInt(process.env.MQTT_PORT) || 1883;
    this.udpPort = parseInt(process.env.UDP_PORT) || this.mqttPort;
    this.publicIp = process.env.PUBLIC_IP || "broker.emqx.io";
    this.connections = new Map(); // clientId -> MQTTConnection
    this.keepAliveTimer = null;
    this.keepAliveCheckInterval = 1000; // Check every 1 second by default
    this.headerBuffer = Buffer.alloc(16);
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
    this.mqttServer = net.createServer((socket) => {
      const connectionId = this.generateNewConnectionId();
      debug(`New client connection: ${connectionId}`);
      new MQTTConnection(socket, connectionId, this);
    });

    this.mqttServer.listen(this.mqttPort, "0.0.0.0", () => {
      console.warn(
        `MQTT server listening on port ${this.mqttPort} (all interfaces)`
      );
    });

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
        console.log(
          `Connections: ${this.connections.size}, Active: ${activeCount}`
        );
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
      console.warn("Received incomplete UDP header", rinfo);
      return;
    }

    try {
      const type = message.readUInt8(0);
      if (type !== 1) return;

      const payloadLength = message.readUInt16BE(2);
      if (message.length < 16 + payloadLength) return;

      const connectionId = message.readUInt32BE(4);
      const connection = this.connections.get(connectionId);
      if (!connection) return;

      const timestamp = message.readUInt32BE(8);
      const sequence = message.readUInt32BE(12);
      connection.onUdpMessage(
        rinfo,
        message,
        payloadLength,
        timestamp,
        sequence
      );
    } catch (error) {
      console.error("UDP message processing error:", error);
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

    if (this.udpServer) {
      this.udpServer.close();
      this.udpServer = null;
      console.warn("UDP server stopped");
    }

    // Close MQTT server
    if (this.mqttServer) {
      this.mqttServer.close();
      this.mqttServer = null;
      console.warn("MQTT server stopped");
    }

    process.exit(0);
  }
}

// Create and start server
const server = new MQTTServer();
server.start();

process.on("SIGINT", () => {
  console.warn("Received SIGINT signal, starting shutdown");
  server.stop();
});
