import { ref } from 'vue'
import { getEnvBaseUploadUrl } from '@/utils'

const VITE_UPLOAD_BASEURL = `${getEnvBaseUploadUrl()}`

type TfileType = 'image' | 'file'
type TImage = 'png' | 'jpg' | 'jpeg' | 'webp' | '*'
type TFile = 'doc' | 'docx' | 'ppt' | 'zip' | 'xls' | 'xlsx' | 'txt' | TImage

interface TOptions<T extends TfileType> {
  formData?: Record<string, any>
  maxSize?: number
  accept?: T extends 'image' ? TImage[] : TFile[]
  fileType?: T
  success?: (params: any) => void
  error?: (err: any) => void
}

export default function useUpload<T extends TfileType>(options: TOptions<T> = {} as TOptions<T>) {
  const {
    formData = {},
    maxSize = 5 * 1024 * 1024,
    accept = ['*'],
    fileType = 'image',
    success,
    error: onError,
  } = options

  const loading = ref(false)
  const error = ref<Error | null>(null)
  const data = ref<any>(null)

  const handleFileChoose = ({ tempFilePath, size }: { tempFilePath: string, size: number }) => {
    if (size > maxSize) {
      uni.showToast({
        title: `文件大小不能超过 ${maxSize / 1024 / 1024}MB`,
        icon: 'none',
      })
      return
    }

    // const fileExtension = file?.tempFiles?.name?.split('.').pop()?.toLowerCase()
    // const isTypeValid = accept.some((type) => type === '*' || type.toLowerCase() === fileExtension)

    // if (!isTypeValid) {
    //   uni.showToast({
    //     title: `仅支持 ${accept.join(', ')} 格式的文件`,
    //     icon: 'none',
    //   })
    //   return
    // }

    loading.value = true
    uploadFile({
      tempFilePath,
      formData,
      onSuccess: (res) => {
        const { data: _data } = JSON.parse(res)
        data.value = _data
        // console.log('上传成功', res)
        success?.(_data)
      },
      onError: (err) => {
        error.value = err
        onError?.(err)
      },
      onComplete: () => {
        loading.value = false
      },
    })
  }

  const run = () => {
    // 微信小程序从基础库 2.21.0 开始， wx.chooseImage 停止维护，请使用 uni.chooseMedia 代替。
    // 微信小程序在2023年10月17日之后，使用本API需要配置隐私协议
    const chooseFileOptions = {
      count: 1,
      success: (res: any) => {
        console.log('File selected successfully:', res)
        // 小程序中res:{errMsg: "chooseImage:ok", tempFiles: [{fileType: "image", size: 48976, tempFilePath: "http://tmp/5iG1WpIxTaJf3ece38692a337dc06df7eb69ecb49c6b.jpeg"}]}
        // h5中res:{errMsg: "chooseImage:ok", tempFilePaths: "blob:http://localhost:9000/f74ab6b8-a14d-4cb6-a10d-fcf4511a0de5", tempFiles: [File]}
        // h5的File有以下字段：{name: "girl.jpeg", size: 48976, type: "image/jpeg"}
        // App中res:{errMsg: "chooseImage:ok", tempFilePaths: "file:///Users/feige/xxx/gallery/1522437259-compressed-IMG_0006.jpg", tempFiles: [File]}
        // App的File有以下字段：{path: "file:///Users/feige/xxx/gallery/1522437259-compressed-IMG_0006.jpg", size: 48976}
        let tempFilePath = ''
        let size = 0
        // #ifdef MP-WEIXIN
        tempFilePath = res.tempFiles[0].tempFilePath
        size = res.tempFiles[0].size
        // #endif
        // #ifndef MP-WEIXIN
        tempFilePath = res.tempFilePaths[0]
        size = res.tempFiles[0].size
        // #endif
        handleFileChoose({ tempFilePath, size })
      },
      fail: (err: any) => {
        console.error('File selection failed:', err)
        error.value = err
        onError?.(err)
      },
    }

    if (fileType === 'image') {
      // #ifdef MP-WEIXIN
      uni.chooseMedia({
        ...chooseFileOptions,
        mediaType: ['image'],
      })
      // #endif

      // #ifndef MP-WEIXIN
      uni.chooseImage(chooseFileOptions)
      // #endif
    }
    else {
      uni.chooseFile({
        ...chooseFileOptions,
        type: 'all',
      })
    }
  }

  return { loading, error, data, run }
}

async function uploadFile({
  tempFilePath,
  formData,
  onSuccess,
  onError,
  onComplete,
}: {
  tempFilePath: string
  formData: Record<string, any>
  onSuccess: (data: any) => void
  onError: (err: any) => void
  onComplete: () => void
}) {
  uni.uploadFile({
    url: VITE_UPLOAD_BASEURL,
    filePath: tempFilePath,
    name: 'file',
    formData,
    success: (uploadFileRes) => {
      try {
        const data = uploadFileRes.data
        onSuccess(data)
      }
      catch (err) {
        onError(err)
      }
    },
    fail: (err) => {
      console.error('Upload failed:', err)
      onError(err)
    },
    complete: onComplete,
  })
}
