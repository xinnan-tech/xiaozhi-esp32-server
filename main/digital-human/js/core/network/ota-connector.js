import { log } from '../../utils/logger.js?v=0205';

// WebSocket 连接
export async function webSocketConnect(otaUrl, config) {

    if (!validateConfig(config)) {
        return;
    }

    // 发送OTA请求并获取返回的websocket信息（请求失败时 sendOTA 抛出带地址和原因的错误）
    const otaResult = await sendOTA(otaUrl, config);

    // 从OTA响应中提取websocket信息
    const websocket = otaResult && otaResult.websocket;
    if (!websocket || !websocket.url) {
        throw new Error(`OTA地址 ${otaUrl} 的响应中缺少websocket信息`);
    }

    // 使用OTA返回的websocket URL
    let connUrl = new URL(websocket.url);

    // 添加token参数（从OTA响应中获取）
    if (websocket.token) {
        if (websocket.token.startsWith("Bearer ")) {
            connUrl.searchParams.append('authorization', websocket.token);
        } else {
            connUrl.searchParams.append('authorization', 'Bearer ' + websocket.token);
        }
    }

    // 添加认证参数（保持原有逻辑）
    connUrl.searchParams.append('device-id', config.deviceId);
    connUrl.searchParams.append('client-id', config.clientId);

    const wsurl = connUrl.toString()

    log(`正在连接: ${wsurl}`, 'info');

    if (wsurl) {
        document.getElementById('serverUrl').value = wsurl;
    }

    return new WebSocket(connUrl.toString());
}

// 验证配置
function validateConfig(config) {
    if (!config.deviceMac) {
        log('设备MAC地址不能为空', 'error');
        return false;
    }
    if (!config.clientId) {
        log('客户端ID不能为空', 'error');
        return false;
    }
    return true;
}

// OTA发送请求，验证状态，并返回响应数据；失败时抛出带地址和排查提示的错误，供页面直接展示
async function sendOTA(otaUrl, config) {
    let res;
    try {
        res = await fetch(otaUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Device-Id': config.deviceId,
                'Client-Id': config.clientId
            },
            body: JSON.stringify({
                version: 0,
                uuid: '',
                application: {
                    name: 'xiaozhi-web-test',
                    version: '1.0.0',
                    compile_time: '2025-04-16 10:00:00',
                    idf_version: '4.4.3',
                    elf_sha256: '1234567890abcdef1234567890abcdef1234567890abcdef'
                },
                ota: { label: 'xiaozhi-web-test' },
                board: {
                    type: config.deviceName,
                    ssid: 'xiaozhi-web-test',
                    rssi: 0,
                    channel: 0,
                    ip: '192.168.1.1',
                    mac: config.deviceMac
                },
                flash_size: 0,
                minimum_free_heap_size: 0,
                mac_address: config.deviceMac,
                chip_model_name: '',
                chip_info: { model: 0, cores: 0, revision: 0, features: 0 },
                partition_table: [{ label: '', type: 0, subtype: 0, address: 0, size: 0 }]
            })
        });
    } catch (err) {
        throw new Error(describeUnreachableOta(otaUrl));
    }

    if (!res.ok) {
        throw new Error(`OTA地址 ${otaUrl} 返回 ${res.status} ${res.statusText}，请确认地址以 /xiaozhi/ota/ 结尾`);
    }

    try {
        return await res.json(); // 返回完整的响应数据
    } catch (err) {
        throw new Error(`OTA地址 ${otaUrl} 返回的不是JSON，请确认填写的是OTA接口地址`);
    }
}

// 浏览器出于安全原因不区分“连接被拒”“跨域被拦”“路径不存在导致预检失败”等网络错误，这里列出最常见的排查方向
function describeUnreachableOta(otaUrl) {
    const hints = [
        '服务是否已启动',
        '端口是否正确（只运行xiaozhi-server时一般是8003，全模块部署时一般是8002）',
        '路径是否以 /xiaozhi/ota/ 结尾'
    ];
    if (window.location.protocol === 'https:' && otaUrl.startsWith('http:')) {
        hints.push('当前页面是https，浏览器会拦截对http地址的请求');
    }
    return `无法访问OTA地址 ${otaUrl}，请检查：${hints.join('；')}`;
}