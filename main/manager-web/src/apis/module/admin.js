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
            .networkFail((err) => {
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
            .networkFail((err) => {
                console.error('删除失败:', err)
                RequestService.reAjaxFun(() => {
                    this.deleteUser(id, callback)
                })
            }).send()
    },
    // 获取用户信息 (通过用户ID) - 使用用户列表API并客户端过滤
    getUserById(userId, callback) {
        // 使用现有的用户列表API，获取所有用户然后客户端过滤
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/users?page=1&limit=1000`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                console.log('getUserById API response:', res);
                
                // 检查响应结构并查找指定用户
                if (res.data && res.data.code === 0 && res.data.data && res.data.data.list && Array.isArray(res.data.data.list)) {
                    // 在用户列表中查找指定ID的用户 (注意字段名是userid，不是id)
                    const userInfo = res.data.data.list.find(user => 
                        user.userid === userId || user.userid === parseInt(userId) || user.userid === String(userId)
                    );
                    
                    if (userInfo) {
                        console.log('Found user info:', userInfo);
                        const formattedResponse = {
                            data: {
                                code: 0,
                                msg: 'success',
                                data: userInfo
                            }
                        };
                        callback(formattedResponse);
                    } else {
                        console.log('User not found in list, userId:', userId);
                        console.log('Available user IDs:', res.data.data.list.map(u => u.userid));
                        // 用户不存在
                        const errorResponse = {
                            data: {
                                code: 1,
                                msg: 'User not found',
                                data: null
                            }
                        };
                        callback(errorResponse);
                    }
                } else {
                    console.error('Invalid response structure for getUserById:', res);
                    const errorResponse = {
                        data: {
                            code: 1,
                            msg: 'Invalid response structure',
                            data: null
                        }
                    };
                    callback(errorResponse);
                }
            })
            .networkFail((err) => {
                console.error('获取用户信息失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getUserById(userId, callback)
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
            .networkFail((err) => {
                console.error('重置密码失败:', err)
                RequestService.reAjaxFun(() => {
                    this.resetUserPassword(id, callback)
                })
            }).send()
    },
    // 获取参数列表
    getParamsList(params, callback) {
        const queryParams = new URLSearchParams({
            page: params.page,
            limit: params.limit,
            paramCode: params.paramCode || ''
        }).toString();

        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params/page?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取参数列表失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getParamsList(params, callback)
                })
            }).send()
    },
    // 保存
    addParam(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('添加参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.addParam(data, callback)
                })
            }).send()
    },
    // 修改
    updateParam(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('更新参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.updateParam(data, callback)
                })
            }).send()
    },
    // 删除
    deleteParam(ids, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params/delete`)
            .method('POST')
            .data(ids)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res);
            })
            .networkFail((err) => {
                console.error('删除参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.deleteParam(ids, callback)
                })
            }).send()
    },
    // 获取ws服务端列表
    getWsServerList(params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/server/server-list`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取ws服务端列表失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getWsServerList(params, callback)
                })
            }).send();
    },
    // 发送ws服务器动作指令
    sendWsServerAction(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/server/emit-action`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                RequestService.reAjaxFun(() => {
                    this.sendWsServerAction(data, callback)
                })
            }).send();
    }

}
