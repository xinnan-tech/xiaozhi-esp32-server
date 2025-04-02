<template>
  <div class="welcome">
    <HeaderBar />

      <div class="operation-bar">
          <h2 class="page-title">模型配置</h2>
        <div class="right-operations">
          <el-button plain size="small" @click="handleImport" style="background: #7b9de5; color: white;">
            <img loading="lazy" alt="" src="@/assets/model/inner_conf.png">
            导入配置
          </el-button>
          <el-button plain size="small" @click="handleExport" style="background: #71c9d1; color: white;">
            <img loading="lazy" alt="" src="@/assets/model/output_conf.png">
            导出配置
          </el-button>
        </div>
      </div>

    <!-- 主体内容 -->
    <div class="main-wrapper">
      <div class="content-panel">
        <!-- 左侧导航 -->
        <el-menu :default-active="activeTab" class="nav-panel" @select="handleMenuSelect"
                 style="background-size: cover; background-position: center;">
          <el-menu-item index="vad">
            <span class="menu-text">语言活动检测</span>
          </el-menu-item>
          <el-menu-item index="asr">
            <span class="menu-text">语音识别</span>
          </el-menu-item>
          <el-menu-item index="llm">
            <span class="menu-text">大语言模型</span>
          </el-menu-item>
          <el-menu-item index="intent">
            <span class="menu-text">意图识别</span>
          </el-menu-item>
          <el-menu-item index="tts">
            <span class="menu-text">语音合成</span>
          </el-menu-item>
          <el-menu-item index="memory">
            <span class="menu-text">记忆</span>
          </el-menu-item>
        </el-menu>

        <!-- 右侧内容 -->
        <div class="content-area">
          <div class="title-bar">
            <div class="title-wrapper">
            <h2 class="model-title">大语言模型（LLM）</h2>
            <el-button type="primary" size="small" @click="addModel" class="add-btn">
               添加
            </el-button>
            </div>
            <div class="action-group">
              <div class="search-group">
                <el-input placeholder="请输入模型名称查询" v-model="search" size="small" class="search-input" clearable/>
                <el-button type="primary" size="small" class="search-btn" @click="handleSearch">
                  查询
                </el-button>
              </div>
            </div>
          </div>

          <el-table ref="modelTable" style="width: 100%" :header-cell-style="{background: 'transparent'}" :data="modelList"  class="data-table" header-row-class-name="table-header" :header-cell-class-name="headerCellClassName" @selection-change="handleSelectionChange">
            <el-table-column type="selection" width="55" align="center"></el-table-column>
            <el-table-column label="模型名称" prop="candidateName" align="center"></el-table-column>
            <el-table-column label="模型编码" prop="code" align="center"></el-table-column>
            <el-table-column label="提供商" prop="supplier" align="center"></el-table-column>
            <el-table-column label="是否启用" align="center">
              <template slot-scope="scope">
                <el-switch v-model="scope.row.isApplied" class="custom-switch" :active-color="null" :inactive-color="null"/>
              </template>
            </el-table-column>
            <el-table-column v-if="activeTab === 'tts'" label="音色管理" align="center">
              <template slot-scope="scope">
                <el-button type="text" size="mini" @click="ttsDialogVisible = true" class="voice-management-btn">
                  音色管理
                </el-button>
              </template>
            </el-table-column>
            <el-table-column label="操作" align="center" width="150px">
              <template slot-scope="scope">
                <el-button type="text" size="mini" @click="editModel(scope.row)" class="edit-btn">
                  修改
                </el-button>
                <el-button type="text" size="mini" @click="deleteModel(scope.row)" class="delete-btn">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="table-footer">
            <div class="batch-actions">
              <el-button size="mini" @click="selectAll" style="width: 75px; background: #606ff3">{{ isAllSelected ? '取消全选' : '全选' }}</el-button>
              <el-button size="mini" type="danger" icon="el-icon-delete" @click="batchDelete">
                删除
              </el-button>
            </div>
            <div class="custom-pagination">
              <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">首页</button>
              <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">上一页</button>

              <button v-for="page in visiblePages" :key="page" class="pagination-btn" :class="{ active: page === currentPage }" @click="goToPage(page)">
                {{ page }}
              </button>

              <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">下一页</button>
              <span class="total-text">共{{ total }}条记录</span>
            </div>
          </div>
        </div>
      </div>

      <ModelEditDialog :visible.sync="editDialogVisible" :modelData="editModelData" @save="handleModelSave"/>
      <TtsModel :visible.sync="ttsDialogVisible" />
      <AddModelDialog  :modelType="activeTab" :visible.sync="addDialogVisible" @confirm="handleAddConfirm"/>
    </div>

    <div class="copyright">
        ©2025 xiaozhi-esp32-server
      </div>
    </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import ModelEditDialog from "@/components/ModelEditDialog.vue";
