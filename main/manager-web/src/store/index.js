import { goToPage } from "@/utils";
import Vue from 'vue';
import Vuex from 'vuex';
import Constant from '../utils/constant';

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    token: '',
    userInfo: {}, // 添加用户信息存储
    isSuperAdmin: false // 添加superAdmin状态
  },
  getters: {
    getToken(state) {
      if (!state.token) {
        state.token = localStorage.getItem('token')
      }
      return state.token
    },
    getUserInfo(state) {
      return state.userInfo
    },
    getIsSuperAdmin(state) {
      if (localStorage.getItem('isSuperAdmin') === null) {
        return state.isSuperAdmin
      }
      return localStorage.getItem('isSuperAdmin') === 'true'
    }
  },
  mutations: {
    setToken(state, token) {
      state.token = token
      localStorage.setItem('token', token)
    },
    setUserInfo(state, userInfo) {
      state.userInfo = userInfo
      const isSuperAdmin = userInfo.superAdmin === 1
      state.isSuperAdmin = isSuperAdmin
      localStorage.setItem('isSuperAdmin', isSuperAdmin)
    },
    clearAuth(state) {
      state.token = ''
      state.userInfo = {}
      state.isSuperAdmin = false
      localStorage.removeItem('token')
      localStorage.removeItem('isSuperAdmin')
    }
  },
  actions: {
    // 添加 logout action
    logout({ commit }) {
      return new Promise((resolve) => {
        commit('clearAuth')
        goToPage(Constant.PAGE.LOGIN, true);
        window.location.reload(); // 彻底重置状态
      })
    }
  },
  modules: {
  }
})