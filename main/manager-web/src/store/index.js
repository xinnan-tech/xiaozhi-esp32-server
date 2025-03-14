import Vue from 'vue'
import Vuex from 'vuex'
import Constant from '../utils/constant'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    token: ''
  },
  getters: {
    getToken(state) {
      if (!state.token) {
        state.token = localStorage.getItem('token')
      }
      return state.token
    }
  },
  mutations: {
    setToken(state, token) {
      state.token = token
      localStorage.token = token
    }
  },
  actions: {
  },
  modules: {
  }
})
