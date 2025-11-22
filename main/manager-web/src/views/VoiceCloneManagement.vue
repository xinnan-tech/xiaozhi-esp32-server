<template>
    <div class="welcome">
        <HeaderBar />
        <div class="operation-bar">
            <h2 class="page-title">{{ $t('voiceClone.title') }}</h2>
            <div class="right-operations">
                <el-input :placeholder="$t('voiceClone.searchPlaceholder')" v-model="searchName" class="search-input"
                    @keyup.enter.native="handleSearch" clearable />
                <el-button class="btn-search" @click="handleSearch">{{ $t('voiceClone.search') }}</el-button>
            </div>
        </div>

        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <!-- 显示表格或空状态 -->
                    <el-card class="params-card" shadow="never" v-if="total > 0">
                        <el-table ref="paramsTable" :data="voiceCloneList" class="transparent-table" v-loading="loading"
                            element-loading-text="Loading" element-loading-spinner="el-icon-loading"
                            element-loading-background="rgba(255, 255, 255, 0.7)">
                            <el-table-column :label="$t('voiceClone.voiceId')" prop="voiceId"
                                align="center"></el-table-column>
                            <el-table-column :label="$t('voiceClone.name')" align="center">
                                <template #default="{ row }">
                                    <el-input v-show="row.isEdit" v-model="row.name" size="mini" maxlength="64"
                                        show-word-limit @blur="onNameBlur(row)" @keyup.enter.native="onNameEnter(row)"
                                        ref="nameInput" />
                                    <span v-show="!row.isEdit" class="name-view">
                                        <i class="el-icon-edit" @click="handleEditName(row)"
                                            style="cursor: pointer;"></i>
                                        <span @click="handleEditName(row)">
                                            {{ row.name || '-' }}
                                        </span>
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column :label="$t('voiceClone.trainStatus')" prop="trainStatus" align="center">
                                <template slot-scope="scope">
                                    <div class="status-button" :class="getStatusButtonClass(scope.row)">
                                        <span>{{ getTrainStatusText(scope.row) }}</span>
                                    </div>
                                </template>
                            </el-table-column>

                            <el-table-column :label="$t('voiceClone.Details')" align="center" width="120">
                                <template slot-scope="scope">
                                    <el-tooltip :content="getTooltipContent(scope.row)" placement="top">
                                        <el-button size="mini" type="text" icon="el-icon-info"
                                            @click="handleViewDetails(scope.row)">
                                        </el-button>
                                    </el-tooltip>
                                </template>
                            </el-table-column>

                            <el-table-column :label="$t('voiceClone.action')" align="center" width="230">
                                <template slot-scope="scope">
                                    <el-button v-if="scope.row.hasVoice" size="mini" type="text"
                                        @click="handlePlay(scope.row)">
                                        {{ playingRowId === scope.row.id ? $t('voiceClone.stop') : $t('voiceClone.play') }}
                                    </el-button>
                                    <el-button size="mini" type="text" @click="handleUpload(scope.row)">
                                        {{ $t('voiceClone.upload') }}
                                    </el-button>
                                    <el-button v-if="scope.row.hasVoice" size="mini" type="text"
                                        @click="handleClone(scope.row)" :loading="scope.row._cloning">
                                        {{ $t('voiceClone.clone') }}
                                    </el-button>
                                </template>
                            </el-table-column>
                        </el-table>

                        <div class="table_bottom">
                            <div class="ctrl_btn">
                            </div>
                            <div class="custom-pagination">
                                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                                    <el-option v-for="item in pageSizeOptions" :key="item"
                                        :label="$t('voiceClone.itemsPerPage', { items: item })" :value="item">
                                    </el-option>
                                </el-select>
                                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">
                                    {{ $t('voiceClone.firstPage') }}
                                </button>
                                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">
                                    {{ $t('voiceClone.prevPage') }}
                                </button>
                                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                                    :class="{ active: page === currentPage }" @click="goToPage(page)">
                                    {{ page }}
                                </button>
                                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">
                                    {{ $t('voiceClone.nextPage') }}
                                </button>
                                <span class="total-text">{{ $t('voiceClone.totalRecords', { total }) }}</span>
                            </div>
                        </div>
                    </el-card>

                    <!-- 空状态提示 -->
                    <div v-else-if="!loading" class="empty-state-wrapper">
                        <div class="empty-state">
                            <div class="empty-icon">
                                <i class="el-icon-microphone" style="font-size: 48px;"></i>
                            </div>
                            <div class="empty-text">
                                {{ $t('voiceClone.noVoiceCloneAssigned') }}
                            </div>
                            <div class="empty-desc">
                                {{ $t('voiceClone.contactAdmin') }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <el-footer>
            <version-footer />
        </el-footer>

        <!-- 复刻弹框 -->
        <VoiceCloneDialog :visible.sync="cloneDialogVisible" :voiceCloneData="currentVoiceClone"
            @success="handleCloneSuccess" />
    </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import VoiceCloneDialog from "@/components/VoiceCloneDialog.vue";
import { formatDate } from "@/utils/format";

export default {
    components: { HeaderBar, VersionFooter, VoiceCloneDialog },
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
            cloneDialogVisible: false,
            currentVoiceClone: {},
            isAllSelected: false,
            voiceCloneForm: {
                modelId: "",
                voiceIds: [],
                userId: null
            },
            // 音频播放相关
            currentAudio: null, // 当前正在播放的音频对象
            playingRowId: null  // 当前正在播放的行 ID
        };
    },
    created() {
        this.fetchVoiceCloneList();
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
        getTooltipContent(row) {
            if (!row.hasVoice) {
                return '待上传';
            }
            switch (row.trainStatus) {
                case 0:
                    return '待复刻';
                case 2:
                    return '训练成功';
                case 3:
                    // 训练失败时，根据错误信息智能展示
                    if (row.trainError) {
                        return `训练失败：${row.trainError}`;
                    }
                    return '训练失败';
                default:
                    return '';
            }
        },
        handleViewDetails(row) {
            console.log('查看详情:', row);
            // 可以在这里添加查看详情的逻辑
        },
        handlePageSizeChange(val) {
            this.pageSize = val;
            this.currentPage = 1;
            this.fetchVoiceCloneList();
        },
        fetchVoiceCloneList() {
            this.loading = true;
            const params = {
                pageNum: this.currentPage,
                pageSize: this.pageSize,
                name: this.searchName || "",
                orderField: "create_date",
                order: "desc"
            };
            Api.voiceClone.getVoiceCloneList(params, (res) => {
                this.loading = false;
                res = res.data
                if (res.code === 0) {
                    this.voiceCloneList = res.data.list;
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
        goFirst() {
            this.currentPage = 1;
            this.fetchVoiceCloneList();
        },
        goPrev() {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.fetchVoiceCloneList();
            }
        },
        goNext() {
            if (this.currentPage < this.pageCount) {
                this.currentPage++;
                this.fetchVoiceCloneList();
            }
        },
        goToPage(page) {
            this.currentPage = page;
            this.fetchVoiceCloneList();
        },
        formatDate,
        getTrainStatusText(row) {
            if (!row.hasVoice) {
                return this.$t('voiceClone.waitingUpload');
            }
            switch (row.trainStatus) {
                case 0:
                    return this.$t('voiceClone.waitingTraining');
                case 2:
                    return this.$t('voiceClone.trainSuccess');
                case 3:
                    return this.$t('voiceClone.trainFailed');
                default:
                    return '';
            }
        },
        // 获取状态按钮样式
        getStatusButtonClass(row) {
            if (!row.hasVoice || row.trainStatus === 0) {
                return 'status-waiting';
            } else if (row.trainStatus === 2) {
                return 'status-success';
            } else if (row.trainStatus === 3) {
                return 'status-failed';
            }
            return '';
        },
        // 处理复刻操作
        handleClone(row) {
            // 防止重复提交
            if (row._cloning) {
                return;
            }
            this.$set(row, '_cloning', true);

            const params = {
                cloneId: row.id
            };
            try {
                Api.voiceClone.cloneAudio(params, (res) => {
                    try {
                        res = res.data;
                        if (res.code === 0) {
                            this.$message.success(this.$t('message.success'));
                            // 复刻成功后刷新列表
                            this.fetchVoiceCloneList();
                        } else {
                            // 复刻失败时刷新列表以获取完整的错误信息
                            console.log('API返回错误，刷新列表获取详细错误信息');
                            this.$message.error(res.msg || this.$t('message.error'));
                            // 刷新列表以获取后端保存的完整错误详情
                            this.fetchVoiceCloneList();
                        }
                    } catch (error) {
                        // 处理响应时出错，刷新列表
                        console.error('处理响应时出错:', error);
                        this.$message.error('处理响应时出错');
                        this.fetchVoiceCloneList();
                    } finally {
                        this.$set(row, '_cloning', false);
                    }
                }, (error) => {
                    // API调用失败，刷新列表以获取最新状态
                    console.error('API调用失败:', error);
                    this.$message.error('克隆失败，请将鼠标悬停在错误提示上，查看错误详情');
                    this.fetchVoiceCloneList();
                    this.$set(row, '_cloning', false);
                });
            } catch (error) {
                // 调用API时出错，刷新列表
                console.error('调用API时出错:', error);
                this.$message.error('调用API时出错');
                this.fetchVoiceCloneList();
                this.$set(row, '_cloning', false);
            }
        },

        // 更新行状态并触发视图更新
        updateRowStatus(row, status, statusCode = null) {
            // 在Vue中直接修改数组中的对象属性可能不会触发视图更新
            const index = this.voiceCloneList.findIndex(item => item.id === row.id);
            const updateData = {
                trainStatus: status
            };

            // 如果提供了状态码，也更新状态码信息
            if (statusCode !== null) {
                updateData.statusCode = statusCode;
            }

            if (index !== -1) {
                // 使用Vue.set来确保响应式更新
                this.$set(this.voiceCloneList, index, {
                    ...this.voiceCloneList[index],
                    ...updateData
                });
                // 强制表格重新渲染
                if (this.$refs.paramsTable) {
                    this.$refs.paramsTable.doLayout();
                }
            } else {
                // 如果找不到索引，直接更新row对象
                row.trainStatus = status;
                if (statusCode !== null) {
                    row.statusCode = statusCode;
                }
                // 强制整个表格重新渲染
                this.$forceUpdate();
            }
            console.log('更新行状态:', row.id, '状态:', status, '状态码:', statusCode);
        },
        // 复刻成功后的回调
        handleCloneSuccess() {
            this.fetchVoiceCloneList();
        },
        // 进入编辑模式
        handleEditName(row) {
            this.$set(row, 'isEdit', true);
            this.$nextTick(() => {
                // 聚焦到输入框
                const input = this.$refs.nameInput;
                if (input) {
                    // nameInput 可能是一个数组
                    if (Array.isArray(input)) {
                        const idx = this.voiceCloneList.indexOf(row);
                        if (input[idx]) {
                            input[idx].focus();
                        }
                    } else {
                        input.focus();
                    }
                }
            });
        },
        // 提交名称修改
        submitName(row) {
            // 防止重复提交
            if (row._submitting) {
                return;
            }
            row._submitting = true;

            const params = {
                id: row.id,
                name: row.name
            };

            Api.voiceClone.updateName(params, (res) => {
                res = res.data;
                if (res.code === 0) {
                    this.$message.success(this.$t('voiceClone.updateNameSuccess') || '名称更新成功');
                } else {
                    this.$message.error(res.msg || this.$t('voiceClone.updateNameFailed') || '名称更新失败');
                    // 失败时恢复原值
                    this.fetchVoiceCloneList();
                }
                row._submitting = false;
            });
        },
        // 名称输入框:失焦时提交
        onNameBlur(row) {
            row.isEdit = false;
            setTimeout(() => {
                this.submitName(row);
            }, 100); // 延迟 100ms，避开 enter+blur 同时触发的窗口
        },
        // 名称输入框:按回车时提交
        onNameEnter(row) {
            row.isEdit = false;
            this.submitName(row);
        },
        // 播放音频
        handlePlay(row) {
            // 如果点击的是正在播放的行,则停止播放
            if (this.playingRowId === row.id && this.currentAudio) {
                this.stopCurrentAudio();
                return;
            }

            // 停止当前正在播放的音频(如果有)
            this.stopCurrentAudio();

            // 先获取音频下载ID
            Api.voiceClone.getAudioId(row.id, (res) => {
                res = res.data;
                if (res.code === 0) {
                    const uuid = res.data;
                    // 使用获取到的uuid播放音频
                    const audioUrl = Api.voiceClone.getPlayVoiceUrl(uuid);
                    const audio = new Audio(audioUrl);

                    // 设置当前播放状态
                    this.currentAudio = audio;
                    this.playingRowId = row.id;

                    // 播放结束时清除状态
                    audio.addEventListener('ended', () => {
                        this.playingRowId = null;
                        this.currentAudio = null;
                    });

                    // 播放出错时清除状态
                    audio.addEventListener('error', () => {
                        this.playingRowId = null;
                        this.currentAudio = null;
                    });

                    audio.play().catch(err => {
                        console.error('播放失败:', err);
                        this.$message.error(this.$t('voiceClone.playFailed') || '播放失败');
                        this.playingRowId = null;
                        this.currentAudio = null;
                    });
                } else {
                    this.$message.error(res.msg || this.$t('voiceClone.audioNotExist') || '音频不存在');
                }
            });
        },
        // 停止当前音频播放
        stopCurrentAudio() {
            if (this.currentAudio) {
                this.currentAudio.pause();
                this.currentAudio.currentTime = 0;
                this.currentAudio = null;
            }
            this.playingRowId = null;
        },
        // 上传音频
        handleUpload(row) {
            this.currentVoiceClone = row;
            this.cloneDialogVisible = true;
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

.empty-state-wrapper {
    margin-top: 20vh;
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

/* 状态按钮样式 */
.status-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}

.status-waiting {
    background-color: #f5f7fa;
    color: #909399;
    border: 1px solid #e4e7ed;
}

.status-success {
    background-color: #f6ffed;
    color: #52c41a;
    border: 1px solid #b7eb8f;
}

.status-failed {
    background-color: #fff2f0;
    color: #ff4d4f;
    border: 1px solid #ffccc7;
}

.name-view {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;

    i {
        color: #909399;
        font-size: 14px;

        &:hover {
            color: #5a64b5;
        }
    }

    span {
        &:hover {
            color: #5a64b5;
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
