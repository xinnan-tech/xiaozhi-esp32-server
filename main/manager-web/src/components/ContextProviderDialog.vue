<template>
  <el-dialog
    :visible.sync="dialogVisible"
    width="900px"
    :title="$t('contextProviderDialog.title')"
    :close-on-click-modal="false"
    custom-class="context-provider-dialog"
    append-to-body
  >
    <div class="dialog-content">
      <el-empty v-if="localProviders.length === 0" :description="$t('contextProviderDialog.noContextApi')">
        <el-button type="primary" icon="el-icon-plus" @click="addProvider(0)">{{ $t('contextProviderDialog.add') }}</el-button>
      </el-empty>

      <div
        v-for="(provider, pIndex) in localProviders"
        :key="pIndex"
        class="provider-item"
      >
        <el-card class="provider-card" shadow="hover" :body-style="{ padding: '15px 20px' }">
          <!-- URL Row -->
          <div class="input-row">
            <span class="label-text">{{ $t('contextProviderDialog.apiUrl') }}</span>
            <el-input
              v-model="provider.url"
              :placeholder="$t('contextProviderDialog.apiUrlPlaceholder')"
              size="small"
              class="flex-1"
            ></el-input>
          </div>

          <!-- Headers Section -->
          <div class="headers-section">
            <div class="label-text" style="margin-top: 6px;">{{ $t('contextProviderDialog.requestHeaders') }}</div>
            <div class="headers-list">
              <div
                v-for="(header, hIndex) in provider.headers"
                :key="hIndex"
                class="header-row"
              >
                <el-input
                  v-model="header.key"
                  :placeholder="$t('contextProviderDialog.headerKeyPlaceholder')"
                  size="small"
                  style="width: 180px;"
                ></el-input>
                <span class="separator">:</span>
                <el-input
                  v-model="header.value"
                  :placeholder="$t('contextProviderDialog.headerValuePlaceholder')"
                  size="small"
                  class="flex-1"
                ></el-input>
                
                <div class="row-controls">
                  <el-button
                    type="primary"
                    icon="el-icon-plus"
                    circle
                    size="mini"
                    plain
                    @click="addHeader(pIndex, hIndex + 1)"
                  ></el-button>
                  <el-button
                    type="danger"
                    icon="el-icon-minus"
                    circle
                    size="mini"
                    plain
                    @click="removeHeader(pIndex, hIndex)"
                  ></el-button>
                </div>
              </div>
              <!-- Empty Headers State -->
              <div v-if="provider.headers.length === 0" class="header-row empty-header">
                 <span class="no-header-text">{{ $t('contextProviderDialog.noHeaders') }}</span>
                 <el-button
                    type="text"
                    icon="el-icon-plus"
                    size="mini"
                    @click="addHeader(pIndex, 0)"
                  >{{ $t('contextProviderDialog.addHeader') }}</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- Provider Block Controls (Right Side) -->
        <div class="block-controls">
          <el-button
            type="primary"
            icon="el-icon-plus"
            circle
            size="medium"
            @click="addProvider(pIndex + 1)"
          ></el-button>
          <el-button
            type="danger"
            icon="el-icon-minus"
            circle
            size="medium"
            @click="removeProvider(pIndex)"
          ></el-button>
        </div>
      </div>
    </div>

    <span slot="footer" class="dialog-footer">
      <el-button @click="dialogVisible = false">{{ $t('contextProviderDialog.cancel') }}</el-button>
      <el-button type="primary" @click="handleConfirm">{{ $t('contextProviderDialog.confirm') }}</el-button>
    </span>
  </el-dialog>
</template>

<script>
export default {
  name: 'ContextProviderDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    providers: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      localProviders: []
    };
  },
  computed: {
    dialogVisible: {
      get() {
        return this.visible;
      },
      set(val) {
        this.$emit('update:visible', val);
      }
    }
  },
  watch: {
    visible(val) {
      if (val) {
        this.initLocalData();
      }
    }
  },
  methods: {
    initLocalData() {
      // 深拷贝并将 headers 对象转换为数组
      this.localProviders = this.providers.map(p => {
        const headers = p.headers || {};
        return {
          url: p.url || '',
          headers: Object.entries(headers).map(([key, value]) => ({ key, value }))
        };
      });
      
      // 如果为空，添加一个默认块
      if (this.localProviders.length === 0) {
         this.localProviders.push({ url: '', headers: [{ key: '', value: '' }] });
      }
    },
    addProvider(index) {
      this.localProviders.splice(index, 0, {
        url: '',
        headers: [{ key: '', value: '' }]
      });
    },
    removeProvider(index) {
      this.localProviders.splice(index, 1);
    },
    addHeader(pIndex, hIndex) {
      this.localProviders[pIndex].headers.splice(hIndex, 0, { key: '', value: '' });
    },
    removeHeader(pIndex, hIndex) {
      this.localProviders[pIndex].headers.splice(hIndex, 1);
    },
    handleConfirm() {
      const result = this.localProviders
        .filter(p => p.url.trim() !== '')
        .map(p => {
          const headersObj = {};
          p.headers.forEach(h => {
            if (h.key.trim()) {
              headersObj[h.key.trim()] = h.value;
            }
          });
          return {
            url: p.url.trim(),
            headers: headersObj
          };
        });
      
      this.$emit('confirm', result);
      this.dialogVisible = false;
    }
  }
};
</script>

<style scoped>
.dialog-content {
  max-height: 60vh;
  overflow-y: auto;
  padding: 20px 25px;
}

.dialog-content::-webkit-scrollbar {
  width: 6px;
}
.dialog-content::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}
.dialog-content::-webkit-scrollbar-track {
  background: #f5f7fa;
}

.provider-item {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  align-items: center;
}

.provider-card {
  flex: 1;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  border-left: 4px solid #409EFF; /* 左侧强调色 */
  background-color: #fff;
  transition: all 0.3s ease;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.provider-card:hover {
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.block-controls {
  display: flex;
  flex-direction: row;
  gap: 8px;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.label-text {
  width: 60px;
  font-weight: 600;
  color: #606266;
  text-align: right;
  font-size: 13px;
  white-space: nowrap;
  line-height: 32px; /* 垂直居中对齐 */
}

.flex-1 {
  flex: 1;
}

.headers-section {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.headers-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #fcfcfc;
  padding: 15px;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
  transition: all 0.3s;
}

.headers-list:hover {
  border-color: #c0c4cc;
  background: #fff;
}

.header-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.separator {
  color: #909399;
  font-weight: bold;
  margin: 0 2px;
}

.row-controls {
  display: flex;
  gap: 6px;
  margin-left: 8px;
  flex-shrink: 0;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.header-row:hover .row-controls {
  opacity: 1;
}

.empty-header {
  justify-content: center;
  padding: 10px;
  color: #909399;
  font-size: 13px;
}

.no-header-text {
  margin-right: 8px;
}
</style>
