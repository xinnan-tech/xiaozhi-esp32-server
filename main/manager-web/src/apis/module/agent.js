import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';


export default {
    // 获取智能体列表
    getAgentList(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/list`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentList(callback);
                });
            }).send();
    },
    // 添加智能体
    addAgent(agentName, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent`)
            .method('POST')
            .data({ agentName: agentName })
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.addAgent(agentName, callback);
                });
            }).send();
    },
    // 删除智能体
    deleteAgent(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.deleteAgent(agentId, callback);
                });
            }).send();
    },
    // 获取智能体配置
    getDeviceConfig(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceConfig(agentId, callback);
                });
            }).send();
    },
    // 配置智能体
    updateAgentConfig(agentId, configData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}`)
            .method('PUT')
            .data(configData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.updateAgentConfig(agentId, configData, callback);
                });
            }).send();
    },
    // 新增方法：获取智能体模板
    getAgentTemplate(callback) {  // 移除templateName参数
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取模板失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentTemplate(callback);
                });
            }).send();
    },

    // 新增：获取智能体模板分页列表
    getAgentTemplatesPage(params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/page`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取模板分页列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentTemplatesPage(params, callback);
                });
            }).send();
    },
    // 获取智能体会话列表
    getAgentSessions(agentId, params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/sessions`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentSessions(agentId, params, callback);
                });
            }).send();
    },
    // 获取智能体聊天记录
    getAgentChatHistory(agentId, sessionId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/chat-history/${sessionId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentChatHistory(agentId, sessionId, callback);
                });
            }).send();
    },
    // 获取音频下载ID
    getAudioId(audioId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/audio/${audioId}`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAudioId(audioId, callback);
                });
            }).send();
    },
    // 获取智能体的MCP接入点地址
    getAgentMcpAccessAddress(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/mcp/address/${agentId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentMcpAccessAddress(agentId, callback);
                });
            }).send();
    },
    // 获取智能体的MCP工具列表
    getAgentMcpToolsList(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/mcp/tools/${agentId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentMcpToolsList(agentId, callback);
                });
            }).send();
    },
    // 添加智能体的声纹
    addAgentVoicePrint(voicePrintData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print`)
            .method('POST')
            .data(voicePrintData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.addAgentVoicePrint(voicePrintData, callback);
                });
            }).send();
    },
    // 获取指定智能体声纹列表
    getAgentVoicePrintList(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print/list/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentVoicePrintList(id, callback);
                });
            }).send();
    },
    // 删除智能体声纹
    deleteAgentVoicePrint(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.deleteAgentVoicePrint(id, callback);
                });
            }).send();
    },
    // 更新智能体声纹
    updateAgentVoicePrint(voicePrintData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print`)
            .method('PUT')
            .data(voicePrintData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.updateAgentVoicePrint(voicePrintData, callback);
                });
            }).send();
    },
    // 获取指定智能体用户类型聊天记录
    getRecentlyFiftyByAgentId(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${id}/chat-history/user`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getRecentlyFiftyByAgentId(id, callback);
                });
            }).send();
    },
    // 获取指定智能体用户类型聊天记录
    getContentByAudioId(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${id}/chat-history/audio`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getContentByAudioId(id, callback);
                });
            }).send();
    },
    // 在文件末尾（在最后一个方法后，大括号前）添加以下方法：
    // 新增智能体模板
    addAgentTemplate(templateData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template`)
            .method('POST')
            .data(templateData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.addAgentTemplate(templateData, callback);
                });
            }).send();
    },

    // 更新智能体模板
    updateAgentTemplate(templateData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template`)
            .method('PUT')
            .data(templateData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.updateAgentTemplate(templateData, callback);
                });
            }).send();
    },

    // 删除智能体模板
    deleteAgentTemplate(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.deleteAgentTemplate(id, callback);
                });
            }).send();
    },

    // 批量删除智能体模板
    batchDeleteAgentTemplate(ids, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/batch-remove`) // 修改为新的URL
            .method('POST')
            .data(Array.isArray(ids) ? ids : [ids]) // 确保是数组格式
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.batchDeleteAgentTemplate(ids, callback);
                });
            }).send();
    },
    // 在getAgentTemplate方法后添加获取单个模板的方法
    getAgentTemplateById(templateId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/${templateId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取单个模板失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentTemplateById(templateId, callback);
                });
            }).send();
    },

    // 获取聊天记录下载链接UUID
    getDownloadUrl(agentId, sessionId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/chat-history/getDownloadUrl/${agentId}/${sessionId}`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getDownloadUrl(agentId, sessionId, callback);
                });
            }).send();
    },
}
