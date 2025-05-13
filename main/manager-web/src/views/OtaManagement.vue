<template>
    <div class="welcome">
        <HeaderBar />

        <div class="operation-bar">
            <h2 class="page-title">固件管理</h2>
            <div class="right-operations">
                <el-input placeholder="请输入固件名称查询" v-model="searchName" class="search-input"
                    @keyup.enter.native="handleSearch" clearable />
                <el-button class="btn-search" @click="handleSearch">搜索</el-button>
            </div>
        </div>

        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="params-card" shadow="never">
                        <el-table ref="paramsTable" :data="paramsList" class="transparent-table" v-loading="loading"
                            element-loading-text="拼命加载中" element-loading-spinner="el-icon-loading"
                            element-loading-background="rgba(255, 255, 255, 0.7)"
                            :header-cell-class-name="headerCellClassName">
                            <el-table-column label="选择" align="center" width="120">
                                <template slot-scope="scope">
                                    <el-checkbox v-model="scope.row.selected"></el-checkbox>
                                </template>
                            </el-table-column>
                            <el-table-column label="固件名称" prop="firmwareName" align="center"></el-table-column>
                            <el-table-column label="固件类型" prop="type" align="center">
                                <template slot-scope="scope">
                                    {{ getFirmwareTypeName(scope.row.type) }}
                                </template>
                            </el-table-column>
                            <el-table-column label="版本号" prop="version" align="center"></el-table-column>
                            <el-table-column label="文件大小" prop="size" align="center">
                                <template slot-scope="scope">
                                    {{ formatFileSize(scope.row.size) }}
                                </template>
                            </el-table-column>
                            <el-table-column label="备注" prop="remark" align="center"
                                show-overflow-tooltip></el-table-column>
                            <el-table-column label="创建时间" prop="createDate" align="center">
                                <template slot-scope="scope">
                                    {{ formatDate(scope.row.createDate) }}
                                </template>
                            </el-table-column>
                            <el-table-column label="更新时间" prop="updateDate" align="center">
                                <template slot-scope="scope">
                                    {{ formatDate(scope.row.updateDate) }}
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" align="center">
                                <template slot-scope="scope">
                                    <el-button size="mini" type="text"
                                        @click="downloadFirmware(scope.row)">下载</el-button>
                                    <el-button size="mini" type="text" @click="editParam(scope.row)">编辑</el-button>
                                    <el-button size="mini" type="text" @click="deleteParam(scope.row)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>

                        <div class="table_bottom">
                            <div class="ctrl_btn">
                                <el-button size="mini" type="primary" class="select-all-btn" @click="handleSelectAll">
                                    {{ isAllSelected ? '取消全选' : '全选' }}
                                </el-button>
                                <el-button size="mini" type="success" @click="showAddDialog"
                                    style="background: #5bc98c;border: None;">新增</el-button>
                                <el-button size="mini" type="danger" icon="el-icon-delete"
                                    @click="deleteSelectedParams">删除</el-button>
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

        <!-- 新增/编辑固件对话框 -->
        <firmware-dialog :title="dialogTitle" :visible.sync="dialogVisible" :form="firmwareForm"
            :firmware-types="firmwareTypes" @submit="handleSubmit" @cancel="dialogVisible = false" />
        <el-footer>
            <version-footer />
        </el-footer>
    </div>
</template>

<script>
import Api from "@/apis/api";
import FirmwareDialog from "@/components/FirmwareDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import { formatDate, formatFileSize } from "@/utils/format";

