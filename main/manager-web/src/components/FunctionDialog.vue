<template>
  <el-drawer :visible.sync="dialogVisible" direction="rtl" size="80%" :wrapperClosable="false" :withHeader="false">
    <!-- 自定义标题区域 -->
    <div class="custom-header">
      <div class="header-left">
        <h3 class="bold-title">功能管理</h3>
      </div>
      <button class="custom-close-btn" @click="closeDialog">×</button>
    </div>

    <div class="function-manager">
      <!-- 左侧：未选功能 -->
      <div class="function-column">
        <div class="column-header">
          <h4 class="column-title">未选功能</h4>
          <el-button type="text" @click="selectAll" class="select-all-btn">全选</el-button>
        </div>
        <div class="function-list">
          <div v-if="unselected.length">
            <div v-for="func in unselected" :key="func.name" class="function-item">
              <el-checkbox :label="func.name" v-model="selectedNames" @change="(val) => handleCheckboxChange(func, val)"
                @click.native.stop></el-checkbox>
              <div class="func-tag" @click="handleFunctionClick(func)">
                <div class="color-dot" :style="{ backgroundColor: getFunctionColor(func.name) }"></div>
                <span>{{ func.name }}</span>
              </div>
            </div>
          </div>
          <div v-else style="display: flex; justify-content: center; align-items: center;">
            <el-empty description="没有更多的插件了" />
          </div>
        </div>
      </div>

      <!-- 中间：已选功能 -->
      <div class="function-column">
        <div class="column-header">
          <h4 class="column-title">已选功能</h4>
          <el-button type="text" @click="deselectAll" class="select-all-btn">全选</el-button>
        </div>
        <div class="function-list">
          <div v-if="selectedList.length > 0">
            <div v-for="func in selectedList" :key="func.name" class="function-item">
              <el-checkbox :label="func.name" v-model="selectedNames" @change="(val) => handleCheckboxChange(func, val)"
                @click.native.stop></el-checkbox>
              <div class="func-tag" @click="handleFunctionClick(func)">
                <div class="color-dot" :style="{ backgroundColor: getFunctionColor(func.name) }"></div>
                <span>{{ func.name }}</span>
              </div>
            </div>
          </div>
          <div v-else style="display: flex; justify-content: center; align-items: center;">
            <el-empty description="请选择插件功能" />
          </div>
        </div>
      </div>

      <!-- 右侧：参数配置 -->
      <div class="params-column">
        <h4 v-if="currentFunction" class="column-title">参数配置 - {{ currentFunction.name }}</h4>
        <div v-if="currentFunction" class="params-container">
          <el-form :model="currentFunction" class="param-form">
            <!-- 遍历 fieldsMeta，而不是 params 的 keys -->
            <div v-if="currentFunction.fieldsMeta.length == 0">
              <el-empty :description="currentFunction.name + ' 无需配置参数'" />
            </div>
            <el-form-item v-for="field in currentFunction.fieldsMeta" :key="field.key" :label="field.label"
              class="param-item" :class="{ 'textarea-field': field.type === 'array' || field.type === 'json' }">
              <template #label>
                <span style="font-size: 16px; margin-right: 6px;">{{ field.label }}</span>
                <el-tooltip effect="dark" :content="fieldRemark(field)" placement="top">
                  <img src="@/assets/home/info.png" alt="" class="info-icon">
                </el-tooltip>
              </template>
              <!-- ARRAY -->
              <el-input v-if="field.type === 'array'" type="textarea" v-model="currentFunction.params[field.key]"
                @change="val => handleParamChange(currentFunction, field.key, val)" />

              <!-- JSON -->
              <el-input v-else-if="field.type === 'json'" type="textarea" :rows="6" placeholder="请输入合法的 JSON"
                v-model="textCache[field.key]" @blur="flushJson(field)" />

              <!-- number -->
              <el-input-number v-else-if="field.type === 'number'" :value="currentFunction.params[field.key]"
                @change="val => handleParamChange(currentFunction, field.key, val)" />

              <!-- boolean -->
              <el-switch v-else-if="field.type === 'boolean' || field.type === 'bool'"
                :value="currentFunction.params[field.key]"
                @change="val => handleParamChange(currentFunction, field.key, val)" />

              <!-- string or fallback -->
              <el-input v-else v-model="currentFunction.params[field.key]"
                @change="val => handleParamChange(currentFunction, field.key, val)" />
            </el-form-item>
          </el-form>
        </div>
        <div v-else class="empty-tip">请选择已配置的功能进行参数设置</div>
      </div>
    </div>

    <div class="drawer-footer">
      <el-button @click="closeDialog">取消</el-button>
      <el-button type="primary" @click="saveSelection">保存配置</el-button>
    </div>
  </el-drawer>
