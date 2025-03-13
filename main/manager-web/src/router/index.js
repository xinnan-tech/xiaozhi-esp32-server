import Vue from 'vue'
import VueRouter from 'vue-router'
import Welcome from '../views/welcome.vue'
import Login from '../views/login.vue'
import Register from '@/views/register.vue' 

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'welcome',
    component: Login
  },
  {
    path: '/login',
    name: 'login',
    // route level code-splitting
    // this generates a separate chunk (about.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    component: function () {
      return import(/* webpackChunkName: "about" */ '../views/login.vue')
    }
  },
  {
    path: '/home',
    name: 'home',
    component: function () {
      return import(/* webpackChunkName: "about" */ '../views/home.vue')
    }
  },
  {
    path: '/register',
    name: 'Register',
    // route level code-splitting
    // this generates a separate chunk (about.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    component: function () {
      return import(/* webpackChunkName: "about" */ '../views/register.vue')
    }
  },
]

const router = new VueRouter({
  routes
})

export default router
