// 引入各个模块的请求
import user from './module/user.js'

/**
 * 接口地址
 * 当前8002端口接口还没开发完成，暂时用 apifoxmock 接口代替
 * 如果你想调用8002端口，就用'/xiaozhi-esp32-api/api/v1'，请与vue.config.js的devServer配置相结合，方便跨域请求
 *
 */
const DEV_API_SERVICE = 'https://apifoxmock.com/m1/5931378-5618560-default'
// 8002开发完成完成后使用这个
// const DEV_API_SERVICE = '/xiaozhi-esp32-api'

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
