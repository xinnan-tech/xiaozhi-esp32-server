<script lang="ts">
import { defineComponent } from 'vue'
// #ifdef APP-PLUS
import { ensureSecureRandomReady, registerRandomBridge } from '@/utils/secure-random'
// #endif

interface BridgeItem {
  length: number
  resolve: (bytes: number[]) => void
  reject: (err: Error) => void
}

/**
 * App 端专用（页面中 #ifdef APP-PLUS 条件挂载）：
 * 逻辑层无 Web Crypto，经 renderjs 在视图层 WebView 取
 * crypto.getRandomValues 后 callMethod 回传，注册为 secure-random 的随机源。
 */
export default defineComponent({
  data() {
    return {
      /** 变化后触发 renderjs 取随机（每次新对象引用确保 prop 变更被感知） */
      bridgeRequest: null as { id: number, length: number } | null,
      // 仅类型检查用：renderjs 模块绑定由 uni-app 编译期处理，运行时不读取
      secureRandomRenderer: { onPropChange: () => {} } as { onPropChange: (...args: any[]) => void },
      seq: 0,
      queue: [] as BridgeItem[],
      sending: false,
      currentId: 0,
      timeoutTimer: undefined as ReturnType<typeof setTimeout> | undefined,
    }
  },
  mounted() {
    // #ifdef APP-PLUS
    registerRandomBridge((length: number) =>
      this.requestBytes(length).then(bytes => new Uint8Array(bytes)),
    )
    ensureSecureRandomReady().catch((e: Error) => {
      console.warn('[secure-random] App 端随机源预热失败', e)
    })
    // #endif
  },
  beforeUnmount() {
    clearTimeout(this.timeoutTimer)
  },
  methods: {
    requestBytes(length: number): Promise<number[]> {
      return new Promise((resolve, reject) => {
        this.queue.push({ length, resolve, reject })
        this.pump()
      })
    },
    /** 串行发送：prop 变更过快时视图层可能丢失中间状态，故一次只发一个请求 */
    pump() {
      if (this.sending || this.queue.length === 0)
        return
      this.sending = true
      const item = this.queue[0]
      this.currentId = ++this.seq
      this.bridgeRequest = { id: this.currentId, length: item.length }
      // 超时保护：视图层无响应时按 fail-closed 报错，避免登录流程永久挂起
      clearTimeout(this.timeoutTimer)
      this.timeoutTimer = setTimeout(() => {
        this.onRandomResult({ id: this.currentId, error: 'renderjs 随机数请求超时' })
      }, 5000)
    },
    /** renderjs 通过 callMethod 回传结果（或错误） */
    onRandomResult(res: { id: number, bytes?: number[], error?: string }) {
      if (res.id !== this.currentId)
        return
      clearTimeout(this.timeoutTimer)
      const item = this.queue.shift()
      this.sending = false
      if (item) {
        if (res.error)
          item.reject(new Error(res.error))
        else
          item.resolve(res.bytes || [])
      }
      this.pump()
    },
  },
})
</script>

<script module="secureRandomRenderer" lang="renderjs">
// 视图层（WebView）：可访问 crypto.getRandomValues
export default {
  methods: {
    onPropChange(newVal, oldVal, ownerInstance, instance) {
      if (!newVal || !newVal.id || !newVal.length)
        return
      try {
        const cryptoObj = (typeof crypto !== 'undefined' && crypto)
          || (typeof window !== 'undefined' && window.crypto)
        if (!cryptoObj || typeof cryptoObj.getRandomValues !== 'function')
          throw new Error('视图层缺少 crypto.getRandomValues')
        const bytes = new Uint8Array(newVal.length)
        cryptoObj.getRandomValues(bytes)
        ownerInstance.callMethod('onRandomResult', { id: newVal.id, bytes: Array.from(bytes) })
      }
      catch (e) {
        ownerInstance.callMethod('onRandomResult', {
          id: newVal.id,
          error: String((e && e.message) || e),
        })
      }
    },
  },
}
</script>

<template>
  <view
    class="secure-random-bridge"
    :prop="bridgeRequest"
    :change:prop="secureRandomRenderer.onPropChange"
  />
</template>

<style>
.secure-random-bridge {
  width: 0;
  height: 0;
  overflow: hidden;
}
</style>
