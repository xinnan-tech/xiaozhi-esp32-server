<template>
  <CustomDialog
    :title="$t('addAgentDialog.title')"
    :visible.sync="visible"
    width="420px"
    @confirm="confirm"
    @cancel="cancel"
    @close="handleClose"
    :confirmText="$t('addAgentDialog.confirm')"
    :cancelText="$t('addAgentDialog.cancel')"
    @open="handleOpen"
  >
    <div class="add-agent-body">
      <div class="add-agent-label">
        <span class="required">*</span>
        {{ $t('addAgentDialog.agentName') }}
      </div>
      <el-input
        maxLength="64"
        ref="inputRef"
        :placeholder="$t('addAgentDialog.placeholder')"
        v-model="wisdomBodyName"
        class="add-agent-input"
        @keyup.enter.native="confirm"
      />
    </div>
  </CustomDialog>
</template>

<script>
import Api from '@/apis/api';
import CustomDialog from './CustomDialog.vue';

export default {
  name: 'AddWisdomBodyDialog',
  components: { CustomDialog },
  props: {
    visible: { type: Boolean, required: true }
  },
  data() {
    return {
      wisdomBodyName: ""
    }
  },
  methods: {
    handleOpen() {
      this.$nextTick(() => {
        if (this.$refs.inputRef && this.$refs.inputRef.focus) {
          this.$refs.inputRef.focus();
        }
      });
    },
    confirm() {
      if (!this.wisdomBodyName.trim()) {
        this.$message.error(this.$t('addAgentDialog.nameRequired'));
        return;
      }
      Api.agent.addAgent(this.wisdomBodyName, (res) => {
        this.$message.success({
          message: this.$t('addAgentDialog.addSuccess'),
          showClose: true
        });
        this.$emit('confirm', res);
        this.$emit('update:visible', false);
        this.wisdomBodyName = "";
      });
    },
    cancel() {
      this.wisdomBodyName = "";
      this.$emit('update:visible', false);
    },
    handleClose() {
      this.cancel();
    }
  }
}
</script>

<style scoped>
.add-agent-body {
  padding: 6px 4px 4px;
}

.add-agent-label {
  font-size: 14px;
  color: #475569;
  text-align: left;
  margin-bottom: 12px;
}

.add-agent-label .required {
  color: #f56c6c;
  margin-right: 2px;
}

.add-agent-input ::v-deep(.el-input__inner) {
  height: 40px;
  border-radius: 8px;
  border-color: #e2e8f0;
  font-size: 14px;
}
</style>