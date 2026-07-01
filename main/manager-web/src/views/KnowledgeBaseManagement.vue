<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area" v-loading="loading" :element-loading-text="$t('knowledgeBaseManagement.loading')">
          <!-- Knowledge Base Cards Section -->
          <div class="kb-section" :style="{ height: filteredKnowledgeBases.length > 0 ? 'fit-content' : '100%' }">
            <div class="kb-section-header">
              <h2 class="page-title">{{ $t('knowledgeBaseManagement.title') }}</h2>
              <div class="right-operations">
                <el-input
                  :placeholder="$t('knowledgeBaseManagement.searchPlaceholder')"
                  v-model="searchKbName"
                  class="search-input"
                  @keyup.enter.native="handleSearchKb"
                  clearable
                  prefix-icon="el-icon-search"
                />
                <CustomButton icon="el-icon-search" @click="handleSearchKb">
                  {{ $t('knowledgeBaseManagement.search') }}
                </CustomButton>
                <CustomButton type="confirm" icon="el-icon-plus" @click="showAddDialog">
                  {{ $t('knowledgeBaseManagement.addKnowledgeBase') }}
                </CustomButton>
              </div>
            </div>
            <div class="kb-cards-wrapper" :style="{ height: filteredKnowledgeBases.length > 0 ? 'fit-content' : '100%' }">
              <div class="kb-arrow left" @click="scrollCards(-1)" v-if="filteredKnowledgeBases.length > 0">
                <i class="el-icon-arrow-left"></i>
              </div>
              <div class="kb-cards" ref="kbCards">
                <div
                  v-for="(kb, index) in filteredKnowledgeBases"
                  :key="kb.datasetId"
                  class="kb-card"
                  :class="{ active: selectedKb && selectedKb.datasetId === kb.datasetId, error: !!kb.errorMessage }"
                  @click="selectKnowledgeBase(kb)"
                >
                  <div class="kb-card-actions-top">
                    <button class="kb-action-icon" :title="$t('knowledgeBaseManagement.edit')" @click.stop="editKnowledgeBase(kb)">
                      <i class="el-icon-edit"></i>
                    </button>
                    <button class="kb-action-icon delete" :title="$t('knowledgeBaseManagement.delete')" @click.stop="deleteKnowledgeBase(kb)">
                      <i class="el-icon-delete"></i>
                    </button>
                  </div>
                  <div class="kb-card-top">
                    <div class="kb-card-icon" :class="getCardColorClass(index)">
                      <ManualIcon :color="getIconColor(index)" />
                    </div>
                    <div class="kb-card-info">
                      <div class="kb-card-name">{{ kb.name }}</div>
                      <div class="kb-card-bottom">
                        <div class="kb-card-meta">
                          <span>{{`文档&nbsp;&nbsp;${kb.documentCount || 0}` }}</span>
                          <el-divider direction="vertical" />
                          <span>{{ formatDate(kb.createdAt) }}</span>
                          <el-divider direction="vertical" />
                          <el-switch
                            v-model="kb.status"
                            :active-value="1"
                            :inactive-value="0"
                            active-color="#5778ff"
                            inactive-color="#DCDFE6"
                            @click.native.stop
                            @change="handleStatusChange(kb)"
                          ></el-switch>
                          <el-tooltip v-if="kb.errorMessage" :content="kb.errorMessage" placement="top-end" effect="dark">
                            <i class="kb-card-warning el-icon-warning"></i>
                          </el-tooltip>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="kb-card-desc">{{ kb.description || '-' }}</div>
                </div>
                <div v-if="filteredKnowledgeBases.length === 0 && !loading" class="kb-empty">
                  <p>{{ $t('knowledgeBaseManagement.noData') }}</p>
                </div>
              </div>
              <div class="kb-arrow right" @click="scrollCards(1)" v-if="filteredKnowledgeBases.length > 0">
                <i class="el-icon-arrow-right"></i>
              </div>
            </div>
          </div>

          <!-- Document Section -->
          <KnowledgeBaseItem
            ref="knowledgeBaseItem"
            v-if="selectedKb"
            :kb="selectedKb"
            @upload="showUploadDialog"
            @retrieval-test="showRetrievalTestDialog"
            @view-slices="handleViewSlices"
            @refresh="refreshDocuments"
          />
        </div>
      </div>
    </div>

    <!-- Knowledge Base Dialog -->
    <KnowledgeBaseDialog
      ref="knowledgeBaseDialog"
      :title="dialogTitle"
      :visible.sync="dialogVisible"
      :form="knowledgeBaseForm"
      @submit="handleSubmit"
      @cancel="dialogVisible = false"
    />

    <!-- Slice Dialog -->
    <CustomDialog
      :title="`${$t('knowledgeFileUpload.viewSlices')} - ${currentDocumentName}`"
      :visible.sync="sliceDialogVisible"
      width="1200px"
      :footer="false"
    >
      <div class="slice-management">
        <div v-loading="sliceLoading" class="slice-content-container">
          <div v-if="sliceList.length > 0" class="slice-cards-container">
            <div v-for="(slice, index) in sliceList" :key="index" class="slice-card">
              <div class="slice-card-content">
                <span class="clice-index">{{ $t('knowledgeFileUpload.slice') }} {{ (sliceCurrentPage - 1) * slicePageSize + index + 1 }}</span>
                <div class="content-text">{{ slice.content }}</div>
              </div>
            </div>
          </div>
          <div v-else class="no-slice-data">
            <el-empty :description="$t('knowledgeFileUpload.noSliceData')"></el-empty>
          </div>
        </div>
        <div class="slice-pagination">
          <CustomPagination
            :total="parseInt(sliceTotal)"
            :current-page="sliceCurrentPage"
            :page-size="slicePageSize"
            :page-size-options="[10, 20, 50]"
            @size-change="handleSliceSizeChange"
            @page-change="handleSlicePageChange"
          />
        </div>
      </div>
    </CustomDialog>

    <!-- Upload Dialog -->
    <CustomDialog
      :title="$t('knowledgeFileUpload.uploadDocument')"
      :visible.sync="uploadDialogVisible"
      width="800px"
      @close="handleUploadDialogClose"
      @confirm="handleBatchUploadSubmit"
    >
      <el-upload
        ref="uploadRef"
        action="#"
        :auto-upload="false"
        :show-file-list="false"
        :on-change="handleFileChange"
        multiple
        accept=".doc,.docx,.pdf,.txt,.md,.mdx,.csv,.xls,.xlsx,.ppt,.pptx"
        drag
      >
        <i class="el-icon-upload"></i>
        <div class="el-upload__text">{{ $t('knowledgeFileUpload.dragOrClick') }}</div>
        <div class="el-upload__tip" slot="tip">{{ $t('knowledgeFileUpload.uploadTip') }}</div>
      </el-upload>
      <!-- 已选择文件列表 -->
      <div class="selected-files-section" v-if="selectedFilesList.length > 0">
        <h4>{{ $t('knowledgeFileUpload.selectedFiles') }} ({{ selectedFilesList.length }})</h4>
        <div class="selected-files-list">
          <div v-for="(file, index) in selectedFilesList" :key="index" class="selected-file-item">
            <div class="file-info">
              <i class="el-icon-document"></i>
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
            </div>
            <el-button type="text" class="remove-btn" @click="removeSelectedFile(index)">
              <i class="el-icon-close"></i>
            </el-button>
          </div>
        </div>
      </div>
    </CustomDialog>

    <!-- Retrieval Test Dialog -->
    <CustomDialog
      :title="$t('knowledgeFileUpload.retrievalTest')"
      :visible.sync="retrievalTestDialogVisible"
      width="900px"
      :close-on-click-modal="false"
      :confirm-text="$t('knowledgeFileUpload.executeTest')"
      :confirmLoading="retrievalTestLoading"
      @confirm="runRetrievalTest"
    >
      <div class="retrieval-test-form">
        <el-form :model="retrievalTestForm" label-width="100px">
          <el-form-item :label="$t('knowledgeFileUpload.testQuestion')" required>
            <el-input
              v-model="retrievalTestForm.question"
              @keyup.enter.native="runRetrievalTest"
              clearable
              :placeholder="$t('knowledgeFileUpload.testQuestionPlaceholder')"
            />
          </el-form-item>
        </el-form>
        <div v-if="retrievalTestResult" class="retrieval-test-result" style="margin-top: 20px;">
          <div class="result-chunks" v-if="retrievalTestResult.chunks.length">
            <div v-for="(chunk, index) in retrievalTestResult.chunks" :key="index" class="result-chunk">
              <div class="chunk-left">
                <div class="chunk-similarity">
                  <p class="similarity-label">{{ $t('knowledgeFileUpload.comprehensiveSimilarity') }}</p>
                  <p class="similarity-value">{{ (chunk.similarity || 0).toFixed(4) }}</p>
                  <el-progress
                    :percentage="Math.round((chunk.similarity || 0) * 100)"
                    :stroke-width="6"
                    :show-text="false"
                    class="similarity-progress"
                  />
                </div>
              </div>
              <el-divider direction="vertical"></el-divider>
              <div class="chunk-right">
                
                <div class="chunk-content">
                  <div class="chunk-right-header">
                    <span class="chunk-source">{{ $t('knowledgeFileUpload.sourceDocument') }}：{{ chunk.document_keyword || '-' }}</span>
                    <span class="chunk-index">{{ $t('knowledgeFileUpload.slice') }} {{ index + 1 }}</span>
                  </div>
                  <p>{{ chunk.content }}</p>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else :description="$t('knowledgeFileUpload.noSliceData')"></el-empty>
        </div>
      </div>
    </CustomDialog>

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
import KnowledgeBaseItem from "./KnowledgeBaseItem.vue";
import ManualIcon from "@/components/ManualIcon.vue";
import CustomDialog from "@/components/CustomDialog.vue";
import CustomPagination from "@/components/CustomPagination.vue";
import CustomButton from "@/components/CustomButton.vue";

