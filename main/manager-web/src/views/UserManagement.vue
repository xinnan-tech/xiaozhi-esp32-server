<template>
  <div class="welcome">
    <HeaderBar />
    <el-main class="main" style="padding: 20px; display: flex; flex-direction: column;">
      <div class="top-area">
        <div class="page-title">用户管理</div>
        <div class="page-search">
          <el-input placeholder="请输入手机号码查询" v-model="searchPhone" class="search-input" @keyup.enter.native="handleSearch"/>
          <el-button class="btn-search" @click="handleSearch">搜索</el-button>
        </div>
      </div>

      <el-card class="user-card" shadow="never">
        <el-table :data="userList" class="transparent-table" :header-cell-class-name="headerCellClassName">
          <el-table-column label="选择" type="selection" align="center" width="120"></el-table-column>
          <el-table-column label="用户Id" prop="user_id" align="center"></el-table-column>
          <el-table-column label="手机号码" prop="mobile" align="center"></el-table-column>
          <el-table-column label="设备数量" prop="device_count" align="center"></el-table-column>
          <el-table-column label="状态" prop="status" align="center"></el-table-column>
          <el-table-column label="操作" align="center">
            <template slot-scope="scope">
            <el-button size="mini" type="text" @click="resetPassword(scope.row)" style="color: #989fdd">重置密码</el-button>
            <el-button size="mini" type="text"
              v-if="scope.row.status === '正常'"
              @click="disableUser(scope.row)">禁用账户</el-button>
            <el-button size="mini" type="text"
              v-if="scope.row.status === '禁用'"
              @click="restoreUser(scope.row)">恢复账号</el-button>
            <el-button size="mini" type="text" @click="deleteUser(scope.row)" style="color: #989fdd">删除用户</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="table_bottom">
          <div class="ctrl_btn">
            <el-button size="mini" type="primary" style="width: 72px; background: #5f70f3">全选</el-button>
            <el-button size="mini" type="success" icon="el-icon-circle-check" style="background: #5bc98c">启用</el-button>
            <el-button size="mini" type="warning" style="color: black; background: #f6d075"><i class="el-icon-remove-outline rotated-icon"></i>禁用</el-button>
            <el-button size="mini" type="danger" icon="el-icon-delete" style="background: #fd5b63">删除</el-button>
          </div>
          <div class="custom-pagination">
            <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">首页</button>
            <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">上一页</button>

            <button
              v-for="page in visiblePages"
              :key="page"
              class="pagination-btn"
              :class="{ active: page === currentPage }"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>

            <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">下一页</button>
            <span class="total-text">共{{ total }}条记录</span>
          </div>
        </div>
      </el-card>

      <div style="font-size: 12px; font-weight: 400; margin-top: auto; padding-top: 30px; color: #979db1;">
        ©2025 xiaozhi-esp32-server
      </div>
    </el-main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import adminApi from '@/apis/module/admin';


