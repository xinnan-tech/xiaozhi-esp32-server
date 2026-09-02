<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <el-card class="main-card" shadow="never">
        <div class="operation-header">
          <h2 class="page-title">{{ $t('dictManagement.pageTitle') }}</h2>
          <div class="right-operations">
            <el-input :placeholder="$t('dictManagement.searchPlaceholder')" v-model="search" class="search-input"
              @keyup.enter.native="handleSearch" clearable />
            <CustomButton icon="el-icon-search" type="confirm" @click="handleSearch">
              {{ $t('dictManagement.search') }}
            </CustomButton>
          </div>
        </div>
        <div class="content-panel">
          <!-- 左侧字典类型列表 -->
          <div class="dict-type-panel">
            <div class="dict-type-header">
              <h4 class="dict-type-title">{{ $t('dictManagement.dictTypeCategory') }}</h4>
              <div>
                <el-button icon="el-icon-plus" size="mini" @click="showAddDictTypeDialog" />
                <el-button icon="el-icon-delete" size="mini" @click="batchDeleteDictType" />
              </div>
            </div>
            <div class="dict-type-checkbox" v-loading="dictTypeLoading">
              <el-checkbox class="dict-type-all" :indeterminate="isIndeterminate" v-model="checkAll" @change="handleCheckAllChange">{{ $t('common.selectAll') }}</el-checkbox>
              <el-checkbox-group v-model="checkedDictTypesIds" @change="handleDictTypeSelectionChange">
                <div 
                  class="dict-type-item" 
                  :class="{ 'dict-type-active': selectedDictType?.id === item.id }"
                  v-for="item in dictTypeList" 
                  :key="item.id"
                >
                  <el-checkbox :label="item.dictName" :key="item.id">
                  </el-checkbox>
                  <div class="dict-type-item-content" @click="handleDictTypeRowClick(item)">
                    <span class="dict-type-name">{{item.dictName}}</span>
                    <el-button class="dict-type-edit-btn" type="text" icon="el-icon-edit" size="mini" @click.stop="editDictType(item)"/>
                  </div>
                </div>
              </el-checkbox-group>
            </div>
          </div>
          <!-- 右侧字典数据列表 -->
          <div class="content-area">
            <CustomTable :data="dictDataList" :columns="tableColumns" :loading="dictDataLoading" :show-selection="true"
              :show-operations="true" :operations-label="$t('dictManagement.operation')" :total="total"
              :current-page="currentPage" :page-size="pageSize" :page-size-options="pageSizeOptions"
              @size-change="handlePageSizeChange" @page-change="goToPage">
              <template slot="selection" slot-scope="scope">
                <el-checkbox v-model="scope.row.selected"></el-checkbox>
              </template>
              <template slot="operations" slot-scope="scope">
                <el-button type="text" size="mini" @click="editDictData(scope.row)">
                  {{ $t('dictManagement.edit') }}
                </el-button>
                <el-button type="text" size="mini" @click="deleteDictData(scope.row)">
                  {{ $t('dictManagement.delete') }}
                </el-button>
              </template>
              <template slot="footer-btns">
                <div class="ctrl_btn">
                  <CustomButton :icon="isAllDictDataSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'"
                    size="small" @click="selectAllDictData">
                    {{ isAllDictDataSelected ? $t('dictManagement.deselectAll') : $t('dictManagement.selectAll') }}
                  </CustomButton>
                  <CustomButton type="add" icon="el-icon-plus" size="small" @click="showAddDictDataDialog">
                    {{ $t('dictManagement.addDictData') }}
                  </CustomButton>
                  <CustomButton size="small" type="delete" icon="el-icon-delete" @click="batchDeleteDictData">
                    {{ $t('dictManagement.batchDeleteDictData') }}
                  </CustomButton>
                </div>
              </template>
            </CustomTable>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 使用字典类型编辑弹框组件 -->
    <DictTypeDialog :visible.sync="dictTypeDialogVisible" :title="dictTypeDialogTitle" :dictTypeData="dictTypeForm"
      @save="saveDictType" />

    <!-- 使用字典数据编辑弹框组件 -->
    <DictDataDialog :visible.sync="dictDataDialogVisible" :title="dictDataDialogTitle" :dictData="dictDataForm"
      :dictTypeId="selectedDictType?.id" @save="saveDictData" />
    <el-footer style="flex-shrink:unset;">
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import dictApi from '@/apis/module/dict'
import DictDataDialog from '@/components/DictDataDialog.vue'
import DictTypeDialog from '@/components/DictTypeDialog.vue'
import HeaderBar from '@/components/HeaderBar.vue'
import VersionFooter from '@/components/VersionFooter.vue'
import CustomButton from '@/components/CustomButton.vue'
import CustomTable from '@/components/CustomTable.vue'
export default {
  name: 'DictManagement',
  components: {
    HeaderBar,
    DictTypeDialog,
    DictDataDialog,
    VersionFooter,
    CustomButton,
    CustomTable
  },
  data() {
    return {
      // 字典类型相关
      dictTypeList: [],
      dictTypeLoading: false,
      selectedDictType: null,
      selectedDictTypes: [],
      dictTypeDialogVisible: false,
      dictTypeDialogTitle: '新增字典类型',
      dictTypeForm: {
        id: null,
        dictName: '',
        dictType: ''
      },

      // 字典数据相关
      dictDataList: [],
      dictDataLoading: false,
      isAllDictDataSelected: false,
      dictDataDialogVisible: false,
      dictDataDialogTitle: '新增字典数据',
      dictDataForm: {
        id: null,
        dictTypeId: null,
        dictLabel: '',
        dictValue: '',
        sort: 0
      },
      search: '',
      pageSizeOptions: [10, 20, 50, 100],
      currentPage: 1,
      pageSize: 10,
      total: 0,
      tableColumns: [],
      isIndeterminate: false,
      checkAll: false,
      checkedDictTypesIds: []
    }
  },
  created() {
    this.initTableColumns()
    this.loadDictTypeList()
  },
  methods: {
    handleCheckAllChange(val) {
      // 根据当前实际选中状态决定是全选还是取消全选
      const isAllSelected = this.checkedDictTypesIds.length === this.dictTypeList.length;
      if (isAllSelected) {
        // 已全选，取消全选
        this.checkedDictTypesIds = [];
        this.checkAll = false;
        this.selectedDictTypes = [];
      } else {
        // 未全选，执行全选
        this.checkedDictTypesIds = this.dictTypeList.map(item => item.dictName);
        this.checkAll = true;
        this.selectedDictTypes = [...this.dictTypeList];
      }
      // 重置 indeterminate 状态
      this.isIndeterminate = false;
    },
    handleDictTypeSelectionChange(checkedIds) {
      // 更新选中的字典类型列表
      this.selectedDictTypes = this.dictTypeList.filter(item => checkedIds.includes(item.dictName));
      // 部分选中时 checkAll 为 true，isIndeterminate 为 true 显示半选状态
      this.checkAll = checkedIds.length > 0;
      this.isIndeterminate = checkedIds.length > 0 && checkedIds.length < this.dictTypeList.length;
    },
    initTableColumns() {
      this.tableColumns = [
        {
          prop: 'dictLabel',
          label: this.$t('dictManagement.dictLabel'),
          align: 'center'
        },
        {
          prop: 'dictValue',
          label: this.$t('dictManagement.dictValue'),
          align: 'center'
        },
        {
          prop: 'sort',
          label: this.$t('dictManagement.sort'),
          align: 'center'
        }
      ]
    },
    // 字典类型相关方法
    loadDictTypeList() {
      this.dictTypeLoading = true
      dictApi.getDictTypeList({
        page: 1,
        limit: 100,
        dictName: this.search
      }, ({ data }) => {
        if (data.code === 0) {
          this.dictTypeList = data.data.list
          if (this.dictTypeList.length > 0) {
            this.selectedDictType = this.dictTypeList[0]
            this.loadDictDataList(this.dictTypeList[0].id)
          }
        }
        this.dictTypeLoading = false
      })
    },
    handleDictTypeRowClick(row) {
      this.selectedDictType = row
      this.loadDictDataList(row.id)
    },
    showAddDictTypeDialog() {
      this.dictTypeDialogTitle = this.$t('dictManagement.addDictType')
      this.dictTypeForm = {
        id: null,
        dictName: '',
        dictType: ''
      }
      this.dictTypeDialogVisible = true
    },
    editDictType(row) {
      this.dictTypeDialogTitle = this.$t('dictManagement.editDictType')
      this.dictTypeForm = { ...row }
      this.dictTypeDialogVisible = true
    },
    saveDictType(formData) {
      const api = formData.id ? dictApi.updateDictType : dictApi.addDictType
      api(formData, ({ data }) => {
        if (data.code === 0) {
          this.$message.success(this.$t('dictManagement.saveSuccess'))
          this.dictTypeDialogVisible = false
          this.loadDictTypeList()
        }
      })
    },
    batchDeleteDictType() {
      if (this.selectedDictTypes.length === 0) {
        this.$message.warning(this.$t('dictManagement.selectDictTypeToDelete'))
        return
      }

      this.$confirm(this.$t('dictManagement.confirmDeleteDictType'), this.$t('dictManagement.confirm'), {
        confirmButtonText: this.$t('dictManagement.confirm'),
        cancelButtonText: this.$t('dictManagement.cancel'),
        type: 'warning'
      }).then(() => {
        const ids = this.selectedDictTypes.map(item => item.id)
        dictApi.deleteDictType(ids, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t('dictManagement.deleteSuccess'))
            this.loadDictTypeList()
          }
        })
      })
    },

    // 字典数据相关方法
    loadDictDataList(dictTypeId) {
      if (!dictTypeId) return
      this.dictDataLoading = true
      dictApi.getDictDataList({
        dictTypeId,
        page: this.currentPage,
        limit: this.pageSize,
        dictLabel: this.search,
        dictValue: ''
      }, ({ data }) => {
        if (data.code === 0) {
          this.dictDataList = data.data.list.map(item => ({
            ...item,
            selected: false
          }))
          this.total = data.data.total
        } else {
          this.$message.error(data.msg || this.$t('dictManagement.getDictDataFailed'))
        }
        this.dictDataLoading = false
      })
    },
    selectAllDictData() {
      this.isAllDictDataSelected = !this.isAllDictDataSelected
      this.dictDataList.forEach(row => {
        row.selected = this.isAllDictDataSelected
      })
    },
    showAddDictDataDialog() {
      if (!this.selectedDictType) {
        this.$message.warning(this.$t('dictManagement.selectDictTypeFirst'))
        return
      }
      this.dictDataDialogTitle = this.$t('dictManagement.addDictData')
      this.dictDataForm = {
        id: null,
        dictTypeId: this.selectedDictType.id,
        dictLabel: '',
        dictValue: '',
        sort: 0
      }
      this.dictDataDialogVisible = true
    },
    editDictData(row) {
      this.dictDataDialogTitle = this.$t('dictManagement.editDictData')
      this.dictDataForm = { ...row }
      this.dictDataDialogVisible = true
    },
    saveDictData(formData) {
      const api = formData.id ? dictApi.updateDictData : dictApi.addDictData
      api(formData, ({ data }) => {
        if (data.code === 0) {
          this.$message.success(this.$t('dictManagement.saveSuccess'))
          this.dictDataDialogVisible = false
          this.loadDictDataList(formData.dictTypeId)
        }
      })
    },
    deleteDictData(row) {
      this.$confirm(this.$t('dictManagement.confirmDeleteDictData'), this.$t('dictManagement.confirm'), {
        confirmButtonText: this.$t('dictManagement.confirm'),
        cancelButtonText: this.$t('dictManagement.cancel'),
        type: 'warning'
      }).then(() => {
        dictApi.deleteDictData([row.id], ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t('dictManagement.deleteSuccess'))
            this.loadDictDataList(row.dictTypeId)
          }
        })
      })
    },
    batchDeleteDictData() {
      const selectedRows = this.dictDataList.filter(row => row.selected)
      if (selectedRows.length === 0) {
        this.$message.warning(this.$t('dictManagement.selectDictDataToDelete'))
        return
      }

      this.$confirm(this.$t('dictManagement.confirmBatchDeleteDictData', { count: selectedRows.length }), this.$t('dictManagement.confirm'), {
        confirmButtonText: this.$t('dictManagement.confirm'),
        cancelButtonText: this.$t('dictManagement.cancel'),
        type: 'warning'
      }).then(() => {
        const ids = selectedRows.map(item => item.id)
        dictApi.deleteDictData(ids, ({ data }) => {
          if (data.code === 0) {
            this.$message.success(this.$t('dictManagement.deleteSuccess'))
            this.loadDictDataList(this.selectedDictType.id)
          }
        })
      })
    },
    handleSearch() {
      if (!this.selectedDictType) {
        this.$message.warning(this.$t('dictManagement.selectDictTypeFirst'))
        return
      }
      this.currentPage = 1
      this.loadDictDataList(this.selectedDictType.id)
    },
    handlePageSizeChange(val) {
      this.pageSize = val
      this.currentPage = 1
      this.loadDictDataList(this.selectedDictType?.id)
    },
    goToPage(page) {
      if (page !== this.currentPage) {
        this.currentPage = page
        this.loadDictDataList(this.selectedDictType?.id)
      }
    }
  }
}
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

