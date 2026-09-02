<template>
  <div class="custom-table-wrapper">
    <div class="table-container" :style="{ height: tableContainerHeight }">
      <el-table
        ref="tableRef"
        :data="data"
        :class="['custom-table', tableClass]"
        height="100%"
        v-loading="loading"
        :element-loading-text="loadingText"
        :element-loading-spinner="loadingSpinner"
        :element-loading-background="loadingBackground"
        :header-cell-class-name="headerCellClassName"
        :row-class-name="rowClassName"
        @selection-change="handleSelectionChange"
        @row-click="handleRowClick"
      >
        <!-- 选择列 -->
        <el-table-column
          v-if="showSelection"
          width="55"
          align="center"
          label="选择"
        >
          <template slot-scope="scope">
            <slot
              v-if="$scopedSlots.selection"
              name="selection"
              :row="scope.row"
              :$index="scope.$index"
            />
            <el-checkbox
              v-else
              :value="scope.row.selected"
              @change="handleCheckboxChange(scope.row)"
            />
          </template>
        </el-table-column>

        <!-- 动态列 -->
        <el-table-column
          v-for="column in columns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="column.width"
          :min-width="column.minWidth"
          :align="column.align || 'center'"
          :show-overflow-tooltip="column.showOverflowTooltip !== false"
        >
          <template slot-scope="scope">
            <!-- 自定义插槽：优先使用 column.slot 指定的插槽名，否则用 column.prop 作为插槽名 -->
            <slot
              v-if="$scopedSlots[column.slot] || $scopedSlots[column.prop]"
              :name="column.slot || column.prop"
              :row="scope.row"
              :$index="scope.$index"
              :column="column"
            />
            <!-- 默认显示 -->
            <template v-else>
              {{ scope.row[column.prop] }}
            </template>
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column
          v-if="showOperations"
          :label="operationsLabel"
          align="center"
          :width="operationsWidth"
        >
          <template slot-scope="scope">
            <slot name="operations" :row="scope.row" :$index="scope.$index" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="table-footer">
      <slot name="footer-btns"></slot>
      <CustomPagination
        v-if="showPagination"
        :total="total"
        :current-page="currentPage"
        :page-size="pageSize"
        :page-size-options="pageSizeOptions"
        @size-change="handleSizeChange"
        @page-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script>
import CustomPagination from './CustomPagination.vue';

export default {
  name: 'CustomTable',
  components: {
    CustomPagination
  },
  props: {
    // 表格数据
    data: {
      type: Array,
      default: () => []
    },
    // 列配置
    columns: {
      type: Array,
      default: () => []
    },
    // 是否显示选择框
    showSelection: {
      type: Boolean,
      default: false
    },
    // 是否显示操作列
    showOperations: {
      type: Boolean,
      default: false
    },
    operationsLabel: {
      type: String,
      default: '操作'
    },
    operationsWidth: {
      type: [String, Number],
      default: 180
    },
    // 分页相关
    showPagination: {
      type: Boolean,
      default: true
    },
    total: {
      type: Number,
      default: 0
    },
    currentPage: {
      type: Number,
      default: 1
    },
    pageSize: {
      type: Number,
      default: 10
    },
    pageSizeOptions: {
      type: Array,
      default: () => [10, 20, 50, 100]
    },
    // 加载状态
    loading: {
      type: Boolean,
      default: false
    },
    loadingText: {
      type: String,
      default: 'Loading'
    },
    loadingSpinner: {
      type: String,
      default: 'el-icon-loading'
    },
    loadingBackground: {
      type: String,
      default: 'rgba(255, 255, 255, 0.7)'
    },
    // 自定义类名
    tableClass: {
      type: String,
      default: ''
    },
    headerCellClassName: {
      type: String,
      default: ''
    },
    rowClassName: {
      type: [String, Function],
      default: ''
    },
  },
  computed: {
    tableContainerHeight() {
      return this.showPagination ? 'calc(100% - 48px)' : '100%';
    }
  },
  methods: {
    // 复选框变化
    handleCheckboxChange(row) {
      this.$set(row, 'selected', !row.selected);
    },
    // 分页事件
    handleSizeChange(val) {
      this.$emit('size-change', val);
    },
    handlePageChange(page) {
      this.$emit('page-change', page);
    },
    // 选择事件
    handleSelectionChange(selection) {
      this.$emit('selection-change', selection);
    },
    // 行点击事件
    handleRowClick(row, column, event) {
      this.$emit('row-click', row, column, event);
    },
    // 清除选择
    clearSelection() {
      this.$refs.tableRef && this.$refs.tableRef.clearSelection();
    },
    // 切换选择
    toggleRowSelection(row, selected) {
      this.$refs.tableRef && this.$refs.tableRef.toggleRowSelection(row, selected);
    }
  }
};
</script>

<style scoped lang="scss">
.custom-table-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  .table-container {
    width: 100%;
    box-shadow: 0 2px 12px rgba(74, 124, 253, 0.12);
    border-radius: 6px;
    .custom-table {
      width: 100%;
      border: 1px solid #eef3fd;
      border-bottom: none;
      border-radius: 6px;
      .el-table__body-wrapper {
        overflow-y: auto;
        &::-webkit-scrollbar {
          width: 6px;
        }
        &::-webkit-scrollbar-thumb {
          background: #a1c9fd;
          border-radius: 3px;
        }
        &::-webkit-scrollbar-track {
          background: #f0f3fe;
          border-radius: 3px;
        }
      }
      .el-table__header {
        th {
          color: #342f45;
          background: #edf2fc !important;
        }
      }
    }
  }
}
:deep(.el-table) {
  .el-table__body-wrapper {
    overflow-y: auto;
    &::-webkit-scrollbar {
      width: 6px;
    }
    &::-webkit-scrollbar-thumb {
      background: #a1c9fd;
      border-radius: 3px;
    }
    &::-webkit-scrollbar-track {
      background: #f0f3fe;
      border-radius: 3px;
    }
  }
  .el-table__header {
    th {
      color: #342f45;
      background: #edf2fc !important;
    }
  }
}
.table-footer {
  padding: 16px 0px 0px;
  display: flex;
  align-items: center;
  justify-content: space-between;
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
