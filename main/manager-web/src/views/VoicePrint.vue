<template>
    <div class="welcome">
        <HeaderBar />
        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="voice-print-card" shadow="never">
                        <div class="operation-header">
                            <h2 class="page-title">{{ $t('voicePrint.pageTitle') }}</h2>
                        </div>
                        <CustomTable
                            ref="paramsTable"
                            :data="voicePrintList"
                            :columns="tableColumns"
                            :loading="loading"
                            :loading-text="$t('voicePrint.loading')"
                            :show-operations="true"
                            :operations-label="$t('voicePrint.action')"
                            :total="total"
                            :show-pagination="false"
                            :current-page="currentPage"
                            :page-size="pageSize"
                            :page-size-options="pageSizeOptions"
                            @size-change="handlePageSizeChange"
                            @page-change="goToPage"
                        >
                            <template slot="operations" slot-scope="scope">
                                <el-button size="mini" type="text" @click="editVoicePrint(scope.row)">{{ $t('voicePrint.edit') }}</el-button>
                                <el-button size="mini" type="text" @click="deleteVoicePrint(scope.row.id)">{{ $t('voicePrint.delete') }}</el-button>
                            </template>
                            <template slot="footer-btns">
                                <div class="ctrl_btn">
                                    <CustomButton icon="el-icon-plus" type="add" size="small" @click="showAddDialog">{{ $t('voicePrint.add') }}</CustomButton>
                                </div>
                            </template>
                        </CustomTable>
                    </el-card>
                </div>
            </div>
        </div>

        <!-- Add/Edit parameter dialog -->
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
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";

export default {
    components: { HeaderBar, VoicePrintDialog, VersionFooter, CustomButton, CustomTable },
    data() {
        return {
            voicePrintList: [],
            allVoicePrints: [],
            loading: false,
            dialogVisible: false,
            dialogTitle: this.$t('voicePrint.addSpeaker'),
            currentPage: 1,
            pageSize: 10,
            pageSizeOptions: [10, 20, 50, 100],
            total: 0,
            paramForm: {
                id: null,
                audioId: '',
                sourceName: '',
                introduce: ''
            },
            agentId: "1",
            tableColumns: []
        };
    },
    created() {
        this.initTableColumns();
    },
    mounted() {
        const agentId = this.$route.query.agentId;
        if (agentId) {
            this.agentId = agentId;
            this.fetchVoicePrints();
        }
    },
    methods: {
        initTableColumns() {
            this.tableColumns = [
                { prop: 'sourceName', label: this.$t('voicePrint.name'), align: 'center' },
                { prop: 'introduce', label: this.$t('voicePrint.description'), align: 'center' },
                { prop: 'createDate', label: this.$t('voicePrint.createTime'), align: 'center' }
            ];
        },
        fetchVoicePrints() {
            this.loading = true;
            Api.agent.getAgentVoicePrintList(this.agentId,
                ({ data }) => {
                    this.loading = false;
                    if (data.code === 0) {
                        this.allVoicePrints = data.data;
                        this.total = data.data.length;
                        this.currentPage = 1;
                        this.updatePagedData();
                    } else {
                        this.$message.error({
                            message: data.msg || this.$t('voicePrint.fetchFailed'),
                            showClose: true
                        });
                    }
                }
            );
        },
        updatePagedData() {
            const start = (this.currentPage - 1) * this.pageSize;
            this.voicePrintList = this.allVoicePrints.slice(start, start + this.pageSize);
        },
        handlePageSizeChange(val) {
            this.pageSize = val;
            this.currentPage = 1;
            this.updatePagedData();
        },
        goToPage(page) {
            if (page !== this.currentPage) {
                this.currentPage = page;
                this.updatePagedData();
            }
        },
        showAddDialog() {
            this.dialogTitle = this.$t('voicePrint.addSpeaker');
            this.paramForm = {
                id: null,
                audioId: '',
                sourceName: '',
                introduce: ''
            };
            this.dialogVisible = true;
        },
        editVoicePrint(row) {
            this.dialogTitle = this.$t('voicePrint.editSpeaker');
            this.paramForm = { ...row };
            this.dialogVisible = true;
        },
        handleSubmit({ form, done }) {
            if (form.id) {
                // Edit
                Api.agent.updateAgentVoicePrint(form, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: this.$t('voicePrint.updateSuccess'),
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
                            message: this.$t('voicePrint.addSuccess'),
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
            this.$confirm(this.$t('voicePrint.confirmDelete'), this.$t('voicePrint.warning'), {
                confirmButtonText: this.$t('voicePrint.confirm'),
                cancelButtonText: this.$t('voicePrint.cancel'),
                type: 'warning',
                distinguishCancelAndClose: true
            }).then(() => {
                Api.agent.deleteAgentVoicePrint(id, ({ data }) => {
                    if (data.code === 0) {
                        this.$message.success({
                            message: this.$t('voicePrint.deleteSuccess'),
                            showClose: true
                        });
                        this.fetchVoicePrints();
                    } else {
                        this.$message.error({
                            message: data.msg || this.$t('voicePrint.deleteFailed'),
                            showClose: true
                        });
                    }
                });
            }).catch(action => {
                if (action === 'cancel') {
                    this.$message({
                        type: 'info',
                        message: this.$t('voicePrint.cancelDelete'),
                        duration: 1000
                    });
                } else {
                    this.$message({
                        type: 'info',
                        message: this.$t('voicePrint.closeOperation'),
                        duration: 1000
                    });
                }
            });
        }
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
    background-size: cover;
    background: #eff4ff;
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
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
}

.operation-header {
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 16px 0;
    box-sizing: border-box;
}

.page-title {
    font-weight: 500;
    font-size: 24px;
    margin: 0;
}

.content-panel {
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
        padding: 14px 20px;
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
