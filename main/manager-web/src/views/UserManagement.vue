<template>
  <div class="welcome">
    <HeaderBar />
    <el-main class="main" style="padding: 20px; display: flex; flex-direction: column;">
      <div class="top-area">
        <div class="page-title">用户管理</div>
        <div class="page-search">
          <el-input placeholder="请输入手机号码查询" v-model="searchPhone" class="search-input" />
          <el-button class="btn-search" @click="handleSearch">搜索</el-button>
          <!-- <el-button type="danger" @click="batchDelete">批量删除</el-button>
          <el-button type="danger" @click="batchDisable">批量禁用</el-button> -->
        </div>
      </div>

      <el-card class="user-card" shadow="never">
        <!-- <div class="user-search-operate" style="display: flex; align-items: center; margin-bottom: 20px;">
          <el-input placeholder="请输入手机号码查询" v-model="searchPhone" style="width: 300px; margin-right: 10px" />
          <el-button @click="handleSearch">查询</el-button>
          <el-button type="danger" @click="batchDelete">批量删除</el-button>
          <el-button type="danger" @click="batchDisable">批量禁用</el-button>
        </div> -->
        <el-table :data="userList" class="transparent-table" :header-cell-class-name="headerCellClassName">
          <el-table-column label="选择" type="selection" width="55"></el-table-column>
          <el-table-column label="用户Id" prop="user_id"></el-table-column>
          <el-table-column label="手机号码" prop="mobile"></el-table-column>
          <el-table-column label="设备数量" prop="device_count"></el-table-column>
          <el-table-column label="状态" prop="status"></el-table-column>
          <el-table-column label="操作">
            <template slot-scope="scope">
            <el-button size="mini" type="text" @click="resetPassword(scope.row)" style="color: #989fdd">重置密码</el-button>
            <el-button size="mini" type="text"
              v-if="scope.row.status === '正常'"
              @click="disableUser(scope.row)">禁用</el-button>
            <el-button size="mini" type="text"
              v-if="scope.row.status === '禁用'"
              @click="restoreUser(scope.row)">恢复</el-button>
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
          <div class="pagination-container">
            <el-pagination
              background
              @current-change="handleCurrentChange"
              :current-page="currentPage"
              :page-sizes="[5, 10, 15]"
              :page-size="pageSize"
              layout="prev, pager, next"
              :total="total"
            />
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
import Api from '@/apis/api';
import adminApi from '@/apis/module/admin';


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
  created() {
    adminApi.getUserList(({data}) => {
      //mock偶尔会返回-1导致出错，又会返回两个list，所以这里只取第一个
      this.userList = data.data[0].list;
      console.log('用户列表：', this.userList);
    })
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
    headerCellClassName({ column, columnIndex }) {
    if (columnIndex === 0) {
      return 'custom-selection-header'
    }
    return ''
    },
  }
};
</script>

<style lang="scss" scoped>

$table-bg-color: #ecf1fd;

.main {
  padding: 20px; display: flex; flex-direction: column;
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
  //box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.table_bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  .ctrl_btn {
    display: flex;
    align-items: center;
  }
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
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

    .el-table__body tr {
      background-color: $table-bg-color;
    }
  }
}

.search-input {
  width: 300px;
  margin-right: 10px;
  :deep(.el-input__inner) {
    background-color: transparent;
    &:focus {
      border-color: #409eff; // 保持聚焦状态下的边框颜色
    }
    //文字颜色
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

</style>