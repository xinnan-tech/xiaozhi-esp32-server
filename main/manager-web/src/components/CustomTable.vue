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
        <!-- Select column -->
        <el-table-column
          v-if="showSelection"
          width="55"
          align="center"
          label="Select"
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

        <!-- Dynamic column -->
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
            <!-- Custom slots: Prioritize the slot name specified by column.slot, otherwise use column.prop as the slot name -->
            <slot
              v-if="$scopedSlots[column.slot] || $scopedSlots[column.prop]"
              :name="column.slot || column.prop"
              :row="scope.row"
              :$index="scope.$index"
              :column="column"
            />
            <!-- Visible by Default -->
            <template v-else>
              {{ scope.row[column.prop] }}
            </template>
          </template>
        </el-table-column>

        <!-- Action column -->
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

    <!-- Pagination -->
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
    // Table data
    data: {
      type: Array,
      default: () => []
    },
    // Column config
    columns: {
      type: Array,
      default: () => []
    },
    // Show selection box
    showSelection: {
      type: Boolean,
      default: false
    },
    // Show action column
    showOperations: {
      type: Boolean,
      default: false
    },
    operationsLabel: {
      type: String,
      default: 'Action'
    },
    operationsWidth: {
      type: [String, Number],
      default: 180
    },
    // Pagination Related
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
    // Loading status
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
    // Custom class name
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
    // Checkbox change
    handleCheckboxChange(row) {
      this.$set(row, 'selected', !row.selected);
    },
    // Pagination Events
    handleSizeChange(val) {
      this.$emit('size-change', val);
    },
    handlePageChange(page) {
      this.$emit('page-change', page);
    },
    // Select Event
    handleSelectionChange(selection) {
      this.$emit('selection-change', selection);
    },
    // Row click event
    handleRowClick(row, column, event) {
      this.$emit('row-click', row, column, event);
    },
    // Clear selection
    clearSelection() {
      this.$refs.tableRef && this.$refs.tableRef.clearSelection();
    },
    // Toggle Selection
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
