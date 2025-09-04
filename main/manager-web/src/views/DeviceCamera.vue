<template>
  <div class="device-camera-page">
    <!-- 公共头部 -->
    <HeaderBar :devices="[]" @search="handleSearch" @search-reset="handleSearchReset" />
    
    <el-main style="padding: 20px;">
      <div class="camera-container">
        <h2>设备摄像头</h2>
    
        <div style="margin:12px 0">
          <label>Device ID(MAC)：</label>
          <input v-model="deviceId" placeholder="例: 80:b5:4e:c7:78:a4" style="width:320px;padding:6px" />
          <button @click="start" :disabled="loading" style="margin-left:8px">开始</button>
          <button @click="stop" :disabled="loading" style="margin-left:8px">停止</button>
          <button @click="testConnection" style="margin-left:8px;background:#ff9800;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer">测试连接</button>
          <button @click="testSimpleGet" style="margin-left:8px;background:#9c27b0;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer">简单测试</button>
        </div>
    
        <div v-if="deviceId" style="margin-top:12px">
          <img v-if="streamUrl" :src="streamUrl" @error="onImgError" style="max-width:100%;border:1px solid #ccc" />
          <div v-else style="padding:20px;text-align:center;color:#888;">
            点击"开始"按钮启动摄像头流
          </div>
        </div>
    
        <p v-if="msg" style="margin-top:8px;color:#888">{{ msg }}</p>
      </div>
    </el-main>
    
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>
  
  <script>
  import HeaderBar from '@/components/HeaderBar.vue';
  import VersionFooter from '@/components/VersionFooter.vue';

  export default {
    name: 'DeviceCamera',
    components: {
      HeaderBar,
      VersionFooter
    },
    data() {
      return {
        // 默认填日志里的示例，可改
        deviceId: '80:b5:4e:c7:78:a4',
        loading: false,
        bust: Date.now(),
        msg: ''
      };
    },
    computed: {
      apiBase() {
        // 直接连接 Python 服务器，端口是8003
        return `${window.location.protocol}//${window.location.hostname}:8003`;
      },
      encodedId() {
        return encodeURIComponent(this.deviceId || '');
      },
      streamUrl() {
        if (!this.deviceId) return '';
        // 直接连接 Python 服务器的摄像头流端点
        return `${this.apiBase}/camera/${this.encodedId}/stream?ts=${this.bust}`;
      },
      authToken() {
        // 正确获取token，登录时存储的是JSON字符串，需要解析
        try {
          const tokenData = localStorage.getItem('token');
          if (tokenData) {
            const parsed = JSON.parse(tokenData);
            return parsed.token || parsed.accessToken || tokenData;
          }
        } catch (e) {
          // 如果解析失败，直接返回原始值
          return localStorage.getItem('token') || '';
        }
        return '';
      }
    },
    methods: {
      // 处理搜索相关的方法
      handleSearch(regex) {
        // 设备摄像头页面不需要搜索功能，但需要实现接口
      },
      handleSearchReset() {
        // 设备摄像头页面不需要搜索功能，但需要实现接口
      },
      async start() {
        if (!this.deviceId) return;
        this.loading = true;
        this.msg = '';
        
        try {
          // 直接连接 Python 服务器的摄像头控制端点
          const xhr = new XMLHttpRequest();
          xhr.open('POST', `${this.apiBase}/camera/${this.encodedId}/start`, true);
          xhr.setRequestHeader('Content-Type', 'application/json');
          
          xhr.onload = () => {
            if (xhr.status === 200) {
              this.msg = '启动成功！正在获取视频流...';
              // 启动成功后，手动获取视频流
              this.startVideoStream();
            } else {
              this.msg = `启动失败！状态码: ${xhr.status}, 响应: ${xhr.responseText}`;
            }
            this.loading = false;
          };
          
          xhr.onerror = () => {
            this.msg = '启动失败：网络错误';
            this.loading = false;
          };
          
          // 允许动态调参，这里我们请求一个中等质量的流
          xhr.send(JSON.stringify({ fps: 8, quality: 12 }));
          
        } catch (e) {
          this.msg = '启动失败：' + e.message;
          this.loading = false;
        }
      },
      
      async startVideoStream() {
        try {
          // 对于MJPEG流，我们需要创建一个新的Image对象并设置src
          // 但是先尝试直接设置URL，看看是否能工作
          this.bust = Date.now();
          this.msg = '视频流已启动，等待画面显示...';
          
          // 设置一个定时器，如果5秒内没有画面，显示错误信息
          setTimeout(() => {
            if (!this.streamUrl) {
              this.msg = '视频流启动超时，请检查设备状态';
            }
          }, 5000);
          
        } catch (e) {
          this.msg = '启动视频流失败：' + e.message;
        }
      },
      async stop() {
        if (!this.deviceId) return;
        this.loading = true;
        this.msg = '';
        
        try {
          // 直接连接 Python 服务器的摄像头控制端点
          const xhr = new XMLHttpRequest();
          xhr.open('POST', `${this.apiBase}/camera/${this.encodedId}/stop`, true);
          
          xhr.onload = () => {
            if (xhr.status === 200) {
              this.msg = '停止成功！';
              // 清空流，或保留最后帧：这里选择刷新让其断流
              this.bust = Date.now();
            } else {
              this.msg = `停止失败！状态码: ${xhr.status}, 响应: ${xhr.responseText}`;
            }
            this.loading = false;
          };
          
          xhr.onerror = () => {
            this.msg = '停止失败：网络错误';
            this.loading = false;
          };
          
          xhr.send();
          
        } catch (e) {
          this.msg = '停止失败：' + e.message;
          this.loading = false;
        }
      },
      onImgError() {
        // 初次 503/404 等待重试
        this.msg = '等待设备开始推流或网络可用...';
        setTimeout(() => (this.bust = Date.now()), 3000);
      },
      async testConnection() {
        this.msg = '正在测试Python服务器连接...';
        
        console.log('完整请求URL:', `${this.apiBase}/camera/${this.encodedId}/start`);
        
        try {
          const response = await fetch(`${this.apiBase}/camera/${this.encodedId}/start`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ fps: 5, quality: 8 })
          });
          
          console.log('响应状态:', response.status);
          console.log('响应头:', Object.fromEntries(response.headers.entries()));
          
          if (response.ok) {
            this.msg = `Python服务器连接成功！状态码: ${response.status}`;
          } else {
            const responseText = await response.text();
            console.log('错误响应内容:', responseText);
            this.msg = `Python服务器连接失败！状态码: ${response.status}, 响应: ${responseText}`;
          }
        } catch (e) {
          console.error('请求异常:', e);
          this.msg = 'Python服务器连接测试失败：' + e.message;
        }
      },
      async testSimpleGet() {
        this.msg = '正在测试简单GET请求...';
        try {
          const response = await fetch(`${this.apiBase}/camera/${this.encodedId}/stream?ts=${Date.now()}`, {
            method: 'GET'
          });
          if (response.ok) {
            this.msg = `简单GET请求成功！状态码: ${response.status}`;
          } else {
            const responseText = await response.text();
            this.msg = `简单GET请求失败！状态码: ${response.status}, 响应: ${responseText}`;
          }
        } catch (e) {
          this.msg = '简单GET请求失败：' + e.message;
        }
      },
      goCamera() {
        this.$router.push('/device/camera');
      }
    }
  };
  </script>