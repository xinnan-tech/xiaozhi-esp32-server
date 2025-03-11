import axios from 'axios'

const api = axios.create({
  baseURL: "http://localhost:8002/xiaozhi-esp32-api",
  timeout: 30000,


})

// 请求拦截器
api.interceptors.request.use(config => {
  // 打印请求信息
  console.log('请求信息：', {
    method: config.method.toUpperCase(),
    url: config.baseURL + config.url,
    params: config.params,
    data: config.data
  });
  
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
})

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 打印响应信息
    console.log('响应数据：', {
      status: response.status,
      data: response.data,
      headers: response.headers
    });
    
    if (response.status !== 200) {
      return Promise.reject(response.data)
    }
    return response
  },
  error => {
    // 打印错误信息
    console.error('请求错误：', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api