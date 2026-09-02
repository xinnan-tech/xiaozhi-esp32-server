<template>
    <div class="welcome">
        <HeaderBar />
        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="params-card" shadow="never">
                        <div class="operation-header">
                            <h2 class="page-title">{{ $t('voiceResource.title') }}</h2>
                            <div class="right-operations">
                                <el-input :placeholder="$t('voiceClone.searchPlaceholder')" v-model="searchName"
                                    class="search-input" @keyup.enter.native="handleSearch" clearable />
                                <CustomButton icon="el-icon-search" type="confirm"
                                    @click="handleSearch">{{ $t('voiceClone.search') }}</CustomButton>
                            </div>
                        </div>
                        <CustomTable ref="voiceTable" :data="voiceCloneList" :columns="tableColumns" :loading="loading"
                            :show-selection="true" :show-operations="true" :operations-label="$t('voiceClone.action')"
                            :total="total" :current-page="currentPage" :page-size="pageSize"
                            :page-size-options="pageSizeOptions" @size-change="handlePageSizeChange"
                            @page-change="goToPage">
                            <template slot="trainStatus" slot-scope="scope">
                                {{ getTrainStatusText(scope.row) }}
                            </template>
                            <template slot="createdAt" slot-scope="scope">
                                {{ formatDate(scope.row.createDate) }}
                            </template>
                            <template slot="operations" slot-scope="scope">
                                <el-button size="mini" type="text"
                                    @click="deleteVoiceClone(scope.row)">{{ $t('voiceClone.delete') }}</el-button>
                            </template>
                            <template slot="footer-btns">
                                <div class="ctrl_btn">
                                    <CustomButton
                                        :icon="isAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'"
                                        size="small" @click="handleSelectAll">
                                        {{ isAllSelected ? $t('voiceClone.deselectAll') : $t('voiceClone.selectAll') }}
                                    </CustomButton>
                                    <CustomButton icon="el-icon-plus" type="add" size="small"
                                        @click="showAddDialog">{{ $t('voiceClone.addNew') }}</CustomButton>
                                    <CustomButton size="small" type="delete" icon="el-icon-delete"
                                        @click="deleteSelectedVoiceClones">{{ $t('voiceClone.delete') }}</CustomButton>
                                </div>
                            </template>
                        </CustomTable>
                    </el-card>
                </div>
            </div>
        </div>

        <!-- 新增音色资源对话框 -->
        <voice-clone-dialog :title="$t('voiceClone.addVoiceClone')" :visible.sync="dialogVisible" :form="voiceCloneForm"
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
import VoiceCloneDialog from "@/components/VoiceResourceDialog.vue";
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";
import { formatDate } from "@/utils/format";

