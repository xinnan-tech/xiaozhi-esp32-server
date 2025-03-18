import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    //设备列表
    getDeviceList(agent_id, callback) {
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/agent/device/bind/${agent_id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('获取设备列表失败:', err);
            }).send()
    },
    //绑定设备
    bindDevice(agent_id, code, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/agent/device/bind/${agent_id}`)
            .method('POST')
            .data({code})
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('绑定设备失败:', err);
                RequestService.reAjaxFun(() => {
                    this.addDevice(name, callback);
                });
            }).send();
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

}
