import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/pages/index/index'
  },
  {
    path: '/pages/index/index',
    name: 'Home',
    component: () => import('../pages/index/index-simple.vue')
  },
  {
    path: '/pages/login/index',
    name: 'Login',
    component: () => import('../pages/login/index.vue')
  },
  {
    path: '/pages/device/index',
    name: 'Device',
    component: () => import('../pages/device/index.vue')
  },
  {
    path: '/pages/agent/index',
    name: 'Agent',
    component: () => import('../pages/agent/index.vue')
  },
  {
    path: '/pages/chat-history/index',
    name: 'ChatHistory',
    component: () => import('../pages/chat-history/index.vue')
  },
  {
    path: '/pages/settings/index',
    name: 'Settings',
    component: () => import('../pages/settings/index.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router