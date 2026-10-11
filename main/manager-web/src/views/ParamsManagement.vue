<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="params-card" shadow="never">
            <div class="operation-header">
              <div class="title-block">
                <h2 class="page-title">{{ $t('paramManagement.pageTitle') }}</h2>
                <span class="total-hint">{{ $t('paramManagement.totalRecords', { total: filteredTotal }) }}</span>
              </div>
              <div class="right-operations">
                <el-input
                  :placeholder="$t('paramManagement.searchPlaceholder')"
                  v-model="searchCode"
                  class="search-input"
                  @keyup.enter.native="handleSearch"
                  @clear="handleSearch"
                  clearable
                />
                <CustomButton icon="el-icon-search" type="confirm" @click="handleSearch">
                  {{ $t('paramManagement.search') }}
                </CustomButton>
              </div>
            </div>

        <div class="main-wrapper">
            <div class="content-panel">
                <div class="content-area">
                    <el-card class="params-card" shadow="never">
                        <el-table ref="paramsTable" :data="paramsList" class="transparent-table" v-loading="loading"
                            element-loading-text="Loading" element-loading-spinner="el-icon-loading"
                            element-loading-background="rgba(255, 255, 255, 0.7)"
                            :header-cell-class-name="headerCellClassName">
                            <el-table-column :label="$t('modelConfig.select')" align="center" width="120">
                                <template slot-scope="scope">
                                    <el-checkbox v-model="scope.row.selected"></el-checkbox>
                                </template>
                            </el-table-column>
                            <el-table-column :label="$t('paramManagement.paramCode')" prop="paramCode"
                                align="center"></el-table-column>
                            <el-table-column :label="$t('paramManagement.paramValue')" prop="paramValue" align="center"
                                show-overflow-tooltip>
                                <template slot-scope="scope">
                                    <div v-if="isSensitiveParam(scope.row.paramCode)">
                                        <span v-if="!scope.row.showValue">{{ maskSensitiveValue(scope.row.paramValue)
                                        }}</span>
                                        <span v-else>{{ scope.row.paramValue }}</span>
                                        <el-button size="mini" type="text" @click="toggleSensitiveValue(scope.row)">
                                            {{ scope.row.showValue ? $t('paramManagement.hide') :
                                                $t('paramManagement.view') }}
                                        </el-button>
                                    </div>
                                    <span v-else>{{ scope.row.paramValue }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column :label="$t('paramManagement.remark')" prop="remark"
                                align="center"></el-table-column>
                            <el-table-column :label="$t('paramManagement.operation')" align="center">
                                <template slot-scope="scope">
                                    <el-button size="mini" type="text" @click="editParam(scope.row)">{{
                                        $t('paramManagement.edit') }}</el-button>
                                    <el-button size="mini" type="text" @click="deleteParam(scope.row)">{{
                                        $t('paramManagement.delete') }}</el-button>
                                </template>
                            </el-table-column>
                        </el-table>

                        <div class="table_bottom">
                            <div class="ctrl_btn">
                                <el-button size="mini" type="primary" class="select-all-btn" @click="handleSelectAll">
                                    {{ isAllSelected ? $t('paramManagement.deselectAll') :
                                        $t('paramManagement.selectAll') }}
                                </el-button>
                                <el-button size="mini" type="success" @click="showAddDialog">{{
                                    $t('paramManagement.add') }}</el-button>
                                <el-button size="mini" type="danger" icon="el-icon-delete"
                                    @click="deleteSelectedParams">{{
                                        $t('paramManagement.delete') }}</el-button>
                            </div>
                            <div class="custom-pagination">
                                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                                    <el-option v-for="item in pageSizeOptions" :key="item"
                                        :label="`${item}${$t('paramManagement.itemsPerPage')}`" :value="item">
                                    </el-option>
                                </el-select>
                                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">
                                    {{ $t('paramManagement.firstPage') }}
                                </button>
                                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">
                                    {{ $t('paramManagement.prevPage') }}
                                </button>
                                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                                    :class="{ active: page === currentPage }" @click="goToPage(page)">
                                    {{ page }}
                                </button>
                                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">
                                    {{ $t('paramManagement.nextPage') }}
                                </button>
                                <span class="total-text">{{ $t('paramManagement.totalRecords', { total }) }}</span>
                            </div>
                        </div>
                    </el-card>
                </div>
            </div>

        <!-- Add/Edit parameter dialog -->
        <param-dialog ref="paramDialog" :title="dialogTitle" :visible.sync="dialogVisible" :form="paramForm"
            @submit="handleSubmit" @cancel="dialogVisible = false" />
        <el-footer>
            <version-footer />
        </el-footer>
    </div>

    <param-dialog
      ref="paramDialog"
      :title="dialogTitle"
      :visible.sync="dialogVisible"
      :form="paramForm"
      @submit="handleSubmit"
      @cancel="dialogVisible = false"
    />
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
import CustomButton from "@/components/CustomButton.vue";

const TOP_GROUP_ORDER = ['server', 'plugins', 'log', 'session_state', 'general'];
const FETCH_LIMIT = 500;

const SERVER_SUB_ORDER = [
  '_root', 'auth', 'connection', 'registry', 'resilience', 'metrics', 'tracing'
];

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
                valueType: "string",
                remark: ""
            },
        };
    },
    filteredTotal() {
      return this.filteredParams.length;
    },
    selectedCount() {
      return this.filteredParams.filter(item => item.selected).length;
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
                            valueType: item.valueType || "string",
                            selected: false,
                            showValue: false
                        }));
                        this.total = data.data.total;
                    } else {
                        this.$message.error({
                            message: data.msg || this.$t('paramManagement.getParamsListFailed'),
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
            this.dialogTitle = this.$t('paramManagement.addParam');
            this.paramForm = {
                id: null,
                paramCode: "",
                paramValue: "",
                valueType: "string", // Default value
                remark: ""
            };
            this.dialogVisible = true;
        },
        editParam(row) {
            this.dialogTitle = this.$t('paramManagement.editParam');
            this.paramForm = {
                id: row.id,
                paramCode: row.paramCode,
                paramValue: row.paramValue,
                valueType: row.valueType || "string", // Ensure has value
                remark: row.remark
            };
            this.dialogVisible = true;
        },
        handleSubmit(form) {
            if (form.id) {
                // Update parameter
                Api.admin.updateParam(form, ({ data }) => {
                    this.dialogVisible = false;
                    this.fetchParams();
                    this.$message.success({
                        message: this.$t('paramManagement.updateSuccess'),
                        showClose: true
                    });
                }, ({ data }) => {
                    this.$message.error({
                        message: data.msg || this.$t('paramManagement.updateFailed'),
                        showClose: true
                    });
                    // Call ParamDialog resetSaving method to reset save status
                    if (this.$refs.paramDialog && typeof this.$refs.paramDialog.resetSaving === 'function') {
                        this.$refs.paramDialog.resetSaving();
                    }
                });
            } else {
                // Add parameter
                Api.admin.addParam(form, ({ data }) => {
                    if (data.code === 0) {
                        this.dialogVisible = false;
                        this.fetchParams();
                        this.$message.success({
                            message: this.$t('paramManagement.addSuccess'),
                            showClose: true
                        });
                    } else {
                        this.$message.error({
                            message: data.msg || this.$t('paramManagement.addFailed'),
                            showClose: true
                        });
                        // Call ParamDialog resetSaving method to reset save status
                        if (this.$refs.paramDialog && typeof this.$refs.paramDialog.resetSaving === 'function') {
                            this.$refs.paramDialog.resetSaving();
                        }
                    }
                });
            }
        },
        deleteSelectedParams() {
            const selectedParams = this.paramsList.filter(row => row.selected);
            if (selectedParams.length === 0) {
                this.$message.warning({
                    message: this.$t('paramManagement.selectParamsFirst'),
                    showClose: true
                });
                return;
            }
            this.deleteParams(selectedParams);
        },
        deleteParam(row) {
            if (!row.id) {
                this.$message.warning({
                    message: this.$t('paramManagement.selectParamsFirst'),
                    showClose: true
                });
                return;
            }
            this.deleteParams([row]);
        },
        deleteParams(params) {
            const paramCount = params.length;
            const paramIds = params.map(param => param.id).filter(id => id);
            if (paramIds.length === 0) {
                this.$message.error({
                    message: this.$t('paramManagement.invalidParamId'),
                    showClose: true
                });
                return;
            }
            this.$confirm(this.$t('paramManagement.confirmBatchDelete', { paramCount }), this.$t('message.warning'), {
                confirmButtonText: this.$t('button.ok'),
                cancelButtonText: this.$t('button.cancel'),
                type: 'warning'
            }).then(() => {
                Api.admin.deleteParam(paramIds, ({ data }) => {
                    if (data.code === 0) {
                        this.fetchParams();
                        this.$message.success({
                            message: this.$t('paramManagement.batchDeleteSuccess', { paramCount }),
                            showClose: true
                        });
                    } else {
                        this.$message.error({
                            message: data.msg || this.$t('paramManagement.deleteFailed'),
                            showClose: true
                        });
                    }
                });
            }).catch(() => {
                this.$message({
                    type: 'info',
                    message: this.$t('paramManagement.operationCancelled'),
                    duration: 1000
                });
            });
        },
        goToPage(page) {
            if (page !== this.currentPage) {
                this.currentPage = page;
                this.fetchParams();
            }
        },
        goFirst() {
            if (this.currentPage !== 1) {
                this.currentPage = 1;
                this.fetchParams();
            }
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
        isSensitiveParam(paramCode) {
            return this.sensitive_keys.some(key => paramCode.toLowerCase().includes(key));
        },
        maskSensitiveValue(value) {
            if (value.length <= 4) {
                return '****';
            }
            return value.substring(0, 2) + '****' + value.substring(value.length - 2);
        },
        toggleSensitiveValue(row) {
            row.showValue = !row.showValue;
        },
        headerCellClassName() {
            return 'header-cell';
        }
    }
  },
  watch: {
    displaySections: {
      immediate: true,
      handler(sections) {
        const keys = sections.map(s => s.key);
        if (!keys.length) {
          this.activeCollapse = [];
          this.isAllSelected = false;
          return;
        }
        // 分组不多时全部展开；较多时默认展开前几组
        const preferOpen = keys.length <= 5 ? keys.slice() : keys.slice(0, 3);
        const stillValid = (this.activeCollapse || []).filter(k => keys.includes(k));
        this.activeCollapse = stillValid.length ? stillValid : preferOpen;
        this.syncSelectAllState();
      }
    },
    categoryTabs(tabs) {
      if (!tabs.some(t => t.key === this.activeCategory)) {
        this.activeCategory = 'all';
        this.activeSubCategory = 'all';
      }
    }
  },
  created() {
    this.fetchParams();
  },
  methods: {
    getTopGroup(paramCode = '') {
      if (paramCode.startsWith('server.')) return 'server';
      if (paramCode.startsWith('plugins.')) return 'plugins';
      if (paramCode.startsWith('log.')) return 'log';
      if (paramCode.startsWith('session_state.')) return 'session_state';
      return 'general';
    },
    getSubGroup(paramCode = '') {
      const top = this.getTopGroup(paramCode);
      const parts = paramCode.split('.');
      if (top === 'server') {
        return parts.length >= 3 ? parts[1] : '_root';
      }
      if (top === 'plugins') {
        return parts.length >= 3 ? parts[1] : '_root';
      }
      if (top === 'log' || top === 'session_state') {
        return '_all';
      }
      return '_all';
    },
    getTopGroupLabel(key) {
      const map = {
        server: 'paramManagement.group.server',
        plugins: 'paramManagement.group.plugins',
        log: 'paramManagement.group.log',
        session_state: 'paramManagement.group.session',
        general: 'paramManagement.group.general'
      };
      return this.$t(map[key] || 'paramManagement.group.general');
    },
    getSubGroupLabel(top, sub) {
      if (sub === '_all') return this.getTopGroupLabel(top);
      if (sub === '_root') return this.$t('paramManagement.subgroup.root');

      const known = {
        'server.auth': 'paramManagement.subgroup.auth',
        'server.connection': 'paramManagement.subgroup.connection',
        'server.registry': 'paramManagement.subgroup.registry',
        'server.resilience': 'paramManagement.subgroup.resilience',
        'server.metrics': 'paramManagement.subgroup.metrics',
        'server.tracing': 'paramManagement.subgroup.tracing'
      };
      const i18nKey = known[`${top}.${sub}`];
      if (i18nKey) return this.$t(i18nKey);

      if (top === 'plugins') {
        return this.$t('paramManagement.subgroup.plugin', { name: sub });
      }
      return sub;
    },
    orderSubKeys(keys, top) {
      if (top === 'server') {
        return [
          ...SERVER_SUB_ORDER.filter(k => keys.includes(k)),
          ...keys.filter(k => !SERVER_SUB_ORDER.includes(k)).sort()
        ];
      }
      return keys.slice().sort((a, b) => {
        if (a === '_root' || a === '_all') return -1;
        if (b === '_root' || b === '_all') return 1;
        return a.localeCompare(b);
      });
    },
    buildSections(items, withinTopCategory) {
      const bucket = {};
      items.forEach(item => {
        const top = this.getTopGroup(item.paramCode);
        const sub = this.getSubGroup(item.paramCode);
        const key = withinTopCategory ? `${top}.${sub}` : `${top}.${sub}`;
        if (!bucket[key]) {
          bucket[key] = {
            key,
            top,
            sub,
            items: []
          };
        }
        bucket[key].items.push(item);
      });

      const sections = Object.values(bucket).map(section => {
        const label = withinTopCategory
          ? this.getSubGroupLabel(section.top, section.sub)
          : (section.sub === '_all' || section.sub === '_root'
            ? this.getTopGroupLabel(section.top)
            : `${this.getTopGroupLabel(section.top)} · ${this.getSubGroupLabel(section.top, section.sub)}`);
        return {
          key: section.key,
          label,
          hint: withinTopCategory ? null : null,
          items: section.items.slice().sort((a, b) => a.paramCode.localeCompare(b.paramCode)),
          _top: section.top,
          _sub: section.sub
        };
      });

      sections.sort((a, b) => {
        const topDiff = TOP_GROUP_ORDER.indexOf(a._top) - TOP_GROUP_ORDER.indexOf(b._top);
        if (topDiff !== 0) return topDiff;
        const orderA = this.orderSubKeys([a._sub, b._sub], a._top);
        return orderA.indexOf(a._sub) - orderA.indexOf(b._sub);
      });

      return sections;
    },
    selectCategory(key) {
      if (this.activeCategory === key) return;
      this.activeCategory = key;
      this.activeSubCategory = 'all';
      this.isAllSelected = false;
      this.allParams.forEach(row => { row.selected = false; });
    },
    selectSubCategory(key) {
      if (this.activeSubCategory === key) return;
      this.activeSubCategory = key;
      this.isAllSelected = false;
      this.filteredParams.forEach(row => { row.selected = false; });
      this.syncSelectAllState();
    },
    fetchParamsPage(page) {
      return new Promise((resolve, reject) => {
        Api.admin.getParamsList(
          {
            page,
            limit: FETCH_LIMIT,
            paramCode: ""
          },
          ({ data }) => {
            if (data.code === 0) {
              resolve(data.data || {});
            } else {
              reject(new Error(data.msg || this.$t('paramManagement.getParamsListFailed')));
            }
          }
        );
      });
    },
    async fetchParams() {
      this.loading = true;
      try {
        const collected = [];
        let page = 1;
        let total = Infinity;
        // 按 total 循环拉全部分页，避免超过 FETCH_LIMIT 时聚合视图缺数据
        while (collected.length < total) {
          const pageData = await this.fetchParamsPage(page);
          const list = pageData.list || [];
          total = typeof pageData.total === 'number' ? pageData.total : collected.length + list.length;
          collected.push(...list);
          if (!list.length) break;
          page += 1;
          // 防御：异常 total / 接口异常时避免死循环
          if (page > 200) break;
        }

        this.allParams = collected.map(item => ({
          ...item,
          valueType: item.valueType || "string",
          selected: false,
          showValue: false
        }));
        this.isAllSelected = false;

        // 若当前分类已无数据，回退到全部
        const exists = this.categoryTabs.some(t => t.key === this.activeCategory);
        if (!exists) {
          this.activeCategory = 'all';
          this.activeSubCategory = 'all';
        }
      } catch (err) {
        this.$message.error({
          message: (err && err.message) || this.$t('paramManagement.getParamsListFailed'),
          showClose: true
        });
      } finally {
        this.loading = false;
      }
    },
    handleSearch() {
      this.appliedSearch = this.searchCode;
      this.activeSubCategory = 'all';
      this.$nextTick(() => {
        if (!this.categoryTabs.some(t => t.key === this.activeCategory)) {
          this.activeCategory = 'all';
        }
        this.syncSelectAllState();
      });
    },
    syncSelectAllState() {
      const list = this.filteredParams;
      this.isAllSelected = list.length > 0 && list.every(row => row.selected);
    },
    handleSelectAll() {
      this.isAllSelected = !this.isAllSelected;
      this.filteredParams.forEach(row => {
        row.selected = this.isAllSelected;
      });
    },
    formatValue(value) {
      if (value == null) return '';
      const text = String(value);
      return text.length > 120 ? `${text.slice(0, 120)}…` : text;
    },
    showAddDialog() {
      this.dialogTitle = this.$t('paramManagement.addParam');
      this.paramForm = {
        id: null,
        paramCode: "",
        paramValue: "",
        valueType: "string",
        remark: ""
      };
      this.dialogVisible = true;
    },
    editParam(row) {
      this.dialogTitle = this.$t('paramManagement.editParam');
      this.paramForm = {
        id: row.id,
        paramCode: row.paramCode,
        paramValue: row.paramValue,
        valueType: row.valueType || "string",
        remark: row.remark
      };
      this.dialogVisible = true;
    },
    handleSubmit(form) {
      if (form.id) {
        Api.admin.updateParam(form, ({ data }) => {
          this.dialogVisible = false;
          this.fetchParams();
          this.$message.success({
            message: this.$t('paramManagement.updateSuccess'),
            showClose: true
          });
        }, ({ data }) => {
          this.$message.error({
            message: data.msg || this.$t('paramManagement.updateFailed'),
            showClose: true
          });
          if (this.$refs.paramDialog && typeof this.$refs.paramDialog.resetSaving === 'function') {
            this.$refs.paramDialog.resetSaving();
          }
        });
      } else {
        Api.admin.addParam(form, ({ data }) => {
          if (data.code === 0) {
            this.dialogVisible = false;
            this.fetchParams();
            this.$message.success({
              message: this.$t('paramManagement.addSuccess'),
              showClose: true
            });
          } else {
            this.$message.error({
              message: data.msg || this.$t('paramManagement.addFailed'),
              showClose: true
            });
            if (this.$refs.paramDialog && typeof this.$refs.paramDialog.resetSaving === 'function') {
              this.$refs.paramDialog.resetSaving();
            }
          }
        }, ({ data }) => {
          this.$message.error({
            message: data.msg || this.$t('paramManagement.updateFailed'),
            showClose: true
          });
          if (this.$refs.paramDialog && typeof this.$refs.paramDialog.resetSaving === 'function') {
            this.$refs.paramDialog.resetSaving();
          }
        });
      }
    },
    deleteSelectedParams() {
      const selectedParams = this.filteredParams.filter(row => row.selected);
      if (selectedParams.length === 0) {
        this.$message.warning({
          message: this.$t('paramManagement.selectParamsFirst'),
          showClose: true
        });
        return;
      }
      this.deleteParams(selectedParams);
    },
    deleteParam(row) {
      if (!row.id) {
        this.$message.warning({
          message: this.$t('paramManagement.selectParamsFirst'),
          showClose: true
        });
        return;
      }
      this.deleteParams([row]);
    },
    deleteParams(params) {
      const paramCount = params.length;
      const paramIds = params.map(param => param.id).filter(id => id);
      if (paramIds.length === 0) {
        this.$message.error({
          message: this.$t('paramManagement.invalidParamId'),
          showClose: true
        });
        return;
      }
      this.$confirm(this.$t('paramManagement.confirmBatchDelete', { paramCount }), this.$t('message.warning'), {
        confirmButtonText: this.$t('button.ok'),
        cancelButtonText: this.$t('button.cancel'),
        type: 'warning'
      }).then(() => {
        Api.admin.deleteParam(paramIds, ({ data }) => {
          if (data.code === 0) {
            this.fetchParams();
            this.$message.success({
              message: this.$t('paramManagement.batchDeleteSuccess', { paramCount }),
              showClose: true
            });
          } else {
            this.$message.error({
              message: data.msg || this.$t('paramManagement.deleteFailed'),
              showClose: true
            });
          }
        });
      }).catch(() => {
        this.$message({
          type: 'info',
          message: this.$t('paramManagement.operationCancelled'),
          duration: 1000
        });
      });
    },
    isSensitiveParam(paramCode) {
      return this.sensitive_keys.some(key => paramCode.toLowerCase().includes(key));
    },
    maskSensitiveValue(value) {
      if (!value || value.length <= 4) {
        return '****';
      }
      return value.substring(0, 2) + '****' + value.substring(value.length - 2);
    },
    toggleSensitiveValue(row) {
      row.showValue = !row.showValue;
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
  background: #eff4ff;
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

.operation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 12px 0;
  gap: 16px;
}

.title-block {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-title {
  font-weight: 500;
  font-size: 24px;
  margin: 0;
}

.total-hint {
  color: #8b93b5;
  font-size: 13px;
}

.right-operations {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.search-input {
  width: 280px;
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
  overflow: hidden;
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
    min-height: 0;
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
  flex-wrap: wrap;
  gap: 0;
}

.footer-meta {
  color: #8b93b5;
  font-size: 12px;
  white-space: nowrap;

  .sep {
    margin: 0 6px;
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
