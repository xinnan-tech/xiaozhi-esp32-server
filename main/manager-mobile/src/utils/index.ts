import { pages, subPackages } from '@/pages.json'
import { isMpWeixin } from './platform'

/**
 * 运行时服务端地址覆盖存储键
 */
export const SERVER_BASE_URL_OVERRIDE_KEY = 'server_base_url_override'

/**
 * 设置/清除/获取 运行时覆盖的服务端地址
 */
export function setServerBaseUrlOverride(url: string) {
  uni.setStorageSync(SERVER_BASE_URL_OVERRIDE_KEY, url)
}

export function clearServerBaseUrlOverride() {
  uni.removeStorageSync(SERVER_BASE_URL_OVERRIDE_KEY)
}

export function getServerBaseUrlOverride(): string | null {
  const value = uni.getStorageSync(SERVER_BASE_URL_OVERRIDE_KEY)
  return value || null
}

export function getLastPage() {
  // getCurrentPages() 至少有1个元素，所以不再额外判断
  // const lastPage = getCurrentPages().at(-1)
  // 上面那个在低版本安卓中打包会报错，所以改用下面这个【虽然我加了 src/interceptions/prototype.ts，但依然报错】
  const pages = getCurrentPages()
  return pages[pages.length - 1]
}

/**
 * 获取当前页面路由的 path 路径和 redirectPath 路径
 * path 如 '/pages/login/index'
 * redirectPath 如 '/pages/demo/base/route-interceptor'
 */
export function currRoute() {
  const lastPage = getLastPage()
  const currRoute = (lastPage as any).$page
  // console.log('lastPage.$page:', currRoute)
  // console.log('lastPage.$page.fullpath:', currRoute.fullPath)
  // console.log('lastPage.$page.options:', currRoute.options)
  // console.log('lastPage.options:', (lastPage as any).options)
  // 经过多端测试，只有 fullPath 靠谱，其他都不靠谱
  const { fullPath } = currRoute as { fullPath: string }
  // console.log(fullPath)
  // eg: /pages/login/index?redirect=%2Fpages%2Fdemo%2Fbase%2Froute-interceptor (小程序)
  // eg: /pages/login/index?redirect=%2Fpages%2Froute-interceptor%2Findex%3Fname%3Dfeige%26age%3D30(h5)
  return getUrlObj(fullPath)
}

function ensureDecodeURIComponent(url: string) {
  if (url.startsWith('%')) {
    return ensureDecodeURIComponent(decodeURIComponent(url))
  }
  return url
}
/**
 * 解析 url 得到 path 和 query
 * 比如输入url: /pages/login/index?redirect=%2Fpages%2Fdemo%2Fbase%2Froute-interceptor
 * 输出: {path: /pages/login/index, query: {redirect: /pages/demo/base/route-interceptor}}
 */
export function getUrlObj(url: string) {
  const [path, queryStr] = url.split('?')
  // console.log(path, queryStr)

  if (!queryStr) {
    return {
      path,
      query: {},
    }
  }
  const query: Record<string, string> = {}
  queryStr.split('&').forEach((item) => {
    const [key, value] = item.split('=')
    // console.log(key, value)
    query[key] = ensureDecodeURIComponent(value) // 这里需要统一 decodeURIComponent 一下，可以兼容h5和微信y
  })
  return { path, query }
}
/**
 * 得到所有的需要登录的 pages，包括主包和分包的
 * 这里设计得通用一点，可以传递 key 作为判断依据，默认是 needLogin, 与 route-block 配对使用
 * 如果没有传 key，则表示所有的 pages，如果传递了 key, 则表示通过 key 过滤
 */
export function getAllPages(key = 'needLogin') {
  // 这里处理主包
  const mainPages = pages
    .filter(page => !key || page[key])
    .map(page => ({
      ...page,
      path: `/${page.path}`,
    }))

  // 这里处理分包
  const subPages: any[] = []
  subPackages.forEach((subPageObj) => {
    // console.log(subPageObj)
    const { root } = subPageObj

    subPageObj.pages
      .filter(page => !key || page[key])
      .forEach((page: { path: string } & Record<string, any>) => {
        subPages.push({
          ...page,
          path: `/${root}/${page.path}`,
        })
      })
  })
  const result = [...mainPages, ...subPages]
  // console.log(`getAllPages by ${key} result: `, result)
  return result
}

/**
 * 得到所有的需要登录的 pages，包括主包和分包的
 * 只得到 path 数组
 */
export const getNeedLoginPages = (): string[] => getAllPages('needLogin').map(page => page.path)

/**
 * 得到所有的需要登录的 pages，包括主包和分包的
 * 只得到 path 数组
 */
export const needLoginPages: string[] = getAllPages('needLogin').map(page => page.path)

