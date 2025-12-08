<template>
  <el-dialog
    :visible.sync="dialogVisible"
    width="520px"
    :title="$t('device.customThemeGenerateModalTitle')"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="progress-body">
      <div class="progress-row">
        <el-progress :percentage="progress" :status="validStatus"></el-progress>
      </div>
      <div class="progress-steps">
        <div
          v-for="step in progressSteps"
          :key="step.id"
          class="step"
          :class="step.status"
        >
          <span class="dot"></span>
          <span>{{ step.name }}</span>
        </div>
      </div>
      <div class="file-info" v-if="isCompleted">
        <div>{{ $t('device.customThemeFileName') }}: assets.bin</div>
        <div>{{ $t('device.customThemeFileSize') }}: {{ generatedFileSize }}</div>
        <div>{{ $t('device.customThemeGenerateTime') }}: {{ generationTime }}</div>
      </div>
    </div>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleClose" v-if="!isGenerating">{{ $t('device.customThemeClose') }}</el-button>
      <el-button type="primary" :disabled="isGenerating" @click="handleDownload" v-if="isCompleted">
        {{ $t('device.customThemeDownload') }}
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'CustomThemeGenerateModal',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    config: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      isGenerating: false,
      isCompleted: false,
      progress: 0,
      progressStatus: null,
      generatedFileSize: '0 KB',
      generationTime: '',
      progressSteps: []
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
    validStatus() {
      return this.progressStatus && ['success', 'exception', 'warning', 'text'].includes(this.progressStatus)
        ? this.progressStatus
        : undefined;
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.resetState();
        this.$nextTick(this.startGenerate);
      }
    }
  },
  methods: {
    resetState() {
      this.isGenerating = false;
      this.isCompleted = false;
      this.progress = 0;
      this.progressStatus = null;
      this.progressSteps = [
        { id: 1, name: this.$t('device.customThemeStep1'), status: 'pending' },
        { id: 2, name: this.$t('device.customThemeStep2'), status: 'pending' },
        { id: 3, name: this.$t('device.customThemeStep3'), status: 'pending' }
      ];
    },
    startGenerate() {
      this.isGenerating = true;
      this.simulate();
    },
    simulate() {
      let idx = 0;
      const run = () => {
        if (idx >= this.progressSteps.length) {
          this.isGenerating = false;
          this.isCompleted = true;
          this.progress = 100;
          this.progressStatus = 'success';
          this.generatedFileSize = '2.5 MB';
          this.generationTime = new Date().toLocaleString('zh-CN');
          return;
        }
        this.$set(this.progressSteps, idx, { ...this.progressSteps[idx], status: 'processing' });
        this.progress = Math.round(((idx + 1) / this.progressSteps.length) * 100);
        setTimeout(() => {
          this.$set(this.progressSteps, idx, { ...this.progressSteps[idx], status: 'completed' });
          idx += 1;
          run();
        }, 800);
      };
      run();
    },
    handleDownload() {
      this.$message.success('assets.bin');
    },
    handleClose() {
      this.dialogVisible = false;
    }
  }
};
</script>

<style scoped>
.progress-body {
  min-height: 160px;
}
.progress-row {
  margin-bottom: 12px;
}
.progress-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}
.step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}
.step .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e5e7eb;
}
.step.processing .dot {
  background: #f59e0b;
}
.step.completed .dot {
  background: #10b981;
}
.file-info {
  margin-top: 12px;
  font-size: 13px;
  color: #374151;
  line-height: 1.6;
}
.dialog-footer {
  text-align: right;
}
</style>

