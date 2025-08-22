<template>
    <div class="welcome">
        <HeaderBar />

        <div class="operation-bar">
            <h2 class="page-title">Parameter Management</h2>
            <div class="right-operations">
                <el-input placeholder="Enter parameter code or remark to search" v-model="searchCode" class="search-input"
                    @keyup.enter.native="handleSearch" clearable />
                <el-button class="btn-search" @click="handleSearch">Search</el-button>
            </div>
        </div>

        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="params-card" shadow="never">
                        <el-table ref="paramsTable" :data="paramsList" class="transparent-table" v-loading="loading"
                            element-loading-text="Loading..." element-loading-spinner="el-icon-loading"
                            element-loading-background="rgba(255, 255, 255, 0.7)"
                            :header-cell-class-name="headerCellClassName">
                            <el-table-column label="Select" align="center" width="120">
                                <template slot-scope="scope">
                                    <el-checkbox v-model="scope.row.selected"></el-checkbox>
                                </template>
                            </el-table-column>
                            <el-table-column label="Parameter Code" prop="paramCode" align="center"></el-table-column>
                            <el-table-column label="Parameter Value" prop="paramValue" align="center" show-overflow-tooltip>
                                <template slot-scope="scope">
                                    <div v-if="isSensitiveParam(scope.row.paramCode)">
                                        <span v-if="!scope.row.showValue">{{ maskSensitiveValue(scope.row.paramValue)
                                        }}</span>
                                        <span v-else>{{ scope.row.paramValue }}</span>
                                        <el-button size="mini" type="text" @click="toggleSensitiveValue(scope.row)">
                                            {{ scope.row.showValue ? 'Hide' : 'View' }}
                                        </el-button>
                                    </div>
                                    <span v-else>{{ scope.row.paramValue }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="Remark" prop="remark" align="center"></el-table-column>
                            <el-table-column label="Actions" align="center">
                                <template slot-scope="scope">
                                    <el-button size="mini" type="text" @click="editParam(scope.row)">Edit</el-button>
                                    <el-button size="mini" type="text" @click="deleteParam(scope.row)">Delete</el-button>
                                </template>
                            </el-table-column>
                        </el-table>

                        <div class="table_bottom">
                            <div class="ctrl_btn">
                                <el-button size="mini" type="primary" class="select-all-btn" @click="handleSelectAll">
                                    {{ isAllSelected ? 'Deselect All' : 'Select All' }}
                                </el-button>
                                <el-button size="mini" type="success" @click="showAddDialog">Add</el-button>
                                <el-button size="mini" type="danger" icon="el-icon-delete"
                                    @click="deleteSelectedParams">Delete</el-button>
                            </div>
                            <div class="custom-pagination">
                                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                                    <el-option v-for="item in pageSizeOptions" :key="item" :label="`${item} items/page`"
                                        :value="item">
                                    </el-option>
                                </el-select>
                                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">
                                    First
                                </button>
                                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">
                                    Previous
                                </button>
                                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                                    :class="{ active: page === currentPage }" @click="goToPage(page)">
                                    {{ page }}
                                </button>
                                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">
                                    Next
                                </button>
                                <span class="total-text">Total {{ total }} records</span>
                            </div>
                        </div>
                    </el-card>
                </div>
            </div>
        </div>

        <!-- 新增/编辑参数对话框 -->
        <param-dialog :title="dialogTitle" :visible.sync="dialogVisible" :form="paramForm" @submit="handleSubmit"
            @cancel="dialogVisible = false" />
        <el-footer>
            <version-footer />
        </el-footer>
    </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import ParamDialog from "@/components/ParamDialog.vue";
import VersionFooter from "@/components/VersionFooter.vue";
export default {
    components: { HeaderBar, ParamDialog, VersionFooter },
    data() {
        return {
            searchCode: "",
            paramsList: [],
            currentPage: 1,
            loading: false,
            pageSize: 10,
            pageSizeOptions: [10, 20, 50, 100],
            total: 0,
            dialogVisible: false,
            dialogTitle: "Add Parameter",
            isAllSelected: false,
            sensitive_keys: ["api_key", "personal_access_token", "access_token", "token", "secret", "access_key_secret", "secret_key"],
            paramForm: {
                id: null,
                paramCode: "",
                paramValue: "",
                remark: ""
            },
        };
    },
    created() {
        this.fetchParams();

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
        },
    },
    methods: {
        handlePageSizeChange(val) {
            this.pageSize = val;
            this.currentPage = 1;
            this.fetchParams();
        },
        fetchParams() {
            this.loading = true;
            Api.admin.getParamsList(
                {
                    page: this.currentPage,
                    limit: this.pageSize,
                    paramCode: this.searchCode,
                },
                ({ data }) => {
                    this.loading = false;
                    if (data.code === 0) {
                        this.paramsList = data.data.list.map(item => ({
                            ...item,
                            selected: false,
                            showValue: false
                        }));
                        this.total = data.data.total;
                    } else {
                        this.$message.error({
                            message: data.msg || 'Failed to get parameter list',
                            showClose: true
                        });
                    }
                }
            );
        },
        handleSearch() {
            this.currentPage = 1;
            this.fetchParams();
        },
        handleSelectAll() {
            this.isAllSelected = !this.isAllSelected;
            this.paramsList.forEach(row => {
                row.selected = this.isAllSelected;
            });
        },
        showAddDialog() {
            this.dialogTitle = "Add Parameter";
            this.paramForm = {
                id: null,
                paramCode: "",
                paramValue: "",
                remark: ""
            };
            this.dialogVisible = true;
        },
        editParam(row) {
            this.dialogTitle = "Edit Parameter";
            this.paramForm = { ...row };
            this.dialogVisible = true;
        },

        handleSubmit({ form, done }) {
            if (form.id) {
                // 编辑
                Api.admin.updateParam(form, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: "Update successful",
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchParams();
                    }
                    done && done();
                });
            } else {
                // 新增
                Api.admin.addParam(form, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: "Added successfully",
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchParams();
                    }
                    done && done();
                });
            }
        },

        deleteSelectedParams() {
            const selectedRows = this.paramsList.filter(row => row.selected);
            if (selectedRows.length === 0) {
                this.$message.warning({
                    message: "Please select parameters to delete",
                    showClose: true
                });
                return;
            }
            this.deleteParam(selectedRows);
        },
        deleteParam(row) {
            // 处理单个参数或参数数组
            const params = Array.isArray(row) ? row : [row];

            if (Array.isArray(row) && row.length === 0) {
                this.$message.warning({
                    message: "Please select parameters to delete",
                    showClose: true
                });
                return;
            }

            const paramCount = params.length;
            this.$confirm(`Are you sure you want to delete ${paramCount} selected parameter(s)?`, 'Warning', {
                confirmButtonText: 'Confirm',
                cancelButtonText: 'Cancel',
                type: 'warning',
                distinguishCancelAndClose: true
            }).then(() => {
                const ids = params.map(param => param.id);
                if (ids.some(id => isNaN(id))) {
                    this.$message.error({
                        message: 'Invalid parameter ID exists',
                        showClose: true
                    });
                    return;
                }

                Api.admin.deleteParam(ids, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: `Successfully deleted ${paramCount} parameter(s)`,
                            showClose: true
                        });
                        this.fetchParams();
                    } else {
                        this.$message.error({
                            message: data.msg || 'Delete failed, please try again',
                            showClose: true
                        });
                    }
                });
            }).catch(action => {
                if (action === 'cancel') {
                    this.$message({
                        type: 'info',
                        message: 'Delete operation cancelled',
                        duration: 1000
                    });
                } else {
                    this.$message({
                        type: 'info',
                        message: 'Operation closed',
                        duration: 1000
                    });
                }
            });
        },
        headerCellClassName({ columnIndex }) {
            if (columnIndex === 0) {
                return "custom-selection-header";
            }
            return "";
        },
        goFirst() {
            this.currentPage = 1;
            this.fetchParams();
        },
        goPrev() {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.fetchParams();
            }
        },
        goNext() {
            if (this.currentPage < this.pageCount) {
                this.currentPage++;
                this.fetchParams();
            }
        },
        goToPage(page) {
            this.currentPage = page;
            this.fetchParams();
        },
        isSensitiveParam(paramCode) {
            return this.sensitive_keys.some(key => paramCode.toLowerCase().includes(key.toLowerCase()));
        },
        maskSensitiveValue(value) {
            if (!value) return '';
            if (value.length <= 8) return '****';
            return value.substring(0, 4) + '****' + value.substring(value.length - 4);
        },
        toggleSensitiveValue(row) {
            this.$set(row, 'showValue', !row.showValue);
        },
    },
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

