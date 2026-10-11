<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">{{ $t("agentTemplateManagement.title") }}</h2>
      <div class="right-operations">
        <el-input
          :placeholder="$t('agentTemplateManagement.searchPlaceholder')"
          v-model="search"
          class="search-input"
          clearable
          @keyup.enter.native="handleSearch"
          style="width: 240px"
        />
        <el-button class="btn-search" @click="handleSearch">
          {{ $t("agentTemplateManagement.search") }}
        </el-button>
      </div>
    </div>

    <!-- Main content -->
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="template-card" shadow="never">
            <el-table
              ref="templateTable"
              :data="templateList"
              style="width: 100%"
              v-loading="templateLoading"
              :element-loading-text="$t('agentTemplateManagement.loading')"
              element-loading-spinner="el-icon-loading"
              element-loading-background="rgba(255, 255, 255, 0.7)"
              class="transparent-table"
              :header-cell-style="{ padding: '10px 20px' }"
              :cell-style="{ padding: '10px 20px' }"
            >
              <!-- Remove @row-click="handleRowClick" -->
              <!-- Custom selection column, header shows "Select" text, data rows show checkboxes -->
              <el-table-column
                :label="$t('agentTemplateManagement.select')"
                align="center"
                min-width="100"
              >
                <template slot-scope="scope">
                  <el-checkbox
                    v-model="scope.row.selected"
                    @change="handleRowSelectionChange(scope.row)"
                    @click.stop
                  ></el-checkbox>
                </template>
              </el-table-column>
              <!-- Template name -->
              <el-table-column
                :label="$t('agentTemplateManagement.templateName')"
                prop="agentName"
                min-width="250"
                show-overflow-tooltip
              >
                <template slot-scope="scope">
                  <span>{{ scope.row.agentName }}</span>
                </template>
              </el-table-column>
              <!-- Changed to serial number column and moved here -->
              <el-table-column
                :label="$t('agentTemplateManagement.serialNumber')"
                min-width="120"
                align="center"
              >
                <template slot-scope="scope">
                  <span>{{ (currentPage - 1) * pageSize + scope.$index + 1 }}</span>
                </template>
              </el-table-column>
              <!-- Action column -->
              <el-table-column
                :label="$t('agentTemplateManagement.action')"
                min-width="250"
                align="center"
              >
                <template slot-scope="scope">
                  <div style="display: flex; justify-content: center; gap: 15px">
                    <el-button type="text" @click="editTemplate(scope.row)">{{
                      $t("agentTemplateManagement.editTemplate")
                    }}</el-button>
                    <el-button type="text" @click="deleteTemplate(scope.row)">{{
                      $t("agentTemplateManagement.deleteTemplate")
                    }}</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <!-- Table bottom operation bar -->
            <div class="table_bottom">
              <div class="ctrl_btn">
                <el-button
                  type="primary"
                  @click="handleSelectAll"
                  size="mini"
                  class="select-all-btn"
                >
                  {{
                    isAllSelected
                      ? $t("agentTemplateManagement.deselectAll")
                      : $t("agentTemplateManagement.selectAll")
                  }}
                </el-button>
                <el-button type="success" @click="showAddTemplateDialog" size="mini">
                  {{ $t("agentTemplateManagement.createTemplate") }}
                </el-button>
                <el-button
                  type="danger"
                  @click="batchDeleteTemplate"
                  :disabled="!hasSelected"
                  size="mini"
                >
                  {{ $t("agentTemplateManagement.batchDelete") }}
                </el-button>
              </div>

              <!-- Pagination -->
              <div class="custom-pagination">
                <el-pagination
                  v-model:current-page="currentPage"
                  v-model:page-size="pageSize"
                  :page-sizes="pageSizeOptions"
                  layout="total, sizes, prev, pager, next, jumper"
                  :total="total"
                  @size-change="handlePageSizeChange"
                  @current-change="handlePageChange"
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
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar";
import agentApi from "@/apis/module/agent";

