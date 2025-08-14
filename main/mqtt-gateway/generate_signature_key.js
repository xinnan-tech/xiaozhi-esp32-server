#!/usr/bin/env node

/**
 * MQTT signature key generator
 * Used to generate MQTT_SIGNATURE_KEY environment variable
 */
const crypto = require('crypto');

function generateSecureKey(length = 32) {
    // Generate random bytes
    const randomBytes = crypto.randomBytes(length);
    // Convert to base64 string
    const base64Key = randomBytes.toString('base64');
    return base64Key;
}

function generateHexKey(length = 32) {
    // Generate random bytes
    const randomBytes = crypto.randomBytes(length);
    // Convert to hexadecimal string
    const hexKey = randomBytes.toString('hex');
    return hexKey;
}

function generateUUIDKey() {
    // Use UUID v4 as key
    const uuid = crypto.randomUUID();
    return uuid;
}

console.log('='.repeat(60));
console.log('MQTT Signature Key Generator');
console.log('='.repeat(60));

console.log('\n1. Base64 format key (recommended):');
const base64Key = generateSecureKey();
console.log(` ${base64Key}`);

console.log('\n2. Hexadecimal format key:');
const hexKey = generateHexKey();
console.log(` ${hexKey}`);

console.log('\n3. UUID format key:');
const uuidKey = generateUUIDKey();
console.log(` ${uuidKey}`);

console.log('\n='.repeat(60));
console.log('Usage:');
console.log('='.repeat(60));

console.log('\nSet environment variable in Windows PowerShell:');
console.log(`$env:MQTT_SIGNATURE_KEY="${base64Key}"`);

console.log('\nSet environment variable in Windows CMD:');
console.log(`set MQTT_SIGNATURE_KEY=${base64Key}`);

console.log('\nSet environment variable in Linux/macOS:');
console.log(`export MQTT_SIGNATURE_KEY="${base64Key}"`);

console.log('\nSet in .env file:');
console.log(`MQTT_SIGNATURE_KEY=${base64Key}`);

console.log('\n='.repeat(60));
console.log('Notes:');
console.log('='.repeat(60));
console.log('1. Please keep the generated key secure and do not leak it to others');
console.log('2. In production environment, longer keys are recommended (64 bytes)');
console.log('3. MQTT server needs to be restarted after setting the key');
console.log('4. Clients need to use the same key to generate password signatures when connecting');

// If command line arguments are provided, generate key with specified length
if (process.argv[2]) {
    const customLength = parseInt(process.argv[2]);
    if (customLength > 0) {
        console.log(`\nCustom length key (${customLength} bytes):`);
        console.log(` ${generateSecureKey(customLength)}`);
    }
}
