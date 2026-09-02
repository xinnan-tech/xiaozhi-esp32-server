<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="template-card" shadow="never">
            <div class="operation-header">
              <h2 class="page-title">{{ $t("agentTemplateManagement.title") }}</h2>
              <div class="right-operations">
                <el-input
                  :placeholder="$t('agentTemplateManagement.searchPlaceholder')"
                  v-model="search"
                  class="search-input"
                  clearable
                  @keyup.enter.native="handleSearch"
                />
                <CustomButton icon="el-icon-search" type="confirm" @click="handleSearch">
                  {{ $t("agentTemplateManagement.search") }}
                </CustomButton>
              </div>
            </div>
            <CustomTable
              ref="templateTable"
              :data="templateList"
              :columns="tableColumns"
              :loading="templateLoading"
              :show-selection="true"
              :show-operations="true"
              :operations-label="$t('agentTemplateManagement.action')"
              :total="total"
              :current-page="currentPage"
              :page-size="pageSize"
              :page-size-options="pageSizeOptions"
              @size-change="handlePageSizeChange"
              @page-change="handlePageChange"
            >
              <template slot="selection" slot-scope="scope">
                <el-checkbox v-model="scope.row.selected" @change="handleRowSelectionChange(scope.row)"></el-checkbox>
              </template>
              <template slot="serialNumber" slot-scope="scope">
                <span>{{ (currentPage - 1) * pageSize + scope.$index + 1 }}</span>
              </template>
              <template slot="operations" slot-scope="scope">
                <el-button size="mini" type="text" @click="editTemplate(scope.row)">
                  {{ $t("agentTemplateManagement.editTemplate") }}
                </el-button>
                <el-button size="mini" type="text" @click="deleteTemplate(scope.row)">
                  {{ $t("agentTemplateManagement.deleteTemplate") }}
                </el-button>
              </template>
              <template slot="footer-btns">
                <div class="ctrl_btn">
                  <CustomButton :icon="isAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'" size="small" @click="handleSelectAll">
                    {{ isAllSelected ? $t("agentTemplateManagement.deselectAll") : $t("agentTemplateManagement.selectAll") }}
                  </CustomButton>
                  <CustomButton type="add" icon="el-icon-plus" size="small" @click="showAddTemplateDialog">
                    {{ $t("agentTemplateManagement.createTemplate") }}
                  </CustomButton>
                  <CustomButton size="small" type="delete" icon="el-icon-delete" @click="batchDeleteTemplate">
                    {{ $t("agentTemplateManagement.batchDelete") }}
                  </CustomButton>
                </div>
              </template>
            </CustomTable>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 新增/编辑模板弹窗 -->
    <CustomDialog
      :title="dialogTitle"
      :visible.sync="dialogVisible"
      :confirm-loading="confirmLoading"
      :footer="true"
      :width="'1200px'"
      @confirm="handleDialogConfirm"
      @cancel="dialogVisible = false"
    >
      <el-form ref="dialogForm" :model="form" :rules="formRules" label-width="100px">
        <el-form-item :label="$t('templateQuickConfig.agentSettings.agentName')" prop="agentName">
          <el-input
            v-model="form.agentName"
            :placeholder="$t('templateQuickConfig.agentSettings.agentNamePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('templateQuickConfig.agentSettings.systemPrompt')" prop="systemPrompt">
          <el-input
            v-model="form.systemPrompt"
            type="textarea"
            :placeholder="$t('templateQuickConfig.agentSettings.systemPromptPlaceholder')"
            show-word-limit
            maxlength="2000"
            :rows="16"
          />
        </el-form-item>
      </el-form>
    </CustomDialog>

    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar";
import agentApi from "@/apis/module/agent";
import VersionFooter from "@/components/VersionFooter.vue";
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";
import CustomDialog from "@/components/CustomDialog.vue";

const DEFAULT_MODEL_CONFIG = {
  ttsModelId: "TTS_EdgeTTS",
  vadModelId: "VAD_SileroVAD",
  asrModelId: "ASR_FunASR",
  llmModelId: "LLM_ChatGLMLLM",
  vllmModelId: "VLLM_ChatGLMVLLM",
  memModelId: "Memory_nomem",
  intentModelId: "Intent_function_call"
};

