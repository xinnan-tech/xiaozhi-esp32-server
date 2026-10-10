import 'element-ui/lib/theme-chalk/index.css';
import 'normalize.css/normalize.css'; // A modern alternative to CSS resets
import Vue from 'vue';
import ElementUI from 'element-ui';
import App from './App.vue';
import router from './router';
import store from './store';
import i18n from './i18n';
import locale from 'element-ui/lib/locale'
import './styles/global.scss';
import { register as registerServiceWorker } from './registerServiceWorker';
import featureManager from './utils/featureManager';

// 创建事件总线，用于组件间通信
Vue.prototype.$eventBus = new Vue();

Vue.use(ElementUI);
locale.i18n((key, value) => i18n.t(key, value))

Vue.config.productionTip = false

// 注册Service Worker
registerServiceWorker();

// 应用启动时把 localStorage 里的 token 同步进 store，避免守卫放行后首次请求时
// httpRequest 读到 state.token=null 而漏带 Authorization 头触发 401 跳登录
const cachedToken = localStorage.getItem('token')
if (cachedToken) {
  store.commit('setToken', cachedToken)
}

// 创建Vue实例
new Vue({
  router,
  store,
  i18n,
  render: function (h) { return h(App) }
}).$mount('#app')
