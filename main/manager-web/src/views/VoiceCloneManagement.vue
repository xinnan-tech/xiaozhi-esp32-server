<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="params-card" shadow="never">
            <div class="operation-header">
              <h2 class="page-title">{{ $t('voiceClone.title') }}</h2>
              <div class="right-operations">
                <el-input :placeholder="$t('voiceClone.searchPlaceholder')" v-model="searchName" class="search-input"
                  @keyup.enter.native="handleSearch" clearable />
                <CustomButton type="confirm" icon="el-icon-search" @click="handleSearch">{{ $t('voiceClone.search') }}</CustomButton>
              </div>
            </div>
        </div>

        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <!-- Show the table or the empty state -->
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
                            <el-table-column :label="$t('voiceClone.languages')" prop="languages"
                                align="center"></el-table-column>
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

                    <!-- Empty state -->
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
                    <div class="info-right" :class="{ 'info-right--centered': !item.hasVoice }">
                       <el-tooltip :content="getTooltipContent(item)" placement="top" effect="light">
                          <div class="status-button" :class="getStatusButtonClass(item)">
                            <span>{{ getTrainStatusText(item) }}</span>
                          </div>
                       </el-tooltip>
                      <div v-if="item.hasVoice" class="voice-wave" :class="{ 'is-playing': playingRowId === item.id }">
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                      </div>
                    </div>
                  </div>
                </div>

        <!-- Clone dialog -->
        <VoiceCloneDialog :visible.sync="cloneDialogVisible" :voiceCloneData="currentVoiceClone"
            @success="handleCloneSuccess" />
    </div>

    <el-footer>
      <version-footer />
    </el-footer>

    <VoiceCloneDialog :visible.sync="cloneDialogVisible" :voiceCloneData="currentVoiceClone"
      @success="handleCloneSuccess" />
  </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import VoiceCloneDialog from "@/components/VoiceCloneDialog.vue";
