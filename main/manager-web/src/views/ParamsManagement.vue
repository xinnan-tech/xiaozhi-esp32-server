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

            <!-- 一级分类 -->
            <div class="group-tabs" v-loading="loading && !allParams.length">
              <button
                v-for="tab in categoryTabs"
                :key="tab.key"
                type="button"
                class="group-tab"
                :class="{ active: activeCategory === tab.key }"
                @click="selectCategory(tab.key)"
              >
                <span class="group-tab-label">{{ tab.label }}</span>
                <span class="group-tab-count">{{ tab.count }}</span>
              </button>
            </div>

            <!-- 二级子分类 -->
            <div class="sub-tabs" v-if="subCategoryTabs.length > 1">
              <button
                v-for="tab in subCategoryTabs"
                :key="tab.key"
                type="button"
                class="sub-tab"
                :class="{ active: activeSubCategory === tab.key }"
                @click="selectSubCategory(tab.key)"
              >
                {{ tab.label }}
                <em>{{ tab.count }}</em>
              </button>
            </div>

            <div class="params-body" v-loading="loading">
              <template v-if="displaySections.length">
                <el-collapse v-model="activeCollapse" class="params-collapse">
                  <el-collapse-item
                    v-for="section in displaySections"
                    :key="section.key"
                    :name="section.key"
                  >
                    <template slot="title">
                      <div class="section-title">
                        <span class="section-name">{{ section.label }}</span>
                        <span class="section-count">{{ section.items.length }}</span>
                        <span v-if="section.hint" class="section-hint">{{ section.hint }}</span>
                      </div>
                    </template>
                    <el-table
                      :data="section.items"
                      class="params-table"
                      size="small"
                      :header-cell-class-name="'params-table-header'"
                    >
                      <el-table-column width="48" align="center" :label="$t('paramManagement.select')">
                        <template slot-scope="scope">
                          <el-checkbox v-model="scope.row.selected" @change="syncSelectAllState" />
                        </template>
                      </el-table-column>
                      <el-table-column
                        prop="paramCode"
                        :label="$t('paramManagement.paramCode')"
                        min-width="220"
                        show-overflow-tooltip
                      >
                        <template slot-scope="scope">
                          <code class="param-code">{{ scope.row.paramCode }}</code>
                        </template>
                      </el-table-column>
                      <el-table-column
                        :label="$t('paramManagement.valueType')"
                        width="90"
                        align="center"
                      >
                        <template slot-scope="scope">
                          <span class="type-tag" :class="'type-' + (scope.row.valueType || 'string')">
                            {{ scope.row.valueType || 'string' }}
                          </span>
                        </template>
                      </el-table-column>
                      <el-table-column
                        :label="$t('paramManagement.paramValue')"
                        min-width="180"
                        show-overflow-tooltip
                      >
                        <template slot-scope="scope">
                          <div class="value-cell" v-if="isSensitiveParam(scope.row.paramCode)">
                            <span class="value-text">
                              {{ scope.row.showValue ? formatValue(scope.row.paramValue) : maskSensitiveValue(scope.row.paramValue) }}
                            </span>
                            <el-button size="mini" type="text" @click="toggleSensitiveValue(scope.row)">
                              {{ scope.row.showValue ? $t('paramManagement.hide') : $t('paramManagement.view') }}
                            </el-button>
                          </div>
                          <span v-else class="value-text">{{ formatValue(scope.row.paramValue) }}</span>
                        </template>
                      </el-table-column>
                      <el-table-column
                        prop="remark"
                        :label="$t('paramManagement.remark')"
                        min-width="200"
                        show-overflow-tooltip
                      />
                      <el-table-column
                        :label="$t('paramManagement.operation')"
                        width="120"
                        align="center"
                        fixed="right"
                      >
                        <template slot-scope="scope">
                          <el-button size="mini" type="text" @click="editParam(scope.row)">
                            {{ $t('paramManagement.edit') }}
                          </el-button>
                          <el-button size="mini" type="text" @click="deleteParam(scope.row)">
                            {{ $t('paramManagement.delete') }}
                          </el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                  </el-collapse-item>
                </el-collapse>
              </template>
              <div v-else class="empty-state">
                {{ $t('paramManagement.emptyResult') }}
              </div>
            </div>

            <div class="table-footer">
              <div class="ctrl_btn">
                <CustomButton
                  :icon="isAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'"
                  size="small"
                  @click="handleSelectAll"
                >
                  {{ isAllSelected ? $t('paramManagement.deselectAll') : $t('paramManagement.selectAll') }}
                </CustomButton>
                <CustomButton icon="el-icon-plus" type="add" size="small" @click="showAddDialog">
                  {{ $t('paramManagement.add') }}
                </CustomButton>
                <CustomButton size="small" type="delete" icon="el-icon-delete" @click="deleteSelectedParams">
                  {{ $t('paramManagement.delete') }}
                </CustomButton>
                <CustomButton
                  icon="el-icon-refresh"
                  size="small"
                  @click="fetchParams"
                >
                  {{ $t('paramManagement.refresh') }}
                </CustomButton>
              </div>
              <div class="footer-meta">
                <span>{{ $t('paramManagement.selectedCount', { count: selectedCount }) }}</span>
                <span class="sep">·</span>
                <span>{{ $t('paramManagement.groupHint') }}</span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
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
  components: { HeaderBar, ParamDialog, VersionFooter, CustomButton },
  data() {
    return {
      searchCode: "",
      appliedSearch: "",
      allParams: [],
      loading: false,
      dialogVisible: false,
      dialogTitle: "",
      isAllSelected: false,
      activeCategory: 'all',
      activeSubCategory: 'all',
      activeCollapse: [],
      sensitive_keys: [
        "api_key", "personal_access_token", "access_token", "token", "secret",
        "access_key_secret", "secret_key", "password", "mqtt_signature_key", "private_key"
      ],
      paramForm: {
        id: null,
        paramCode: "",
        paramValue: "",
        valueType: "string",
        remark: ""
      }
    };
  },
  computed: {
    filteredParams() {
      const keyword = (this.appliedSearch || "").trim().toLowerCase();
      let list = this.allParams;

      if (this.activeCategory !== 'all') {
        list = list.filter(item => this.getTopGroup(item.paramCode) === this.activeCategory);
      }

      if (this.activeSubCategory !== 'all') {
        list = list.filter(item => this.getSubGroup(item.paramCode) === this.activeSubCategory);
      }

      if (keyword) {
        list = list.filter(item => {
          const code = (item.paramCode || "").toLowerCase();
          const remark = (item.remark || "").toLowerCase();
          return code.includes(keyword) || remark.includes(keyword);
        });
      }

      return list;
    },
    filteredTotal() {
      return this.filteredParams.length;
    },
    selectedCount() {
      return this.filteredParams.filter(item => item.selected).length;
    },
    categoryTabs() {
      const keyword = (this.appliedSearch || "").trim().toLowerCase();
      const searchFiltered = keyword
        ? this.allParams.filter(item => {
            const code = (item.paramCode || "").toLowerCase();
            const remark = (item.remark || "").toLowerCase();
            return code.includes(keyword) || remark.includes(keyword);
          })
        : this.allParams;

      const searchCounts = {
        all: searchFiltered.length,
        server: 0,
        plugins: 0,
        log: 0,
        session_state: 0,
        general: 0
      };
      searchFiltered.forEach(item => {
        const key = this.getTopGroup(item.paramCode);
        searchCounts[key] = (searchCounts[key] || 0) + 1;
      });

      return [
        { key: 'all', label: this.$t('paramManagement.group.all'), count: searchCounts.all },
        { key: 'server', label: this.$t('paramManagement.group.server'), count: searchCounts.server },
        { key: 'plugins', label: this.$t('paramManagement.group.plugins'), count: searchCounts.plugins },
        { key: 'log', label: this.$t('paramManagement.group.log'), count: searchCounts.log },
        { key: 'session_state', label: this.$t('paramManagement.group.session'), count: searchCounts.session_state },
        { key: 'general', label: this.$t('paramManagement.group.general'), count: searchCounts.general }
      ].filter(tab => tab.key === 'all' || searchCounts[tab.key] > 0);
    },
    subCategoryTabs() {
      const source = this.activeCategory === 'all'
        ? []
        : this.allParams.filter(item => this.getTopGroup(item.paramCode) === this.activeCategory);

      if (!source.length) return [];

      const keyword = (this.appliedSearch || "").trim().toLowerCase();
      const filtered = keyword
        ? source.filter(item => {
            const code = (item.paramCode || "").toLowerCase();
            const remark = (item.remark || "").toLowerCase();
            return code.includes(keyword) || remark.includes(keyword);
          })
        : source;

      const countMap = {};
      filtered.forEach(item => {
        const sub = this.getSubGroup(item.paramCode);
        countMap[sub] = (countMap[sub] || 0) + 1;
      });

      const keys = Object.keys(countMap);
      if (keys.length <= 1) return [];

      const ordered = this.orderSubKeys(keys, this.activeCategory);
      return [
        { key: 'all', label: this.$t('paramManagement.group.all'), count: filtered.length },
        ...ordered.map(key => ({
          key,
          label: this.getSubGroupLabel(this.activeCategory, key),
          count: countMap[key]
        }))
      ];
    },
    displaySections() {
      const items = this.filteredParams;
      if (!items.length) return [];

      // 选中一级且选中二级（非 all）时，单段展示
      if (this.activeCategory !== 'all' && this.activeSubCategory !== 'all') {
        return [{
          key: `${this.activeCategory}.${this.activeSubCategory}`,
          label: this.getSubGroupLabel(this.activeCategory, this.activeSubCategory),
          hint: this.getTopGroupLabel(this.activeCategory),
          items
        }];
      }

      // 选中某一一级分类：按二级聚合
      if (this.activeCategory !== 'all') {
        return this.buildSections(items, true);
      }

      // 全部：按一级 → 二级聚合为扁平段落（一级·二级）
      return this.buildSections(items, false);
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

.group-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-bottom: 10px;
}

.group-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e4e8f5;
  background: #f7f9ff;
  color: #5a648f;
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s ease;

  &:hover {
    border-color: #b7c3ef;
    color: #3f4c88;
  }

  &.active {
    background: linear-gradient(135deg, #6b8cff, #7a6dff);
    border-color: transparent;
    color: #fff;
    box-shadow: 0 4px 12px rgba(107, 140, 255, 0.28);

    .group-tab-count {
      background: rgba(255, 255, 255, 0.22);
      color: #fff;
    }
  }
}

.group-tab-count {
  min-width: 22px;
  padding: 0 6px;
  height: 20px;
  line-height: 20px;
  border-radius: 10px;
  background: #e8ecfb;
  color: #5a648f;
  font-size: 12px;
  text-align: center;
}

.sub-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 0 12px;
}

