<template>
    <div class="welcome">
        <HeaderBar />

        <div class="operation-bar">
            <h2 class="page-title">字典管理</h2>
            <div class="action-group">
                <div class="search-group">
                    <el-input placeholder="请输入字典值标签查询" v-model="search" class="search-input" clearable
                        @keyup.enter.native="handleSearch" style="width: 240px" />
                    <el-button class="btn-search" @click="handleSearch">
                        搜索
                    </el-button>
                </div>
            </div>
        </div>

        <!-- 主体内容 -->
        <div class="main-wrapper">
            <div class="content-panel">
                <!-- 左侧字典类型列表 -->
                <div class="dict-type-panel">
                    <div class="dict-type-header">
                        <el-button type="success" size="mini" @click="showAddDictTypeDialog">新增字典类型</el-button>
                        <el-button type="danger" size="mini" @click="batchDeleteDictType"
                            :disabled="selectedDictTypes.length === 0">
                            批量删除字典类型
                        </el-button>
                    </div>
                    <el-table ref="dictTypeTable" :data="dictTypeList" style="width: 100%" v-loading="dictTypeLoading"
                        element-loading-text="拼命加载中" element-loading-spinner="el-icon-loading"
                        element-loading-background="rgba(255, 255, 255, 0.7)" @row-click="handleDictTypeRowClick"
                        @selection-change="handleDictTypeSelectionChange" :row-class-name="tableRowClassName"
                        class="dict-type-table">
                        <el-table-column type="selection" width="55" align="center"></el-table-column>
                        <el-table-column label="字典类型名称" prop="dictName" align="center"></el-table-column>
                        <el-table-column label="操作" width="100" align="center">
                            <template slot-scope="scope">
                                <el-button type="text" size="mini" @click.stop="editDictType(scope.row)">编辑</el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </div>

                <!-- 右侧字典数据列表 -->
                <div class="content-area">
                    <el-card class="dict-data-card" shadow="never">
                        <el-table ref="dictDataTable" :data="dictDataList" style="width: 100%"
                            v-loading="dictDataLoading" element-loading-text="拼命加载中"
                            element-loading-spinner="el-icon-loading"
                            element-loading-background="rgba(255, 255, 255, 0.7)"
                            class="data-table"
                            header-row-class-name="table-header">
                            <el-table-column label="选择" align="center" width="55">
                                <template slot-scope="scope">
                                    <el-checkbox v-model="scope.row.selected"></el-checkbox>
                                </template>
                            </el-table-column>
                            <el-table-column label="字典标签" prop="dictLabel" align="center"></el-table-column>
                            <el-table-column label="字典值" prop="dictValue" align="center"></el-table-column>
                            <el-table-column label="排序" prop="sort" align="center"></el-table-column>
                            <el-table-column label="操作" align="center" width="180px">
                                <template slot-scope="scope">
                                    <el-button type="text" size="mini" @click="editDictData(scope.row)"
                                        class="edit-btn">
                                        修改
                                    </el-button>
                                    <el-button type="text" size="mini" @click="deleteDictData(scope.row)"
                                        class="delete-btn">
                                        删除
                                    </el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                        <div class="table-footer">
                            <div class="batch-actions">
                                <el-button size="mini" type="primary" @click="selectAllDictData">
                                    {{ isAllDictDataSelected ? '取消全选' : '全选' }}
                                </el-button>
                                <el-button type="success" size="mini" @click="showAddDictDataDialog" class="add-btn">
                                    新增字典数据
                                </el-button>
                                <el-button size="mini" type="danger" icon="el-icon-delete" @click="batchDeleteDictData">
                                    批量删除字典数据
                                </el-button>
                            </div>
                            <div class="custom-pagination">
                                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                                    <el-option v-for="item in pageSizeOptions" :key="item" :label="`${item}条/页`"
                                        :value="item">
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
export default {
    name: 'DictManagement',
    components: {
        HeaderBar,
        DictTypeDialog,
        DictDataDialog,
        VersionFooter
    },
    data() {
        return {
            // 字典类型相关
            dictTypeList: [],
            dictTypeLoading: false,
            selectedDictType: null,
            selectedDictTypes: [],  // 恢复多选数组
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
            // 添加分页相关数据
            pageSizeOptions: [10, 20, 50, 100],
            currentPage: 1,
            pageSize: 10,
            total: 0
        }
    },
    created() {
        this.loadDictTypeList()
    },
    methods: {
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
                        this.$nextTick(() => {
                            this.$refs.dictTypeTable.setCurrentRow(this.dictTypeList[0])
                        })
                    }
                }
                this.dictTypeLoading = false
            })
        },
        handleDictTypeRowClick(row) {
            this.selectedDictType = row
            this.loadDictDataList(row.id)
            this.$refs.dictTypeTable.setCurrentRow(row)
        },
        handleDictTypeSelectionChange(val) {
            this.selectedDictTypes = val
        },
        tableRowClassName({ row }) {
            return row === this.selectedDictType ? 'current-row' : ''
        },
        showAddDictTypeDialog() {
            this.dictTypeDialogTitle = '新增字典类型'
            this.dictTypeForm = {
                id: null,
                dictName: '',
                dictType: ''
            }
            this.dictTypeDialogVisible = true
        },
        editDictType(row) {
            this.dictTypeDialogTitle = '编辑字典类型'
            this.dictTypeForm = { ...row }
            this.dictTypeDialogVisible = true
        },
        saveDictType(formData) {
            const api = formData.id ? dictApi.updateDictType : dictApi.addDictType
            api(formData, ({ data }) => {
                if (data.code === 0) {
                    this.$message.success('保存成功')
                    this.dictTypeDialogVisible = false
                    this.loadDictTypeList()
                }
            })
        },
        batchDeleteDictType() {
            if (this.selectedDictTypes.length === 0) {
                this.$message.warning('请选择要删除的字典类型')
                return
            }

            this.$confirm('确定要删除选中的字典类型吗?', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                const ids = this.selectedDictTypes.map(item => item.id)
                dictApi.deleteDictType(ids, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success('删除成功')
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
                    this.$message.error(data.msg || '获取字典数据失败')
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
                this.$message.warning('请先选择字典类型')
                return
            }
            this.dictDataDialogTitle = '新增字典数据'
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
            this.dictDataDialogTitle = '编辑字典数据'
            this.dictDataForm = { ...row }
            this.dictDataDialogVisible = true
        },
        saveDictData(formData) {
            const api = formData.id ? dictApi.updateDictData : dictApi.addDictData
            api(formData, ({ data }) => {
                if (data.code === 0) {
                    this.$message.success('保存成功')
                    this.dictDataDialogVisible = false
                    this.loadDictDataList(formData.dictTypeId)
                }
            })
        },
        deleteDictData(row) {
            this.$confirm('确定要删除该字典数据吗?', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                dictApi.deleteDictData([row.id], ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success('删除成功')
                        this.loadDictDataList(row.dictTypeId)
                    }
                })
            })
        },
        batchDeleteDictData() {
            const selectedRows = this.dictDataList.filter(row => row.selected)
            if (selectedRows.length === 0) {
                this.$message.warning('请选择要删除的字典数据')
                return
            }

            this.$confirm(`确定要删除选中的${selectedRows.length}个字典数据吗?`, '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                const ids = selectedRows.map(item => item.id)
                dictApi.deleteDictData(ids, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success('删除成功')
                        this.loadDictDataList(this.selectedDictType.id)
                    }
                })
            })
        },
        handleSearch() {
            if (!this.selectedDictType) {
                this.$message.warning('请先选择字典类型')
                return
            }
            this.currentPage = 1
            this.loadDictDataList(this.selectedDictType.id)
        },
        // 添加分页相关方法
        handlePageSizeChange(val) {
            this.pageSize = val;
            this.currentPage = 1;
            this.loadDictDataList(this.selectedDictType?.id);
        },
        goFirst() {
            this.currentPage = 1;
            this.loadDictDataList(this.selectedDictType?.id);
        },
        goPrev() {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadDictDataList(this.selectedDictType?.id);
            }
        },
        goNext() {
            if (this.currentPage < this.pageCount) {
                this.currentPage++;
                this.loadDictDataList(this.selectedDictType?.id);
            }
        },
        goToPage(page) {
            this.currentPage = page;
            this.loadDictDataList(this.selectedDictType?.id);
        }
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