export default {
  components: { HeaderBar, VersionFooter, KnowledgeBaseDialog, KnowledgeBaseItem, ManualIcon, CustomDialog, CustomPagination, CustomButton },
  data() {
    return {
      knowledgeBases: [],
      selectedKb: null,
      searchKbName: '',
      loading: false,
      dialogVisible: false,
      dialogTitle: '',
      knowledgeBaseForm: {
        id: null,
        datasetId: null,
        name: '',
        description: '',
        status: 1
      },
      uploadDialogVisible: false,
      sliceDialogVisible: false,
      retrievalTestDialogVisible: false,
      retrievalTestForm: {
        question: ''
      },
      retrievalTestResult: null,
      retrievalTestLoading: false,
      selectedFilesList: [],
      uploading: false,
      currentDocumentId: '',
      currentDocumentName: '',
      sliceList: [],
      sliceLoading: false,
      sliceCurrentPage: 1,
      slicePageSize: 10,
      sliceTotal: 0,
    };
  },
  computed: {
    filteredKnowledgeBases() {
      return this.knowledgeBases;
    },
  },
  created() {
    this.fetchKnowledgeBases();
  },
  methods: {
    fetchKnowledgeBases() {
      this.loading = true;
      Api.knowledgeBase.getKnowledgeBaseList(
        { page: 1, page_size: 100, name: this.searchKbName },
        (res) => {
          this.loading = false;
          if (res.data && res.data.code === 0) {
            const pageData = res.data.data || {};
            this.knowledgeBases = pageData.list || [];
            if (this.knowledgeBases.length > 0 && !this.selectedKb) {
              this.selectKnowledgeBase(this.knowledgeBases[0]);
            } else if (this.selectedKb) {
              const updated = this.knowledgeBases.find(kb => kb.datasetId === this.selectedKb.datasetId);
              if (updated) this.selectedKb = updated;
            }
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.getListFailed'));
          }
        },
        () => {
          this.loading = false;
          this.$message.error(this.$t('knowledgeBaseManagement.getListFailed'));
        }
      );
    },

    selectKnowledgeBase(kb) {
      this.selectedKb = kb;
    },

    refreshDocuments() {
      this.$refs.knowledgeBaseItem?.fetchDocuments();
    },

    handleSearchKb() {
      this.fetchKnowledgeBases();
    },

    scrollCards(direction) {
      const container = this.$refs.kbCards;
      if (container) {
        container.scrollBy({ left: direction * 364, behavior: 'smooth' });
      }
    },

    showAddDialog() {
      this.dialogTitle = this.$t('knowledgeBaseManagement.addKnowledgeBase');
      this.knowledgeBaseForm = {
        id: null,
        datasetId: null,
        name: '',
        description: '',
        status: 1
      };
      this.dialogVisible = true;
    },

    editKnowledgeBase(kb) {
      this.dialogTitle = this.$t('knowledgeBaseManagement.editKnowledgeBase');
      this.knowledgeBaseForm = {
        id: kb.id,
        datasetId: kb.datasetId,
        name: kb.name,
        description: kb.description || '',
        status: kb.status,
        ragModelId: kb.ragModelId
      };
      this.dialogVisible = true;
    },

    handleStatusChange(kb) {
      const updateForm = {
        id: kb.id,
        datasetId: kb.datasetId,
        name: kb.name,
        description: kb.description,
        status: kb.status
      };
      Api.knowledgeBase.updateKnowledgeBase(kb.datasetId, updateForm, (res) => {
        if (res.data && res.data.code !== 0) {
          this.fetchKnowledgeBases();
          this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.updateFailed'));
        } else {
          this.$message.success(kb.status === 1 ? this.$t('knowledgeBaseManagement.enabled') : this.$t('knowledgeBaseManagement.disabled'));
          if (this.selectedKb && this.selectedKb.datasetId === kb.datasetId) {
            this.selectedKb = { ...kb };
          }
        }
      }, () => {
        this.fetchKnowledgeBases();
        this.$message.error(this.$t('knowledgeBaseManagement.updateFailed'));
      });
    },

    deleteKnowledgeBase(kb) {
      this.$confirm(
        this.$t("knowledgeBaseManagement.confirmBatchDelete", {count: 1}),
        this.$t('message.warning'),
        {
          confirmButtonText: this.$t('knowledgeBaseDialog.confirm'),
          cancelButtonText: this.$t('knowledgeBaseDialog.cancel'),
          type: 'warning'
        }
      ).then(() => {
        Api.knowledgeBase.deleteKnowledgeBase(kb.datasetId, (res) => {
          if (res.data && res.data.code === 0) {
            this.$message.success(this.$t('knowledgeBaseManagement.batchDeleteSuccess', { count: 1 }));
            if (this.selectedKb && this.selectedKb.datasetId === kb.datasetId) {
              this.selectedKb = null;
            }
            this.fetchKnowledgeBases();
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.deleteFailed'));
          }
        }, (err) => {
          this.$message.error(err?.data?.msg || this.$t('knowledgeBaseManagement.deleteFailed'));
        });
      }).catch(() => {});
    },

    showUploadDialog() {
      this.uploadDialogVisible = true;
    },

    handleSubmit(form) {
      if (form.id) {
        Api.knowledgeBase.updateKnowledgeBase(form.datasetId, form, (res) => {
          if (res.data && res.data.code === 0) {
            this.dialogVisible = false;
            this.fetchKnowledgeBases();
            this.$message.success(this.$t('knowledgeBaseManagement.updateSuccess'));
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.updateFailed'));
          }
        }, (err) => {
          this.$message.error(err?.data?.msg || this.$t('knowledgeBaseManagement.updateFailed'));
        });
      } else {
        const createData = {
          name: form.name,
          description: form.description,
          status: form.status,
          ragModelId: form.ragModelId
        };
        Api.knowledgeBase.createKnowledgeBase(createData, (res) => {
          if (res.data && res.data.code === 0) {
            this.dialogVisible = false;
            this.fetchKnowledgeBases();
            this.$message.success(this.$t('knowledgeBaseManagement.addSuccess'));
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeBaseManagement.addFailed'));
          }
        }, (err) => {
          this.$message.error(err?.data?.msg || this.$t('knowledgeBaseManagement.addFailed'));
        });
      }
    },

    handleUploadDialogClose() {
      if (this.$refs.uploadRef) {
        this.$refs.uploadRef.clearFiles();
      }
      this.selectedFilesList = [];
    },

    handleFileChange(file) {
      if (!file || !file.raw) return;
       // 文件上传前的验证
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        this.$message.error(this.$t('knowledgeFileUpload.fileSizeExceeded'));
        return;
      }
      this.selectedFilesList.push({
        name: file.name,
        size: file.size,
        raw: file.raw
      });
    },

    removeSelectedFile(index) {
      this.selectedFilesList.splice(index, 1);
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    handleBatchUploadSubmit() {
      if (this.selectedFilesList.length === 0) {
        this.$message.error(this.$t('knowledgeFileUpload.fileRequired'));
        return;
      }

      this.uploading = true;

      const uploadPromises = this.selectedFilesList.map(file => {
        return new Promise((resolve, reject) => {
          const formData = new FormData();
          formData.append('file', file.raw);

          Api.knowledgeBase.uploadDocument(this.selectedKb.datasetId, formData,
            ({ data }) => {
              if (data && data.code === 0) {
                resolve({ success: true, fileName: file.name });
              } else {
                reject({ success: false, fileName: file.name, error: data?.msg || this.$t('knowledgeFileUpload.uploadFailed') });
              }
            },
            (err) => {
              if (err && err.data) {
                reject({ success: false, fileName: file.name, error: err.data.msg || err.msg || this.$t('knowledgeFileUpload.uploadFailed') });
              } else {
                reject({ success: false, fileName: file.name, error: this.$t('knowledgeFileUpload.uploadFailed') });
              }
              console.error('上传文档失败:', err);
            }
          );
        });
      });

      Promise.all(uploadPromises.map(p => p.catch(e => e)))
        .then(results => {
          this.uploading = false;

          const successCount = results.filter(r => r.success).length;
          const failedCount = results.filter(r => !r.success).length;

          if (successCount > 0) {
            this.$message.success(this.$t('knowledgeFileUpload.uploadSuccess'));
          }

          if (failedCount > 0) {
            this.$message.error(this.$t('knowledgeFileUpload.uploadFailed'));
          }

          if (successCount > 0) {
            this.uploadDialogVisible = false;
            this.refreshDocuments();
          }
        })
        .catch(error => {
          this.uploading = false;
          this.$message.error(this.$t('knowledgeFileUpload.uploadFailed'));
          console.error(error);
        });
    },

    showRetrievalTestDialog() {
      this.retrievalTestForm.question = '';
      this.retrievalTestResult = null;
      this.retrievalTestDialogVisible = true;
    },

    runRetrievalTest() {
      if (this.retrievalTestLoading) return;
      if (!this.retrievalTestForm.question.trim()) {
        this.$message.error(this.$t('knowledgeFileUpload.testQuestionRequired'));
        return;
      }
      this.retrievalTestLoading = true;
      Api.knowledgeBase.retrievalTest(
        this.selectedKb.datasetId,
        { question: this.retrievalTestForm.question.trim() },
        ({ data }) => {
          this.retrievalTestLoading = false;
          if (data && data.code === 0) {
            this.retrievalTestResult = data.data || data;
          } else {
            this.$message.error(data?.msg || '召回测试失败');
          }
        },
        (err) => {
          this.retrievalTestLoading = false;
          this.$message.error(err?.data?.msg || '召回测试失败');
        }
      );
    },

    handleViewSlices(doc) {
      this.currentDocumentId = doc.id;
      this.currentDocumentName = doc.name;
      this.sliceDialogVisible = true;
      this.sliceCurrentPage = 1;
      this.fetchSlices();
    },

    fetchSlices() {
      if (!this.selectedKb || !this.currentDocumentId) return;
      this.sliceLoading = true;
      const params = {
        page: this.sliceCurrentPage,
        page_size: this.slicePageSize
      };
      Api.knowledgeBase.listChunks(
        this.selectedKb.datasetId,
        this.currentDocumentId,
        params,
        ({ data }) => {
          this.sliceLoading = false;
          if (data && data.code === 0) {
            const responseData = data.data;
            if (responseData && responseData.list) {
              this.sliceList = responseData.list;
              this.sliceTotal = responseData.total || responseData.list.length;
            } else if (responseData && responseData.chunks && Array.isArray(responseData.chunks)) {
              this.sliceList = responseData.chunks;
              this.sliceTotal = responseData.total || responseData.chunks.length;
            } else if (Array.isArray(responseData)) {
              this.sliceList = responseData;
              this.sliceTotal = responseData.length;
            } else {
              this.sliceList = [];
              this.sliceTotal = 0;
            }
          } else {
            this.$message.error(data?.msg || this.$t('knowledgeBaseManagement.getListFailed'));
            this.sliceList = [];
            this.sliceTotal = 0;
          }
        },
        (err) => {
          this.sliceLoading = false;
          if (err && err.data) {
            this.$message.error(err.data.msg || err.msg || this.$t('knowledgeBaseManagement.getListFailed'));
          } else {
            this.$message.error(this.$t('knowledgeBaseManagement.getListFailed'));
          }
          this.sliceList = [];
          this.sliceTotal = 0;
        }
      );
    },

    handleSliceSizeChange(val) {
      this.slicePageSize = val;
      this.sliceCurrentPage = 1;
      this.fetchSlices();
    },

    handleSlicePageChange(page) {
      this.sliceCurrentPage = page;
      this.fetchSlices();
    },

    getCardColorClass(index) {
      const colors = ['blue', 'green', 'purple', 'orange', 'pink', 'cyan'];
      return colors[index % colors.length];
    },

    getIconColor(index) {
      const colors = ['#2f5bff', '#34c759', '#6a5cff', '#ff9500', '#f43f7a', '#00c9db'];
      return colors[index % colors.length];
    },

    getStatusClass(kb) {
      return kb.status === 1 ? 'active' : 'inactive';
    },

    getStatusText(kb) {
      return kb.status === 1 ? this.$t('knowledgeBaseManagement.enabled') : this.$t('knowledgeBaseManagement.disabled');
    },

    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    },

    formatFileSize(bytes) {
      if (!bytes) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB'];
      let i = 0;
      let size = bytes;
      while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
      }
      return size.toFixed(1) + ' ' + units[i];
    },
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
  background: #eff4ff;
  background-size: cover;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
}

