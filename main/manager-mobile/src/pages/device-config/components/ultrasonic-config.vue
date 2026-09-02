<script setup lang="ts">
import { computed, ref } from 'vue'
import { useToast } from 'wot-design-uni/components/wd-toast'
import { t } from '@/i18n'

// 类型定义
interface WiFiNetwork {
  ssid: string
  rssi: number
  authmode: number
  channel: number
}

// Props
interface Props {
  selectedNetwork: WiFiNetwork | null
  password: string
}

const props = defineProps<Props>()

// Toast 实例
const toast = useToast()

// 响应式数据
const generating = ref(false)
const playing = ref(false)
const audioGenerated = ref(false)
const autoLoop = ref(true)
const audioFilePath = ref('')
const audioContext = ref<any>(null)

// AFSK调制参数 - 参考HTML文件
const MARK = 1800 // 二进制1的频率 (Hz)
const SPACE = 1500 // 二进制0的频率 (Hz)
const SAMPLE_RATE = 44100 // 采样率
const BIT_RATE = 100 // 比特率 (bps)
const START_BYTES = [0x01, 0x02] // 起始标记
const END_BYTES = [0x03, 0x04] // 结束标记

// 计算属性
const canGenerate = computed(() => {
  if (!props.selectedNetwork)
    return false
  if (props.selectedNetwork.authmode > 0 && !props.password)
    return false
  return true
})

const audioLengthText = computed(() => {
  if (!props.selectedNetwork)
    return '0秒'
  const dataStr = `${props.selectedNetwork.ssid}\n${props.password}`
  const textBytes = stringToBytes(dataStr)
  const totalBits = (START_BYTES.length + textBytes.length + 1 + END_BYTES.length) * 8
  const duration = Math.ceil(totalBits / BIT_RATE)
  return `${t('deviceConfig.about')}${duration}${t('deviceConfig.seconds')}`
})

// 字符串转字节数组 - uniapp兼容版本
function stringToBytes(str: string): number[] {
  const bytes: number[] = []
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i)
    if (code < 0x80) {
      bytes.push(code)
    }
    else if (code < 0x800) {
      bytes.push(0xC0 | (code >> 6))
      bytes.push(0x80 | (code & 0x3F))
    }
    else if (code < 0xD800 || code >= 0xE000) {
      bytes.push(0xE0 | (code >> 12))
      bytes.push(0x80 | ((code >> 6) & 0x3F))
      bytes.push(0x80 | (code & 0x3F))
    }
    else {
      // 代理对处理
      i++
      const hi = code
      const lo = str.charCodeAt(i)
      const codePoint = 0x10000 + (((hi & 0x3FF) << 10) | (lo & 0x3FF))
      bytes.push(0xF0 | (codePoint >> 18))
      bytes.push(0x80 | ((codePoint >> 12) & 0x3F))
      bytes.push(0x80 | ((codePoint >> 6) & 0x3F))
      bytes.push(0x80 | (codePoint & 0x3F))
    }
  }
  return bytes
}

// 校验和计算 - 参考HTML文件
function checksum(data: number[]): number {
  return data.reduce((sum, b) => (sum + b) & 0xFF, 0)
}

// 字节转比特位 - 参考HTML文件
function toBits(byte: number): number[] {
  const bits: number[] = []
  for (let i = 7; i >= 0; i--) {
    bits.push((byte >> i) & 1)
  }
  return bits
}

// AFSK调制 - 参考HTML文件算法
function afskModulate(bits: number[]): Float32Array {
  const samplesPerBit = SAMPLE_RATE / BIT_RATE
  const totalSamples = Math.floor(bits.length * samplesPerBit)
  const buffer = new Float32Array(totalSamples)

  for (let i = 0; i < bits.length; i++) {
    const freq = bits[i] ? MARK : SPACE
    for (let j = 0; j < samplesPerBit; j++) {
      const t = (i * samplesPerBit + j) / SAMPLE_RATE
      buffer[i * samplesPerBit + j] = Math.sin(2 * Math.PI * freq * t)
    }
  }

  return buffer
}

