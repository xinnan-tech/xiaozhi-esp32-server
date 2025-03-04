<!-- components/SwitchToggle.vue -->
<template>
    <div class="switch" :class="{ 'is-checked': isChecked }" @click="toggle">
      <div class="switch-core"></div>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  
  const isChecked = ref(false);
  
  const toggle = () => {
    isChecked.value = !isChecked.value;
  };
  </script>
  
  <style scoped>
  .switch {
    position: relative;
    display: inline-flex;
    align-items: center;
    width: 40px;
    height: 20px;
    line-height: 20px;
    background-color: #dcdfe6;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.3s;
  }
  
  .switch.is-checked {
    background-color: #4178EE;
  }
  
  .switch-core {
    position: absolute;
    left: 2px;
    top: 2px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background-color: #fff;
    transition: all 0.3s;
  }
  
  .switch.is-checked .switch-core {
    left: 22px;
  }
  </style>