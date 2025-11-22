<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">{{ $t('knowledgeBaseManagement.title') }}</h2>
      <div class="right-operations">
        <el-input :placeholder="$t('knowledgeBaseManagement.searchPlaceholder')" v-model="searchName" class="search-input"
          @keyup.enter.native="handleSearch" clearable />
        <el-button class="btn-search" @click="handleSearch">{{ $t('knowledgeBaseManagement.search') }}</el-button>
      </div>
    </div>

    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="params-card" shadow="never">
            <div>
              <el-table ref="paramsTable" :data="knowledgeBaseList" class="transparent-table" v-loading="loading"
                :element-loading-text="$t('common.loading')" element-loading-spinner="el-icon-loading"
                element-loading-background="rgba(255, 255, 255, 0.7)"
                :header-cell-class-name="headerCellClassName" @selection-change="handleSelectionChange">
                <el-table-column type="selection" width="55" align="center" />
                <el-table-column :label="$t('knowledgeBaseManagement.name')" prop="name" align="center">
                  <template slot-scope="scope">
                    <span class="knowledge-base-name">{{ scope.row.name }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="$t('knowledgeBaseManagement.description')" prop="description" align="center" show-overflow-tooltip>
                  <template slot-scope="scope">
                    <span>{{ scope.row.description || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="$t('knowledgeBaseManagement.documentCount')" align="center">
                  <template slot-scope="scope">
                    <span>{{ scope.row.documentCount || 0 }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="$t('knowledgeBaseManagement.status')" align="center">
                  <template slot-scope="scope">
                    <el-switch
                      v-model="scope.row.status"
                      :active-value="1"
                      :inactive-value="0"
                      active-color="#13ce66"
                      inactive-color="#909399"
                      @change="handleStatusChange(scope.row)"
                    ></el-switch>
                  </template>
                </el-table-column>
                <el-table-column :label="$t('knowledgeBaseManagement.createdAt')" prop="createdAt" align="center">
                  <template slot-scope="scope">
                    <span>{{ formatDate(scope.row.createdAt) }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="$t('knowledgeBaseManagement.operation')" align="center">
                  <template slot-scope="scope">
                    <el-button size="mini" type="text" @click="showViewDialog(scope.row)">
                      {{ $t('knowledgeBaseManagement.view') }}
                    </el-button>
                    <el-button size="mini" type="text" @click="showEditDialog(scope.row)">
                      {{ $t('knowledgeBaseManagement.edit') }}
                    </el-button>
                    <el-button size="mini" type="text" @click="deleteSingleKnowledgeBase(scope.row)">
                      {{ $t('knowledgeBaseManagement.delete') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="table_bottom">
              <div class="ctrl_btn">
                <el-button size="mini" type="primary" @click="toggleSelectAll">
                  {{ isAllSelected ? $t('knowledgeBaseManagement.cancelSelectAll') : $t('knowledgeBaseManagement.selectAll') }}
                </el-button>
                <el-button size="mini" type="success" @click="showAddDialog">
                  {{ $t('knowledgeBaseManagement.add') }}
                </el-button>
                <el-button size="mini" type="danger" icon="el-icon-delete" @click="deleteSelectedKnowledgeBase" :disabled="selectedKnowledgeBase.length === 0">
                  {{ $t('knowledgeBaseManagement.delete') }}
                </el-button>
              </div>
              <div class="custom-pagination">
                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                  <el-option v-for="item in pageSizeOptions" :key="item"
                    :label="`${item}${$t('knowledgeBaseManagement.itemsPerPage')}`" :value="item">
                  </el-option>
                </el-select>
                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">
                  {{ $t('knowledgeBaseManagement.firstPage') }}
                </button>
                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">
                  {{ $t('knowledgeBaseManagement.prevPage') }}
                </button>
                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                  :class="{ active: page === currentPage }" @click="goToPage(page)">
                  {{ page }}
                </button>
                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">
                  {{ $t('knowledgeBaseManagement.nextPage') }}
                </button>
                <span class="total-text">{{ $t('knowledgeBaseManagement.totalRecords', { total }) }}</span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 新增/编辑知识库对话框 -->
    <knowledge-base-dialog ref="knowledgeBaseDialog" :title="dialogTitle" :visible.sync="dialogVisible" :form="knowledgeBaseForm"
      @submit="handleSubmit" @cancel="dialogVisible = false" />

    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import KnowledgeBaseDialog from "@/components/KnowledgeBaseDialog.vue";

export default {
  components: { HeaderBar, VersionFooter, KnowledgeBaseDialog },
  data() {
    return {
      searchName: "",
      knowledgeBaseList: [],
      currentPage: 1,
      loading: false,
      pageSize: 10,
      pageSizeOptions: [10, 20, 50, 100],
      total: 0,
      dialogVisible: false,
      dialogTitle: "",
      selectedKnowledgeBase: [],
      isAllSelected: false,
      knowledgeBaseForm: {
        id: null,
        datasetId: null,
        name: "",
        description: "",
        status: 1
      }
    };
  },
  created() {
    this.fetchKnowledgeBaseList();
  },
  computed: {
    pageCount() {
      return Math.ceil(this.total / this.pageSize);
    },
    visiblePages() {
      const pages = [];
      const maxVisible = 3;
      let start = Math.max(1, this.currentPage - 1);
      let end = Math.min(this.pageCount, start + maxVisible - 1);

      if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1);
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      return pages;
    },
  },
  methods: {
    handlePageSizeChange: function(val) {
      this.pageSize = val;
      this.currentPage = 1;
      this.fetchKnowledgeBaseList();
    },
    fetchKnowledgeBaseList: function() {
      this.loading = true;
      Api.knowledgeBase.getKnowledgeBaseList(
        {
          page: this.currentPage,
          page_size: this.pageSize,
          name: this.searchName,
        },
        (res) => {
          this.loading = false;
          console.log('getKnowledgeBaseList response:', res); // 添加调试日志
          
          // 修复：从 res.data 获取分页数据，而不是 res.data.data
          // 因为 knowledgeBase.js 直接传递了整个响应对象
          if (res.data && res.data.code === 0) {
            const pageData = res.data.data || {};
            this.knowledgeBaseList = pageData.list || [];
            this.total = pageData.total || 0;
            console.log('Updated knowledgeBaseList:', this.knowledgeBaseList); // 添加调试日志
          } else {
            this.$message.error({
              message: res.data?.msg || this.$t('knowledgeBaseManagement.getKnowledgeBaseListFailed'),
              showClose: true
            });
          }
        },
        () => {
          this.loading = false;
          this.$message.error(this.$t('knowledgeBaseManagement.getKnowledgeBaseListFailed'));
        }
      );
    },
    handleSearch: function() {
      this.currentPage = 1;
      this.fetchKnowledgeBaseList();
    },
    handleSelectionChange: function(val) {
      this.selectedKnowledgeBase = val;
    },
    toggleSelectAll: function() {
      if (this.isAllSelected) {
        // 取消全选
        this.$refs.paramsTable.clearSelection();
        this.isAllSelected = false;
      } else {
        // 全选
        this.knowledgeBaseList.forEach(row => {
          this.$refs.paramsTable.toggleRowSelection(row, true);
        });
        this.isAllSelected = true;
      }
    },
    headerCellClassName: function({ row, column, rowIndex, columnIndex }) {
      if (columnIndex === 0) {
        return 'header-cell-first';
      }
      return 'header-cell';
    },
    showAddDialog: function() {
      console.log('showAddDialog called');
      this.dialogTitle = this.$t('knowledgeBaseManagement.addKnowledgeBase');
      this.knowledgeBaseForm = {
        id: null,
        datasetId: null,
        name: "",
        description: "",
        status: 1
      };
      this.dialogVisible = true;
      console.log('dialogVisible set to:', this.dialogVisible);
    },
    showViewDialog: function(row) {
      // 跳转到上传文件页面，传递知识库ID和名称
      this.$router.push({
        path: '/knowledge-file-upload',
        query: {
          datasetId: row.datasetId,
          knowledgeBaseName: row.name
        }
      });
    },
    showEditDialog: function(row) {
      this.dialogTitle = this.$t('knowledgeBaseManagement.editKnowledgeBase');
      this.knowledgeBaseForm = {
        id: row.id,
        datasetId: row.datasetId,
        name: row.name,
        description: row.description || "",
        status: row.status,
        ragModelId: row.ragModelId || null
      };
      this.dialogVisible = true;
    },
    handleSubmit: function(form) {
      console.log('handleSubmit called with form:', form);
      if (form.id) {
        console.log('Editing knowledge base:', form.datasetId);
        Api.knowledgeBase.updateKnowledgeBase(form.datasetId, form, (res) => {
          console.log('Update response:', res);
          if (res.data && res.data.code === 0) {
            this.dialogVisible = false;
            this.fetchKnowledgeBaseList();
            this.$message.success(this.$t('knowledgeBaseManagement.updateSuccess'));
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.updateFailed'));
          }
        }, (err) => {
          console.log('Error callback received:', err);
          // 错误回调处理后端返回的错误信息
          if (err && err.data) {
            console.log('后端返回错误消息:', err.data.msg || err.msg);
            this.$message.error(err.data.msg || err.msg || this.$t('knowledgeBaseManagement.updateFailed'));
          } else {
            this.$message.error(this.$t('knowledgeBaseManagement.updateFailed'));
          }
        });
      } else {
        // 新增 - 只传递必要的字段，不传递id
        const createData = {
          name: form.name,
          description: form.description,
          status: form.status,
          ragModelId: form.ragModelId
        };
        console.log('Creating knowledge base with data:', createData);
        Api.knowledgeBase.createKnowledgeBase(createData, (res) => {
          console.log('Create response:', res);
          if (res.data && res.data.code === 0) {
            this.dialogVisible = false;
            this.fetchKnowledgeBaseList();
            this.$message.success(this.$t('knowledgeBaseManagement.addSuccess'));
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.addFailed'));
          }
        }, (err) => {
          console.log('Error callback received:', err);
          // 错误回调处理后端返回的错误信息
          if (err && err.data) {
            console.log('后端返回错误消息:', err.data.msg || err.msg);
            this.$message.error(err.data.msg || err.msg || this.$t('knowledgeBaseManagement.addFailed'));
          } else {
            this.$message.error(this.$t('knowledgeBaseManagement.addFailed'));
          }
        });
      }
    },
    deleteSelectedKnowledgeBase: function() {
      if (this.selectedKnowledgeBase.length === 0) {
        this.$message.warning(this.$t('knowledgeBaseManagement.selectKnowledgeBaseFirst'));
        return;
      }

      this.$confirm(
        this.$t('knowledgeBaseManagement.confirmBatchDelete', { count: this.selectedKnowledgeBase.length }),
        this.$t('common.warning'),
        {
          confirmButtonText: this.$t('common.confirm'),
          cancelButtonText: this.$t('common.cancel'),
          type: 'warning'
        }).then(() => {
        const ids = this.selectedKnowledgeBase.map(item => item.datasetId).join(',');
        Api.knowledgeBase.deleteKnowledgeBases(ids, (res) => {
          if (res.data && res.data.code === 0) {
            this.fetchKnowledgeBaseList();
            this.$message.success(this.$t('knowledgeBaseManagement.batchDeleteSuccess', { count: this.selectedKnowledgeBase.length }));
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.deleteFailed'));
          }
        }, (err) => {
          console.log('Error callback received:', err);
          // 错误回调处理后端返回的错误信息
          if (err && err.data) {
            console.log('后端返回错误消息:', err.data.msg || err.msg);
            this.$message.error(err.data.msg || err.msg || this.$t('knowledgeBaseManagement.deleteFailed'));
          } else {
            this.$message.error(this.$t('knowledgeBaseManagement.deleteFailed'));
          }
        });
      }).catch(() => {
        this.$message({
          type: 'info',
          message: this.$t('knowledgeBaseManagement.operationCancelled'),
          duration: 1000
        });
      });
    },
    deleteSingleKnowledgeBase: function(row) {
      this.$confirm(
        this.$t('knowledgeBaseManagement.confirmBatchDelete', { count: 1 }),
        this.$t('common.warning'),
        {
          confirmButtonText: this.$t('common.confirm'),
          cancelButtonText: this.$t('common.cancel'),
          type: 'warning'
        }).then(() => {
        Api.knowledgeBase.deleteKnowledgeBase(row.datasetId, (res) => {
          if (res.data && res.data.code === 0) {
            this.fetchKnowledgeBaseList();
            this.$message.success(this.$t('knowledgeBaseManagement.batchDeleteSuccess', { count: 1 }));
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.deleteFailed'));
          }
        }, (err) => {
          console.log('Error callback received:', err);
          // 错误回调处理后端返回的错误信息
          if (err && err.data) {
            console.log('后端返回错误消息:', err.data.msg || err.msg);
            this.$message.error(err.data.msg || err.msg || this.$t('knowledgeBaseManagement.deleteFailed'));
          } else {
            this.$message.error(this.$t('knowledgeBaseManagement.deleteFailed'));
          }
        });
      }).catch(() => {
        this.$message({
          type: 'info',
          message: this.$t('knowledgeBaseManagement.operationCancelled'),
          duration: 1000
        });
      });
    },
    handleStatusChange: function(row) {
      // 只传递需要更新的字段，确保包含id字段
      const updateForm = {
        id: row.id, // 添加id字段，后端需要此字段来定位记录
        datasetId: row.datasetId,
        name: row.name,
        description: row.description,
        status: row.status
      };
      console.log('Updating knowledge base status:', updateForm); // 添加调试日志
      Api.knowledgeBase.updateKnowledgeBase(row.datasetId, updateForm, (res) => {
        console.log('Status update response:', res); // 添加调试日志
        if (res.data && res.data.code !== 0) {
          // 恢复原来的状态
          this.fetchKnowledgeBaseList();
          this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.updateFailed'));
        } else {
          // 更新成功，显示成功消息
          this.$message.success(this.$t('knowledgeBaseManagement.updateSuccess'));
        }
      }, () => {
        // 恢复原来的状态
        this.fetchKnowledgeBaseList();
        this.$message.error(this.$t('knowledgeBaseManagement.updateFailed'));
      });
    },
    goToPage: function(page) {
      if (page !== this.currentPage) {
        this.currentPage = page;
        this.fetchKnowledgeBaseList();
      }
    },
    goFirst: function() {
      if (this.currentPage !== 1) {
        this.currentPage = 1;
        this.fetchKnowledgeBaseList();
      }
    },
    goPrev: function() {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetchKnowledgeBaseList();
      }
    },
    goNext: function() {
      if (this.currentPage < this.pageCount) {
        this.currentPage++;
        this.fetchKnowledgeBaseList();
      }
    },
    formatDate: function(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
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
    background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd) center;
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
    background: rgba(237, 242, 255, 0.5);
    display: flex;
    flex-direction: column;
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

.right-operations {
    display: flex;
    gap: 10px;
    margin-left: auto;
}

.search-input {
    width: 240px;
}

.btn-search {
    background: linear-gradient(135deg, #6b8cff, #a966ff);
    border: none;
    color: white;
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
        padding: 15px;
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
    margin-top: auto; 
    padding-bottom: 10px;
    width: 100%;
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
    gap: 5px;

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
}

.total-text {
    margin-left: 10px;
    color: #606266;
    font-size: 14px;
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
        font-weight: 600;
        height: 40px;
        padding: 8px 0;
        font-size: 14px;
        border-bottom: 1px solid #e4e7ed;
    }

    .el-table__body tr {
        background-color: white;

        td {
            border-top: 1px solid rgba(0, 0, 0, 0.04);
            border-bottom: 1px solid rgba(0, 0, 0, 0.04);
            padding: 8px 0;
            height: 40px;
            color: #606266;
            font-size: 14px;
        }
    }

    .el-table__row:hover>td {
        background-color: #f5f7fa !important;
    }

    &::before {
        display: none;
    }
}

:deep(.el-table .el-button--text) {
    color: #7079aa !important;
}

:deep(.el-table .el-button--text:hover) {
    color: #5a64b5 !important;
}

:deep(.el-checkbox__inner) {
    background-color: #eeeeee !important;
    border-color: #cccccc !important;
}

:deep(.el-checkbox__inner:hover) {
    border-color: #cccccc !important;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
    background-color: #5f70f3 !important;
    border-color: #5f70f3 !important;
}

:deep(.el-loading-mask) {
    background-color: rgba(255, 255, 255, 0.6) !important;
    backdrop-filter: blur(2px);
}

:deep(.el-loading-spinner .path) {
    stroke: #6b8cff;
}

:deep(.el-table__empty-block) {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 300px;
}

.el-table {
    --table-max-height: calc(100vh - 40vh);
    max-height: var(--table-max-height);
    flex: 1;

    .el-table__body-wrapper {
        max-height: calc(var(--table-max-height) - 40px);
    }
}

@media (min-width: 1144px) {
    .table_bottom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: auto;
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
</style>
