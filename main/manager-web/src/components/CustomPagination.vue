<template>
  <div class="pagination-wrapper">
    <el-pagination
      :current-page="currentPage"
      :page-size="pageSize"
      :page-sizes="pageSizeOptions"
      :total="total"
      layout="sizes, prev, pager, next, total"
      background
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />
  </div>
</template>

<script>
export default {
  name: 'Pagination',
  props: {
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
    }
  },
  methods: {
    handleSizeChange(val) {
      this.$emit('size-change', val);
    },
    handlePageChange(page) {
      this.$emit('page-change', page);
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .el-pagination {
  .btn-next,
  .btn-prev,
  .el-pager li {
    background: transparent !important;
    min-width: 36px !important;
  }
  .el-pager li:not(.disabled).active {
    background: linear-gradient(135deg, #2a6dfe 0%, #6b8cff 50%, #2a6dfe 100%) !important;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(45, 111, 254, 0.3);
    color: #fff;
    font-weight: 600;
    text-shadow: 0 1px 1px rgba(0, 0, 0, 0.15);
  }
}
</style>