export default {
  components: { HeaderBar },
  data() {
    return {
      searchPhone: '',
      userList: [],
      originalUserList: [], // 原始数据
      currentPage: 1,
      pageSize: 5,
      total: 20
    };
  },
  created() {
    this.fetchUsers();
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
    }
  },
  methods: {
    // 获取用户列表
    fetchUsers() {
      adminApi.getUserList(({data}) => {
        if (data.code === 0) {
          const responseData = data.data[0] || data.data;
          this.originalUserList = responseData.list.map(user => ({
            ...user,
            status: user.status === '1' ? '正常' : '禁用'
          }));
          this.userList = [...this.originalUserList];
          this.total = responseData.totalCount || 0;
        }
      });
    },

    // 分页变化
    handleCurrentChange(page) {
      this.currentPage = page;
      this.fetchUsers();
    },

    // 搜索
    handleSearch() {
      if (!this.searchPhone) {
        this.userList = [...this.originalUserList];
        return;
      }
      this.userList = this.originalUserList.filter(user =>
        user.mobile.includes(this.searchPhone)
      )},
    batchDelete() {
      console.log('执行批量删除操作');
    },
    batchDisable() {
      console.log('执行批量禁用操作');
    },
    resetPassword(row) {
      console.log('重置用户密码，用户：', row);
    },
    disableUser(row) {
      row.status = '禁用';
      console.log('禁用用户：', row);
    },
    restoreUser(row) {
      row.status = '正常';
      console.log('恢复用户：', row);
    },
    deleteUser(row) {
      console.log('删除用户：', row);
    },
    handleSizeChange(val) {
      this.pageSize = val;
      console.log('每页条数：', val);
    },
    headerCellClassName({column, columnIndex}) {
      if (columnIndex === 0) {
        return 'custom-selection-header'
      }
      return ''
    },
    goFirst() {
      this.currentPage = 1;
      this.handleCurrentChange(1);
    },
    goPrev() {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.handleCurrentChange(this.currentPage);
      }
    },
    goNext() {
      if (this.currentPage < this.pageCount) {
        this.currentPage++;
        this.handleCurrentChange(this.currentPage);
      }
    },
    goToPage(page) {
      this.currentPage = page;
      this.handleCurrentChange(page);
    },
  }
};
</script>

<style lang="scss" scoped>

$table-bg-color: #ecf1fd;

.main {
  padding: 20px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd);
}

.top-area {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;

  .page-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin-left: 20px;
  }

  .page-search {
    display: flex;
    align-items: center;

    .btn-search {
      margin-left: 10px;
      background: linear-gradient(to right, #5778ff, #c793f3);
      width: 100px;
      color: #fff;
    }
  }
}

.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-image: url("@/assets/home/background.png");
  background-size: cover;
  background-position: center;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.user-search-operate {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.user-search-operate > * {
  margin-right: 10px;
}

.el-table__header th {
  background-color: #f5f7fa;
  color: #606266;
}

.user-card {
  background: $table-bg-color;
  border-radius: 12px;
  padding: 20px;
  margin: 15px;
}

.table_bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;

  .ctrl_btn {
    display: flex;
    align-items: center;
    margin-left: 25px;
  }
}

.rotated-icon {
  display: inline-block;
  transform: rotate(45deg);
  margin-right: 4px;
  color: black;
}

:deep(.el-table) {
  background: $table-bg-color;

  &.transparent-table {
    .el-table__header th {
      background: $table-bg-color !important;
      color: black;
    }

    &::before {
      display: none;
    }

    &:last-child td {
        border-bottom: none !important;
    }

    .el-table__body tr {
      background-color: $table-bg-color;
      td {
        border: {
          top: 1px solid rgba(0, 0, 0, 0.04);
          bottom: 1px solid rgba(0, 0, 0, 0.04);
        }
      }
    }
  }
}

.search-input {
  width: 300px;
  margin-right: 10px;

  :deep(.el-input__inner) {
    background-color: transparent;
    border-color: #d3d6dc;

    &:focus {
      border-color: #409eff;
    }

    &::placeholder {
      color: #606266;
      opacity: 0.7;
    }
  }
}

:deep(.custom-selection-header) {
  .el-checkbox {
    display: none !important;
  }

  &::after {
    content: '选择';
    display: inline-block;
    color: black;
    font-weight: bold;
    padding-bottom: 18px;
  }
}

.custom-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 15px;

  /* 导航按钮样式 (首页、上一页、下一页) */
  .pagination-btn:first-child,
  .pagination-btn:nth-child(2),
  .pagination-btn:nth-last-child(2) {
    min-width: 60px;
    height: 32px;
    padding: 0 12px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    background: #DEE7FF;
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

    /* 数字按钮样式 */
  .pagination-btn:not(:first-child):not(:nth-child(2)):not(:nth-last-child(2)) {
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

  .total-text {
    color: #909399;
    font-size: 14px;
    margin-left: 10px;
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


</style>
