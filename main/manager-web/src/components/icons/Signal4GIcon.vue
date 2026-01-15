<template>
  <svg :class="iconClass" fill="currentColor" viewBox="0 0 24 24">
    <!-- Signal bars -->
    <rect x="2" y="16" width="3" height="6" rx="0.5"/>
    <rect x="7" y="12" width="3" height="10" rx="0.5" opacity="0.8"/>
    <rect x="12" y="8" width="3" height="14" rx="0.5" opacity="0.6"/>
    <rect x="17" y="4" width="3" height="18" rx="0.5" opacity="0.4"/>
    <!-- 4G text -->
    <text x="21" y="8" font-size="6" font-weight="bold" fill="currentColor">4G</text>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: String,
    default: 'w-4 h-4'
  },
  color: {
    type: String,
    default: 'text-green-500'
  }
})

const iconClass = computed(() => `${props.size} ${props.color}`)
</script>
