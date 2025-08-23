import { createApp } from 'vue'
import App from './App.vue'

console.log('main-simple.ts loaded')

const app = createApp(App)
console.log('Vue app created', app)

app.mount('#app')
console.log('Vue app mounted to #app')

export { app }