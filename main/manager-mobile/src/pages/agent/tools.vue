<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationBarTitleText": "编辑功能",
    "navigationStyle": "custom",
  },
}
</route>

<script lang="ts" setup>
import { useMessage } from 'wot-design-uni'
import { getMcpAddress, getMcpTools } from '@/api/agent/agent'
import { usePluginStore } from '@/store'

const message = useMessage()
const pluginStore = usePluginStore()

const segmentedList = ref<string[]>(['未选', '已选'])
const currentSegmented = ref('未选')
const notSelectedList = ref<any[]>([])
const selectedList = ref<any[]>([])

// 使用计算属性从store获取数据
const allFunctions = computed(() => pluginStore.allFunctions)
const functions = computed(() => pluginStore.currentFunctions)
const agentId = computed(() => pluginStore.currentAgentId)
const mcpAddress = ref('')
const mcpTools = ref<string[]>([])

// 初始化时从本地存储加载MCP地址
if (uni.getStorageSync('cachedMcpAddress_' + agentId.value)) {
  mcpAddress.value = uni.getStorageSync('cachedMcpAddress_' + agentId.value)
}

// 参数编辑相关
const showParamDialog = ref(false)
const currentFunction = ref<any>(null)
const tempParams = ref<Record<string, any>>({})
const arrayTextCache = ref<Record<string, string>>({})
const jsonTextCache = ref<Record<string, string>>({})

async function mergeFunctions() {
  selectedList.value = functions.value.map((mapping) => {
    const meta = allFunctions.value.find(f => f.id === mapping.pluginId)
    if (!meta) {
      return { id: mapping.pluginId, name: mapping.pluginId, params: {} }
    }

    return {
      id: mapping.pluginId,
      name: meta.name,
      params: mapping.paramInfo || { ...meta.params },
      fieldsMeta: meta.fieldsMeta,
    }
  })

  // 未选的插件
  notSelectedList.value = allFunctions.value.filter(
    item => !selectedList.value.some(f => f.id === item.id),
  )

  if (agentId.value) {
    // 优先获取并显示MCP地址
    try {
      const address = await getMcpAddress(agentId.value)
      mcpAddress.value = address
      // 缓存到本地存储，下次打开页面可以立即显示
      uni.setStorageSync('cachedMcpAddress_' + agentId.value, address)
    } catch (error) {
      console.error('获取MCP地址失败:', error)
    }
    
    // 异步获取MCP工具列表，不阻塞UI显示
    try {
      const tools = await getMcpTools(agentId.value)
      mcpTools.value = tools || []
    } catch (error) {
      console.error('获取MCP工具列表失败:', error)
    }
  }
}

// 添加插件到已选
function selectFunction(func: any) {
  // 添加到已选列表
  selectedList.value.push({
    id: func.id,
    name: func.name,
    params: { ...func.params },
    fieldsMeta: func.fieldsMeta,
  })

  // 从未选列表中移除
  notSelectedList.value = notSelectedList.value.filter(
    item => item.id !== func.id,
  )
}

// 从已选中移除插件
function removeFunction(func: any) {
  // 从已选列表中移除
  selectedList.value = selectedList.value.filter(item => item.id !== func.id)

  // 添加回未选列表
  const originalFunc = allFunctions.value.find(f => f.id === func.id)
  if (originalFunc) {
    notSelectedList.value.push(originalFunc)
  }
}

// 编辑插件参数
function editFunction(func: any) {
  currentFunction.value = func

  // 直接使用当前函数的参数
  tempParams.value = { ...func.params }

  // 初始化文本缓存
  if (func.fieldsMeta) {
    func.fieldsMeta.forEach((field: any) => {
      if (field.type === 'array') {
        const value = tempParams.value[field.key]
        arrayTextCache.value[field.key] = Array.isArray(value)
          ? value.join('\n')
          : value || ''
      }
      else if (field.type === 'json') {
        const value = tempParams.value[field.key]
        try {
          jsonTextCache.value[field.key] = JSON.stringify(value || {}, null, 2)
        }
        catch {
          jsonTextCache.value[field.key] = '{}'
        }
      }
    })
  }

  showParamDialog.value = true
}

