// src/store/index.ts
import Vue from 'vue'
import Vuex, { ActionTree, GetterTree, MutationTree, StoreOptions } from 'vuex'
import type { RootState, UserInfo, PubConfig } from './types'
import { goToPage } from '@/utils'
import Api from '@/apis/api'
import Constant from '@/utils/constant'

Vue.use(Vuex)

const state: RootState = {
  token: '', // 添加token存储
  userInfo: {}, // 添加用户信息存储
  isSuperAdmin: false, // 添加superAdmin状态
  pubConfig: { // 添加公共配置存储
    version: '',
    beianIcpNum: '',
    beianGaNum: '',
    allowUserRegister: false
  }
}

const getters: GetterTree<RootState, RootState> = {
  getToken(state): string {
    if (!state.token) {
      state.token = localStorage.getItem('token') || ''
    }
    return state.token
  },
  getUserInfo(state): UserInfo {
    return state.userInfo
  },
  getIsSuperAdmin(state): boolean {
    const cached = localStorage.getItem('isSuperAdmin')
    if (cached === null) {
      return state.isSuperAdmin
    }
    return cached === 'true'
  },
  getPubConfig(state): PubConfig {
    return state.pubConfig
  }
}

const mutations: MutationTree<RootState> = {
  setToken(state, token: string) {
    state.token = token
    localStorage.setItem('token', token)
  },

  setUserInfo(state, userInfo: UserInfo) {
    state.userInfo = userInfo
    const isSuperAdmin = userInfo.superAdmin === 1 || userInfo.superAdmin === true
    state.isSuperAdmin = isSuperAdmin
    localStorage.setItem('isSuperAdmin', String(isSuperAdmin))
  },

  setPubConfig(state, config: PubConfig | Partial<PubConfig>) {
    // 允许后端只返回部分字段，这里做一次合并
    state.pubConfig = { ...state.pubConfig, ...config }
  },

  clearAuth(state) {
    state.token = ''
    state.userInfo = {}
    state.isSuperAdmin = false
    localStorage.removeItem('token')
    localStorage.removeItem('isSuperAdmin')
  }
}

const actions: ActionTree<RootState, RootState> = {
  // 添加 logout action
  logout({ commit }): Promise<void> {
    return new Promise((resolve) => {
      commit('clearAuth')
      goToPage(Constant.PAGE.LOGIN, true)
      resolve()
      window.location.reload() // 彻底重置状态
    })
  },

  fetchPubConfig({ commit }): Promise<void> {
    return new Promise((resolve) => {
      Api.user.getPubConfig(({ data }: any) => {
        if (data && data.code === 0) {
          commit('setPubConfig', data.data as Partial<PubConfig>)
        }
        resolve()
      })
    })
  }
}

const storeOptions: StoreOptions<RootState> = {
  state,
  getters,
  mutations,
  actions,
  modules: {}
}

const store = new Vuex.Store<RootState>(storeOptions)
export default store
