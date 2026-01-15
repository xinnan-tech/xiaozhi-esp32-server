<template>
  <svg :class="iconClass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <!-- WiFi waves from outer to inner -->
    <path d="M3 9c4.97-4.97 13.03-4.97 18 0" stroke-width="2" stroke-linecap="round"/>
    <path d="M6 12c3.31-3.31 8.69-3.31 12 0" stroke-width="2" stroke-linecap="round"/>
    <path d="M9 15c1.66-1.66 4.34-1.66 6 0" stroke-width="2" stroke-linecap="round"/>
    <!-- Center dot (device) -->
    <circle cx="12" cy="18" r="1.5" fill="currentColor"/>
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
    default: 'text-blue-500'
  }
})

const iconClass = computed(() => `${props.size} ${props.color}`)
</script>