export default {
  name: "AgentTemplateManagement",
  components: {
    HeaderBar,
  },

  data() {
    return {
      // Template related
      templateList: [],
      templateLoading: false,
      selectedTemplates: [],
      isAllSelected: false, // Add select all state

      search: "",
      // Pagination related data
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
        agentCode: "Xiaozhi",
        agentName: "",
        systemPrompt: "",
        sort: 0,
        model: { ...DEFAULT_MODEL_CONFIG }
      },
      formRules: {
        agentName: [
          { required: true, message: "Enter assistant nickname", trigger: "blur" }
        ],
        systemPrompt: [
          { required: true, message: "Enter role description", trigger: "blur" }
        ]
      },
      originalForm: null
    };
  },
  created() {
    this.initTableColumns();
    this.loadTemplateList();
  },
  // Add hasSelected property in computed section
  computed: {
    hasSelected() {
      return this.selectedTemplates.length > 0;
    }
  },
  methods: {
    // Load template list
    // Improve error handling logic for loadTemplateList method
    loadTemplateList() {
      this.templateLoading = true;
      const params = {
        page: this.currentPage,
        limit: this.pageSize
      };
      if (this.search) {
        params.agentName = this.search;
      }

      try {
        agentApi.getAgentTemplatesPage(
          params,
          (res) => {
            // More robust response handling logic
            if (res && typeof res === "object") {
              if (res.data && res.data.code === 0) {
                const responseData = res.data.data || {};
                // Add selected property to each template
                this.templateList = Array.isArray(responseData.list)
                  ? responseData.list.map((item) => ({ ...item, selected: false }))
                  : [];
                this.total =
                  typeof responseData.total === "number" ? responseData.total : 0;
              } else {
                this.templateList = [];
                this.total = 0;
                this.$message.error(
                  res?.data?.msg || this.$t("agentTemplateManagement.fetchTemplateFailed")
                );
              }
            } else {
              this.templateList = [];
              this.total = 0;
              this.$message.error(
                this.$t("agentTemplateManagement.fetchTemplateBackendError")
              );
            }
            this.templateLoading = false;
          },
          (error) => {
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

    // Search templates
    handleSearch() {
      this.currentPage = 1;
      this.loadTemplateList();
    },

    // Modify showAddTemplateDialog method to navigate to same page as edit page
    // Show add template dialog
    showAddTemplateDialog() {
      // Navigate to template quick config page, not passing templateId parameter means add new
      this.$router.push({
        path: "/template-quick-config",
      });
    },

    // Edit template
    editTemplate(row) {
      // Navigate to template quick config page and pass template ID parameter
      this.$router.push({
        path: "/template-quick-config",
        query: { templateId: row.id },
      });
    },
    handleDialogConfirm() {
      this.$refs.dialogForm.validate((valid) => {
        if (!valid) return;

    // Delete template
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
            if (res && typeof res === "object") {
              // Check if res.data exists and contains code=0
              if (res.data && res.data.code === 0) {
                this.$message.success(this.$t("agentTemplateManagement.deleteSuccess"));
                this.loadTemplateList();
              } else {
                this.$message.error(
                  res?.data?.msg || this.$t("agentTemplateManagement.deleteFailed")
                );
              }
            } else {
              this.$message.error(res?.data?.msg || this.$t("agentTemplateManagement.deleteFailed"));
            }
          });
        })
        .catch(() => {
          this.$message.info(this.$t("common.deleteCancelled"));
        });
    },

    // Batch delete templates
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
          // Ensure parameter format is correct - use id array as request body
          const ids = this.selectedTemplates.map((template) => template.id);
          agentApi.batchDeleteAgentTemplate(ids, (res) => {
            if (res && typeof res === "object") {
              if (res.data && res.data.code === 0) {
                this.$message.success(
                  this.$t("agentTemplateManagement.batchDeleteSuccess")
                );
                // Reload template list
                this.loadTemplateList();
                // Clear selected state
                this.selectedTemplates = [];
                this.isAllSelected = false;
              } else {
                this.$message.error(
                  res?.data?.msg || this.$t("agentTemplateManagement.batchDeleteFailed")
                );
              }
            } else {
              this.$message.error(res?.data?.msg || this.$t("agentTemplateManagement.batchDeleteFailed"));
            }
          });
        })
        .catch(() => {
          this.$message.info(this.$t("common.deleteCancelled"));
        });
    },

    // Complete pagination related methods
    handlePageChange(page) {
      this.currentPage = page;
      this.loadTemplateList();
    },
    handlePageSizeChange(size) {
      this.pageSize = size;
      this.currentPage = 1;
      this.loadTemplateList();
    },

    goFirst() {
      this.currentPage = 1;
    },
    goPrev() {
      this.currentPage--;
    },
    goNext() {
      this.currentPage++;
    },
    goToPage(page) {
      this.currentPage = page;
    },
    getVisiblePages() {
      const pages = [];
      const totalPages = this.pageCount;
      const currentPage = this.currentPage;

      if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) {
          pages.push(i);
        }
      } else {
        if (currentPage <= 4) {
          for (let i = 1; i <= 5; i++) {
            pages.push(i);
          }
          pages.push("...");
          pages.push(totalPages);
        } else if (currentPage >= totalPages - 3) {
          pages.push(1);
          pages.push("...");
          for (let i = totalPages - 4; i <= totalPages; i++) {
            pages.push(i);
          }
        } else {
          pages.push(1);
          pages.push("...");
          for (let i = currentPage - 1; i <= currentPage + 1; i++) {
            pages.push(i);
          }
          pages.push("...");
          pages.push(totalPages);
        }
      }

      return pages;
    },

    // Modify handleSelectAll method
    handleSelectAll() {
      this.isAllSelected = !this.isAllSelected;
      this.templateList.forEach((row) => {
        row.selected = this.isAllSelected;
      });
      // Update selected template list
      this.selectedTemplates = this.isAllSelected ? [...this.templateList] : [];
    },

    // Handle row selection change
    handleRowSelectionChange(row) {
      // Find selected templates
      this.selectedTemplates = this.templateList.filter((template) => template.selected);
      // Update select all state
      this.isAllSelected =
        this.templateList.length > 0 &&
        this.selectedTemplates.length === this.templateList.length;
    }
  }
};
</script>