export default {
  name: "AgentTemplateManagement",
  components: {
    HeaderBar,
    VersionFooter,
    CustomButton,
    CustomTable,
    CustomDialog
  },

  data() {
    return {
      templateList: [],
      templateLoading: false,
      selectedTemplates: [],
      isAllSelected: false,
      search: "",
      pageSizeOptions: [10, 20, 50, 100],
      currentPage: 1,
      pageSize: 10,
      total: 0,
      tableColumns: [],
      dialogVisible: false,
      dialogTitle: "",
      confirmLoading: false,
      form: {
        id: null,
        agentCode: "小智",
        agentName: "",
        systemPrompt: "",
        sort: 0,
        model: { ...DEFAULT_MODEL_CONFIG }
      },
      formRules: {
        agentName: [
          { required: true, message: "请输入助手昵称", trigger: "blur" }
        ],
        systemPrompt: [
          { required: true, message: "请输入角色介绍", trigger: "blur" }
        ]
      },
      originalForm: null
    };
  },
  created() {
    this.initTableColumns();
    this.loadTemplateList();
  },
  computed: {
    hasSelected() {
      return this.selectedTemplates.length > 0;
    }
  },
  methods: {
    initTableColumns() {
      this.tableColumns = [
        {
          prop: "agentName",
          label: this.$t("agentTemplateManagement.templateName"),
        },
        {
          prop: "serialNumber",
          label: this.$t("agentTemplateManagement.serialNumber"),
        }
      ];
    },
    loadTemplateList() {
      this.templateLoading = true;
      const params = {
        page: this.currentPage,
        limit: this.pageSize
      };
      if (this.search) {
        params.agentName = this.search;
      }

      agentApi.getAgentTemplatesPage(
        params,
        (res) => {
          if (res && res.data && res.data.code === 0) {
            const responseData = res.data.data || {};
            this.templateList = Array.isArray(responseData.list)
              ? responseData.list.map((item) => ({ ...item, selected: false }))
              : [];
            this.total = typeof responseData.total === "number" ? responseData.total : 0;
          } else {
            this.templateList = [];
            this.total = 0;
            this.$message.error(res?.data?.msg || this.$t("agentTemplateManagement.fetchTemplateFailed"));
          }
          this.templateLoading = false;
        },
        (error) => {
          this.templateList = [];
          this.total = 0;
          this.templateLoading = false;
          this.$message.error(this.$t("common.networkError"));
        }
      );
    },
    handleSearch() {
      this.currentPage = 1;
      this.loadTemplateList();
    },
    showAddTemplateDialog() {
      this.dialogTitle = this.$t("templateQuickConfig.addTemplate");
      this.form = {
        id: null,
        agentCode: "小智",
        agentName: this.$t("templateQuickConfig.newTemplate"),
        systemPrompt: "",
        sort: 1,
        model: { ...DEFAULT_MODEL_CONFIG }
      };
      this.originalForm = JSON.parse(JSON.stringify(this.form));
      this.dialogVisible = true;
    },
    editTemplate(row) {
      this.dialogTitle = this.$t("templateQuickConfig.editTemplate");
      this.fetchTemplateById(row.id);
    },
    fetchTemplateById(templateId) {
      agentApi.getAgentTemplateById(templateId, (res) => {
        if (res && res.data && res.data.code === 0 && res.data.data) {
          const template = res.data.data;
          this.form = {
            id: template.id,
            agentCode: template.agentCode || "小智",
            agentName: template.agentName || "",
            systemPrompt: template.systemPrompt || "",
            sort: template.sort || 0,
            model: {
              ttsModelId: template.ttsModelId || DEFAULT_MODEL_CONFIG.ttsModelId,
              vadModelId: template.vadModelId || DEFAULT_MODEL_CONFIG.vadModelId,
              asrModelId: template.asrModelId || DEFAULT_MODEL_CONFIG.asrModelId,
              llmModelId: template.llmModelId || DEFAULT_MODEL_CONFIG.llmModelId,
              vllmModelId: template.vllmModelId || DEFAULT_MODEL_CONFIG.vllmModelId,
              memModelId: template.memModelId || DEFAULT_MODEL_CONFIG.memModelId,
              intentModelId: template.intentModelId || DEFAULT_MODEL_CONFIG.intentModelId
            }
          };
          this.originalForm = JSON.parse(JSON.stringify(this.form));
          this.dialogVisible = true;
        } else {
          this.$message.error(res?.data?.msg || this.$t("templateQuickConfig.templateNotFound"));
        }
      });
    },
    handleDialogConfirm() {
      this.$refs.dialogForm.validate((valid) => {
        if (!valid) return;

        const configData = {
          id: this.form.id || "",
          agentCode: this.form.agentCode,
          agentName: this.form.agentName,
          systemPrompt: this.form.systemPrompt,
          sort: this.form.sort,
          functions: [],
          ...this.form.model
        };

        this.confirmLoading = true;
        const apiCall = this.form.id
          ? agentApi.updateAgentTemplate
          : agentApi.addAgentTemplate;

      apiCall(configData, (res) => {
        this.confirmLoading = false;
        if (res && res.data && res.data.code === 0) {
          this.$message.success({
            message: this.$t("templateQuickConfig.saveSuccess"),
            showClose: true
          });
          this.dialogVisible = false;
          this.loadTemplateList();
        } else {
          this.$message.error({
            message: res?.data?.msg || this.$t("templateQuickConfig.saveFailed"),
            showClose: true
          });
        }
      }, (error) => {
        this.confirmLoading = false;
        this.$message.error(this.$t("common.networkError"));
      });
      });
    },
    deleteTemplate(row) {
      this.$confirm(
        this.$t("agentTemplateManagement.confirmSingleDelete"),
        this.$t("common.warning"),
        {
          confirmButtonText: this.$t("common.confirm"),
          cancelButtonText: this.$t("common.cancel"),
          type: "warning"
        }
      )
        .then(() => {
          agentApi.deleteAgentTemplate(row.id, (res) => {
            if (res && res.data && res.data.code === 0) {
              this.$message.success(this.$t("agentTemplateManagement.deleteSuccess"));
              this.selectedTemplates = [];
              this.isAllSelected = false;
              this.loadTemplateList();
            } else {
              this.$message.error(res?.data?.msg || this.$t("agentTemplateManagement.deleteFailed"));
            }
          });
        })
        .catch(() => {
          this.$message.info(this.$t("common.deleteCancelled"));
        });
    },
    batchDeleteTemplate() {
      if (this.selectedTemplates.length === 0) {
        this.$message.warning(this.$t("agentTemplateManagement.selectTemplate"));
        return;
      }
      this.$confirm(
        this.$t("agentTemplateManagement.confirmBatchDelete", { count: this.selectedTemplates.length }),
        this.$t("common.warning"),
        {
          confirmButtonText: this.$t("common.confirm"),
          cancelButtonText: this.$t("common.cancel"),
          type: "warning"
        }
      )
        .then(() => {
          const ids = this.selectedTemplates.map((template) => template.id);
          agentApi.batchDeleteAgentTemplate(ids, (res) => {
            if (res && res.data && res.data.code === 0) {
              this.$message.success(this.$t("agentTemplateManagement.batchDeleteSuccess"));
              this.loadTemplateList();
              this.selectedTemplates = [];
              this.isAllSelected = false;
            } else {
              this.$message.error(res?.data?.msg || this.$t("agentTemplateManagement.batchDeleteFailed"));
            }
          });
        })
        .catch(() => {
          this.$message.info(this.$t("common.deleteCancelled"));
        });
    },
    handlePageChange(page) {
      this.currentPage = page;
      this.loadTemplateList();
    },
    handlePageSizeChange(size) {
      this.pageSize = size;
      this.currentPage = 1;
      this.loadTemplateList();
    },
    handleSelectAll() {
      this.isAllSelected = !this.isAllSelected;
      this.templateList.forEach((row) => {
        row.selected = this.isAllSelected;
      });
      this.selectedTemplates = this.isAllSelected ? [...this.templateList] : [];
    },
    handleRowSelectionChange(row) {
      this.selectedTemplates = this.templateList.filter((template) => template.selected);
      this.isAllSelected =
        this.templateList.length > 0 &&
        this.selectedTemplates.length === this.templateList.length;
    }
  }
};
</script>

<style lang="scss" scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background: #eff4ff;
  background-size: cover;
  overflow: hidden;
}

.main-wrapper {
  height: calc(100vh - 63px - 35px);
  padding: 20px 22px 0;
  position: relative;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.operation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 16px 0;
}

.page-title {
  font-weight: 500;
  font-size: 24px;
  margin: 0;
}

.right-operations {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.search-input {
  width: 240px;
}

.content-panel {
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.content-area {
  flex: 1;
  height: 100%;
  min-width: 600px;
  overflow: auto;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.template-card {
  background: white;
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
  overflow: hidden;

  ::v-deep .el-card__body {
    padding: 14px 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }
}

.ctrl_btn {
  display: flex;
}

:deep(.el-table .el-button--text) {
  color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5;
}
</style>