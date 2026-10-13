import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
    // Bound devices
    getAgentBindDevices(agentId, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device/bind/${agentId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                RequestService.clearRequestTime();
                if (failCallback) {
                    failCallback(err);
                }
            })
            .networkFail((err) => {
                console.error('Failed to get device list:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentBindDevices(agentId, callback, failCallback);
                });
            }).send();
    },
    // Unbind device
    unbindDevice(device_id, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device/unbind`)
            .method('POST')
            .data({ deviceId: device_id })
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                RequestService.clearRequestTime();
                if (failCallback) {
                    failCallback(err);
                }
            })
            .networkFail((err) => {
                console.error('Failed to unbind device:', err);
                RequestService.reAjaxFun(() => {
                    this.unbindDevice(device_id, callback, failCallback);
                });
            }).send();
    },
    // Bind device
    bindDevice(agentId, deviceCode, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device/bind/${agentId}/${deviceCode}`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                RequestService.clearRequestTime();
                if (failCallback) {
                    failCallback(err);
                }
            })
            .networkFail((err) => {
                console.error('Failed to bind device:', err);
                RequestService.reAjaxFun(() => {
                    this.bindDevice(agentId, deviceCode, callback, failCallback);
                });
            }).send();
    },
    updateDeviceInfo(id, payload, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device/update/${id}`)
            .method('PUT')
            .data(payload)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                RequestService.clearRequestTime();
                if (failCallback) {
                    failCallback(err);
                }
            })
            .networkFail((err) => {
                console.error('Failed to update OTA status:', err)
                this.$message.error(err.msg || 'Failed to update OTA status')
                RequestService.reAjaxFun(() => {
                    this.updateDeviceInfo(id, payload, callback, failCallback)
                })
            }).send()
    },
    // Manually add device
    manualAddDevice(params, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device/manual-add`)
            .method('POST')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                RequestService.clearRequestTime();
                if (failCallback) {
                    failCallback(err);
                }
            })
            .networkFail((err) => {
                console.error('Failed to manually add device:', err);
                RequestService.reAjaxFun(() => {
                    this.manualAddDevice(params, callback, failCallback);
                });
            }).send();
    },
    // Get device status
    getDeviceStatus(agentId, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device/bind/${agentId}`)
            .method('POST')
            .data({}) // Send empty object as request body
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Failed to get device status:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceStatus(agentId, callback, failCallback);
                });
            }).send();
    },
    // Send device command
    sendDeviceCommand(deviceId, mcpData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device/commands/${deviceId}`)
            .method('POST')
            .data(mcpData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Failed to send device command:', err);
                RequestService.reAjaxFun(() => {
                    this.sendDeviceCommand(deviceId, mcpData, callback);
                });
            }).send();
    },
}