.content-panel {
  flex: 1;
  gap: 16px;
  padding: 0 20px;
  display: flex;
  min-height: 0;
}

.dict-type-panel {
  width: 340px;
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
  box-shadow: 0 0 12px rgba(74, 124, 253, 0.12);
  border-radius: 6px;
  .dict-type-checkbox {
    flex: 1;
    padding: 16px 10px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    .dict-type-all {
      margin-left: 10px;
    }
    ::v-deep .el-checkbox-group {
      width: 100%;
      gap: 10px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      .el-checkbox__label {
        display: none;
      }
    }
    .dict-type-item {
      padding: 0 10px;
      padding-right: 0;
      width: 100%;
      display: flex;
      align-items: center;
      cursor: pointer;
      box-sizing: border-box;
      border-radius: 4px;
      &:hover {
       background: #4998ff;
        .dict-type-name, .dict-type-edit-btn {
          color: #ffffff;
        }
      }
      .dict-type-item-content {
        flex: 1;
        padding: 8px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .dict-type-name {
        margin-left: 10px;
        font-size: 14px;
      }
      .dict-type-edit-btn {
        color: #303133;
        padding: 6px 10px;
        font-size: 14px;
      }
    }
    .dict-type-active {
      background-color: #4998ff;
      .dict-type-name, .dict-type-edit-btn {
        color: #ffffff;
      }
    }
  }
}

.dict-type-header {
  display: flex;
  padding: 10px 16px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  .dict-type-title {
    margin: 0;
    font-weight: 500;
  }
  > div {
    .el-button {
      border-radius: 6px;
      padding: 7px 8px;
    }
  }
}

.content-area {
  flex: 1;
  height: 100%;
  min-width: 600px;
  display: flex;
  flex-direction: column;
  padding: 0 0 20px;
  box-sizing: border-box;
}

.main-card {
  background: white;
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  border-radius: 15px;
  overflow: hidden;

  ::v-deep .el-card__body {
    padding: 0;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }
}

.operation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  flex-shrink: 0;
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

.ctrl_btn {
  display: flex;
}

:deep(.el-table .el-button--text) {
  color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5;
}

:deep(.el-checkbox__inner) {
  background-color: #ffffff !important;
  border-color: #cccccc !important;
}

:deep(.el-checkbox__inner:hover) {
  border-color: #cccccc !important;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #5f70f3 !important;
  border-color: #5f70f3 !important;
}
</style>
