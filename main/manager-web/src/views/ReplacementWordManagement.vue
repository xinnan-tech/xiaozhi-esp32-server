<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="params-card" shadow="never">
            <div class="operation-header">
              <h2 class="page-title">{{ $t('replacementWordManagement.pageTitle') }}</h2>
              <div class="right-operations">
                <el-input
                  :placeholder="$t('replacementWordManagement.searchPlaceholder')"
                  v-model="searchKeyword"
                  class="search-input"
                  @keyup.enter.native="handleSearch"
                  clearable
                />
                <CustomButton icon="el-icon-search" type="confirm" size="small" @click="handleSearch">
                  {{ $t('replacementWordManagement.search') }}
                </CustomButton>
              </div>
            </div>
            <CustomTable
              ref="paramsTable"
              :data="filteredParamsList"
              :columns="tableColumns"
              :loading="loading"
              :show-selection="true"
              :show-operations="true"
              :operations-label="$t('replacementWordManagement.operation')"
              :total="total"
              :current-page="currentPage"
              :page-size="pageSize"
              :page-size-options="pageSizeOptions"
              @size-change="handlePageSizeChange"
              @page-change="goToPage"
            >
              <template slot="content" slot-scope="scope">
                <el-tooltip placement="right" effect="light" popper-class="replace-word-tooltip">
                  <div slot="content" class="replace-word-content">
                    <el-tag
                      v-for="(item, index) in scope.row.content"
                      :key="index"
                      size="mini"
                      class="custom-tag"
                    >
                      {{ item }}
                    </el-tag>
                  </div>
                  <span class="content-text">{{ formatContent(scope.row.content) }}</span>
                </el-tooltip>
              </template>
              <template slot="operations" slot-scope="scope">
                <el-button size="mini" type="text" @click="handleEdit(scope.row)">
                  {{ $t('replacementWordManagement.edit') }}
                </el-button>
                <el-button size="mini" type="text" @click="handleDownload(scope.row)">
                  {{ $t('replacementWordManagement.download') }}
                </el-button>
                <el-button size="mini" type="text" @click="handleDelete(scope.row)">
                  {{ $t('replacementWordManagement.delete') }}
                </el-button>
              </template>
              <template slot="footer-btns">
                <div class="ctrl_btn">
                  <CustomButton
                    :icon="allSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'"
                    size="small"
                    @click="handleSelectAll"
                  >
                    {{ allSelected ? $t('user.deselectAll') : $t('user.selectAll') }}
                  </CustomButton>
                  <CustomButton type="add" icon="el-icon-plus" size="small" @click="handleAdd">
                    {{ $t('replacementWordManagement.addFile') }}
                  </CustomButton>
                  <CustomButton size="small" type="delete" icon="el-icon-delete" @click="handleBatchDelete">
                    {{ $t('replacementWordManagement.batchDelete') }}
                  </CustomButton>
                </div>
              </template>
            </CustomTable>
          </el-card>
        </div>
      </div>
    </div>

    <ReplacementWordDialog
      ref="paramDialog"
      :title="dialogTitle"
      :visible.sync="dialogVisible"
      :form="dialogForm"
      @submit="handleSubmit"
      @cancel="dialogVisible = false"
    />
    <el-footer><VersionFooter/></el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import ReplacementWordDialog from "@/components/ReplacementWordDialog.vue";
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";