.main-wrapper {
  height: calc(100vh - 63px - 35px);
  margin: 20px 22px 0;
  border-radius: 15px;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
}

.page-title {
  font-weight: 500;
  font-size: 24px;
  margin: 0;
}

.right-operations {
  display: flex;
  margin-left: auto;
  align-items: center;
}

.search-input {
  margin-right: 10px;
  width: 240px;
}

.content-panel {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
}

.content-area {
  flex: 1;
  height: 100%;
  min-width: 600px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ========== Knowledge Base Cards Section ========== */
.kb-section {
  background: #fff;
  border-radius: 10px;
  padding: 14px 20px;
  border: 1px solid #f0f3f9;
}

.kb-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 16px 0;
}

.kb-section-title {
  font-size: 18px;
  font-weight: 500;
  color: #1f2a44;
}

.kb-cards-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kb-cards {
  flex: 1;
  display: flex;
  gap: 24px;
  overflow-x: auto;
  padding: 10px;
  scroll-behavior: smooth;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.kb-arrow {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #fff;
  border: 1px solid #e7ecf5;
  box-shadow: 0 4px 16px rgba(31, 42, 68, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #2f5bff;
  font-size: 18px;

  &:hover {
    border-color: #2f5bff;
    box-shadow: 0 4px 20px rgba(47, 91, 255, 0.15);
  }
}

.kb-card {
  width: 300px;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid transparent;
  background: #fff;
  cursor: pointer;
  transition: all 0.25s;
  display: flex;
  flex-direction: column;
  flex: 0 0 300px;
  position: relative;
  box-shadow: 0 0 10px rgba(47, 91, 255, 0.15);

  &:hover {
    box-shadow: 0 0 10px rgba(47, 91, 255, 0.15);
    border: 1px solid #6b80eb;
  }

  &.active {
    border: 1px solid #6b80eb;
  }

  &.error {
    background: linear-gradient(135deg, #fff5f5, #fff0f0);
    border: 1px solid #fde2e2;
    box-shadow: 0 0 10px rgba(245, 108, 108, 0.15);

    &:hover {
      border: 1px solid #f56c6c;
      box-shadow: 0 0 12px rgba(245, 108, 108, 0.25);
    }

    &.active {
      border: 1px solid #f56c6c;
    }
  }
}

.kb-card-top {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.kb-card-warning {
  color: #e6a23c;
  font-size: 16px;
  cursor: pointer;
  vertical-align: middle;
  margin-left: 6px;
  animation: warning-pulse 2s ease-in-out infinite;
}

@keyframes warning-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.kb-card-actions-top {
  position: absolute;
  top: 10px;
  right: 4px;
  display: flex;
  z-index: 2;
}

.kb-action-icon {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #6b7280;
  font-size: 13px;
  transition: all 0.2s;
  padding: 0;

  &:hover {
    color: #2f5bff;
  }

  &.delete:hover {
    color: #ff5a5f;
  }
}

.kb-card-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;

  &.blue {
    background: linear-gradient(135deg, #e8ecff, #d4daff);
    color: #2f5bff;
  }
  &.purple {
    background: linear-gradient(135deg, #ede8ff, #dcd4ff);
    color: #6a5cff;
  }
  &.green {
    background: linear-gradient(135deg, #e2f9ed, #c8f0d8);
    color: #34c759;
  }
  &.orange {
    background: linear-gradient(135deg, #fff3e0, #ffe4b8);
    color: #ff9500;
  }
  &.pink {
    background: linear-gradient(135deg, #ffe4ed, #ffc8db);
    color: #f43f7a;
  }
  &.cyan {
    background: linear-gradient(135deg, #dff8fa, #c4f0f4);
    color: #00c9db;
  }
}

.kb-card-info {
  height: 100%;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.kb-card-name {
  font-size: 18px;
  font-weight: 500;
  color: #1f2a44;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}

.kb-card-desc {
  font-size: 14px;
  text-align: left;
  color: #7888a8;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-card-bottom {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kb-card-meta {
  font-size: 12px;
  color: #a0aec0;
}

.kb-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  width: 100%;
  color: #b0bbc9;
  font-size: 14px;

  i {
    font-size: 36px;
    margin-bottom: 8px;
  }
}

/* ========== Slice Dialog ========== */
.slice-management {
  display: flex;
  flex-direction: column;
}

.slice-content-container {
  flex: 1;
  overflow: hidden;
}

.slice-cards-container {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px;

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-thumb {
    background: #e0e0e0;
    border-radius: 3px;
  }
}

.slice-card {
  background: #f8f9fa;
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }
}

.slice-header-info {
  margin-bottom: 10px;
  p {
    margin: 0;
    font-size: 14px;
    strong {
      color: #374151;
    }
  }
}

.slice-card-content {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  text-align: left;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: #e0e0e0;
    border-radius: 2px;
  }
  .clice-index {
    color: #467afe;
    display: inline-block;
    padding: 4px 6px;
    background: #e6f0fe;
    border-radius: 4px;
  }
}

.content-text {
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}

.no-slice-data {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slice-pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}


/* ========== Selected Files List ========== */
.selected-files-section {
  margin-top: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background-color: #f8f9fa;

  h4 {
    margin: 0 0 12px 0;
    font-size: 14px;
    font-weight: 600;
    color: #606266;
  }
}

.selected-files-list {
  max-height: 180px;
  overflow-y: auto;
}

.selected-file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: white;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }

  .file-info {
    display: flex;
    align-items: center;
    flex: 1;

    .el-icon-document {
      color: #409eff;
      margin-right: 8px;
      font-size: 16px;
    }

    .file-name {
      font-size: 14px;
      color: #303133;
      margin-right: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 300px;
    }

    .file-size {
      font-size: 12px;
      color: #909399;
    }
  }

  .remove-btn {
    color: #f56c6c;
    padding: 4px;

    &:hover {
      color: #f78989;
      background-color: #fef0f0;
      border-radius: 4px;
    }
  }
}

/* ========== Retrieval Test Dialog ========== */
.retrieval-test-form {
  .result-chunks {
    max-height: 400px;
    overflow-y: auto;
  }

  .result-chunk {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 14px;

    .chunk-left {
      flex-shrink: 0;
      display: flex;
      align-items: center;

      .chunk-similarity {
        // font-size: 12px;
        color: #409eff;
        white-space: nowrap;

        .similarity-label {
          // font-size: 12px;
          color: #333;
          margin-bottom: 4px;
        }

        .similarity-value {
          text-align: left;
          margin-top: 4px;
          font-size: 16px;
          font-weight: 600;
          margin-bottom: 12px;
        }

        .similarity-progress {
          margin-top: 8px;

          ::v-deep(.el-progress-bar__outer) {
            border-radius: 3px;
            background-color: rgba(64, 158, 255, 0.1);
          }
          ::v-deep(.el-progress-bar__inner) {
            border-radius: 3px;
            background: #4a7cfd;
          }
        }
      }
    }

    .chunk-right {
      flex: 1;
      min-width: 0;

      .chunk-right-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .chunk-source {
          font-size: 14px;
          font-weight: 600;
        }

        .chunk-index {
          color: #467afe;
          display: inline-block;
          padding: 4px 6px;
          background: #e6f0fe;
          border-radius: 4px;
        }
      }

      .chunk-content {
        text-align: left;
        white-space: normal;
        background: #fff;
        border-radius: 4px;
        // max-height: 150px;
        // overflow-y: auto;
        font-size: 14px;
        line-height: 1.6;
        // white-space: pre-wrap;
        // word-break: break-word;
        > p {
          margin: 0;
        }
      }
    }
  }
}
</style>
