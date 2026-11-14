/**
 * 为 sm-crypto >= 0.5.0 提供 crypto.getRandomValues 兼容层
 * （0.5.0 起强制要求 CSPRNG，不支持时模块加载即抛异常，见 CVE-2026-73567）。
 *
 * 策略：
 * 1. 经平台异步 CSPRNG API 分块并行取真随机字节，填入同步缓冲池。
 *    探测顺序 wx → uni → my → tt → swan → ks → qq → jd → lark → xhs；
 *    App 端逻辑层无 CSPRNG，
 *    由 secure-random-bridge 组件经 renderjs 回传（registerRandomBridge 兜底）。
 * 2. 垫片同步从缓冲池取字节，池不足即抛错，不回退弱随机（fail-closed）。
 * 3. sm-crypto 熵池初始化已通过 pnpm patch 推迟到首次取随机
 *    （patches/sm-crypto@0.5.8.patch），首次 sm2 调用前 await
 *    ensureSecureRandomReady() 即可。
 *
 * 无任何 CSPRNG 的平台（如支付宝/百度小程序）会 reject，属预期行为。
 */
const CHUNK_SIZE = 64
const CHUNK_COUNT = 8
const LOW_WATER_MARK = 128

// 标记垫片自身，探测时与原生实现区分，避免失败重试被短路成假成功
const SHIM_MARKER = Symbol('secureRandomShim')

// App 端桥接通道，由 secure-random-bridge 组件挂载时注册
let bridgeProvider: ((length: number) => Promise<Uint8Array>) | null = null

export function registerRandomBridge(provider: (length: number) => Promise<Uint8Array>) {
  bridgeProvider = provider
}

let pool: number[] = []
let readyPromise: Promise<void> | null = null
let refillInFlight = false

function getGlobalObj(): Record<string, any> | null {
  // sm-crypto 读取的是 globalThis.crypto，垫片必须装在同一对象上
  if (typeof globalThis !== 'undefined')
    return globalThis as unknown as Record<string, any>
  return null
}

function hasNativeGetRandomValues(): boolean {
  try {
    // 探测 globalThis.crypto：Node、h5:ssr 等环境有原生 CSPRNG 但无 window
    const fn = getGlobalObj()?.crypto?.getRandomValues
    // 排除垫片自身，否则失败重试会被短路成假成功
    return typeof fn === 'function' && !(fn as any)[SHIM_MARKER]
  }
  catch {
    return false
  }
}

/**
 * 按优先级探测提供异步 CSPRNG 的平台全局对象。
 * uni.getRandomValues 仅有声明无实现，故排在 wx 之后兜底；
 * 其余平台对象未在 TS 类型中声明，经 globalThis 探测，
 * 对应平台未来实现同名 API 时自动生效。
 */
function findRandomApi(): { name: string, api: any } | null {
  const globalObj = getGlobalObj()
  const candidates: Array<[string, any]> = [
    ['wx', typeof wx !== 'undefined' ? wx : null],
    ['uni', typeof uni !== 'undefined' ? uni : null],
    ['my', globalObj ? globalObj.my : null],
    ['tt', globalObj ? globalObj.tt : null],
    ['swan', globalObj ? globalObj.swan : null],
    ['ks', globalObj ? globalObj.ks : null],
    ['qq', globalObj ? globalObj.qq : null],
    ['jd', globalObj ? globalObj.jd : null],
    ['lark', globalObj ? globalObj.lark : null],
    ['xhs', globalObj ? globalObj.xhs : null],
  ]
  for (const [name, api] of candidates) {
    if (api && typeof api.getRandomValues === 'function')
      return { name, api }
  }
  return null
}

