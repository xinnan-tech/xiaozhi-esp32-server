import axios from 'axios'

const api = axios.create({
  baseURL: "http://localhost:8002/xiaozhi-esp32-api",
  timeout: 10000,


})

// 请求拦截器
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => {
    if (response.data.code !== 200) {
      return Promise.reject(response.data)
    }
    return response.data
  },
  error => {
    if (error.response.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api