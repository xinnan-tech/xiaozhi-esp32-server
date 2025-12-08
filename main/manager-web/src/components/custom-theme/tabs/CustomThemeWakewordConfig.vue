<template>
  <div class="wakeword-config-wrapper">
    <div class="config-header">
      <h3 class="config-title">{{ $t('device.customThemeWakewordTab') }}</h3>
      <p class="config-desc">
        {{ $t('device.customThemeWakewordDesc') }}
        <span class="chip-tip">
          {{ chipModel.includes('c3') || chipModel.includes('c6') ? $t('device.customThemeWakewordChipTipC3') : $t('device.customThemeWakewordChipTipS3') }}
        </span>
      </p>
    </div>

    <div class="select-section">
      <label class="select-label">{{ $t('device.customThemeSelectWakeword') }}</label>
      <el-select
        :value="localValue"
        :placeholder="$t('device.customThemeSelectWakewordPlaceholder')"
        clearable
        style="width: 100%"
        @change="selectWakeword"
      >
        <el-option
          v-for="wakeword in availableWakewords"
          :key="wakeword.id"
          :label="`${wakeword.name} (${wakeword.model})`"
          :value="wakeword.id"
        />
      </el-select>
    </div>

    <div v-if="localValue" class="selected-info">
      <div class="selected-content">
        <div class="selected-icon"><i class="el-icon-success"></i></div>
        <div class="selected-details">
          <div class="selected-title">{{ $t('device.customThemeSelectedWakeword') }}: {{ getSelectedWakewordName() }}</div>
          <div class="selected-meta">{{ $t('device.customThemeWakewordModel') }}: {{ getSelectedWakewordModel() }}</div>
          <div class="selected-meta">{{ $t('device.customThemeWakewordFileName') }}: {{ localValue }}.bin</div>
        </div>
      </div>
    </div>

    <div class="tips-card">
      <div class="tips-title">{{ $t('device.customThemeTips') }}</div>
      <ul class="tips-list">
        <li>{{ $t('device.customThemeWakewordTip1') }}</li>
        <li>{{ chipModel.includes('c3') || chipModel.includes('c6') ? $t('device.customThemeWakewordTip2C3') : $t('device.customThemeWakewordTip2S3') }}</li>
        <li>{{ $t('device.customThemeWakewordTip3') }}</li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CustomThemeWakewordConfig',
  props: {
    value: {
      type: String,
      default: ''
    },
    chipModel: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      wakewordData: [
        { id: 'wn9s_alexa', name: 'Alexa', model: 'WakeNet9s' },
        { id: 'wn9s_hiesp', name: 'Hi,ESP', model: 'WakeNet9s' },
        { id: 'wn9s_hijason', name: 'Hi,Jason', model: 'WakeNet9s' },
        { id: 'wn9s_hilexin', name: 'Hi,乐鑫', model: 'WakeNet9s' },
        { id: 'wn9s_nihaoxiaozhi', name: '你好小智', model: 'WakeNet9s' },
        { id: 'wn7_xiaoaitongxue', name: '小爱同学', model: 'WakeNet7' }
      ]
    };
  },
  computed: {
    localValue: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit('input', val);
      }
    },
    availableWakewords() {
      if (this.chipModel.includes('c3') || this.chipModel.includes('c6')) {
        return this.wakewordData.filter(w => w.model === 'WakeNet9s');
      }
      return this.wakewordData.filter(w => w.model === 'WakeNet9s' || w.model === 'WakeNet7');
    }
  },
  methods: {
    selectWakeword(id) {
      console.log('[CustomThemeWakeword] select', id);
      this.localValue = id || '';
    },
    getSelectedWakewordName() {
      const selected = this.wakewordData.find(w => w.id === this.localValue);
      return selected ? selected.name : '';
    },
    getSelectedWakewordModel() {
      const selected = this.wakewordData.find(w => w.id === this.localValue);
      return selected ? selected.model : '';
    }
  }
};
</script>

<style scoped>
.wakeword-config-wrapper {
  padding: 8px 4px;
  text-align: left;
}
.config-header {
  margin-bottom: 12px;
}
.config-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
}
.config-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
.chip-tip {
  color: #409eff;
}
.select-section {
  margin: 10px 0 14px;
}
.select-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.selected-info {
  background: #f0f9ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 12px;
}
.selected-content {
  display: flex;
  gap: 10px;
}
.selected-icon {
  color: #67c23a;
  font-size: 18px;
}
.selected-details {
  font-size: 13px;
  color: #065f46;
}
.selected-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.selected-meta {
  margin-top: 2px;
}
.tips-card {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px;
}
.tips-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.tips-list {
  padding-left: 18px;
  margin: 0;
  font-size: 13px;
  color: #1e3a8a;
  line-height: 1.6;
}
</style>

