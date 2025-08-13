import { getServiceUrl } from '../api'
import RequestService from '../httpRequest'


export default {
    // Login
    login(loginForm, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/login`)
            .method('POST')
            .data(loginForm)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                RequestService.clearRequestTime()
                failCallback(err)
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.login(loginForm, callback)
                })
            }).send()
    },
    // Get verification code
    getCaptcha(uuid, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/captcha?uuid=${uuid}`)
            .method('GET')
            .type('blob')
            .header({
                'Content-Type': 'image/gif',
                'Pragma': 'No-cache',
                'Cache-Control': 'no-cache'
            })
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {  // Add error parameter

            }).send()
    },
    // Send SMS verification code
    sendSmsVerification(data, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/smsVerification`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                RequestService.clearRequestTime()
                failCallback(err)
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.sendSmsVerification(data, callback, failCallback)
                })
            }).send()
    },
    // Register account
    register(registerForm, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/register`)
            .method('POST')
            .data(registerForm)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                RequestService.clearRequestTime()
                failCallback(err)
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.register(registerForm, callback, failCallback)
                })
            }).send()
    },
    // Save device configuration
    saveDeviceConfig(device_id, configData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/configDevice/${device_id}`)
            .method('PUT')
            .data(configData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Save configuration failed:', err);
                RequestService.reAjaxFun(() => {
                    this.saveDeviceConfig(device_id, configData, callback);
                });
            }).send();
    },
    // Get user information
    getUserInfo(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/info`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('API request failed:', err)
                RequestService.reAjaxFun(() => {
                    this.getUserInfo(callback)
                })
            }).send()
    },
    // Change user password
    changePassword(oldPassword, newPassword, successCallback, errorCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/change-password`)
            .method('PUT')
            .data({
                password: oldPassword,
                newPassword: newPassword,
            })
            .success((res) => {
                RequestService.clearRequestTime();
                successCallback(res);
            })
            .networkFail((error) => {
                RequestService.reAjaxFun(() => {
                    this.changePassword(oldPassword, newPassword, successCallback, errorCallback);
                });
            })
            .send();
    },
    // Change user status
    changeUserStatus(status, userIds, successCallback) {
        console.log(555, userIds)
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/users/changeStatus/${status}`)
            .method('put')
            .data(userIds)
            .success((res) => {
                RequestService.clearRequestTime()
                successCallback(res);
            })
            .networkFail((err) => {
                console.error('Change user status failed:', err)
                RequestService.reAjaxFun(() => {
                    this.changeUserStatus(status, userIds)
                })
            }).send()
    },
    // Get public configuration
    getPubConfig(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/pub-config`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Get public configuration failed:', err);
                RequestService.reAjaxFun(() => {
                    this.getPubConfig(callback);
                });
            }).send();
    },
    // Retrieve user password
    retrievePassword(passwordData, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/user/retrieve-password`)
            .method('PUT')
            .data({
                phone: passwordData.phone,
                code: passwordData.code,
                password: passwordData.password
            })
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                RequestService.clearRequestTime();
                failCallback(err);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.retrievePassword(passwordData, callback, failCallback);
                });
            }).send()
    }
}
