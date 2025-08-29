import './uni-polyfill'
import { createApp as createVueApp } from 'vue'
import App from './App.vue'
import store from './store'
import router from './router'

// Use createApp instead of createSSRApp for client-side only
const app = createVueApp(App)
app.use(store)
app.use(router)

// Mount immediately for H5
if (typeof window !== 'undefined' && document.getElementById('app')) {
  // Clear the loading message before mounting
  const appEl = document.getElementById('app')
  if (appEl) {
    appEl.innerHTML = ''
  }
  app.mount('#app')
}

export function createApp() {
  return {
    app,
  }
}