// 浮点转16位PCM - 参考HTML文件
function floatTo16BitPCM(floatSamples: Float32Array): Uint8Array {
  const buffer = new Uint8Array(floatSamples.length * 2)
  for (let i = 0; i < floatSamples.length; i++) {
    const s = Math.max(-1, Math.min(1, floatSamples[i]))
    const val = s < 0 ? s * 0x8000 : s * 0x7FFF
    buffer[i * 2] = val & 0xFF
    buffer[i * 2 + 1] = (val >> 8) & 0xFF
  }
  return buffer
}

// base64编码表
const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

// 兼容的base64编码实现
function base64Encode(bytes: Uint8Array): string {
  let result = ''
  let i = 0

  while (i < bytes.length) {
    const a = bytes[i++]
    const b = i < bytes.length ? bytes[i++] : 0
    const c = i < bytes.length ? bytes[i++] : 0

    const bitmap = (a << 16) | (b << 8) | c

    result += base64Chars.charAt((bitmap >> 18) & 63)
    result += base64Chars.charAt((bitmap >> 12) & 63)
    result += i - 2 < bytes.length ? base64Chars.charAt((bitmap >> 6) & 63) : '='
    result += i - 1 < bytes.length ? base64Chars.charAt(bitmap & 63) : '='
  }

  return result
}

// 数组转base64编码 - 兼容版本
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)

  // 尝试使用原生btoa，如果不存在则使用自定义实现
  if (typeof btoa !== 'undefined') {
    let binary = ''
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }
  else {
    return base64Encode(bytes)
  }
}

// 构建WAV文件 - 返回ArrayBuffer而不是Blob
function buildWav(pcm: Uint8Array): ArrayBuffer {
  const wavHeader = new Uint8Array(44)
  const dataLen = pcm.length
  const fileLen = 36 + dataLen

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      wavHeader[offset + i] = str.charCodeAt(i)
    }
  }

  const write32 = (offset: number, value: number) => {
    wavHeader[offset] = value & 0xFF
    wavHeader[offset + 1] = (value >> 8) & 0xFF
    wavHeader[offset + 2] = (value >> 16) & 0xFF
    wavHeader[offset + 3] = (value >> 24) & 0xFF
  }

  const write16 = (offset: number, value: number) => {
    wavHeader[offset] = value & 0xFF
    wavHeader[offset + 1] = (value >> 8) & 0xFF
  }

  writeStr(0, 'RIFF')
  write32(4, fileLen)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  write32(16, 16)
  write16(20, 1)
  write16(22, 1)
  write32(24, SAMPLE_RATE)
  write32(28, SAMPLE_RATE * 2)
  write16(32, 2)
  write16(34, 16)
  writeStr(36, 'data')
  write32(40, dataLen)

  // 合并header和数据
  const result = new ArrayBuffer(44 + dataLen)
  const resultView = new Uint8Array(result)
  resultView.set(wavHeader)
  resultView.set(pcm, 44)

  return result
}

