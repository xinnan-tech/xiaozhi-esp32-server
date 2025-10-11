<template>
  <el-dialog :title="title" :visible.sync="dialogVisible" :close-on-click-modal="false" @close="handleClose"
    @open="handleOpen" width="500px">
    <el-form ref="form" :model="form" :rules="rules" label-width="120px">
      <el-form-item :label="$t('voiceClone.platformName')" prop="modelId">
        <el-select v-model="form.modelId" :placeholder="$t('voiceClone.platformNamePlaceholder')" filterable
          style="width: 100%" @change="handlePlatformChange">
          <el-option v-for="model in platformList" :key="model.id" :label="model.modelName" :value="model.id">
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item :label="$t('voiceClone.voiceId')" prop="voiceIds">
        <el-select v-model="form.voiceIds" :placeholder="$t('voiceClone.voiceIdPlaceholder')" filterable multiple
          allow-create default-first-option style="width: 100%">
          <el-option v-for="voiceId in voiceIdList" :key="voiceId" :label="voiceId" :value="voiceId">
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item :label="$t('voiceClone.userId')" prop="userId">
        <el-select v-model="form.userId" :placeholder="$t('voiceClone.userIdPlaceholder')" filterable remote
          :remote-method="remoteSearchUser" :loading="userLoading" style="width: 100%">
          <el-option v-for="user in userList" :key="user.userid" :label="user.mobile" :value="user.userid">
          </el-option>
        </el-select>
      </el-form-item>
    </el-form>

    <div slot="footer" class="dialog-footer">
      <el-button @click="handleCancel">{{ $t('voiceClone.operationCancelled') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('voiceClone.addNew') }}</el-button>
    </div>
  </el-dialog>
</template>

<script>
import Api from '@/apis/api';

export default {
  name: 'VoiceCloneDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: ''
    },
    form: {
      type: Object,
      default: () => ({})
    }
  },

  data() {
    return {
      dialogVisible: this.visible,
      platformList: [],
      voiceIdList: [],
      userList: [],
      userLoading: false,
      rules: {
        modelId: [
          { required: true, message: this.$t('voiceClone.platformNameRequired'), trigger: 'change' }
        ],
        voiceIds: [
          { required: true, message: this.$t('voiceClone.voiceIdRequired'), trigger: 'change' }
        ],
        userId: [
          { required: true, message: this.$t('voiceClone.userIdRequired'), trigger: 'change' }
        ]
      }
    }
  },

  watch: {
    visible(val) {
      this.dialogVisible = val;
    },
    dialogVisible(val) {
      this.$emit('update:visible', val);
    }
  },

  methods: {
    handleClose() {
      this.dialogVisible = false;
      this.$emit('cancel');
    },

    handleCancel() {
      this.$refs.form.clearValidate();
      this.$emit('cancel');
    },

    handleSubmit() {
      this.$refs.form.validate(valid => {
        if (valid) {
          this.$emit('submit', this.form);
        }
      });
    },

    handleOpen() {
      // 对话框打开时加载平台列表
      this.fetchPlatformList();
      // 重置音色ID列表
      this.voiceIdList = [];
    },

    handlePlatformChange(modelId) {
      // 清空音色ID选择
      this.form.voiceIds = [];
    },

    // 获取TTS平台列表
    fetchPlatformList() {
      Api.voiceResource.getTtsPlatformList((res) => {
        if (res.data.code === 0) {
          this.platformList = res.data.data;
        }
      });
    },

    // 远程搜索用户
    remoteSearchUser(query) {
      if (query !== '') {
        this.userLoading = true;
        const params = {
          page: 1,
          limit: 20,
          mobile: query
        };
        Api.admin.getUserList(params, (res) => {
          this.userLoading = false;
          if (res.data.code === 0) {
            this.userList = res.data.data.list;
          }
        });
      } else {
        this.userList = [];
      }
    }
  }
}
</script>

<style lang="scss" scoped>
::v-deep .el-dialog {
  border-radius: 20px;
}
</style>
