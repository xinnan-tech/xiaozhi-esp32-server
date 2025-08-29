// Uni-app polyfill for H5 platform
if (typeof window !== 'undefined' && !window.uni) {
  window.uni = {
    getStorageSync: (key: string) => {
      try {
        return localStorage.getItem(key)
      } catch (e) {
        return null
      }
    },
    setStorageSync: (key: string, value: any) => {
      try {
        localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value))
      } catch (e) {
        console.error('Failed to set storage', e)
      }
    },
    removeStorageSync: (key: string) => {
      try {
        localStorage.removeItem(key)
      } catch (e) {
        console.error('Failed to remove storage', e)
      }
    },
    navigateTo: (options: any) => {
      console.log('Navigate to:', options)
      if (options.url) {
        window.location.href = options.url
      }
    },
    redirectTo: (options: any) => {
      console.log('Redirect to:', options)
      if (options.url) {
        window.location.replace(options.url)
      }
    },
    switchTab: (options: any) => {
      console.log('Switch tab:', options)
      if (options.url) {
        window.location.href = options.url
      }
    },
    showToast: (options: any) => {
      console.log('Toast:', options.title)
    },
    showLoading: (options: any) => {
      console.log('Loading:', options.title)
    },
    hideLoading: () => {
      console.log('Hide loading')
    },
    request: (options: any) => {
      return fetch(options.url, {
        method: options.method || 'GET',
        headers: options.header || {},
        body: options.data ? JSON.stringify(options.data) : undefined,
      }).then(res => res.json())
    },
    uploadFile: (options: any) => {
      const formData = new FormData()
      formData.append(options.name, options.filePath)
      return fetch(options.url, {
        method: 'POST',
        body: formData,
      })
    },
    getSystemInfoSync: () => {
      return {
        platform: 'h5',
        windowWidth: window.innerWidth,
        windowHeight: window.innerHeight,
      }
    },
  } as any
}