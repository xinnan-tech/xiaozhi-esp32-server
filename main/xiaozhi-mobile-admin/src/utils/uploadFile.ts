import { toast } from './toast'

/**
 * 文件上传钩子函数使用示例
 * @example
 * const { loading, error, data, progress, run } = useUpload<IUploadResult>(
 *   uploadUrl,
 *   {},
 *   {
 *     maxSize: 5, // 最大5MB
 *     sourceType: ['album'], // 仅支持从相册选择
 *     onProgress: (p) => console.log(`上传进度：${p}%`),
 *     onSuccess: (res) => console.log('上传成功', res),
 *     onError: (err) => console.error('上传失败', err),
 *   },
 * )
 */

/**
 * 上传文件的URL配置
 */
export const uploadFileUrl = {
  /** 用户头像上传地址 */
  USER_AVATAR: `${import.meta.env.VITE_SERVER_BASEURL}/user/avatar`,
}

/**
 * 通用文件上传函数（支持直接传入文件路径）
 * @param url 上传地址
 * @param filePath 本地文件路径
 * @param formData 额外表单数据
 * @param options 上传选项
 */
export function useFileUpload<T = string>(url: string, filePath: string, formData: Record<string, any> = {}, options: Omit<UploadOptions, 'sourceType' | 'sizeType' | 'count'> = {}) {
  return useUpload<T>(
    url,
    formData,
    {
      ...options,
      sourceType: ['album'],
      sizeType: ['original'],
    },
    filePath,
  )
}

export interface UploadOptions {
  /** 最大可选择的图片数量，默认为1 */
  count?: number
  /** 所选的图片的尺寸，original-原图，compressed-压缩图 */
  sizeType?: Array<'original' | 'compressed'>
  /** 选择图片的来源，album-相册，camera-相机 */
  sourceType?: Array<'album' | 'camera'>
  /** 文件大小限制，单位：MB */
  maxSize?: number //
  /** 上传进度回调函数 */
  onProgress?: (progress: number) => void
  /** 上传成功回调函数 */
  onSuccess?: (res: Record<string, any>) => void
  /** 上传失败回调函数 */
  onError?: (err: Error | UniApp.GeneralCallbackResult) => void
  /** 上传完成回调函数（无论成功失败） */
  onComplete?: () => void
}

/**
 * 文件上传钩子函数
 * @template T 上传成功后返回的数据类型
 * @param url 上传地址
 * @param formData 额外的表单数据
 * @param options 上传选项
 * @returns 上传状态和控制对象
 */
export function useUpload<T = string>(url: string, formData: Record<string, any> = {}, options: UploadOptions = {},
  /** 直接传入文件路径，跳过选择器 */
  directFilePath?: string) {
  /** 上传中状态 */
  const loading = ref(false)
  /** 上传错误状态 */
  const error = ref(false)
  /** 上传成功后的响应数据 */
  const data = ref<T>()
  /** 上传进度（0-100） */
  const progress = ref(0)

  /** 解构上传选项，设置默认值 */
  const {
    /** 最大可选择的图片数量 */
    count = 1,
    /** 所选的图片的尺寸 */
    sizeType = ['original', 'compressed'],
    /** 选择图片的来源 */
    sourceType = ['album', 'camera'],
    /** 文件大小限制（MB） */
    maxSize = 10,
    /** 进度回调 */
    onProgress,
    /** 成功回调 */
    onSuccess,
    /** 失败回调 */
    onError,
    /** 完成回调 */
    onComplete,
  } = options

  /**
   * 检查文件大小是否超过限制
   * @param size 文件大小（字节）
   * @returns 是否通过检查
   */
  const checkFileSize = (size: number) => {
    const sizeInMB = size / 1024 / 1024
    if (sizeInMB > maxSize) {
      toast.warning(`文件大小不能超过${maxSize}MB`)
      return false
    }
    return true
  }
  /**
   * 触发文件选择和上传
   * 根据平台使用不同的选择器：
   * - 微信小程序使用 chooseMedia
   * - 其他平台使用 chooseImage
   */
  const run = () => {
    if (directFilePath) {
      // 直接使用传入的文件路径
      loading.value = true
      progress.value = 0
      uploadFile<T>({
        url,
        tempFilePath: directFilePath,
        formData,
        data,
        error,
        loading,
        progress,
        onProgress,
        onSuccess,
        onError,
        onComplete,
      })
      return
    }

    // #ifdef MP-WEIXIN
    // 微信小程序环境下使用 chooseMedia API
    uni.chooseMedia({
      count,
      mediaType: ['image'], // 仅支持图片类型
      sourceType,
      success: (res) => {
        const file = res.tempFiles[0]
        // 检查文件大小是否符合限制
        if (!checkFileSize(file.size))
          return

        // 开始上传
        loading.value = true
        progress.value = 0
        uploadFile<T>({
          url,
          tempFilePath: file.tempFilePath,
          formData,
          data,
          error,
          loading,
          progress,
          onProgress,
          onSuccess,
          onError,
          onComplete,
        })
      },
      fail: (err) => {
        console.error('选择媒体文件失败:', err)
        error.value = true
        onError?.(err)
      },
    })
    // #endif

    // #ifndef MP-WEIXIN
    // 非微信小程序环境下使用 chooseImage API
    uni.chooseImage({
      count,
      sizeType,
      sourceType,
      success: (res) => {
        console.log('选择图片成功:', res)

        // 开始上传
        loading.value = true
        progress.value = 0
        uploadFile<T>({
          url,
          tempFilePath: res.tempFilePaths[0],
          formData,
          data,
          error,
          loading,
          progress,
          onProgress,
          onSuccess,
          onError,
          onComplete,
        })
      },
      fail: (err) => {
        console.error('选择图片失败:', err)
        error.value = true
        onError?.(err)
      },
    })
    // #endif
  }

  return { loading, error, data, progress, run }
}

