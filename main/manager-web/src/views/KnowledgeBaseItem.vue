<template>
  <div class="doc-section">
    <div class="doc-section-header">
      <div class="doc-section-left">
        <div class="doc-section-title">{{`${$t('knowledgeBaseManagement.currentKnowledgeBaseDocuments')}（${kb?.name}）`}}</div>
        <div class="doc-section-count" v-if="kb">{{ $t('knowledgeBaseManagement.totalDocuments', { total }) }}</div>
      </div>
      <div class="doc-section-actions">
        <el-input
          :placeholder="$t('knowledgeFileUpload.documentNamePlaceholder')"
          v-model="searchDocName"
          class="doc-search-input"
          size="small"
          prefix-icon="el-icon-search"
          clearable
        />
        <CustomButton size="small" @click="handleSearch">{{ $t('knowledgeBaseManagement.search') }}</CustomButton>
        <CustomButton type="add" size="small" @click="handleUpload">{{ $t('knowledgeBaseManagement.add') }}</CustomButton>
        <CustomButton type="confirm" size="small" @click="handleRetrievalTest">{{ $t('knowledgeFileUpload.retrievalTest') }}</CustomButton>
      </div>
    </div>
    <div class="doc-grid" v-loading="docLoading" :element-loading-text="$t('knowledgeBaseManagement.loading')">
      <div v-for="doc in documents" :key="doc.id" class="doc-card">
        <div class="doc-card-top">
          <img class="doc-file-icon" :src="getFileIconSrc(doc.name)" />
          <div class="doc-card-info">
            <div class="doc-card-name" :title="doc.name">{{ doc.name }}</div>
            <div class="doc-card-meta">{{ $t('knowledgeFileUpload.uploadTime') }} {{ formatDate(doc.createdAt) }}</div>
          </div>
        </div>
        <div class="doc-card-bottom">
          <div class="doc-card-progress">
            <div class="progress-ring">
              <svg viewBox="0 0 40 40">
                <circle class="bg" cx="20" cy="20" r="15"/>
                <circle class="fg" :class="getProgressClass(doc)" cx="20" cy="20" r="15"
                  stroke-dasharray="94.25"
                  :stroke-dashoffset="getProgressOffset(doc)"/>
              </svg>
              <span class="progress-ring-text" :style="{ color: getProgressTextColor(doc) }">{{ getProgressText(doc) }}</span>
            </div>
            <div class="progress-container">
              <span class="progress-label" :class="getProgressClass(doc)">{{ getDocStatusText(doc) }}</span>
              <span class="doc-slice-count">{{ $t('knowledgeFileUpload.sliceCount') }} <b>{{ doc.sliceCount }}</b></span>
            </div>
          </div>
          <div class="doc-card-actions">
            <el-button
              v-if="doc.parseStatusCode === 3"
              type="text"
              @click.stop="$emit('view-slices', doc)"
            >
              {{ $t('knowledgeFileUpload.viewSlices') }}
            </el-button>
            <el-button
              v-else
              type="text"
              :disabled="doc.parseStatusCode === 1"
              :loading="doc.parsing"
              @click.stop="handleParse(doc)"
            >
              {{ $t('knowledgeFileUpload.parse') }}
            </el-button>
            <el-button type="text" class="delete-btn" :loading="deleteLoadingMap[doc.id]" @click.stop="handleDelete(doc)">
              {{ $t('knowledgeBaseManagement.delete') }}
            </el-button>
          </div>
        </div>
      </div>
      <div v-if="documents.length === 0 && !docLoading" class="doc-empty">
        <el-empty :description="$t('knowledgeBaseManagement.noData')"></el-empty>
      </div>
    </div>
    <CustomPagination
      class="pagination-wrapper"
      :total="total"
      :current-page="currentPage"
      :page-size="pageSize"
      :page-size-options="pageSizeOptions"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
    />
  </div>
</template>

