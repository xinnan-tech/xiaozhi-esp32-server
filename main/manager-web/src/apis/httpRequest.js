import Fly from 'flyio/dist/npm/fly.js';
import store from '../store/index';
import Constant from '../utils/constant';
import { goToPage, isNotNull, showDanger, showWarning } from '../utils/index';

const fly = new Fly()
// Set timeout
fly.config.timeout = 30000

/**
 * Request服务封装
 */
export default {
    sendRequest,
    reAjaxFun,
    clearRequestTime
}

function sendRequest() {
    return {
        _sucCallback: null,
        _failCallback: null,
        _networkFailCallback: null,
        _method: 'GET',
        _data: {},
        _header: { 'content-type': 'application/json; charset=utf-8' },
        _url: '',
        _responseType: undefined, // Added response type field
        'send'() {
            if (isNotNull(store.getters.getToken)) {
                this._header.Authorization = 'Bearer ' + (JSON.parse(store.getters.getToken)).token
            }

            // Log request information
            fly.request(this._url, this._data, {
                method: this._method,
                headers: this._header,
                responseType: this._responseType
            }).then((res) => {
                const error = httpHandlerError(res, this._failCallback, this._networkFailCallback);
                if (error) {
                    return
                }

                if (this._sucCallback) {
                    this._sucCallback(res)
                }
            }).catch((res) => {
                // Log failed response
                console.log('catch', res)
                httpHandlerError(res, this._failCallback, this._networkFailCallback)
            })
            return this
        },
        'success'(callback) {
            this._sucCallback = callback
            return this
        },
        'fail'(callback) {
            this._failCallback = callback
            return this
        },
        'networkFail'(callback) {
            this._networkFailCallback = callback
            return this
        },
        'url'(url) {
            if (url) {
                url = url.replaceAll('$', '/')
            }
            this._url = url
            return this
        },
        'data'(data) {
            this._data = data
            return this
        },
        'method'(method) {
            this._method = method
            return this
        },
        'header'(header) {
            this._header = header
            return this
        },
        'showLoading'(showLoading) {
            this._showLoading = showLoading
            return this
        },
        'async'(flag) {
            this.async = flag
        },
        // Added type setting method
        'type'(responseType) {
            this._responseType = responseType;
            return this;
        }
    }
}

/**
 * Info information returned after request completion
 * failCallback 回调函数
 * networkFailCallback 回调函数
 */
// 在错误处理函数中添加日志
function httpHandlerError(info, failCallback, networkFailCallback) {

    /** Request successful, exit function. Success can be determined based on project requirements. Here, status 200 indicates success */
    let networkError = false
    if (info.status === 200) {
        if (info.data.code === 'success' || info.data.code === 0 || info.data.code === undefined) {
            return networkError
        } else if (info.data.code === 401) {
            store.commit('clearAuth');
            goToPage(Constant.PAGE.LOGIN, true);
            return true
        } else {
            if (failCallback) {
                failCallback(info)
            } else {
                showDanger(info.data.msg)
            }
            return true
        }
    }
    if (networkFailCallback) {
        networkFailCallback(info)
    } else {
        showDanger(`Network request error [${info.status}]`)
    }
    return true
}

let requestTime = 0
let reAjaxSec = 2

function reAjaxFun(fn) {
    let nowTimeSec = new Date().getTime() / 1000
    if (requestTime === 0) {
        requestTime = nowTimeSec
    }
    let ajaxIndex = parseInt((nowTimeSec - requestTime) / reAjaxSec)
    if (ajaxIndex > 10) {
        showWarning('Unable to connect to server')
    } else {
        showWarning('Connecting to server (' + ajaxIndex + ')')
    }
    if (ajaxIndex < 10 && fn) {
        setTimeout(() => {
            fn()
        }, reAjaxSec * 1000)
    }
}

function clearRequestTime() {
    requestTime = 0
}