<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">{{ $t("modelConfig." + activeTab) }}</h2>
      <div class="action-group">
        <div class="search-group">
          <el-input
            :placeholder="$t('modelConfig.searchPlaceholder')"
            v-model="search"
            class="search-input"
            clearable
            @keyup.enter.native="handleSearch"
            style="width: 240px"
          />
          <el-button class="btn-search" @click="handleSearch">
            {{ $t("modelConfig.search") }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Main content -->
    <div class="main-wrapper">
      <div class="content-panel">
        <!-- Left navigation -->
        <el-menu
          :default-active="activeTab"
          class="nav-panel"
          @select="handleMenuSelect"
          style="background-size: cover; background-position: center"
        >
          <el-menu-item index="vad">
            <span class="menu-text">{{ $t("modelConfig.vad") }}</span>
          </el-menu-item>
          <el-menu-item index="asr">
            <span class="menu-text">{{ $t("modelConfig.asr") }}</span>
          </el-menu-item>
          <el-menu-item index="llm">
            <span class="menu-text">{{ $t("modelConfig.llm") }}</span>
          </el-menu-item>
          <el-menu-item index="vllm">
            <span class="menu-text">{{ $t("modelConfig.vllm") }}</span>
          </el-menu-item>
          <el-menu-item index="intent">
            <span class="menu-text">{{ $t("modelConfig.intent") }}</span>
          </el-menu-item>
          <el-menu-item index="tts">
            <span class="menu-text">{{ $t("modelConfig.tts") }}</span>
          </el-menu-item>
          <el-menu-item index="memory">
            <span class="menu-text">{{ $t("modelConfig.memory") }}</span>
          </el-menu-item>
        </el-menu>

        <!-- Right content -->
        <div class="content-area">
          <el-card class="model-card" shadow="never">
            <el-table
              ref="modelTable"
              style="width: 100%"
              v-loading="loading"
              :element-loading-text="$t('modelConfig.loading')"
              element-loading-spinner="el-icon-loading"
              element-loading-background="rgba(255, 255, 255, 0.7)"
              :header-cell-style="{ background: 'transparent' }"
              :data="modelList"
              class="data-table"
              header-row-class-name="table-header"
              :header-cell-class-name="headerCellClassName"
              @selection-change="handleSelectionChange"
            >
              <el-table-column
                type="selection"
                width="55"
                align="center"
                :cell-class-name="selectionCellClassName"
              ></el-table-column>
              <el-table-column
                :label="$t('modelConfig.modelId')"
                prop="id"
                align="center"
              ></el-table-column>
              <el-table-column
                :label="$t('modelConfig.modelName')"
                prop="modelName"
                align="center"
              ></el-table-column>
              <el-table-column :label="$t('modelConfig.provider')" align="center">
                <template slot-scope="scope">
                  {{ scope.row.configJson.type || $t("modelConfig.unknown") }}
                </template>
              </el-table-column>
              <el-table-column :label="$t('modelConfig.isEnabled')" align="center">
                <template slot-scope="scope">
                  <el-switch
                    v-model="scope.row.isEnabled"
                    active-color="#5778ff"
                    inactive-color="#DCDFE6"
                    :active-value="1"
                    :inactive-value="0"
                    @change="handleStatusChange(scope.row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="$t('modelConfig.isDefault')" align="center">
                <template slot-scope="scope">
                  <el-switch
                    v-model="scope.row.isDefault"
                    active-color="#5778ff"
                    inactive-color="#DCDFE6"
                    :active-value="1"
                    :inactive-value="0"
                    @change="handleDefaultChange(scope.row)"
                  />
                </template>
              </el-table-column>
              <el-table-column
                v-if="activeTab === 'tts'"
                :label="$t('modelConfig.voiceManagement')"
                align="center"
              >
                <template slot-scope="scope">
                  <el-button
                    type="text"
                    size="mini"
                    @click="openTtsDialog(scope.row)"
                    class="voice-management-btn"
                  >
                    {{ $t("modelConfig.voiceManagement") }}
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column
                :label="$t('modelConfig.action')"
                align="center"
                width="210px"
              >
                <template slot-scope="scope">
                  <el-button
                    type="text"
                    size="mini"
                    @click="editModel(scope.row)"
                    class="edit-btn"
                  >
                    {{ $t("modelConfig.edit") }}
                  </el-button>
                  <el-button
                    type="text"
                    size="mini"
                    @click="duplicateModel(scope.row)"
                    class="edit-btn"
                  >
                    {{ $t("modelConfig.duplicate") }}
                  </el-button>
                  <el-button
                    type="text"
                    size="mini"
                    @click="deleteModel(scope.row)"
                    class="delete-btn"
                  >
                    {{ $t("modelConfig.delete") }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="table-footer">
              <div class="batch-actions">
                <CustomButton :icon="isAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'" type="default" size="small" @click="selectAll">
                  {{
                    isAllSelected
                      ? $t("modelConfig.deselectAll")
                      : $t("modelConfig.selectAll")
                  }}
                </CustomButton>
                <CustomButton icon="el-icon-plus" type="add" size="small" @click="addModel">
                  {{ $t("modelConfig.add") }}
                </CustomButton>
                <CustomButton
                  type="delete"
                  size="small"
                  icon="el-icon-delete"
                  @click="batchDelete"
                >
                  {{ $t("modelConfig.delete") }}
                </CustomButton>
              </div>
              <CustomPagination
                :total="total"
                :current-page="currentPage"
                :page-size="pageSize"
                :page-size-options="pageSizeOptions"
                @size-change="handlePageSizeChange"
                @page-change="handlePageChange"
              />
            </div>
          </el-card>
        </div>
      </div>

      <ModelEditDialog
        :modelType="activeTab"
        :visible.sync="editDialogVisible"
        :modelData="editModelData"
        @save="handleModelSave"
      />
      <TtsModel
        :visible.sync="ttsDialogVisible"
        :ttsModelId="selectedTtsModelId"
        :modelConfig="selectedModelConfig"
      />
      <AddModelDialog
        :modelType="activeTab"
        :visible.sync="addDialogVisible"
        @confirm="handleAddConfirm"
      />
    </div>
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import AddModelDialog from "@/components/AddModelDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import ModelEditDialog from "@/components/ModelEditDialog.vue";
import TtsModel from "@/components/TtsModel.vue";
import CustomPagination from "@/components/CustomPagination.vue";
import CustomButton from "@/components/CustomButton.vue";
import VersionFooter from "@/components/VersionFooter.vue";
export default {
  components: { HeaderBar, ModelEditDialog, TtsModel, AddModelDialog, VersionFooter, CustomPagination, CustomButton },
  data() {
    return {
      addDialogVisible: false,
      activeTab: "llm",
      search: "",
      editDialogVisible: false,
      editModelData: {},
      ttsDialogVisible: false,
      selectedTtsModelId: "",
      modelList: [],
      pageSizeOptions: [10, 20, 50, 100],
      currentPage: 1,
      pageSize: 10,
      total: 0,
      selectedModels: [],
      isAllSelected: false,
      loading: false,
      selectedModelConfig: {},
    };
  },

  created() {
    this.loadData();
  },

  mounted() {
    // Ensure table header translation text displays correctly after component mount
    setTimeout(() => {
      this.updateSelectionHeaderText();
    }, 100);
  },

  updated() {
    // Reset table header translation text after component update
    this.updateSelectionHeaderText();
  },

  computed: {
    modelTypeText() {
      return (
        this.$t("modelConfig." + this.activeTab) || this.$t("modelConfig.modelConfig")
      );
    },
  },

  methods: {
    // Update selection list header translation text
    updateSelectionHeaderText() {
      const thElement = document.querySelector(`.el-table__header th:nth-child(1) .cell`);
      if (thElement) {
        thElement.setAttribute("data-content", this.$t("modelConfig.select"));
      }
    },
    handlePageSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
      this.loadData();
    },
    openTtsDialog(row) {
      this.selectedTtsModelId = row.id;
      this.selectedModelConfig = row;
      this.ttsDialogVisible = true;
    },
    headerCellClassName({ column, columnIndex }) {
      if (columnIndex === 0) {
        return "custom-selection-header";
      }
      return "";
    },
    selectionCellClassName({ row, column, rowIndex, columnIndex }) {
      // Only set data-content for header rows
      if (rowIndex === undefined) {
        // Use setTimeout to ensure DOM has finished rendering
        setTimeout(() => {
          const thElement = document.querySelector(
            `.el-table__header th:nth-child(1) .cell`
          );
          if (thElement) {
            thElement.setAttribute("data-content", this.$t("modelConfig.select"));
          }
        }, 0);
      }
      return "";
    },
    handleMenuSelect(index) {
      this.activeTab = index;
      this.currentPage = 1; // Reset to first page
      this.pageSize = 10; // Optional: reset items per page
      this.loadData();
    },
    handleSearch() {
      this.currentPage = 1;
      this.loadData();
    },
    // Batch delete
    batchDelete() {
      if (this.selectedModels.length === 0) {
        this.$message.warning(this.$t("modelConfig.selectModelsFirst"));
        return;
      }

      this.$confirm(this.$t("modelConfig.confirmBatchDelete"), this.$t("message.info"), {
        confirmButtonText: this.$t("common.confirm"),
        cancelButtonText: this.$t("common.cancel"),
        type: "warning",
      })
        .then(() => {
          const deletePromises = this.selectedModels.map(
            (model) =>
              new Promise((resolve) => {
                Api.model.deleteModel(model.id, ({ data }) => resolve(data.code === 0));
              })
          );

          Promise.all(deletePromises).then((results) => {
            if (results.every(Boolean)) {
              this.$message.success({
                message: this.$t("modelConfig.batchDeleteSuccess"),
                showClose: true,
              });
              this.loadData();
            } else {
              this.$message.error({
                message: this.$t("modelConfig.partialDeleteFailed"),
                showClose: true,
              });
            }
          });
        })
        .catch(() => {
          this.$message.info(this.$t("modelConfig.deleteCancelled"));
        });
    },
    addModel() {
      this.addDialogVisible = true;
    },
    editModel(model) {
      this.editModelData = JSON.parse(JSON.stringify(model));
      this.editDialogVisible = true;
    },
    duplicateModel(model) {
      this.editModelData = JSON.parse(JSON.stringify(model));
      this.editModelData.duplicateMode = true;
      this.editDialogVisible = true;
    },
    // Delete single model
    deleteModel(model) {
      this.$confirm(this.$t("modelConfig.confirmDelete"), this.$t("message.info"), {
        confirmButtonText: this.$t("common.confirm"),
        cancelButtonText: this.$t("common.cancel"),
        type: "warning",
      })
        .then(() => {
          Api.model.deleteModel(model.id, ({ data }) => {
            if (data.code === 0) {
              this.$message.success({
                message: this.$t("modelConfig.deleteSuccess"),
                showClose: true,
              });
              this.loadData();
            } else {
              this.$message.error({
                message: data.msg || this.$t("modelConfig.deleteFailed"),
                showClose: true,
              });
            }
          });
        })
        .catch(() => {
          this.$message.info(this.$t("modelConfig.deleteCancelled"));
        });
    },
    handlePageChange(page) {
      this.currentPage = page;
      this.loadData();
    },
    handleModelSave({ provideCode, formData, done }) {
      const modelType = this.activeTab;
      const id = formData.id;

      if (this.editModelData.duplicateMode) {
        Api.model.addModel({ modelType, provideCode, formData }, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t("modelConfig.duplicateSuccess"));
            this.loadData();
            this.editDialogVisible = false;
          } else {
            this.$message.error(data.msg || this.$t("modelConfig.duplicateFailed"));
          }
          done && done(); // Call done callback to close loading state
        });
      } else {
        Api.model.updateModel({ modelType, provideCode, id, formData }, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t("modelConfig.saveSuccess"));
            this.loadData();
            this.editDialogVisible = false;
          } else {
            this.$message.error(data.msg || this.$t("modelConfig.saveFailed"));
          }
          done && done(); // Call done callback to close loading state
        });
      }
    },
    selectAll() {
      if (this.isAllSelected) {
        this.$refs.modelTable.clearSelection();
      } else {
        this.$refs.modelTable.toggleAllSelection();
      }
    },
    handleSelectionChange(val) {
      this.selectedModels = val;
      this.isAllSelected = val.length === this.modelList.length;
      if (val.length === 0) {
        this.isAllSelected = false;
      }
    },

    // Add new model configuration
    handleAddConfirm(newModel) {
      const params = {
        modelType: this.activeTab,
        provideCode: newModel.provideCode,
        formData: {
          ...newModel,
          isDefault: newModel.isDefault ? 1 : 0,
          isEnabled: newModel.isEnabled ? 1 : 0,
          configJson: newModel.configJson,
        },
      };

      Api.model.addModel(params, ({ data }) => {
        if (data.code === 0) {
          this.$message.success({
            message: this.$t("modelConfig.addSuccess"),
            showClose: true,
          });
          this.loadData();
        } else {
          this.$message.error({
            message: data.msg || this.$t("modelConfig.addFailed"),
            showClose: true,
          });
        }
      });
    },

    // Pagination
    goFirst() {
      this.currentPage = 1;
      this.loadData();
    },
    goPrev() {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.loadData();
      }
    },
    goNext() {
      if (this.currentPage < this.pageCount) {
        this.currentPage++;
        this.loadData();
      }
    },
    goToPage(page) {
      this.currentPage = page;
      this.loadData();
    },

    // Get model configuration list
    loadData() {
      this.loading = true; // Start loading
      const params = {
        modelType: this.activeTab,
        modelName: this.search,
        page: this.currentPage,
        limit: this.pageSize,
      };

      Api.model.getModelList(params, ({ data }) => {
        this.loading = false; // End loading
        if (data.code === 0) {
          this.modelList = data.data.list;
          this.total = data.data.total;
        } else {
          this.$message.error(data.msg || this.$t("modelConfig.fetchModelsFailed"));
        }
      });
    },
    // Handle enable/disable status change
    handleStatusChange(model) {
      const newStatus = model.isEnabled ? 1 : 0;
      const originalStatus = model.isEnabled;

      model.isEnabled = !model.isEnabled;

      Api.model.updateModelStatus(model.id, newStatus, ({ data }) => {
        if (data.code === 0) {
          this.$message.success(
            newStatus === 1
              ? this.$t("modelConfig.enableSuccess")
              : this.$t("modelConfig.disableSuccess")
          );
          // Keep new state
          model.isEnabled = newStatus;
          // Refresh table data
          this.loadData();
        } else {
          // Restore original state when operation fails
          model.isEnabled = originalStatus;
          this.$message.error(data.msg || this.$t("modelConfig.operationFailed"));
        }
      });
    },
    handleDefaultChange(model) {
      Api.model.setDefaultModel(model.id, ({ data }) => {
        if (data.code === 0) {
          this.$message.success(this.$t("modelConfig.setDefaultSuccess"));
          this.loadData();
        }
      });
    },
  },
};
</script>

