<template>
    <div class="welcome">
        <HeaderBar />

        <div class="operation-bar">
            <h2 class="page-title">Voice Recognition</h2>
        </div>

        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="voice-print-card" shadow="never">
                        <el-table ref="paramsTable" :data="voicePrintList" class="transparent-table" v-loading="loading"
                            element-loading-text="Loading..." element-loading-spinner="el-icon-loading"
                            element-loading-background="rgba(255, 255, 255, 0.7)">
                            <el-table-column label="Name" prop="sourceName" align="center"></el-table-column>
                            <el-table-column label="Description" prop="introduce" align="center"></el-table-column>
                            <el-table-column label="Create Time" prop="createDate" align="center"></el-table-column>
                            <el-table-column label="Actions" align="center">
                                <template slot-scope="scope">
                                    <el-button size="mini" type="text" @click="editVoicePrint(scope.row)">Edit</el-button>
                                    <el-button size="mini" type="text"
                                        @click="deleteVoicePrint(scope.row.id)">Delete</el-button>
                                </template>
                            </el-table-column>
                        </el-table>

                        <div class="table_bottom">
                            <div class="ctrl_btn">
                                <el-button size="mini" type="success" @click="showAddDialog">Add</el-button>
                            </div>
                        </div>
                    </el-card>
                </div>
            </div>
        </div>

        <!-- Add/Edit Parameter Dialog -->
        <voice-print-dialog :title="dialogTitle" :visible.sync="dialogVisible" :agentId="agentId" :form="paramForm"
            @submit="handleSubmit" @cancel="dialogVisible = false" />
        <el-footer>
            <version-footer />
        </el-footer>
    </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import VoicePrintDialog from "@/components/VoicePrintDialog.vue";
export default {
    components: { HeaderBar, VoicePrintDialog, VersionFooter },
    data() {
        return {
            voicePrintList: [],
            loading: false,
            dialogVisible: false,
            dialogTitle: "Add Speaker",
            isAllSelected: false,
            paramForm: {
                id: null,
                audioId: '',
                sourceName: '',
                introduce: ''
            },
            agentId: "1"
        };
    },
    mounted() {
        const agentId = this.$route.query.agentId;
        if (agentId) {
            this.agentId = agentId
            this.fetchVoicePrints();
        }
    },
    methods: {
        fetchVoicePrints() {
            this.loading = true;
            Api.agent.getAgentVoicePrintList(this.agentId,
                ({ data }) => {
                    this.loading = false;
                    if (data.code === 0) {
                        this.voicePrintList = data.data.map(item => ({
                            ...item,

                        }));
                    } else {
                        this.$message.error({
                            message: data.msg || 'Failed to get voice print list',
                            showClose: true
                        });
                    }
                }
            );
        },
        showAddDialog() {
            this.dialogTitle = "Add Speaker";
            this.paramForm = {
                id: null,
                audioId: '',
                sourceName: '',
                introduce: ''
            };
            this.dialogVisible = true;
        },
        editVoicePrint(row) {
            this.dialogTitle = "Edit Speaker";
            this.paramForm = { ...row };
            this.dialogVisible = true;
        },

        handleSubmit({ form, done }) {
            if (form.id) {
                // Edit
                Api.agent.updateAgentVoicePrint(form, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: "Update successful",
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchVoicePrints();
                    }
                    done && done();
                });
            } else {
                // Add
                Api.agent.addAgentVoicePrint({
                    agentId: this.agentId,
                    audioId: form.audioId,
                    sourceName: form.sourceName,
                    introduce: form.introduce
                }, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: "Add successful",
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchVoicePrints();
                    }
                    done && done();
                });
            }
        },
        // Delete button
        deleteVoicePrint(id) {
            this.$confirm(`Are you sure you want to delete this voice print?`, 'Warning', {
                confirmButtonText: 'Confirm',
                cancelButtonText: 'Cancel',
                type: 'warning',
                distinguishCancelAndClose: true
            }).then(() => {
                Api.agent.deleteAgentVoicePrint(id, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: `Successfully deleted voice print`,
                            showClose: true
                        });
                        this.fetchVoicePrints();
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

.voice-print-card {
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