</template>

<script>
export default {
  props: {
    value: Boolean,
    functions: {
      type: Array,
      default: () => []
    },
    allFunctions: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      textCache: {},
      dialogVisible: this.value,
      selectedNames: [],
      currentFunction: null,
      modifiedFunctions: {},
      functionColorMap: [
        '#FF6B6B', '#4ECDC4', '#45B7D1',
        '#96CEB4', '#FFEEAD', '#D4A5A5', '#A2836E'
      ],
      tempFunctions: {},
      // 添加一个标志位来跟踪是否已经保存
      hasSaved: false,
      loading: false,
    }
  },
  computed: {
    selectedList() {
      return this.allFunctions.filter(f => this.selectedNames.includes(f.name));
    },
    unselected() {
      return this.allFunctions.filter(f => !this.selectedNames.includes(f.name));
    }
  },
  watch: {
    currentFunction(newFn) {
      if (!newFn) return;
      // 对每个字段，如果是 array 或 json，就在 textCache 里生成初始字符串
      newFn.fieldsMeta.forEach(f => {
        const v = newFn.params[f.key];
        if (f.type === 'array') {
          this.$set(this.textCache, f.key, Array.isArray(v) ? v.join('\n') : '');
        }
        else if (f.type === 'json') {
          try {
            this.$set(this.textCache, f.key, JSON.stringify(v ?? {}, null, 2));
          } catch {
            this.$set(this.textCache, f.key, '');
          }
        }
      });
    },
    value(v) {
      this.dialogVisible = v;
      if (v) {
        // 对话框打开时，初始化选中态
        this.selectedNames = this.functions.map(f => f.name);
        // 把后端传来的 this.functions（带 params）merge 到 allFunctions 上
        this.functions.forEach(saved => {
          const idx = this.allFunctions.findIndex(f => f.name === saved.name);
          if (idx >= 0) {
            // 保留用户之前在 saved.params 上的改动
            this.allFunctions[idx].params = { ...saved.params };
          }
        });
        // 右侧默认指向第一个
        this.currentFunction = this.selectedList[0] || null;
      }
    },
    dialogVisible(newVal) {
      this.$emit('input', newVal);
    }
  },
  methods: {
    flushArray(key) {
      const text = this.textCache[key] || '';
      const arr = text
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean);
      this.handleParamChange(this.currentFunction, key, arr);
    },

    flushJson(field) {
      const key = field.key;
      if (!key) {
        return;
      }
      const text = this.textCache[key] || '';
      try {
        const obj = JSON.parse(text);
        this.handleParamChange(this.currentFunction, key, obj);
      } catch {
        this.$message.error(`${this.currentFunction.name}的${key}字段格式错误：JSON格式有误`);
      }
    },
    handleFunctionClick(func) {
      if (this.selectedNames.includes(func.name)) {
        const tempFunc = this.tempFunctions[func.name];
        this.currentFunction = tempFunc ? tempFunc : func;
      }
    },
    handleParamChange(func, key, value) {
      if (!this.tempFunctions[func.name]) {
        this.tempFunctions[func.name] = JSON.parse(JSON.stringify(func));
      }
      this.tempFunctions[func.name].params[key] = value;
    },
    handleCheckboxChange(func, checked) {
      if (checked) {
        if (!this.selectedNames.includes(func.name)) {
          this.selectedNames = [...this.selectedNames, func.name];
        }
      } else {
        this.selectedNames = this.selectedNames.filter(name => name !== func.name);
      }

      if (this.selectedList.length > 0) {
        this.currentFunction = this.selectedList[0];
      } else {
        this.currentFunction = null;
      }
    },

    selectAll() {
      this.selectedNames = [...this.allFunctions.map(f => f.name)];
      if (this.selectedList.length > 0) {
        this.currentFunction = JSON.parse(JSON.stringify(this.selectedList[0]));
      }
    },

    deselectAll() {
      this.selectedNames = [];
      this.currentFunction = null;
    },

    closeDialog() {
      this.tempFunctions = {};
      this.selectedNames = this.functions.map(f => f.name);
      this.currentFunction = null;
      this.dialogVisible = false;
      this.$emit('input', false);
      this.$emit('dialog-closed', false);
    },

    saveSelection() {
      Object.keys(this.tempFunctions).forEach(name => {
        this.modifiedFunctions[name] = JSON.parse(JSON.stringify(this.tempFunctions[name]));
      });
      this.tempFunctions = {};
      this.hasSaved = true;

      const selected = this.selectedList.map(f => {
        const modified = this.modifiedFunctions[f.name];
        return {
          id: f.id,
          name: f.name,
          params: modified
            ? { ...modified.params }
            : { ...f.params }
        }
      });

      this.$emit('update-functions', selected);
      this.dialogVisible = false;
      // 通知父组件对话框已关闭且已保存
      this.$emit('dialog-closed', true);
    },
    getFunctionColor(name) {
      const hash = [...name].reduce((acc, char) => acc + char.charCodeAt(0), 0);
      return this.functionColorMap[hash % this.functionColorMap.length];
    },
    fieldRemark(field) {
      let description = (field && field.label) ? field.label : '';
      if (field.default) {
        description += `（默认值：${field.default}）`;
      }
      return description;
    },
  }
}
</script>