export default {
    components: { HeaderBar, FirmwareDialog, VersionFooter },
    data() {
        return {
            searchName: "",
            loading: false,
            paramsList: [],
            firmwareList: [],
            currentPage: 1,
            pageSize: 10,
            pageSizeOptions: [10, 20, 50, 100],
            total: 0,
            dialogVisible: false,
            dialogTitle: "新增固件",
            isAllSelected: false,
            firmwareForm: {
                id: null,
                firmwareName: "",
                type: "",
                version: "",
                size: 0,
                remark: "",
                firmwarePath: ""
            },
            firmwareTypes: [],
        };
    },
    created() {
        this.fetchFirmwareList();
        this.getFirmwareTypes();
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
            this.fetchFirmwareList();
        },
        fetchFirmwareList() {
            this.loading = true;
            const params = {
                pageNum: this.currentPage,
                pageSize: this.pageSize,
                firmwareName: this.searchName || "",
                orderField: "create_date",
                order: "desc"
            };
            Api.ota.getOtaList(params, (res) => {
                this.loading = false;
                res = res.data
                if (res.code === 0) {
                    this.firmwareList = res.data.list.map(item => ({
                        ...item,
                        selected: false
                    }));
                    this.paramsList = this.firmwareList;
                    this.total = res.data.total || 0;
                } else {
                    this.firmwareList = [];
                    this.paramsList = [];
                    this.total = 0;
                    this.$message.error({
                        message: res?.data?.msg || '获取固件列表失败',
                        showClose: true
                    });
                }
            });
        },
        handleSearch() {
            this.currentPage = 1;
            this.fetchFirmwareList();
        },
        handleSelectAll() {
            this.isAllSelected = !this.isAllSelected;
            this.firmwareList.forEach(row => {
                row.selected = this.isAllSelected;
            });
        },
        showAddDialog() {
            this.dialogTitle = "新增固件";
            // 完全重置表单数据
            this.firmwareForm = {
                id: null,
                firmwareName: "",
                type: "",
                version: "",
                size: 0,
                remark: "",
                firmwarePath: ""
            };
            this.$nextTick(() => {
                // 重置表单的校验状态
                if (this.$refs.firmwareDialog && this.$refs.firmwareDialog.$refs.form) {
                    this.$refs.firmwareDialog.$refs.form.clearValidate();
                }
            });
            this.dialogVisible = true;
        },
        editParam(row) {
            this.dialogTitle = "编辑固件";
            this.firmwareForm = { ...row };
            this.dialogVisible = true;
        },
        handleSubmit(form) {
            if (form.id) {
                // 编辑
                Api.ota.updateOta(form.id, form, (res) => {
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success({
                            message: "修改成功",
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchFirmwareList();
                    } else {
                        this.$message.error({
                            message: res.msg || "修改失败",
                            showClose: true
                        });
                    }
                });
            } else {
                // 新增
                Api.ota.saveOta(form, (res) => {
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success({
                            message: "新增成功",
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchFirmwareList();
                    } else {
                        this.$message.error({
                            message: res.msg || "新增失败",
                            showClose: true
                        });
                    }
                });
            }
        },

        deleteSelectedParams() {
            const selectedRows = this.firmwareList.filter(row => row.selected);
            if (selectedRows.length === 0) {
                this.$message.warning({
                    message: "请先选择需要删除的固件",
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
                    message: "请先选择需要删除的参数",
                    showClose: true
                });
                return;
            }

            const paramCount = params.length;
            this.$confirm(`确定要删除选中的${paramCount}个固件吗？`, '警告', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning',
                distinguishCancelAndClose: true
            }).then(() => {
                const ids = params.map(param => param.id);
                if (ids.some(id => !id)) {
                    this.$message.error({
                        message: '存在无效的参数ID',
                        showClose: true
                    });
                    return;
                }

                Api.ota.deleteOta(ids, (res) => {
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success({
                            message: `成功删除${paramCount}个固件`,
                            showClose: true
                        });
                        this.fetchFirmwareList();
                    } else {
                        this.$message.error({
                            message: res.msg || '删除失败，请重试',
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
        headerCellClassName({ columnIndex }) {
            if (columnIndex === 0) {
                return "custom-selection-header";
            }
            return "";
        },
        goFirst() {
            this.currentPage = 1;
            this.fetchFirmwareList();
        },
        goPrev() {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.fetchFirmwareList();
            }
        },
        goNext() {
            if (this.currentPage < this.pageCount) {
                this.currentPage++;
                this.fetchFirmwareList();
            }
        },
        goToPage(page) {
            this.currentPage = page;
            this.fetchFirmwareList();
        },
        downloadFirmware(firmware) {
            if (!firmware || !firmware.id) {
                this.$message.error('固件信息不完整');
                return;
            }
            // 先获取下载链接
            Api.ota.getDownloadUrl(firmware.id, (res) => {
                if (res.data.code === 0) {
                    const uuid = res.data.data;
                    const baseUrl = process.env.VUE_APP_API_BASE_URL || '';
                    window.open(`${window.location.origin}${baseUrl}/otaMag/download/${uuid}`);
                } else {
                    this.$message.error('获取下载链接失败');
                }
            });
        },
        formatDate,
        formatFileSize,
        async getFirmwareTypes() {
            try {
                const res = await Api.dict.getDictDataByType('FIRMWARE_TYPE')
                this.firmwareTypes = res.data
            } catch (error) {
                console.error('获取固件类型失败:', error)
                this.$message.error(error.message || '获取固件类型失败')
            }
        },
        getFirmwareTypeName(type) {
            const firmwareType = this.firmwareTypes.find(item => item.key === type)
            return firmwareType ? firmwareType.name : type
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
    gap: 5px;

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
}

.total-text {
    margin-left: 10px;
    color: #606266;
    font-size: 14px;
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
        font-weight: 600;
        height: 40px;
        padding: 8px 0;
        font-size: 14px;
        border-bottom: 1px solid #e4e7ed;
    }

    .el-table__body tr {
        background-color: white;

        td {
            border-top: 1px solid rgba(0, 0, 0, 0.04);
            border-bottom: 1px solid rgba(0, 0, 0, 0.04);
            padding: 8px 0;
            height: 40px;
            color: #606266;
            font-size: 14px;
        }
    }

    .el-table__row:hover>td {
        background-color: #f5f7fa !important;
    }

    &::before {
        display: none;
    }
}

:deep(.el-table .el-button--text) {
    color: #7079aa !important;
}

:deep(.el-table .el-button--text:hover) {
    color: #5a64b5 !important;
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

:deep(.el-loading-mask) {
    background-color: rgba(255, 255, 255, 0.6) !important;
    backdrop-filter: blur(2px);
}

:deep(.el-loading-spinner .path) {
    stroke: #6b8cff;
}

.el-table {
    --table-max-height: calc(100vh - 40vh);
    max-height: var(--table-max-height);

    .el-table__body-wrapper {
        max-height: calc(var(--table-max-height) - 40px);
    }
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
</style>
