<template>
  <div class="registration-container">
    <h1>注册</h1>
    <form @submit.prevent="handleRegistration">
      <div class="form-group">
        <label for="username">用户名</label>
        <input type="text" v-model="username" id="username" required />
      </div>
      <div class="form-group">
        <label for="password">密码</label>
        <input type="password" v-model="password" id="password" required />
      </div>
      <div class="form-group">
        <label for="confirmPassword">确认密码</label>
        <input type="password" v-model="confirmPassword" id="confirmPassword" required />
      </div>
      <button type="submit" :disabled="isLoading">{{ isLoading ? '注册中...' : '注册' }}</button>
    </form>
    <p>
      已有账号？
      <router-link to="/login">点击登录</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { API_BASE_URL } from '../config/api';

const router = useRouter();
const username = ref('');
const password = ref('');
const confirmPassword = ref('');
const isLoading = ref(false);

const handleRegistration = async () => {
  if (password.value !== confirmPassword.value) {
    alert('密码不匹配，请重试！');
    return;
  }

  if (!username.value || !password.value) {
    alert('用户名和密码不能为空！');
    return;
  }

  isLoading.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    });

    const data = await response.json();
    
    if (data.success) {
      alert('注册成功！即将跳转到登录页面。');
      // 清空表单数据
      username.value = '';
      password.value = '';
      confirmPassword.value = '';
      
      // 使用路由导航到登录页面
      router.push('/login');
    } else {
      alert(data.message || '注册失败');
    }
  } catch (error) {
    console.error('Registration error:', error);
    alert('注册失败，请检查网络连接');
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.registration-container {
  max-width: 420px;
  margin: 20px auto;
  padding: 40px 50px;
  border: none;
  border-radius: 12px;
  background-color: #ffffff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transition: all 0.3s ease;
}

h1 {
  text-align: center;
  color: #2c3e50;
  font-size: 28px;
  margin-bottom: 25px;
  font-weight: 600;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #4a5568;
}

input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background-color: #f8fafc;
  transition: all 0.3s ease;
  font-size: 15px;
}

input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.2);
}

button {
  width: 100%;
  padding: 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s ease;
  margin-top: 10px;
}

button:hover {
  background-color: #0056b3;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.2);
}

button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

p {
  margin-top: 20px;
  color: #666;
  font-size: 14px;
}

a {
  color: #007bff;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
}

a:hover {
  color: #0056b3;
  text-decoration: underline;
}
</style>