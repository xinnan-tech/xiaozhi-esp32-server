<template>
  <div class="welcome">
    <HeaderBar />

      <div class="operation-bar">

        <div class="right-operations">
          <el-button v-if="activeTab === 'tts'" type="primary" plain size="small" @click="ttsDialogVisible = true">
            语音设置
          </el-button>
          <el-button type="primary" plain size="small" @click="handleImport">
            导入配置
          </el-button>
          <el-button type="success" plain size="small" @click="handleExport">
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

          <el-table :header-cell-style="{background: 'transparent'}" :data="modelList" border class="data-table" header-row-class-name="table-header" >
            <el-table-column type="selection" width="55" align="center"></el-table-column>
            <el-table-column label="模型名称" prop="candidateName" align="center"></el-table-column>
            <el-table-column label="模型编码" prop="code" align="center"></el-table-column>
            <el-table-column label="提供商" prop="supplier" align="center"></el-table-column>
            <el-table-column label="是否启用" align="center" width="120">
              <template slot-scope="scope">
                <el-switch v-model="scope.row.isApplied" class="custom-switch" :active-color="null" :inactive-color="null"/>
              </template>
            </el-table-column>
            <el-table-column label="操作" align="center" width="180">
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
              <el-button size="mini" @click="selectAll">全选</el-button>
              <el-button size="mini" type="danger" icon="el-icon-delete" @click="batchDelete">
                删除
              </el-button>
            </div>
            <div class="pagination-container">
            <el-pagination @current-change="handleCurrentChange" background :current-page="currentPage" :page-size="pageSize" layout="prev, pager, next" :total="total"/>
            </div>
          </div>
        </div>
      </div>

      <ModelEditDialog :visible.sync="editDialogVisible" :modelData="editModelData" @save="handleModelSave"/>
      <TtsModel :visible.sync="ttsDialogVisible" />
      <AddModelDialog :visible.sync="addDialogVisible" @confirm="handleAddConfirm"/>
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
      total: 20
    };
  },
  methods: {
    handleMenuSelect(index) {
      this.activeTab = index;
    },
    handleSearch() {
      console.log('查询：', this.search);
    },
    batchDelete() {
      console.log('批量删除');
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
      console.log('删除：', model);
    },
    handleCurrentChange(page) {
      this.currentPage = page;
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
      console.log('全选');
    },
    handleAddConfirm(newModel) {
      console.log('新增模型数据:', newModel);
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
  background-image: url("@/assets/home/background.png");
  border-radius: 15px;
  min-height: 600px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
}

.operation-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #ebeef5;
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
  width: 18%;
  min-width: 200px;
  height: 100%;
  border-right: 1px solid #ebeef5;
  background-size: cover;
  background: url("../assets/model/model.png") no-repeat center;
  padding: 16px 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.nav-panel .el-menu-item {
  height: 48px;
  line-height: 40px;
  border-radius: 4px;
  transition: all 0.3s;
  display: flex !important;
  justify-content: flex-end;
  padding-right: 12px !important;
  width: fit-content;
  margin: 8px 12px 8px auto;
  min-width: unset;
}

.nav-panel .el-menu-item.is-active {
  background: #ecf5ff;
  color: #409EFF;
  border-right: 3px solid #409EFF;
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

.edit-btn {
  color: #409EFF !important;
}

.delete-btn {
  color: #F56C6C !important;
}

.add-btn {
  background: #87CEFA;
  border: none;
  color: white;
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


</style>

