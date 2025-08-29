import type { UserInfo } from '../api/auth'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getUserInfo as _getUserInfo,
} from '../api/auth'

// 初始化状态
const userInfoState: UserInfo & { avatar?: string, token?: string } = {
  id: 0,
  username: '',
  realName: '',
  email: '',
  mobile: '',
  status: 0,
  superAdmin: 0,
  avatar: '/static/images/default-avatar.png',
  token: '',
}

export const useUserStore = defineStore(
  'user',
  () => {
    // 定义用户信息
    const userInfo = ref<UserInfo & { avatar?: string, token?: string }>({ ...userInfoState })
    // 设置用户信息
    const setUserInfo = (val: UserInfo & { avatar?: string, token?: string }) => {
      console.log('设置用户信息', val)
      // 若头像为空 则使用默认头像
      if (!val.avatar) {
        val.avatar = userInfoState.avatar
      }
      else {
        val.avatar = 'https://oss.laf.run/ukw0y1-site/avatar.jpg?feige'
      }
      userInfo.value = val
    }
    const setUserAvatar = (avatar: string) => {
      userInfo.value.avatar = avatar
      console.log('设置用户头像', avatar)
      console.log('userInfo', userInfo.value)
    }
    // 删除用户信息
    const removeUserInfo = () => {
      userInfo.value = { ...userInfoState }
      uni.removeStorageSync('userInfo')
      uni.removeStorageSync('token')
    }
    /**
     * 获取用户信息
     */
    const getUserInfo = async () => {
      const userData = await _getUserInfo()
      const userInfoWithExtras = {
        ...userData,
        avatar: userInfoState.avatar,
        token: uni.getStorageSync('token') || '',
      }
      setUserInfo(userInfoWithExtras)
      uni.setStorageSync('userInfo', userInfoWithExtras)
      // TODO 这里可以增加获取用户路由的方法 根据用户的角色动态生成路由
      return userInfoWithExtras
    }
    /**
     * 退出登录 并 删除用户信息
     */
    const logout = async () => {
      removeUserInfo()
    }

    return {
      userInfo,
      getUserInfo,
      setUserInfo,
      setUserAvatar,
      logout,
      removeUserInfo,
    }
  },
  {
    persist: true,
  },
)
