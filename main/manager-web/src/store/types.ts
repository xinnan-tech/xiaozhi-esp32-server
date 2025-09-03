// src/store/types.ts

export interface UserInfo {
    superAdmin?: number | boolean
    // 其余后端返回的字段先不细化，保持可扩展
    [key: string]: any
}

export interface MobileAreaItem {
    key: string
    name: string
}

export interface PubConfig {
    version: string
    beianIcpNum: string | null
    beianGaNum: string | null
    allowUserRegister: boolean
    enableMobileRegister?: boolean
    mobileAreaList?: MobileAreaItem[]
}

export interface RootState {
    token: string
    userInfo: UserInfo
    isSuperAdmin: boolean
    pubConfig: PubConfig
}
