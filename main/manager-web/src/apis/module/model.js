import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
  // 获取模型配置列表
  getModelList(params, callback) {
    const queryParams = new URLSearchParams({
      modelType: params.modelType,
      modelName: params.modelName || '',
      page: params.page || 0,
      limit: params.limit || 10
    }).toString();

    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/list?${queryParams}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .fail((err) => {
        console.error('获取模型列表失败:', err)
        RequestService.reAjaxFun(() => {
          this.getModelList(params, callback)
        })
      }).send()
  },
  // 获取模型供应器列表
  getModelProviders(modelType, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${modelType}/provideTypes`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res.data?.data || [])
      })
      .fail((err) => {
        console.error('获取供应器列表失败:', err)
        this.$message.error('获取供应器列表失败')
        RequestService.reAjaxFun(() => {
          this.getModelProviders(modelType, callback)
        })
      }).send()
  },

  // 新增模型配置
  addModel(params, callback) {
    const { modelType, provideCode, formData } = params;
    const postData = {
      modelCode: formData.modelCode,
      modelName: formData.modelName,
      isDefault: formData.isDefault ? 1 : 0,
      isEnabled: formData.isEnabled ? 1 : 0,
      configJson: formData.configJson,
      docLink: formData.docLink,
      remark: formData.remark,
      sort: formData.sort || 0
    };

    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${modelType}/${provideCode}`)
      .method('POST')
      .data(postData)
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .fail((err) => {
        console.error('新增模型失败:', err)
        this.$message.error(err.msg || '新增模型失败')
        RequestService.reAjaxFun(() => {
          this.addModel(params, callback)
        })
      }).send()
  },
  // 删除模型配置
  deleteModel(id, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${id}`)
      .method('DELETE')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .fail((err) => {
        console.error('删除模型失败:', err)
        this.$message.error(err.msg || '删除模型失败')
        RequestService.reAjaxFun(() => {
          this.deleteModel(id, callback)
        })
      }).send()
  },
  // 获取模型名称列表
  getModelNames(modelType, modelName, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/names`)
      .method('GET')
      .data({ modelType, modelName })
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .fail(() => {
        RequestService.reAjaxFun(() => {
          this.getModelNames(modelType, modelName, callback);
        });
      }).send();
  },
  // 获取模型音色列表
  getModelVoices(modelId, voiceName, callback) {
    const queryParams = new URLSearchParams({
      voiceName: voiceName || ''
    }).toString();
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${modelId}/voices?${queryParams}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .fail(() => {
        RequestService.reAjaxFun(() => {
          this.getModelVoices(modelId, voiceName, callback);
        });
      }).send();
  },
  // 获取单个模型配置
  getModelConfig(id, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${id}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .fail((err) => {
        console.error('获取模型配置失败:', err)
        this.$message.error(err.msg || '获取模型配置失败')
        RequestService.reAjaxFun(() => {
          this.getModelConfig(id, callback)
        })
      }).send()
  },
  // 启用/禁用模型状态
  updateModelStatus(id, status, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/enable/${id}/${status}`)
      .method('PUT')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .fail((err) => {
        console.error('更新模型状态失败:', err)
        this.$message.error(err.msg || '更新模型状态失败')
        RequestService.reAjaxFun(() => {
          this.updateModelStatus(id, status, callback)
        })
      }).send()
  },
  // 更新模型配置
  updateModel(params, callback) {
    const { modelType, provideCode, id, formData } = params;
    const payload = {
      ...formData,
      configJson: formData.configJson
    };
    RequestService.sendRequest()
        .url(`${getServiceUrl()}/models/${modelType}/${provideCode}/${id}`)
        .method('PUT')
        .data(payload)
        .success((res) => {
            RequestService.clearRequestTime();
            callback(res);
        })
        .fail((err) => {
            console.error('更新模型失败:', err);
            this.$message.error(err.msg || '更新模型失败');
            RequestService.reAjaxFun(() => {
                this.updateModel(params, callback);
            });
        }).send();
  },
  // 设置默认模型
  setDefaultModel(id, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/default/${id}`)
      .method('PUT')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .fail((err) => {
        console.error('设置默认模型失败:', err)
        this.$message.error(err.msg || '设置默认模型失败')
        RequestService.reAjaxFun(() => {
          this.setDefaultModel(id, callback)
        })
      }).send()
  }
}
