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
    <div style="height: 1px;background: #e8f0ff;" />
    <div style="margin: 22px 15px;">
      <div style="font-weight: 400;text-align: left;color: #3d4566;">
        <div style="color: red;display: inline-block;">*</div> {{ $t('addAgentDialog.agentName') }}：
      </div>
      <div class="input-46" style="margin-top: 12px;">
        <el-input ref="inputRef" :placeholder="$t('addAgentDialog.placeholder')" v-model="wisdomBodyName" @keyup.enter.native="confirm" />
      </div>
    </div>
    <div style="display: flex;margin: 15px 15px;gap: 7px;">
      <div class="dialog-btn" @click="confirm">
        {{ $t('addAgentDialog.confirm') }}
      </div>
      <div class="dialog-btn" style="background: #e6ebff;border: 1px solid #adbdff;color: #5778ff;" @click="cancel">
        {{ $t('addAgentDialog.cancel') }}
      </div>
    </div>
  </el-dialog>
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