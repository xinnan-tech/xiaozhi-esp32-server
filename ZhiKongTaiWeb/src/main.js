import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import Login from './components/Login.vue'
import Panel from './components/panel.vue'
import MainPage from './components/Main.vue'
import RoleSetting from './components/RoleSetting.vue'
import Registration from './components/Registration.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { 
      path: '/login',
      component: Login,
      name: 'login'
    },
    {
      path: '/register',
      component: Registration,
      name: 'register'
    },
    {
      path: '/panel',
      component: Panel,
      name: 'panel',
      meta: { requiresAuth: true }
    },
    {
      path: '/role-setting/:deviceId',
      component: RoleSetting,
      name: 'role-setting',
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      component: MainPage,
      name: 'main',
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach((to, from, next) => {
  const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true'
  if (to.meta.requiresAuth && !isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && isLoggedIn) {
    next('/panel')
  } else {
    next()
  }
})

const app = createApp(App)
app.use(router)
app.mount('#app')
