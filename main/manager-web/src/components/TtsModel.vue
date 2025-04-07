<template>
  <el-dialog :visible.sync="localVisible" width="80%" @close="handleClose">
    <el-row class="main-container">
      <el-col :span="4">
        <el-menu class="model-menu" :default-active="activeModel" mode="vertical" @select="handleModelSelect">
          <el-menu-item index="EdgeTTS">EdgeTTS</el-menu-item>
          <el-menu-item index="DoubaoTTS">DoubaoTTS</el-menu-item>
          <el-menu-item index="TTS302AI">TTS302AI</el-menu-item>
          <el-menu-item index="CosyVoiceSiliconflow">CosyVoiceSiliconflow</el-menu-item>
        </el-menu>
      </el-col>

      <el-col :span="20">
        <div class="search-operate">
          <el-input placeholder="请输入音色名称查询" v-model="searchQuery" style="width: 300px; margin-right: 10px;"/>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button type="primary" plain @click="handleAddVoice">添加音色</el-button>
          <el-button type="danger" plain @click="handleBatchDelete">批量删除</el-button>
        </div>

        <el-table :data="filteredTtsModels" style="width: 100%" border stripe header-row-class-name="table-header">
          <el-table-column label="音色编码" prop="voiceCode" width="150" align="center"></el-table-column>
          <el-table-column label="音色名称" prop="voiceName" width="180" align="center"></el-table-column>
          <el-table-column label="语言类型" prop="languageType" width="120" align="center"></el-table-column>
          <el-table-column label="备注" prop="remark" align="center"></el-table-column>
          <el-table-column label="操作" width="200" align="center">
            <template slot-scope="scope">
              <el-button size="mini" type="text" @click="editVoice(scope.row)" style="color: #409EFF; margin-right: 15px;">修改</el-button>
              <el-button size="mini" type="text" @click="deleteVoice(scope.row)" style="color: #F56C6C;">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container">
          <el-pagination :current-page="currentPage" :page-size="pageSize" :total="total" layout="prev, pager, next" prev-text="<" next-text=">"/>
        </div>

        <div slot="footer" class="dialog-footer">
          <el-button @click="handleClose" size="medium">关闭</el-button>
          <el-button type="primary" @click="handleImportExport" size="medium">导入导出配置</el-button>
        </div>
        <EditVoiceDialog :showDialog="editDialogVisible" :voiceData="editVoiceData" @update:showDialog="editDialogVisible = $event" @saveVoice="handleSaveEditedVoice"/>
      </el-col>
    </el-row>
  </el-dialog>
</template>

<script>
import EditVoiceDialog from "@/components/EditVoiceDialog.vue";
export default {
  components: { EditVoiceDialog },
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      localVisible: this.visible,
      activeModel: 'EdgeTTS',
      searchQuery: '',
      editDialogVisible: false,
      editVoiceData: {},
      ttsModels: [
        { voiceCode: 'wawaxiaohe', voiceName: '湾湾小何', languageType: '中文', remark: '' },
        { voiceCode: 'wawaxiaohe', voiceName: '湾湾小何', languageType: '中文', remark: '' },
        { voiceCode: 'wawaxiaohe', voiceName: '湾湾小何', languageType: '中文', remark: '' },
        { voiceCode: 'wawaxiaohe', voiceName: '湾湾小何', languageType: '中文', remark: '' },
      ],
      currentPage: 1,
      pageSize: 4,
      total: 20
    };
  },
  watch: {
    visible(newVal) {
      this.localVisible = newVal;
    }
  },
  computed: {
    filteredTtsModels() {
      return this.ttsModels.filter(model =>
        model.voiceName.toLowerCase().includes(this.searchQuery.toLowerCase())
      );
    }
  },
  methods: {
    handleClose() {
      this.localVisible = false;
      this.$emit('update:visible', false);
    },
    handleModelSelect(index) {
      this.activeModel = index;
      // 可根据选中模型加载对应数据
    },
    handleSearch() {
      // 搜索
    },
    handleAddVoice() {
      // 添加音色
    },
    handleBatchDelete() {
      // 批量删除
    },
     editVoice(voice) {
      this.editVoiceData = { ...voice };
      this.editDialogVisible = true;
    },
    handleSaveEditedVoice(voiceForm) {
      const index = this.ttsModels.findIndex(item => item.voiceCode === voiceForm.voiceCode);
      if (index !== -1) {
        this.ttsModels.splice(index, 1, voiceForm);
      }
    },
    deleteVoice(voice) {
      // 删除
    },
    handleImportExport() {
      // 导入导出
    }
  }
};
</script>

<style scoped>
.main-container {
  padding: 20px;
}

.model-menu {
  border-right: 1px solid #ebeef5;
  height: calc(100vh - 300px);
  background-color: #fafafa;
}

.search-operate {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.pagination-container {
  margin: 20px 0;
  display: flex;
  justify-content: right;
}

.dialog-footer {
  text-align: right;
  padding: 20px 20px 0;
  border-top: 1px solid #ebeef5;
}

::v-deep .table-header th {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

::v-deep .el-table--striped .el-table__body tr.el-table__row--striped td {
  background-color: #fafafa;
}

::v-deep .el-table--border td, ::v-deep .el-table--border th {
  border-right: 1px solid #ebeef5;
}

::v-deep .el-pagination {
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

::v-deep .el-pagination .btn-prev, ::v-deep .el-pagination .btn-next {
  background-color: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

::v-deep .el-pagination .btn-prev:hover, ::v-deep .el-pagination .btn-next:hover {
  background-color: #f5f7fa;
}

::v-deep .el-pagination .el-pager li {
  background-color: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  margin: 0 2px;
}

::v-deep .el-pagination .el-pager li:hover {
  background-color: #f5f7fa;
}

::v-deep .el-pagination .el-pager li.active {
  background-color: #409EFF;
  color: #fff;
  border-color: #409EFF;
}
</style>