<style lang="scss" scoped>
.function-manager {
  display: grid;
  grid-template-columns: max-content max-content 1fr;
  gap: 12px;
  height: calc(70vh - 60px);
}

.custom-header {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #EBEEF5;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .bold-title {
    font-size: 18px;
    font-weight: bold;
    margin: 0;
  }

  .select-all-btn {
    padding: 0;
    height: auto;
    font-size: 14px;
  }
}

.function-column {
  position: relative;
  width: auto;
  padding: 10px;
  overflow-y: auto;
  border-right: 1px solid #EBEEF5;
  scrollbar-width: none;
  overflow-x: hidden;
}

.function-column::-webkit-scrollbar {
  display: none;
}

.function-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.function-item {
  padding: 8px 12px;
  margin: 4px 0;
  width: 100%;
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: space-between;

  &:hover {
    background-color: #f5f7fa;
  }
}

.params-column {
  min-width: 280px;
  padding: 10px;
  overflow-y: auto;
  scrollbar-width: none;
}

.params-column::-webkit-scrollbar {
  display: none;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.column-title {
  text-align: center;
  width: 100%;
}

.func-tag {
  display: flex;
  align-items: center;
  cursor: pointer;
  flex-grow: 1;
  margin-left: 8px;
}

.color-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  margin-right: 8px;
  border-radius: 50%;
}

.param-form {
  .param-item {
    font-size: 16px;

    &.textarea-field {
      ::v-deep .el-form-item__content {
        margin-left: 0 !important;
        display: block;
        width: 100%;
      }

      ::v-deep .el-form-item__label {
        display: block;
        width: 100% !important;
        margin-bottom: 8px;
      }
    }
  }

  .param-input {
    width: 100%;
  }

  ::v-deep .el-form-item {
    display: flex;
    flex-direction: column;
    margin-bottom: 12px;

    .el-form-item__label {
      font-size: 14px !important;
      color: #606266;
      text-align: left;
      padding-right: 10px;
      flex-shrink: 0;
      width: auto !important;
    }

    .el-form-item__content {
      margin-left: 0 !important;
      flex-grow: 1;

      .el-input__inner {
        text-align: left;
        padding-left: 8px;
        width: 100%;
      }
    }
  }
}

.params-container {
  padding: 16px;
  border-radius: 4px;
  min-width: 280px;
}

.empty-tip {
  padding: 20px;
  color: #909399;
  text-align: center;
}


.drawer-footer {
  position: absolute;
  bottom: 0;
  width: 100%;
  border-top: 1px solid #e8e8e8;
  padding: 10px 16px;
  text-align: center;
  background: #fff;
}

.info-icon {
  width: 16px;
  height: 16px;
  margin-right: 1vh;
}

.custom-close-btn {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  width: 35px;
  height: 35px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 30px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0;
  outline: none;
  transition: all 0.3s;
}

.custom-close-btn:hover {
  color: #409EFF;
  border-color: #409EFF;
}

::v-deep .el-checkbox__label {
  display: none;
}
</style>