// 生成并播放声波 - 主要功能函数
async function generateAndPlay() {
  if (!canGenerate.value || !props.selectedNetwork)
    return

  generating.value = true

  try {
    console.log(`${t('deviceConfig.generatingUltrasonicConfigAudio')}...`)

    // 准备配网数据 - 参考HTML文件格式
    const dataStr = `${props.selectedNetwork.ssid}\n${props.password}`
    const textBytes = stringToBytes(dataStr)
    const fullBytes = [...START_BYTES, ...textBytes, checksum(textBytes), ...END_BYTES]

    console.log(`${t('deviceConfig.configData')}:`, { ssid: props.selectedNetwork.ssid, password: props.password })
    console.log(`${t('deviceConfig.dataBytesLength')}:`, textBytes.length)

    // 转换为比特流
    let bits: number[] = []
    fullBytes.forEach((b) => {
      bits = bits.concat(toBits(b))
    })

    console.log(`${t('deviceConfig.bitStreamLength')}:`, bits.length)

    // AFSK调制 - 减少采样率降低文件大小
    const reducedSampleRate = 22050 // 降低采样率
    const samplesPerBit = reducedSampleRate / BIT_RATE
    const totalSamples = Math.floor(bits.length * samplesPerBit)
    const floatBuf = new Float32Array(totalSamples)

    for (let i = 0; i < bits.length; i++) {
      const freq = bits[i] ? MARK : SPACE
      for (let j = 0; j < samplesPerBit; j++) {
        const t = (i * samplesPerBit + j) / reducedSampleRate
        floatBuf[i * samplesPerBit + j] = Math.sin(2 * Math.PI * freq * t) * 0.5 // 降低音量
      }
    }

    const pcmBuf = floatTo16BitPCM(floatBuf)

    // 生成WAV文件 - 使用降低的采样率
    const wavBuffer = buildWavOptimized(pcmBuf, reducedSampleRate)
    const base64 = arrayBufferToBase64(wavBuffer)
    const dataUri = `data:audio/wav;base64,${base64}`

    console.log(`${t('deviceConfig.base64Length')}:`, base64.length, t('deviceConfig.about'), Math.round(base64.length / 1024), 'KB')

    // 检查数据大小
    if (base64.length > 1024 * 1024) { // 超过1MB
      throw new Error(t('deviceConfig.audioFileTooLarge'))
    }

    audioFilePath.value = dataUri
    audioGenerated.value = true

    console.log(`${t('deviceConfig.audioGenerationSuccess')}，比特流长度:`, bits.length, `${t('deviceConfig.samplePoints')}:`, floatBuf.length)

    toast.success(t('deviceConfig.soundWaveGenerationSuccess'))

    // 延迟播放
    setTimeout(async () => {
      await playAudio()
    }, 800) // 增加延迟时间
  }
  catch (error) {
    console.error(`${t('deviceConfig.audioGenerationFailed')}:`, error)
    toast.error(`${t('deviceConfig.soundWaveGenerationFailed')}: ${error.message || error}`)
  }
  finally {
    generating.value = false
  }
}

// 优化的WAV构建函数
function buildWavOptimized(pcm: Uint8Array, sampleRate: number): ArrayBuffer {
  const wavHeader = new Uint8Array(44)
  const dataLen = pcm.length
  const fileLen = 36 + dataLen

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      wavHeader[offset + i] = str.charCodeAt(i)
    }
  }

  const write32 = (offset: number, value: number) => {
    wavHeader[offset] = value & 0xFF
    wavHeader[offset + 1] = (value >> 8) & 0xFF
    wavHeader[offset + 2] = (value >> 16) & 0xFF
    wavHeader[offset + 3] = (value >> 24) & 0xFF
  }

  const write16 = (offset: number, value: number) => {
    wavHeader[offset] = value & 0xFF
    wavHeader[offset + 1] = (value >> 8) & 0xFF
  }

  writeStr(0, 'RIFF')
  write32(4, fileLen)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  write32(16, 16)
  write16(20, 1)
  write16(22, 1)
  write32(24, sampleRate) // 使用传入的采样率
  write32(28, sampleRate * 2)
  write16(32, 2)
  write16(34, 16)
  writeStr(36, 'data')
  write32(40, dataLen)

  // 合并header和数据
  const result = new ArrayBuffer(44 + dataLen)
  const resultView = new Uint8Array(result)
  resultView.set(wavHeader)
  resultView.set(pcm, 44)

  return result
}

