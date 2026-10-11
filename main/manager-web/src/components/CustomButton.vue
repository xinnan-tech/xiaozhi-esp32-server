<template>
  <el-button
    :class="['custom-button', `custom-button--${type}`]"
    v-bind="$attrs"
    @click="$emit('click', $event)"
  >
    <slot />
  </el-button>
</template>

<script>
export default {
  name: 'CustomButton',
  props: {
    type: {
      type: String,
      default: 'default',
      validator: (val) => ['default', 'confirm', 'delete', 'add'].includes(val)
    }
  }
};
</script>

<style lang="scss" scoped>
.custom-button--default {
  width: fit-content;
  background: #4998ff;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  transition: all 0.3s ease;

  &.el-button--small {
    padding: 9px 14px;
    font-size: 12px;
  }
  &.el-button--medium {
    padding: 12px 20px;
  }

  &:hover {
    background: #62a4fc;
    color: #ffffff;
    border-color: transparent;
    box-shadow: 0 2px 8px rgba(74, 124, 253, 0.2);
    transform: translateY(-2px);
  }

  &.is-disabled,
  &.is-disabled:hover {
    background: linear-gradient(to right, #f0f3fe, #f5f6fe);
    color: rgba(74, 124, 253, 0.5);
    border-color: transparent;
    box-shadow: none;
    transform: none;
    cursor: not-allowed;
  }
}

.custom-button--confirm {
  width: fit-content;
  background: linear-gradient(to right, #4a7cfd, #8154fc);
  color: white;
  border: none;
  border-radius: 4px;
  transition: all 0.3s ease;

  &.el-button--small {
    padding: 9px 14px;
    font-size: 12px;
  }
  &.el-button--medium {
    padding: 12px 20px;
  }

  &:hover {
    color: white;
    border-color: transparent;
    box-shadow: 0 2px 8px rgba(74, 124, 253, 0.3);
    transform: translateY(-2px);
  }

  &.is-disabled,
  &.is-disabled:hover {
    background: linear-gradient(to right, #a0b4fd, #b8a4fd);
    color: rgba(255, 255, 255, 0.6);
    border-color: transparent;
    box-shadow: none;
    transform: none;
    cursor: not-allowed;
  }
}

.custom-button--delete {
  width: fit-content;
  background: #ff6b6b;
  color: white;
  border: none;
  border-radius: 4px;
  transition: all 0.3s ease;

  &.el-button--small {
    padding: 9px 14px;
    font-size: 12px;
  }
  &.el-button--medium {
    padding: 12px 20px;
  }

  &:hover {
    color: white;
    border-color: transparent;
    box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
    transform: translateY(-2px);
  }

  &.is-disabled,
  &.is-disabled:hover {
    background: linear-gradient(to right, #ffaaaa, #ffcaca);
    color: rgba(255, 255, 255, 0.6);
    border-color: transparent;
    box-shadow: none;
    transform: none;
    cursor: not-allowed;
  }
}

.custom-button--add {
  width: fit-content;
  background: #52c41a;
  color: white;
  border: none;
  border-radius: 4px;
  transition: all 0.3s ease;

  &.el-button--small {
    padding: 9px 14px;
    font-size: 12px;
  }
  &.el-button--medium {
    padding: 12px 20px;
  }

  &:hover {
    color: white;
    border-color: transparent;
    box-shadow: 0 2px 8px rgba(82, 196, 26, 0.3);
    transform: translateY(-2px);
  }

  &.is-disabled,
  &.is-disabled:hover {
    background: linear-gradient(to right, #a0e89a, #c4f0c0);
    color: rgba(255, 255, 255, 0.6);
    border-color: transparent;
    box-shadow: none;
    transform: none;
    cursor: not-allowed;
  }
}
</style>