export default {
    components: { HeaderBar, VoiceCloneDialog, VersionFooter, CustomButton, CustomTable },
    data() {
        return {
            searchName: "",
            loading: false,
            voiceCloneList: [],
            currentPage: 1,
            pageSize: 10,
            pageSizeOptions: [10, 20, 50, 100],
            total: 0,
            dialogVisible: false,
            isAllSelected: false,
            voiceCloneForm: {
                modelId: "",
                voiceIds: [],
                userId: null,
                languages: ""
            },
            tableColumns: []
        };
    },
    created() {
        this.initTableColumns();
        this.fetchVoiceCloneList();
    },
    methods: {
        initTableColumns() {
            this.tableColumns = [
                { prop: 'voiceId', label: this.$t('voiceClone.voiceId'), align: 'center' },
                { prop: 'name', label: this.$t('voiceClone.name'), align: 'center' },
                { prop: 'userName', label: this.$t('voiceClone.userId'), align: 'center' },
                { prop: 'modelName', label: this.$t('voiceClone.platformName'), align: 'center' },
                { prop: 'languages', label: this.$t('voiceClone.languages'), align: 'center' },
                { prop: 'trainStatus', label: this.$t('voiceClone.trainStatus'), align: 'center' },
                { prop: 'createdAt', label: this.$t('voiceClone.createdAt'), align: 'center' }
            ];
        },
        handlePageSizeChange(val) {
            this.pageSize = val;
            this.currentPage = 1;
            this.fetchVoiceCloneList();
        },
        fetchVoiceCloneList() {
            this.loading = true;
            const params = {
                page: this.currentPage,
                limit: this.pageSize,
                name: this.searchName || "",
                orderField: "create_date",
                order: "desc"
            };
            Api.voiceResource.getVoiceResourceList(params, (res) => {
                this.loading = false;
                res = res.data
                if (res.code === 0) {
                    this.voiceCloneList = res.data.list.map(item => ({
                        ...item,
                        selected: false
                    }));
                    this.total = res.data.total || 0;
                } else {
                    this.voiceCloneList = [];
                    this.total = 0;
                    this.$message.error({
                        message: res?.data?.msg || this.$t('voiceClone.deleteFailed'),
                        showClose: true
                    });
                }
            });
        },
        handleSearch() {
            this.currentPage = 1;
            this.fetchVoiceCloneList();
        },
        handleSelectAll() {
            this.isAllSelected = !this.isAllSelected;
            this.voiceCloneList.forEach(row => {
                row.selected = this.isAllSelected;
            });
        },
        showAddDialog() {
            this.voiceCloneForm = {
                modelId: "",
                voiceIds: [],
                userId: null,
                languages: ""
            };
            this.$nextTick(() => {
                if (this.$refs.voiceCloneForm) {
                    this.$refs.voiceCloneForm.clearValidate();
                }
            });
            this.dialogVisible = true;
        },
        handleSubmit(formData) {
            Api.voiceResource.saveVoiceResource(formData, (res) => {
                res = res.data;
                if (res.code === 0) {
                    this.$message.success({
                        message: this.$t('voiceClone.addSuccess'),
                        showClose: true
                    });
                    this.dialogVisible = false;
                    this.fetchVoiceCloneList();
                } else {
                    this.$message.error({
                        message: res.msg || this.$t('voiceClone.addFailed'),
                        showClose: true
                    });
                }
            });
        },
        deleteSelectedVoiceClones() {
            const selectedRows = this.voiceCloneList.filter(row => row.selected);
            if (selectedRows.length === 0) {
                this.$message.warning({
                    message: this.$t('voiceClone.selectFirst'),
                    showClose: true
                });
                return;
            }
            this.deleteVoiceClone(selectedRows);
        },
        deleteVoiceClone(row) {
            const items = Array.isArray(row) ? row : [row];

            if (Array.isArray(row) && row.length === 0) {
                this.$message.warning({
                    message: this.$t('voiceClone.selectFirst'),
                    showClose: true
                });
                return;
            }

            const itemCount = items.length;
            this.$confirm(this.$t('voiceClone.confirmDelete', { count: itemCount }), this.$t('voiceClone.warning'), {
                confirmButtonText: this.$t('voiceClone.ok'),
                cancelButtonText: this.$t('voiceClone.cancel'),
                type: 'warning',
                distinguishCancelAndClose: true
            }).then(() => {
                const ids = items.map(item => item.id);
                if (ids.some(id => !id)) {
                    this.$message.error({
                        message: this.$t('voiceClone.deleteFailed'),
                        showClose: true
                    });
                    return;
                }

                Api.voiceResource.deleteVoiceResource(ids, (res) => {
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success({
                            message: this.$t('voiceClone.deleteSuccess', { count: itemCount }),
                            showClose: true
                        });
                        this.fetchVoiceCloneList();
                    } else {
                        this.$message.error({
                            message: res.msg || this.$t('voiceClone.deleteFailed'),
                            showClose: true
                        });
                    }
                });
            }).catch(action => {
                if (action === 'cancel') {
                    this.$message({
                        type: 'info',
                        message: this.$t('voiceClone.operationCancelled'),
                        duration: 1000
                    });
                } else {
                    this.$message({
                        type: 'info',
                        message: this.$t('voiceClone.operationClosed'),
                        duration: 1000
                    });
                }
            });
        },
        goToPage(page) {
            if (page !== this.currentPage) {
                this.currentPage = page;
                this.fetchVoiceCloneList();
            }
        },
        formatDate,
        getTrainStatusText(row) {
            if (!row.hasVoice) {
                return this.$t('voiceClone.waitingUpload');
            }
            switch (row.trainStatus) {
                case 0:
                    return this.$t('voiceClone.waitingTraining');
                case 1:
                    return this.$t('voiceClone.training');
                case 2:
                    return this.$t('voiceClone.trainSuccess');
                case 3:
                    return this.$t('voiceClone.trainFailed');
                default:
                    return '';
            }
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
    background: #eff4ff;
    -webkit-background-size: cover;
    -o-background-size: cover;
    overflow: hidden;
}

.main-wrapper {
    // 顶部 63px 底部 35px
    height: calc(100vh - 63px - 35px);
    padding: 20px 22px 0;
    position: relative;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
}

.operation-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 16px 0;
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

.params-card {
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

.ctrl_btn {
    display: flex;
}

:deep(.el-table .el-button--text) {
    color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
    color: #5a64b5;
}
</style>