import TtsModel from "@/components/TtsModel.vue";
import AddModelDialog from "@/components/AddModelDialog.vue";

export default {
  components: { HeaderBar, ModelEditDialog, TtsModel, AddModelDialog },
  data() {
    return {
      addDialogVisible: false,
      activeTab: 'llm',
      search: '',
      editDialogVisible: false,
      editModelData: {},
      ttsDialogVisible: false,
      modelList: [
        { code: 'DeepSeek', candidateName: '深度求索', isApplied: true, supplier: '硅基流动' },
        { code: 'SmartAssist', candidateName: '智能助手', isApplied: false, supplier: '智脑科技' },
        { code: 'CogEngine', candidateName: '认知引擎', isApplied: true, supplier: '云智科技' },
      ],
      currentPage: 1,
      pageSize: 4,
      total: 20,
      selectedModels: [],
      isAllSelected: false
    };
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
    }
  },

  methods: {
    headerCellClassName({ column, columnIndex }) {
      if (columnIndex === 0) {
        return 'custom-selection-header';
      }
      return '';
    },
    handleMenuSelect(index) {
      this.activeTab = index;
    },
    handleSearch() {
      console.log('查询：', this.search);
    },
    batchDelete() {
      if (this.selectedModels.length === 0) {
        this.$message.warning('请先选择要删除的模型');
        return;
      }
      this.$confirm('确定要删除选中的模型吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const selectedIds = this.selectedModels.map(model => model.code);
        this.modelList = this.modelList.filter(model => !selectedIds.includes(model.code));
        this.$message.success('删除成功');
        this.selectedModels = [];
        this.isAllSelected = false;
      }).catch(() => {
        this.$message.info('已取消删除');
        });
      },
    addModel() {
      this.addDialogVisible = true;
    },
    editModel(model) {
      this.editModelData = {
        code: model.code,
        name: model.candidateName,
        supplier: model.supplier,
      };
      this.editDialogVisible = true;
    },
    deleteModel(model) {
      this.$confirm(`确定要删除模型 ${model.candidateName} 吗?`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.modelList = this.modelList.filter(item => item.code !== model.code);
        this.$message.success('删除成功');
      }).catch(() => {
        this.$message.info('已取消删除');
      });
    },
    handleCurrentChange(page) {
      this.currentPage = page;
      this.$refs.modelTable.clearSelection();
      console.log('当前页码：', page);
    },
    handleImport() {
      console.log('导入配置');
    },
    handleExport() {
      console.log('导出配置');
    },
    handleModelSave(formData) {
      console.log('保存的模型数据：', formData);
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
    handleAddConfirm(newModel) {
      console.log('新增模型数据:', newModel);
    },

    // 分页器
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
    loadData() {
      console.log('加载数据，当前页:', this.currentPage);
    }
  },
};
</script>

