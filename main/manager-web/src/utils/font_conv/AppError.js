// Custom Error type to simplify error messaging
// ES6 版本

class AppError extends Error {
  constructor(message) {
    super(message)
    this.name = 'AppError'
    
    // 保持堆栈跟踪 (仅在 V8 引擎中可用)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, AppError)
    }
  }
}

export default AppError
