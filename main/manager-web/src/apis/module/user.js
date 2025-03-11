import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    // 登录
    login(loginForm, callback) {
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/login`).method('POST')
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
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/info`).method('GET')
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
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/device/bind`).method('GET')
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
    }
}
