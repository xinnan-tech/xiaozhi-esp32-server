import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    // 登录
    login(loginForm, callback) {
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/login`)
            .method('POST')
            .data(loginForm)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.login(loginForm, callback)
                })
            }).send()
    },
    // 获取用户信息
    getUserInfo(callback) {
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/info`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.getUserInfo()
                })
            }).send()
    },
    // 获取设备信息
    getHomeList(callback) {
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/device/bind`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.getUserInfo()
                })
            }).send()
    },
    // 解绑设备
    unbindDevice(device_id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/device/unbind/${device_id}`)
            .method('PUT')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                  this.unbindDevice(device_id, callback);
                });
              }).send()
    },
    // 绑定设备
    bindDevice(deviceCode, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/device/bind/${deviceCode}`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('绑定设备失败:', err);
                RequestService.reAjaxFun(() => {
                    this.bindDevice(deviceCode, callback);
                });
            }).send();
    },
    // 保存设备配置
    saveDeviceConfig(device_id, configData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/configDevice/${device_id}`)
            .method('PUT')
            .data(configData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('保存配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.saveDeviceConfig(device_id, configData, callback);
                });
            }).send();
    },
    // 获取设备配置
    getDeviceConfig(device_id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/configDevice/${device_id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('获取配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceConfig(device_id, callback);
                });
            }).send();
    },
    // 获取所有模型名称
    getModelNames(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/models/names`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.getModelNames(callback);
                });
            }).send();
    },

    // 获取模型音色
    getModelVoices(modelName, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/models/${modelName}/voices`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.getModelVoices(modelName, callback);
                });
            }).send();
    },

}
