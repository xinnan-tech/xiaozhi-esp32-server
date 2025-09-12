import ElementUI from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';
import 'normalize.css/normalize.css'; // A modern alternative to CSS resets
import Vue from 'vue';
import App from './App.vue';
import router from './router';
import store from './store';
import i18n from './i18n';
import './styles/global.scss';
import { register as registerServiceWorker } from './registerServiceWorker';

// 创建事件总线，用于组件间通信
Vue.prototype.$eventBus = new Vue();

Vue.use(ElementUI);

Vue.config.productionTip = false

// 注册Service Worker
registerServiceWorker();

// 创建Vue实例
new Vue({
  router,
  store,
  i18n,
  render: function (h) { return h(App) }
}).$mount('#app')