<style scoped lang="scss">
/* Basic background and layout settings */
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

/* Operation bar styles */
.operation-bar {
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
  width: 200px;
}

.btn-search {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
}

/* Main container styles */
.main-wrapper {
  margin: 5px 22px;
  border-radius: 15px;
  min-height: calc(100vh - 24vh);
  height: auto;
  max-height: 80vh;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  background: rgba(237, 242, 255, 0.5);
  display: flex;
  flex-direction: column;
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

/* Template card styles */
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

/* Table styles - optimized integrated version */
.transparent-table {
  width: 100%;
  flex: 1;
  min-height: 0;
}

:deep(.el-table) {
  height: 100%;
  display: flex;
  flex-direction: column;
  --table-max-height: calc(100vh - 42vh);
  max-height: var(--table-max-height);

  /* Table header styles */
  .el-table__header th {
    padding: 8px 0 !important;
    height: 40px !important;
  }

  .el-table__header th .cell {
    color: #303133 !important;
    font-weight: 600;
  }

  /* Table body styles */
  .el-table__body {
    .el-table__row td {
      padding: 12px 0 !important;
      border-bottom: 1px solid #ebeef5;
    }
    .el-table__row:hover {
      background-color: #f5f7fa;
    }
  }

  /* Table button styles */
  .el-button--text {
    color: #7079aa;
  }

  .el-button--text:hover {
    color: #5a64b5;
  }

  /* Cell text styles */
  .cell {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

/* Table bottom operation bar */
.table_bottom {
  display: flex;
  justify-content: space-between !important;
  align-items: center;
  margin-top: auto;
  padding: 0 20px 15px !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

/* Control button styles */
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