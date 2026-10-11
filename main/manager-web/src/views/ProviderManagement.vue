<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="provider-card" shadow="never">
            <el-table ref="providersTable" :data="filteredProvidersList" class="transparent-table" v-loading="loading"
              element-loading-text="Loading..." element-loading-spinner="el-icon-loading"
              element-loading-background="rgba(255, 255, 255, 0.7)" :header-cell-class-name="headerCellClassName">
              <el-table-column :label="$t('modelConfig.select')" align="center" width="120">
                <template slot-scope="scope">
                  <el-checkbox v-model="scope.row.selected"></el-checkbox>
                </template>
              </el-table-column>

              <el-table-column :label="$t('providerManagement.category')" prop="modelType" align="center" width="200">
                <template slot="header" slot-scope="scope">
                  <el-dropdown trigger="click" @command="handleSelectModelType"
                    @visible-change="isDropdownOpen = $event">
                    <span class="dropdown-trigger" :class="{ 'active': isDropdownOpen }">
                      {{ $t('providerManagement.category') }}{{ selectedModelTypeLabel }} <i class="dropdown-arrow"
                        :class="{ 'is-active': isDropdownOpen }"></i>
                    </span>
                    <el-dropdown-menu slot="dropdown">
                      <el-dropdown-item command="">{{ $t('common.all') }}</el-dropdown-item>
                      <el-dropdown-item v-for="item in translatedModelTypes" :key="item.value" :command="item.value">
                        {{ item.label }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </el-dropdown>
                <CustomButton icon="el-icon-search" type="confirm" @click="handleSearch">{{ $t('common.search') }}</CustomButton>
              </div>
            </div>
            <CustomTable
              ref="providersTable"
              :data="filteredProvidersList"
              :columns="tableColumns"
              :loading="loading"
              :show-selection="true"
              :show-operations="true"
              :operations-label="$t('common.action')"
              :total="total"
              :current-page="currentPage"
              :page-size="pageSize"
              :page-size-options="pageSizeOptions"
              @size-change="handlePageSizeChange"
              @page-change="goToPage"
            >
              <template slot="selection" slot-scope="scope">
                <el-checkbox v-model="scope.row.selected"></el-checkbox>
              </template>
              <template slot="modelType" slot-scope="scope">
                <el-tag :type="getModelTypeTag(scope.row.modelType)">
                  {{ getModelTypeLabel(scope.row.modelType) }}
                </el-tag>
              </template>
              <template slot="fields" slot-scope="scope">
                <el-popover placement="top-start" width="400" trigger="hover">
                  <div v-for="field in scope.row.fields" :key="field.key" class="field-item">
                    <span class="field-label">{{ field.label }}:</span>
                    <span class="field-type">{{ field.type }}</span>
                    <span v-if="isSensitiveField(field.key)" class="sensitive-tag">{{ $t('common.sensitive') }}</span>
                  </div>
                  <el-button slot="reference" size="mini" type="text">{{ $t('providerManagement.viewFields') }}</el-button>
                </el-popover>
              </template>
              <template slot="operations" slot-scope="scope">
                <el-button size="mini" type="text" @click="editProvider(scope.row)">{{ $t('common.edit') }}</el-button>
                <el-button size="mini" type="text" @click="deleteProvider(scope.row)">{{ $t('common.delete') }}</el-button>
              </template>
              <template slot="footer-btns">
                <div class="ctrl_btn">
                  <CustomButton :icon="isAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'" size="small" @click="handleSelectAll">
                    {{ isAllSelected ? $t('common.deselectAll') : $t('common.selectAll') }}
                  </CustomButton>
                  <CustomButton type="add" icon="el-icon-plus" size="small" @click="showAddDialog">
                    {{ $t('common.add') }}
                  </CustomButton>
                  <CustomButton size="small" type="delete" icon="el-icon-delete" @click="deleteSelectedProviders">
                    {{ $t('common.delete') }}
                  </CustomButton>
                </div>
              </template>
            </CustomTable>
          </el-card>
        </div>
      </div>
    </div>

    <!-- Add/Edit provider dialog -->
    <provider-dialog :title="dialogTitle" :visible.sync="dialogVisible" :form="providerForm" :model-types="modelTypes"
      @submit="handleSubmit" @cancel="dialogVisible = false" />

    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import ProviderDialog from "@/components/ProviderDialog.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";

export default {
  components: { HeaderBar, ProviderDialog, VersionFooter, CustomButton, CustomTable },
  data() {
    return {
      searchName: "",
      searchModelType: "",
      providersList: [],
      modelTypes: [
        { value: "ASR", labelKey: 'providerManagement.modelType.ASR' },
        { value: "TTS", labelKey: 'providerManagement.modelType.TTS' },
        { value: "LLM", labelKey: 'providerManagement.modelType.LLM' },
        { value: "VLLM", labelKey: 'providerManagement.modelType.VLLM' },
        { value: "Intent", labelKey: 'providerManagement.modelType.Intent' },
        { value: "Memory", labelKey: 'providerManagement.modelType.Memory' },
        { value: "VAD", labelKey: 'providerManagement.modelType.VAD' },
        { value: "Plugin", labelKey: 'providerManagement.modelType.Plugin' }
      ],
      currentPage: 1,
      loading: false,
      pageSize: 10,
      pageSizeOptions: [10, 20, 50, 100],
      total: 0,
      dialogVisible: false,
      dialogTitle: "Add Provider",
      isAllSelected: false,
      DropdownVisible: false,
      sensitive_keys: ["api_key", "personal_access_token", "access_token", "token", "secret", "access_key_secret", "secret_key"],
      providerForm: {
        id: null,
        modelType: "",
        providerCode: "",
        name: "",
        fields: [],
        sort: 0
      },
      tableColumns: []
    };
  },
  created() {
    this.initTableColumns();
    this.fetchProviders();
  },
  computed: {
    translatedModelTypes() {
      return this.modelTypes.map(type => ({
        value: type.value,
        label: this.$t(type.labelKey)
      }));
    },
    selectedModelTypeLabel() {
      if (!this.searchModelType) return `（${this.$t('providerManagement.all')}）`;
      const selectedType = this.modelTypes.find(item => item.value === this.searchModelType);
      return selectedType ? `（${this.$t(selectedType.labelKey)}）` : "";
    },
    filteredProvidersList() {
      return this.providersList;

      // let list = this.providersList.filter(item => {
      //   const nameMatch = item.name.toLowerCase().includes(this.searchName.toLowerCase());
      //   const typeMatch = !this.searchModelType || item.model_type === this.searchModelType;
      //   return nameMatch && typeMatch;
      // });

      // list.sort((a, b) => a.sort - b.sort);

      // // Pagination handling
      // const start = (this.currentPage - 1) * this.pageSize;
      // return list.slice(start, start + this.pageSize);
    }
  },
  methods: {
    initTableColumns() {
      this.tableColumns = [
        {
          prop: 'modelType',
          label: this.$t('providerManagement.category'),
          align: 'center',
          width: 200
        },
        {
          prop: 'providerCode',
          label: this.$t('providerManagement.providerCode'),
          align: 'center',
          width: 150
        },
        {
          prop: 'name',
          label: this.$t('common.name'),
          align: 'center'
        },
        {
          prop: 'fields',
          label: this.$t('providerManagement.fieldConfig'),
          align: 'center'
        },
        {
          prop: 'sort',
          label: this.$t('common.sort'),
          align: 'center',
          width: 80
        }
      ];
    },
    fetchProviders() {
      this.loading = true;

      Api.model.getModelProvidersPage(
        {
          page: this.currentPage,
          limit: this.pageSize,
          name: this.searchName,
          modelType: this.searchModelType
        },
        ({ data }) => {
          this.loading = false;
          if (data.code === 0) {
            this.providersList = data.data.list.map(item => {
              return {
                ...item,
                selected: false,
                fields: JSON.parse(item.fields)
              };
            });
            this.total = data.data.total;
          } else {
            this.$message.error({
              message: data.msg || 'Failed to get parameter list'
            });
          }
        }
      );
    },
    handleSearch() {
      this.currentPage = 1;
      this.fetchProviders();
    },
    handleSelectModelType(value) {
      this.searchModelType = value;
      this.handleSearch();
    },
    handleSelectAll() {
      this.isAllSelected = !this.isAllSelected;
      this.providersList.forEach(row => {
        row.selected = this.isAllSelected;
      });
    },
    showAddDialog() {
      this.dialogTitle = this.$t('common.addProvider');
      this.providerForm = {
        id: null,
        modelType: "",
        providerCode: "",
        name: "",
        fields: [],
        sort: 0
      };
      this.dialogVisible = true;
    },
    editProvider(row) {
      this.dialogTitle = this.$t('common.editProvider');
      this.providerForm = {
        ...row,
        fields: JSON.parse(JSON.stringify(row.fields))
      };
      this.dialogVisible = true;
    },
    handleSubmit({ form, done }) {
      if (form.id) {
        // Edit
        Api.model.updateModelProvider(form, ({ data }) => {
          if (data.code === 0) {
            this.fetchProviders(); // Refresh table
            this.$message.success({
              message: this.$t('common.updateSuccess'),
              showClose: true
            });
            this.dialogVisible = false;
          } else {
            this.$message.error({
              message: data.msg || this.$t('common.updateFailure'),
              showClose: true
            });
          }
          done && done();
        });
      } else {
        // Add
        Api.model.addModelProvider(form, ({ data }) => {
          if (data.code === 0) {
            this.fetchProviders(); // Refresh table
            this.$message.success({
              message: this.$t('common.addSuccess'),
              showClose: true
            });
            this.total += 1;
            this.dialogVisible = false;
          } else {
            this.$message.error({
              message: data.msg || this.$t('common.addFailure'),
              showClose: true
            });
          }
          done && done();
        });
      }
    },
    deleteSelectedProviders() {
      const selectedRows = this.providersList.filter(row => row.selected);
      if (selectedRows.length === 0) {
        this.$message.warning({
          message: this.$t('providerManagement.selectToDelete'),
          showClose: true
        });
        return;
      }
      this.deleteProvider(selectedRows);
    },
    deleteProvider(row) {
      const providers = Array.isArray(row) ? row : [row];
      const providerCount = providers.length;

      this.$confirm(this.$t('providerManagement.confirmDelete', { count: providerCount }), this.$t('common.warning'), {
        confirmButtonText: this.$t('common.confirm'),
        cancelButtonText: this.$t('common.cancel'),
        type: 'warning',
      }).then(() => {
        const ids = providers.map(provider => provider.id);
        Api.model.deleteModelProviderByIds(ids, ({ data }) => {
          if (data.code === 0) {
            this.isAllSelected = false;
            this.fetchProviders(); // Refresh table

            this.$message.success({
              message: this.$t('common.deleteSuccess'),
              showClose: true
            });
          } else {
            this.$message.error({
              message: data.msg || this.$t('common.deleteFailure'),
              showClose: true
            });
          }
        });
      }).catch(() => {
        this.$message({
          type: 'info',
          message: this.$t('common.deleteCancelled'),
          showClose: true,
          duration: 1000
        });
      });
    },
    getModelTypeTag(type) {
      const typeMap = {
        'ASR': 'success',
        'TTS': 'warning',
        'LLM': 'danger',
        'Intent': 'info',
        'Memory': '',
        'VAD': 'primary'
      };
      return typeMap[type] || '';
    },
    getModelTypeLabel(type) {
      const typeItem = this.modelTypes.find(item => item.value === type);
      return typeItem ? this.$t(typeItem.labelKey) : type;
    },
    isSensitiveField(fieldKey) {
      if (typeof fieldKey !== 'string') return false;
      return this.sensitive_keys.some(key =>
        fieldKey.toLowerCase().includes(key.toLowerCase())
      );
    },
    handlePageSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
      this.fetchProviders();
    },
    headerCellClassName({ columnIndex }) {
      if (columnIndex === 0) {
        return "custom-selection-header";
      }
      return "";
    },
    selectionCellClassName() {
      return "custom-selection-cell";
    },
    updateSelectionHeaderText() {
      // Ensure table is rendered
      this.$nextTick(() => {
        if (this.$refs.providersTable && this.$refs.providersTable.$el) {
          const headerCheckbox = this.$refs.providersTable.$el.querySelector('.custom-selection-header .el-checkbox .el-checkbox__label');
          if (headerCheckbox) {
            headerCheckbox.textContent = this.$t('modelConfig.select');
          }
        }
      });
    },
    mounted() {
      this.updateSelectionHeaderText();
    },
    updated() {
      this.updateSelectionHeaderText();
    },
    goFirst() {
      this.currentPage = 1;
      this.fetchProviders();
    },
    goPrev() {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetchProviders();
      }
    },
    goNext() {
      if (this.currentPage < this.pageCount) {
        console.log("this.currentPage", this.currentPage);
        this.currentPage++;
        this.fetchProviders();
      }
    },
    goToPage(page) {
      if (page !== this.currentPage) {
        this.currentPage = page;
        this.fetchProviders();
      }
    },
    handleDropdownVisibleChange(visible) {
      this.DropdownVisible = visible;
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
  background-size: cover;
  background: #eff4ff;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
}

.main-wrapper {
  margin: 5px 22px;
  border-radius: 15px;
  min-height: calc(100vh - 24vh);
  height: auto;
  max-height: 80vh;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
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
  align-items: center;
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

.provider-card {
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

.table_bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-bottom: 10px;
}

.ctrl_btn {
  display: flex;
  gap: 8px;
  padding-left: 26px;

  .el-button {
    min-width: 72px;
    height: 32px;
    padding: 7px 12px 7px 10px;
    font-size: 12px;
    border-radius: 4px;
    line-height: 1;
    font-weight: 500;
    border: none;
    transition: all 0.3s ease;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
  }

  .el-button--primary {
    background: #5f70f3;
    color: white;
  }

  .el-button--danger {
    background: #fd5b63;
    color: white;
  }
}

.custom-pagination {
  display: flex;
  align-items: center;
  gap: 10px;

  .el-select {
    margin-right: 8px;
  }

  .pagination-btn:first-child,
  .pagination-btn:nth-child(2),
  .pagination-btn:nth-last-child(2),
  .pagination-btn:nth-child(3) {
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

  .pagination-btn:not(:first-child):not(:nth-child(3)):not(:nth-child(2)):not(:nth-last-child(2)) {
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

:deep(.transparent-table) {
  background: white;
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;

  .el-table__body-wrapper {
    flex: 1;
    overflow-y: auto;
    max-height: none !important;
  }

  .el-table__header-wrapper {
    flex-shrink: 0;
  }

  .el-table__header th {
    background: white !important;
    color: black;
  }

  &::before {
    display: none;
  }

  .el-table__body tr {
    background-color: white;

    td {
      border-top: 1px solid rgba(0, 0, 0, 0.04);
      border-bottom: 1px solid rgba(0, 0, 0, 0.04);
    }
  }
}


:deep(.el-checkbox__inner) {
  background-color: #ffffff !important;
  border-color: #cccccc !important;
}

:deep(.el-checkbox__inner:hover) {
  border-color: #cccccc !important;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #5f70f3 !important;
  border-color: #5f70f3 !important;
}

@media (min-width: 1144px) {
  .table_bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 40px;
  }

  :deep(.transparent-table) {
    .el-table__body tr {
      td {
        padding-top: 16px;
        padding-bottom: 16px;
      }

      &+tr {
        margin-top: 10px;
      }
    }
  }
}

:deep(.el-table .el-button--text) {
  color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5;
}

.el-button--success {
  background: #5bc98c;
  color: white;
}

:deep(.el-table .cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-size-select {
  width: 100px;
  margin-right: 10px;

  :deep(.el-input__inner) {
    height: 32px;
    line-height: 32px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    background: #dee7ff;
    color: #606266;
    font-size: 14px;
  }

  :deep(.el-input__suffix) {
    right: 6px;
    width: 15px;
    height: 20px;
    display: flex;
    justify-content: center;
    align-items: center;
    top: 6px;
    border-radius: 4px;
  }

  :deep(.el-input__suffix-inner) {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
  }

  :deep(.el-icon-arrow-up:before) {
    content: "";
    display: inline-block;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 9px solid #606266;
    position: relative;
    transform: rotate(0deg);
    transition: transform 0.3s;
  }
}

:deep(.el-table) {
  .el-table__body-wrapper {
    transition: height 0.3s ease;
  }
}

.el-table {
  --table-max-height: calc(100vh - 40vh);
  max-height: var(--table-max-height);

  .el-table__body-wrapper {
    max-height: calc(var(--table-max-height) - 40px);
  }
}

:deep(.el-loading-mask) {
  background-color: rgba(255, 255, 255, 0.6) !important;
  backdrop-filter: blur(2px);
}

:deep(.el-loading-spinner .circular) {
  width: 28px;
  height: 28px;
}

:deep(.el-loading-spinner .path) {
  stroke: #6b8cff;
}

:deep(.el-loading-text) {
  color: #6b8cff !important;
  font-size: 14px;
  margin-top: 8px;
}

.field-item {
  padding: 5px 0;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;

  .field-label {
    flex: 1;
    font-weight: bold;
  }

  .field-type {
    width: 80px;
    color: #666;
  }

  .sensitive-tag {
    margin-left: 10px;
    color: #f56c6c;
    font-size: 12px;
  }
}

.rotate-down {
  transform: rotate(180deg);
  transition: transform 0.3s ease;
}

.el-icon-arrow-down {
  transition: transform 0.3s ease;
}

:deep(.el-table .el-button--text) {
  color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5;
}

/* Ensure selection column header style is correct */
.custom-selection-header {
  position: relative;
}

:deep(.custom-selection-header .el-checkbox) {
  display: flex !important;
  align-items: center;
  justify-content: center;
}

:deep(.custom-selection-header .el-checkbox__label) {
  position: relative;
  white-space: nowrap;
}

:deep(.custom-selection-cell) {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>