.action-group {
    display: flex;
    align-items: center;
    gap: 16px;
}

.search-group {
    display: flex;
    gap: 10px;
}

.search-input {
    width: 240px;
}

.btn-search {
    background: linear-gradient(135deg, #6b8cff, #a966ff);
    border: none;
    color: white;
}

.btn-search:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

:deep(.search-input .el-input__inner) {
    border-radius: 4px;
    border: 1px solid #DCDFE6;
    background-color: white;
    transition: border-color 0.2s;
}

:deep(.search-input .el-input__inner:focus) {
    border-color: #6b8cff;
    outline: none;
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

.dict-type-panel {
    width: 300px;
    background: white;
    border-right: 1px solid #ebeef5;
    display: flex;
    flex-direction: column;
}

.dict-type-header {
    padding: 16px;
    border-bottom: 1px solid #ebeef5;
    display: flex;
    gap: 8px;
}

.dict-type-table {
    flex: 1;
    overflow-y: auto;
}

.content-area {
    flex: 1;
    padding: 24px;
    height: 100%;
    min-width: 600px;
    overflow: hidden;
    background-color: white;
    display: flex;
    flex-direction: column;
}

.dict-data-card {
    background: white;
    flex: 1;
    display: flex;
    flex-direction: column;
    border: none;
    box-shadow: none;
    overflow: hidden;
}

.data-table {
    border-radius: 6px;
    overflow-y: auto;
    background-color: transparent !important;
    --table-max-height: calc(100vh - 40vh);
    max-height: var(--table-max-height);

    :deep(.el-table__body-wrapper) {
        max-height: calc(var(--table-max-height) - 40px);
    }

    :deep(.el-table__body) {
        tr:last-child td {
            border-bottom: none;
        }
    }
}

:deep(.el-table) {
    &::before {
        display: none;
    }

    &::after {
        display: none;
    }
}

.table-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 0;
    width: 100%;
    flex-shrink: 0;
    min-height: 60px;
    background: white;
    margin-top: 10px;
}

.batch-actions {
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

    .el-button--success {
        background: #5bc98c;
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
    gap: 8px;

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

.edit-btn,
.delete-btn {
    margin: 0 8px;
    color: #7079aa !important;
    font-size: 12px;
    padding: 7px 12px;
    height: 32px;
    line-height: 1;
    border-radius: 4px;
    transition: all 0.3s ease;

    &:hover {
        color: #5a64b5 !important;
        transform: translateY(-1px);
    }
}

:deep(.dict-type-header .el-button) {
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

    &.el-button--success {
        background: #5bc98c;
        color: white;
    }

    &.el-button--danger {
        background: #fd5b63;
        color: white;
    }
}

:deep(.el-table .cell) {
    padding-left: 10px;
    padding-right: 10px;
}

:deep(.el-loading-mask) {
    background-color: rgba(255, 255, 255, 0.6) !important;
    backdrop-filter: blur(2px);
}

:deep(.el-loading-spinner .circular) {
    width: 28px;
    height: 28px;
}

:deep(.el-loading-spinner .path) {
    stroke: #6b8cff;
}

:deep(.el-loading-text) {
    color: #6b8cff !important;
    font-size: 14px;
    margin-top: 8px;
}

:deep(.dict-type-table .el-table__row) {
    cursor: pointer;
}

:deep(.dict-type-table .el-table__row.current-row) {
    background-color: #5778ff !important;
    color: white;
}

:deep(.dict-type-table .el-table__row.current-row .el-button--text) {
    color: white !important;
}

:deep(.dict-type-table .el-table__row:hover) {
    background-color: #f5f7fa;
}

:deep(.dict-type-table .el-table__row.current-row:hover) {
    background-color: #5778ff !important;
}

:deep(.dict-type-table .el-table__row td) {
    background-color: transparent !important;
}

:deep(.el-table thead) {
    color: #000000;
}

:deep(.el-card__body) {
    padding: 15px;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
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
</style>