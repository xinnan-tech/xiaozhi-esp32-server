<template>
  <el-dialog
      :visible.sync="localVisible"
      width="85%"
      @close="handleClose"
      :show-close="false"
      :append-to-body="true"
      :close-on-click-modal="true">
    <button class="custom-close-btn" @click="handleClose">
      ×
    </button>
    <div class="scroll-wrapper">
      <div
          class="table-container"
          ref="tableContainer"
          @scroll="handleScroll">
          <el-table
              v-loading="loading"
              :data="filteredTtsModels"
              style="width: 100%;"
              class="data-table"
              header-row-class-name="table-header"
              :fit="true"
              element-loading-text="拼命加载中"
              element-loading-spinner="el-icon-loading"
              element-loading-background="rgba(0, 0, 0, 0.8)">
          <el-table-column label="选择" width="50" align="center">
            <template slot-scope="scope">
              <el-checkbox v-model="scope.row.selected"></el-checkbox>
            </template>
          </el-table-column>
          <el-table-column label="音色编码" align="center" min-width="50">
            <template slot-scope="scope">
              <el-input v-if="scope.row.editing" v-model="scope.row.voiceCode"></el-input>
              <span v-else>{{ scope.row.voiceCode }}</span>
            </template>
          </el-table-column>
          <el-table-column label="音色名称" align="center" min-width="50">
            <template slot-scope="scope">
              <el-input v-if="scope.row.editing" v-model="scope.row.voiceName"></el-input>
              <span v-else>{{ scope.row.voiceName }}</span>
            </template>
          </el-table-column>
          <el-table-column label="语言类型" align="center" min-width="50">
            <template slot-scope="scope">
              <el-input v-if="scope.row.editing" v-model="scope.row.languageType"></el-input>
              <span v-else>{{ scope.row.languageType }}</span>
            </template>
          </el-table-column>
          <el-table-column label="试听" align="center" min-width="100px" class-name="audio-column">
            <template slot-scope="scope">
              <div class="custom-audio-container">
                <el-input
                    v-if="scope.row.editing"
                    v-model="scope.row.voiceDemo"
                    placeholder="请输入MP3地址"
                    size="mini"
                    class="audio-input">
                </el-input>
                <AudioPlayer v-else-if="isValidAudioUrl(scope.row.voiceDemo)" :audioUrl="scope.row.voiceDemo"/>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="备注" align="center">
            <template slot-scope="scope">
              <el-input
                  v-if="scope.row.editing"
                  type="textarea"
                  :rows="1"
                  autosize
                  v-model="scope.row.remark"
                  placeholder="这里是备注"
                  class="remark-input"></el-input>
              <span v-else>{{ scope.row.remark }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" align="center" width="150">
            <template slot-scope="scope">
              <template v-if="!scope.row.editing">
                <el-button type="text" size="mini" @click="startEdit(scope.row)" class="edit-btn">
                  编辑
                </el-button>
                <el-button type="text" size="mini" @click="deleteRow(scope.row)" class="delete-btn">
                  删除
                </el-button>
              </template>
              <el-button
                  v-else
                  type="success"
                  size="mini"
                  @click="saveEdit(scope.row)"
                  class="save-Tts">保存
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 自定义滚动条 -->
      <div class="custom-scrollbar" ref="scrollbar">
        <div class="custom-scrollbar-track" ref="scrollbarTrack" @click="handleTrackClick">
          <div class="custom-scrollbar-thumb" ref="scrollbarThumb" @mousedown="startDrag"></div>
        </div>
      </div>
    </div>
    <div class="action-buttons">
      <el-button type="primary" size="mini" @click="toggleSelectAll" style="background: #606ff3;border: None">
        {{ selectAll ? '取消全选' : '全选' }}
      </el-button>
      <el-button type="primary" size="mini" @click="addNew" style="background: #5bc98c;border: None;">
        新增
      </el-button>
      <el-button type="primary"
                 size="mini"
                 @click="deleteRow(filteredTtsModels.filter(row => row.selected))"
                 style="background: red;border:None">删除
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
import AudioPlayer from './AudioPlayer.vue'
import Api from "@/apis/api";

export default {
  components: {AudioPlayer},
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    ttsModelId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      localVisible: this.visible,
      searchQuery: '',
      editDialogVisible: false,
      editVoiceData: {},
      ttsModels: [],
      currentPage: 1,
      pageSize: 10000,
      total: 0,
      isDragging: false,
      startY: 0,
      scrollTop: 0,
      selectAll: false,
      selectedRows: [],
      loading: false,
    };
  },
  watch: {
    visible(newVal) {
      this.localVisible = newVal;
      if (newVal) {
        this.currentPage = 1;
        this.loadData(); // 对话框显示时加载数据
        this.$nextTick(() => {
          this.updateScrollbar();
        });
      }
    },
    filteredTtsModels() {
      this.$nextTick(() => {
        this.updateScrollbar();
      });
    }
  },
  computed: {
    filteredTtsModels() {
      return this.ttsModels.filter(model =>
          model.voiceName.toLowerCase().includes(this.searchQuery.toLowerCase())
      );
    }
  },
  mounted() {
    this.updateScrollbar();
    window.addEventListener('resize', this.updateScrollbar);
    window.addEventListener('mouseup', this.stopDrag);
    window.addEventListener('mousemove', this.handleDrag);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateScrollbar);
    window.removeEventListener('mouseup', this.stopDrag);
    window.removeEventListener('mousemove', this.handleDrag);
  },
  methods: {
    loadData() {
      this.loading = true;
      const params = {
        ttsModelId: this.ttsModelId,
        page: this.currentPage,
        limit: this.pageSize,
        name: this.searchQuery
      };
      Api.timbre.getVoiceList(params, (data) => {
        if (data.code === 0) {
          this.ttsModels = data.data.list
            .map(item => ({
              id: item.id || '',
              voiceCode: item.ttsVoice || '',
              voiceName: item.name || '未命名音色',
              languageType: item.languages || '',
              remark: item.remark || '',
              voiceDemo: item.voiceDemo || '',
              selected: false,
              editing: false,
              sort: Number(item.sort)
            }))
            .sort((a, b) => a.sort - b.sort);
          this.total = data.total;
        } else {
          this.$message.error({
            message: data.msg || '获取音色列表失败',
            showClose: true
          });
        }
        this.loading = false;
      }, (err) => {
        console.error('加载失败:', err);
        this.$message.error({
          message: '加载音色数据失败',
          showClose: true
        });
        this.loading = false;
      });
    },

    handleClose() {
      // 重置状态
      this.ttsModels = [];
      this.currentPage = 1;
      this.total = 0;
      this.selectAll = false;
      this.searchQuery = '';

      this.localVisible = false;
      this.$emit('update:visible', false);
    },

    updateScrollbar() {
      const container = this.$refs.tableContainer;
      const scrollbarThumb = this.$refs.scrollbarThumb;
      const scrollbarTrack = this.$refs.scrollbarTrack;

      if (!container || !scrollbarThumb || !scrollbarTrack) return;

      const {scrollHeight, clientHeight} = container;
      const trackHeight = scrollbarTrack.clientHeight;
      const thumbHeight = Math.max((clientHeight / scrollHeight) * trackHeight, 20);

      scrollbarThumb.style.height = `${thumbHeight}px`;
      this.updateThumbPosition();
    },

    updateThumbPosition() {
      const container = this.$refs.tableContainer;
      const scrollbarThumb = this.$refs.scrollbarThumb;
      const scrollbarTrack = this.$refs.scrollbarTrack;

      if (!container || !scrollbarThumb || !scrollbarTrack) return;

      const {scrollHeight, clientHeight, scrollTop} = container;
      const trackHeight = scrollbarTrack.clientHeight;
      const thumbHeight = scrollbarThumb.clientHeight;
      const maxTop = trackHeight - thumbHeight;
      const thumbTop = (scrollTop / (scrollHeight - clientHeight)) * (trackHeight - thumbHeight);

      scrollbarThumb.style.top = `${Math.min(thumbTop, maxTop)}px`;
    },

    handleScroll() {
      const container = this.$refs.tableContainer;
      if (container.scrollTop + container.clientHeight >= container.scrollHeight - 50) {
        if (this.currentPage * this.pageSize < this.total) {
          this.currentPage++;
          this.loadData();
        }
      }
      this.updateThumbPosition();
    },

    startDrag(e) {
      this.isDragging = true;
      this.startY = e.clientY;
      this.scrollTop = this.$refs.tableContainer.scrollTop;
      e.preventDefault();
    },

    stopDrag() {
      this.isDragging = false;
    },

    handleDrag(e) {
      if (!this.isDragging) return;

      const container = this.$refs.tableContainer;
      const scrollbarTrack = this.$refs.scrollbarTrack;
      const scrollbarThumb = this.$refs.scrollbarThumb;
      const deltaY = e.clientY - this.startY;
      const trackHeight = scrollbarTrack.clientHeight;
      const thumbHeight = scrollbarThumb.clientHeight;
      const maxScrollTop = container.scrollHeight - container.clientHeight;

      const scrollRatio = (trackHeight - thumbHeight) / maxScrollTop;
      container.scrollTop = this.scrollTop + deltaY / scrollRatio;
    },

    handleTrackClick(e) {
      const container = this.$refs.tableContainer;
      const scrollbarTrack = this.$refs.scrollbarTrack;
      const scrollbarThumb = this.$refs.scrollbarThumb;

      if (!container || !scrollbarTrack || !scrollbarThumb) return;

      const trackRect = scrollbarTrack.getBoundingClientRect();
      const thumbHeight = scrollbarThumb.clientHeight;
      const clickPosition = e.clientY - trackRect.top;
      const thumbCenter = clickPosition - thumbHeight / 2;

      const trackHeight = scrollbarTrack.clientHeight;
      const maxTop = trackHeight - thumbHeight;
      const newTop = Math.max(0, Math.min(thumbCenter, maxTop));

      scrollbarThumb.style.top = `${newTop}px`;
      container.scrollTop = (newTop / (trackHeight - thumbHeight)) * (container.scrollHeight - container.clientHeight);
    },

    startEdit(row) {
      row.editing = true;
      this.$set(row, 'originalData', {...row});
    },

    saveEdit(row) {
      if (!row.voiceCode || !row.voiceName || !row.languageType) {
        this.$message.error({
          message: '音色编码、音色名称和语言类型不能为空',
          showClose: true
        });
        return;
      }

      try {
        const params = {
          id: row.id,
          voiceCode: row.voiceCode,
          voiceName: row.voiceName,
          languageType: row.languageType,
          remark: row.remark,
          ttsModelId: this.ttsModelId,
          voiceDemo: row.voiceDemo || '',
          sort: row.sort
        };

        let res;
        if (row.id) {
          // 已有ID，执行更新操作
          Api.timbre.updateVoice(params, (response) => {
            res = response;
            this.handleResponse(res, row);
          });
        } else {
          // 没有ID，执行新增操作
          Api.timbre.saveVoice(params, (response) => {
            res = response;
            this.handleResponse(res, row);
          });
        }
      } catch (error) {
        console.error('操作失败:', error);
        // 异常情况下也恢复原始数据
        if (row.originalData) {
          Object.assign(row, row.originalData);
          row.editing = false;
          delete row.originalData;
        }
        this.$message.error({
          message: '操作失败，请重试',
          showClose: true
        });
      }
    },

    handleResponse(res, row) {
      if (res.code === 0) {
        this.$message.success({
          message: row.id ? '修改成功' : '保存成功',
          showClose: true
        });
        row.editing = false;
        delete row.originalData;
        this.loadData(); // 刷新数据
      } else {
        // 保存失败时恢复原始数据
        if (row.originalData) {
          Object.assign(row, row.originalData);
          row.editing = false;
          delete row.originalData;
        }
        this.$message.error({
          message: res.msg || (row.id ? '修改失败' : '保存失败'),
          showClose: true
        });
      }
    },

    toggleSelectAll() {
      this.selectAll = !this.selectAll;
      this.filteredTtsModels.forEach(row => {
        row.selected = this.selectAll;
      });
    },

    addNew() {
      const hasEditing = this.ttsModels.some(row => row.editing);
      if (hasEditing) {
        this.$message.warning('请先完成当前编辑再新增');
        return;
      }

      const maxSort = this.ttsModels.length > 0
          ? Math.max(...this.ttsModels.map(item => Number(item.sort) || 0))
          : 0;

      const newRow = {
        voiceCode: '',
        voiceName: '',
        languageType: '中文',
        voiceDemo: '',
        remark: '',
        selected: false,
        editing: true,
        sort: maxSort + 1
      };

      this.ttsModels.unshift(newRow);
    },

    deleteRow(row) {
        // 处理单个音色或音色数组
        const voices = Array.isArray(row) ? row : [row];

        if (Array.isArray(row) && row.length === 0) {
            this.$message.warning("请先选择需要删除的音色");
            return;
        }


        const voiceCount = voices.length;
        this.$confirm(`确定要删除选中的${voiceCount}个音色吗？`, "警告", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
            distinguishCancelAndClose: true
        }).then(() => {
            const ids = voices.map(voice => voice.id);
            if (ids.some(id => !id)) {
                this.$message.error("存在无效的音色ID");
                return;
            }

        Api.timbre.deleteVoice(ids, ({data}) => {
            if (data.code === 0) {
                this.$message.success({
                    message: `成功删除${voiceCount}个参数`,
                    showClose: true
                });
                this.loadData(); // 刷新参数列表
            } else {
                this.$message.error({
                    message: data.msg || '删除失败，请重试',
                    showClose: true
                });
            }
        });
      }).catch(action => {
          if (action === 'cancel') {
              this.$message({
                  type: 'info',
                  message: '已取消删除操作',
                  duration: 1000
              });
          } else {
              this.$message({
                  type: 'info',
                  message: '操作已关闭',
                  duration: 1000
              });
          }
      });
    },

    isValidAudioUrl(url) {
      return url && (url.endsWith('.mp3') || url.endsWith('.ogg') || url.endsWith('.wav'));
    }
  }
};
</script>

