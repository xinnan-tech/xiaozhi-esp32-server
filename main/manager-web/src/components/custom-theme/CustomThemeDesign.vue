<template>
  <div class="theme-design-wrapper">
    <div class="design-header">
      <h2 class="design-title">{{ $t('device.customThemeStep2') }}</h2>
      <p class="design-desc">{{ $t('device.customThemeDesignDesc') }}</p>
    </div>

    <div class="tab-navigation">
      <div class="tab-nav-container">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-nav-item"
          :class="{ active: currentTab === tab.id }"
          @click="handleTabClick(tab.id)"
        >
          <span class="tab-nav-content">
            <i :class="tab.icon" class="tab-icon"></i>
            <span class="tab-text">{{ tab.name }}</span>
            <span v-if="getTabStatus(tab.id)" class="tab-status-dot"></span>
          </span>
        </button>
      </div>
    </div>

    <div class="tab-content-wrapper">
      <CustomThemeWakewordConfig
        v-if="currentTab === 'wakeword'"
        v-model="localValue.wakeword"
        :chip-model="chipModel"
      />
      <CustomThemeFontConfig
        v-if="currentTab === 'font'"
        v-model="localValue.font"
      />
      <CustomThemeEmojiConfig
        v-if="currentTab === 'emoji'"
        v-model="localValue.emoji"
        :display-size="chipDisplay"
      />
      <CustomThemeBackgroundConfig
        v-if="currentTab === 'background'"
        v-model="localValue.skin"
      />
    </div>

    <div class="navigation-buttons">
      <el-button @click="handlePrev">{{ $t('device.customThemePrev') }}</el-button>
      <el-button type="primary" :disabled="!canProceed" @click="handleNext">
        {{ $t('device.customThemeNext') }}
      </el-button>
    </div>
  </div>
</template>

<script>
import CustomThemeWakewordConfig from './tabs/CustomThemeWakewordConfig.vue';
import CustomThemeFontConfig from './tabs/CustomThemeFontConfig.vue';
import CustomThemeEmojiConfig from './tabs/CustomThemeEmojiConfig.vue';
import CustomThemeBackgroundConfig from './tabs/CustomThemeBackgroundConfig.vue';

export default {
  name: 'CustomThemeDesign',
  components: {
    CustomThemeWakewordConfig,
    CustomThemeFontConfig,
    CustomThemeEmojiConfig,
    CustomThemeBackgroundConfig
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
    chipDisplay: {
      type: Object,
      default: () => ({ width: 32, height: 32 })
    },
    activeTab: {
      type: String,
      default: 'wakeword'
    }
  },
  data() {
    return {
      currentTab: this.activeTab,
      tabs: [
        { id: 'wakeword', name: this.$t('device.customThemeWakewordTab'), icon: 'el-icon-microphone' },
        { id: 'font', name: this.$t('device.customThemeFontTab'), icon: 'el-icon-edit-outline' },
        { id: 'emoji', name: this.$t('device.customThemeEmojiTab'), icon: 'el-icon-star-on' },
        { id: 'background', name: this.$t('device.customThemeBackgroundTab'), icon: 'el-icon-picture' }
      ]
    };
  },
  computed: {
    localValue: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit('input', val);
      }
    },
    getTabStatus() {
      return (tabId) => {
        switch (tabId) {
          case 'wakeword':
            return !!this.localValue.wakeword;
          case 'font':
            return this.localValue.font.preset || this.localValue.font.custom.file;
          case 'emoji':
            return this.localValue.emoji.preset || Object.keys(this.localValue.emoji.custom.images).length > 0;
          case 'background':
            return true;
          default:
            return false;
        }
      };
    },
    canProceed() {
      const hasFont = this.localValue.font.preset || this.localValue.font.custom.file;
      const hasEmoji = this.localValue.emoji.preset || Object.keys(this.localValue.emoji.custom.images).length > 0;
      return hasFont && hasEmoji;
    }
  },
  watch: {
    activeTab(newVal) {
      this.currentTab = newVal;
    }
  },
  methods: {
    handleTabClick(id) {
      this.currentTab = id;
      this.$emit('tabChange', id);
    },
    handleNext() {
      if (this.canProceed) this.$emit('next');
      else this.$message.warning(this.$t('device.customThemeIncompleteConfig'));
    },
    handlePrev() {
      this.$emit('prev');
    }
  }
};
</script>

<style scoped>
.theme-design-wrapper {
  padding: 10px 6px;
  text-align: left;
}
.design-header {
  margin-bottom: 16px;
}
.design-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 6px;
}
.design-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
.tab-navigation {
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 16px;
}
.tab-nav-container {
  display: flex;
  gap: 24px;
}
.tab-nav-item {
  padding: 8px 4px;
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
}
.tab-nav-item.active {
  color: #409eff;
  border-bottom-color: #409eff;
}
.tab-nav-item:hover {
  color: #374151;
}
.tab-nav-content {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tab-status-dot {
  width: 8px;
  height: 8px;
  background: #67c23a;
  border-radius: 50%;
}
.tab-content-wrapper {
  min-height: 360px;
}
.navigation-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>

