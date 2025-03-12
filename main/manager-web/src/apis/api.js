// 引入各个模块的请求
import user from './module/user.js'
/**
 * 接口地址
 * 在开发阶段，如果地址写的是相对路径，请与vue.config.js的devServer配置相结合，方便跨域请求
 *
 */
const DEV_API_SERVICE = 'http://localhost:8002/xiaozhi-esp32-api'

/**
 * 根据开发环境返回接口url
 * @returns {string}
 */
export function getServiceUrl() {
    return DEV_API_SERVICE
}


/** request服务封装 */
export default {
    getServiceUrl,
    user,
}