<script>
import Api from "@/apis/api";
import CustomButton from "@/components/CustomButton.vue";
import CustomPagination from "@/components/CustomPagination.vue";

const iconMap = {
  pdf: require('@/assets/knowledge-base/pdf.png'),
  doc: require('@/assets/knowledge-base/docX.png'),
  docx: require('@/assets/knowledge-base/docX.png'),
  xls: require('@/assets/knowledge-base/xlsx.png'),
  xlsx: require('@/assets/knowledge-base/xlsx.png'),
  csv: require('@/assets/knowledge-base/xlsx.png'),
  md: require('@/assets/knowledge-base/MD.png'),
  markdown: require('@/assets/knowledge-base/MD.png'),
  txt: require('@/assets/knowledge-base/txt.png'),
};

export default {
  name: 'LibraryItem',
  components: { CustomPagination, CustomButton },
  props: {
    kb: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      documents: [],
      docLoading: false,
      deleteLoadingMap: {},
      searchDocName: '',
      total: 0,
      currentPage: 1,
      pageSize: 10,
      pageSizeOptions: [10, 20, 50, 100],
    };
  },
  watch: {
    kb: {
      handler(newKb) {
        if (newKb && newKb.datasetId) {
          this.currentPage = 1;
          this.fetchDocuments();
        } else {
          this.documents = [];
          this.total = 0;
        }
      },
      immediate: true
    }
  },
  methods: {
    fetchDocuments() {
      if (!this.kb || !this.kb.datasetId) return;
      this.docLoading = true;
      const params = {
        page: this.currentPage,
        page_size: this.pageSize,
        name: this.searchDocName
      };
      Api.knowledgeBase.getDocumentList(
        this.kb.datasetId,
        params,
        ({ data }) => {
          this.docLoading = false;
          if (data && data.code === 0) {
            this.documents = data.data.list || [];
            this.total = data.data.total || 0;
            this.fetchSliceCountsForDocuments();
          } else {
            this.$message.error(data?.msg || '获取文档列表失败');
            this.documents = [];
            this.total = 0;
          }
        },
        (err) => {
          this.docLoading = false;
          if (err && err.data) {
            this.$message.error(err.data.msg || err.msg || '获取文档列表失败');
          } else {
            this.$message.error('获取文档列表失败');
          }
          this.documents = [];
          this.total = 0;
        }
      );
    },

    handleSearch() {
      this.currentPage = 1;
      this.fetchDocuments();
    },

    handlePageChange(page) {
      this.currentPage = page;
      this.fetchDocuments();
    },

    handleSizeChange(size) {
      this.pageSize = size;
      this.currentPage = 1;
      this.fetchDocuments();
    },

    handleUpload() {
      this.$emit('upload');
    },

    handleRetrievalTest() {
      this.$emit('retrieval-test');
    },

    handleDelete(doc) {
      if (!this.kb) return;
      this.$confirm(
        this.$t('knowledgeFileUpload.confirmDelete'),
        this.$t('message.warning'),
        {
          confirmButtonText: this.$t('knowledgeBaseDialog.confirm'),
          cancelButtonText: this.$t('knowledgeBaseDialog.cancel'),
          type: 'warning'
        }
      ).then(() => {
        this.$set(this.deleteLoadingMap, doc.id, true);
        Api.knowledgeBase.deleteDocument(this.kb.datasetId, doc.id, (res) => {
          this.$set(this.deleteLoadingMap, doc.id, false);
          if (res.data && res.data.code === 0) {
            if (this.documents.length === 1 && this.currentPage > 1) {
              this.currentPage--;
            }
            this.fetchDocuments();
            this.$message.success(this.$t('knowledgeFileUpload.deleteSuccess'));
          } else {
            this.$message.error(res.data?.msg || this.$t('knowledgeFileUpload.deleteFailed'));
          }
        }, (err) => {
          this.$set(this.deleteLoadingMap, doc.id, false);
          this.$message.error(err?.data?.msg ||this.$t('knowledgeFileUpload.deleteFailed'));
        });
      }).catch(() => {});
    },

    handleParse(doc) {
      this.$confirm(this.$t('knowledgeFileUpload.confirmParse'), this.$t('message.info'), {
        confirmButtonText: this.$t('knowledgeFileUpload.confirm'),
        cancelButtonText: this.$t('knowledgeFileUpload.cancel'),
        type: 'info'
      }).then(() => {
        this.$set(doc, 'parsing', true);
        doc.parseStatusCode = 1;
        Api.knowledgeBase.parseDocument(
          this.kb.datasetId,
          doc.id,
          ({ data }) => {
            if (data && data.code === 0) {
              this.$message.success(this.$t('knowledgeFileUpload.parsing'));
              this.$set(doc, 'parsing', false);
              this.startParsePolling(doc);
            } else {
              this.$set(doc, 'parsing', false);
              doc.parseStatusCode = 0;
              this.$message.error(data?.msg || this.$t('knowledgeFileUpload.parseFailed'));
            }
          },
          (err) => {
            this.$set(doc, 'parsing', false);
            doc.parseStatusCode = 0;
            this.$message.error(err?.data?.msg || this.$t('knowledgeFileUpload.parseFailed'));
          }
        );
      }).catch(() => {});
    },

    startParsePolling(doc) {
      const poll = () => {
        if (!this.kb) return;
        Api.knowledgeBase.getDocumentList(
          this.kb.datasetId,
          { page: 1, page_size: 100, name: this.searchDocName },
          ({ data }) => {
            if (data && data.code === 0) {
              const list = data.data.list || [];
              const updated = list.find(d => d.id === doc.id);
              if (updated) {
                this.$set(doc, 'parseStatusCode', updated.parseStatusCode);
                if (updated.parseStatusCode !== 1) {
                  this.$set(doc, 'parsing', false);
                  if (updated.parseStatusCode === 3) {
                    this.$message.success(`「${doc.name}」${this.$t('knowledgeFileUpload.parseSuccess')}`);
                    this.fetchSliceCountForSingleDocument(doc);
                  } else if (updated.parseStatusCode === 4) {
                    this.$message.error(`「${doc.name}」${this.$t('knowledgeFileUpload.parseFailed')}`);
                  }
                  return;
                }
              }
              setTimeout(poll, 5000);
            }
          },
          () => {
            setTimeout(poll, 5000);
          }
        );
      };
      setTimeout(poll, 3000);
    },

    fetchSliceCountsForDocuments() {
      if (!this.documents || this.documents.length === 0) return;
      this.documents.forEach(doc => {
        this.fetchSliceCountForSingleDocument(doc);
      });
    },

    fetchSliceCountForSingleDocument(doc) {
      const params = { page: 1, page_size: 1 };
      Api.knowledgeBase.listChunks(
        this.kb.datasetId,
        doc.id,
        params,
        ({ data }) => {
          if (data && data.code === 0) {
            this.$set(doc, 'sliceCount', data.data.total || 0);
          }
        },
        () => {}
      );
    },

    getFileIconSrc(fileName) {
      if (!fileName) return require('@/assets/knowledge-base/default.png');
      const ext = fileName.split('.').pop().toLowerCase();
      return iconMap[ext] || require('@/assets/knowledge-base/default.png');
    },

    getProgressClass(doc) {
      const code = doc.parseStatusCode;
      if (code === 3) return 'complete';
      if (code === 1) return 'processing';
      return 'pending';
    },

    getProgressOffset(doc) {
      const code = doc.parseStatusCode;
      const circumference = 94.25;
      if (code === 3) return 0;
      if (code === 1) {
        const progress = doc.chunkNum && doc.totalChunkNum
          ? Math.round((doc.chunkNum / doc.totalChunkNum) * 100)
          : 50;
        return circumference * (1 - progress / 100);
      }
      return circumference;
    },

    getProgressText(doc) {
      const code = doc.parseStatusCode;
      if (code === 3) return '100%';
      if (code === 1) {
        if (doc.chunkNum && doc.totalChunkNum) {
          return Math.round((doc.chunkNum / doc.totalChunkNum) * 100) + '%';
        }
        return '50%';
      }
      return '0%';
    },

    getProgressTextColor(doc) {
      const code = doc.parseStatusCode;
      if (code === 3) return '#34c759';
      if (code === 1) return '#2f5bff';
      return '#7888a8';
    },

    getDocStatusText(doc) {
      const code = doc.parseStatusCode;
      if (code === 3) return this.$t('knowledgeFileUpload.statusCompleted');
      if (code === 1) return this.$t('knowledgeFileUpload.statusProcessing');
      if (code === 0) return this.$t('knowledgeFileUpload.statusNotStarted');
      if (code === 4) return this.$t('knowledgeFileUpload.statusFailed');
      if (code === 2) return this.$t('knowledgeFileUpload.statusCancelled');
      return this.$t('knowledgeFileUpload.statusNotStarted');
    },

    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    },
  }
};
</script>

