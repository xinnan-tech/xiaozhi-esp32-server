<template>
    <div class="welcome">
        <HeaderBar />
        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="params-card" shadow="never">
                        <div class="operation-header">
                            <h2 class="page-title">{{ $t('otaManagement.firmwareManagement') }}</h2>
                            <div class="right-operations">
                                <el-input :placeholder="$t('otaManagement.searchPlaceholder')" v-model="searchName"
                                    class="search-input" @keyup.enter.native="handleSearch" clearable />
                                <CustomButton icon="el-icon-search" type="confirm" @click="handleSearch">
                                    {{ $t('otaManagement.search') }}
                                </CustomButton>
                            </div>
                        </div>
                        <CustomTable ref="paramsTable" :data="paramsList" :columns="tableColumns" :loading="loading"
                            :show-selection="true" :show-operations="true" :operations-label="$t('otaManagement.action')"
                            :total="total" :current-page="currentPage" :page-size="pageSize"
                            :page-size-options="pageSizeOptions" @size-change="handlePageSizeChange"
                            @page-change="goToPage">
                            <template slot="selection" slot-scope="scope">
                                <el-checkbox v-model="scope.row.selected"></el-checkbox>
                            </template>
                            <template slot="type" slot-scope="scope">
                                {{ getFirmwareTypeName(scope.row.type) }}
                            </template>
                            <template slot="size" slot-scope="scope">
                                {{ formatFileSize(scope.row.size) }}
                            </template>
                            <template slot="createDate" slot-scope="scope">
                                {{ formatDate(scope.row.createDate) }}
                            </template>
                            <template slot="updateDate" slot-scope="scope">
                                {{ formatDate(scope.row.updateDate) }}
                            </template>
                            <template slot="operations" slot-scope="scope">
                                <el-button size="mini" type="text"
                                    @click="downloadFirmware(scope.row)">{{ $t('otaManagement.download') }}</el-button>
                                <el-button size="mini" type="text" @click="editParam(scope.row)">
                                    {{ $t('otaManagement.edit') }}
                                </el-button>
                                <el-button size="mini" type="text" @click="deleteParam(scope.row)">
                                    {{ $t('otaManagement.delete') }}
                                </el-button>
                            </template>
                            <template slot="footer-btns">
                                <div class="ctrl_btn">
                                    <CustomButton
                                        :icon="isAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'"
                                        size="small" @click="handleSelectAll">
                                        {{ isAllSelected ? $t('otaManagement.deselectAll') : $t('otaManagement.selectAll') }}
                                    </CustomButton>
                                    <CustomButton type="add" icon="el-icon-plus" size="small" @click="showAddDialog">
                                        {{ $t('otaManagement.addNew') }}
                                    </CustomButton>
                                    <CustomButton size="small" type="delete" icon="el-icon-delete"
                                        @click="deleteSelectedParams">
                                        {{ $t('otaManagement.delete') }}
                                    </CustomButton>
                                </div>
                            </template>
                        </CustomTable>
                    </el-card>
                </div>
            </div>
        </div>

        <!-- Add/Edit firmware dialog -->
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
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";
import { formatDate, formatFileSize } from "@/utils/format";

