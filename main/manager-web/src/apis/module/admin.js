import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';


export default {
    // 用户列表
    getUserList(params, callback) {
        const queryParams = new URLSearchParams({
            page: params.page,
            limit: params.limit,
            mobile: params.mobile
        }).toString();

        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/users?${queryParams}`)
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
            .url(`${getServiceUrl()}/admin/users/${id}`)
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
            .url(`${getServiceUrl()}/admin/users/${id}`)
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
    },
    getParamsList(params, callback) {
        const queryParams = new URLSearchParams({
            page: params.page,
            limit: params.limit
        }).toString();

        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params/page?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('获取参数列表失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getParamsList(params, callback)
                })
            }).send()
    },
    addParam(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('添加参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.addParam(data, callback)
                })
            }).send()
    },
    updateParam(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('更新参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.updateParam(data, callback)
                })
            }).send()
    },
    deleteParam(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('DELETE')
            .data({ ids: [id] })
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('删除参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.deleteParam(id, callback)
                })
            }).send()
    },
    batchDeleteParams(ids, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('DELETE')
            .data({ ids })
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                console.error('批量删除参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.batchDeleteParams(ids, callback)
                })
            }).send()
    }
}
