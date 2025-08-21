<template>
  <el-dialog
    title="CDN资源缓存状态"
    :visible.sync="visible"
    width="70%"
    :before-close="handleClose"
  >
    <div v-if="isLoading" class="loading-container">
      <p>正在加载缓存信息...</p>
    </div>
    
    <div v-else>
      <div v-if="!cacheAvailable" class="no-cache-message">
        <i class="el-icon-warning-outline"></i>
        <p>您的浏览器不支持Cache API或Service Worker未安装</p>
        <el-button type="primary" @click="refreshPage">刷新页面</el-button>
      </div>
      
      <div v-else>
        <el-alert
          v-if="cacheData.totalCached === 0"
          title="未发现缓存的CDN资源"
          type="warning"
          :closable="false"
          show-icon
        >
          <p>Service Worker可能尚未完成初始化或缓存尚未建立。请刷新页面或等待一会后再试。</p>
        </el-alert>
        
        <div v-else>
          <el-alert
            title="CDN资源缓存状态"
            type="success"
            :closable="false"
            show-icon
          >
            共发现 {{ cacheData.totalCached }} 个缓存资源
          </el-alert>
          
          <h3>JavaScript 资源 ({{ cacheData.js.length }})</h3>
          <el-table :data="cacheData.js" stripe style="width: 100%">
            <el-table-column prop="url" label="URL" width="auto" show-overflow-tooltip />
            <el-table-column prop="cached" label="状态" width="100">
              <template slot-scope="scope">
                <el-tag type="success" v-if="scope.row.cached">已缓存</el-tag>
                <el-tag type="danger" v-else>未缓存</el-tag>
              </template>
            </el-table-column>
          </el-table>
          
          <h3>CSS 资源 ({{ cacheData.css.length }})</h3>
          <el-table :data="cacheData.css" stripe style="width: 100%">
            <el-table-column prop="url" label="URL" width="auto" show-overflow-tooltip />
            <el-table-column prop="cached" label="状态" width="100">
              <template slot-scope="scope">
                <el-tag type="success" v-if="scope.row.cached">已缓存</el-tag>
                <el-tag type="danger" v-else>未缓存</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
    
    <span slot="footer" class="dialog-footer">
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" @click="refreshCache">刷新缓存状态</el-button>
      <el-button type="danger" @click="clearCache">清除缓存</el-button>
    </span>
  </el-dialog>
</template>

<script>
import {
  getCacheNames,
  checkCdnCacheStatus,
  clearAllCaches,
  logCacheStatus
} from '../utils/cacheViewer';

export default {
  name: 'CacheViewer',
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      isLoading: true,
      cacheAvailable: false,
      cacheData: {
        css: [],
        js: [],
        totalCached: 0,
        totalNotCached: 0
      }
    };
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.loadCacheData();
      }
    }
  },
  methods: {
    async loadCacheData() {
      this.isLoading = true;
      
      try {
        // 先检查是否支持缓存API
        if (!('caches' in window)) {
          this.cacheAvailable = false;
          this.isLoading = false;
          return;
        }
        
        // 检查是否有Service Worker缓存
        const cacheNames = await getCacheNames();
        this.cacheAvailable = cacheNames.length > 0;
        
        if (this.cacheAvailable) {
          // 获取CDN缓存状态
          this.cacheData = await checkCdnCacheStatus();
          
          // 在控制台输出完整缓存状态
          await logCacheStatus();
        }
      } catch (error) {
        console.error('加载缓存数据失败:', error);
        this.$message.error('加载缓存数据失败');
      } finally {
        this.isLoading = false;
      }
    },
    
    async refreshCache() {
      this.loadCacheData();
      this.$message.success('正在刷新缓存状态');
    },
    
    async clearCache() {
      this.$confirm('确定要清除所有缓存吗?', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const success = await clearAllCaches();
          if (success) {
            this.$message.success('缓存已清除');
            await this.loadCacheData();
          } else {
            this.$message.error('清除缓存失败');
          }
        } catch (error) {
          console.error('清除缓存失败:', error);
          this.$message.error('清除缓存失败');
        }
      }).catch(() => {
        this.$message.info('已取消清除');
      });
    },
    
    refreshPage() {
      window.location.reload();
    },
    
    handleClose() {
      this.$emit('update:visible', false);
    }
  }
};
</script>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.loading-spinner {
  margin-bottom: 10px;
}

.no-cache-message {
  text-align: center;
  padding: 20px;
}

.no-cache-message i {
  font-size: 48px;
  color: #E6A23C;
  margin-bottom: 10px;
}

h3 {
  margin-top: 20px;
  margin-bottom: 10px;
  font-weight: 500;
}
</style> 