// Config management module

// Default wake word list
export const DEFAULT_WAKE_WORDS = 'Alexa\nHi ESP\nJarvis\ncomputer\nHey Willow\nSophia\nHey Wanda\nHi Jolly\nHi Fairy\nHey Printer\nMycroft\nHi Joy\nHi Jason\nAstrolabe\nHey Ily\nBlue Chip\nHi Lily';

// Generate random MAC address
function generateRandomMac() {
    const hexDigits = '0123456789ABCDEF';
    let mac = '';
    for (let i = 0; i < 6; i++) {
        if (i > 0) mac += ':';
        for (let j = 0; j < 2; j++) {
            mac += hexDigits.charAt(Math.floor(Math.random() * 16));
        }
    }
    return mac;
}

// Load config
export function loadConfig() {
    const deviceMacInput = document.getElementById('deviceMac');
    const deviceNameInput = document.getElementById('deviceName');
    const clientIdInput = document.getElementById('clientId');
    const otaUrlInput = document.getElementById('otaUrl');
    const wakewordWsUrlInput = document.getElementById('wakewordWsUrl');
    const wakewordEnabledInput = document.getElementById('wakewordEnabled');
    const wakewordListInput = document.getElementById('wakewordList');

    // Load MAC address from localStorage, generate a new one if missing
    let savedMac = localStorage.getItem('xz_tester_deviceMac');
    if (!savedMac) {
        savedMac = generateRandomMac();
        localStorage.setItem('xz_tester_deviceMac', savedMac);
    }
    deviceMacInput.value = savedMac;

    // Load other configs from localStorage
    const savedDeviceName = localStorage.getItem('xz_tester_deviceName');
    if (savedDeviceName) {
        deviceNameInput.value = savedDeviceName;
    }

    const savedClientId = localStorage.getItem('xz_tester_clientId');
    if (savedClientId) {
        clientIdInput.value = savedClientId;
    }

    const savedOtaUrl = localStorage.getItem('xz_tester_otaUrl');
    if (savedOtaUrl) {
        otaUrlInput.value = savedOtaUrl;
    }

    const savedWakewordWsUrl = localStorage.getItem('xz_tester_wakewordWsUrl');
    if (savedWakewordWsUrl !== null && wakewordWsUrlInput) {
        wakewordWsUrlInput.value = savedWakewordWsUrl;
    }

    const savedWakewordEnabled = localStorage.getItem('xz_tester_wakewordEnabled');
    if (savedWakewordEnabled !== null && wakewordEnabledInput) {
        wakewordEnabledInput.value = savedWakewordEnabled;
    }

    const savedWakewordList = localStorage.getItem('xz_tester_wakewordList');
    if (savedWakewordList !== null && wakewordListInput) {
        wakewordListInput.value = savedWakewordList;
    } else if (wakewordListInput) {
        wakewordListInput.value = DEFAULT_WAKE_WORDS;
    }

    const emojiEnabledInput = document.getElementById('emojiEnabled');
    const savedEmojiEnabled = localStorage.getItem('xz_tester_emojiEnabled');
    if (savedEmojiEnabled !== null && emojiEnabledInput) {
        emojiEnabledInput.value = savedEmojiEnabled;
    }
}

// Save config
export function saveConfig() {
    const deviceMacInput = document.getElementById('deviceMac');
    const deviceNameInput = document.getElementById('deviceName');
    const clientIdInput = document.getElementById('clientId');
    const wakewordWsUrlInput = document.getElementById('wakewordWsUrl');
    const wakewordEnabledInput = document.getElementById('wakewordEnabled');
    const wakewordListInput = document.getElementById('wakewordList');

    localStorage.setItem('xz_tester_deviceMac', deviceMacInput.value);
    localStorage.setItem('xz_tester_deviceName', deviceNameInput.value);
    localStorage.setItem('xz_tester_clientId', clientIdInput.value);
    const emojiEnabledInput = document.getElementById('emojiEnabled');
    if (emojiEnabledInput) {
        localStorage.setItem('xz_tester_emojiEnabled', emojiEnabledInput.value);
    }
    if (wakewordEnabledInput) {
        localStorage.setItem('xz_tester_wakewordEnabled', wakewordEnabledInput.value);
    }
    if (wakewordListInput) {
        localStorage.setItem('xz_tester_wakewordList', wakewordListInput.value);
    }
    if (wakewordWsUrlInput && wakewordWsUrlInput.value.trim()) {
        localStorage.setItem('xz_tester_wakewordWsUrl', wakewordWsUrlInput.value.trim());
    }
}

// Get config value
export function getConfig() {
    // Get value from DOM
    const deviceMac = document.getElementById('deviceMac')?.value.trim() || '';
    const deviceName = document.getElementById('deviceName')?.value.trim() || '';
    const clientId = document.getElementById('clientId')?.value.trim() || '';
    const emojiEnabled = document.getElementById('emojiEnabled')?.value !== 'false';

    return {
        deviceId: deviceMac,  // Use MAC address as deviceId
        deviceName,
        deviceMac,
        clientId,
        emojiEnabled
    };
}

// Save connection URL
export function saveConnectionUrls() {
    const otaUrl = document.getElementById('otaUrl').value.trim();
    const wsUrl = document.getElementById('serverUrl').value.trim();
    localStorage.setItem('xz_tester_otaUrl', otaUrl);
    localStorage.setItem('xz_tester_wsUrl', wsUrl);
}
