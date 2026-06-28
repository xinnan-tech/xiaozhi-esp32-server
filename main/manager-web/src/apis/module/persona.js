import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
    // 手动切换角色(标 manual=1,自动任务不再覆盖)
    switchPersona(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/persona/switch`)
            .method('POST')
            .data({ agentId })
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.switchPersona(agentId, callback);
                });
            }).send();
    },
    // 恢复自动匹配(manual=0)
    resetAuto(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/persona/auto`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.resetAuto(callback);
                });
            }).send();
    },
}
