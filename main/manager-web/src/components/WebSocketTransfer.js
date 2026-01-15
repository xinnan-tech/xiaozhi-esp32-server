class WebSocketTransfer {
  constructor(token) {
    this.token = token
    this.ws = null
    this.isConnected = false
    this.isCancelled = false
    this.chunkSize = 64 * 1024 // 64KB per chunk
    this.onProgress = null
    this.onError = null
    this.onComplete = null
    this.onDownloadUrlReady = null
    this.onTransferStarted = null // 新增：transfer_started事件回调
    this.currentSession = null
    this.totalBytesSent = 0 // 新增：总发送字节数跟踪
    this.isSendingChunk = false // 新增：标记是否正在发送数据块
  }

  // 连接到transfer服务器
  async connect() {
    return new Promise((resolve, reject) => {
      try {
        // 使用固定的transfer服务器地址
        const wsUrl = `wss://api.tenclass.net/transfer/?token=${encodeURIComponent(this.token)}`
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          this.isConnected = true
          console.log('WebSocket connected to transfer server')
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event)
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnected = false
          reject(new Error('WebSocket connection failed'))
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason)
          this.isConnected = false
        }

        // 设置连接超时
        setTimeout(() => {
          if (!this.isConnected) {
            this.ws.close()
            reject(new Error('WebSocket connection timeout'))
          }
        }, 10000)

      } catch (error) {
        reject(new Error(`Failed to create WebSocket connection: ${error.message}`))
      }
    })
  }

  // 处理WebSocket消息
  handleMessage(event) {
    try {
      if (typeof event.data === 'string') {
        const message = JSON.parse(event.data)

        switch (message.type) {
          case 'file_created':
            if (this.currentSession) {
              this.currentSession.url = message.url
              // 通知下载URL已准备就绪
              if (this.onDownloadUrlReady) {
                this.onDownloadUrlReady(message.url)
              }
              // 等待transfer_started消息后再开始发送数据
            }
            break

          case 'transfer_started':
            if (this.currentSession) {
              // 标记已收到transfer_started消息
              this.currentSession.transferStarted = true

              // 通知外部监听器
              if (this.onTransferStarted) {
                this.onTransferStarted()
              }

              // 如果传输已准备好，开始发送文件数据
              if (this.currentSession.transferReady) {
                this.sendFileData()
              }
            }
            break

          case 'ack':
            // 收到确认，验证并更新bytesSent
            if (this.currentSession) {
              const { blob } = this.currentSession
              const totalSize = blob.size
              const serverBytesSent = message.bytesSent

              // 验证服务器报告的bytesSent
              if (serverBytesSent < 0) {
                console.error('Invalid server bytesSent (negative):', serverBytesSent)
                this.isSendingChunk = false // 重置发送标志
                if (this.onError) {
                  this.onError(new Error('Server returned invalid byte count'))
                }
                return
              }

              if (serverBytesSent > totalSize) {
                console.error(`Server bytesSent (${serverBytesSent}) exceeds fileSize (${totalSize})`)
                this.isSendingChunk = false // 重置发送标志
                if (this.onError) {
                  this.onError(new Error('Server byte count exceeds file size'))
                }
                return
              }

              // 标记当前数据块已发送完成
              this.isSendingChunk = false

              // 使用服务器确认的bytesSent
              if (serverBytesSent > this.currentSession.bytesSent) {
                this.currentSession.bytesSent = serverBytesSent
              }

              // 发送下一块数据
              this.sendFileData()
            }
            break

          case 'transfer_completed':
            // 验证传输完整性
            if (this.currentSession) {
              const expectedSize = this.currentSession.blob.size
              if (this.totalBytesSent !== expectedSize) {
                console.warn(`Transfer size mismatch: sent ${this.totalBytesSent} bytes, expected ${expectedSize} bytes`)
              }
            }

            if (this.onComplete) {
              this.onComplete()
            }
            break

          case 'error':
            console.error('Transfer error:', message.message)
            if (this.onError) {
              this.onError(new Error(message.message))
            }
            break
        }
      }
    } catch (error) {
      console.error('Error handling message:', error)
      if (this.onError) {
        this.onError(error)
      }
    }
  }

  // 发送文件数据
  async sendFileData() {
    // 防止并发发送
    if (this.isSendingChunk) {
      return
    }

    if (!this.currentSession || this.isCancelled) {
      return
    }

    const { blob } = this.currentSession
    const totalSize = blob.size
    let bytesSent = this.currentSession.bytesSent

    // 严格检查：确保不会发送超出文件大小的数据
    if (bytesSent >= totalSize) {
      if (this.onProgress) {
        this.onProgress(100, 'Transfer completed, waiting for device confirmation...')
      }
      return
    }

    this.isSendingChunk = true

    // 再次验证bytesSent不超过文件大小
    if (bytesSent > totalSize) {
      console.error(`Critical error: bytesSent (${bytesSent}) exceeds fileSize (${totalSize})`)
      if (this.onError) {
        this.onError(new Error('Transfer byte count exceeds file size'))
      }
      return
    }

    // 计算下一块的大小，确保不会超出文件边界
    const remainingBytes = Math.max(0, totalSize - bytesSent)
    const chunkSize = Math.min(this.chunkSize, remainingBytes)

    if (chunkSize <= 0) {
      return
    }

    const chunk = blob.slice(bytesSent, bytesSent + chunkSize)

    try {
      // 读取文件块
      const arrayBuffer = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result)
        reader.onerror = () => reject(new Error('File read failed'))
        reader.readAsArrayBuffer(chunk)
      })

      if (this.isCancelled) {
        return
      }

      // 发送二进制数据
      this.ws.send(arrayBuffer)

      // 更新本地bytesSent计数（乐观更新）
      const newBytesSent = bytesSent + chunkSize
      this.currentSession.bytesSent = newBytesSent
      this.totalBytesSent += chunkSize // 更新总发送字节数

      // 验证更新后的bytesSent不超过文件大小
      if (newBytesSent > totalSize) {
        console.error(`Critical error: bytesSent (${newBytesSent}) exceeds fileSize (${totalSize})`)
        if (this.onError) {
          this.onError(new Error('Transfer byte count exceeds file size'))
        }
        return
      }

      // 额外验证：总发送字节数也不应该超过文件大小
      if (this.totalBytesSent > totalSize) {
        console.error(`Critical error: totalBytesSent (${this.totalBytesSent}) exceeds fileSize (${totalSize})`)
        if (this.onError) {
          this.onError(new Error('Total sent bytes exceed file size'))
        }
        return
      }

      // 更新进度（只更新传输进度部分）
      const transferProgress = Math.round(newBytesSent / totalSize * 60) + 40 // 40-100范围
      const step = `Transferring... ${Math.round(newBytesSent / 1024)}KB / ${Math.round(totalSize / 1024)}KB`

      if (this.onProgress) {
        this.onProgress(transferProgress, step)
      }

    } catch (error) {
      console.error('Error sending file chunk:', error)
      this.isSendingChunk = false // 重置发送标志
      if (this.onError) {
        this.onError(error)
      }
    }
  }

  // 初始化传输会话（只建立连接和获取URL）
  async initializeSession(blob, onProgress, onError, onDownloadUrlReady) {
    return new Promise((resolve, reject) => {
      this.onProgress = onProgress
      this.onError = (error) => {
        if (onError) onError(error)
        reject(error)
      }
      this.onDownloadUrlReady = (url) => {
        if (onDownloadUrlReady) onDownloadUrlReady(url)
        resolve(url)
      }
      this.isCancelled = false

      try {
        // 连接到WebSocket服务器
        if (this.onProgress) {
          this.onProgress(5, 'Connecting to transfer server...')
        }

        this.connect().then(() => {
          // 发送文件创建请求
          if (this.onProgress) {
            this.onProgress(10, 'Creating file session...')
          }

          const createMessage = {
            type: 'create_file',
            fileName: 'assets.bin',
            fileSize: blob.size
          }

          this.ws.send(JSON.stringify(createMessage))

          // 保存blob引用，等待file_created消息
          this.currentSession = {
            blob: blob,
            bytesSent: 0,
            fileSize: blob.size,
            transferStarted: false,
            transferReady: true // 初始化时就设置为true，因为initializeSession后就可以开始传输
          }
          // 重置总发送字节数
          this.totalBytesSent = 0
        }).catch(error => {
          console.error('Transfer initialization failed:', error)
          if (this.onError) {
            this.onError(error)
          }
        })

      } catch (error) {
        console.error('Transfer initialization failed:', error)
        if (this.onError) {
          this.onError(error)
        }
      }
    })
  }

  // 开始传输文件数据（假设会话已初始化）
  async startTransfer(onProgress, onError, onComplete) {
    return new Promise((resolve, reject) => {
      this.onProgress = onProgress
      this.onError = (error) => {
        this.isSendingChunk = false // 重置发送标志
        if (onError) onError(error)
        reject(error)
      }
      this.onComplete = () => {
        this.isSendingChunk = false // 重置发送标志
        if (onComplete) onComplete()
        resolve()
      }

      if (!this.currentSession || !this.currentSession.blob) {
        const error = new Error('Transfer session not initialized')
        if (this.onError) this.onError(error)
        reject(error)
        return
      }

      // 设置传输状态，等待transfer_started消息
      this.currentSession.transferReady = true

      // 如果已经收到了transfer_started消息，开始传输
      if (this.currentSession.transferStarted) {
        this.sendFileData()
      } else {
      }
      // 否则等待transfer_started消息
    })
  }

  // 开始传输文件
  async transferFile(blob, onProgress, onError, onComplete, onDownloadUrlReady) {
    // 如果提供了onDownloadUrlReady回调，使用分阶段传输
    if (onDownloadUrlReady) {
      await this.initializeSession(blob, onProgress, onError, onDownloadUrlReady)
      // 返回，让调用者决定何时开始传输
      return
    }

    // 否则，使用传统的一次性传输
    this.onProgress = onProgress
    this.onError = onError
    this.onComplete = onComplete
    this.isCancelled = false

    try {
      // 连接到WebSocket服务器
      if (this.onProgress) {
        this.onProgress(5, 'Connecting to transfer server...')
      }

      await this.connect()

      // 发送文件创建请求
      if (this.onProgress) {
        this.onProgress(10, 'Creating file session...')
      }

      const createMessage = {
        type: 'create_file',
        fileName: 'assets.bin',
        fileSize: blob.size
      }

      this.ws.send(JSON.stringify(createMessage))

      // 保存blob引用，等待file_created消息
      this.currentSession = {
        blob: blob,
        bytesSent: 0,
        fileSize: blob.size,
        transferStarted: false,
        transferReady: true // 传统模式下直接设置为true
      }

    } catch (error) {
      console.error('Transfer initialization failed:', error)
      if (this.onError) {
        this.onError(error)
      }
    }
  }

  // 取消传输
  cancel() {
    this.isCancelled = true
    this.isSendingChunk = false // 重置发送标志
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close()
    }
  }

  // 清理资源
  destroy() {
    this.cancel()
    this.onProgress = null
    this.onError = null
    this.onComplete = null
    this.onDownloadUrlReady = null
    this.onTransferStarted = null
    this.totalBytesSent = 0
    this.isSendingChunk = false
  }
}

export default WebSocketTransfer
