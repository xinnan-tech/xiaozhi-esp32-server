import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
    // 分页查询音色资源
    getVoiceResourceList(params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取音色资源列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getVoiceResourceList(params, callback);
                });
            }).send();
    },
    // 获取单个音色资源信息
    getVoiceResourceInfo(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取音色资源信息失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getVoiceResourceInfo(id, callback);
                });
            }).send();
    },
    // 保存音色资源
    saveVoiceResource(entity, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource`)
            .method('POST')
            .data(entity)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('保存音色资源失败:', err);
                RequestService.reAjaxFun(() => {
                    this.saveVoiceResource(entity, callback);
                });
            }).send();
    },
    // 删除音色资源
    deleteVoiceResource(ids, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/${ids}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('删除音色资源失败:', err);
                RequestService.reAjaxFun(() => {
                    this.deleteVoiceResource(ids, callback);
                });
            }).send();
    },
    // 根据用户ID获取音色资源列表
    getVoiceResourceByUserId(userId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/user/${userId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取用户音色资源列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getVoiceResourceByUserId(userId, callback);
                });
            }).send();
    },
    // 获取TTS平台列表
    getTtsPlatformList(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/ttsPlatforms`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取TTS平台列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getTtsPlatformList(callback);
                });
            }).send();
    }
}
