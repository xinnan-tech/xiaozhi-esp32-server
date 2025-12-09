<template>
  <el-dialog
    :visible.sync="dialogVisible"
    width="700px"
    :title="$t('device.customThemeGenerateModalTitle')"
    :close-on-click-modal="false"
    :close-on-press-escape="true"
    :modal-append-to-body="true"
    :append-to-body="true"
    :lock-scroll="true"
    @close="handleClose"
    custom-class="generate-modal-dialog"
  >
    <!-- 第一步：配置确认页面 -->
    <div v-if="!isGenerating && !isCompleted" class="config-confirm-page">
      <!-- 配置确认 -->
      <div class="config-section">
        <h4 class="section-title">请确认您的配置</h4>
        <div class="config-info-box">
          <div class="config-item">
            <span class="config-label">芯片型号:</span>
            <span class="config-value">{{ getChipModel() }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">分辨率:</span>
            <span class="config-value">{{ getResolution() }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">唤醒词:</span>
            <span class="config-value">{{ getWakewordName() }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">字体:</span>
            <span class="config-value">{{ getFontName() }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">表情包:</span>
            <span class="config-value">{{ getEmojiName() }}</span>
          </div>
        </div>
      </div>

      <!-- 文件列表 -->
      <div class="file-list-section">
        <h4 class="section-title">包含的文件列表</h4>
        <div class="file-list-container">
          <div
            v-for="item in fileList"
            :key="item.id"
            class="file-item"
          >
            <div class="file-info-left">
              <i :class="item.iconClass" :style="{ color: item.iconColor }"></i>
              <span class="file-name">{{ item.name }}</span>
            </div>
            <div class="file-size">
              {{ item.size }}
              <span v-if="item.estimated" class="estimated">预估</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 第二步：生成进度页面 -->
    <div v-if="isGenerating" class="generating-page">
      <div class="loading-spinner-container">
        <div class="loading-spinner"></div>
      </div>
      
      <div class="progress-section">
        <p class="progress-title">正在生成 assets.bin</p>
        <div class="progress-bar-container">
          <div 
            class="progress-bar-fill"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <div class="progress-info">
          <div class="current-step">{{ currentStep }}</div>
          <div class="progress-percent">{{ progress }}% 完成</div>
        </div>
      </div>

      <!-- 进度步骤列表 -->
      <div class="progress-steps-list">
        <div
          v-for="step in progressSteps"
          :key="step.id"
          class="progress-step-item"
        >
          <div class="step-icon">
            <i v-if="step.status === 'completed'" class="el-icon-check step-check-icon"></i>
            <div v-else-if="step.status === 'processing'" class="step-processing-dot"></div>
            <div v-else class="step-pending-dot"></div>
          </div>
          <span :class="[
            'step-name',
            step.status === 'completed' ? 'step-completed' : 
            step.status === 'processing' ? 'step-processing' : 
            'step-pending'
          ]">{{ step.name }}</span>
        </div>
      </div>
    </div>

    <!-- 第三步：完成页面 -->
    <div v-if="isCompleted && !isGenerating" class="completed-page">
      <div class="success-icon">
        <i class="el-icon-success"></i>
      </div>
      <div class="success-text">assets.bin 已生成完成</div>
      <div class="result-box">
        <div class="result-item">文件名: assets.bin</div>
        <div class="result-item">文件大小: {{ generatedFileSize }}</div>
        <div class="result-item">生成时间: {{ generationTime }}</div>
      </div>
      <div class="action-buttons column">
        <el-button type="primary" @click="downloadFile" :disabled="!generatedBlob" class="action-btn full">
          下载 assets.bin
        </el-button>
        <el-button type="primary" plain @click="startOnlineFlash" :disabled="!generatedBlob" class="action-btn secondary full">
          在线烧录到设备
        </el-button>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div slot="footer" class="dialog-footer" v-if="!isGenerating && !isCompleted">
      <el-button @click="handleClose">
        取消
      </el-button>
      <el-button
        type="primary"
        @click="startGeneration"
        :disabled="!hasSelectedFiles"
      >
        开始生成
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
import Api from '@/apis/api';
// 延迟导入 AssetsBuilder，避免组件加载时出错
let AssetsBuilder = null;
const loadAssetsBuilder = async () => {
  if (!AssetsBuilder) {
    try {
      const module = await import('@/utils/AssetsBuilder.js');
      AssetsBuilder = module.default || module;
    } catch (error) {
      throw error;
    }
  }
  return AssetsBuilder;
};

export default {
  name: 'CustomThemeGenerateModal',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    device: {
      type: Object,
      default: null
    },
    agentId: {
      type: [String, Number],
      default: ''
    },
    config: {
      type: Object,
      default: () => ({
        chip: {
          model: '',
          display: { width: 320, height: 240, color: 'RGB565' },
          preset: ''
        },
        theme: {
          wakeword: '',
          font: { type: 'preset', preset: '', custom: { file: null, name: '', size: 16, bpp: 4 } },
          emoji: { type: 'preset', preset: '', custom: { images: {}, size: { width: 32, height: 32 } } },
          skin: {
            light: { backgroundType: 'color', backgroundColor: '#ffffff', textColor: '#000000', backgroundImage: '' },
            dark: { backgroundType: 'color', backgroundColor: '#121212', textColor: '#ffffff', backgroundImage: '' }
          }
        }
      })
    }
  },
  data() {
    return {
      isGenerating: false,
      isCompleted: false,
      fileList: [],
      progress: 0,
      currentStep: '',
      generationStartTime: null,
      generatedBlob: null,
      generatedFileSize: '',
      generationTime: '',
      deviceOnline: false,
      progressSteps: [
        { id: 1, name: '初始化生成器', status: 'pending' },
        { id: 2, name: '处理字体文件', status: 'pending' },
        { id: 3, name: '打包唤醒词模型', status: 'pending' },
        { id: 4, name: '处理表情图片', status: 'pending' },
        { id: 5, name: '处理背景图片', status: 'pending' },
        { id: 6, name: '生成索引文件', status: 'pending' },
        { id: 7, name: '构建SPIFFS映射', status: 'pending' },
        { id: 8, name: '完成打包', status: 'pending' }
      ]
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
    },
    hasSelectedFiles() {
      return this.fileList.length > 0;
    }
  },
  mounted() {
    if (this.visible) {
      this.resetState();
      this.initializeFileList();
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.resetState();
        this.initializeFileList();
      }
    },
    config: {
      deep: true,
      handler() {
        if (this.visible) {
          this.initializeFileList();
        }
      }
    }
  },
  methods: {
    resetState() {
      this.isGenerating = false;
      this.isCompleted = false;
      this.fileList = [];
      this.progress = 0;
      this.currentStep = '';
      this.generationStartTime = null;
      this.progressSteps = [
        { id: 1, name: '初始化生成器', status: 'pending' },
        { id: 2, name: '处理字体文件', status: 'pending' },
        { id: 3, name: '打包唤醒词模型', status: 'pending' },
        { id: 4, name: '处理表情图片', status: 'pending' },
        { id: 5, name: '处理背景图片', status: 'pending' },
        { id: 6, name: '生成索引文件', status: 'pending' },
        { id: 7, name: '构建SPIFFS映射', status: 'pending' },
        { id: 8, name: '完成打包', status: 'pending' }
      ];
    },
    getChipModel() {
      if (!this.config || !this.config.chip || !this.config.chip.model) {
        return '未配置';
      }
      return this.config.chip.model.toUpperCase();
    },
    getResolution() {
      if (!this.config || !this.config.chip || !this.config.chip.display) {
        return '未配置';
      }
      return `${this.config.chip.display.width}×${this.config.chip.display.height}`;
    },
    getWakewordName() {
      if (!this.config || !this.config.theme || !this.config.theme.wakeword) {
        return '未配置';
      }
      const names = {
        'wn9s_alexa': 'Alexa',
        'wn9s_hiesp': 'Hi,ESP',
        'wn9s_hijason': 'Hi,Jason',
        'wn9s_hilexin': 'Hi,乐鑫',
        'wn9s_nihaoxiaozhi': '你好小智',
        'wn7_xiaoaitongxue': '小爱同学'
      };
      return names[this.config.theme.wakeword] || this.config.theme.wakeword || '未配置';
    },
    getFontName() {
      if (!this.config || !this.config.theme || !this.config.theme.font) {
        return '未配置';
      }
      if (this.config.theme.font.type === 'preset') {
        const preset = this.config.theme.font.preset || '';
        const presetNames = {
          'font_puhui_deepseek_14_1': '普惠体 14px',
          'font_puhui_deepseek_16_4': '普惠体 16px',
          'font_puhui_deepseek_20_4': '普惠体 20px',
          'font_puhui_deepseek_30_4': '普惠体 30px'
        };
        return presetNames[preset] || preset || '未配置';
      } else {
        const custom = this.config.theme.font.custom;
        if (custom && custom.size) {
          return `自定义字体 ${custom.size}px`;
        }
        return '自定义字体';
      }
    },
    getEmojiName() {
      if (!this.config || !this.config.theme || !this.config.theme.emoji) {
        return '未配置';
      }
      if (this.config.theme.emoji.type === 'preset' && this.config.theme.emoji.preset) {
        return this.config.theme.emoji.preset === 'twemoji64' ? 'Twemoji 64×64' : 'Twemoji 32×32';
      } else if (this.config.theme.emoji.type === 'custom') {
        const count = Object.keys(this.config.theme.emoji.custom.images || {}).length;
        return count > 0 ? `自定义表情 ${count}张` : '未配置';
      }
      return '未配置';
    },
    initializeFileList() {
      this.fileList = [];

      // 添加索引文件
      this.fileList.push({
        id: 'index',
        name: 'index.json',
        iconClass: 'el-icon-document',
        iconColor: '#409eff',
        size: '1KB'
      });

      if (!this.config || !this.config.theme) {
        return;
      }

      // 添加唤醒词模型
      if (this.config.theme.wakeword) {
        this.fileList.push({
          id: 'srmodels',
          name: 'srmodels.bin',
          iconClass: 'el-icon-microphone',
          iconColor: '#67c23a',
          size: '~2.1MB'
        });
      }

      // 添加字体文件
      if (this.config.theme.font && this.config.theme.font.type === 'preset') {
        const fontSizes = {
          'font_puhui_deepseek_14_1': '180KB',
          'font_puhui_deepseek_16_4': '720KB',
          'font_puhui_deepseek_20_4': '1.1MB',
          'font_puhui_deepseek_30_4': '2.5MB'
        };
        const preset = this.config.theme.font.preset || '';
        this.fileList.push({
          id: 'font',
          name: `${preset}.bin`,
          iconClass: 'el-icon-edit-outline',
          iconColor: '#e6a23c',
          size: fontSizes[preset] || '500KB'
        });
      } else if (this.config.theme.font && this.config.theme.font.custom && this.config.theme.font.custom.file) {
        const custom = this.config.theme.font.custom;
        const estimatedSize = Math.max(100, custom.size * custom.size * custom.bpp * 0.1);
        this.fileList.push({
          id: 'font',
          name: `font_custom_${custom.size}_${custom.bpp}.bin`,
          iconClass: 'el-icon-edit-outline',
          iconColor: '#e6a23c',
          size: estimatedSize > 1024 ? `${(estimatedSize/1024).toFixed(1)}MB` : `${Math.round(estimatedSize)}KB`,
          estimated: true
        });
      }

      // 添加表情文件
      if (this.config.theme.emoji && this.config.theme.emoji.type === 'preset' && this.config.theme.emoji.preset) {
        const emotionList = ['neutral', 'happy', 'laughing', 'funny', 'sad', 'angry', 'crying', 'loving', 'embarrassed', 'surprised', 'shocked', 'thinking', 'winking', 'cool', 'relaxed', 'delicious', 'kissy', 'confident', 'sleepy', 'silly', 'confused'];
        const size = this.config.theme.emoji.preset === 'twemoji64' ? '3KB' : '1KB';
        emotionList.forEach(emotion => {
          this.fileList.push({
            id: `emoji_${emotion}`,
            name: `${emotion}.png`,
            iconClass: 'el-icon-picture',
            iconColor: '#f56c6c',
            size: size
          });
        });
      } else if (this.config.theme.emoji && this.config.theme.emoji.type === 'custom' && this.config.theme.emoji.custom.images) {
        Object.entries(this.config.theme.emoji.custom.images).forEach(([emotion, file]) => {
          if (file) {
            const fileSizeKB = Math.round(file.size / 1024);
            this.fileList.push({
              id: `emoji_${emotion}`,
              name: file.name || `${emotion}.png`,
              iconClass: 'el-icon-picture',
              iconColor: '#f56c6c',
              size: fileSizeKB > 1024 ? `${(fileSizeKB/1024).toFixed(1)}MB` : `${fileSizeKB}KB`
            });
          }
        });
      }

      // 添加背景文件
      if (this.config.theme.skin && this.config.theme.skin.light && 
          this.config.theme.skin.light.backgroundType === 'image' && 
          this.config.theme.skin.light.backgroundImage) {
        const { width, height } = this.config.chip.display || { width: 320, height: 240 };
        const estimatedSize = Math.round(width * height * 2 / 1024);
        this.fileList.push({
          id: 'bg_light',
          name: 'background_light.raw',
          iconClass: 'el-icon-picture',
          iconColor: '#909399',
          size: estimatedSize > 1024 ? `${(estimatedSize/1024).toFixed(1)}MB` : `${estimatedSize}KB`,
          estimated: true
        });
      }

      if (this.config.theme.skin && this.config.theme.skin.dark && 
          this.config.theme.skin.dark.backgroundType === 'image' && 
          this.config.theme.skin.dark.backgroundImage) {
        const { width, height } = this.config.chip.display || { width: 320, height: 240 };
        const estimatedSize = Math.round(width * height * 2 / 1024);
        this.fileList.push({
          id: 'bg_dark',
          name: 'background_dark.raw',
          iconClass: 'el-icon-picture',
          iconColor: '#909399',
          size: estimatedSize > 1024 ? `${(estimatedSize/1024).toFixed(1)}MB` : `${estimatedSize}KB`,
          estimated: true
        });
      }
    },
    async startGeneration() {
      this.isGenerating = true;
      this.progress = 0;
      this.generationStartTime = Date.now();
      
      try {
        // 动态加载 AssetsBuilder
        const AssetsBuilderClass = await loadAssetsBuilder();
        // 创建AssetsBuilder实例
        const builder = new AssetsBuilderClass();
        builder.setConfig(this.config);
        
        // 生成assets.bin
        const blob = await builder.generateAssetsBin((progressPercent, message) => {
          this.progress = parseInt(progressPercent);
          this.currentStep = message;
          
          // 更新进度步骤状态
          const stepIndex = Math.floor(progressPercent / (100 / this.progressSteps.length));
          this.progressSteps.forEach((step, index) => {
            if (index < stepIndex) {
              step.status = 'completed';
            } else if (index === stepIndex) {
              step.status = 'processing';
            } else {
              step.status = 'pending';
            }
          });
        });
        
        // 完成生成
        this.isGenerating = false;
        this.isCompleted = true;
        
        // 标记所有步骤为完成
        this.progressSteps.forEach(step => {
          step.status = 'completed';
        });
        
        // 存储生成的文件用于下载
        this.generatedBlob = blob;
        this.generatedFileSize = this.formatFileSize(blob.size);
        const endTime = Date.now();
        const duration = endTime - this.generationStartTime;
        this.generationTime = this.formatDuration(duration);
        
      } catch (error) {
        console.error('生成 assets.bin 失败:', error);
        this.$message.error('生成失败: ' + (error.message || '未知错误'));
        
        // 重置状态
        this.isGenerating = false;
        this.isCompleted = false;
      }
    },
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    },
    formatDuration(milliseconds) {
      if (milliseconds < 1000) {
        return `${milliseconds}ms`;
      } else if (milliseconds < 60000) {
        return `${(milliseconds / 1000).toFixed(1)}s`;
      } else {
        const minutes = Math.floor(milliseconds / 60000);
        const seconds = Math.floor((milliseconds % 60000) / 1000);
        return `${minutes}m ${seconds}s`;
      }
    },
    handleClose() {
      this.dialogVisible = false;
    },
    downloadFile() {
      if (!this.generatedBlob) {
        this.$message.error('没有可下载的文件');
        return;
      }
      const url = URL.createObjectURL(this.generatedBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'assets.bin';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    async startOnlineFlash() {
      if (!this.generatedBlob) {
        this.$message.error('请先生成文件');
        return;
      }
      const online = await this.checkDeviceOnline();
      if (!online) return;

      try {
        // 先上传 assets.bin 到 8003
        const downloadUrl = await this.uploadAssetsBin();
        await this.sendSetDownloadUrl(downloadUrl);
        await this.sendRebootCommand();
        this.$message.success('下载URL已下发，重启命令已发送');
      } catch (e) {
        console.error('[Flash] 烧录流程失败', e);
        this.$message.error('烧录流程失败: ' + (e.message || e));
      }
    },
    async uploadAssetsBin() {
      if (!this.generatedBlob) throw new Error('没有生成好的 assets.bin');
      const url = `${window.location.protocol}//${window.location.hostname}:8003/xiaozhi/trans/upload`;
      const form = new FormData();
      form.append('file', this.generatedBlob, 'assets.bin');
      const res = await fetch(url, { method: 'POST', body: form });
      if (!res.ok) {
        throw new Error(`上传失败 HTTP ${res.status}`);
      }
      return `${window.location.protocol}//${window.location.hostname}:8003/xiaozhi/trans/assets.bin`;
    },
    buildClientId(device) {
      const mac = (device && device.macAddress) ? device.macAddress : '';
      const model = (device && device.model) ? device.model : 'esp32';
      const macUnderscore = mac.replace(/:/g, '_');
      return `${model}@@@${macUnderscore}@@@${macUnderscore}`;
    },
    getGatewayBaseCandidates() {
      const params = new URLSearchParams(window.location.search || '');
      const override = params.get('mqttGatewayUrl');
      const bases = [];
      if (override) bases.push(override.replace(/\/$/, ''));
      bases.push(`${window.location.protocol}//${window.location.hostname}:8007`); // 与脚本一致
      bases.push(window.location.origin); // 若有同源反代可避开 CORS
      return bases;
    },
    computeToken(dateStr, key) {
      return crypto.subtle && window.TextEncoder
        ? null // will handle async in list builder
        : btoa(dateStr + key).slice(0, 64);
    },
    async buildSha256(content) {
      const buf = await window.crypto.subtle.digest('SHA-256', new TextEncoder().encode(content));
      return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
    },
    async getGatewayTokensList() {
      const params = new URLSearchParams(window.location.search || '');

      // 多渠道覆盖 token，优先已算好的值，避免浏览器计算差异
      const tokenFromUrl = params.get('mqttToken') || params.get('token');
      const list = [];
      if (tokenFromUrl) list.push(tokenFromUrl);

      const tokenFromLS = typeof localStorage !== 'undefined' ? localStorage.getItem('mqttToken') : '';
      if (tokenFromLS) list.push(tokenFromLS);

      if (window.__MQTT_TOKEN__) list.push(window.__MQTT_TOKEN__);

      const key =
        params.get('mqttKey') ||
        window.__MQTT_SIGNATURE_KEY__ ||
        process.env.VUE_APP_MQTT_SIGNATURE_KEY ||
        'Jiangli.2014';

      const dateOverride =
        params.get('mqttDate') ||
        params.get('date') ||
        window.__MQTT_DATE__;
      const dates = [];
      const makeDateStr = (d) => {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
      };
      if (dateOverride) {
        dates.push(dateOverride);
      } else {
        const today = new Date();
        const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
        const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
        dates.push(makeDateStr(today), makeDateStr(yesterday), makeDateStr(tomorrow));
      }

      for (const ds of dates) {
        if (window.crypto && window.crypto.subtle && window.TextEncoder) {
          list.push(await this.buildSha256(ds + key));
        } else {
          list.push(btoa(ds + key).slice(0, 64));
        }
      }

      // 去重
      return Array.from(new Set(list)).filter(Boolean);
    },
    async checkDeviceOnline() {
      const dev = this.device || (this.$parent && this.$parent.selectedDeviceForTheme);
      if (!dev) {
        console.warn('[Flash] 无设备信息，无法查询在线状态');
        this.$message.error('缺少设备信息，无法查询在线状态');
        return false;
      }
      const agentId = this.agentId || (this.$route && this.$route.query && this.$route.query.agentId) || '';
      if (!agentId) {
        this.$message.error('缺少 agentId，无法查询在线状态');
        console.warn('[Flash] 缺少 agentId');
        return false;
      }
      const clientId = this.buildClientId(dev);
      try {
        const data = await new Promise((resolve, reject) => {
          Api.device.getDeviceStatus(agentId, ({ data }) => resolve(data), reject);
        });
        if (data.code === 0) {
          const statusData = JSON.parse(data.data || '{}');
          const status = statusData[clientId];
          let isOnline = false;
          if (status) {
            if (status.isAlive === true) isOnline = true;
            else if (status.isAlive === false) isOnline = false;
            else if (status.isAlive === null && status.exists === true) isOnline = true;
          }
          this.deviceOnline = isOnline;
          dev.deviceStatus = isOnline ? 'online' : 'offline';
          console.log('[Flash] 设备在线查询（同设备管理接口）', { agentId, clientId, status, online: isOnline });
          if (isOnline) {
            this.$message.success('设备在线，可以开始烧录');
          } else {
            this.$message.error('设备不在线，无法烧录');
          }
          return isOnline;
        }
        this.$message.error(data.msg || '查询设备在线状态失败');
        console.error('[Flash] 查询设备在线失败', data);
      } catch (e) {
        console.error('[Flash] 查询设备在线失败', e);
        this.$message.error('查询设备在线状态失败');
      }
      return false;
    },
    buildDownloadUrl() {
      const params = new URLSearchParams(window.location.search || '');
      return params.get('downloadUrl') ||
        `${window.location.protocol}//${window.location.hostname}:8003/xiaozhi/trans/assets.bin`;
    },
    async sendSetDownloadUrl(downloadUrl) {
      const dev = this.device || (this.$parent && this.$parent.selectedDeviceForTheme);
      const clientId = this.buildClientId(dev);
      const topic = `devices/p2p/${clientId.split('@@@')[1]}`;
      const tokens = await this.getGatewayTokensList();
      const params = new URLSearchParams(window.location.search || '');
      const override = params.get('mqttGatewayUrl') || params.get('gateway');
      const useGatewayOnly = params.get('useGatewayOnly') !== 'false'; // 默认只尝试网关
      const bases = [];
      if (override) bases.push(override.replace(/\/$/, ''));
      bases.push(`${window.location.protocol}//${window.location.hostname}:8007`); // 脚本默认
      if (!useGatewayOnly) bases.push(window.location.origin); // 显式允许再试同源
      const payload = {
        type: 'mcp',
        payload: {
          jsonrpc: '2.0',
          method: 'tools/call',
          id: Date.now(),
          params: {
            name: 'self.assets.set_download_url',
            arguments: { url: downloadUrl }
          }
        }
      };
      let lastErr = '';
      for (const base of bases) {
        try {
          // 先尝试 Bearer，再尝试裸 Authorization，避免自定义 token 头触发 CORS 拒绝
          let ok = false;
          for (const token of tokens) {
            const headerVariants = [
              { Authorization: `Bearer ${token}` },
              { Authorization: token }
            ];
            for (const headers of headerVariants) {
              const res = await fetch(`${base}/api/messages/publish`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  ...headers
                },
                body: JSON.stringify({
                  topic,
                  clientId,
                  message: JSON.stringify(payload),
                  qos: 1
                })
              });
              if (res.ok || res.type === 'opaque') {
                ok = true;
                break;
              }
              lastErr = `HTTP ${res.status}`;
            }
            if (ok) break;
          }
          if (ok) {
            console.log('[Flash] set_download_url 下发成功', { base, topic, clientId, downloadUrl });
            return;
          }
        } catch (e) {
          lastErr = e.message || String(e);
        }
      }
      throw new Error('下发下载URL失败: ' + lastErr);
    },
    async sendRebootCommand() {
      const dev = this.device || (this.$parent && this.$parent.selectedDeviceForTheme);
      const clientId = this.buildClientId(dev);
      const topic = `devices/p2p/${clientId.split('@@@')[1]}`;
      const tokens = await this.getGatewayTokensList();
      const params = new URLSearchParams(window.location.search || '');
      const override = params.get('mqttGatewayUrl') || params.get('gateway');
      const useGatewayOnly = params.get('useGatewayOnly') !== 'false';
      const bases = [];
      if (override) bases.push(override.replace(/\/$/, ''));
      bases.push(`${window.location.protocol}//${window.location.hostname}:8007`);
      if (!useGatewayOnly) bases.push(window.location.origin);
      const payload = {
        type: 'mcp',
        payload: {
          jsonrpc: '2.0',
          method: 'tools/call',
          id: Date.now(),
          params: {
            name: 'self.reboot',
            arguments: {}
          }
        }
      };
      let lastErr = '';
      for (const base of bases) {
        try {
          let ok = false;
          for (const token of tokens) {
            const headerVariants = [
              { Authorization: `Bearer ${token}` },
              { Authorization: token }
            ];
            for (const headers of headerVariants) {
              const res = await fetch(`${base}/api/messages/publish`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  ...headers
                },
                body: JSON.stringify({
                  topic,
                  clientId,
                  message: JSON.stringify(payload),
                  qos: 1
                })
              });
              if (res.ok || res.type === 'opaque') {
                ok = true;
                break;
              }
              lastErr = `HTTP ${res.status}`;
            }
            if (ok) break;
          }
          if (ok) {
            console.log('[Flash] reboot 下发成功', { base, topic, clientId });
            return;
          }
        } catch (e) {
          lastErr = e.message || String(e);
        }
      }
      throw new Error('下发重启失败: ' + lastErr);
    }
  }
};
</script>