export default {
    components: { HeaderBar, FirmwareDialog, VersionFooter, CustomButton, CustomTable },
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
            dialogTitle: "Add Firmware",
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
            tableColumns: []
        };
    },
    created() {
        this.initTableColumns();
        this.fetchFirmwareList();
        this.getFirmwareTypes();
    },
    methods: {
        initTableColumns() {
            this.tableColumns = [
                { prop: 'firmwareName', label: this.$t('otaManagement.firmwareName'), align: 'center' },
                { prop: 'type', label: this.$t('otaManagement.firmwareType'), align: 'center' },
                { prop: 'version', label: this.$t('otaManagement.version'), align: 'center' },
                { prop: 'size', label: this.$t('otaManagement.fileSize'), align: 'center' },
                { prop: 'remark', label: this.$t('otaManagement.remark'), align: 'center' },
                { prop: 'createDate', label: this.$t('otaManagement.createTime'), align: 'center' },
                { prop: 'updateDate', label: this.$t('otaManagement.updateTime'), align: 'center' }
            ];
        },
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
                        message: res?.data?.msg || this.$t('otaManagement.fetchFirmwareListFailed'),
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
            this.dialogTitle = this.$t('otaManagement.addFirmware');
            // Completely reset form data
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
                // Reset form validation status
                if (this.$refs.firmwareDialog && this.$refs.firmwareDialog.$refs.form) {
                    this.$refs.firmwareDialog.$refs.form.clearValidate();
                }
            });
            this.dialogVisible = true;
        },
        editParam(row) {
            this.dialogTitle = this.$t('otaManagement.editFirmware');
            this.firmwareForm = { ...row };
            this.dialogVisible = true;
        },
        handleSubmit(form) {
            if (form.id) {
                // Edit
                Api.ota.updateOta(form.id, form, (res) => {
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success({
                            message: this.$t('otaManagement.updateSuccess'),
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchFirmwareList();
                    } else {
                        this.$message.error({
                            message: res.msg || this.$t('otaManagement.updateFailed'),
                            showClose: true
                        });
                    }
                    this.$refs.firmwareDialog?.resetSaving();
                });
            } else {
                // Add
                Api.ota.saveOta(form, (res) => {
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success({
                            message: this.$t('otaManagement.addSuccess'),
                            showClose: true
                        });
                        this.dialogVisible = false;
                        this.fetchFirmwareList();
                    } else {
                        this.$message.error({
                            message: res.msg || this.$t('otaManagement.addFailed'),
                            showClose: true
                        });
                    }
                    this.$refs.firmwareDialog?.resetSaving();
                });
            }
        },
        deleteSelectedParams() {
            const selectedRows = this.firmwareList.filter(row => row.selected);
            if (selectedRows.length === 0) {
                this.$message.warning({
                    message: this.$t('otaManagement.selectFirmwareFirst'),
                    showClose: true
                });
                return;
            }
            this.deleteParam(selectedRows);
        },
        deleteParam(row) {
            // Handle single parameter or parameter array
            const params = Array.isArray(row) ? row : [row];

            if (Array.isArray(row) && row.length === 0) {
                this.$message.warning({
                    message: this.$t('otaManagement.selectFirmwareFirst'),
                    showClose: true
                });
                return;
            }

            const paramCount = params.length;
            this.$confirm(this.$t('otaManagement.confirmBatchDelete', { paramCount }), 'Warning', {
                confirmButtonText: 'OK',
                cancelButtonText: 'Cancel',
                type: 'warning',
                distinguishCancelAndClose: true
            }).then(() => {
                const ids = params.map(param => param.id);
                if (ids.some(id => !id)) {
                    this.$message.error({
                        message: this.$t('otaManagement.invalidFirmwareId'),
                        showClose: true
                    });
                    return;
                }

                Api.ota.deleteOta(ids, (res) => {
                    res = res.data;
                    if (res.code === 0) {
                        this.$message.success({
                            message: this.$t('otaManagement.batchDeleteSuccess', { paramCount }),
                            showClose: true
                        });
                        this.fetchFirmwareList();
                    } else {
                        this.$message.error({
                            message: res.msg || this.$t('otaManagement.deleteFailed'),
                            showClose: true
                        });
                    }
                });
            }).catch(action => {
                if (action === 'cancel') {
                    this.$message({
                        type: 'info',
                        message: this.$t('otaManagement.operationCancelled'),
                        duration: 1000
                    });
                } else {
                    this.$message({
                        type: 'info',
                        message: this.$t('otaManagement.operationClosed'),
                        duration: 1000
                    });
                }
            });
        },
        goToPage(page) {
            if (page !== this.currentPage) {
                this.currentPage = page;
                this.fetchFirmwareList();
            }
        },
        downloadFirmware(firmware) {
            if (!firmware || !firmware.id) {
                this.$message.error(this.$t('otaManagement.incompleteFirmwareInfo'));
                return;
            }
            // First get download link
            Api.ota.getDownloadUrl(firmware.id, (res) => {
                if (res.data.code === 0) {
                    const uuid = res.data.data;
                    const baseUrl = process.env.VUE_APP_API_BASE_URL || '';
                    window.open(`${window.location.origin}${baseUrl}/otaMag/download/${uuid}`);
                } else {
                    this.$message.error(this.$t('otaManagement.getDownloadUrlFailed'));
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
                console.error('Failed to get firmware type:', error)
                this.$message.error(error.message || this.$t('otaManagement.getFirmwareTypesFailed'))
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
    color: #5a64b5 !important;
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
