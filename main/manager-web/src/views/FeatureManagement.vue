<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
          <h2 class="page-title">{{ $t('header.featureManagement') }}</h2>
        </div>

    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="feature-card" shadow="never">
            <div class="config-header">
              <div class="header-icon">
                <img loading="lazy" src="@/assets/home/equipment.png" alt="" />
              </div>
              <div class="header-actions">
                <el-button @click="!isSaving && toggleSelectAll()" class="btn-select-all" :disabled="isSaving">
                  {{ isAllSelected ? $t('featureManagement.deselectAll') : $t('featureManagement.selectAll') }}
                </el-button>
                <el-button type="primary" class="save-btn" @click="handleSave" :disabled="isSaving">
                  {{ isSaving ? $t('featureManagement.saving') : $t('featureManagement.save') }}
                </el-button>
                <el-button class="reset-btn" @click="handleReset" :disabled="isSaving">
                  {{ $t('featureManagement.reset') }}
                </el-button>
              </div>
            </div>
            <div class="divider"></div>
            
            <!-- 功能分组容器 - 左右布局 -->
            <div class="feature-groups-container">
              <!-- 功能管理分组 -->
              <div v-if="featureManagementFeatures.length > 0" class="feature-group">
                <h3 class="group-title">{{ $t('featureManagement.group.featureManagement') }}</h3>
                <div class="features-grid">
                  <div
                    v-for="feature in featureManagementFeatures"
                    :key="feature.id"
                    class="feature-card-item"
                    :class="{ 'feature-enabled': feature.enabled, 'feature-disabled': isSaving }"
                    @click="!isSaving && toggleFeature(feature)"
                  >
                    <div class="feature-header">
                      <h3 class="feature-name">{{ $t(`feature.${feature.id}.name`) }}</h3>
                      <el-checkbox
                        v-model="feature.enabled"
                        @change="!isSaving && toggleFeature(feature)"
                        class="feature-checkbox"
                        :disabled="isSaving"
                      />
                    </div>
                    <p class="feature-description">{{ $t(`feature.${feature.id}.description`) }}</p>
                  </div>
                </div>
              </div>
              
              <!-- 语音管理分组 -->
              <div v-if="voiceManagementFeatures.length > 0" class="feature-group">
                <h3 class="group-title">{{ $t('featureManagement.group.voiceManagement') }}</h3>
                <div class="features-grid">
                  <div
                    v-for="feature in voiceManagementFeatures"
                    :key="feature.id"
                    class="feature-card-item"
                    :class="{ 'feature-enabled': feature.enabled, 'feature-disabled': isSaving }"
                    @click="!isSaving && toggleFeature(feature)"
                  >
                    <div class="feature-header">
                      <h3 class="feature-name">{{ $t(`feature.${feature.id}.name`) }}</h3>
                      <el-checkbox
                        v-model="feature.enabled"
                        @change="!isSaving && toggleFeature(feature)"
                        class="feature-checkbox"
                        :disabled="isSaving"
                      />
                    </div>
                    <p class="feature-description">{{ $t(`feature.${feature.id}.description`) }}</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div v-if="filteredFeatures.length === 0" class="empty-state">
              <el-empty :description="$t('featureManagement.noFeatures')">
                <p class="empty-tip">{{ $t('featureManagement.contactAdmin') }}</p>
              </el-empty>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <el-footer>
      <VersionFooter />
    </el-footer>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import featureManager from "@/utils/featureManager.js";