<style scoped>
.config-confirm-page {
  padding: 0;
}

.config-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
  margin-bottom: 12px;
}

.config-info-box {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.config-label {
  color: #6b7280;
}

.config-value {
  font-weight: 500;
  color: #111827;
}

.file-list-section {
  margin-top: 24px;
}

.file-list-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 256px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
}

.file-info-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-info-left i {
  font-size: 16px;
}

.file-name {
  font-size: 13px;
  font-weight: 500;
  color: #111827;
}

.file-size {
  font-size: 13px;
  color: #374151;
}

.estimated {
  font-size: 11px;
  color: #9ca3af;
  margin-left: 4px;
}

.dialog-footer {
  text-align: right;
}

/* 生成进度页面样式 */
.generating-page {
  text-align: center;
  padding: 20px 0;
}

.loading-spinner-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.loading-spinner {
  width: 64px;
  height: 64px;
  border: 3px solid #e5e7eb;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.progress-section {
  margin-bottom: 24px;
}

.progress-title {
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 16px;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-bar-fill {
  height: 100%;
  background: #409eff;
  border-radius: 4px;
  transition: width 0.5s ease-out;
}

.progress-info {
  font-size: 13px;
  color: #6b7280;
}

.current-step {
  margin-bottom: 4px;
}

.progress-percent {
  margin-top: 4px;
}

.progress-steps-list {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 24px;
}

.completed-page {
  text-align: center;
  padding: 24px 0;
}

.success-icon {
  font-size: 64px;
  color: #67c23a;
  margin-bottom: 16px;
}

.success-text {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #2c3e50;
}

.result-box {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 12px 16px;
  display: inline-block;
  text-align: left;
  color: #3a3a3a;
  margin-bottom: 16px;
}

.result-item + .result-item {
  margin-top: 4px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.action-buttons.column {
  flex-direction: column;
  align-items: stretch;
}

.action-btn.full {
  width: 100%;
  height: 40px;
  font-size: 14px;
  justify-content: center;
}

.action-btn.secondary {
  background: #ecf5ff;
  border-color: #c6e2ff;
  color: #409eff;
}

.action-btn.secondary:hover {
  background: #d9ecff;
}

.progress-step-item {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.step-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin-right: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-check-icon {
  color: #67c23a;
  font-size: 14px;
}

.step-processing-dot {
  width: 20px;
  height: 20px;
  background: #409eff;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

.step-pending-dot {
  width: 20px;
  height: 20px;
  background: #d1d5db;
  border-radius: 50%;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.step-name {
  flex: 1;
}

.step-completed {
  color: #67c23a;
}

.step-processing {
  color: #409eff;
}

.step-pending {
  color: #9ca3af;
}
</style>

<style>
.generate-modal-dialog .el-dialog__body {
  padding: 24px;
  max-height: calc(90vh - 140px);
  overflow-y: auto;
}
</style>
