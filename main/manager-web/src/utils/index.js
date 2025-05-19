import { Message } from 'element-ui'
import router from '../router'
import Constant from '../utils/constant'

/**
 * 判断用户是否登录
 */
export function checkUserLogin(fn) {
    let token = localStorage.getItem(Constant.STORAGE_KEY.TOKEN)
    let userType = localStorage.getItem(Constant.STORAGE_KEY.USER_TYPE)
    if (isNull(token) || isNull(userType)) {
        goToPage('console', true)
        return
    }
    if (fn) {
        fn()
    }
}

/**
 * 判断是否为空
 * @param data
 * @returns {boolean}
 */
export function isNull(data) {
    if (data === undefined) {
        return true
    } else if (data === null) {
        return true
    } else if (typeof data === 'string' && (data.length === 0 || data === '' || data === 'undefined' || data === 'null')) {
        return true
    } else if ((data instanceof Array) && data.length === 0) {
        return true
    }
    return false
}

/**
 * 判断不为空
 * @param data
 * @returns {boolean}
 */
export function isNotNull(data) {
    return !isNull(data)
}

/**
 * 显示顶部红色通知
 * @param msg
 */
export function showDanger(msg) {
    if (isNull(msg)) {
        return
    }
    Message({
        message: msg,
        type: 'error',
        showClose: true
    })
}

/**
 * 显示顶部橙色通知
 * @param msg
 */
export function showWarning(msg) {
    if (isNull(msg)) {
        return
    }
    Message({
        message: msg,
        type: 'warning',
        showClose: true
    });
}



/**
 * 显示顶部绿色通知
 * @param msg
 */
export function showSuccess(msg) {
    Message({
        message: msg,
        type: 'success',
        showClose: true
    })
}



/**
 * 页面跳转
 * @param path
 * @param isRepalce
 */
export function goToPage(path, isRepalce) {
    if (isRepalce) {
        router.replace(path)
    } else {
        router.push(path)
    }
}

/**
 * 获取当前vue页面名称
 * @param path
 * @param isRepalce
 */
export function getCurrentPage() {
    let hash = location.hash.replace('#', '')
    if (hash.indexOf('?') > 0) {
        hash = hash.substring(0, hash.indexOf('?'))
    }
    return hash
}

/**
 * 生成从[min,max]的随机数
 * @param min
 * @param max
 * @returns {number}
 */
export function randomNum(min, max) {
    return Math.round(Math.random() * (max - min) + min)
}


/**
 * 获取uuid
 */
export function getUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        return (c === 'x' ? (Math.random() * 16 | 0) : ('r&0x3' | '0x8')).toString(16)
    })
}

/**
 * 验证手机号格式
 * @param {string} mobile 手机号
 * @param {string} areaCode 区号
 * @returns {boolean}
 */
export function validateMobile(mobile, areaCode) {
    // 移除所有非数字字符
    const cleanMobile = mobile.replace(/\D/g, '');

    // 根据不同区号使用不同的验证规则
    switch (areaCode) {
        case '+86': // 中国大陆
            return /^1[3-9]\d{9}$/.test(cleanMobile);
        case '+852': // 中国香港
            return /^[569]\d{7}$/.test(cleanMobile);
        case '+853': // 中国澳门
            return /^6\d{7}$/.test(cleanMobile);
        case '+886': // 中国台湾
            return /^9\d{8}$/.test(cleanMobile);
        case '+1': // 美国/加拿大
            return /^[2-9]\d{9}$/.test(cleanMobile);
        case '+44': // 英国
            return /^7[1-9]\d{8}$/.test(cleanMobile);
        case '+81': // 日本
            return /^[7890]\d{8}$/.test(cleanMobile);
        case '+82': // 韩国
            return /^1[0-9]\d{7}$/.test(cleanMobile);
        case '+65': // 新加坡
            return /^[89]\d{7}$/.test(cleanMobile);
        case '+61': // 澳大利亚
            return /^[4578]\d{8}$/.test(cleanMobile);
        case '+49': // 德国
            return /^1[5-7]\d{8}$/.test(cleanMobile);
        case '+33': // 法国
            return /^[67]\d{8}$/.test(cleanMobile);
        case '+39': // 意大利
            return /^3[0-9]\d{8}$/.test(cleanMobile);
        case '+34': // 西班牙
            return /^[6-9]\d{8}$/.test(cleanMobile);
        case '+55': // 巴西
            return /^[1-9]\d{10}$/.test(cleanMobile);
        case '+91': // 印度
            return /^[6-9]\d{9}$/.test(cleanMobile);
        case '+971': // 阿联酋
            return /^[5]\d{8}$/.test(cleanMobile);
        case '+966': // 沙特阿拉伯
            return /^[5]\d{8}$/.test(cleanMobile);
        case '+880': // 孟加拉国
            return /^1[3-9]\d{8}$/.test(cleanMobile);
        case '+234': // 尼日利亚
            return /^[789]\d{9}$/.test(cleanMobile);
        case '+254': // 肯尼亚
            return /^[17]\d{8}$/.test(cleanMobile);
        case '+255': // 坦桑尼亚
            return /^[67]\d{8}$/.test(cleanMobile);
        case '+7': // 哈萨克斯坦
            return /^[67]\d{9}$/.test(cleanMobile);
        default:
            // 其他国际号码：至少5位，最多15位
            return /^\d{5,15}$/.test(cleanMobile);
    }
}

