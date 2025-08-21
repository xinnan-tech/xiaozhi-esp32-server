// 枚举定义

export enum TestEnum {
  A = '1',
  B = '2',
}

// uni.uploadFile文件上传参数
export interface IUniUploadFileOptions {
  file?: File
  files?: UniApp.UploadFileOptionFiles[]
  filePath?: string
  name?: string
  formData?: any
}
