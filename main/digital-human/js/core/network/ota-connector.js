import { log } from '../../utils/logger.js?v=0205';

// 子协议值必须是合法的 token 字符，冒号不在其中，所以 Device-Id 去掉分隔符。
// OTA 请求头与 websocket 子协议必须用同一个值，否则 token 签名对不上
export function normalizeDeviceId(deviceId) {
    return (deviceId || '').replace(/[:-_]/g, '').toLowerCase();
}

// WebSocket 连接
export async function webSocketConnect(otaUrl, config) {

    if (!validateConfig(config)) {
        return;
    }

    // 发送OTA请求并获取返回的websocket信息
    const otaResult = await sendOTA(otaUrl, config);
    if (!otaResult) {
        log('无法从OTA服务器获取信息', 'error');
        return;
    }

    // 从OTA响应中提取websocket信息
    const { websocket } = otaResult;
    if (!websocket || !websocket.url) {
        log('OTA响应中缺少websocket信息', 'error');
        return;
    }

    // token 存下来下次续签用：激活码用掉即作废，
    // 不存的话第二次点连接必然被服务端拒
    const issuedToken = (websocket.token || otaResult.mqtt?.token || '').replace(/^Bearer\s+/i, '');
    if (issuedToken) {
        sessionStorage.setItem('xz_tester_token', issuedToken);
        localStorage.setItem('xz_tester_token', issuedToken);
    }

    // 使用OTA返回的websocket URL
    const connUrl = new URL(websocket.url);

    // 浏览器不能自定义 websocket 请求头，凭证和设备标识改走子协议头：
    // xiaozhi, t-<token>, d-<deviceId>, c-<clientId>，服务端只回显 xiaozhi。
    // 不再拼进 URL 查询串，那会原样落进反代访问日志
    const subprotocols = [
        'xiaozhi',
        `d-${normalizeDeviceId(config.deviceId)}`,
        `c-${config.clientId}`
    ];
    if (websocket.token) {
        const token = websocket.token.startsWith('Bearer ')
            ? websocket.token.slice(7)
            : websocket.token;
        subprotocols.splice(1, 0, `t-${token}`);
    }

    const wsurl = connUrl.toString()

    log(`正在连接: ${wsurl}`, 'info');

    if (wsurl) {
        document.getElementById('serverUrl').value = wsurl;
    }

    return new WebSocket(connUrl.toString(), subprotocols);
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

// OTA发送请求，验证状态，并返回响应数据
async function sendOTA(otaUrl, config) {
    try {
        // 有 token 用 token 续签，没有才用激活码换首次 token
        const credential = config.token || config.activationCode;
        const res = await fetch(otaUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Device-Id': normalizeDeviceId(config.deviceId),
                'Client-Id': config.clientId,
                ...(credential ? { 'Authorization': `Bearer ${credential}` } : {})
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

        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);

        const result = await res.json();
        return result; // 返回完整的响应数据
    } catch (err) {
        // 跨域失败在浏览器里是不透明的：fetch 直接抛 TypeError，
        // 拿不到状态码，也看不出是服务端没回跨域头还是服务没起来。
        // 页面知道自己的来源，直接点名让人去加白名单
        if (err instanceof TypeError) {
            log(`请求 ${otaUrl} 被浏览器拦下（跨域）。把 ${window.location.origin} 加到服务端的 server.cors.allowed_origins 里`, 'error');
        } else {
            log(`OTA请求失败: ${err.message}`, 'error');
        }
        return null; // 失败返回null
    }
}