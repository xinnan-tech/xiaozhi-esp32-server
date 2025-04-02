import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


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
        .url(`${getServiceUrl()}/api/v1/models/models/list?${queryParams}`)
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

}
