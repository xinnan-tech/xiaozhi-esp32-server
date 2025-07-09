require('dotenv').config();
const crypto = require('crypto');


function generatePasswordSignature(content, secretKey) {
    // Create an HMAC object using SHA256 and the secretKey
    const hmac = crypto.createHmac('sha256', secretKey);
    
    // Update the HMAC object with the clientId
    hmac.update(content);
    
    // Generate the HMAC digest in binary format
    const binarySignature = hmac.digest();
    
    // Encode the binary signature to Base64
    const base64Signature = binarySignature.toString('base64');
    
    return base64Signature;
}

function validateMqttCredentials(clientId, username, password) {
    // 验证密码签名
    const signatureKey = process.env.MQTT_SIGNATURE_KEY;
    if (signatureKey) {
        const expectedSignature = generatePasswordSignature(clientId + '|' + username, signatureKey);
        if (password !== expectedSignature) {
            throw new Error('密码签名验证失败');
        }
    } else {
        console.warn('缺少MQTT_SIGNATURE_KEY环境变量，跳过密码签名验证');
    }

    // 验证clientId
    if (!clientId || typeof clientId !== 'string') {
        throw new Error('clientId必须是非空字符串');
    }
    
    // 验证clientId格式（必须包含@@@分隔符）
    const clientIdParts = clientId.split('@@@');
    // 新版本 MQTT 参数
    if (clientIdParts.length !== 3) {
        throw new Error('clientId格式错误，必须包含@@@分隔符');
    }
    
    // 验证username
    if (!username || typeof username !== 'string') {
        throw new Error('username必须是非空字符串');
    }
    
    // 尝试解码username（应该是base64编码的JSON）
    let userData;
    try {
        const decodedUsername = Buffer.from(username, 'base64').toString();
        userData = JSON.parse(decodedUsername);
    } catch (error) {
        throw new Error('username不是有效的base64编码JSON');
    }
    
    // 解析clientId中的信息
    const [groupId, macAddress, uuid] = clientIdParts;
    
    // 如果验证成功，返回解析后的有用信息
    return { 
        groupId,
        macAddress: macAddress.replace(/_/g, ':'),
        uuid,
        userData
    };
}

function generateMqttConfig(groupId, macAddress, uuid, userData) {
    const endpoint = process.env.MQTT_ENDPOINT;
    const signatureKey = process.env.MQTT_SIGNATURE_KEY;
    if (!signatureKey) {
        console.warn('No signature key, skip generating MQTT config');
        return;
    }
    const deviceIdNoColon = macAddress.replace(/:/g, '_');
    const clientId = `${groupId}@@@${deviceIdNoColon}@@@${uuid}`;
    const username = Buffer.from(JSON.stringify(userData)).toString('base64');
    const password = generatePasswordSignature(clientId + '|' + username, signatureKey);
    return {
        endpoint,
        port: 8883,
        client_id: clientId,
        username,
        password,
        publish_topic: 'device-server',
        subscribe_topic: 'null' // 旧版本固件不返回此字段会出错
    }
}

module.exports = {
    generateMqttConfig,
    validateMqttCredentials
}

if (require.main === module) {
    const config = generateMqttConfig('GID_test', '11:22:33:44:55:66', '36c98363-3656-43cb-a00f-8bced2391a90', { ip: '222.222.222.222' });
    console.log('config', config);
    const credentials = validateMqttCredentials(config.client_id, config.username, config.password);
    console.log('credentials', credentials);
}
