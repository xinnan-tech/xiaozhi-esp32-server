/**
 * 为缺少 Web Crypto API 的运行环境（主要是微信小程序）提供
 * crypto.getRandomValues 兼容层，供 sm-crypto >= 0.5.0 使用。
 *
 * 背景（CVE-2026-73567 / GHSA-vh45-f885-3848）：sm-crypto 0.5.0 起强制要求
 * 密码学安全随机源 crypto.getRandomValues（仅在模块加载时取一次 32 字节熵，
 * 之后不再重新播种），环境不支持时加载即抛异常，不会回退到不安全实现。
 *
 * 小程序运行环境没有 window.crypto / globalThis.crypto，也没有同步的
 * CSPRNG API，因此本垫片的策略是：
 * 1. 启动阶段通过平台提供的异步 CSPRNG API 获取真随机字节（64 字节分块、并行
 *    请求，规避单次长度上限），填入同步缓冲池。已知实现：微信 wx.getRandomValues；
 *    uni.getRandomValues 在 uni-app 运行时中仅有类型声明、无实现，故同时按
 *    wx → uni → my → tt → swan → ks 顺序探测各平台全局对象，后续其他小程序
 *    平台若提供同名 API 可被自动覆盖；
 * 2. 垫片的 getRandomValues 同步从缓冲池取字节，池不足时抛出异常
 *    （fail-closed，绝不回退到 Math.random 等可预测源）；
 * 3. sm-crypto 的熵池初始化已通过 pnpm patch（patches/sm-crypto@0.5.8.patch）
 *    推迟到首次取随机字节时，调用方只需在首次调用 sm2 前 await
 *    ensureSecureRandomReady()，即可保证其取到真随机熵。
 *
 * 注意：若某平台既无 window.crypto 又无任何 CSPRNG API（如支付宝/百度等
 * 小程序当前普遍如此），ensureSecureRandomReady 会 reject，登录等加密流程
 * 将明确报错而非静默使用弱随机——这是 fail-closed 的预期行为。
 */

const CHUNK_SIZE = 64
const CHUNK_COUNT = 8
const LOW_WATER_MARK = 128

let pool: number[] = []
let readyPromise: Promise<void> | null = null
let refillInFlight = false

function getGlobalObj(): Record<string, any> | null {
  // globalThis 在所有目标环境（现代浏览器 / 微信小程序 / Node）均存在；
  // sm-crypto 读取的也是 globalThis.crypto，垫片必须装在同一个对象上
  if (typeof globalThis !== 'undefined')
    return globalThis as unknown as Record<string, any>
  return null
}

function hasNativeGetRandomValues(): boolean {
  try {
    return typeof window !== 'undefined'
      && !!window.crypto
      && typeof window.crypto.getRandomValues === 'function'
  }
  catch {
    return false
  }
}

/**
 * 按优先级探测当前平台提供异步 CSPRNG 的全局对象。
 * uni.getRandomValues 在 uni-app 运行时中无实现，仅为声明，因此 uni 放在
 * wx 之后仅作兜底；my/tt/swan/ks 等平台对象通过 globalThis 探测（未在
 * TS 类型中声明），若对应平台未来提供 getRandomValues 可自动适配。
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
    if (!found) {
      reject(new Error(
        '当前平台不支持获取密码学安全随机数（getRandomValues），无法安全执行 SM2 加密。'
        + '当前已适配：微信小程序（wx.getRandomValues）、浏览器、Node 环境；'
        + '其余小程序/App 平台因缺少 CSPRNG API 被按 fail-closed 原则拒绝，'
        + '如需支持请扩展 secure-random.ts 的 findRandomApi 适配链。',
      ))
      return
    }
    found.api.getRandomValues({
      length,
      success: (res: { randomValues: ArrayBuffer | Uint8Array | number[] }) => {
        resolve(new Uint8Array(res.randomValues))
      },
      fail: (err: unknown) => {
        reject(err instanceof Error ? err : new Error(`getRandomValues 调用失败: ${JSON.stringify(err)}`))
      },
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
    .catch(() => {
      // 尽力而为的补充；缓冲池仍够用时静默失败，不足时由 getRandomValues 抛错兜底
    })
    .finally(() => {
      refillInFlight = false
    })
}

function installShim() {
  const globalObj = getGlobalObj()
  if (!globalObj)
    throw new Error('无法获取全局对象，无法安装 crypto.getRandomValues 垫片')

  const existing = globalObj.crypto
  if (existing && typeof existing.getRandomValues === 'function')
    return

  globalObj.crypto = {
    getRandomValues<T extends ArrayBufferView>(array: T): T {
      const bytes = array as unknown as Uint8Array
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
    },
  }
}

/**
 * 确保密码学安全随机源可用（sm-crypto 加载前必须 await 本方法）。
 * - 浏览器 / App WebView 等原生支持 window.crypto 的环境：直接就绪；
 * - 小程序等缺失环境：安装垫片并从系统 CSPRNG 预热缓冲池。
 * 不支持获取随机数的环境会 reject，由调用方 fail-closed 处理。
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