.sub-tab {
  border: none;
  background: transparent;
  color: #7079aa;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.15s ease;

  em {
    font-style: normal;
    margin-left: 4px;
    opacity: 0.7;
  }

  &:hover {
    background: #eef2ff;
  }

  &.active {
    background: #e8ecfb;
    color: #4d59a8;
    font-weight: 600;
  }
}

.params-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.params-collapse {
  border: none;

  ::v-deep .el-collapse-item {
    margin-bottom: 10px;
    border: 1px solid #eef1fb;
    border-radius: 10px;
    overflow: hidden;
  }

  ::v-deep .el-collapse-item__header {
    height: 44px;
    line-height: 44px;
    padding: 0 14px;
    background: #f8faff;
    border-bottom: 1px solid transparent;
    font-weight: 500;
    color: #3f4a75;
  }

  ::v-deep .el-collapse-item__wrap {
    border-bottom: none;
  }

  ::v-deep .el-collapse-item__content {
    padding: 0;
  }

  ::v-deep .el-collapse-item.is-active .el-collapse-item__header {
    border-bottom-color: #eef1fb;
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding-right: 8px;
}

.section-name {
  font-size: 14px;
}

.section-count {
  font-size: 12px;
  color: #7b84ad;
  background: #eef1fb;
  border-radius: 10px;
  padding: 0 8px;
  height: 20px;
  line-height: 20px;
}

.section-hint {
  font-size: 12px;
  color: #9aa3c7;
}

.params-table {
  width: 100%;

  ::v-deep .params-table-header {
    background: #fcfdff;
    color: #6a739c;
    font-weight: 500;
  }
}

.param-code {
  font-family: Consolas, 'SF Mono', Monaco, Menlo, monospace;
  font-size: 12px;
  color: #3d4a7a;
  background: #f3f6ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.type-tag {
  display: inline-block;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #eef1f8;
  color: #6a739c;

  &.type-number { background: #e8f5ff; color: #2f7db8; }
  &.type-boolean { background: #e9f8ef; color: #2f8a55; }
  &.type-json,
  &.type-array { background: #f6efff; color: #7a4fb3; }
}

.value-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.value-text {
  color: #4a5378;
  word-break: break-all;
}

.empty-state {
  padding: 64px 0;
  text-align: center;
  color: #9aa3c7;
  font-size: 14px;
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #eef1fb;
  margin-top: 8px;
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
</style>
