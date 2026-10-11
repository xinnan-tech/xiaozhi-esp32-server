<template>
  <el-drawer :visible.sync="dialogVisible" direction="rtl" size="80%" :wrapperClosable="false" :withHeader="false">
    <!-- Custom title area -->
    <div class="custom-header">
      <div class="header-left">
        <h3 class="bold-title">{{ $t('functionDialog.title') }}</h3>
      </div>
      <button class="custom-close-btn" @click="closeDialog">×</button>
    </div>

    <div class="function-manager">
      <!-- Left: No feature selected -->
      <div class="function-column">
        <div class="column-header">
          <h4 class="column-title">{{ $t('functionDialog.unselectedFunctions') }}</h4>
          <el-button type="text" @click="selectAll" class="select-all-btn">
            {{ $t('functionDialog.selectAll') }}
          </el-button>
        </div>
        <div class="function-list">
          <div v-if="unselected.length">
            <div v-for="func in unselected" :key="func.name" class="function-item">
              <el-checkbox :label="func.name" v-model="selectedNames" @change="(val) => handleCheckboxChange(func, val)"
                @click.native.stop></el-checkbox>
              <div class="func-tag" @click="handleFunctionClick(func)">
                <div class="color-dot"></div>
                <span>{{ func.name }}</span>
              </div>
            </div>
          </div>
          <div v-else style="display: flex; justify-content: center; align-items: center;">
            <el-empty :description="$t('functionDialog.noMorePlugins')" />
          </div>
        </div>
      </div>

      <!-- Middle: Selected features -->
      <div class="function-column">
        <div class="column-header">
          <h4 class="column-title">{{ $t('functionDialog.selectedFunctions') }}</h4>
          <el-button type="text" @click="deselectAll" class="select-all-btn">
            {{ $t('functionDialog.selectAll') }}
          </el-button>
        </div>
        <div class="function-list">
          <div v-if="selectedList.length > 0">
            <div v-for="func in selectedList" :key="func.name" class="function-item">
              <el-checkbox :label="func.name" v-model="selectedNames" @change="(val) => handleCheckboxChange(func, val)"
                @click.native.stop></el-checkbox>
              <div class="func-tag" @click="handleFunctionClick(func)">
                <div class="color-dot"></div>
                <span>{{ func.name }}</span>
              </div>
            </div>
          </div>
          <div v-else style="display: flex; justify-content: center; align-items: center;">
            <el-empty :description="$t('functionDialog.pleaseSelectPlugin')" />
          </div>
        </div>
      </div>

      <!-- Right side: Parameter config -->
      <div class="params-column">
        <h4 v-if="currentFunction" class="column-title">
          {{ $t('functionDialog.paramConfig') }} - {{ currentFunction.name }}
        </h4>
        <div v-if="currentFunction" class="params-container">
          <el-form :model="currentFunction" class="param-form">
            <!-- Iterate over fieldsMeta instead of params keys -->
            <div v-if="currentFunction.fieldsMeta.length == 0">
              <el-empty :description="currentFunction.name + $t('functionDialog.noNeedToConfig')" />
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
              <el-input v-else-if="field.type === 'json'" type="textarea" :rows="6" :placeholder="$t('functionDialog.enterValidJson')"
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
        <div v-else class="empty-tip">{{ $t('functionDialog.pleaseSelectFunctionForParam') }}</div>
      </div>
    </div>

    <!-- MCP Region -->
    <div class="mcp-access-point" v-if="featureStatus.mcpAccessPoint">
      <div class="mcp-container">
        <!-- Left area -->
        <div class="mcp-left">
          <div class="mcp-header">
            <h3 class="bold-title">{{ $t('functionDialog.mcpAccessPoint') }}</h3>
          </div>
          <div class="url-header">
            <div class="address-desc">
              <span>{{ $t('functionDialog.mcpAddressDesc') }}</span>
              <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/mcp-endpoint-enable.md"
                target="_blank" class="doc-link">{{ $t('functionDialog.howToDeployMcp') }}</a> &nbsp;&nbsp;|&nbsp;&nbsp;
              <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/mcp-endpoint-integration.md"
                target="_blank" class="doc-link">{{ $t('functionDialog.howToIntegrateMcp') }}</a> &nbsp;
            </div>
          </div>
          <el-input v-model="mcpUrl" readonly class="url-input">
            <template #suffix>
              <el-button @click="copyUrl" class="inner-copy-btn" icon="el-icon-document-copy">
                {{ $t('functionDialog.copy') }}
              </el-button>
            </template>
          </el-input>
        </div>

        <!-- Right-side area -->
        <div class="mcp-right">
          <div class="mcp-header">
            <h3 class="bold-title">{{ $t('functionDialog.accessPointStatus') }}</h3>
          </div>
          <div class="status-container">
            <span class="status-indicator" :class="mcpStatus"></span>
            <span class="status-text">{{
              mcpStatus === 'connected' ? $t('functionDialog.connected') :
                mcpStatus === 'loading' ? $t('functionDialog.loading') : $t('functionDialog.disconnected')
            }}</span>
            <button class="refresh-btn" @click="refreshStatus">
              <span class="refresh-icon">↻</span>
              <span>{{ $t('functionDialog.refresh') }}</span>
            </button>
          </div>
          <div class="mcp-tools-list">
            <div v-if="mcpTools.length > 0" class="tools-grid">
              <el-button v-for="tool in mcpTools" :key="tool" size="small" class="tool-btn" plain>
                {{ tool }}
              </el-button>
            </div>
            <div v-else class="no-tools">
              <span>{{ $t('functionDialog.noAvailableTools') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="drawer-footer">
      <el-button @click="closeDialog">{{ $t('functionDialog.cancel') }}</el-button>
      <el-button type="primary" @click="saveSelection">{{ $t('functionDialog.saveConfig') }}</el-button>
    </div>
  </el-drawer>
</template>

<script>
import Api from '@/apis/api';
import i18n from '@/i18n';
import featureManager from '@/utils/featureManager';

export default {
  i18n,

  props: {
    value: Boolean,
    functions: {
      type: Array,
      default: () => []
    },
    allFunctions: {
      type: Array,
      default: () => []
    },
    agentId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      textCache: {},
      dialogVisible: this.value,
      selectedNames: [],
      currentFunction: null,
      modifiedFunctions: {},
      tempFunctions: {},
      // Add a flag to track whether the state has been saved
      hasSaved: false,
      loading: false,

      mcpUrl: "",
      mcpStatus: "disconnected",
      mcpTools: [],
      
      // Feature status
      featureStatus: {
        mcpAccessPoint: false,
        addressBook: false
      }
    }
  },
  computed: {
    selectedList() {
      const list = this.allFunctions.filter(f => this.selectedNames.includes(f.name));
      // If the contacts feature is disabled, filter out the device-to-device call plugin
      if (!this.featureStatus.addressBook) {
        return list.filter(f => f.providerCode !== 'call_device');
      }
      return list;
    },
    unselected() {
      const list = this.allFunctions.filter(f => !this.selectedNames.includes(f.name));
      // If the contacts feature is disabled, filter out the device-to-device call plugin
      if (!this.featureStatus.addressBook) {
        return list.filter(f => f.providerCode !== 'call_device');
      }
      return list;
    }
  },
  watch: {
    currentFunction(newFn) {
      if (!newFn) return;
      // For each field, if it is an array or JSON, generate an initial string in textCache
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
    async value(v) {
      this.dialogVisible = v;
      if (v) {
        // Load feature status (must be done before initializing selection state)
        await this.loadFeatureStatus();

        // Initialize selection state when dialog opens
        this.selectedNames = this.functions.map(f => f.name);

        // If the contacts feature is disabled, remove the device-to-device call plugin from the selected list
        if (!this.featureStatus.addressBook) {
          this.selectedNames = this.selectedNames.filter(name => {
            const func = this.allFunctions.find(f => f.name === name);
            return func && func.providerCode !== 'call_device';
          });
        }

        // Merge backend-provided this.functions (with params) into allFunctions
        this.functions.forEach(saved => {
          const idx = this.allFunctions.findIndex(f => f.name === saved.name);
          if (idx >= 0) {
            // Preserve user changes to saved.params
            this.allFunctions[idx].params = { ...saved.params };
          }
        });
        // Right side defaults to the first item
        this.currentFunction = this.selectedList[0] || null;

        // Load MCP data
        this.loadMcpAddress();
        this.loadMcpTools();
      }
    },
    dialogVisible(newVal) {
      this.$emit('input', newVal);
    }
  },
  methods: {
    /**
     * Load feature status
     */
    async loadFeatureStatus() {
      // Ensure featureManager is fully initialized
      await featureManager.waitForInitialization();

      const config = featureManager.getConfig();
      this.featureStatus = {
        mcpAccessPoint: config.mcpAccessPoint || false,
        addressBook: config.addressBook || false
      };
    },
    
    copyUrl() {
      const textarea = document.createElement('textarea');
      textarea.value = this.mcpUrl;
      textarea.style.position = 'fixed';  // Prevent page scrolling
      document.body.appendChild(textarea);
      textarea.select();

      try {
        const successful = document.execCommand('copy');
        if (successful) {
          this.$message.success(this.$t('functionDialog.copiedToClipboard'));
        } else {
          this.$message.error(this.$t('functionDialog.copyFailed'));
        }
      } catch (err) {
        this.$message.error(this.$t('functionDialog.copyFailed'));
        console.error('Copy failed:', err);
      } finally {
        document.body.removeChild(textarea);
      }
    },

    refreshStatus() {
      this.mcpStatus = "loading";
      this.loadMcpTools();
    },

    // Load MCP endpoint address
    loadMcpAddress() {
      Api.agent.getAgentMcpAccessAddress(this.agentId, (res) => {
        if (res.data.code === 0) {
          this.mcpUrl = res.data.data || "";
        } else {
          this.mcpUrl = res.data.msg;
          console.error('Failed to get MCP address:', res.data.msg);
        }
      });
    },

    // Load MCP tool list
    loadMcpTools() {
      Api.agent.getAgentMcpToolsList(this.agentId, (res) => {
        if (res.data.code === 0) {
          this.mcpTools = res.data.data || [];
          // Update status based on tool list
          this.mcpStatus = this.mcpTools.length > 0 ? "connected" : "disconnected";
        } else {
          this.mcpTools = [];
          this.mcpStatus = "disconnected";
          console.error('Failed to get MCP tool list:', res.data.msg);
        }
      });
    },

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
        this.$message.error(`${this.currentFunction.name}${this.$t('functionDialog.jsonFormatError')}`);
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

      let selected = this.selectedList.map(f => {
        const modified = this.modifiedFunctions[f.name];
        return {
          id: f.id,
          name: f.name,
          params: modified
            ? { ...modified.params }
            : { ...f.params }
        }
      });

      // If contacts feature is disabled, automatically deselect the device call plugin
      if (!this.featureStatus.addressBook) {
        selected = selected.filter(f => f.providerCode !== 'call_device');
      }

      this.$emit('update-functions', selected);
      this.dialogVisible = false;
      // Notify parent component that dialog is closed and saved
      this.$emit('dialog-closed', true);
    },
    fieldRemark(field) {
      let description = (field && field.label) ? field.label : '';
      if (field.default) {
        description += `(${this.$t('functionDialog.defaultValue')}:${field.default})`;
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
  height: calc(58vh);
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
  display: flex;
  flex-direction: column;
  width: auto;
  height: 100%; 
  padding: 10px;
  border-right: 1px solid #EBEEF5;
  scrollbar-width: none;
  overflow-x: hidden;
  box-sizing: border-box;
}

.mcp-access-point {
  position: relative;
  z-index: 1;
  background: white;
}

.function-column::-webkit-scrollbar {
  display: none;
}

.function-list {
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
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
  background-color: #5778ff;
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
  z-index: 2;
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

.mcp-access-point {
  border-top: 1px solid #EBEEF5;
  padding: 20px 24px;
  text-align: left;
}

.mcp-header {
  .bold-title {
    font-size: 18px;
    font-weight: bold;
    margin: 5px 0 30px 0;
  }
}

.mcp-container {
  display: flex;
  justify-content: space-between;
  gap: 30px;
}

.mcp-left,
.mcp-right {
  flex: 1;
  padding-bottom: 50px;
}

.url-header {
  margin-bottom: 8px;
  color: black;

  h4 {
    margin: 0 0 15px 0;
    font-size: 16px;
    font-weight: normal;
  }

  .address-desc {
    display: flex;
    align-items: center;
    font-size: 14px;
    margin-bottom: 12px;

    .doc-link {
      color: #1677ff;
      text-decoration: none;
      margin-left: 4px;

      &:hover {
        text-decoration: underline;
      }
    }
  }
}

.url-input {
  border-radius: 4px 0 0 4px;
  font-size: 14px;
  height: 36px;
  box-sizing: border-box;

  ::v-deep .el-input__inner {
    background-color: #f5f5f5 !important;
  }

  ::v-deep .el-input__suffix {
    right: 0;
    display: flex;
    align-items: center;
    padding-right: 10px;

    .inner-copy-btn {
      pointer-events: auto;
      border: none;
      background: #1677ff;
      color: white;
      padding: 6px;
      margin-top: 4px;
      margin-left: 4px;
    }
  }
}

.mcp-right {
  h4 {
    margin: 0 0 10px 0;
    font-size: 16px;
    font-weight: normal;
    color: black;
  }
}

.status-container {
  display: flex;
  align-items: center;

  .status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;

    &.disconnected {
      background-color: #909399;
      /* Gray - Not connected */
    }

    &.connected {
      background-color: #67C23A;
      /* Green - Connected */
    }

    &.loading {
      background-color: #E6A23C;
      /* Orange - Loading */
      animation: pulse 1.5s infinite;
    }
  }

  .status-text {
    font-size: 14px;
    margin-right: 10px;
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    padding: 2px 10px;
    background: white;
    color: black;
    border: 1px solid #DCDFE6;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.3s;

    &:hover {
      background: #1677ff;
      color: white;
      border-color: #1677ff;
    }

    .refresh-icon {
      margin-right: 6px;
      font-size: 14px;
    }
  }
}

@keyframes pulse {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0.4;
  }

  100% {
    opacity: 1;
  }
}

.mcp-tools-list {
  margin-top: 10px;

  .tools-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .tool-btn {
    padding: 6px 12px;
    border-color: #1677ff;
    color: #1677ff;
    background-color: white;
    font-size: 12px;

    &:hover {
      background-color: #1677ff;
      color: white;
      border-color: #1677ff;
    }
  }

  .no-tools {
    text-align: center;
    color: #909399;
    font-size: 14px;
    padding: 10px 0;
  }
}
</style>
