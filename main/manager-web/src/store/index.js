import Vue from 'vue'
import Vuex from 'vuex'
import Constant from '../utils/constant'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    token: '',
    userInfo: {} // 添加用户信息存储
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
    }
  },
  mutations: {
    setToken(state, token) {
      state.token = token
      localStorage.setItem('token', token)
    },
    setUserInfo(state, userInfo) {
      state.userInfo = userInfo
    },
    clearAuth(state) {
      state.token = ''
      state.userInfo = {}
      localStorage.removeItem('token')
    }
  },
  actions: {
    // 添加 logout action
    logout({ commit }) {
      return new Promise((resolve) => {
        commit('clearAuth')
        window.location.href = '/login';
      })
    }
  },
  modules: {
  }
})