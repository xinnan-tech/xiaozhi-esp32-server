<template>
    <div class="copyright">
        ©2025 xiaozhi-esp32-server v{{ version }}
    </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
    name: 'VersionFooter',
    computed: {
        ...mapState({
            version: state => state.pubConfig.version
        })
    },
    mounted() {
        this.$store.dispatch('fetchPubConfig');
    }
}
</script>

<style scoped></style>