<style scoped>
::v-deep .el-table tr{
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
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd) center;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.main-wrapper {
  margin: 5px 60px;
  border-radius: 15px;
  min-height: 600px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  background: rgba(237,242,255,0.5);
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #ebeef5;
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

.content-panel {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
}

.nav-panel {
  min-width: 242px;
  height: 100%;
  border-right: 1px solid #ebeef5;
  background:
    linear-gradient(
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
  line-height: 50px;
  border-radius: 4px;
  transition: all 0.3s;
  display: flex !important;
  justify-content: flex-end;
  padding-right: 12px !important;
  width: fit-content;
  margin: 8px 0px 8px auto;
  min-width: unset;
}

.nav-panel .el-menu-item.is-active {
  background: #e9f0ff;
  color: #0ba6f4 !important;
  position: relative;
  padding-left: 40px !important;
}

.nav-panel .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 50%;
  transform: translateY(-50%);
  width: 13px;
  height: 13px;
  background: #409EFF;
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
  overflow-x: auto;
  background-color: white;

}

.title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: nowrap;
}

.model-title {
  font-size: 18px;
  color: #303133;
  margin: 0;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-group {
  display: flex;
  gap: 8px;
}

.search-input {
  width: 240px;
}

::v-deep .search-input .el-input__inner::placeholder {
  color: black;
  opacity: 0.6;
}

::v-deep .search-input .el-input__inner {
  background: transparent;
}

.search-btn {
  background: linear-gradient(135deg, #6B8CFF, #A966FF);
  border: none;
  color: white;
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
  margin-top: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  width: 100%;
}

.batch-actions {
  display: flex;
  gap: 8px;
}

.copyright {
  text-align: center;
  color: #979db1;
  font-size: 12px;
  font-weight: 400;
  margin-top: auto;
  padding: 30px 0 20px;
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
}

.add-btn {
  background: #cce5f9;
  width: 75px;
  border: none;
  color: black;
  padding: 8px 16px;
}

.title-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-actions .el-button:first-child {
  background: linear-gradient(135deg, #409EFF, #6B8CFF);
  border: none;
  color: white;
}

.batch-actions .el-button:first-child:hover {
  background: linear-gradient(135deg, #3A8EE6, #5A7CFF);
}

.el-table th /deep/ .el-table__cell {
  overflow: hidden;
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
  background-color: transparent !important;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
}

::v-deep .el-table .custom-selection-header .cell .el-checkbox__inner {
  display: none !important; /* 使表头复选框不可见 */
}

::v-deep .el-table .custom-selection-header .cell::before {
  content: '选择';
  display: block;
  text-align: center;
  line-height: 0;
  color: black;
  margin-top: 23px;
}

::v-deep .el-table__body .el-checkbox__inner {
  display: inline-block !important;
  background: #e6edfa;
}

::v-deep .el-table thead th:not(:first-child) .cell {
  color: #303133 !important;
}

::v-deep .nav-panel .el-menu-item.is-active .menu-text {
  color: #409EFF !important;
}

::v-deep .data-table {
  &.el-table::before,
  &.el-table::after,
  &.el-table__inner-wrapper::before {
    display: none !important;
  }
}

::v-deep .data-table .el-table__header-wrapper {
  border-bottom: 1px solid rgb(224,227,237);
}

::v-deep .data-table .el-table__body td {
  border-bottom: 1px solid rgb(224,227,237) !important;
}

.el-button img{
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
  background-color: #409EFF !important;
  border-color: #409EFF !important;
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
    background: #8aa2e0; /* 悬停时颜色加深 */
  transform: scale(1.05);
}

::v-deep .el-table .el-table-column--selection .cell {
  padding-left: 15px !important;
}

::v-deep .el-table .el-table__fixed-right .cell {
  padding-right: 15px !important;
}

.edit-btn, .delete-btn {
  margin: 0 8px;
  color: #7079aa !important;
}

::v-deep .el-table .cell {
  padding-left: 10px;
  padding-right: 10px;
}

/* 分页器 */
.custom-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 15px;

  /* 导航按钮样式 (首页、上一页、下一页) */

  .pagination-btn:first-child,
  .pagination-btn:nth-child(2),
  .pagination-btn:nth-last-child(2) {
    min-width: 60px;
    height: 32px;
    padding: 0 12px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    background: #DEE7FF;
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

  /* 数字按钮样式 */

  .pagination-btn:not(:first-child):not(:nth-child(2)):not(:nth-last-child(2)) {
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

</style>

