<template>
    <div class="copyright">
        ©2025 xiaozhi-esp32-server v{{ version }}
    </div>
</template>

<script>
import Api from '@/apis/api';

export default {
    name: 'VersionFooter',
    data() {
        return {
            version: ''
        }
    },
    mounted() {
        this.getSystemVersion();
    },
    methods: {
        getSystemVersion() {
            const storedVersion = sessionStorage.getItem('systemVersion');
            if (storedVersion) {
                this.version = storedVersion;
                return;
            }

            Api.user.getPubConfig(({ data }) => {
                if (data.code === 0 && data.data.version) {
                    this.version = data.data.version;
                    sessionStorage.setItem('systemVersion', data.data.version);
                }
            });
        }
    }
}
</script>

<style scoped></style>