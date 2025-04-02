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
        <el-table ref="userTable" :data="userList" class="transparent-table" :header-cell-class-name="headerCellClassName">
          <el-table-column label="选择" type="selection" align="center" width="120"></el-table-column>
          <el-table-column label="用户Id" prop="userid" align="center"></el-table-column>
          <el-table-column label="手机号码" prop="mobile" align="center"></el-table-column>
          <el-table-column label="设备数量" prop="deviceCount" align="center"></el-table-column>
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
            <el-button size="mini" type="primary" class="select-all-btn" @click="handleSelectAll">全选</el-button>
            <el-button size="mini" type="success" icon="el-icon-circle-check" @click="batchEnable">启用</el-button>
            <el-button size="mini" type="warning" @click="batchDisable"><i class="el-icon-remove-outline rotated-icon"></i>禁用</el-button>
            <el-button size="mini" type="danger" icon="el-icon-delete" @click="batchDelete">删除</el-button>
          </div>
          <div class="custom-pagination">
            <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">首页</button>
            <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">上一页</button>

            <button v-for="page in visiblePages" :key="page" class="pagination-btn" :class="{ active: page === currentPage }" @click="goToPage(page)">
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
        <view-password-dialog :visible.sync="showViewPassword" :password="currentPassword"/>
    </el-main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import adminApi from '@/apis/module/admin';
import ViewPasswordDialog from '@/components/ViewPasswordDialog.vue'

