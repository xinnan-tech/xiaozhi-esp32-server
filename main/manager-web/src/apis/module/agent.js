import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    //智能体列表
    getAgentList(callback) {
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/user/agent`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('获取智能体列表失败:', err);
            }).send()
    },
    //添加智能体
    addAgent(name, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/agent`)
            .method('POST')
            .data({name})
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('添加智能体失败:', err);
                RequestService.reAjaxFun(() => {
                    this.addAgent(name, callback);
                });
            }).send();
    },
    //获取智能体配置
    getAgentConfig(agent_id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/agent/${agent_id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('获取智能体配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentConfig(agent_id, callback);
                });
            }).send();
    },
    //配置智能体
    saveAgentConfig(agent_id, configData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/agent/${agent_id}`)
            .method('PUT')
            .data(configData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('保存智能体配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.saveAgentConfig(device_id, configData, callback);
                });
            }).send();
    },
    //删除智能体
    delAgent(agent_id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/user/agent/${agent_id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                console.error('删除智能体失败:', err);
                RequestService.reAjaxFun(() => {
                    this.deleteAgent(agent_id, callback);
                });
            }).send();
    },
}