/**
 * 文件上传选项接口
 * @template T 上传成功后返回的数据类型
 */
interface UploadFileOptions<T> {
  /** 上传地址 */
  url: string
  /** 临时文件路径 */
  tempFilePath: string
  /** 额外的表单数据 */
  formData: Record<string, any>
  /** 上传成功后的响应数据 */
  data: Ref<T | undefined>
  /** 上传错误状态 */
  error: Ref<boolean>
  /** 上传中状态 */
  loading: Ref<boolean>
  /** 上传进度（0-100） */
  progress: Ref<number>
  /** 上传进度回调 */
  onProgress?: (progress: number) => void
  /** 上传成功回调 */
  onSuccess?: (res: Record<string, any>) => void
  /** 上传失败回调 */
  onError?: (err: Error | UniApp.GeneralCallbackResult) => void
  /** 上传完成回调 */
  onComplete?: () => void
}

/**
 * 执行文件上传
 * @template T 上传成功后返回的数据类型
 * @param options 上传选项
 */
function uploadFile<T>({
  url,
  tempFilePath,
  formData,
  data,
  error,
  loading,
  progress,
  onProgress,
  onSuccess,
  onError,
  onComplete,
}: UploadFileOptions<T>) {
  try {
    // 创建上传任务
    const uploadTask = uni.uploadFile({
      url,
      filePath: tempFilePath,
      name: 'file', // 文件对应的 key
      formData,
      header: {
        // H5环境下不需要手动设置Content-Type，让浏览器自动处理multipart格式
        // #ifndef H5
        'Content-Type': 'multipart/form-data',
        // #endif
      },
      // 确保文件名称合法
      success: (uploadFileRes) => {
        console.log('上传文件成功:', uploadFileRes)
        try {
          // 解析响应数据
          const { data: _data } = JSON.parse(uploadFileRes.data)
          // 上传成功
          data.value = _data as T
          onSuccess?.(_data)
        }
        catch (err) {
          // 响应解析错误
          console.error('解析上传响应失败:', err)
          error.value = true
          onError?.(new Error('上传响应解析失败'))
        }
      },
      fail: (err) => {
        // 上传请求失败
        console.error('上传文件失败:', err)
        error.value = true
        onError?.(err)
      },
      complete: () => {
        // 无论成功失败都执行
        loading.value = false
        onComplete?.()
      },
    })

    // 监听上传进度
    uploadTask.onProgressUpdate((res) => {
      progress.value = res.progress
      onProgress?.(res.progress)
    })
  }
  catch (err) {
    // 创建上传任务失败
    console.error('创建上传任务失败:', err)
    error.value = true
    loading.value = false
    onError?.(new Error('创建上传任务失败'))
  }
}