export default {
  components: { HeaderBar, ViewPasswordDialog },
  data() {
    return {
      showViewPassword: false,
      currentPassword: '', // 存储获取到的密码
      searchPhone: '',
      userList: [],
      currentPage: 1,
      pageSize: 5,
      total: 0
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
        adminApi.getUserList({
            page: this.currentPage,
            limit: this.pageSize,
            mobile: this.searchPhone
        }, ({ data }) => {
            if (data.code === 0) {
                this.userList = data.data.list.map(user => ({
                    ...user,
                    status: user.status === '1' ? '正常' : '禁用'
                }));
                this.total = data.data.total;
            }
        });
    },

    // 搜索
    handleSearch() {
        this.currentPage = 1;
        this.fetchUsers();
    },

    // 全选
    handleSelectAll() {
      this.$refs.userTable.toggleAllSelection();
    },

    // 批量删除用户
    batchDelete() {
      const selectedUsers = this.$refs.userTable.selection;
      if (selectedUsers.length === 0) {
        this.$message.warning('请先选择需要删除的用户');
        return;
      }

      this.$confirm(`确定要删除选中的${selectedUsers.length}个用户吗？`, '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        const loading = this.$loading({
          lock: true,
          text: '正在删除中...',
          spinner: 'el-icon-loading',
          background: 'rgba(0, 0, 0, 0.7)'
        });

        try {
          const results = await Promise.all(
            selectedUsers.map(user => {
              return new Promise((resolve) => {
                adminApi.deleteUser(user.userid, ({data}) => {
                  if (data.code === 0) {
                    resolve({success: true, userid: user.userid});
                  } else {
                    resolve({success: false, userid: user.userid, msg: data.msg});
                  }
                });
              });
            })
          );

          const successCount = results.filter(r => r.success).length;
          const failCount = results.length - successCount;

          if (failCount === 0) {
            this.$message.success(`成功删除${successCount}个用户`);
          } else if (successCount === 0) {
            this.$message.error(`删除失败，请重试`);
          } else {
            this.$message.warning(`成功删除${successCount}个用户，${failCount}个删除失败`);
          }

          this.fetchUsers();
        } catch (error) {
          this.$message.error('删除过程中发生错误');
        } finally {
          loading.close();
        }
      }).catch(() => {
        this.$message.info('已取消删除');
      });
    },

    // 批量启用用户
    batchEnable() {
      const selectedUsers = this.$refs.userTable.selection;
      if (selectedUsers.length === 0) {
        this.$message.warning('请先选择需要启用的用户');
        return;
      }
      selectedUsers.forEach(user => {
        user.status = '正常';
      });
      this.$message.success('启用操作成功');
    },

    // 批量禁用用户
    batchDisable() {
      this.userList.forEach(user => {
      user.status = '禁用';
      });
      this.$message.success('状态已更新为禁用');
    },

    // 重置密码
    resetPassword(row) {
      this.$confirm('重置后将会生成新密码，是否继续？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }).then(() => {
        adminApi.resetUserPassword(row.userid, ({ data }) => {
          if (data.code === 0) {
            this.currentPassword = data.data
            this.showViewPassword = true
            this.$message.success('密码已重置，请通知用户使用新密码登录')
          }
        })
      })
    },
    disableUser(row) {
      row.status = '禁用';
      console.log('禁用用户：', row);
    },
    restoreUser(row) {
      row.status = '正常';
      console.log('恢复用户：', row);
    },

    // 用户删除
    deleteUser(row) {
        this.$confirm('确定要删除该用户吗？', '警告', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
        }).then(() => {
            adminApi.deleteUser(row.userid, ({data}) => {
                if (data.code === 0) {
                    this.$message.success('删除成功')
                    this.fetchUsers()
                } else {
                    this.$message.error(data.msg || '删除失败')
                }
            })
        }).catch(() => {})
    },
    headerCellClassName({columnIndex}) {
      if (columnIndex === 0) {
        return 'custom-selection-header'
      }
      return ''
    },
    goFirst() {
      this.currentPage = 1;
      this.fetchUsers();
    },
    goPrev() {
      if (this.currentPage > 1) {
        this.currentPage--;
         this.fetchUsers();
      }
    },
    goNext() {
      if (this.currentPage < this.pageCount) {
        this.currentPage++;
         this.fetchUsers();
      }
    },
    goToPage(page) {
      this.currentPage = page;
      this.fetchUsers();
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
  background: white;
  border-radius: 12px;
  padding: 15px;
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
    margin-left: 30px;
    .el-button {
      min-width: 72px;
      height: 32px;
      padding: 7px 12px;
      font-size: 12px;
      border-radius: 4px;
      line-height: 1;
      font-weight: 500;
      border: none;
      transition: all 0.3s ease;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
      position: relative;
      overflow: hidden;

      &:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
      }

      &:active {
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }

      &::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 5px;
        height: 5px;
        background: rgba(255, 255, 255, 0.5);
        opacity: 0;
        border-radius: 100%;
        transform: scale(1, 1) translate(-50%, -50%);
        transform-origin: 50% 50%;
      }

      &:focus:not(:active)::after {
        animation: ripple 0.6s ease-out;
      }
    }

    /* 全选按钮 */
    .el-button--primary {
      background: #5f70f3;
      box-shadow: 0 2px 6px rgba(95, 112, 243, 0.3);

      &:hover {
        background: #4d5fe1;
        box-shadow: 0 4px 8px rgba(95, 112, 243, 0.4);
      }

      &:active {
        background: #3a4bcf;
        box-shadow: 0 2px 4px rgba(95, 112, 243, 0.2);
      }
    }

    /* 启用按钮 */
    .el-button--success {
      background: #5bc98c;
      box-shadow: 0 2px 6px rgba(91, 201, 140, 0.3);

      &:hover {
        background: #4ab57d;
        box-shadow: 0 4px 8px rgba(91, 201, 140, 0.4);
      }

      &:active {
        background: #3aa16e;
        box-shadow: 0 2px 4px rgba(91, 201, 140, 0.2);
      }
    }

    /* 禁用按钮 */
    .el-button--warning {
      background: #f6d075;
      color: black;
      box-shadow: 0 2px 6px rgba(246, 208, 117, 0.3);

      &:hover {
        background: #e4c068;
        box-shadow: 0 4px 8px rgba(246, 208, 117, 0.4);
      }

      &:active {
        background: #d2b05b;
        box-shadow: 0 2px 4px rgba(246, 208, 117, 0.2);
      }

      .rotated-icon {
        display: inline-block;
        transform: rotate(45deg);
        margin-right: 4px;
        color: black;
      }
    }

    /* 删除按钮 */
    .el-button--danger {
      background: #fd5b63;
      box-shadow: 0 2px 6px rgba(253, 91, 99, 0.3);

      &:hover {
        background: #e44a52;
        box-shadow: 0 4px 8px rgba(253, 91, 99, 0.4);
      }

      &:active {
        background: #cb3941;
        box-shadow: 0 2px 4px rgba(253, 91, 99, 0.2);
      }
    }
  }

  @keyframes ripple {
    0% {
      transform: scale(0, 0);
      opacity: 0.5;
    }
    100% {
      transform: scale(20, 20);
      opacity: 0;
    }
  }
  }

  .rotated-icon {
    display: inline-block;
    transform: rotate(45deg);
    margin-right: 4px;
    color: black;
  }

  :deep(.el-table) {
    background: white;

    &.transparent-table {
      .el-table__header th {
        background: white !important;
        color: black;
      }

      &::before {
        display: none;
      }

      &:last-child td {
          border-bottom: none !important;
      }

      .el-table__body tr {
        background-color: white;
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
