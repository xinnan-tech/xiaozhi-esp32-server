<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="user-card" shadow="never">
            <div class="operation-header">
              <h2 class="page-title">{{ $t('header.userManagement') }}</h2>
              <div class="right-operations">
                <el-input :placeholder="$t('user.searchPhone')" v-model="searchPhone" class="search-input" clearable
                  @keyup.enter.native="handleSearch" />
                <CustomButton icon="el-icon-search" type="confirm" @click="handleSearch">{{ $t('user.search') }}</CustomButton>
              </div>
            </div>
            <CustomTable
              ref="userTable"
              :data="userList"
              :columns="tableColumns"
              :loading="loading"
              :loading-text="$t('modelConfig.loading')"
              :show-selection="true"
              :show-operations="true"
              :operations-label="$t('modelConfig.action')"
              :operations-width="300"
              :total="total"
              :current-page="currentPage"
              :page-size="pageSize"
              :page-size-options="pageSizeOptions"
              @size-change="handlePageSizeChange"
              @page-change="goToPage"
            >
              <template slot="selection" slot-scope="scope">
                <el-checkbox v-model="scope.row.selected"></el-checkbox>
              </template>
              <template slot="status" slot-scope="scope">
                <el-tag v-if="scope.row.status === 1" type="success">{{ $t('user.normal') }}</el-tag>
                <el-tag v-else type="danger">{{ $t('user.disabled') }}</el-tag>
              </template>
              <template slot="operations" slot-scope="scope">
                <el-button size="mini" type="text" @click="resetPassword(scope.row)">{{ $t('user.resetPassword')
                  }}</el-button>
                <el-button size="mini" type="text" v-if="scope.row.status === 1"
                  @click="handleChangeStatus(scope.row, 0)">{{ $t('user.disableAccount') }}</el-button>
                <el-button size="mini" type="text" v-if="scope.row.status === 0"
                  @click="handleChangeStatus(scope.row, 1)">{{ $t('user.enableAccount') }}</el-button>
                <el-button size="mini" type="text" @click="deleteUser(scope.row)">{{ $t('user.deleteUser')
                  }}</el-button>
              </template>
              <template slot="footer-btns">
                <div class="ctrl_btn">
                  <CustomButton :icon="isAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'" size="small" @click="handleSelectAll">
                    {{ isAllSelected ? $t('user.deselectAll') : $t('user.selectAll') }}
                  </CustomButton>
                  <CustomButton size="small" icon="el-icon-remove-outline" @click="batchDisable">
                    {{$t('user.disable') }}
                  </CustomButton>
                  <CustomButton size="small" type="add" icon="el-icon-circle-check" @click="batchEnable">{{
                    $t('user.enable')
                    }}</CustomButton>
                  <CustomButton size="small" type="delete" icon="el-icon-delete" @click="batchDelete">{{ $t('user.delete')
                    }}</CustomButton>
                </div>
              </template>
            </CustomTable>
          </el-card>
        </div>
      </div>
    </div>

    <view-password-dialog :visible.sync="showViewPassword" :password="currentPassword" />
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import ViewPasswordDialog from "@/components/ViewPasswordDialog.vue";
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";
export default {
  components: { HeaderBar, ViewPasswordDialog, VersionFooter, CustomButton, CustomTable },
  data() {
    return {
      showViewPassword: false,
      currentPassword: "",
      searchPhone: "",
      userList: [],
      pageSizeOptions: [10, 20, 50, 100],
      currentPage: 1,
      pageSize: 10,
      total: 0,
      isAllSelected: false,
      loading: false,
      tableColumns: []
    };
  },
  created() {
    this.initTableColumns();
    this.fetchUsers();
  },
  methods: {
    initTableColumns() {
      this.tableColumns = [
        {
          prop: 'userid',
          label: this.$t('user.userid'),
          align: 'center'
        },
        {
          prop: 'mobile',
          label: this.$t('user.mobile'),
          align: 'center'
        },
        {
          prop: 'deviceCount',
          label: this.$t('user.deviceCount'),
          align: 'center'
        },
        {
          prop: 'createDate',
          label: this.$t('user.createDate'),
          align: 'center'
        },
        {
          prop: 'status',
          label: this.$t('user.status'),
          align: 'center'
        }
      ];
    },
    handlePageSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
      this.fetchUsers();
    },

    fetchUsers() {
      this.loading = true;
      Api.admin.getUserList(
        {
          page: this.currentPage,
          limit: this.pageSize,
          mobile: this.searchPhone,
        },
        ({ data }) => {
          this.loading = false; // 结束加载
          if (data.code === 0) {
            this.userList = data.data.list.map(item => ({
              ...item,
              selected: false
            }));
            this.total = data.data.total;
          }
        }
      );
    },
    handleSearch() {
      this.currentPage = 1;
      this.fetchUsers();
    },
    handleSelectAll() {
      this.isAllSelected = !this.isAllSelected;
      this.userList.forEach(row => {
        row.selected = this.isAllSelected;
      });
    },
    batchDelete() {
      const selectedUsers = this.userList.filter(user => user.selected);
      if (selectedUsers.length === 0) {
        this.$message.warning(this.$t('user.selectUsersFirst'));
        return;
      }

      this.$confirm(this.$t('user.confirmDeleteSelected', { count: selectedUsers.length }), this.$t('common.warning'), {
        confirmButtonText: this.$t('common.confirm'),
        cancelButtonText: this.$t('common.cancel'),
        type: "warning",
      })
        .then(async () => {
          const loading = this.$loading({
            lock: true,
            text: this.$t('user.deleting'),
            spinner: "el-icon-loading",
            background: "rgba(0, 0, 0, 0.7)",
          });

          try {
            const results = await Promise.all(
              selectedUsers.map((user) => {
                return new Promise((resolve) => {
                  Api.admin.deleteUser(user.userid, ({ data }) => {
                    if (data.code === 0) {
                      resolve({ success: true, userid: user.userid });
                    } else {
                      resolve({ success: false, userid: user.userid, msg: data.msg });
                    }
                  });
                });
              })
            );

            const successCount = results.filter((r) => r.success).length;
            const failCount = results.length - successCount;

            if (failCount === 0) {
              this.$message.success({
                message: this.$t('user.deleteSuccess', { count: successCount }),
                showClose: true
              });
            } else if (successCount === 0) {
              this.$message.error({
                message: this.$t('user.deleteFailed'),
                showClose: true
              });
            } else {
              this.$message.warning(
                this.$t('user.partialDelete', { successCount: successCount, failCount: failCount })
              );
            }

            this.fetchUsers();
          } catch (error) {
            this.$message.error(this.$t('user.deleteError'));
          } finally {
            loading.close();
          }
        })
        .catch(() => {
          this.$message.info(this.$t('user.deleteCancelled'));
        });
    },
    batchEnable() {
      const selectedUsers = this.userList.filter(user => user.selected);
      if (selectedUsers.length === 0) {
        this.$message.warning(this.$t('user.selectUsersToEnable'));
        return;
      }
      this.handleChangeStatus(selectedUsers, 1);
    },
    batchDisable() {
      const selectedUsers = this.userList.filter(user => user.selected);
      if (selectedUsers.length === 0) {
        this.$message.warning(this.$t('user.selectUsersToDisable'));
        return;
      }
      this.handleChangeStatus(selectedUsers, 0);
    },
    resetPassword(row) {
      this.$confirm(this.$t('user.confirmResetPassword'), this.$t('common.warning'), {
        confirmButtonText: this.$t('common.confirm'),
        cancelButtonText: this.$t('common.cancel'),
        type: 'warning'
      }).then(() => {
        Api.admin.resetUserPassword(row.userid, ({ data }) => {
          if (data.code === 0) {
            // 显示生成的默认密码
            this.$alert(this.$t('user.resetPasswordSuccess') + '\n\n' + this.$t('user.generatedPassword') + ': ' + data.data, this.$t('common.success'), {
              confirmButtonText: this.$t('common.confirm'),
              dangerouslyUseHTMLString: true
            });
            this.fetchUsers();
          } else {
            this.$message.error(data.msg || this.$t('user.operationFailed'));
          }
        });
      }).catch(() => {
        this.$message.info(this.$t('common.deleteCancelled'));
      });
    },
    deleteUser(row) {
      this.$confirm(this.$t('user.confirmDeleteUser'), this.$t('common.warning'), {
        confirmButtonText: this.$t('common.confirm'),
        cancelButtonText: this.$t('common.cancel'),
        type: 'warning'
      }).then(() => {
        Api.admin.deleteUser(row.userid, ({ data }) => {
          if (data.code === 0) {
            // 删除后检查是否需要调整页码
            const newTotal = this.total - 1;
            const maxPage = Math.max(1, Math.ceil(newTotal / this.pageSize));
            if (this.currentPage > maxPage) {
              this.currentPage = maxPage;
            }
            this.$message.success(this.$t('user.deleteUserSuccess'));
            this.fetchUsers();
          } else {
            this.$message.error(data.msg || this.$t('user.operationFailed'));
          }
        });
      }).catch(() => {
        this.$message.info(this.$t('common.deleteCancelled'));
      });
    },
    goToPage(page) {
      if (page !== this.currentPage) {
        this.currentPage = page;
        this.fetchUsers();
      }
    },
    handleChangeStatus(row, status) {
      // 处理单个用户或用户数组
      const users = Array.isArray(row) ? row : [row];
      const actionText = status === 0 ? this.$t('user.disable') : this.$t('user.enable');
      const userCount = users.length;

      this.$confirm(this.$t('user.confirmStatusChange', { action: actionText, count: userCount }), this.$t('common.warning'), {
        confirmButtonText: this.$t('common.confirm'),
        cancelButtonText: this.$t('common.cancel'),
        type: 'warning'
      }).then(() => {
        const userIds = users.map(user => user.userid);
        if (userIds.some(id => isNaN(id))) {
          this.$message.error(this.$t('user.invalidUserId'));
          return;
        }

        Api.user.changeUserStatus(status, userIds, ({ data }) => {
          if (data.code === 0) {
            this.$message.success({
              message: this.$t('user.statusChangeSuccess', { action: actionText, count: userCount }),
              showClose: true
            });
            this.fetchUsers(); // 刷新用户列表
          } else {
            this.$message.error({
              message: this.$t('user.operationFailed'),
              showClose: true
            });
          }
        });
      }).catch(() => {
        // 用户取消操作
      });
    },
    // 这个方法已被batchDelete替代，保留用于向后兼容
    handleBatchDelete() {
      this.batchDelete();
    },
    // This method has been fixed to use existing functionality
    handleBatchStatusChange(status) {
      const selectedUsers = this.userList.filter(user => user.selected);
      if (selectedUsers.length === 0) {
        this.$message.warning(this.$t('user.selectUsersFirst'));
        return;
      }

      // Call the existing handleChangeStatus method which already handles both single and multiple users
      this.handleChangeStatus(selectedUsers, status);
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
  // 顶部 63px 底部 35px
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

.btn-search {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
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

.user-card {
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

.ctrl_btn {
  display: flex;
}

:deep(.el-table .el-button--text) {
  color: #7079aa !important;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5 !important;
}
</style>
