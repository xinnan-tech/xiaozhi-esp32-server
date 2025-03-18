<template>
  <div v-if="visible" class="message">
          {{message}}
        </div>
</template>

<script>
export default {
  name: 'Footer',
  props: {
    visible: { type: Boolean, required: true },
    message: { type: String, required: false, default: '©2025 xiaozhi-esp32-server' }
  },
  data() {
    return {  }
  },
  methods: {
  }
}
</script>

<style scoped>
.message {
  font-size: 14px;
  font-weight: 400;
  margin-top: auto;
  padding-top: 30px;
  color: #979db1;
}
</style>