import CustomButton from "@/components/CustomButton.vue";
import CustomPagination from "@/components/CustomPagination.vue";
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
            // Audio playback state
            currentAudio: null, // Audio object currently playing
            playingRowId: null  // ID of the row currently playing
        };
    },
    handleViewDetails(row) {
      console.log('View details:', row);
    },
    handlePageSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
      this.fetchVoiceCloneList();
    },
    goToPage(page) {
      if (page !== this.currentPage) {
        this.currentPage = page;
        this.fetchVoiceCloneList();
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
        },
    },
    methods: {
        getTooltipContent(row) {
            if (!row.hasVoice) {
                return 'Pending upload';
            }
            switch (row.trainStatus) {
                case 0:
                    return 'Pending clone';
                case 2:
                    return 'Training successful';
                case 3:
                    // Show the training error when available.
                    if (row.trainError) {
                        return `Training failed: ${row.trainError}`;
                    }
                    return 'Training failed';
                default:
                    return '';
            }
        },
        handleViewDetails(row) {
            console.log('View details:', row);
            // Add detail-view logic here if needed.
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
        // Get the status button style
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
        // Handle the clone action
        handleClone(row) {
            // Prevent duplicate submissions
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
                            // Refresh after a successful clone.
                            this.fetchVoiceCloneList();
                        } else {
                            // Refresh to pick up the full error details.
                            console.log('API returned an error; refreshing to fetch details');
                            this.$message.error(res.msg || this.$t('message.error'));
                            this.fetchVoiceCloneList();
                        }
                    } catch (error) {
                        // Refresh if response handling fails.
                        console.error('Error handling response:', error);
                        this.$message.error('Error handling response');
                        this.fetchVoiceCloneList();
                    } finally {
                        this.$set(row, '_cloning', false);
                    }
                }, (error) => {
                    // Refresh on API failure so the latest status is visible.
                    console.error('API call failed:', error);
                    this.$message.error('Clone failed. Hover over the error message to view details.');
                    this.fetchVoiceCloneList();
                    this.$set(row, '_cloning', false);
                });
            } catch (error) {
                // Refresh if the API call throws unexpectedly.
                console.error('Error calling API:', error);
                this.$message.error('Error calling API');
                this.fetchVoiceCloneList();
                this.$set(row, '_cloning', false);
            }
        },

        // Update row state and refresh the view
        updateRowStatus(row, status, statusCode = null) {
            // Directly mutating an object inside an array may not trigger a Vue update
            const index = this.voiceCloneList.findIndex(item => item.id === row.id);
            const updateData = {
                trainStatus: status
            };

            // Update status code metadata when provided
            if (statusCode !== null) {
                updateData.statusCode = statusCode;
            }

            if (index !== -1) {
                // Use Vue.set to guarantee reactive updates
                this.$set(this.voiceCloneList, index, {
                    ...this.voiceCloneList[index],
                    ...updateData
                });
                // Force the table to re-render
                if (this.$refs.paramsTable) {
                    this.$refs.paramsTable.doLayout();
                }
            } else {
                // If the index cannot be found, update the row object directly
                row.trainStatus = status;
                if (statusCode !== null) {
                    row.statusCode = statusCode;
                }
                // Force the entire table to re-render
                this.$forceUpdate();
            }
            console.log('Updating row status:', row.id, 'status:', status, 'status code:', statusCode);
        },
        // Callback after a successful clone.
        handleCloneSuccess() {
            this.fetchVoiceCloneList();
        },
        // Enter edit mode.
        handleEditName(row) {
            this.$set(row, 'isEdit', true);
            this.$nextTick(() => {
                // Focus the input field.
                const input = this.$refs.nameInput;
                if (input) {
                    // nameInput may be an array.
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
        // Submit the name change.
        submitName(row) {
            // Prevent duplicate submissions.
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
                    this.$message.success(this.$t('voiceClone.updateNameSuccess') || 'Name updated successfully');
                } else {
                    this.$message.error(res.msg || this.$t('voiceClone.updateNameFailed') || 'Failed to update name');
                    this.fetchVoiceCloneList();
                }
                row._submitting = false;
            });
        },
        // Submit when the name input loses focus.
        onNameBlur(row) {
            row.isEdit = false;
            setTimeout(() => {
                this.submitName(row);
            }, 100); // Small delay avoids the enter+blur overlap.
        },
        // Submit when Enter is pressed in the name input.
        onNameEnter(row) {
            row.isEdit = false;
            this.submitName(row);
        },
        // Play audio.
        handlePlay(row) {
            // Stop if the clicked row is already playing.
            if (this.playingRowId === row.id && this.currentAudio) {
                this.stopCurrentAudio();
                return;
            }

            // Stop any currently playing audio.
            this.stopCurrentAudio();

            // Fetch the audio download ID first.
            Api.voiceClone.getAudioId(row.id, (res) => {
                res = res.data;
                if (res.code === 0) {
                    const uuid = res.data;
                    // Play the audio using the returned UUID.
                    const audioUrl = Api.voiceClone.getPlayVoiceUrl(uuid);
                    const audio = new Audio(audioUrl);

                    // Mark this row as playing.
                    this.currentAudio = audio;
                    this.playingRowId = row.id;

                    // Clear state when playback ends.
                    audio.addEventListener('ended', () => {
                        this.playingRowId = null;
                        this.currentAudio = null;
                    });

                    // Clear state on playback error.
                    audio.addEventListener('error', () => {
                        this.playingRowId = null;
                        this.currentAudio = null;
                    });

                    audio.play().catch(err => {
                        console.error('Playback failed:', err);
                        this.$message.error(this.$t('voiceClone.playFailed') || 'Playback failed');
                        this.playingRowId = null;
                        this.currentAudio = null;
                    });
                } else {
                    this.$message.error(res.msg || this.$t('voiceClone.audioNotExist') || 'Audio does not exist');
                }
            });
        },
        // Stop the current audio playback.
        stopCurrentAudio() {
            if (this.currentAudio) {
                this.currentAudio.pause();
                this.currentAudio.currentTime = 0;
                this.currentAudio = null;
            }
            this.playingRowId = null;
        },
        // Upload audio.
        handleUpload(row) {
            this.currentVoiceClone = row;
            this.cloneDialogVisible = true;
        }
      });
    },
    handleSearch() {
      this.currentPage = 1;
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
    handleClone(row) {
      if (row._cloning) {
        return;
      }
      this.$set(row, '_cloning', true);
      const params = { cloneId: row.id };
      try {
        Api.voiceClone.cloneAudio(params, (res) => {
          try {
            res = res.data;
            if (res.code === 0) {
              this.$message.success(this.$t('message.success'));
              this.fetchVoiceCloneList();
            } else {
              this.$message.error(res.msg || this.$t('message.error'));
              this.fetchVoiceCloneList();
            }
          } catch (error) {
            console.error('Error processing response:', error);
            this.$message.error('Error processing response');
            this.fetchVoiceCloneList();
          } finally {
            this.$set(row, '_cloning', false);
          }
        }, (error) => {
          console.error('API call failed:', error);
          this.$message.error(this.$t('voiceClone.cloneErrorTip'));
          this.fetchVoiceCloneList();
          this.$set(row, '_cloning', false);
        });
      } catch (error) {
        console.error('Error calling API:', error);
        this.$message.error(this.$t('voiceClone.apiError'));
        this.fetchVoiceCloneList();
        this.$set(row, '_cloning', false);
      }
    },
    handleCloneSuccess() {
      this.fetchVoiceCloneList();
    },
    handleEditName(row) {
      this.$set(row, 'isEdit', true);
      this.$nextTick(() => {
        const input = this.$refs.nameInput;
        if (input) {
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
    submitName(row) {
      if (row._submitting) {
        return;
      }
      row._submitting = true;
      const params = { id: row.id, name: row.name };
      Api.voiceClone.updateName(params, (res) => {
        res = res.data;
        if (res.code === 0) {
          this.$message.success(this.$t('voiceClone.updateNameSuccess') || 'Name updated successfully');
        } else {
          this.$message.error(res.msg || this.$t('voiceClone.updateNameFailed') || 'Name update failed');
          this.fetchVoiceCloneList();
        }
        row._submitting = false;
      });
    },
    handleEditButtonClick(row) {
      if (row.isEdit) {
        row.isEdit = false;
        this.submitName(row);
      } else {
        this.handleEditName(row);
      }
    },
    onNameEnter(row) {
      row.isEdit = false;
      this.submitName(row);
    },
    handlePlay(row) {
      if (this.playingRowId === row.id && this.currentAudio) {
        this.stopCurrentAudio();
        return;
      }
      this.stopCurrentAudio();
      Api.voiceClone.getAudioId(row.id, (res) => {
        res = res.data;
        if (res.code === 0) {
          const uuid = res.data;
          const audioUrl = Api.voiceClone.getPlayVoiceUrl(uuid);
          const audio = new Audio(audioUrl);
          this.currentAudio = audio;
          this.playingRowId = row.id;
          audio.addEventListener('ended', () => {
            this.playingRowId = null;
            this.currentAudio = null;
          });
          audio.addEventListener('error', () => {
            this.playingRowId = null;
            this.currentAudio = null;
          });
          audio.play().catch(err => {
            console.error('Playback failed:', err);
            this.$message.error(this.$t('voiceClone.playFailed') || 'Playback failed');
            this.playingRowId = null;
            this.currentAudio = null;
          });
        } else {
          this.$message.error(res.msg || this.$t('voiceClone.audioNotExist') || 'Audio not found');
        }
      });
    },
    stopCurrentAudio() {
      if (this.currentAudio) {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio = null;
      }
      this.playingRowId = null;
    },
    handleUpload(row) {
      this.currentVoiceClone = row;
      this.cloneDialogVisible = true;
    }
  }
};
</script>

<style lang="scss" scoped>
@import '@/styles/global.scss';

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
    // Top 63px, bottom 35px, search 72px
    height: calc(100vh - 63px - 35px - 72px);
    margin: 0 22px;
    border-radius: 15px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    position: relative;
    background: rgba(237, 242, 255, 0.5);
    display: flex;
    flex-direction: column;
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

/* Status button styles */
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

.voice-clone-grid {
  padding: 10px 16px;
  margin-bottom: 20px;
  height: calc(100% - 90px);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
  align-content: start;
  min-height: 200px;
  overflow: auto;
  @include scrollbar-style;
}

.voice-clone-card {
  display: flex;
  flex-direction: column; 
  gap: 14px;
  padding: 16px 16px 8px;
  background: #fff;
  box-shadow: 0 0 10px 0 #e8ecf5;
  border-radius: 8px;
  transition: box-shadow 0.2s, border-color 0.2s;

  &:hover {
    border-color: #c0caff;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  }
}

.card-top {
  display: flex;
  gap: 12px;
}

.voice-wave {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  flex: 1;
  min-height: 40px;
  width: 100%;
  padding: 0 4px;

  .wave-bar {
    width: 3px;
    height: 50%;
    max-height: 80px;
    background: linear-gradient(to top, #a5b4fc 0%, #c4b5fd 100%);
    border-radius: 2px;
    transform-origin: center;
    animation: voice-wave 1.2s ease-in-out infinite paused;

    &:nth-child(1) { animation-delay: -0s; }
    &:nth-child(2) { animation-delay: -0.12s; }
    &:nth-child(3) { animation-delay: -0.24s; }
    &:nth-child(4) { animation-delay: -0.36s; }
    &:nth-child(5) { animation-delay: -0.48s; }
    &:nth-child(6) { animation-delay: -0.6s; }
    &:nth-child(7) { animation-delay: -0.72s; }
    &:nth-child(8) { animation-delay: -0.84s; }
    &:nth-child(9) { animation-delay: -0.96s; }
    &:nth-child(10) { animation-delay: -1.08s; }
    &:nth-child(11) { animation-delay: -1.2s; }
  }

  &.is-playing .wave-bar {
    animation-play-state: running;
  }
}

@keyframes voice-wave {
  0%, 100% { transform: scaleY(0.2); }
  50% { transform: scaleY(0.95); }
}

.card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 12px;
}

.info-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
}

.info-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  flex-shrink: 0;
  min-width: 100px;
}

.info-title {
  min-width: 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;

  .name-text {
    line-height: 28px;
    text-align: left;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  font-size: 13px;
  line-height: 1.5;
}

.info-label {
  margin-right: 10px;
  color: #909399;
  flex-shrink: 0;
}

.info-value {
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 8px;
  padding-top: 10px;
  border-top: 1px solid #f0f2f5;

  ::v-deep .el-button {
    display: flex;
    align-items: center;
  }

  ::v-deep .el-button--text {
    color: #7079aa;
  }

  ::v-deep .el-button--text:hover {
    color: #5a64b5;
  }
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #909399;
  font-size: 14px;
}
</style>