.right-operations {
    display: flex;
    gap: 10px;
    margin-left: auto;
}

.search-input {
    width: 240px;
}

.btn-search {
    background: linear-gradient(135deg, #6b8cff, #a966ff);
    border: none;
    color: white;
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

.content-area {
    flex: 1;
    height: 100%;
    min-width: 600px;
    overflow: auto;
    background-color: white;
    display: flex;
    flex-direction: column;
}

.params-card {
    background: white;
    flex: 1;
    display: flex;
    flex-direction: column;
    border: none;
    box-shadow: none;
    overflow: hidden;

    ::v-deep .el-card__body {
        padding: 15px;
        display: flex;
        flex-direction: column;
        flex: 1;
        overflow: hidden;
    }
}

.table_bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    padding-bottom: 10px;
}

.ctrl_btn {
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

    .el-button--danger {
        background: #fd5b63;
        color: white;
    }
}

.custom-pagination {
    display: flex;
    align-items: center;
    gap: 10px;

    .el-select {
        margin-right: 8px;
    }

    .pagination-btn:first-child,
    .pagination-btn:nth-child(2),
    .pagination-btn:nth-last-child(2),
    .pagination-btn:nth-child(3) {
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

    .pagination-btn:not(:first-child):not(:nth-child(3)):not(:nth-child(2)):not(:nth-last-child(2)) {
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

:deep(.transparent-table) {
    background: white;
    flex: 1;
    width: 100%;
    display: flex;
    flex-direction: column;

    .el-table__body-wrapper {
        flex: 1;
        overflow-y: auto;
        max-height: none !important;
    }

    .el-table__header-wrapper {
        flex-shrink: 0;
    }

    .el-table__header th {
        background: white !important;
        color: black;
    }

    &::before {
        display: none;
    }

    .el-table__body tr {
        background-color: white;

        td {
            border-top: 1px solid rgba(0, 0, 0, 0.04);
            border-bottom: 1px solid rgba(0, 0, 0, 0.04);
        }
    }
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

@media (min-width: 1144px) {
    .table_bottom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 40px;
    }

    :deep(.transparent-table) {
        .el-table__body tr {
            td {
                padding-top: 16px;
                padding-bottom: 16px;
            }

            &+tr {
                margin-top: 10px;
            }
        }
    }
}

:deep(.el-table .el-button--text) {
    color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
    color: #5a64b5;
}

.el-button--success {
    background: #5bc98c;
    color: white;
}

:deep(.el-table .cell) {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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

:deep(.el-table) {
    .el-table__body-wrapper {
        transition: height 0.3s ease;
    }
}

.el-table {
    --table-max-height: calc(100vh - 40vh);
    max-height: var(--table-max-height);

    .el-table__body-wrapper {
        max-height: calc(var(--table-max-height) - 40px);
    }
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
</style>
