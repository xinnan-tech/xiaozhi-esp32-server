<template>
    <div class="welcome">
        <HeaderBar />

        <div class="operation-bar">
            <h2 class="page-title">参数管理</h2>
            <div class="right-operations">
                <el-input placeholder="请输入参数编码查询" v-model="searchCode" class="search-input"
                    @keyup.enter.native="handleSearch" />
                <el-button class="btn-search" @click="handleSearch">搜索</el-button>
                <el-button type="primary" @click="showAddDialog">新增参数</el-button>
            </div>
        </div>

        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="params-card" shadow="never">
                        <el-table ref="paramsTable" :data="paramsList" class="transparent-table"
                            :header-cell-class-name="headerCellClassName">
                            <el-table-column label="选择" type="selection" align="center" width="120"></el-table-column>
                            <el-table-column label="参数编码" prop="paramCode" align="center"></el-table-column>
                            <el-table-column label="参数值" prop="paramValue" align="center"></el-table-column>
                            <el-table-column label="备注" prop="remark" align="center"></el-table-column>
                            <el-table-column label="操作" align="center">
                                <template slot-scope="scope">
                                    <el-button size="mini" type="text" @click="editParam(scope.row)">编辑</el-button>
                                    <el-button size="mini" type="text" @click="deleteParam(scope.row)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>

                        <div class="table_bottom">
                            <div class="ctrl_btn">
                                <el-button size="mini" type="primary" class="select-all-btn"
                                    @click="handleSelectAll">全选</el-button>
                                <el-button size="mini" type="danger" icon="el-icon-delete"
                                    @click="batchDelete">删除</el-button>
                            </div>
                            <div class="custom-pagination">
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

        <!-- 新增/编辑参数对话框 -->
        <el-dialog :title="dialogTitle" :visible.sync="dialogVisible" width="500px">
            <el-form :model="paramForm" :rules="rules" ref="paramForm" label-width="100px">
                <el-form-item label="参数编码" prop="paramCode">
                    <el-input v-model="paramForm.paramCode" placeholder="请输入参数编码"></el-input>
                </el-form-item>
                <el-form-item label="参数值" prop="paramValue">
                    <el-input v-model="paramForm.paramValue" placeholder="请输入参数值"></el-input>
                </el-form-item>
                <el-form-item label="备注" prop="remark">
                    <el-input type="textarea" v-model="paramForm.remark" placeholder="请输入备注"></el-input>
                </el-form-item>
            </el-form>
            <div slot="footer" class="dialog-footer">
                <el-button @click="dialogVisible = false">取 消</el-button>
                <el-button type="primary" @click="submitForm">确 定</el-button>
            </div>
        </el-dialog>

        <div class="copyright">©2025 xiaozhi-esp32-server</div>
    </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";

export default {
    components: { HeaderBar },
    data() {
        return {
            searchCode: "",
            paramsList: [],
            currentPage: 1,
            pageSize: 5,
            total: 0,
            dialogVisible: false,
            dialogTitle: "新增参数",
            paramForm: {
                id: null,
                paramCode: "",
                paramValue: "",
                remark: ""
            },
            rules: {
                paramCode: [
                    { required: true, message: "请输入参数编码", trigger: "blur" }
                ],
                paramValue: [
                    { required: true, message: "请输入参数值", trigger: "blur" }
                ]
            }
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
        fetchParams() {
            Api.admin.getParamsList(
                {
                    page: this.currentPage,
                    limit: this.pageSize,
                    paramCode: this.searchCode,
                },
                ({ data }) => {
                    if (data.code === 0) {
                        this.paramsList = data.data.list;
                        this.total = data.data.total;
                    }
                }
            );
        },
        handleSearch() {
            this.currentPage = 1;
            this.fetchParams();
        },
        handleSelectAll() {
            this.$refs.paramsTable.toggleAllSelection();
        },
        showAddDialog() {
            this.dialogTitle = "新增参数";
            this.paramForm = {
                id: null,
                paramCode: "",
                paramValue: "",
                remark: ""
            };
            this.dialogVisible = true;
        },
        editParam(row) {
            this.dialogTitle = "编辑参数";
            this.paramForm = { ...row };
            this.dialogVisible = true;
        },
        submitForm() {
            this.$refs.paramForm.validate((valid) => {
                if (valid) {
                    if (this.paramForm.id) {
                        // 编辑
                        Api.admin.updateParam(this.paramForm, ({ data }) => {
                            if (data.code === 0) {
                                this.$message.success("修改成功");
                                this.dialogVisible = false;
                                this.fetchParams();
                            }
                        });
                    } else {
                        // 新增
                        Api.admin.addParam(this.paramForm, ({ data }) => {
                            if (data.code === 0) {
                                this.$message.success("新增成功");
                                this.dialogVisible = false;
                                this.fetchParams();
                            }
                        });
                    }
                }
            });
        },
        deleteParam(row) {
            this.$confirm("确定要删除该参数吗？", "警告", {
                confirmButtonText: "确定",
                cancelButtonText: "取消",
                type: "warning",
            })
                .then(() => {
                    Api.admin.deleteParam(row.id, ({ data }) => {
                        if (data.code === 0) {
                            this.$message.success("删除成功");
                            this.fetchParams();
                        }
                    });
                })
                .catch(() => { });
        },
        batchDelete() {
            const selectedParams = this.$refs.paramsTable.selection;
            if (selectedParams.length === 0) {
                this.$message.warning("请先选择需要删除的参数");
                return;
            }

            this.$confirm(`确定要删除选中的${selectedParams.length}个参数吗？`, "警告", {
                confirmButtonText: "确定",
                cancelButtonText: "取消",
                type: "warning",
            })
                .then(() => {
                    const ids = selectedParams.map(item => item.id);
                    Api.admin.batchDeleteParams(ids, ({ data }) => {
                        if (data.code === 0) {
                            this.$message.success("删除成功");
                            this.fetchParams();
                        }
                    });
                })
                .catch(() => { });
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
        }
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
}

.main-wrapper {
    margin: 5px 22px;
    border-radius: 15px;
    min-height: 600px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    position: relative;
    background: rgba(237, 242, 255, 0.5);
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
    overflow-x: auto;
    background-color: white;
}

.params-card {
    background: white;
    border: none;
    box-shadow: none;
}

.table_bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
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

.copyright {
    text-align: center;
    color: #979db1;
    font-size: 12px;
    font-weight: 400;
    margin-top: auto;
    padding: 30px 0 20px;
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
}

.custom-pagination {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 15px;

    .pagination-btn:first-child,
    .pagination-btn:nth-child(2),
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

    .pagination-btn:not(:first-child):not(:nth-child(2)):not(:nth-last-child(2)) {
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

:deep(.custom-selection-header) {
    .el-checkbox {
        display: none !important;
    }

    &::after {
        content: "选择";
        display: inline-block;
        color: black;
        font-weight: bold;
        padding-bottom: 18px;
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
</style>