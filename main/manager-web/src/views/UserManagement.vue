<template>
  <div class="welcome">
    <HeaderBar />
    <el-main style="padding: 20px; display: flex; flex-direction: column;">
      <el-card class="user-card" shadow="always" >
      <div class="user-search-operate" style="display: flex; align-items: center; margin-bottom: 20px;">
        <el-input placeholder="请输入手机号码查询" v-model="searchPhone" style="width: 300px; margin-right: 10px" />
        <el-button @click="handleSearch">查询</el-button>
        <el-button type="danger" @click="batchDelete">批量删除</el-button>
        <el-button type="danger" @click="batchDisable">批量禁用</el-button>
      </div>
      
      <el-table :data="userList" style="width: 100%;" border stripe>
        <el-table-column label="用户Id" prop="userId"></el-table-column>
        <el-table-column label="手机号码" prop="phone"></el-table-column>
        <el-table-column label="Status" prop="status"></el-table-column>
        <el-table-column label="设备数量" prop="deviceCount"></el-table-column>
        <el-table-column label="操作">
          <template slot-scope="scope">
            <el-button size="mini" @click="resetPassword(scope.row)">重置密码</el-button>
            <el-button size="mini"
              v-if="scope.row.status === '正常'"
              @click="disableUser(scope.row)">禁用</el-button>
            <el-button size="mini"
              v-if="scope.row.status === '禁用'"
              @click="restoreUser(scope.row)">恢复</el-button>
            <el-button size="mini" @click="deleteUser(scope.row)" style="color: #ff4949">删除用户</el-button>
          </template>
        </el-table-column>
      </el-table>
      </el-card>

      <div class="pagination-container">
        <el-pagination
          @current-change="handleCurrentChange"
          :current-page="currentPage"
          :page-sizes="[5, 10, 15]"
          :page-size="pageSize"
          layout="prev, pager, next"
          :total="total"
        />
      </div>

      <div style="font-size: 12px; font-weight: 400; margin-top: auto; padding-top: 30px; color: #979db1;">
        ©2025 xiaozhi-esp32-server
      </div>
    </el-main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";

export default {
  components: { HeaderBar },
  data() {
    return {
      searchPhone: '',
      userList: [
        { userId: '123456', phone: '13800138000', status: '正常', deviceCount: 10 },
        { userId: '123456', phone: '13800138000', status: '正常', deviceCount: 9 },
        { userId: '123456', phone: '13800138000', status: '正常', deviceCount: 7 },
        { userId: '123456', phone: '13800138000', status: '禁用', deviceCount: 7 }
      ],
      currentPage: 1,
      pageSize: 4,
      total: 20
    };
  },
  methods: {
    handleSearch() {
      // 模拟搜索逻辑
      console.log('执行查询，搜索号码：', this.searchPhone);
    },
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
    handleCurrentChange(page) {
      this.currentPage = page;
      console.log('当前页码：', page);
    },
  }
};
</script>

<style scoped>
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
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

</style>