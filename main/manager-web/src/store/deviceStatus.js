const state = {
  // 设备状态
  deviceStatus: {
    isOnline: false,
    error: '',
    lastCheck: null
  },
  deviceInfo: {
    chip: null,
    board: null,
    firmware: null,
    flash: null,
    assetsPartition: null,
    network: null,
    screen: null
  },
  token: '',
  isChecking: false,
  retryTimer: null
};

const mutations = {
  // 设置token
  SET_TOKEN(state, token) {
    state.token = token
  },
  
  // 设置设备在线状态
  SET_DEVICE_ONLINE(state, isOnline) {
    state.deviceStatus.isOnline = isOnline
  },
  
  // 更新设备状态
  UPDATE_DEVICE_STATUS(state, status) {
    state.deviceStatus = { ...state.deviceStatus, ...status }
  },
  
  // 更新设备信息
  UPDATE_DEVICE_INFO(state, info) {
    state.deviceInfo = { ...state.deviceInfo, ...info }
  },
  
  // 设置检查状态
  SET_IS_CHECKING(state, checking) {
    state.isChecking = checking
  },
  
  // 设置重试计时器
  SET_RETRY_TIMER(state, timer) {
    state.retryTimer = timer
  }
};

const actions = {
  // 获取URL参数
  getUrlParameter(state, name) {
    const urlParams = new URLSearchParams(window.location.search)
    return urlParams.get(name)
  },
  
  // 调用MCP工具
  async callMcpTool(state, toolName, params = {}) {
    if (!state.token) {
      throw new Error('Authentication token not found')
    }

    const response = await fetch('/api/messaging/device/tools/call', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.token}`
      },
      body: JSON.stringify({
        name: toolName,
        arguments: params
      })
    })

    if (response.ok) {
      const result = await response.json()
      return result
    } else {
      const errorText = await response.text()
      console.error(`MCP tool ${toolName} failed:`, response.status, errorText)
      
      // 解析错误信息
      let errorMessage = `Failed to call ${toolName}`
      try {
        const errorData = JSON.parse(errorText)
        if (errorData.message) {
          errorMessage = errorData.message
        }
      } catch (e) {
        // 如果解析失败，使用HTTP状态码
        errorMessage = `${errorMessage}: HTTP ${response.status}`
      }
      
      throw new Error(errorMessage)
    }
  },
  
  // 获取设备详细信息
  async fetchDeviceInfo(state) {
    try {
    // 并发获取所有设备信息
    const [systemInfoResponse, deviceStateResponse, screenInfoResponse] = await Promise.allSettled([
      callMcpTool('self.get_system_info'),
      callMcpTool('self.get_device_status'),
      callMcpTool('self.screen.get_info')
    ])

    // 处理系统信息
    if (systemInfoResponse.status === 'fulfilled' && systemInfoResponse.value) {
      const data = systemInfoResponse.value.data || systemInfoResponse.value

      state.commit("UPDATE_DEVICE_INFO", {
        chip: { model: data.chip_model_name || 'Unknown' },
        board: { model: data.board?.name || 'Unknown' },
        firmware: { version: data.application?.version || 'Unknown' }
      })

      // 获取Flash大小
      if (data.flash_size) {
        const sizeInMB = Math.round(data.flash_size / 1024 / 1024)
        state.commit("UPDATE_DEVICE_INFO", {
          flash: { size: `${sizeInMB}MB` },
        })
      } else {
        state.commit("UPDATE_DEVICE_INFO", {
          flash: { size: 'Unknown' }
        })
      }

      // 获取assets分区大小
      if (data.partition_table) {
        const assetsPartition = data.partition_table.find(p => p.label === 'assets')
        if (assetsPartition) {
          state.commit("UPDATE_DEVICE_INFO", {
            assetsPartition: {
              size: assetsPartition.size,
              sizeFormatted: `${Math.round(assetsPartition.size / 1024 / 1024)}MB`
            }
          })
        } else {
          state.commit("UPDATE_DEVICE_INFO", {
            assetsPartition: null
          })
        }
      } else {
        state.commit("UPDATE_DEVICE_INFO", {
          assetsPartition: null
        })
      }
    } else {
      console.warn('系统信息获取失败:', systemInfoResponse.reason || systemInfoResponse.value)
      state.commit("UPDATE_DEVICE_INFO", {
        chip: { model: 'Unknown' },
        board: { model: 'Unknown' },
        firmware: { version: 'Unknown' },
        flash: { size: 'Unknown' },
        assetsPartition: null
      })
    }

    // 处理设备状态信息
    if (deviceStateResponse.status === 'fulfilled' && deviceStateResponse.value) {
      const data = deviceStateResponse.value.data || deviceStateResponse.value

      state.commit("UPDATE_DEVICE_INFO", {
        network: {
          type: data.network?.type || 'unknown',
          signal: data.network?.signal || 'Unknown'
        }
      })
    } else {
      console.warn('设备状态获取失败:', deviceStateResponse.reason || deviceStateResponse.value)
      state.commit("UPDATE_DEVICE_INFO", {
        network: { type: 'unknown', signal: 'Unknown' }
      })
    }

    // 处理屏幕信息
    if (screenInfoResponse.status === 'fulfilled' && screenInfoResponse.value) {
      const data = screenInfoResponse.value.data || screenInfoResponse.value
      state.commit("UPDATE_DEVICE_INFO", {
        screen: { resolution: `${data.width || 0}x${data.height || 0}` }
      })
    } else {
      console.warn('屏幕信息获取失败:', screenInfoResponse.reason || screenInfoResponse.value)
      state.commit("UPDATE_DEVICE_INFO", {
        screen: { resolution: 'Unknown' }
      })
    }
  } catch (error) {
    console.error('获取设备信息时发生错误:', error)
  }
  },
  
  // 检查设备是否在线
  async checkDeviceStatus(state) {
    if (state.isChecking || !state.token) return

    state.commit("SET_IS_CHECKING", true);
    try {
      const response = await fetch('/api/messaging/device/tools/list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token.value}`
        }
      })

      if (response.ok) {
        state.commit("UPDATE_DEVICE_STATUS", {
          isOnline: true,
          error: '',
          lastCheck: new Date()
        })

        // 获取设备详细信息
        await fetchDeviceInfo()
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
    } catch (error) {
      state.commit("UPDATE_DEVICE_STATUS", {
        isOnline: false,
        error: '',
        lastCheck: new Date()
      })

      // 30秒后重试
      if (state.retryTimer) {
        clearTimeout(state.retryTimer)
      }
      state.commit("SET_RETRY_TIMER", setTimeout(checkDeviceStatus, 30000));
    } finally {
      state.commit("SET_IS_CHECKING", false);
    }
  },
  
  // 初始化设备状态监控
  initializeDeviceStatus(state) {
    state.commit("SET_TOKEN", state.dispatch("getUrlParameter", "token"))
    if (state.token) {
      state.dispatch("checkDeviceStatus");
    }
  },
  
  // 清理资源
  cleanupDeviceStatus(state) {
    if (state.retryTimer) {
      clearTimeout(state.retryTimer)
      state.commit('SET_RETRY_TIMER', null)
    }
  },
  
  // 手动刷新设备状态
  async refreshDeviceStatus(state) {
    await state.dispatch('checkDeviceStatus')
  }
};

const getters = {
  // 是否有token
  hasToken(state) {
    return !!state.token;
  },
  
  // 设备是否在线
  isDeviceOnline(state) {
    return state.isOnline;
  }
}

export default {
  // 开启命名空间（关键！避免模块间命名冲突）
  namespaced: true,
  state,
  mutations,
  actions,
  getters
}