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
 * 固件类型选项
 */
export const FIRMWARE_TYPES = [
    { "key": "bread-compact-wifi", "name": "面包板新版接线（WiFi）" },
    { "key": "bread-compact-wifi-lcd", "name": "面包板新版接线（WiFi）+ LCD" },
    { "key": "bread-compact-ml307", "name": "面包板新版接线（ML307 AT）" },
    { "key": "bread-compact-esp32", "name": "面包板（WiFi） ESP32 DevKit" },
    { "key": "bread-compact-esp32-lcd", "name": "面包板（WiFi+ LCD） ESP32 DevKit" },
    { "key": "df-k10", "name": "DFRobot 行空板 k10" },
    { "key": "esp32-cgc", "name": "ESP32 CGC" },
    { "key": "esp-box-3", "name": "ESP BOX 3" },
    { "key": "esp-box", "name": "ESP BOX" },
    { "key": "esp-box-lite", "name": "ESP BOX Lite" },
    { "key": "kevin-box-1", "name": "Kevin Box 1" },
    { "key": "kevin-box-2", "name": "Kevin Box 2" },
    { "key": "kevin-c3", "name": "Kevin C3" },
    { "key": "kevin-sp-v3-dev", "name": "Kevin SP V3开发板" },
    { "key": "kevin-sp-v4-dev", "name": "Kevin SP V4开发板" },
    { "key": "kevin-yuying-313lcd", "name": "鱼鹰科技3.13LCD开发板" },
    { "key": "lichuang-dev", "name": "立创·实战派ESP32-S3开发板" },
    { "key": "lichuang-c3-dev", "name": "立创·实战派ESP32-C3开发板" },
    { "key": "magiclick-2p4", "name": "神奇按钮 Magiclick_2.4" },
    { "key": "magiclick-2p5", "name": "神奇按钮 Magiclick_2.5" },
    { "key": "magiclick-c3", "name": "神奇按钮 Magiclick_C3" },
    { "key": "magiclick-c3-v2", "name": "神奇按钮 Magiclick_C3_v2" },
    { "key": "m5stack-core-s3", "name": "M5Stack CoreS3" },
    { "key": "atoms3-echo-base", "name": "AtomS3 + Echo Base" },
    { "key": "atoms3r-echo-base", "name": "AtomS3R + Echo Base" },
    { "key": "atoms3r-cam-m12-echo-base", "name": "AtomS3R CAM/M12 + Echo Base" },
    { "key": "atommatrix-echo-base", "name": "AtomMatrix + Echo Base" },
    { "key": "xmini-c3", "name": "虾哥 Mini C3" },
    { "key": "esp32s3-korvo2-v3", "name": "ESP32S3_KORVO2_V3开发板" },
    { "key": "esp-sparkbot", "name": "ESP-SparkBot开发板" },
    { "key": "esp-spot-s3", "name": "ESP-Spot-S3" },
    { "key": "esp32-s3-touch-amoled-1.8", "name": "Waveshare ESP32-S3-Touch-AMOLED-1.8" },
    { "key": "esp32-s3-touch-lcd-1.85c", "name": "Waveshare ESP32-S3-Touch-LCD-1.85C" },
    { "key": "esp32-s3-touch-lcd-1.85", "name": "Waveshare ESP32-S3-Touch-LCD-1.85" },
    { "key": "esp32-s3-touch-lcd-1.46", "name": "Waveshare ESP32-S3-Touch-LCD-1.46" },
    { "key": "esp32-s3-touch-lcd-3.5", "name": "Waveshare ESP32-S3-Touch-LCD-3.5" },
    { "key": "tudouzi", "name": "土豆子" },
    { "key": "lilygo-t-circle-s3", "name": "LILYGO T-Circle-S3" },
    { "key": "lilygo-t-cameraplus-s3", "name": "LILYGO T-CameraPlus-S3" },
    { "key": "movecall-moji-esp32s3", "name": "Movecall Moji 小智AI衍生版" },
    { "key": "movecall-cuican-esp32s3", "name": "Movecall CuiCan 璀璨·AI吊坠" },
    { "key": "atk-dnesp32s3", "name": "正点原子DNESP32S3开发板" },
    { "key": "atk-dnesp32s3-box", "name": "正点原子DNESP32S3-BOX" },
    { "key": "du-chatx", "name": "嘟嘟开发板CHATX(wifi)" },
    { "key": "taiji-pi-s3", "name": "太极小派esp32s3" },
    { "key": "xingzhi-cube-0.85tft-wifi", "name": "无名科技星智0.85(WIFI)" },
    { "key": "xingzhi-cube-0.85tft-ml307", "name": "无名科技星智0.85(ML307)" },
    { "key": "xingzhi-cube-0.96oled-wifi", "name": "无名科技星智0.96(WIFI)" },
    { "key": "xingzhi-cube-0.96oled-ml307", "name": "无名科技星智0.96(ML307)" },
    { "key": "xingzhi-cube-1.54tft-wifi", "name": "无名科技星智1.54(WIFI)" },
    { "key": "xingzhi-cube-1.54tft-ml307", "name": "无名科技星智1.54(ML307)" },
    { "key": "sensecap-watcher", "name": "SenseCAP Watcher" },
    { "key": "doit-s3-aibox", "name": "四博智联AI陪伴盒子" },
    { "key": "mixgo-nova", "name": "元控·青春" }
]

