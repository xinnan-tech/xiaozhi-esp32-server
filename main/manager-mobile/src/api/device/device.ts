import type { Device, FirmwareType } from './types'
import { http } from '@/http/request/alova'

/**
 * 获取设备类型列表
 */
export function getFirmwareTypes() {
  return http.Get<FirmwareType[]>('/admin/dict/data/type/FIRMWARE_TYPE')
}

/**
 * 获取绑定设备列表
 * @param agentId 智能体ID
 */
export function getBindDevices(agentId: string) {
  return http.Get<Device[]>(`/device/bind/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

/**
 * 添加设备
 * @param agentId 智能体ID
 * @param code 验证码
 */
export function bindDevice(agentId: string, code: string) {
  return http.Post(`/device/bind/${agentId}/${code}`, null)
}

/**
 * 设置设备OTA升级开关
 * @param deviceId 设备ID (MAC地址)
 * @param autoUpdate 是否自动升级 0|1
 */
export function updateDeviceAutoUpdate(deviceId: string, autoUpdate: number) {
  return http.Put(`/device/update/${deviceId}`, {
    autoUpdate,
  })
}

/**
 * 解绑设备
 * @param deviceId 设备ID (MAC地址)
 */
export function unbindDevice(deviceId: string) {
  return http.Post('/device/unbind', {
    deviceId,
  })
}
