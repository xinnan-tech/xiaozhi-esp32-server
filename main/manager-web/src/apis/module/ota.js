import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
    // Paginated query OTA firmware information
    getOtaList(params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/otaMag`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Get OTA firmware list failed:', err);
                RequestService.reAjaxFun(() => {
                    this.getOtaList(params, callback);
                });
            }).send();
    },
    // Get single OTA firmware information
    getOtaInfo(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/otaMag/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Get OTA firmware information failed:', err);
                RequestService.reAjaxFun(() => {
                    this.getOtaInfo(id, callback);
                });
            }).send();
    },
    // Save OTA firmware information
    saveOta(entity, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/otaMag`)
            .method('POST')
            .data(entity)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Save OTA firmware information failed:', err);
                RequestService.reAjaxFun(() => {
                    this.saveOta(entity, callback);
                });
            }).send();
    },
    // Update OTA firmware information
    updateOta(id, entity, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/otaMag/${id}`)
            .method('PUT')
            .data(entity)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Update OTA firmware information failed:', err);
                RequestService.reAjaxFun(() => {
                    this.updateOta(id, entity, callback);
                });
            }).send();
    },
    // Delete OTA firmware
    deleteOta(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/otaMag/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Delete OTA firmware failed:', err);
                RequestService.reAjaxFun(() => {
                    this.deleteOta(id, callback);
                });
            }).send();
    },
    // Upload firmware file
    uploadFirmware(file, callback) {
        const formData = new FormData();
        formData.append('file', file);
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/otaMag/upload`)
            .method('POST')
            .data(formData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Upload firmware file failed:', err);
                RequestService.reAjaxFun(() => {
                    this.uploadFirmware(file, callback);
                });
            }).send();
    },
    // Get firmware download link
    getDownloadUrl(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/otaMag/getDownloadUrl/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('Get download link failed:', err);
                RequestService.reAjaxFun(() => {
                    this.getDownloadUrl(id, callback);
                });
            }).send();
    }
}