<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">默认角色管理</h2>
      <div class="right-operations">
        <el-input placeholder="请输入模板名称查询" v-model="search" class="search-input" clearable
          @keyup.enter.native="handleSearch" style="width: 240px" />
        <el-button class="btn-search" @click="handleSearch">
          搜索
        </el-button>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="template-card" shadow="never">
            
            
            <el-table ref="templateTable" :data="templateList" style="width: 100%" v-loading="templateLoading"
              element-loading-text="拼命加载中" element-loading-spinner="el-icon-loading"
              element-loading-background="rgba(255, 255, 255, 0.7)"
              class="transparent-table" @row-click="handleRowClick">
              <!-- 自定义选择列，实现表头是"选择"文字，数据行是小方框 -->
              <el-table-column label="选择" align="center" width="80">
                <template slot-scope="scope">
                  <el-checkbox v-model="scope.row.selected" @change="handleRowSelectionChange(scope.row)"></el-checkbox>
                </template>
              </el-table-column>
              <el-table-column label="模板名称" prop="agentName" align="center"></el-table-column>
              <el-table-column label="语言编码" prop="langCode" align="center"></el-table-column>
              <el-table-column label="交互语种" prop="language" align="center"></el-table-column>
              <el-table-column label="排序" prop="sort" align="center"></el-table-column>
              <!-- 将原来的操作列合并为一列，显示编辑和删除按钮 -->
              <el-table-column label="操作" width="160" align="center">
                <template slot-scope="scope">
                  <el-button type="text" size="mini" @click.stop="editTemplate(scope.row)">编辑</el-button>
                  <el-button type="text" size="mini" @click.stop="deleteTemplate(scope.row)" class="delete-btn">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            
            <!-- 修改table_bottom结构，添加按钮组容器 -->
            <div class="table_bottom">
              <!-- 左侧按钮组 -->
              <div class="ctrl_btn">
                <!-- 将checkbox改为按钮样式 -->
                <el-button size="mini" type="primary" class="select-all-btn" @click="handleSelectAll">
                  {{ isAllSelected ? '取消全选' : '全选' }}
                </el-button>
                <el-button size="mini" type="success" @click="showAddTemplateDialog">新增模板</el-button>
                <el-button size="mini" type="danger" @click="batchDeleteTemplate" :disabled="selectedTemplates.length === 0">
                  批量删除模板
                </el-button>
              </div>
              
              <!-- 右侧分页控件 -->
              <div class="custom-pagination">
                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                  <el-option v-for="item in pageSizeOptions" :key="item" :label="`${item}条/页`" :value="item">
                  </el-option>
                </el-select>

                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">
                  首页
                </button>
                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">
                  上一页
                </button>
                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                  :class="{ active: page === currentPage }" @click="goToPage(page)">
                  {{ page }}
                </button>
                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">
                  下一页
                </button>
                <span class="total-text">共{{ total }}条记录</span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 使用模板编辑弹框组件 -->
    <AgentTemplateDialog :visible.sync="templateDialogVisible" :title="templateDialogTitle" :templateData="templateForm"
      @save="saveTemplate" />
    <el-footer style="flex-shrink:unset;">
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import agentApi from '@/apis/module/agent'
import AgentTemplateDialog from '@/components/AgentTemplateDialog.vue'
import HeaderBar from '@/components/HeaderBar.vue'
import VersionFooter from '@/components/VersionFooter.vue'