export default {
  name: "FeatureManagement",
  components: {
    HeaderBar,
    VersionFooter
  },
  data() {
    return {
      pendingChanges: false,
      featureManagementFeatures: [],
      voiceManagementFeatures: [],
      isSaving: false // 添加保存状态锁定
    }
  },
  computed: {
    // 所有功能列表
    filteredFeatures() {
      return [...this.featureManagementFeatures, ...this.voiceManagementFeatures]
    },
    
    // 判断是否所有功能都已选中
    isAllSelected() {
      const allFeatures = [...this.featureManagementFeatures, ...this.voiceManagementFeatures]
      return allFeatures.length > 0 && allFeatures.every(feature => feature.enabled)
    }
  },
  async created() {
    // 等待功能配置管理器初始化完成
    try {
      await featureManager.waitForInitialization()
      await this.loadFeatures()
      this.setupConfigChangeListener()
    } catch (error) {
      console.error('功能配置管理器初始化等待失败:', error)
      await this.loadFeatures()
      this.setupConfigChangeListener()
    }
  },
  
  beforeDestroy() {
    this.removeConfigChangeListener()
  },
  
  methods: {
    // 根据ID列表获取功能
    async getFeaturesByIds(featureIds) {
      try {
        const featureConfig = await featureManager.getAllFeatures()
        const result = featureIds.map(id => {
          const feature = featureConfig[id]
          return {
            id: id,
            name: this.$t(`feature.${id}.name`),
            description: this.$t(`feature.${id}.description`),
            enabled: feature?.enabled || false
          }
        })
        
        return result
      } catch (error) {
        console.error('获取功能配置失败:', error)
        // 如果获取失败，返回默认配置
        return featureIds.map(id => ({
          id: id,
          name: this.$t(`feature.${id}.name`),
          description: this.$t(`feature.${id}.description`),
          enabled: false
        }))
      }
    },
    
    // 加载功能配置
    async loadFeatures() {
      // 保存当前用户的选择状态
      const currentFeatureStates = {}
      const allCurrentFeatures = [...this.featureManagementFeatures, ...this.voiceManagementFeatures]
      allCurrentFeatures.forEach(feature => {
        currentFeatureStates[feature.id] = feature.enabled
      })
      
      // 重新加载配置
      this.featureManagementFeatures = await this.getFeaturesByIds(['voiceprintRecognition', 'voiceClone', 'knowledgeBase', 'mcpAccessPoint'])
      this.voiceManagementFeatures = await this.getFeaturesByIds(['vad', 'asr'])
      
      // 恢复用户的选择状态（如果存在）
      const allFeatures = [...this.featureManagementFeatures, ...this.voiceManagementFeatures]
      allFeatures.forEach(feature => {
        if (currentFeatureStates.hasOwnProperty(feature.id)) {
          feature.enabled = currentFeatureStates[feature.id]
        }
      })
    },
    // 切换功能状态
    async toggleFeature(feature) {
      // 如果正在保存，阻止操作
      if (this.isSaving) {
        return
      }
      
      feature.enabled = !feature.enabled
      this.pendingChanges = true
      
      // 不再立即更新到配置管理器，只在保存时统一更新
    },
    // 保存配置
    async handleSave() {
      if (!this.pendingChanges) {
        this.$message.info({
          message: this.$t('featureManagement.noChanges'),
          showClose: true
        })
        return
      }
      
      // 设置保存状态，锁定界面
      this.isSaving = true
      
      try {
        // 获取当前所有功能的状态并保存
        const featureUpdates = {}
        const allFeatures = [...this.featureManagementFeatures, ...this.voiceManagementFeatures]
        allFeatures.forEach(feature => {
          featureUpdates[feature.id] = feature.enabled
        })
        await featureManager.updateFeatures(featureUpdates)
        
        this.pendingChanges = false
        this.$message.success({
          message: this.$t('featureManagement.saveSuccess'),
          showClose: true
        })

        setTimeout(() => {
          this.loadFeatures()
        }, 1000)
      } catch (error) {
        console.error('保存配置失败:', error)
        this.$message.error({
          message: this.$t('featureManagement.saveError'),
          showClose: true
        })
      } finally {
        // 无论成功与否，都解除保存状态锁定
        this.isSaving = false
      }
    },
    // 设置配置变化监听器
    setupConfigChangeListener() {
      this.configChangeHandler = () => {
        this.loadFeatures()
      }
      window.addEventListener('featureConfigReloaded', this.configChangeHandler)
    },
    
    // 移除配置变化监听器
    removeConfigChangeListener() {
      if (this.configChangeHandler) {
        window.removeEventListener('featureConfigReloaded', this.configChangeHandler)
      }
    },
    
    // 重置配置
    async handleReset() {
      try {
        await this.$confirm(
          this.$t('featureManagement.resetConfirm'),
          this.$t('featureManagement.reset'),
          {
            confirmButtonText: this.$t('featureManagement.confirm'),
            cancelButtonText: this.$t('featureManagement.cancel'),
            type: 'warning'
          }
        )
        
        featureManager.resetToDefault()
        this.loadFeatures()
        this.pendingChanges = false
        
        this.$message.success({
          message: this.$t('featureManagement.resetSuccess'),
          showClose: true
        })
        
        setTimeout(() => {
          this.loadFeatures()
          this.$router.go(0)
        }, 1000)
      } catch (error) {
        // 用户取消操作
      }
    },
    // 搜索功能（预留接口）
    handleSearch() {
      // 搜索功能待实现
    },
    // 全选/取消全选
    toggleSelectAll() {
      // 如果正在保存，阻止操作
      if (this.isSaving) {
        return
      }
      
      const allFeatures = [...this.featureManagementFeatures, ...this.voiceManagementFeatures]
      const newStatus = !this.isAllSelected
      
      allFeatures.forEach(feature => {
        feature.enabled = newStatus
      })
      
      this.pendingChanges = true
    }
  }
}
</script>

