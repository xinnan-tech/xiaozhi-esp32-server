<template>
  <div class="space-y-6">
    <div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">{{ $t('wakewordConfig.title') }}</h3>
      <p class="text-gray-600">
        {{ $t('wakewordConfig.description') }}
      </p>
    </div>

    <!-- 不支持唤醒词的提示 -->
    <div v-if="!canUseAnyWakeword" class="bg-orange-50 border border-orange-200 rounded-lg p-4">
      <div class="text-sm text-orange-800">
        <strong>{{ $t('wakewordConfig.notice') }}</strong>
        <p class="mt-1">{{ $t('wakewordConfig.unsupportedMessage', { chipModel }) }}</p>
      </div>
    </div>

    <div v-else class="space-y-6">
      <!-- 唤醒词类型选择 -->
      <div class="flex space-x-4 justify-center">
        <el-button
          @click="setWakewordType('none')"
          :type="value.type === 'none' ? 'primary' : 'default'"
        >
          {{ $t('wakewordConfig.noWakeword') }}
        </el-button>
        <el-button
          @click="setWakewordType('preset')"
          :type="value.type === 'preset' ? 'primary' : 'default'"
        >
          {{ $t('wakewordConfig.presetWakeword') }}
        </el-button>
        <el-button
          v-if="supportCustom"
          @click="setWakewordType('custom')"
          :type="value.type === 'custom' ? 'primary' : 'default'"
        >
          {{ $t('wakewordConfig.customWakeword') }}
        </el-button>
      </div>

      <!-- 预设唤醒词选择 -->
      <div v-if="value.type === 'preset'" class="space-y-4">
        <label class="block text-sm font-medium text-gray-700">{{ $t('wakewordConfig.selectWakeword') }}</label>
        <div class="relative">
          <select 
            :value="value.preset"
            @change="selectPresetWakeword($event.target.value)"
            class="w-full border border-gray-300 rounded-md px-3 py-2 pr-10 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option
              v-for="wakeword in availableWakewords"
              :key="wakeword.id"
              :value="wakeword.id"
            >
              {{ wakeword.name }} ({{ wakeword.model }})
            </option>
          </select>
        </div>
      </div>

      <!-- 自定义唤醒词设置 -->
      <div v-if="value.type === 'custom'" class="space-y-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
        <h4 class="font-medium text-gray-900">{{ $t('wakewordConfig.customSettings') }}</h4>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ $t('wakewordConfig.wakewordName') }}
              <span class="text-red-500">*</span>
            </label>
            <input 
              type="text"
              v-model="localCustom.name"
              :placeholder="$t('wakewordConfig.wakewordNamePlaceholder')"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              :class="{ 'border-red-500': errors.name }"
            >
            <p v-if="errors.name" class="text-xs text-red-500 mt-1">{{ errors.name }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ $t('wakewordConfig.wakewordCommand') }}
              <span class="text-red-500">*</span>
            </label>
            <input 
              type="text"
              v-model="localCustom.command"
              :placeholder="localCustom.model.includes('_cn') ? $t('wakewordConfig.wakewordCommandPlaceholderCN') : $t('wakewordConfig.wakewordCommandPlaceholderEN')"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              :class="{ 'border-red-500': errors.command }"
            >
            <p v-if="errors.command" class="text-xs text-red-500 mt-1">{{ errors.command }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('wakewordConfig.threshold') }}</label>
            <div class="flex items-center space-x-2">
              <input 
                type="range" 
                v-model.number="localCustom.threshold"
                min="0" max="100" step="1"
                class="flex-1"
              >
              <span class="text-sm text-gray-600 w-8">{{ localCustom.threshold }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-1">{{ $t('wakewordConfig.thresholdDesc') }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ $t('wakewordConfig.duration') }} (ms)
            </label>
            <input 
              type="number"
              v-model.number="localCustom.duration"
              min="500" max="10000" step="100"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              :class="{ 'border-red-500': errors.duration }"
            >
            <p v-if="errors.duration" class="text-xs text-red-500 mt-1">{{ errors.duration }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('wakewordConfig.selectModel') }}</label>
            <select 
              v-model="localCustom.model"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="mn6_cn">{{ $t('wakewordConfig.mn6cn') }}</option>
              <option value="mn6_en">{{ $t('wakewordConfig.mn6en') }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 提示信息 -->
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div class="text-sm text-blue-800">
          <strong>{{ $t('wakewordConfig.tips.tipLabel') }}</strong>
          <ul class="mt-1 list-disc list-inside space-y-1">
            <li>{{ $t('wakewordConfig.tips.optional') }}</li>
            <li v-if="supportWakeNet9s">{{ $t('wakewordConfig.tips.wakeNet9sOnly') }}</li>
            <li v-else-if="supportWakeNet9">{{ $t('wakewordConfig.tips.wakeNet9Full') }}</li>
            <li v-if="supportCustom">{{ $t('wakewordConfig.tips.customSupport') }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Vue from 'vue'
import { mapState } from 'vuex'

export default {
  props: {
    value: {
      type: Object,
      required: true
    },
    chipModel: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      // 完整的唤醒词配置数据
      wakewordData: [
        // WakeNet9s (C3/C5/C6 芯片支持)
        { id: 'wn9s_hilexin', name: 'Hi,乐鑫', model: 'WakeNet9s' },
        { id: 'wn9s_hiesp', name: 'Hi,ESP', model: 'WakeNet9s' },
        { id: 'wn9s_nihaoxiaozhi', name: '你好小智', model: 'WakeNet9s' },
        { id: 'wn9s_hijason', name: 'Hi,Jason', model: 'WakeNet9s' },
        { id: 'wn9s_alexa', name: 'Alexa', model: 'WakeNet9s' },
        
        // WakeNet9 (S3/P4 芯片支持)
        { id: 'wn9_hilexin', name: 'Hi,乐鑫', model: 'WakeNet9' },
        { id: 'wn9_hiesp', name: 'Hi,ESP', model: 'WakeNet9' },
        { id: 'wn9_nihaoxiaozhi_tts', name: '你好小智', model: 'WakeNet9' },
        { id: 'wn9_hijason_tts2', name: 'Hi,Jason', model: 'WakeNet9' },
        { id: 'wn9_nihaomiaoban_tts2', name: '你好喵伴', model: 'WakeNet9' },
        { id: 'wn9_xiaoaitongxue', name: '小爱同学', model: 'WakeNet9' },
        { id: 'wn9_himfive', name: 'Hi,M Five', model: 'WakeNet9' },
        { id: 'wn9_alexa', name: 'Alexa', model: 'WakeNet9' },
        { id: 'wn9_jarvis_tts', name: 'Jarvis', model: 'WakeNet9' },
        { id: 'wn9_computer_tts', name: 'Computer', model: 'WakeNet9' },
        { id: 'wn9_heywillow_tts', name: 'Hey,Willow', model: 'WakeNet9' },
        { id: 'wn9_sophia_tts', name: 'Sophia', model: 'WakeNet9' },
        { id: 'wn9_mycroft_tts', name: 'Mycroft', model: 'WakeNet9' },
        { id: 'wn9_heyprinter_tts', name: 'Hey,Printer', model: 'WakeNet9' },
        { id: 'wn9_hijoy_tts', name: 'Hi,Joy', model: 'WakeNet9' },
        { id: 'wn9_heywanda_tts', name: 'Hey,Wand', model: 'WakeNet9' },
        { id: 'wn9_astrolabe_tts', name: 'Astrolabe', model: 'WakeNet9' },
        { id: 'wn9_heyily_tts2', name: 'Hey,Ily', model: 'WakeNet9' },
        { id: 'wn9_hijolly_tts2', name: 'Hi,Jolly', model: 'WakeNet9' },
        { id: 'wn9_hifairy_tts2', name: 'Hi,Fairy', model: 'WakeNet9' },
        { id: 'wn9_bluechip_tts2', name: 'Blue Chip', model: 'WakeNet9' },
        { id: 'wn9_hiandy_tts2', name: 'Hi,Andy', model: 'WakeNet9' },
        { id: 'wn9_heyivy_tts2', name: 'Hey,Ivy', model: 'WakeNet9' },
        { id: 'wn9_hiwalle_tts2', name: 'Hi,Wall E', model: 'WakeNet9' },
        { id: 'wn9_nihaoxiaoxin_tts', name: '你好小鑫', model: 'WakeNet9' },
        { id: 'wn9_xiaomeitongxue_tts', name: '小美同学', model: 'WakeNet9' },
        { id: 'wn9_hixiaoxing_tts', name: 'Hi,小星', model: 'WakeNet9' },
        { id: 'wn9_xiaolongxiaolong_tts', name: '小龙小龙', model: 'WakeNet9' },
        { id: 'wn9_miaomiaotongxue_tts', name: '喵喵同学', model: 'WakeNet9' },
        { id: 'wn9_himiaomiao_tts', name: 'Hi,喵喵', model: 'WakeNet9' },
        { id: 'wn9_hilili_tts', name: 'Hi,Lily', model: 'WakeNet9' },
        { id: 'wn9_hitelly_tts', name: 'Hi,Telly', model: 'WakeNet9' },
        { id: 'wn9_xiaobinxiaobin_tts', name: '小滨小滨', model: 'WakeNet9' },
        { id: 'wn9_haixiaowu_tts', name: 'Hi,小巫', model: 'WakeNet9' },
        { id: 'wn9_xiaoyaxiaoya_tts2', name: '小鸭小鸭', model: 'WakeNet9' },
        { id: 'wn9_linaiban_tts2', name: '璃奈板', model: 'WakeNet9' },
        { id: 'wn9_xiaosurou_tts2', name: '小酥肉', model: 'WakeNet9' },
        { id: 'wn9_xiaoyutongxue_tts2', name: '小宇同学', model: 'WakeNet9' },
        { id: 'wn9_xiaomingtongxue_tts2', name: '小明同学', model: 'WakeNet9' },
        { id: 'wn9_xiaokangtongxue_tts2', name: '小康同学', model: 'WakeNet9' },
        { id: 'wn9_xiaojianxiaojian_tts2', name: '小箭小箭', model: 'WakeNet9' },
        { id: 'wn9_xiaotexiaote_tts2', name: '小特小特', model: 'WakeNet9' },
        { id: 'wn9_nihaoxiaoyi_tts2', name: '你好小益', model: 'WakeNet9' },
        { id: 'wn9_nihaobaiying_tts2', name: '你好百应', model: 'WakeNet9' },
        { id: 'wn9_xiaoluxiaolu_tts2', name: '小鹿小鹿', model: 'WakeNet9' },
        { id: 'wn9_nihaodongdong_tts2', name: '你好东东', model: 'WakeNet9' },
        { id: 'wn9_nihaoxiaoan_tts2', name: '你好小安', model: 'WakeNet9' },
        { id: 'wn9_ni3hao3xiao3mai4_tts2', name: '你好小脉', model: 'WakeNet9' },
        { id: 'wn9_ni3hao3xiao3rui4_tts3', name: '你好小瑞', model: 'WakeNet9' },
        { id: 'wn9_hai1xiao3ou1_tts3', name: '嗨小欧', model: 'WakeNet9' }
      ],
      localCustom: {
        name: '',
        command: '',
        threshold: 20,
        duration: 3000,
        model: 'mn6_cn'
      },
      errors: {
        name: '',
        command: '',
        duration: ''
      },
      isUpdatingFromProps: false
    }
  },
  computed: {
    // 判断芯片是否支持 WakeNet9
    supportWakeNet9() {
      const chip = this.chipModel.toLowerCase()
      return chip === 'esp32s3' || chip === 'esp32p4'
    },
    // 判断芯片是否支持 WakeNet9s
    supportWakeNet9s() {
      const chip = this.chipModel.toLowerCase()
      return chip === 'esp32c3' || chip === 'esp32c5' || chip === 'esp32c6'
    },
    // 判断芯片是否支持自定义唤醒词 (MultiNet 目前主要支持 S3)
    supportCustom() {
      const chip = this.chipModel.toLowerCase()
      return chip === 'esp32s3'
    },
    canUseAnyWakeword() {
      return this.supportWakeNet9 || this.supportWakeNet9s
    },
    // 根据芯片型号过滤可用的唤醒词
    availableWakewords() {
      if (this.supportWakeNet9) {
        return this.wakewordData.filter(w => w.model === 'WakeNet9')
      } else if (this.supportWakeNet9s) {
        return this.wakewordData.filter(w => w.model === 'WakeNet9s')
      } else {
        return []
      }
    }
  },
  watch: {
    // 监听本地自定义设置变化并同步到父组件
    'localCustom': {
      handler(newVal) {
        if (this.isUpdatingFromProps) return
        
        if (this.value.type === 'custom') {
          this.validate()
          this.$emit('input', {
            ...this.value,
            custom: { ...newVal }
          })
        }
      },
      deep: true
    },
    // 监听父组件属性变化并同步到本地
    'value.custom': {
      handler(newVal) {
        if (newVal) {
          this.isUpdatingFromProps = true
          this.localCustom = {
            name: newVal.name || '',
            command: newVal.command || '',
            threshold: newVal.threshold !== undefined ? newVal.threshold : 20,
            duration: newVal.duration !== undefined ? newVal.duration : 3000,
            model: newVal.model || 'mn6_cn'
          }
          // 使用 $nextTick 避免循环更新
          this.$nextTick(() => {
            this.isUpdatingFromProps = false
          })
        }
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    validate() {
      let isValid = true
      this.errors = { name: '', command: '', duration: '' }

      if (!this.localCustom.name.trim()) {
        this.errors.name = this.$t('wakewordConfig.errors.nameRequired')
        isValid = false
      }
      if (!this.localCustom.command.trim()) {
        this.errors.command = this.$t('wakewordConfig.errors.commandRequired')
        isValid = false
      } else if (this.localCustom.model.includes('_en')) {
        // English model doesn't support punctuation
        if (/[!,.?]/.test(this.localCustom.command)) {
          this.errors.command = this.$t('wakewordConfig.errors.noPunctuation')
          isValid = false
        }
      }

      if (!this.localCustom.duration || this.localCustom.duration < 500 || this.localCustom.duration > 10000) {
        this.errors.duration = this.$t('wakewordConfig.errors.durationRange')
        isValid = false
      }

      return isValid
    },
    setWakewordType(type) {
      this.$emit('input', {
        ...this.value,
        type,
        preset: type === 'preset' ? (this.value.preset || this.availableWakewords[0]?.id || '') : '',
        custom: {
          ...this.value.custom,
          ...this.localCustom
        }
      })
    },
    selectPresetWakeword(id) {
      this.$emit('input', {
        ...this.value,
        preset: id
      })
    }
  }
}
</script>
