<template>
  <el-dialog :title="title" :visible="dialogVisible" width="600px" class="address-book-dialog" @close="handleClose">
    <el-form ref="addressBookForm" :model="form" :rules="rules" label-width="100px" size="medium">
      <el-form-item :label="$t('addressBookDialog.name')" prop="name">
        <el-input v-model="form.name" :placeholder="$t('addressBookDialog.namePlaceholder')" clearable></el-input>
      </el-form-item>
      <el-form-item :label="$t('addressBookDialog.description')" prop="description">
        <el-input v-model="form.description" :placeholder="$t('addressBookDialog.descriptionPlaceholder')"
          type="textarea" :rows="4" maxlength="300" show-word-limit></el-input>
      </el-form-item>
      <el-form-item :label="$t('addressBookDialog.status')" prop="status">
        <el-switch
          v-model="form.status"
          :active-value="1"
          :inactive-value="0"
          active-color="#13ce66"
          inactive-color="#909399"
        />
      </el-form-item>
    </el-form>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleClose">{{ $t('addressBookDialog.cancel') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('addressBookDialog.confirm') }}</el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: "AddressBookDialog",
  props: {
    title: {
      type: String,
      default: ""
    },
    visible: {
      type: Boolean,
      default: false
    },
    form: {
      type: Object,
      default: () => ({
        id: null,
        name: "",
        description: "",
        status: 1
      })
    }
  },
  data() {
    return {
      dialogVisible: this.visible,
      rules: {
        name: [
          {
            required: true,
            message: this.$t("addressBookDialog.nameRequired"),
            trigger: "blur"
          },
          {
            min: 1,
            max: 50,
            message: this.$t("addressBookDialog.nameLength"),
            trigger: "blur"
          },
          {
            pattern: /^[一-龥a-zA-Z0-9\s-_]+$/,
            message: this.$t("addressBookDialog.namePattern"),
            trigger: "blur"
          }
        ],
        description: [
          {
            required: true,
            message: this.$t("addressBookDialog.descriptionRequired"),
            trigger: "blur"
          },
          {
            max: 300,
            message: this.$t("addressBookDialog.descriptionLength"),
            trigger: "blur"
          }
        ]
      }
    };
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
      if (val) {
        if (this.$refs.addressBookForm) {
          this.$refs.addressBookForm.clearValidate();
        }
      }
    }
  },
  methods: {
    handleClose() {
      if (this.$refs.addressBookForm) {
        this.$refs.addressBookForm.clearValidate();
      }
      this.dialogVisible = false;
      this.$emit("update:visible", false);
    },
    handleSubmit() {
      this.$refs.addressBookForm.validate(valid => {
        if (valid) {
          this.$emit("submit", {
            ...this.form
          });
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.address-book-dialog {
  ::v-deep .el-dialog {
    border-radius: 20px;
    overflow: hidden;
  }

  ::v-deep .el-dialog__body {
    padding: 20px 30px;
  }

  ::v-deep .el-form-item {
    margin-bottom: 20px;
  }

  ::v-deep .el-form-item__label {
    font-weight: 500;
    color: #34495e;
    font-size: 14px;
  }

  ::v-deep .el-input {
    .el-input__inner {
      height: 36px;
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  ::v-deep .el-textarea {
    .el-textarea__inner {
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>