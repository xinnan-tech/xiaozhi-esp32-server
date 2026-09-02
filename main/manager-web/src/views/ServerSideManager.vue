<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="params-card" shadow="never">
            <div class="operation-header">
              <h2 class="page-title">{{ $t('serverSideManager.pageTitle') }}</h2>
            </div>
            <el-card class="server-list-card">
              <div v-for="(item, index) in paramsList" :key="index" class="server-list" v-loading="loading">
                <div class="server-card">
                  <div class="server-info">
                    <span class="server-label">{{ $t('serverSideManager.wsAddress') }}</span>
                    <span class="server-value">{{ item.address }}</span>
                  </div>
                  <el-button class="copy-button" type="text" size="small" @click="copyAddress(item.address)">{{ $t('common.copyAddress') }}</el-button>
                </div>
                <el-divider />
                <div class="header-actions">
                  <CustomButton icon="el-icon-refresh-right" size="small" @click="emitAction(item, actionMap.restart)">{{
                    $t('serverSideManager.restart') }}</CustomButton>
                  <CustomButton icon="el-icon-setting" size="small" type="confirm" @click="emitAction(item, actionMap.update_config)">
                    {{ $t('serverSideManager.updateConfig') }}
                  </CustomButton>
                </div>
                <el-empty v-if="paramsList.length === 0 && !loading" :description="$t('common.noData')"></el-empty>
              </div>
            </el-card>
          </el-card>
        </div>
      </div>
    </div>
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import CustomButton from "@/components/CustomButton.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";

export default {
  components: { HeaderBar, VersionFooter, CustomButton },
  data() {
    return {
      paramsList: [],
      loading: false,
    };
  },
  created() {
    this.fetchParams();
  },
  computed: {
    actionMap() {
      return {
        restart: {
          value: 'restart',
          title: this.$t('serverSideManager.restartServer'),
          message: this.$t('serverSideManager.confirmRestart'),
          confirmText: this.$t('serverSideManager.restart'),
        },
        update_config: {
          value: 'update_config',
          title: this.$t('serverSideManager.updateConfigTitle'),
          message: this.$t('serverSideManager.confirmUpdateConfig'),
          confirmText: this.$t('serverSideManager.updateConfig'),
        }
      };
    }
  },
  methods: {
    fetchParams() {
      this.loading = true;
      Api.admin.getWsServerList(
        {},
        ({ data }) => {
          this.loading = false;
          if (data.code === 0) {
            this.paramsList = data.data.map(item => ({ address: item }));
          } else {
            this.$message.error({
              message: data.msg || this.$t('serverSideManager.getServerListFailed'),
              showClose: true
            });
          }
        }
      );
    },
    emitAction(rowItem, actionItem) {
      if (actionItem === undefined || rowItem.address === undefined) {
        return;
      }
      this.$confirm(actionItem.message, actionItem.title, {
        confirmButtonText: actionItem.confirmText,
        cancelButtonText: this.$t('common.cancel')
      }).then(() => {
        Api.admin.sendWsServerAction({
          targetWs: rowItem.address,
          action: actionItem.value
        }, ({ data }) => {
          if (data.code !== 0) {
            this.$message.error({
              message: data.msg || this.$t('serverSideManager.operationFailed'),
              showClose: true
            });
            return;
          }
          this.$message.success({
            message: actionItem.value === 'restart' ? this.$t('serverSideManager.restartSuccess') : this.$t('serverSideManager.updateConfigSuccess'),
            showClose: true
          })
        })
      })
    },
    copyAddress(address) {
      navigator.clipboard.writeText(address).then(() => {
        this.$message.success(this.$t('common.copySuccess'));
      }).catch(() => {
        this.$message.error(this.$t('common.copyFailed'));
      });
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
  background-size: cover;
  background: #eff4ff;
  -webkit-background-size: cover;
  -o-background-size: cover;
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

.page-title {
  font-weight: 500;
  font-size: 24px;
  margin: 0;
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
  }
}

.server-list {
  padding: 16px 20px;
  border-radius: 10px;
  box-shadow: 0 0 8px #ececec;
}

.server-list-card {
  flex: 1;
  border: none;
  border-radius: 8px;
  box-shadow: none;

  ::v-deep .el-card__body {
    gap: 20px;
    overflow: auto;
    padding: 16px;
    height: 100%;
    box-sizing: border-box;
  }

  ::v-deep .el-divider {
    margin: 16px 0 !important;
    background: #ecf2fb !important;
  }
}

.header-actions {
  display: flex;
  justify-content: flex-end;
}

.operation-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 16px 0;
  box-sizing: border-box;
}

.server-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-radius: 10px;
  background: rgba(239, 243, 252, 0.4);
  border: 1px solid #ecf2fb;
}

.server-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.server-label {
  font-size: 16px;
  font-weight: 500;
}

.server-value {
  margin-top: 10px;
  font-size: 14px;
}

.server-actions {
  display: flex;
  gap: 8px;
}
.copy-button {
  font-size: 14px;
  color: #5778ff;
}
</style>