<style scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background-size: cover;
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd) center;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
}

.page-title {
  font-size: 24px;
  margin: 0;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 16px 0;
}

.header-icon {
  width: 40px;
  height: 40px;
  background: #5778ff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
}

.header-icon img {
  width: 20px;
  height: 20px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.divider {
  height: 1px;
  background: #e0e0e0;
  margin-bottom: 20px;
}

.btn-select-all {
  background: #e6ebff;
  color: #5778ff;
  border: 1px solid #adbdff;
  border-radius: 18px;
  padding: 8px 16px;
  height: 32px;
  font-size: 14px;
}

.btn-select-all:hover {
  background: #d0d8ff;
}

.save-btn {
  background: #5778ff;
  color: white;
  border: none;
  border-radius: 18px;
  padding: 8px 16px;
  height: 32px;
  font-size: 14px;
}

.save-btn:hover {
  background: #4a6ae8;
}

.reset-btn {
  background: #e6ebff;
  color: #5778ff;
  border: 1px solid #adbdff;
  border-radius: 18px;
  padding: 8px 16px;
  height: 32px;
}

.reset-btn:hover {
  background: #d0d8ff;
}

.main-wrapper {
  margin: 0 22px 5px 22px;
  border-radius: 15px;
  min-height: calc(100vh - 24vh);
  height: auto;
  max-height: 80vh;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  background: rgba(237, 242, 255, 0.5);
  display: flex;
  flex-direction: column;
}

.content-panel {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.content-area {
  flex: 1;
  height: 100%;
  min-width: 600px;
  overflow: auto;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.feature-card {
  background: white;
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
  overflow: hidden;
}

.feature-card ::v-deep .el-card__body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.feature-card-item {
  display: flex;
  flex-direction: column;
  padding: 20px;
  border-radius: 12px;
  border: 2px solid #e0e0e0;
  background-color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
  position: relative;
}

.feature-card-item:hover {
  border-color: #869bf0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.feature-card-item.feature-enabled {
  border-color:#5778ff;
  box-shadow: 0 4px 16px rgba(95, 112, 243, 0.2);
  transform: translateY(-2px);
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.feature-checkbox ::v-deep .el-checkbox__input {
  transform: scale(1.2);
}

.feature-checkbox ::v-deep .el-checkbox__input.is-checked .el-checkbox__inner {
  background-color: #5778ff;
  border-color: #5778ff;
}

.feature-checkbox ::v-deep .el-checkbox__input.is-checked + .el-checkbox__label {
  color: #5778ff;
}


.feature-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0;
  transition: color 0.3s ease;
}


.feature-description {
  font-size: 14px;
  line-height: 1.6;
  color: #666;
  margin: 0 0 12px 0;
  transition: color 0.3s ease;
  text-align: left;
}


/* 功能分组容器 - 左右布局 */
.feature-groups-container {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  position: relative;
}

/* 分组之间的分隔线 */
.feature-groups-container::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  height: 550px;
  background: #e0e0e0;
  opacity: 0.5;
  transform: translateX(-50%);
}

/* 分组样式 */
.feature-group {
  flex: 1;
  min-width: 0;
  margin-bottom: 32px;
}

.group-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  padding-left: 12px;
  border-left: 4px solid #5f70f3;
  text-align: left;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
</style>