import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    // 用户列表
    getUserList(callback) {
        RequestService.sendRequest().url(`${getServiceUrl()}/api/v1/admin/users`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail(() => {
                RequestService.reAjaxFun(() => {
                    this.getList()
                })
            }).send()
    },
}
