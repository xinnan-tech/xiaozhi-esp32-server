<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ $t('themeDesign.title') }}</h2>
      <p class="text-gray-600 mb-6">{{ $t('themeDesign.description') }}</p>
    </div>

    <!-- Tab Navigation -->
    <div class="border-b border-gray-200">
      <nav class="-mb-px p-0 flex space-x-4 sm:space-x-8">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="handleTabClick(tab.id)"
          :class="[
            'py-2 px-1 border-b-2 font-medium text-sm relative',
            currentTab === tab.id
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          ]"
        >
          <span class="flex items-center">
            <component :is="tab.icon" class="w-5 h-5 sm:mr-2" />
            <span class="hidden sm:inline">{{ tab.name }}</span>
          </span>
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div class="min-h-96">
      <WakewordConfig 
        v-if="currentTab === 'wakeword'"
        v-model="localValue.wakeword"
        :chipModel="chipModel"
      />
      
      <FontConfig 
        v-if="currentTab === 'font'"
        v-model="localValue.font"
      />
      
      <EmojiConfig 
        v-if="currentTab === 'emoji'"
        v-model="localValue.emoji"
      />
      
      <BackgroundConfig 
        v-if="currentTab === 'background'"
        v-model="localValue.skin"
      />
    </div>

    <!-- Navigation Buttons -->
    <div class="flex justify-between">
      <button 
        @click="$emit('prev')"
        class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
      >
        {{ $t('themeDesign.previous') }}
      </button>
      <button 
        @click="handleNext"
        class="bg-primary-500 hover:bg-primary-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
      >
        {{ $t('themeDesign.next') }}
      </button>
    </div>
  </div>
</template>

<script>
import WakewordConfig from './tabs/WakewordConfig.vue'
import FontConfig from './tabs/FontConfig.vue'
import EmojiConfig from './tabs/EmojiConfig.vue'
import BackgroundConfig from './tabs/BackgroundConfig.vue'

// Icons (simple SVG components)
// 麦克风图标
const MicrophoneIcon = {
  render(h) { // 接收 h 函数（createElement）作为参数
    return h('svg', {
      // SVG 基础属性（放在 attrs 中）
      attrs: {
        fill: 'none',
        stroke: 'currentColor',
        viewBox: '0 0 24 24'
      },
      // 样式类名（可选，也可在使用时传递）
      class: 'w-5 h-5'
    }, [
      // 子节点：path 标签
      h('path', {
        attrs: {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z'
        }
      })
    ]);
  }
};

// 字体图标
const FontIcon = {
  render(h) {
    return h('svg', {
      attrs: {
        xmlns: 'http://www.w3.org/2000/svg',
        fill: 'currentColor',
        viewBox: '0 0 640 640'
      },
      class: 'w-5 h-5'
    }, [
      h('path', {
        attrs: {
          d: 'M320 96C329.5 96 338 101.5 341.9 110.2L515.1 496L536 496C549.3 496 560 506.7 560 520C560 533.3 549.3 544 536 544L440 544C426.7 544 416 533.3 416 520C416 506.7 426.7 496 440 496L462.5 496L426.6 416L213.4 416L177.5 496L200 496C213.3 496 224 506.7 224 520C224 533.3 213.3 544 200 544L104 544C90.7 544 80 533.3 80 520C80 506.7 90.7 496 104 496L124.9 496L298.1 110.2C302 101.5 310.5 96 320 96zM320 178.6L235 368L405 368L320 178.6z'
        }
      })
    ]);
  }
};

// 表情图标
const EmojiIcon = {
  render(h) {
    return h('svg', {
      attrs: {
        fill: 'none',
        stroke: 'currentColor',
        viewBox: '0 0 24 24'
      },
      class: 'w-5 h-5'
    }, [
      h('path', {
        attrs: {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
        }
      })
    ]);
  }
};