<style scoped>
.el-switch {
  height: 23px;
}

::v-deep .el-table tr {
  background: transparent;
}

.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background-size: cover;
  background: #eff4ff;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.main-wrapper {
  margin: 5px 22px;
  border-radius: 15px;
  min-height: calc(100vh - 26vh);
  height: auto;
  max-height: 80vh;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
}

.page-title {
  font-size: 24px;
  margin: 0;
}

.content-panel {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.nav-panel {
  min-width: 242px;
  height: 100%;
  border-right: 1px solid #ebeef5;
  background: linear-gradient(
      120deg,
      rgba(107, 140, 255, 0.3) 0%,
      rgba(169, 102, 255, 0.3) 25%,
      transparent 60%
    ),
    url("../assets/model/model.png") no-repeat center / cover;
  padding: 16px 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.nav-panel .el-menu-item {
  height: 50px;
  background: #e9f0ff;
  line-height: 50px;
  border-radius: 4px 0 0 4px !important;
  transition: all 0.3s;
  display: flex !important;
  justify-content: flex-end;
  padding-right: 12px !important;
  width: fit-content;
  margin: 8px 0 8px auto;
  min-width: unset;
}

.nav-panel .el-menu-item.is-active {
  background: #5778ff;
  position: relative;
  padding-left: 40px !important;
}

.nav-panel .el-menu-item.is-active::before {
  content: "";
  position: absolute;
  left: 15px;
  top: 50%;
  transform: translateY(-50%);
  width: 13px;
  height: 13px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.5);
}

.menu-text {
  font-size: 14px;
  color: #606266;
  text-align: right;
  width: 100%;
  padding-right: 8px;
}

.content-area {
  flex: 1;
  padding: 24px;
  height: 100%;
  min-width: 600px;
  overflow: hidden;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-group {
  display: flex;
  gap: 10px;
}

.search-input {
  width: 240px;
}

.btn-search {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
}

.btn-search:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

::v-deep .search-input .el-input__inner {
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  background-color: white;
  transition: border-color 0.2s;
}

::v-deep .search-input .el-input__inner:focus {
  border-color: #6b8cff;
  outline: none;
}

.data-table {
  border-radius: 6px;
  overflow: hidden;
  background-color: transparent !important;
}

.data-table /deep/ .el-table__row {
  background-color: transparent !important;
}

.table-header th {
  background-color: transparent !important;
  color: #606266;
  font-weight: 600;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  width: 100%;
  flex-shrink: 0;
  min-height: 60px;
  background: white;
}

// .batch-actions {
//   display: flex;
//   gap: 8px;
// }

// .batch-actions .el-button {
//   min-width: 72px;
//   height: 32px;
//   padding: 7px 12px 7px 10px;
//   font-size: 12px;
//   border-radius: 4px;
//   line-height: 1;
//   font-weight: 500;
//   border: none;
//   transition: all 0.3s ease;
//   box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
// }

// .batch-actions .el-button:hover {
//   transform: translateY(-1px);
//   box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
// }

// .batch-actions .el-button--primary {
//   background: #5f70f3 !important;
//   color: white;
// }

// .batch-actions .el-button--success {
//   background: #5bc98c;
//   color: white;
// }

// .batch-actions .el-button--danger {
//   background: #fd5b63;
//   color: white;
// }

// .batch-actions .el-button:first-child {
//   background: linear-gradient(135deg, #409eff, #6b8cff);
//   border: none;
//   color: white;
// }

// .batch-actions .el-button:first-child:hover {
//   background: linear-gradient(135deg, #3a8ee6, #5a7cff);
// }

.el-table th /deep/ .el-table__cell {
  overflow: hidden;
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
  background-color: transparent !important;
}

::v-deep .el-table .custom-selection-header .cell .el-checkbox__inner {
  display: none !important;
}

::v-deep .el-table .custom-selection-header .cell::before {
  content: attr(data-content);
  display: block;
  text-align: center;
  line-height: 32px;
  /* Set appropriate line height to ensure text displays completely */
  color: black;
  margin-top: 0;
  /* Remove top margin that may cause offset */
  height: 32px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
}

.custom-selection-header .cell {
  position: relative;
}

/* Removed empty pseudo-elements that may affect text display */

::v-deep .el-table__body .el-checkbox__inner {
  display: inline-block !important;
  background: #ffffff;
}

::v-deep .el-table thead th:not(:first-child) .cell {
  color: #303133 !important;
}

::v-deep .nav-panel .el-menu-item.is-active .menu-text {
  color: #fff !important;
}

::v-deep .data-table {
  &.el-table::before,
  &.el-table::after,
  &.el-table__inner-wrapper::before {
    display: none !important;
  }
}

::v-deep .data-table .el-table__header-wrapper {
  border-bottom: 1px solid rgb(224, 227, 237);
}

::v-deep .data-table .el-table__body td {
  border-bottom: 1px solid rgb(224, 227, 237) !important;
}

.el-button img {
  height: 1em;
  vertical-align: middle;
  padding-right: 2px;
  padding-bottom: 2px;
}

::v-deep .el-checkbox__inner {
  border-color: #cfcfcf !important;
  transition: all 0.2s ease-in-out;
}

::v-deep .el-checkbox__input.is-checked .el-checkbox__inner {
  background-color: #5f70f3;
  border-color: #5f70f3;
}

.voice-management-btn {
  background: #9db3ea;
  color: white;
  min-width: 68px;
  line-height: 14px;
  white-space: nowrap;
  transition: all 0.3s;
  border-radius: 10px;
}

.voice-management-btn:hover {
  background: #8aa2e0;
  /* Darken color on hover */
  transform: scale(1.05);
}

::v-deep .el-table .el-table-column--selection .cell {
  padding-left: 15px !important;
}

::v-deep .el-table .el-table__fixed-right .cell {
  padding-right: 15px !important;
}

.edit-btn,
.delete-btn {
  margin: 0 8px;
  color: #7079aa !important;
}

::v-deep .el-table .cell {
  padding-left: 10px;
  padding-right: 10px;
}

/* Pagination */
.custom-pagination {
  display: flex;
  align-items: center;
  gap: 8px;

  /* Navigation button styles (first page, previous page, next page) */
  .pagination-btn:first-child,
  .pagination-btn:nth-child(2),
  .pagination-btn:nth-child(3),
  .pagination-btn:nth-last-child(2) {
    min-width: 60px;
    height: 32px;
    padding: 0 12px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    background: #dee7ff;
    color: #606266;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      background: #d7dce6;
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  /* Number button styles */
  .pagination-btn:not(:first-child):not(:nth-child(2)):not(:nth-child(3)):not(:nth-last-child(2)) {
    min-width: 28px;
    height: 32px;
    padding: 0;
    border-radius: 4px;
    border: 1px solid transparent;
    background: transparent;
    color: #606266;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(245, 247, 250, 0.3);
    }
  }

  .pagination-btn.active {
    background: #5f70f3 !important;
    color: #ffffff !important;
    border-color: #5f70f3 !important;

    &:hover {
      background: #6d7cf5 !important;
    }
  }

  .total-text {
    color: #909399;
    font-size: 14px;
    margin-left: 10px;
  }
}

.model-card {
  background: white;
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
  overflow: hidden;
}

.model-card ::v-deep .el-card__body {
  padding: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.data-table {
  --table-max-height: calc(100vh - 45vh);
  max-height: var(--table-max-height);
}

.data-table ::v-deep .el-table__body-wrapper {
  max-height: calc(var(--table-max-height) - 80px);
  overflow-y: auto;
}

::v-deep .el-loading-mask {
  background-color: rgba(255, 255, 255, 0.6) !important;
  backdrop-filter: blur(2px);
}

::v-deep .el-loading-spinner .circular {
  width: 28px;
  height: 28px;
}

::v-deep .el-loading-spinner .path {
  stroke: #6b8cff;
}

::v-deep .el-loading-text {
  color: #6b8cff !important;
  font-size: 14px;
  margin-top: 8px;
}
</style>
