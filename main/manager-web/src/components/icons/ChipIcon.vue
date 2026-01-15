<template>
  <svg :class="iconClass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <rect x="7" y="7" width="10" height="10" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="9" y="9" width="6" height="6" stroke-width="1.5" fill="currentColor" opacity="0.1"/>
    <line x1="7" y1="9" x2="4" y2="9" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="7" y1="12" x2="4" y2="12" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="7" y1="15" x2="4" y2="15" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="17" y1="9" x2="20" y2="9" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="17" y1="12" x2="20" y2="12" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="17" y1="15" x2="20" y2="15" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="9" y1="7" x2="9" y2="4" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="12" y1="7" x2="12" y2="4" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="15" y1="7" x2="15" y2="4" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="9" y1="17" x2="9" y2="20" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="12" y1="17" x2="12" y2="20" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="15" y1="17" x2="15" y2="20" stroke-width="1.5" stroke-linecap="round"/>
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
    default: 'text-gray-400'
  }
})

const iconClass = computed(() => `${props.size} ${props.color}`)
</script>