// 播放音频
async function playAudio() {
  if (!audioFilePath.value) {
    toast.error(t('deviceConfig.pleaseGenerateAudioFirst'))
    return
  }

  try {
    // 强制清理所有旧的音频实例
    await cleanupAudio()

    // 等待一下确保清理完成
    await new Promise(resolve => setTimeout(resolve, 200))

    playing.value = true
    console.log(t('deviceConfig.startPlayingUltrasonicConfigAudio'))

    // 创建新的音频上下文
    const innerAudioContext = uni.createInnerAudioContext()
    audioContext.value = innerAudioContext

    // 最简化的音频设置
    innerAudioContext.src = audioFilePath.value
    innerAudioContext.loop = autoLoop.value
    innerAudioContext.volume = 0.8
    innerAudioContext.autoplay = false

    // 简化的事件监听
    innerAudioContext.onPlay(() => {
      console.log(t('deviceConfig.ultrasonicAudioStartedPlaying'))
      toast.success(t('deviceConfig.startPlayingConfigSoundWave'))
    })

    innerAudioContext.onEnded(() => {
      console.log(t('deviceConfig.ultrasonicAudioPlaybackEnded'))
      if (!autoLoop.value) {
        playing.value = false
        cleanupAudio()
      }
    })

    innerAudioContext.onError((error) => {
      console.error(`${t('deviceConfig.audioPlaybackFailed')}:`, error)
      playing.value = false

      let errorMsg = t('deviceConfig.audioPlaybackFailed')
      if (error.errCode === -99) {
        errorMsg = t('deviceConfig.audioResourceBusy')
      }
      else if (error.errCode === 10004) {
        errorMsg = t('deviceConfig.audioFormatNotSupported')
      }
      else if (error.errCode === 10003) {
        errorMsg = t('deviceConfig.audioFileError')
      }

      toast.error(errorMsg)

      cleanupAudio()
    })

    innerAudioContext.onStop(() => {
      console.log('音频播放停止')
      playing.value = false
    })

    // 延迟播放
    setTimeout(() => {
      if (audioContext.value) {
        console.log('尝试播放音频，src长度:', audioFilePath.value.length)
        audioContext.value.play()
      }
    }, 300)
  }
  catch (error) {
    console.error(`${t('deviceConfig.audioPlaybackError')}:`, error)
    playing.value = false
    await cleanupAudio()
    toast.error(`${t('deviceConfig.playbackFailed')}: ${error.message}`)
  }
}

// 清理音频资源
async function cleanupAudio() {
  if (audioContext.value) {
    try {
      audioContext.value.pause()
      audioContext.value.destroy()
      console.log(t('deviceConfig.cleaningUpAudioContext'))
    }
    catch (e) {
      console.log(`${t('deviceConfig.cleaningUpAudioContextFailed')}:`, e)
    }
    finally {
      audioContext.value = null
    }
  }
}

// 停止播放
async function stopAudio() {
  playing.value = false
  await cleanupAudio()

  console.log(t('deviceConfig.stoppedPlayingUltrasonicAudio'))
  toast.success(t('deviceConfig.stoppedPlaying'))
}
</script>

