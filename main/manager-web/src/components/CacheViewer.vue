<template>
  <el-dialog
    :title="$t('cache.dialogTitle')"
    :visible.sync="visible"
    width="70%"
    :before-close="handleClose"
  >
    <div v-if="isLoading" class="loading-container">
      <p>{{ $t('cache.loading') }}</p>
    </div>
    
    <div v-else>
      <div v-if="!cacheAvailable" class="no-cache-message">
        <i class="el-icon-warning-outline"></i>
        <p>{{ $t('cache.notSupported') }}</p>
        <el-button type="primary" @click="refreshPage">{{ $t('cache.refreshPage') }}</el-button>
      </div>
      
      <div v-else>
        <el-alert
            v-if="cacheData.totalCached === 0"
            :title="$t('cache.noCachedResources')"
            type="warning"
            :closable="false"
            show-icon
          >
            <p>{{ $t('cache.noCachedResourcesDesc') }}</p>
          </el-alert>
        
        <div v-else>
          <el-alert
            :title="$t('cache.cdnCacheStatus')"
            type="success"
            :closable="false"
            show-icon
          >
            {{ $t('cache.totalCachedResources').replace('{count}', cacheData.totalCached) }}
          </el-alert>
          
          <h3>{{ $t('cache.jsResources').replace('{count}', cacheData.js.length) }}</h3>
          <el-table :data="cacheData.js" stripe style="width: 100%">
            <el-table-column prop="url" label="URL" width="auto" show-overflow-tooltip />
            <el-table-column prop="cached" :label="$t('cache.status')" width="100">
              <template slot-scope="scope">
                <el-tag type="success" v-if="scope.row.cached">{{ $t('cache.cached') }}</el-tag>
                <el-tag type="danger" v-else>{{ $t('cache.notCached') }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          
          <h3>{{ $t('cache.cssResources').replace('{count}', cacheData.css.length) }}</h3>
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
      <el-button @click="handleClose">{{ $t('button.close') }}</el-button>
      <el-button type="primary" @click="refreshCache">{{ $t('cache.refreshStatus') }}</el-button>
      <el-button type="danger" @click="clearCache">{{ $t('cache.clearCache') }}</el-button>
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
      this.$message.success(this.$t('cache.refreshingStatus'));
    },
    
    async clearCache() {
      this.$confirm(this.$t('cache.confirmClear'), this.$t('message.warning'), {
        confirmButtonText: this.$t('button.ok'),
        cancelButtonText: this.$t('button.cancel'),
        type: 'warning'
      }).then(async () => {
        try {
          const success = await clearAllCaches();
          if (success) {
            this.$message.success(this.$t('cache.clearedSuccess'));
            await this.loadCacheData();
          } else {
            this.$message.error(this.$t('cache.clearFailed'));
          }
        } catch (error) {
          console.error('清除缓存失败:', error);
          this.$message.error(this.$t('cache.clearFailed'));
        }
      }).catch(() => {
        this.$message.info(this.$t('cache.clearCanceled'));
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