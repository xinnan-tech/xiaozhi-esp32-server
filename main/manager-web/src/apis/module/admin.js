import RequestService from '../httpRequest'
import {getServiceUrl} from '../api'


export default {
    // 用户列表
    getUserList(params, callback) {
      const queryParams = new URLSearchParams({
        page: params.page,
        limit: params.limit,
        mobile: params.mobile
      }).toString();

      RequestService.sendRequest()
        .url(`${getServiceUrl()}/api/v1/admin/users?${queryParams}`)
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
                }).send()
        },
    // 删除用户
    deleteUser(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/admin/users/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('删除失败:', err)
                RequestService.reAjaxFun(() => {
                    this.deleteUser(id, callback)
                })
            }).send()
    },
    // 重置用户密码
    resetUserPassword(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/api/v1/admin/users/${id}`)
            .method('PUT')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('重置密码失败:', err)
                RequestService.reAjaxFun(() => {
                    this.resetUserPassword(id, callback)
                })
            }).send()
    }

}
