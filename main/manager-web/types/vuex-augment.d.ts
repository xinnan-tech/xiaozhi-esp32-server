// types/vuex-augment.d.ts
import 'vue'
import { Store } from 'vuex'
import type { RootState } from '@/store/types'

declare module 'vue/types/vue' {
    interface Vue {
        $store: Store<RootState>
    }
}
