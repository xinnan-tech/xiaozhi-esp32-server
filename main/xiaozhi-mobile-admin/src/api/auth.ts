import { http } from '@/http/request/alova'

// 登录接口数据类型
export interface LoginData {
  username: string
  password: string
  captcha: string
  captchaId: string
  areaCode?: string
  mobile?: string
}

// 登录响应数据类型
export interface LoginResponse {
  token: string
  expire: number
  clientHash: string
}

// 验证码响应数据类型
export interface CaptchaResponse {
  captchaId: string
  captchaImage: string
}

// 获取验证码
export function getCaptcha(uuid: string) {
  return http.Get<string>('/user/captcha', {
    params: { uuid },
    meta: {
      ignoreAuth: true,
      toast: false,
    },
  })
}

// 用户登录
export function login(data: LoginData) {
  return http.Post<LoginResponse>('/user/login', data, {
    meta: {
      ignoreAuth: true,
      toast: true,
    },
  })
}

// 用户信息响应数据类型
export interface UserInfo {
  id: number
  username: string
  realName: string
  email: string
  mobile: string
  status: number
  superAdmin: number
}

// 公共配置响应数据类型
export interface PublicConfig {
  enableMobileRegister: boolean
  version: string
  year: string
  allowUserRegister: boolean
  mobileAreaList: Array<{
    name: string
    key: string
  }>
  beianIcpNum: string
  beianGaNum: string
  name: string
}

// 获取用户信息
export function getUserInfo() {
  return http.Get<UserInfo>('/user/info', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// 获取公共配置
export function getPublicConfig() {
  return http.Get<PublicConfig>('/user/pub-config', {
    meta: {
      ignoreAuth: true,
      toast: false,
    },
  })
}

// 注册数据类型
export interface RegisterData {
  username: string
  password: string
  confirmPassword: string
  captcha: string
  captchaId: string
  areaCode: string
  mobile: string
  mobileCaptcha: string
}

// 发送短信验证码
export function sendSmsCode(data: {
  phone: string
  captcha: string
  captchaId: string
}) {
  return http.Post('/user/smsVerification', data, {
    meta: {
      ignoreAuth: true,
      toast: false,
    },
  })
}

// 用户注册
export function register(data: RegisterData) {
  return http.Post('/user/register', data, {
    meta: {
      ignoreAuth: true,
      toast: true,
    },
  })
}
