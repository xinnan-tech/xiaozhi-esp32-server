<template>
  <div class="welcome">
    <HeaderBar />
    <div class="model-tabs-container">
      <el-tabs v-model="activeTab" class="model-tabs" >
        <el-tab-pane label="语音活动检测模型(VAD)" name="vad"></el-tab-pane>
        <el-tab-pane label="语音识别(ASR)" name="asr"></el-tab-pane>
        <el-tab-pane label="大语言模型(LLM)" name="llm"></el-tab-pane>
        <el-tab-pane label="意图识别模型(Intent)" name="intent"></el-tab-pane>
        <el-tab-pane label="语音合成模型(TTS)" name="tts"></el-tab-pane>
        <el-tab-pane label="记忆模型(Memory)" name="memory"></el-tab-pane>
      </el-tabs>
      <div class="import-export-btn">
        <el-button v-if="activeTab === 'tts'" type="primary" @click="ttsDialogVisible = true" style="margin-right: 10px;">模型设置</el-button>
        <el-button size="small" @click="handleImportExport">导入导出配置</el-button>
      </div>
    </div>

    <el-main style="padding: 20px; display: flex; flex-direction: column;">

      <el-card class="model-card" shadow="always">
        <div class="model-search-operate" style="display: flex; align-items: center; margin-bottom: 20px;">
          <el-input placeholder="请输入模型名称查询" v-model="search" style="width: 300px; margin-right: 10px" />
          <el-button @click="handleSearch">查询</el-button>
          <el-button type="primary" @click="addModel">增加模型</el-button>
          <el-button type="danger" @click="batchDelete">批量删除</el-button>
        </div>

        <el-table :data="modelList" style="width: 100%;" border stripe>
          <el-table-column label="模型编码" prop="code"></el-table-column>
          <el-table-column label="模型名称" prop="candidateName"></el-table-column>
          <el-table-column label="是否应用">
            <template slot-scope="scope">
              <el-tag :type="scope.row.isApplied ? 'success' : 'danger'">
                {{ scope.row.isApplied ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="供应商名称" prop="supplier"></el-table-column>
          <el-table-column label="操作">
            <template slot-scope="scope">
              <el-button size="mini" @click="editModel(scope.row)" style="margin-right: 10px;">修改</el-button>
              <el-button size="mini" type="danger" @click="deleteModel(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <div class="pagination-container">
        <el-pagination
          @current-change="handleCurrentChange"
          :current-page="currentPage"
          :page-sizes="[5, 10, 15]"
          :page-size="pageSize"
          layout="prev, pager, next"
          :total="total"
        />
      </div>

      <div style="font-size: 12px; font-weight: 400; margin-top: auto; padding-top: 30px; color: #979db1;">
        ©2025 xiaozhi-esp32-server
      </div>
        <ModelEditDialog :visible.sync="editDialogVisible" :modelData="editModelData" @save="handleModelSave"/>
        <TtsModel :visible.sync="ttsDialogVisible" />
    </el-main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import ModelEditDialog from "@/components/ModelEditDialog.vue";
import TtsModel from "@/components/TtsModel.vue";

export default {
  components: { HeaderBar, ModelEditDialog, TtsModel },
  data() {
    return {
      activeTab: 'vad',
      search: '',
      editDialogVisible: false,
      editModelData: {},
      ttsDialogVisible: false,
      modelList: [
        { code: 'AILLM', candidateName: '阿里百炼', isApplied: true, supplier: 'openai' },
        { code: 'DoubaoLLM', candidateName: '豆包大模型', isApplied: true, supplier: 'openai' },
        { code: 'DeepSeekLLM', candidateName: '深度求索', isApplied: true, supplier: 'openai' },
        { code: 'DifyLLM', candidateName: 'DifChat', isApplied: true, supplier: 'dify' },
      ],
      currentPage: 1,
      pageSize: 4,
      total: 20
    };
  },
  methods: {
    // 查询
    handleSearch() {
      console.log('查询：', this.search);
    },
    // 批量删除
    batchDelete() {
      console.log('批量删除');
    },
    // 增加
    addModel() {
      console.log('增加模型');
    },
    // 修改
    editModel(model) {
      this.editModelData = {
        code: model.code,
        name: model.candidateName,
        supplier: model.supplier,
      };
      this.editDialogVisible = true;
    },
    // 删除
    deleteModel(model) {
      console.log('删除：', model);
    },
    handleCurrentChange(page) {
      this.currentPage = page;
      console.log('当前页码：', page);
    },
    // 导入导出
    handleImportExport() {
      console.log('导入导出');
    },
    handleModelSave(formData) {
      // 处理保存
      console.log('保存的模型数据：', formData);
    },
  }
};
</script>

<style scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-image: url("@/assets/home/background.png");
  background-size: cover;
  background-position: center;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.model-search-operate {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.model-search-operate > * {
  margin-right: 10px;
}

.el-table__header th {
  background-color: #f5f7fa;
  color: #606266;
}

.model-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.model-tabs-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 25px;
}

.model-tabs {
  flex-grow: 0;
  margin-right: 20px;
}

.import-export-btn {
  margin-right: 40px;
  margin-bottom: 20px;

}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

::v-deep .el-tabs {
  margin-left: 70px;
}
</style>
