import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    // 用户列表
    getUserList(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/admin/users`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('请求失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getUserList(callback)
                })
            })
            .send()
    }
}