// 背景图标
const BackgroundIcon = {
  render(h) {
    return h('svg', {
      attrs: {
        xmlns: 'http://www.w3.org/2000/svg',
        fill: 'currentColor',
        viewBox: '0 0 640 640'
      },
      class: 'w-5 h-5'
    }, [
      h('path', {
        attrs: {
          d: 'M160 144C151.2 144 144 151.2 144 160L144 480C144 488.8 151.2 496 160 496L480 496C488.8 496 496 488.8 496 480L496 160C496 151.2 488.8 144 480 144L160 144zM96 160C96 124.7 124.7 96 160 96L480 96C515.3 96 544 124.7 544 160L544 480C544 515.3 515.3 544 480 544L160 544C124.7 544 96 515.3 96 480L96 160zM224 192C241.7 192 256 206.3 256 224C256 241.7 241.7 256 224 256C206.3 256 192 241.7 192 224C192 206.3 206.3 192 224 192zM360 264C368.5 264 376.4 268.5 380.7 275.8L460.7 411.8C465.1 419.2 465.1 428.4 460.8 435.9C456.5 443.4 448.6 448 440 448L200 448C191.1 448 182.8 443 178.7 435.1C174.6 427.2 175.2 417.6 180.3 410.3L236.3 330.3C240.8 323.9 248.1 320.1 256 320.1C263.9 320.1 271.2 323.9 275.7 330.3L292.9 354.9L339.4 275.9C343.7 268.6 351.6 264.1 360.1 264.1z'
        }
      })
    ]);
  }
};

export default {
  name: 'ThemeDesign',
  components: {
    WakewordConfig,
    FontConfig,
    EmojiConfig,
    BackgroundConfig,
    MicrophoneIcon,
    FontIcon,
    EmojiIcon,
    BackgroundIcon
  },
  props: {
    value: {
      type: Object,
      required: true
    },
    chipModel: {
      type: String,
      required: true
    },
    activeTab: {
      type: String,
      default: 'wakeword'
    }
  },
  data() {
    return {
      currentTab: this.activeTab
    }
  },
  computed: {
    // 使用计算属性来获取翻译后的tab名称
    tabs() {
      return [
        { id: 'wakeword', name: this.$t('themeDesign.tabs.wakeword'), icon: 'MicrophoneIcon' },
        { id: 'font', name: this.$t('themeDesign.tabs.font'), icon: 'FontIcon' },
        { id: 'emoji', name: this.$t('themeDesign.tabs.emoji'), icon: 'EmojiIcon' },
        { id: 'background', name: this.$t('themeDesign.tabs.background'), icon: 'BackgroundIcon' }
      ]
    },
    localValue: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit('update:value', value);
      }
    }
  },
  watch: {
    // 监听外部activeTab的变化
    activeTab(newTab) {
      this.currentTab = newTab
    },
  },
  methods: {
    // 更新模型值
    updateModel(key, value) {
      const newModel = { ...this.value }
      newModel[key] = value
      this.$emit('input', newModel)
      this.$emit('update:value', newModel) // 兼容Vue 3
    },
    
    handleNext() {
      // 校验唤醒词配置
      const wakeword = this.value.wakeword
      if (wakeword.type === 'custom') {
        if (!wakeword.custom.name?.trim()) {
          alert(this.$t('wakewordConfig.errors.nameRequired'))
          return
        }
        if (!wakeword.custom.command?.trim()) {
          alert(this.$t('wakewordConfig.errors.commandRequired'))
          return
        }
        if (!wakeword.custom.duration || wakeword.custom.duration < 500 || wakeword.custom.duration > 10000) {
          alert(this.$t('wakewordConfig.errors.durationRange'))
          return
        }
      }

      // 校验字体配置
      const font = this.value.font
      if (font.type === 'custom' && !font.custom?.file) {
        alert(this.$t('fontConfig.selectValidFontFile'))
        return
      }

      this.$emit('next')
    },
    
    handleTabClick(tabId) {
      this.currentTab = tabId
      this.$emit('tabChange', tabId)
    }
  },
}
</script>
