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
          label="自定义 (mn5q8_cn)"
          value="custom"
        />
        <el-option
          v-for="wakeword in availableWakewords"
          :key="wakeword.id"
          :label="`${wakeword.name} (${wakeword.model})`"
          :value="wakeword.id"
        />
      </el-select>
    </div>

    <!-- 自定义唤醒词输入框 -->
    <div v-if="localValue === 'custom'" class="custom-wakeword-section">
      <div class="custom-input-row">
        <div class="custom-input-item">
          <label class="custom-input-label">Custom Wake Word</label>
          <el-input
            v-model="customWakeword.pinyin"
            placeholder="请输入拼音，用空格分隔，如：ni hao xiao zhi"
            @input="updateCustomWakeword"
          />
        </div>
        <div class="custom-input-item">
          <label class="custom-input-label">Custom Wake Word Display</label>
          <el-input
            v-model="customWakeword.chinese"
            placeholder="请输入拼音，不用空格分隔，如：nihaoxiaozhi"
            @input="updateCustomWakeword"
          />
        </div>
      </div>
    </div>

    <div v-if="localValue && localValue !== 'custom'" class="selected-info">
      <div class="selected-content">
        <div class="selected-icon"><i class="el-icon-success"></i></div>
        <div class="selected-details">
          <div class="selected-title">{{ $t('device.customThemeSelectedWakeword') }}: {{ getSelectedWakewordName() }}</div>
          <div class="selected-meta">{{ $t('device.customThemeWakewordModel') }}: {{ getSelectedWakewordModel() }}</div>
          <div class="selected-meta">{{ $t('device.customThemeWakewordFileName') }}: {{ localValue }}.bin</div>
        </div>
      </div>
    </div>

    <div v-if="localValue === 'custom' && customWakeword.chinese && customWakeword.pinyin" class="selected-info">
      <div class="selected-content">
        <div class="selected-icon"><i class="el-icon-success"></i></div>
        <div class="selected-details">
          <div class="selected-title">自定义唤醒词: {{ customWakeword.chinese }}</div>
          <div class="selected-meta">拼音: {{ customWakeword.pinyin }}</div>
          <div class="selected-meta">模型: Multinet5Q8 (mn5q8_cn)</div>
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
      ],
      customWakeword: {
        chinese: '',
        pinyin: ''
      }
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
      const newValue = id || '';
      // 如果切换到非自定义选项，清空自定义唤醒词
      if (id !== 'custom') {
        this.customWakeword = { chinese: '', pinyin: '' };
      }
      // 更新 localValue，这会触发 input 事件
      this.$emit('input', newValue);
      // 通知父组件更新自定义唤醒词配置
      this.$nextTick(() => {
        this.$emit('custom-wakeword-change', {
          wakeword: newValue,
          customWakeword: newValue === 'custom' ? this.customWakeword : null
        });
      });
    },
    updateCustomWakeword() {
      // 通知父组件更新自定义唤醒词配置
      if (this.localValue === 'custom') {
        this.$emit('custom-wakeword-change', {
          wakeword: this.localValue,
          customWakeword: this.customWakeword
        });
      }
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
.custom-wakeword-section {
  margin: 14px 0;
}
.custom-input-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.custom-input-item {
  flex: 1;
}
.custom-input-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #606266;
}
</style>

