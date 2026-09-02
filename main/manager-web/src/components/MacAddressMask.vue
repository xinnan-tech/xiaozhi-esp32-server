<template>
  <span v-if="isValid" class="mac-address-wrapper">{{ prefix }}<span class="mac-address-mask">{{ middle }}</span>{{ suffix }}</span>
  <span v-else>{{ macAddress }}</span>
</template>

<script>
export default {
  props: {
    macAddress: {
      type: String,
      default: '',
    },
  },
  computed: {
    isValid() {
      return /^(?:[0-9A-Z]{2}[:-]){5}[0-9A-Z]{2}$/i.test(this.macAddress);
    },
    segments() {
      return this.macAddress.split(':');
    },
    prefix() {
      return this.segments.slice(0, 2).join(':');
    },
    middle() {
      return ':' + this.segments.slice(2, 4).join(':') + ':';
    },
    suffix() {
      return this.segments.slice(4).join(':');
    },
  },
};
</script>

<style lang="scss" scoped>
.mac-address-wrapper:hover .mac-address-mask {
  filter: none;
}

.mac-address-mask {
  filter: blur(4px);
  transition: filter 0.3s;
}
</style>