<style lang="scss" scoped>

::v-deep .el-dialog {
  border-radius: 8px !important;
  overflow: hidden;
  top: 1vh !important;
}

::v-deep .el-dialog__header {
  display: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* 表格样式 */
::v-deep .data-table .el-table__header th {
  color: black;
  padding: 6px 0 !important;
}

::v-deep .data-table .el-table__row td {
  padding: 8px 0 12px !important;
}

::v-deep .data-table {
  border: none !important;
}

::v-deep .data-table.el-table::before {
  display: none !important;
}

::v-deep .data-table .el-table__header-wrapper {
  border-bottom: 2px solid #f1f2fb !important;
}

::v-deep .data-table .el-table__body-wrapper .el-table__body td {
  border: none !important;
}

/* 关闭按钮 */
.custom-close-btn {
  position: absolute;
  top: 15px;
  right: 15px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 30px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0;
  outline: none;
}

.custom-close-btn:hover {
  color: #409EFF;
  border-color: #409EFF;
}

/* 备注文本 */
::v-deep .remark-input .el-textarea__inner {
  border-radius: 4px;
  border: 1px solid #e6e6e6;
  padding: 8px 12px;
  resize: none;
  max-height: 40px !important;
  line-height: 1.5;
  background-color: transparent !important;
}

::v-deep .remark-input .el-textarea__inner:focus {
  border-color: #409EFF !important;
  outline: none;
}

::v-deep .remark-input .el-textarea__inner::placeholder {
  color: #c0c4cc !important;
  opacity: 1;
}


/* 滚动容器 */
.scroll-wrapper {
  display: flex;
  max-height: 55vh;
  position: relative;
}

.table-container {
  flex: 1;
  overflow: auto;
  scrollbar-width: none;
  padding-right: 15px;
  width: calc(100% - 16px);
}

.table-container::-webkit-scrollbar {
  display: none;
}

/* 自定义滚动条 */
.custom-scrollbar {
  width: 8px;
  background: #f1f1f1;
  border-radius: 4px;
  position: relative;
  margin-left: 8px;
  height: 100%;
  top: 55px;
}

.custom-scrollbar-track {
  position: relative;
  height: 380px;
  cursor: pointer;
}

.custom-scrollbar-thumb {
  position: absolute;
  width: 100%;
  background: #9dade7;
  border-radius: 4px;
  cursor: grab;
  transition: background 0.2s;
}

.custom-scrollbar-thumb:hover {
  background: #6b84d9;
}

.custom-scrollbar-thumb:active {
  cursor: grabbing;
}

.save-Tts {
  background: #796dea;
  border: None;
}

.save-Tts:hover {
  background: #8b80f0;
}

.custom-audio-container audio {
  display: none;
}

/* 音频播放器容器样式 */
.custom-audio-container {
  width: 90%;
  margin: 0 auto;
}

.action-buttons .el-button {
  padding: 8px 15px;
  font-size: 11px;
}

.edit-btn,
.delete-btn,
.save-btn {
  margin: 0 8px;
  color: #7079aa !important;
  transition: all 0.3s;
}

.edit-btn:hover,
.delete-btn:hover,
.save-btn:hover {
  color: #5f70f3 !important;
  transform: scale(1.05);
}

.save-btn {
  color: #5cca8e !important;
}

/* 表格单元格自适应 */
::v-deep .el-table__body-wrapper {
  overflow-x: hidden !important;
}

::v-deep .el-table td {
  white-space: pre-wrap !important;
  word-break: break-all !important;
}
/* 按钮组定位调整 */
.action-buttons {
  position: static;
  padding: 15px 0;
  background: white;
}

/* 输入框自适应 */
::v-deep .el-input__inner,
::v-deep .el-textarea__inner {
  width: 100% !important;
  min-width: 120px;
}

/* 音频输入框特殊处理 */
.audio-input ::v-deep .el-input__inner {
  min-width: 200px;
}

/* 操作按钮弹性布局 */
::v-deep .el-table__row .el-button {
  flex-shrink: 0;
  margin: 2px !important;
}

</style>