<template>
  <view class="ultrasonic-config">
    <!-- 选中的网络信息 -->
    <view v-if="props.selectedNetwork" class="selected-network">
      <view class="network-info">
        <view class="network-name">
          {{ t('deviceConfig.selectedNetwork') }}: {{ props.selectedNetwork.ssid }}
        </view>
        <view class="network-details">
          <text class="network-signal">
            {{ t('deviceConfig.signal') }}: {{ props.selectedNetwork.rssi }}dBm
          </text>
          <text class="network-security">
            {{ props.selectedNetwork.authmode === 0 ? t('deviceConfig.openNetwork') : t('deviceConfig.encryptedNetwork') }}
          </text>
        </view>
        <view v-if="props.password" class="network-password">
          {{ t('deviceConfig.password') }}: {{ '*'.repeat(props.password.length) }}
        </view>
      </view>
    </view>

    <!-- 超声波配网操作 -->
    <view class="submit-section">
      <wd-button
        type="primary"
        size="large"
        block
        :loading="generating"
        :disabled="!canGenerate"
        @click="generateAndPlay"
      >
        {{ generating ? t('deviceConfig.generating') : `🎵 ${t('deviceConfig.generateAndPlaySoundWave')}` }}
      </wd-button>

      <wd-button
        v-if="audioGenerated"
        type="success"
        size="large"
        block
        :loading="playing"
        @click="playAudio"
      >
        {{ playing ? t('deviceConfig.playing') : `🔊 ${t('deviceConfig.playSoundWave')}` }}
      </wd-button>

      <wd-button
        v-if="playing"
        type="warning"
        size="large"
        block
        @click="stopAudio"
      >
        ⏹️ {{ t('deviceConfig.stopPlaying') }}
      </wd-button>
    </view>

    <!-- 音频控制选项 -->
    <view v-if="audioGenerated" class="audio-options">
      <view class="option-item">
        <wd-checkbox v-model="autoLoop">
          {{ t('deviceConfig.autoLoopPlaySoundWave') }}
        </wd-checkbox>
      </view>
    </view>

    <!-- 音频播放器 -->
    <view v-if="audioGenerated" class="audio-player">
      <view class="player-info">
        <text class="audio-title">
          {{ t('deviceConfig.configAudioFile') }}
        </text>
        <text class="audio-duration">
          {{ t('deviceConfig.duration') }}: {{ audioLengthText }}
        </text>
      </view>
    </view>

    <!-- 使用说明 -->
    <view class="help-section">
      <view class="help-title">
        {{ t('deviceConfig.ultrasonicConfigInstructions') }}
      </view>
      <view class="help-content">
        <text class="help-item">
          1. {{ t('deviceConfig.ensureWifiNetworkSelectedAndPasswordEntered') }}
        </text>
        <text class="help-item">
          2. {{ t('deviceConfig.clickGenerateAndPlaySoundWave') }}
        </text>
        <text class="help-item">
          3. {{ t('deviceConfig.bringPhoneCloseToXiaozhiDevice') }}
        </text>
        <text class="help-item">
          4. {{ t('deviceConfig.duringAudioPlaybackXiaozhiWillReceive') }}
        </text>
        <text class="help-item">
          5. {{ t('deviceConfig.afterConfigSuccessDeviceWillConnect') }}
        </text>
        <text class="help-tip">
          {{ t('deviceConfig.usesAfskModulation') }}
        </text>
        <text class="help-tip">
          {{ t('deviceConfig.ensureModeratePhoneVolume') }}
        </text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.ultrasonic-config {
  padding: 20rpx 0;
}

.selected-network {
  margin-bottom: 32rpx;
}

.network-info {
  padding: 24rpx;
  background-color: #f0f6ff;
  border: 1rpx solid #336cff;
  border-radius: 16rpx;
}

.network-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #232338;
  margin-bottom: 8rpx;
}

.network-details {
  display: flex;
  gap: 24rpx;
  margin-bottom: 8rpx;
}

.network-signal,
.network-security {
  font-size: 24rpx;
  color: #65686f;
}

.network-password {
  font-size: 24rpx;
  color: #65686f;
}

.submit-section {
  margin-bottom: 32rpx;
}

.submit-section .wd-button {
  margin-bottom: 16rpx;
}

.submit-section .wd-button:last-child {
  margin-bottom: 0;
}

.audio-options {
  margin-bottom: 32rpx;
  padding: 24rpx;
  background-color: #fbfbfb;
  border-radius: 16rpx;
  border: 1rpx solid #eeeeee;
}

.option-item {
  font-size: 28rpx;
}

.audio-player {
  margin-bottom: 32rpx;
  padding: 24rpx;
  background-color: #f0f6ff;
  border: 1rpx solid #336cff;
  border-radius: 16rpx;
}

.player-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.audio-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #232338;
}

.audio-duration {
  font-size: 24rpx;
  color: #65686f;
}

.help-section {
  padding: 32rpx 24rpx;
  background-color: #fbfbfb;
  border-radius: 16rpx;
  border: 1rpx solid #eeeeee;
}

.help-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #232338;
  margin-bottom: 20rpx;
}

.help-content {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.help-item {
  font-size: 24rpx;
  color: #65686f;
  line-height: 1.5;
}

.help-tip {
  font-size: 24rpx;
  color: #336cff;
  font-weight: 500;
  margin-top: 8rpx;
}
</style>
