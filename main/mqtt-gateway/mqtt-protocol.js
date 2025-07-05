const debug = require('debug')('mqtt-server');
const EventEmitter = require('events');

// MQTT 固定头部的类型
const PacketType = {
    CONNECT: 1,
    CONNACK: 2,
    PUBLISH: 3,
    SUBSCRIBE: 8,
    SUBACK: 9,
    PINGREQ: 12,
    PINGRESP: 13,
    DISCONNECT: 14    // 添加 DISCONNECT
};

/**
 * MQTT协议处理类
 * 负责MQTT协议的解析和封装，以及心跳维持
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
     * 设置Socket事件处理
     */
    setupSocketHandlers() {
        this.socket.on('data', (data) => {
            this.lastActivity = Date.now();
            this.buffer = Buffer.concat([this.buffer, data]);
            this.processBuffer();
        });

        this.socket.on('close', () => {
            this.emit('close');
        });

        this.socket.on('error', (err) => {
            this.emit('error', err);
        });
    }

    /**
     * 处理缓冲区中的所有完整消息
     */
    processBuffer() {
        // 持续处理缓冲区中的数据，直到没有完整的消息可以处理
        while (this.buffer.length > 0) {
            // 至少需要2个字节才能开始解析（1字节固定头部 + 至少1字节的剩余长度）
            if (this.buffer.length < 2) return;

            try {
                // 获取消息类型
                const firstByte = this.buffer[0];
                const type = (firstByte >> 4);
                
                // 解析剩余长度
                const { value: remainingLength, bytesRead } = this.decodeRemainingLength(this.buffer);
                
                // 计算整个消息的长度
                const messageLength = 1 + bytesRead + remainingLength;
                
                // 检查缓冲区中是否有完整的消息
                if (this.buffer.length < messageLength) {
                    // 消息不完整，等待更多数据
                    return;
                }
                
                // 提取完整的消息
                const message = this.buffer.subarray(0, messageLength);
                if (!this.isConnected && type !== PacketType.CONNECT) {
                    debug('未连接时收到非CONNECT消息，关闭连接');
                    this.socket.end();
                    return;
                }
                
                // 根据消息类型处理
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
                        debug('未处理的包类型:', type, message);
                        this.emit('protocolError', new Error(`未处理的包类型: ${type}`));
                }
                
                // 从缓冲区中移除已处理的消息
                this.buffer = this.buffer.subarray(messageLength);
                
            } catch (err) {
                // 如果解析出错，可能是数据不完整，等待更多数据
                if (err.message === 'Malformed Remaining Length') {
                    return;
                }
                // 其他错误可能是协议错误，清空缓冲区并发出错误事件
                this.buffer = Buffer.alloc(0);
                this.emit('protocolError', err);
                return;
            }
        }
    }

    /**
     * 解析MQTT报文中的Remaining Length字段
     * @param {Buffer} buffer - 消息缓冲区
     * @returns {{value: number, bytesRead: number}} 包含解析的值和读取的字节数
     */
    decodeRemainingLength(buffer) {
        let multiplier = 1;
        let value = 0;
        let bytesRead = 0;
        let digit;

        do {
            if (bytesRead >= 4 || bytesRead >= buffer.length - 1) {
                throw new Error('Malformed Remaining Length');
            }
            
            digit = buffer[bytesRead + 1];
            bytesRead++;
            
            value += (digit & 127) * multiplier;
            multiplier *= 128;
            
        } while ((digit & 128) !== 0);

        return { value, bytesRead };
    }

    /**
     * 编码MQTT报文中的Remaining Length字段
     * @param {number} length - 要编码的长度值
     * @returns {{bytes: Buffer, bytesLength: number}} 包含编码后的字节和字节长度
     */
    encodeRemainingLength(length) {
        let digit;
        const bytes = Buffer.alloc(4); // 最多4个字节
        let bytesLength = 0;
        
        do {
            digit = length % 128;
            length = Math.floor(length / 128);
            // 如果还有更多字节，设置最高位
            if (length > 0) {
                digit |= 0x80;
            }
            bytes[bytesLength++] = digit;
        } while (length > 0 && bytesLength < 4);
        
        return { bytes, bytesLength };
    }

    /**
     * 解析CONNECT消息
     * @param {Buffer} message - 完整的CONNECT消息
     */
    parseConnect(message) {
        // 解析剩余长度
        const { value: remainingLength, bytesRead } = this.decodeRemainingLength(message);
        
        // 固定头部之后的位置 (MQTT固定头部第一个字节 + Remaining Length字段的字节)
        const headerLength = 1 + bytesRead;
        
        // 从可变头部开始位置读取协议名长度
        const protocolLength = message.readUInt16BE(headerLength);
        const protocol = message.toString('utf8', headerLength + 2, headerLength + 2 + protocolLength);
        
        // 更新位置指针，跳过协议名
        let pos = headerLength + 2 + protocolLength;
        
        // 协议级别，4为MQTT 3.1.1
        const protocolLevel = message[pos];
        
        // 检查协议版本
        if (protocolLevel !== 4) {  // 4 表示 MQTT 3.1.1
            debug('不支持的协议版本:', protocolLevel);
            // 发送 CONNACK，使用不支持的协议版本的返回码 (0x01)
            this.sendConnack(1, false);
            // 关闭连接
            this.socket.end();
            return;
        }
        
        pos += 1;
        
        // 连接标志
        const connectFlags = message[pos];
        const hasUsername = (connectFlags & 0x80) !== 0;
        const hasPassword = (connectFlags & 0x40) !== 0;
        const cleanSession = (connectFlags & 0x02) !== 0;
        pos += 1;
        
        // 保持连接时间
        const keepAlive = message.readUInt16BE(pos);
        pos += 2;
        
        // 解析 clientId
        const clientIdLength = message.readUInt16BE(pos);
        pos += 2;
        const clientId = message.toString('utf8', pos, pos + clientIdLength);
        pos += clientIdLength;

        // 解析 username（如果存在）
        let username = '';
        if (hasUsername) {
            const usernameLength = message.readUInt16BE(pos);
            pos += 2;
            username = message.toString('utf8', pos, pos + usernameLength);
            pos += usernameLength;
        }

        // 解析 password（如果存在）
        let password = '';
        if (hasPassword) {
            const passwordLength = message.readUInt16BE(pos);
            pos += 2;
            password = message.toString('utf8', pos, pos + passwordLength);
            pos += passwordLength;
        }

        // 设置心跳间隔（客户端指定的keepAlive值的1.5倍，单位为秒）
        this.keepAliveInterval = keepAlive * 1000 * 1.5;
        
        // 发送 CONNACK
        this.sendConnack(0, false);
        
        // 标记为已连接
        this.isConnected = true;
        
        // 发出连接事件
        this.emit('connect', {
            clientId,
            protocol,
            protocolLevel,
            keepAlive,
            username,
            password,
            cleanSession
        });
    }

    /**
     * 解析PUBLISH消息
     * @param {Buffer} message - 完整的PUBLISH消息
     */
    parsePublish(message) {
        // 从第一个字节中提取QoS级别(bits 1-2)
        const firstByte = message[0];
        const qos = (firstByte & 0x06) >> 1;  // 0x06 是二进制 00000110，用于掩码提取QoS位
        const dup = (firstByte & 0x08) !== 0;  // 0x08 是二进制 00001000，用于掩码提取DUP标志
        const retain = (firstByte & 0x01) !== 0;  // 0x01 是二进制 00000001，用于掩码提取RETAIN标志
        
        // 使用通用方法解析剩余长度
        const { value: remainingLength, bytesRead } = this.decodeRemainingLength(message);
        
        // 固定头部之后的位置 (MQTT固定头部第一个字节 + Remaining Length字段的字节)
        const headerLength = 1 + bytesRead;
        
        // 解析主题
        const topicLength = message.readUInt16BE(headerLength);
        const topic = message.toString('utf8', headerLength + 2, headerLength + 2 + topicLength);
        
        // 对于QoS > 0，包含消息ID
        let packetId = null;
        let payloadStart = headerLength + 2 + topicLength;
        
        if (qos > 0) {
            packetId = message.readUInt16BE(payloadStart);
            payloadStart += 2;
        }
        
        // 解析有效载荷
        const payload = message.slice(payloadStart).toString('utf8');
        
        // 发出发布事件
        this.emit('publish', {
            topic,
            payload,
            qos,
            dup,
            retain,
            packetId
        });
    }

    /**
     * 解析SUBSCRIBE消息
     * @param {Buffer} message - 完整的SUBSCRIBE消息
     */
    parseSubscribe(message) {
        const packetId = message.readUInt16BE(2);
        const topicLength = message.readUInt16BE(4);
        const topic = message.toString('utf8', 6, 6 + topicLength);
        const qos = message[6 + topicLength]; // QoS值
        
        // 发出订阅事件
        this.emit('subscribe', {
            packetId,
            topic,
            qos
        });
    }

    /**
     * 解析PINGREQ消息
     * @param {Buffer} message - 完整的PINGREQ消息
     */
    parsePingReq(message) {
        debug('收到心跳请求');
        
        // 发送 PINGRESP
        this.sendPingResp();
        
        debug('已发送心跳响应');
    }

    /**
     * 解析DISCONNECT消息
     * @param {Buffer} message - 完整的DISCONNECT消息
     */
    parseDisconnect(message) {
        // 标记为未连接
        this.isConnected = false;
        
        // 发出断开连接事件
        this.emit('disconnect');
        
        // 关闭 socket
        this.socket.end();
    }

    /**
     * 发送CONNACK消息
     * @param {number} returnCode - 返回码
     * @param {boolean} sessionPresent - 会话存在标志
     */
    sendConnack(returnCode = 0, sessionPresent = false) {
        if (!this.socket.writable) return;
        
        const packet = Buffer.from([
            PacketType.CONNACK << 4,
            2,  // Remaining length
            sessionPresent ? 1 : 0,  // Connect acknowledge flags
            returnCode  // Return code
        ]);
        
        this.socket.write(packet);
    }

    /**
     * 发送PUBLISH消息
     * @param {string} topic - 主题
     * @param {string} payload - 有效载荷
     * @param {number} qos - QoS级别
     * @param {boolean} dup - 重复标志
     * @param {boolean} retain - 保留标志
     * @param {number} packetId - 包ID（仅QoS > 0时需要）
     */
    sendPublish(topic, payload, qos = 0, dup = false, retain = false, packetId = null) {
        if (!this.isConnected || !this.socket.writable) return;
        
        const topicLength = Buffer.byteLength(topic);
        const payloadLength = Buffer.byteLength(payload);
        
        // 计算剩余长度
        let remainingLength = 2 + topicLength + payloadLength;
        
        // 如果QoS > 0，需要包含包ID
        if (qos > 0 && packetId) {
            remainingLength += 2;
        }
        
        // 编码可变长度
        const { bytes: remainingLengthBytes, bytesLength: remainingLengthSize } = this.encodeRemainingLength(remainingLength);
        
        // 分配缓冲区：固定头部(1字节) + 可变长度字段 + 剩余长度值
        const packet = Buffer.alloc(1 + remainingLengthSize + remainingLength);
        
        // 写入固定头部
        let firstByte = PacketType.PUBLISH << 4;
        if (dup) firstByte |= 0x08;
        if (qos > 0) firstByte |= (qos << 1);
        if (retain) firstByte |= 0x01;
        
        packet[0] = firstByte;
        
        // 写入可变长度字段
        remainingLengthBytes.copy(packet, 1, 0, remainingLengthSize);
        
        // 写入主题长度和主题
        const variableHeaderStart = 1 + remainingLengthSize;
        packet.writeUInt16BE(topicLength, variableHeaderStart);
        packet.write(topic, variableHeaderStart + 2);
        
        // 如果QoS > 0，写入包ID
        let payloadStart = variableHeaderStart + 2 + topicLength;
        if (qos > 0 && packetId) {
            packet.writeUInt16BE(packetId, payloadStart);
            payloadStart += 2;
        }
        
        // 写入有效载荷
        packet.write(payload, payloadStart);
        
        this.socket.write(packet);
        this.lastActivity = Date.now();
    }

    /**
     * 发送SUBACK消息
     * @param {number} packetId - 包ID
     * @param {number} returnCode - 返回码
     */
    sendSuback(packetId, returnCode = 0) {
        if (!this.isConnected || !this.socket.writable) return;
        
        const packet = Buffer.from([
            PacketType.SUBACK << 4,
            3,                  // Remaining length
            packetId >> 8,     // Packet ID MSB
            packetId & 0xFF,   // Packet ID LSB
            returnCode         // Return code
        ]);
        
        this.socket.write(packet);
        this.lastActivity = Date.now();
    }

    /**
     * 发送PINGRESP消息
     */
    sendPingResp() {
        if (!this.isConnected || !this.socket.writable) return;
        
        const packet = Buffer.from([
            PacketType.PINGRESP << 4,  // Fixed header
            0                          // Remaining length
        ]);
        
        this.socket.write(packet);
        this.lastActivity = Date.now();
    }

    /**
     * 获取上次活动时间
     */
    getLastActivity() {
        return this.lastActivity;
    }

    /**
     * 获取心跳间隔
     */
    getKeepAliveInterval() {
        return this.keepAliveInterval;
    }

    /**
     * 清空缓冲区
     */
    clearBuffer() {
        this.buffer = Buffer.alloc(0);
    }

    /**
     * 关闭连接
     */
    close() {
        if (this.socket.writable) {
            this.socket.end();
        }
    }
}

// 导出 PacketType 和 MQTTProtocol 类
module.exports = {
    PacketType,
    MQTTProtocol
}; 