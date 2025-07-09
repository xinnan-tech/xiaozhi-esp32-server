#!/usr/bin/env node
/**
 * MQTT签名密钥生成器
 * 用于生成MQTT_SIGNATURE_KEY环境变量
 */

const crypto = require('crypto');

function generateSecureKey(length = 32) {
    // 生成随机字节
    const randomBytes = crypto.randomBytes(length);
    
    // 转换为base64字符串
    const base64Key = randomBytes.toString('base64');
    
    return base64Key;
}

function generateHexKey(length = 32) {
    // 生成随机字节
    const randomBytes = crypto.randomBytes(length);
    
    // 转换为十六进制字符串
    const hexKey = randomBytes.toString('hex');
    
    return hexKey;
}

function generateUUIDKey() {
    // 使用UUID v4作为密钥
    const uuid = crypto.randomUUID();
    return uuid;
}

console.log('='.repeat(60));
console.log('MQTT签名密钥生成器');
console.log('='.repeat(60));

console.log('\n1. Base64格式密钥 (推荐):');
const base64Key = generateSecureKey();
console.log(`   ${base64Key}`);

console.log('\n2. 十六进制格式密钥:');
const hexKey = generateHexKey();
console.log(`   ${hexKey}`);

console.log('\n3. UUID格式密钥:');
const uuidKey = generateUUIDKey();
console.log(`   ${uuidKey}`);

console.log('\n='.repeat(60));
console.log('使用方法:');
console.log('='.repeat(60));
console.log('\n在Windows PowerShell中设置环境变量:');
console.log(`$env:MQTT_SIGNATURE_KEY="${base64Key}"`);

console.log('\n在Windows CMD中设置环境变量:');
console.log(`set MQTT_SIGNATURE_KEY=${base64Key}`);

console.log('\n在Linux/macOS中设置环境变量:');
console.log(`export MQTT_SIGNATURE_KEY="${base64Key}"`);

console.log('\n在.env文件中设置:');
console.log(`MQTT_SIGNATURE_KEY=${base64Key}`);

console.log('\n='.repeat(60));
console.log('注意事项:');
console.log('='.repeat(60));
console.log('1. 请妥善保管生成的密钥，不要泄露给他人');
console.log('2. 在生产环境中，建议使用更长的密钥 (64字节)');
console.log('3. 密钥设置后需要重启MQTT服务器才能生效');
console.log('4. 客户端连接时需要使用相同的密钥生成密码签名');

// 如果提供了命令行参数，生成指定长度的密钥
if (process.argv[2]) {
    const customLength = parseInt(process.argv[2]);
    if (customLength > 0) {
        console.log(`\n自定义长度密钥 (${customLength}字节):`);
        console.log(`   ${generateSecureKey(customLength)}`);
    }
}