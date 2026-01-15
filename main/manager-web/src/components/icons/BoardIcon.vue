<template>
  <svg :class="iconClass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <!-- PCB board outline -->
    <rect x="4" y="4" width="16" height="16" rx="1" stroke-width="2"/>
    <!-- Corner mounting holes -->
    <circle cx="6.5" cy="6.5" r="1" stroke-width="1.5"/>
    <circle cx="17.5" cy="6.5" r="1" stroke-width="1.5"/>
    <circle cx="6.5" cy="17.5" r="1" stroke-width="1.5"/>
    <circle cx="17.5" cy="17.5" r="1" stroke-width="1.5"/>
    <!-- Components on board -->
    <rect x="9" y="9" width="6" height="6" rx="0.5" stroke-width="1.5" fill="currentColor" opacity="0.1"/>
    <line x1="9" y1="11" x2="15" y2="11" stroke-width="1" opacity="0.5"/>
    <line x1="9" y1="13" x2="15" y2="13" stroke-width="1" opacity="0.5"/>
    <!-- Connection traces -->
    <line x1="9" y1="12" x2="6" y2="12" stroke-width="1" opacity="0.4"/>
    <line x1="15" y1="12" x2="18" y2="12" stroke-width="1" opacity="0.4"/>
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
