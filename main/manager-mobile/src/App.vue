<template>
  <router-view />
</template>

<script setup lang="ts">
// For H5 platform, we'll use Vue lifecycle hooks instead
import { onMounted } from 'vue'

onMounted(() => {
  console.log('App mounted')
})
</script>

<style>
/* Global app styles */
page {
  background-color: #f5f5f5;
}

.container {
  padding: 20rpx;
}
</style>