export default {
  components: { HeaderBar, VersionFooter, ReplacementWordDialog, CustomButton, CustomTable },
  data() {
    return {
      searchKeyword: "",
      paramsList: [],
      selectedRows: new Set(),
      currentPage: 1,
      loading: false,
      pageSize: 10,
      pageSizeOptions: [10, 20, 50, 100],
      total: 0,
      dialogVisible: false,
      dialogTitle: '',
      dialogForm: {},
      tableColumns: []
    };
  },
  computed: {
    filteredParamsList() {
      if (!this.searchKeyword) {
        return this.paramsList;
      }
      const keyword = this.searchKeyword.toLowerCase();
      return this.paramsList.filter(row =>
        (row.fileName || '').toLowerCase().includes(keyword)
      );
    },

    hasAnySelected() {
      return this.selectedRows.size > 0;
    },

    allSelected() {
      if (this.filteredParamsList.length === 0) {
        return false;
      }
      return this.filteredParamsList.every(row => this.selectedRows.has(row.id));
    }
  },
  created() {
    this.initTableColumns();
    this.fetchFileList();
  },
  mounted() {
    this.dialogTitle = this.$t('replacementWordManagement.addFile');
  },
  methods: {
    initTableColumns() {
      this.tableColumns = [
        {
          prop: 'fileName',
          label: this.$t('replacementWordManagement.fileName'),
          align: 'center'
        },
        {
          prop: 'wordCount',
          label: this.$t('replacementWordManagement.replacementWordCount'),
          align: 'center'
        },
        {
          prop: 'content',
          label: this.$t('replacementWordManagement.replacementWordContent'),
          align: 'center',
          slot: 'content'
        },
        {
          prop: 'createdAt',
          label: this.$t('replacementWordManagement.createTime'),
          align: 'center'
        },
        {
          prop: 'updatedAt',
          label: this.$t('replacementWordManagement.updateTime'),
          align: 'center'
        }
      ];
    },

    formatContent(content) {
      if (!content) return '';
      if (Array.isArray(content)) {
        return content.join(',');
      }
      return content;
    },

    handleSearch() {
      this.currentPage = 1;
    },

    handlePageSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
      this.fetchFileList();
    },

    goToPage(page) {
      if (page !== this.currentPage) {
        this.currentPage = page;
        this.fetchFileList();
      }
    },

    handleCheckboxChange(row) {
      const newSet = new Set(this.selectedRows);
      if (row.selected) {
        newSet.add(row.id);
      } else {
        newSet.delete(row.id);
      }
      this.selectedRows = newSet;
    },

    handleSelectAll() {
      if (this.allSelected) {
        this.filteredParamsList.forEach(row => {
          this.$set(row, 'selected', false);
        });
        this.selectedRows = new Set();
      } else {
        this.filteredParamsList.forEach(row => {
          this.$set(row, 'selected', true);
        });
        this.selectedRows = new Set(this.filteredParamsList.map(row => row.id));
      }
    },

    handleBatchDelete() {
      const ids = Array.from(this.filteredParamsList)
        .filter(row => row.selected)
        .map(row => row.id);

      if (ids.length === 0) {
        return;
      }

      this.$confirm(
        this.$t('replacementWordManagement.confirmBatchDelete', { count: ids.length }),
        this.$t('replacementWordManagement.batchDeleteHint'),
        {
          confirmButtonText: this.$t('common.confirm'),
          cancelButtonText: this.$t('common.cancel')
        }
      ).then(() => {
        Api.correctWord.batchDeleteFile(ids, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t('common.deleteSuccess'));

            const newSet = new Set(this.selectedRows);
            ids.forEach(id => {
              newSet.delete(id);
            });
            this.selectedRows = newSet;

            this.fetchFileList();
          } else {
            this.$message.error(data.msg || this.$t('common.deleteFailure'));
          }
        });
      }).catch(() => {});
    },

    fetchFileList() {
      this.loading = true;
      Api.correctWord.getFileList({
        page: this.currentPage,
        pageSize: this.pageSize
      }, ({ data }) => {
        this.loading = false;
        if (data.code === 0) {
          this.paramsList = (data.data.list || []).map(row => ({
            ...row,
            selected: this.selectedRows.has(row.id)
          }));

          this.total = data.data.total || 0;
        } else {
          this.$message.error({
            message: data.msg || this.$t('replacementWordManagement.getListFailed'),
            showClose: true
          });
        }
      });
    },

    handleAdd() {
      this.dialogForm = {
        id: undefined,
        fileName: '',
        content: ''
      };
      this.dialogTitle = this.$t('replacementWordManagement.addFile');
      this.dialogVisible = true;
    },

    handleEdit(row) {
      this.dialogForm = {
        id: row.id,
        fileName: row.fileName,
        content: row.content || ''
      };
      this.dialogTitle = this.$t('replacementWordManagement.edit');
      this.dialogVisible = true;
    },

    handleDownload(row) {
      Api.correctWord.downloadFile(row.id, (res) => {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.download = `${row.fileName}.txt`;
        link.click();
        window.URL.revokeObjectURL(url);
      });
    },

    handleDelete(row) {
      this.$confirm(
        this.$t('replacementWordManagement.confirmDelete'),
        this.$t('replacementWordManagement.deleteHint'),
        {
          confirmButtonText: this.$t('common.confirm'),
          cancelButtonText: this.$t('common.cancel')
        }
      ).then(() => {
        Api.correctWord.deleteFile(row.id, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t('common.deleteSuccess'));
            const newSet = new Set(this.selectedRows);
            newSet.delete(row.id);
            this.selectedRows = newSet;
            this.fetchFileList();
          } else {
            this.$message.error(data.msg || this.$t('common.deleteFailure'));
          }
        });
      }).catch(() => {});
    },

    handleSubmit(formData) {
      if (formData.id) {
        Api.correctWord.updateFile(formData, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t('replacementWordManagement.saveSuccess'));
            this.dialogVisible = false;
            this.fetchFileList();
          } else {
            this.$message.error(data.msg || this.$t('replacementWordManagement.saveFailed'));
          }
          if (this.$refs.paramDialog) {
            this.$refs.paramDialog.resetSaving();
          }
        });
      } else {
        Api.correctWord.addFile(formData, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t('common.addSuccess'));
            this.dialogVisible = false;
            this.fetchFileList();
          } else {
            this.$message.error(data.msg || this.$t('replacementWordManagement.addFailed'));
          }
          if (this.$refs.paramDialog) {
            this.$refs.paramDialog.resetSaving();
          }
        });
      }
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

.params-card {
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

:deep(.el-table .cell) {
  .content-text {
    display: block;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.custom-tag {
  background: #e6ebff;
  color: #5778ff;
  border-radius: 8px;
  font-size: 12px;
  font-weight: normal;
  border: none;
}
</style>

<style>
.replace-word-tooltip {
  .popper__arrow {
    border-top-color: transparent !important;
    border-right-color: #e4e7ed !important;
  }
}
.replace-word-content {
  max-width: 400px;
  max-height: 60vh;
  overflow-y: auto;
  scrollbar-width: thin;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>