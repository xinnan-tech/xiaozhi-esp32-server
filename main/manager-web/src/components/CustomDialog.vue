<template>
  <el-dialog
    :title="title"
    :visible.sync="dialogVisible"
    :width="width"
    :close-on-click-modal="closeOnClickModal"
    :close-on-press-escape="closeOnPressEscape"
    :show-close="showClose"
    :destroy-on-close="destroyOnClose"
    :custom-class="dialogCustomClass"
    class="custom-dialog"
    @close="handleClose"
    @open="handleOpen"
  >
    <template slot="title">
      <slot name="title">
        <div class="dialog-title">
          <img src="@/assets/knowledge-base/level.png" class="title-icon" />
          <span>{{ title }}</span>
        </div>
      </slot>
    </template>
    <slot></slot>
    <template slot="footer">
      <div v-if="footer" class="dialog-footer">
        <CustomButton @click="handleCancel">{{ cancelText }}</CustomButton>
        <CustomButton :loading="confirmLoading" type="confirm" @click="handleConfirm">
          <span class="confirm-inner">
            <img src="@/assets/knowledge-base/star.png" class="confirm-icon" />
            {{ confirmText }}
          </span>
        </CustomButton>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import CustomButton from './CustomButton.vue';
export default {
  name: "CustomDialog",
  props: {
    title: {
      type: String,
      default: ""
    },
    visible: {
      type: Boolean,
      default: false
    },
    confirmLoading: {
      type: Boolean,
      default: false
    },
    width: {
      type: String,
      default: "720px"
    },
    footer: {
      type: Boolean,
      default: true
    },
    closeOnClickModal: {
      type: Boolean,
      default: false
    },
    closeOnPressEscape: {
      type: Boolean,
      default: true
    },
    showClose: {
      type: Boolean,
      default: true
    },
    destroyOnClose: {
      type: Boolean,
      default: true
    },
    customClass: {
      type: String,
      default: ""
    },
    size: {
      type: String,
      default: "small",
      validator: (val) => ["small", "large"].includes(val),
    },
    cancelText: {
      type: String,
      default: "取消"
    },
    confirmText: {
      type: String,
      default: "确认保存"
    }
  },
  data() {
    return {
      dialogVisible: this.visible
    };
  },
  computed: {
    dialogCustomClass() {
      const classes = ["custom-dialog"];
      if (this.customClass) classes.push(this.customClass);
      if (this.size === "large") classes.push("custom-dialog--large");
      if (String(this.width).includes("%")) classes.push("custom-dialog--fluid");
      return classes.join(" ");
    },
  },
  components: {
    CustomButton
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
    }
  },
  methods: {
    handleClose() {
      this.dialogVisible = false;
      this.$emit("update:visible", false);
      this.$emit("close");
    },
    handleOpen() {
      this.$emit("open");
    },
    handleCancel() {
      this.dialogVisible = false;
      this.$emit("update:visible", false);
      this.$emit("cancel");
    },
    handleConfirm() {
      this.$emit("confirm");
    }
  }
};
</script>

<style lang="scss" scoped>
/* 大档与小档通过 .custom-dialog--large 区分 */
::v-deep .el-dialog.custom-dialog {
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin: 5vh auto !important;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 10vh);
}

::v-deep .el-dialog__body {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding: 20px;
}

/* .v-modal 样式由 global.scss 全局定义 */
::v-deep .el-dialog__header {
  padding: 16px 20px 12px;
  background: linear-gradient(135deg, #e2eeff, #edeafe);
  text-align: left;
}

::v-deep .el-dialog__title {
  font-size: 16px;
  font-weight: 500;
  color: #1a1a1a;
}

::v-deep .dialog-title {
  font-size: 18px;
  display: inline-flex;
  align-items: center;
  > span {
    line-height: 18px;
    font-weight: 500;
  }
}

::v-deep .title-icon {
  width: 24px;
  height: 24px;
  margin-right: 8px;
}

::v-deep .el-dialog__headerbtn {
  top: 12px;
  right: 16px;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;

  .el-dialog__close {
    font-size: 18px;
    color: #666;
    position: static;
    transform: none;
  }

  &:hover {
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);

    .el-dialog__close {
      color: #333;
    }
  }
}

::v-deep .el-dialog__footer {
  padding: 12px 20px 16px;
}

::v-deep .dialog-footer {
  display: flex;
  justify-content: flex-end;

  .el-button {
    padding: 10px 20px;
    display: flex;
    align-items: center;
  }

  .el-button--primary {
    background: linear-gradient(to right, #4a7cfd, #8154fc);
    border: none;

    &:hover,
    &:focus {
      background: linear-gradient(to right, #4a7cfd, #8154fc);
      opacity: 0.85;
    }
  }

  .confirm-inner {
    display: inline-flex;
    align-items: center;
  }

  .confirm-icon {
    width: 16px;
    height: 16px;
    margin-right: 4px;
  }
}

/* 大档：上下各留 10px 让边框和圆角可见 */
::v-deep .el-dialog.custom-dialog.custom-dialog--large {
  margin: 10px auto !important;
  height: calc(100vh - 20px);
  max-height: calc(100vh - 20px);
  border-radius: 10px;
}

::v-deep .el-dialog.custom-dialog.custom-dialog--large.custom-dialog--fluid {
  max-width: var(--dialog-table-max);
}

::v-deep .el-dialog.custom-dialog--large .el-dialog__body {
  max-height: calc(100vh - 20px - 110px);
  flex: 1;
  min-height: 0;
}
</style>