/**
 * 根据微信小程序当前环境，判断应该获取的 baseUrl
 */
export function getEnvBaseUrl() {
  // 若存在用户设置的覆盖地址，优先返回
  const override = getServerBaseUrlOverride()
  if (override)
    return override

  // 请求基准地址（默认来源于 env）
  let baseUrl = import.meta.env.VITE_SERVER_BASEURL

  // # 有些同学可能需要在微信小程序里面根据 develop、trial、release 分别设置上传地址，参考代码如下。
  const VITE_SERVER_BASEURL__WEIXIN_DEVELOP = 'https://ukw0y1.laf.run'
  const VITE_SERVER_BASEURL__WEIXIN_TRIAL = 'https://ukw0y1.laf.run'
  const VITE_SERVER_BASEURL__WEIXIN_RELEASE = 'https://ukw0y1.laf.run'

  // 微信小程序端环境区分
  if (isMpWeixin) {
    const {
      miniProgram: { envVersion },
    } = uni.getAccountInfoSync()

    switch (envVersion) {
      case 'develop':
        baseUrl = VITE_SERVER_BASEURL__WEIXIN_DEVELOP || baseUrl
        break
      case 'trial':
        baseUrl = VITE_SERVER_BASEURL__WEIXIN_TRIAL || baseUrl
        break
      case 'release':
        baseUrl = VITE_SERVER_BASEURL__WEIXIN_RELEASE || baseUrl
        break
    }
  }

  return baseUrl
}

/**
 * 根据微信小程序当前环境，判断应该获取的 UPLOAD_BASEURL
 */
export function getEnvBaseUploadUrl() {
  // 请求基准地址
  let baseUploadUrl = import.meta.env.VITE_UPLOAD_BASEURL

  const VITE_UPLOAD_BASEURL__WEIXIN_DEVELOP = 'https://ukw0y1.laf.run/upload'
  const VITE_UPLOAD_BASEURL__WEIXIN_TRIAL = 'https://ukw0y1.laf.run/upload'
  const VITE_UPLOAD_BASEURL__WEIXIN_RELEASE = 'https://ukw0y1.laf.run/upload'

  // 微信小程序端环境区分
  if (isMpWeixin) {
    const {
      miniProgram: { envVersion },
    } = uni.getAccountInfoSync()

    switch (envVersion) {
      case 'develop':
        baseUploadUrl = VITE_UPLOAD_BASEURL__WEIXIN_DEVELOP || baseUploadUrl
        break
      case 'trial':
        baseUploadUrl = VITE_UPLOAD_BASEURL__WEIXIN_TRIAL || baseUploadUrl
        break
      case 'release':
        baseUploadUrl = VITE_UPLOAD_BASEURL__WEIXIN_RELEASE || baseUploadUrl
        break
    }
  }

  return baseUploadUrl
}

import smCrypto from 'sm-crypto'

/**
 * 生成SM2密钥对（十六进制格式）
 * @returns {Object} 包含公钥和私钥的对象
 */
export function generateSm2KeyPairHex() {
    // 使用sm-crypto库生成SM2密钥对
    const sm2 = smCrypto.sm2;
    const keypair = sm2.generateKeyPairHex();
    
    return {
        publicKey: keypair.publicKey,
        privateKey: keypair.privateKey,
        clientPublicKey: keypair.publicKey, // 客户端公钥
        clientPrivateKey: keypair.privateKey // 客户端私钥
    };
}

/**
 * SM2公钥加密
 * @param {string} publicKey 公钥（十六进制格式）
 * @param {string} plainText 明文
 * @returns {string} 加密后的密文（十六进制格式）
 */
export function sm2Encrypt(publicKey: string, plainText: string): string {
    if (!publicKey) {
        throw new Error('公钥不能为null或undefined');
    }
    
    if (!plainText) {
        throw new Error('明文不能为空');
    }
    
    const sm2 = smCrypto.sm2;
    // SM2加密，添加04前缀表示未压缩公钥
    const encrypted = sm2.doEncrypt(plainText, publicKey, 1);
    // 转换为十六进制格式（与后端保持一致，添加04前缀）
    const result = "04" + encrypted;
    
    return result;
}

/**
 * SM2私钥解密
 * @param {string} privateKey 私钥（十六进制格式）
 * @param {string} cipherText 密文（十六进制格式）
 * @returns {string} 解密后的明文
 */
export function sm2Decrypt(privateKey: string, cipherText: string): string {
    const sm2 = smCrypto.sm2;
    // 移除04前缀（与后端保持一致）
    const dataWithoutPrefix = cipherText.startsWith("04") ? cipherText.substring(2) : cipherText;
    // SM2解密
    return sm2.doDecrypt(dataWithoutPrefix, privateKey, 1);
}