<style lang="scss" scoped>
/* ========== Document Section ========== */
.doc-section {
  background: #fff;
  border-radius: 10px;
  padding: 16px 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.doc-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.doc-section-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doc-section-title {
  font-size: 18px;
  font-weight: 500;
  color: #1f2a44;
}

.doc-section-count {
  font-size: 18px;
  color: #788ba8;
}

.doc-section-actions {
  display: flex;
  align-items: center;
}

.doc-search-input {
  width: 200px;
  margin-right: 10px;
}

/* ========== Document Grid ========== */
.doc-grid {
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill,minmax(300px, 1fr));
  gap: 16px 20px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
}

.doc-card {
  max-height: 110px;
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 18px;
  background: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s;
  position: relative;
  box-shadow: 0 0 6px rgba(47, 91, 255, 0.15);

  &:hover {
    box-shadow: 0 0 6px rgba(47, 91, 255, 0.15);
    border: 1px solid #6b80eb;
  }
}

.doc-card-top {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.doc-file-icon {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  object-fit: contain;
  flex-shrink: 0;
}

.doc-card-info {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  text-align: left;
}

.doc-card-name {
  font-size: 15px;
  font-weight: 500;
  color: #1f2a44;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.doc-card-meta {
  font-size: 13px;
  color: #7888a8;
}

.doc-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.doc-card-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ========== Progress Ring ========== */
.progress-ring {
  width: 40px;
  height: 40px;
  position: relative;

  svg {
    width: 40px;
    height: 40px;
    transform: rotate(-90deg);
  }

  .bg {
    fill: none;
    stroke: #e7ecf5;
    stroke-width: 4;
  }

  .fg {
    fill: none;
    stroke-width: 4;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.5s ease;

    &.complete { stroke: #34c759; }
    &.processing { stroke: #2f5bff; }
    &.pending { stroke: #e7ecf5; }
  }
}

.progress-ring-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 10px;
  font-weight: 600;
  color: #7888a8;
}

.progress-container {
  height: 36px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  .progress-label {
    font-size: 12px;
    color: #7888a8;
  
    &.complete { color: #34c759; }
    &.processing { color: #2f5bff; }
  }

  .doc-slice-count {
    font-size: 12px;
    > b {
      font-weight: bold;
      font-size: 14px;
    }
  }
}


.doc-card-actions {
  display: flex;
  align-items: center;
  gap: 4px;

  :deep(.el-button--text) {
    padding: 4px 8px;
    font-size: 13px;
  }

  .delete-btn {
    color: #f56c6c !important;
    &:hover {
      color: #f78989 !important;
    }
  }
}

.doc-empty {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: #b0bbc9;
  font-size: 14px;

  i {
    font-size: 48px;
    margin-bottom: 12px;
  }
}

.pagination-wrapper {
  margin-top: 20px;
}

@media (max-width: 1144px) {
  .doc-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .doc-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>