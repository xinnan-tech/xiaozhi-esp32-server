// 反馈系统 API 调用模块
// API 走相对路径（同源请求，不会有 CORS 和混合内容问题）
//
// 架构（FRP 单端口模式）:
//   外网 https://feedback.new123.vip
//     → FRP 隧道 → 本地 8007 (start.py)
//       ├─ /api/v1/*   → 反代到 127.0.0.1:8009 (feedback-backend)
//       ├─ /xiaozhi/*  → 反代到 127.0.0.1:8002 (Java)
//       └─ /         → H5 静态文件
//
// 本地开发时（端口 8007 直连）和生产环境（FRP+域名）使用同一套相对路径配置

const FEEDBACK_API_BASE = window.location.origin + '/api/v1';

// WebSocket 走 OTA 返回的地址（带 token），由 connectVoice 处理
// 生产环境如果 WebSocket 也要走 FRP，需要 OTA 返回 wss://feedback.new123.vip/ws/ 这种地址
const WS_BASE = (window.location.protocol === 'https:' ? 'wss:' : 'ws:')
    + '//' + window.location.host + '/ws';

export { FEEDBACK_API_BASE, WS_BASE };

export const FeedbackAPI = {
    // 通过6位码查询门店信息
    async getStoreByCode(storeCode) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/store/${storeCode}`);
            const data = await res.json();
            if (data.code === 0) {
                return { success: true, data: data.data };
            }
            return { success: false, message: data.msg || '门店查询失败' };
        } catch (e) {
            console.error('门店查询失败:', e);
            return { success: false, message: '门店不存在或网络错误' };
        }
    },

    // 获取门店下的员工列表
    async getEmployees(storeId) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/employees/${storeId}`);
            const data = await res.json();
            if (data.code === 0) {
                return { success: true, data: data.data || [] };
            }
            return { success: false, message: data.msg || '获取员工列表失败' };
        } catch (e) {
            console.error('员工列表查询失败:', e);
            return { success: false, message: '网络错误' };
        }
    },

    // 初始化设备绑定 - 返回 deviceMac、otaUrl、agentId、otaResult
    async deviceInit(storeId, employeeId) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/device-init`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storeId, employeeId })
            });
            const data = await res.json();
            if (data.code === 0) {
                return { success: true, data: data.data };
            }
            throw new Error(data.msg);
        } catch (e) {
            console.error('设备初始化失败:', e);
            // fallback: 前端自己生成 MAC（注意：没有 otaResult，需要在语音页重新获取）
            let mac = localStorage.getItem('feedback_device_mac');
            if (!mac) {
                const hex = '0123456789ABCDEF';
                mac = 'FB';
                for (let i = 0; i < 5; i++) {
                    mac += ':' + hex.charAt(Math.floor(Math.random()*16)) + hex.charAt(Math.floor(Math.random()*16));
                }
                localStorage.setItem('feedback_device_mac', mac);
            }
            return {
                success: true,
                data: {
                    deviceMac: mac,
                    // 没有 otaResult，connectVoice 会在语音页重新调用 OTA
                }
            };
        }
    },

    // 保存反馈记录 → feedback-backend
    async saveRecord(recordData) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/record`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(recordData)
            });
            const data = await res.json();
            return { success: data.code === 0 };
        } catch (e) {
            console.error('保存记录失败:', e);
            return { success: false };
        }
    },

    // 调用反馈AI处理 → feedback-backend（3步 LLM Pipeline）
    async processFeedback(processData) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/process`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(processData)
            });
            const data = await res.json();
            if (data.code === 0 && data.data && data.data.success) {
                return { success: true, data: data.data };
            }
            return { success: false, message: (data.data && data.data.message) || data.msg || 'AI处理失败' };
        } catch (e) {
            console.error('AI处理连接失败:', e);
            return { success: false, message: 'AI处理服务连接失败' };
        }
    },

    // 预约页初始化：门店、技师、当天空档
    async appointmentBootstrap(storeCode, date, durationMinutes = 60) {
        try {
            const params = new URLSearchParams({ storeCode, durationMinutes: String(durationMinutes) });
            if (date) params.set('date', date);
            const res = await fetch(`${FEEDBACK_API_BASE}/public/appointment/bootstrap?${params.toString()}`);
            const data = await res.json();
            return { success: data.code === 0, data: data.data, message: data.msg };
        } catch (e) {
            console.error('预约初始化失败:', e);
            return { success: false, message: '预约初始化失败' };
        }
    },

    // 查询预约空档
    async getAppointmentAvailability(storeCode, date, employeeId, durationMinutes = 60) {
        try {
            const params = new URLSearchParams({ storeCode, date, durationMinutes: String(durationMinutes) });
            if (employeeId) params.set('employeeId', employeeId);
            const res = await fetch(`${FEEDBACK_API_BASE}/public/appointment/availability?${params.toString()}`);
            const data = await res.json();
            return { success: data.code === 0, data: data.data, message: data.msg };
        } catch (e) {
            console.error('查询预约空档失败:', e);
            return { success: false, message: '查询预约空档失败' };
        }
    },

    // 根据手机号查询客户可预约项目
    async getAppointmentMemberProducts(storeCode, phone) {
        try {
            const params = new URLSearchParams({ storeCode, phone });
            const res = await fetch(`${FEEDBACK_API_BASE}/public/appointment/member-products?${params.toString()}`);
            const data = await res.json();
            return { success: data.code === 0, data: data.data, message: data.msg, code: data.code };
        } catch (e) {
            console.error('查询客户项目失败:', e);
            return { success: false, message: '查询客户项目失败' };
        }
    },

    // 查询我的未完成预约
    async getMyAppointments(storeCode, phone) {
        try {
            const params = new URLSearchParams({ storeCode, phone });
            const res = await fetch(`${FEEDBACK_API_BASE}/public/appointment/my?${params.toString()}`);
            const data = await res.json();
            return { success: data.code === 0, data: data.data, message: data.msg, code: data.code };
        } catch (e) {
            console.error('查询我的预约失败:', e);
            return { success: false, message: '查询我的预约失败' };
        }
    },

    async cancelAppointmentPublic(payload) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/appointment/cancel`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            const data = await res.json();
            return { success: data.code === 0, data: data.data, message: data.msg, code: data.code };
        } catch (e) {
            console.error('取消预约失败:', e);
            return { success: false, message: '取消预约失败' };
        }
    },

    async rescheduleAppointmentPublic(payload) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/appointment/reschedule`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            const data = await res.json();
            return { success: data.code === 0, data: data.data, message: data.msg, code: data.code };
        } catch (e) {
            console.error('改约失败:', e);
            return { success: false, message: '改约失败' };
        }
    },


    // 提交预约（后端会实时二次校验冲突）
    async bookAppointment(payload) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/appointment/book`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            return { success: data.code === 0, data: data.data, message: data.msg, code: data.code };
        } catch (e) {
            console.error('提交预约失败:', e);
            return { success: false, message: '提交预约失败' };
        }
    },

    // OTA连接 - 通过 feedback-backend 代理转发到 Java manager-api（避免浏览器 CORS）
    async connectOTA(deviceMac, clientId) {
        try {
            const res = await fetch(`${FEEDBACK_API_BASE}/public/ota/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Device-Id': deviceMac,
                    'Client-Id': clientId || 'feedback_client'
                },
                body: JSON.stringify({
                    version: 0,
                    uuid: '',
                    application: {
                        name: 'xiaozhi-feedback-h5',
                        version: '1.0.0',
                        compile_time: '2026-06-10 10:00:00',
                        idf_version: '4.4.3',
                        elf_sha256: '1234567890abcdef1234567890abcdef1234567890abcdef'
                    },
                    ota: { label: 'xiaozhi-feedback-h5' },
                    board: {
                        type: '反馈H5',
                        ssid: 'xiaozhi-feedback-h5',
                        rssi: 0,
                        channel: 0,
                        ip: '192.168.1.1',
                        mac: deviceMac
                    },
                    flash_size: 0,
                    minimum_free_heap_size: 0,
                    mac_address: deviceMac,
                    chip_model_name: '',
                    chip_info: { model: 0, cores: 0, revision: 0, features: 0 },
                    partition_table: [{ label: '', type: 0, subtype: 0, address: 0, size: 0 }]
                })
            });
            return await res.json();
        } catch (e) {
            console.error('OTA连接失败:', e);
            return null;
        }
    }
};
