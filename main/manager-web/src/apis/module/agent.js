import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    // 获取智能体列表
    getAgentList(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/agent/list`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentList(callback);
                });
            }).send();
    },
    // 添加智能体
    addAgent(agentName, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/agent`)
            .method('POST')
            .data({agentName: agentName})
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.addAgent(agentName, callback);
                });
            }).send();
    },
    // 删除智能体
    deleteAgent(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/agent/${agentId}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.deleteAgent(agentId, callback);
                });
            }).send();
    },
    // 获取智能体配置
    getDeviceConfig(deviceId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/agent/${deviceId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('获取配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceConfig(deviceId, callback);
                });
            }).send();
    },
    // 配置智能体
    updateAgentConfig(agentId, configData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/agent/${agentId}`)
            .method('PUT')
            .data(configData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.updateAgentConfig(agentId, configData, callback);
                });
            }).send();
    },
    // 新增方法：获取智能体模板
    getAgentTemplate(callback) {  // 移除templateName参数
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/agent/template`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('获取模板失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentTemplate(callback);
                });
            }).send();
    },
}