export default {
  name: 'AgentTemplateManagement',
  components: {
    HeaderBar,
    AgentTemplateDialog,
    VersionFooter
  },
  // 1. 首先确保在 data 部分添加了 isAllSelected 状态
  data() {
    return {
      // 模板相关
      templateList: [],
      templateLoading: false,
      selectedTemplates: [],
      isAllSelected: false, // 添加全选状态
      templateDialogVisible: false,
      templateDialogTitle: '新增模板',
      templateForm: {
        id: null,
        agentCode: '',
        agentName: '',
        asrModelId: '',
        vadModelId: '',
        llmModelId: '',
        vllmModelId: '',
        ttsModelId: '',
        ttsVoiceId: '',
        memModelId: '',
        intentModelId: '',
        chatHistoryConf: 0,
        systemPrompt: '',
        summaryMemory: '',
        langCode: '',
        language: '',
        sort: 0
      },
      search: '',
      // 分页相关数据
      pageSizeOptions: [10, 20, 50, 100],
      currentPage: 1,
      pageSize: 10,
      total: 0
    }
  },
  created() {
    this.loadTemplateList()
  },
  computed: {
    pageCount() {
      return Math.ceil(this.total / this.pageSize)
    },
    visiblePages() {
      return this.getVisiblePages()
    }
  },
  methods: {
    // 加载模板列表
    // 改进loadTemplateList方法的错误处理逻辑
    loadTemplateList() {
      this.templateLoading = true
      const params = {
        page: this.currentPage,
        limit: this.pageSize
      }
      if (this.search) {
        params.agentName = this.search
      }
      
      try {
        agentApi.getAgentTemplatesPage(params, (res) => {
          // 更健壮的响应处理逻辑
          if (res && typeof res === 'object') {
            if (res.data && res.data.code === 0) {
              const responseData = res.data.data || {}
              // 为每个模板添加selected属性
              this.templateList = Array.isArray(responseData.list) ? 
                responseData.list.map(item => ({ ...item, selected: false })) : []
              this.total = typeof responseData.total === 'number' ? responseData.total : 0
            } else {
              console.error('获取模板列表失败:', res)
              this.templateList = []
              this.total = 0
              this.$message.error(res?.data?.msg || '获取模板列表失败')
            }
          } else {
            console.error('无效的响应对象:', res)
            this.templateList = []
            this.total = 0
            this.$message.error('获取模板列表失败')
          }
          this.templateLoading = false
        }, (error) => {
          console.error('API调用失败:', error)
          this.templateList = []
          this.total = 0
          this.templateLoading = false
          this.$message.error('网络请求失败')
        })
      } catch (error) {
        console.error('调用API时发生异常:', error)
        this.templateList = []
        this.total = 0
        this.templateLoading = false
        this.$message.error('加载模板列表时发生错误')
      }
    },

    // 搜索模板
    handleSearch() {
      if (this.search) {
        const searchValue = this.search.toLowerCase()
        const filteredList = this.templateList.filter(template => 
          template.agentName.toLowerCase().includes(searchValue)
        )
        this.templateList = filteredList
        this.total = filteredList.length
      } else {
        this.loadTemplateList()
      }
    },

    // 修改showAddTemplateDialog方法，使其跳转到与编辑页面相同的页面
    // 显示新增模板弹窗
    showAddTemplateDialog() {
      // 跳转到模板快速配置页面，不传递templateId参数表示新增
      this.$router.push({
        path: '/template-quick-config'
      })
    },
    
    // 保留原有的editTemplate方法
    // 编辑模板 - 完全替换这个方法
    editTemplate(row) {
      // 跳转到模板快速配置页面，并传递模板ID参数
      this.$router.push({
        path: '/template-quick-config',
        query: { templateId: row.id }
      })
    },

    // 保存模板
    saveTemplate(data) {
      // 这里需要调用保存模板的API
      if (data.id) {
        // 更新模板
        agentApi.updateAgentTemplate(data, (res) => {
          if (res.code === 0) {
            this.$message.success('模板更新成功')
            this.templateDialogVisible = false
            this.loadTemplateList()
          } else {
            this.$message.error('模板更新失败')
          }
        })
      } else {
        // 新增模板
        agentApi.addAgentTemplate(data, (res) => {
          if (res.code === 0) {
            this.$message.success('模板新增成功')
            this.templateDialogVisible = false
            this.loadTemplateList()
          } else {
            this.$message.error('模板新增失败')
          }
        })
      }
    },

    // 删除模板
    deleteTemplate(row) {
      this.$confirm('确定要删除这个模板吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        agentApi.deleteAgentTemplate(row.id, (res) => {
          // 添加调试日志
          console.log('删除模板响应:', res);
          
          if (res && typeof res === 'object') {
            // 检查res.data是否存在且包含code=0
            if (res.data && res.data.code === 0) {
              this.$message.success('模板删除成功')
              this.loadTemplateList()
            } else {
              this.$message.error(res?.data?.msg || '模板删除失败')
            }
          } else {
            console.error('无效的响应对象:', res);
            this.$message.error('删除失败，请检查后端服务是否正常')
          }
        })
      }).catch(() => {
        this.$message.info('已取消删除')
      })
    },

    // 修改batchDeleteTemplate方法，使用selectedTemplates
    batchDeleteTemplate() {
      if (this.selectedTemplates.length === 0) {
        this.$message.warning('请选择要删除的模板')
        return
      }

      this.$confirm(`确定要删除选中的 ${this.selectedTemplates.length} 个模板吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const ids = this.selectedTemplates.map(template => template.id)
        agentApi.batchDeleteAgentTemplate(ids, (res) => {
          if (res && typeof res === 'object') {
            if (res.data && res.data.code === 0) {
              this.$message.success('模板批量删除成功')
              this.loadTemplateList()
              this.selectedTemplates = []
              this.isAllSelected = false
            } else {
              this.$message.error(res?.data?.msg || '模板批量删除失败')
            }
          } else {
            console.error('无效的响应对象:', res)
            this.$message.error('删除失败')
          }
        })
      }).catch(() => {
        this.$message.info('已取消删除')
      })
    },



    // 分页相关方法
    handlePageSizeChange() {
      this.currentPage = 1
    },
    goFirst() {
      this.currentPage = 1
    },
    goPrev() {
      this.currentPage--
    },
    goNext() {
      this.currentPage++
    },
    goToPage(page) {
      this.currentPage = page
    },
    getVisiblePages() {
      const pages = []
      const totalPages = this.pageCount
      const currentPage = this.currentPage
      
      if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) {
          pages.push(i)
        }
      } else {
        if (currentPage <= 4) {
          for (let i = 1; i <= 5; i++) {
            pages.push(i)
          }
          pages.push('...')
          pages.push(totalPages)
        } else if (currentPage >= totalPages - 3) {
          pages.push(1)
          pages.push('...')
          for (let i = totalPages - 4; i <= totalPages; i++) {
            pages.push(i)
          }
        } else {
          pages.push(1)
          pages.push('...')
          for (let i = currentPage - 1; i <= currentPage + 1; i++) {
            pages.push(i)
          }
          pages.push('...')
          pages.push(totalPages)
        }
      }
      
      return pages
    },
    
    // 修改handleSelectAll方法
    handleSelectAll() {
      this.isAllSelected = !this.isAllSelected
      this.templateList.forEach(row => {
        row.selected = this.isAllSelected
      })
      // 更新选中的模板列表
      this.selectedTemplates = this.isAllSelected ? [...this.templateList] : []
    },
    
    // 处理行选择变化
    handleRowSelectionChange(row) {
      // 查找选中的模板
      this.selectedTemplates = this.templateList.filter(template => template.selected);
      // 更新全选状态
      this.isAllSelected = this.templateList.length > 0 && this.selectedTemplates.length === this.templateList.length;
    },

    // 修改handleRowClick方法，实现点击行选中/取消选中
    handleRowClick(row, event, column) {
      // 如果点击的是选择框所在的列，则不触发行选择
      if (column && column.label === '选择') {
        return;
      }
      row.selected = !row.selected;
      this.handleRowSelectionChange(row);
    },

  }
}
</script>

<style scoped lang="scss">
/* 首先确保html和body元素有正确的背景设置 */
:global(html),
:global(body) {
  background: #f5f7fa;
  margin: 0;
  padding: 0;
  height: 100%;
}

.welcome {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  background-size: cover;
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd) center;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
  width: 100%;
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
  align-items: center;
  gap: 10px;
}

.search-input {
  width: 200px;
}

.btn-search {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
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

.content-panel {
  width: 100%;
  flex: 1;
  display: flex;
  overflow: hidden;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.content-area {
  flex: 1;
  min-width: 600px;
  overflow-x: auto;
  background-color: white;
  display: flex;
  flex-direction: column;
  position: relative;
}

.template-card {
  border: none;
  box-shadow: none;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  :deep(.el-card__body) {
    padding: 15px;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }
}

.transparent-table {
  width: 100%;
  /* 关键：为表格容器设置最大高度，确保有足够空间将按钮推到底部 */
  flex: 1;
  min-height: 0;
}

/* 添加表格内部容器的样式，确保表格本身有高度限制 */
:deep(.el-table) {
  height: 100%;
  display: flex;
  flex-direction: column;
  --table-max-height: calc(100vh - 42vh);
  max-height: var(--table-max-height);
  
  .el-table__body-wrapper {
    flex: 1;
    overflow-y: auto;
    overflow-x: auto;
  }
}

// 表格底部操作栏
.table_bottom {
  display: flex;
  justify-content: space-between !important;
  align-items: center;
  margin-top: auto; /* 关键：使用auto margin将按钮栏推到底部 */
  padding: 0 20px 15px !important; /* 增加底部padding，让按钮看起来更靠下 */
  width: 100% !important;
  box-sizing: border-box !important;
}

.ctrl_btn {
  display: flex;
  gap: 8px;
  padding-left: 0 !important;
  margin-left: 0 !important;
  
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

  .el-button--success {
    background: #5bc98c;
    color: white;
  }

  .el-button--danger {
    background: #fd5b63;
    color: white;
  }
}

// 自定义分页样式
.custom-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto !important;
  padding-right: 0 !important;
  margin-right: 0 !important;
}

// 调整分页按钮样式
.pagination-btn:last-child {
  margin-right: 0;
}
  .el-select {
    margin-right: 8px;
  }

  .pagination-btn:first-child,
  .pagination-btn:nth-child(2),
  .pagination-btn:nth-child(3),
  .pagination-btn:nth-last-child(2) {
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

  .pagination-btn:not(:first-child):not(:nth-child(2)):not(:nth-child(3)):not(:nth-last-child(2)) {
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


// 表格内部样式调整
:deep(.el-table__header th) {
  padding: 8px 0 !important;
  height: 40px !important;
}

:deep(.el-table__header th .cell) {
  color: #303133 !important;
  font-weight: 600;
}

:deep(.el-table__body) {
  .el-table__row td {
    padding: 12px 0 !important;
    border-bottom: 1px solid #ebeef5;
  }
  .el-table__row:hover {
    background-color: #f5f7fa;
  }
}

:deep(.el-table .el-button--text) {
  color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5;
}

:deep(.el-table .cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

// 选择框样式
:deep(.el-checkbox__inner) {
  background-color: #ffffff !important;
  border-color: #dcdfe6 !important;
  width: 16px !important;
  height: 16px !important;
  border-radius: 2px !important;
}

:deep(.el-checkbox__inner:hover) {
  border-color: #c0c4cc !important;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #5f70f3 !important;
  border-color: #5f70f3 !important;
}

// 调整表格最大高度
:deep(.el-table) {
  --table-max-height: calc(100vh - 42vh);
  max-height: var(--table-max-height);
  .el-table__body-wrapper {
    max-height: calc(var(--table-max-height) - 40px);
  }
}
</style>