// 处理参数变化 - 实时保存
function handleParamChange(key: string, value: any, field: any) {
  tempParams.value[key] = value

  // 实时更新到 selectedList
  if (currentFunction.value) {
    const index = selectedList.value.findIndex(
      f => f.id === currentFunction.value.id,
    )
    if (index >= 0) {
      selectedList.value[index].params = { ...tempParams.value }
    }
  }
}

// 处理数组类型参数变化 - 实时保存
function handleArrayChange(key: string, value: string, field: any) {
  arrayTextCache.value[key] = value
  // 转换为数组存储
  const arrayValue = value.split('\n').filter(Boolean)
  tempParams.value[key] = arrayValue

  // 实时更新到 selectedList
  if (currentFunction.value) {
    const index = selectedList.value.findIndex(
      f => f.id === currentFunction.value.id,
    )
    if (index >= 0) {
      selectedList.value[index].params = { ...tempParams.value }
    }
  }
}

// 处理JSON类型参数变化 - 实时保存
function handleJsonChange(key: string, value: string, field: any) {
  jsonTextCache.value[key] = value
  try {
    const jsonValue = JSON.parse(value)
    tempParams.value[key] = jsonValue

    // 实时更新到 selectedList
    if (currentFunction.value) {
      const index = selectedList.value.findIndex(
        f => f.id === currentFunction.value.id,
      )
      if (index >= 0) {
        selectedList.value[index].params = { ...tempParams.value }
      }
    }
  }
  catch {
    message.alert('JSON格式错误')
  }
}

// 关闭参数编辑弹窗
function closeParamEdit() {
  showParamDialog.value = false
  tempParams.value = {}
  arrayTextCache.value = {}
  jsonTextCache.value = {}
}

// 返回上一页并更新配置
function goBack() {
  const finalFunctions = selectedList.value.map(f => ({
    pluginId: f.id,
    paramInfo: f.params,
  }))

  // 更新到store中
  pluginStore.updateFunctions(finalFunctions)

  // 直接返回
  uni.navigateBack()
}

// 复制MCP地址
function copyMcpAddress() {
  if (!mcpAddress.value) {
    message.alert('暂无MCP地址可复制')
    return
  }

  uni.setClipboardData({
    data: mcpAddress.value,
    showToast: false,
    success: () => {
      message.alert('MCP地址已复制到剪贴板')
    },
    fail: () => {
      message.alert('复制失败，请重试')
    },
  })
}

// 渲染参数字段的辅助函数
function getFieldDisplayValue(field: any, value: any) {
  if (field.type === 'array') {
    return Array.isArray(value) ? value.join('\n') : value || ''
  }
  return value || ''
}

// 字段说明
function getFieldRemark(field: any) {
  let description = field.label || ''
  if (field.default) {
    description += `（默认值：${field.default}）`
  }
  return description
}