function fetchRandomChunk(length: number): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    const found = findRandomApi()
    if (!found && !bridgeProvider) {
      reject(new Error(
        '当前平台不支持获取密码学安全随机数（getRandomValues），无法安全执行 SM2 加密。'
        + '当前已适配：微信小程序（wx.getRandomValues）、浏览器、Node 环境、'
        + 'App 端（renderjs 桥接，需页面挂载 secure-random-bridge 组件）；'
        + '其余小程序平台因缺少 CSPRNG API 被按 fail-closed 原则拒绝，'
        + '如需支持请扩展 secure-random.ts 的 findRandomApi 适配链。',
      ))
      return
    }
    if (found) {
      found.api.getRandomValues({
        length,
        success: (res: { randomValues: ArrayBuffer | Uint8Array | number[] }) => {
          resolve(new Uint8Array(res.randomValues))
        },
        fail: (err: unknown) => {
          reject(err instanceof Error ? err : new Error(`getRandomValues 调用失败: ${JSON.stringify(err)}`))
        },
      })
      return
    }
    bridgeProvider!(length).then(resolve, (err: unknown) => {
      reject(err instanceof Error ? err : new Error(`renderjs 桥接取随机失败: ${String(err)}`))
    })
  })
}

async function refillPool(totalLength: number): Promise<void> {
  const chunks = await Promise.all(
    Array.from({ length: Math.ceil(totalLength / CHUNK_SIZE) }, () => fetchRandomChunk(CHUNK_SIZE)),
  )
  for (const chunk of chunks) {
    for (let i = 0; i < chunk.length; i++)
      pool.push(chunk[i])
  }
}

function scheduleRefill() {
  if (refillInFlight)
    return
  refillInFlight = true
  refillPool(256)
    .catch((err) => {
      // 补充失败仅告警：池仍够用则无感，耗尽时由 getRandomValues 抛错兜底
      console.warn('[secure-random] 补充随机数缓冲池失败', err)
    })
    .finally(() => {
      refillInFlight = false
    })
}

function createGetRandomValues<T extends ArrayBufferView>(array: T): T {
  // 按字节拷贝，兼容 Uint16Array/Uint32Array 等视图
  const view = array as unknown as ArrayBufferView
  const bytes = new Uint8Array(view.buffer, view.byteOffset, view.byteLength)
  if (pool.length < bytes.length) {
    scheduleRefill()
    throw new Error('安全随机数缓冲池未就绪或已耗尽，请先等待 ensureSecureRandomReady() 完成')
  }
  for (let i = 0; i < bytes.length; i++)
    bytes[i] = pool[i]
  pool = pool.slice(bytes.length)
  if (pool.length < LOW_WATER_MARK)
    scheduleRefill()
  return array
}

;(createGetRandomValues as any)[SHIM_MARKER] = true

function installShim() {
  const globalObj = getGlobalObj()
  if (!globalObj)
    throw new Error('无法获取全局对象，无法安装 crypto.getRandomValues 垫片')

  if (globalObj.crypto && typeof globalObj.crypto.getRandomValues === 'function')
    return

  if (globalObj.crypto) {
    // 只补缺的方法，保留宿主 crypto 其他成员；defineProperty 规避只读访问器赋值失败
    Object.defineProperty(globalObj.crypto, 'getRandomValues', {
      value: createGetRandomValues,
      configurable: true,
      writable: true,
    })
  }
  else {
    globalObj.crypto = { getRandomValues: createGetRandomValues }
  }
}

/**
 * 确保密码学安全随机源可用（首次 sm2 调用前必须 await）。
 * 原生支持的环境直接就绪；缺失环境安装垫片并预热缓冲池；
 * 无 CSPRNG 的环境 reject，由调用方 fail-closed 处理。
 */
export function ensureSecureRandomReady(): Promise<void> {
  if (hasNativeGetRandomValues())
    return Promise.resolve()
  if (!readyPromise) {
    readyPromise = (async () => {
      installShim()
      await refillPool(CHUNK_SIZE * CHUNK_COUNT)
    })().catch((err) => {
      // 失败后重置，允许后续重试
      readyPromise = null
      throw err
    })
  }
  return readyPromise
}
