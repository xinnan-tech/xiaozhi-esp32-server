<template>
  <svg :class="iconClass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <!-- Flash chip body -->
    <rect x="6" y="5" width="12" height="14" rx="1" stroke-width="2"/>
    <!-- Pins on left -->
    <line x1="6" y1="8" x2="4" y2="8" stroke-width="1.5"/>
    <line x1="6" y1="11" x2="4" y2="11" stroke-width="1.5"/>
    <line x1="6" y1="14" x2="4" y2="14" stroke-width="1.5"/>
    <line x1="6" y1="17" x2="4" y2="17" stroke-width="1.5"/>
    <!-- Pins on right -->
    <line x1="18" y1="8" x2="20" y2="8" stroke-width="1.5"/>
    <line x1="18" y1="11" x2="20" y2="11" stroke-width="1.5"/>
    <line x1="18" y1="14" x2="20" y2="14" stroke-width="1.5"/>
    <line x1="18" y1="17" x2="20" y2="17" stroke-width="1.5"/>
    <!-- Lightning bolt icon for flash -->
    <path d="M13 7l-3 5h2l-1 4 3-5h-2l1-4z" fill="currentColor" opacity="0.5"/>
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