onMounted(async () => {
  // 直接从store获取数据并合并
  await mergeFunctions()
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- 头部导航 -->
    <wd-navbar
      title=""
      safe-area-inset-top
      left-arrow
      :bordered="false"
      @click-left="goBack"
    >
      <template #left>
        <wd-icon name="arrow-left" size="18" />
      </template>
    </wd-navbar>

    <!-- 内容区域 -->
    <scroll-view
      scroll-y
      class="box-border flex-1 bg-transparent px-[20rpx]"
      :style="{ height: 'calc(100vh - 120rpx)' }"
      :scroll-with-animation="true"
    >
      <!-- 内置插件区域 -->
      <view class="mt-[20rpx] flex flex-1 flex-col">
        <view class="text-[32rpx] text-[#333] font-medium">
          内置插件
        </view>
        <view
          class="mt-[20rpx] box-border flex flex-1 flex-col rounded-[10rpx] bg-white p-[20rpx]"
        >
          <!-- 分段控制器 -->
          <wd-segmented
            v-model:value="currentSegmented"
            :options="segmentedList"
          />

          <!-- 插件列表 -->
          <view class="mt-[20rpx] flex-1 overflow-hidden">
            <!-- 未选插件 -->
            <scroll-view
              v-if="currentSegmented === '未选'"
              class="max-h-[600rpx] bg-transparent"
              scroll-y
            >
              <view
                v-if="notSelectedList.length === 0"
                class="h-[400rpx] flex items-center justify-center"
              >
                <wd-status-tip image="content" tip="暂无更多插件" />
              </view>
              <view v-else class="p-[20rpx] space-y-[20rpx]">
                <view
                  v-for="func in notSelectedList"
                  :key="func.id"
                  class="flex items-center justify-between border border-[#e9ecef] rounded-[10rpx] bg-[#f8f9fa] p-[20rpx]"
                  @click="selectFunction(func)"
                >
                  <view class="flex-1">
                    <view
                      class="mb-[10rpx] text-[30rpx] text-[#333] font-medium"
                    >
                      {{ func.name }}
                    </view>
                    <view class="text-[24rpx] text-[#666]">
                      {{ func.providerCode }}
                    </view>
                  </view>
                  <view
                    class="h-[60rpx] w-[60rpx] flex items-center justify-center rounded-full bg-[#1677ff]"
                  >
                    <text class="text-[36rpx] text-white">
                      +
                    </text>
                  </view>
                </view>
              </view>
            </scroll-view>

            <!-- 已选插件 -->
            <scroll-view v-else class="max-h-[600rpx] bg-transparent" scroll-y>
              <view
                v-if="selectedList.length === 0"
                class="h-[400rpx] flex items-center justify-center"
              >
                <wd-status-tip image="content" tip="请选择插件功能" />
              </view>
              <view v-else class="p-[20rpx] space-y-[20rpx]">
                <view
                  v-for="func in selectedList"
                  :key="func.id"
                  class="border border-[#d4edff] rounded-[10rpx] bg-[#f0f7ff] p-[20rpx]"
                >
                  <view class="flex items-center justify-between">
                    <view class="flex-1" @click="editFunction(func)">
                      <view
                        class="mb-[10rpx] text-[30rpx] text-[#333] font-medium"
                      >
                        {{ func.name }}
                      </view>
                      <view class="text-[24rpx] text-[#1677ff]">
                        点击配置参数
                      </view>
                    </view>
                    <view class="flex space-x-[20rpx]">
                      <!-- 配置按钮 -->
                      <view
                        class="h-[60rpx] w-[60rpx] flex items-center justify-center rounded-full bg-[#1677ff]"
                        @click="editFunction(func)"
                      >
                        <text class="text-[24rpx] text-white">
                          ⚙
                        </text>
                      </view>
                      <!-- 移除按钮 -->
                      <view
                        class="h-[60rpx] w-[60rpx] flex items-center justify-center rounded-full bg-[#ff4757]"
                        @click="removeFunction(func)"
                      >
                        <text class="text-[32rpx] text-white">
                          ×
                        </text>
                      </view>
                    </view>
                  </view>
                </view>
              </view>
            </scroll-view>
          </view>
        </view>
      </view>

      <!-- MCP接入点区域 -->
      <view class="mt-[20rpx] flex flex-1 flex-col">
        <view class="text-[32rpx] text-[#333] font-medium">
          mcp接入点
        </view>
        <view
          class="mt-[20rpx] box-border flex flex-1 flex-col rounded-[10rpx] bg-white p-[20rpx]"
        >
          <view class="flex items-center justify-between text-[24rpx]">
            <input
              v-model="mcpAddress"
              type="text"
              disabled
              class="flex-1 rounded-[10rpx] bg-[#f5f7fb] p-[20rpx]"
            >
            <view
              class="ml-[20rpx] h-[70rpx] flex items-center justify-center rounded-[10rpx] bg-[#1677ff] px-[20rpx] text-[24rpx] text-white"
              @click="copyMcpAddress"
            >
              复制
            </view>
          </view>
          <!-- 工具列表 -->
          <view class="mt-[20rpx] flex-1 overflow-hidden">
            <scroll-view class="max-h-[600rpx] bg-transparent" scroll-y>
              <view
                v-if="mcpTools && mcpTools.length === 0"
                class="h-[400rpx] flex items-center justify-center"
              >
                <wd-status-tip image="content" tip="暂无工具" />
              </view>
              <view v-else class="p-[20rpx]">
                <view class="flex flex-wrap">
                  <view
                    v-for="tool in mcpTools"
                    :key="tool"
                    class="mb-[20rpx] mr-[20rpx] rounded-[10rpx] bg-[#f5f7fb] p-[20rpx]"
                  >
                    {{ tool }}
                  </view>
                </view>
              </view>
            </scroll-view>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 参数编辑弹窗 -->
    <wd-action-sheet
      v-model="showParamDialog"
      :title="`参数配置 - ${currentFunction?.name || ''}`"
      custom-header-class="h-[75vh]"
      @close="closeParamEdit"
    >
      <scroll-view
        scroll-y
        class="bg-[#f5f7fb]"
        :style="{ height: 'calc(75vh - 60rpx)' }"
      >
        <view class="p-[30rpx] pb-[40rpx]">
          <!-- 无参数提示 -->
          <view
            v-if="
              !currentFunction?.fieldsMeta
                || currentFunction.fieldsMeta.length === 0
            "
            class="h-[400rpx] flex items-center justify-center"
          >
            <text class="text-[28rpx] text-[#999]">
              {{ currentFunction?.name }} 无需配置参数
            </text>
          </view>

          <!-- 参数表单 - 卡片式布局 -->
          <view v-else class="flex flex-col gap-[24rpx]">
            <view
              v-for="field in currentFunction.fieldsMeta"
              :key="field.key"
              class="border border-[#eeeeee] rounded-[20rpx] bg-white p-[30rpx]"
              style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);"
            >
              <!-- 字段信息 -->
              <view class="mb-[24rpx]">
                <text class="mb-[8rpx] block text-[32rpx] text-[#232338] font-medium">
                  {{ field.label }}
                </text>
                <text v-if="getFieldRemark(field)" class="block text-[24rpx] text-[#65686f] leading-[1.5]">
                  {{ getFieldRemark(field) }}
                </text>
              </view>

              <!-- 输入控件 -->
              <view>
                <!-- 字符串类型 -->
                <input
                  v-if="field.type === 'string'"
                  v-model="tempParams[field.key]"
                  class="box-border h-[80rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
                  type="text"
                  :placeholder="`请输入${field.label}`"
                  @input="
                    handleParamChange(field.key, $event.detail.value, field)
                  "
                >

                <!-- 数组类型 -->
                <view v-else-if="field.type === 'array'">
                  <text class="mb-[16rpx] block text-[24rpx] text-[#65686f]">
                    每行输入一个项目
                  </text>
                  <textarea
                    v-model="arrayTextCache[field.key]"
                    class="box-border min-h-[200rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
                    :placeholder="`请输入${field.label}，每行一个`"
                    @input="
                      handleArrayChange(field.key, $event.detail.value, field)
                    "
                  />
                </view>

                <!-- JSON类型 -->
                <view v-else-if="field.type === 'json'">
                  <text class="mb-[16rpx] block text-[24rpx] text-[#65686f]">
                    请输入有效的JSON格式
                  </text>
                  <textarea
                    v-model="jsonTextCache[field.key]"
                    class="box-border min-h-[300rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] font-mono focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
                    placeholder="请输入合法的JSON格式"
                    @blur="
                      handleJsonChange(field.key, $event.detail.value, field)
                    "
                  />
                </view>

                <!-- 数字类型 -->
                <input
                  v-else-if="field.type === 'number'"
                  v-model="tempParams[field.key]"
                  class="box-border h-[80rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
                  type="number"
                  :placeholder="`请输入${field.label}`"
                  @input="
                    handleParamChange(
                      field.key,
                      Number($event.detail.value),
                      field,
                    )
                  "
                >

                <!-- 布尔类型 -->
                <view
                  v-else-if="field.type === 'boolean' || field.type === 'bool'"
                  class="flex items-center justify-between py-[20rpx]"
                >
                  <view class="flex-1">
                    <text class="mb-[8rpx] block text-[28rpx] text-[#232338]">
                      启用功能
                    </text>
                    <text class="block text-[24rpx] text-[#65686f]">
                      开启或关闭此功能
                    </text>
                  </view>
                  <switch
                    :checked="tempParams[field.key]"
                    @change="
                      handleParamChange(field.key, $event.detail.value, field)
                    "
                  />
                </view>

                <!-- 默认字符串类型 -->
                <input
                  v-else
                  v-model="tempParams[field.key]"
                  class="box-border h-[80rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
                  type="text"
                  :placeholder="`请输入${field.label}`"
                  @input="
                    handleParamChange(field.key, $event.detail.value, field)
                  "
                >
              </view>
            </view>
          </view>
        </view>
      </scroll-view>
    </wd-action-sheet>
  </view>
</template>
