import axios from 'axios';
import { API_BASE_URL } from '../config/api';

// Add server status check utility
export const checkServerStatus = async () => {
  try {
    await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
    return true;
  } catch (error) {
    return false;
  }
};

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000  // Add timeout
});

// 添加请求拦截器，自动添加 session_id
apiClient.interceptors.request.use(config => {
  const sessionId = localStorage.getItem('session_id');
  if (sessionId) {
    config.headers.Authorization = sessionId;
  }
  return config;
});

// 响应拦截器
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Network error or server not reachable
    if (!error.response || error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
      localStorage.removeItem('session_id');
      localStorage.removeItem('isLoggedIn');
      
      const errorMessage = error.code === 'ECONNABORTED' 
        ? '服务器响应超时'
        : '无法连接到服务器，请检查服务器是否正常运行';
      
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(new Error(errorMessage));
    }

    // Unauthorized error
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('session_id');
      localStorage.removeItem('isLoggedIn');
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
