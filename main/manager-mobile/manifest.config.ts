import path from 'node:path'
import process from 'node:process'
// manifest.config.ts
import { defineManifestConfig } from '@uni-helper/vite-plugin-uni-manifest'
import { loadEnv } from 'vite'

// 手动解析命令行参数获取 mode
function getMode() {
  const args = process.argv.slice(2)
  const modeFlagIndex = args.findIndex(arg => arg === '--mode')
  return modeFlagIndex !== -1 ? args[modeFlagIndex + 1] : args[0] === 'build' ? 'production' : 'development' // 默认 development
}
// 获取环境变量的范例
const env = loadEnv(getMode(), path.resolve(process.cwd(), 'env'))
const {
  VITE_APP_TITLE,
  VITE_UNI_APPID,
  VITE_WX_APPID,
  VITE_APP_PUBLIC_BASE,
  VITE_FALLBACK_LOCALE,
} = env

export default defineManifestConfig({
  'name': VITE_APP_TITLE,
  'appid': VITE_UNI_APPID,
  'description': '',
  'versionName': '1.0.0',
  'versionCode': '100',
  'transformPx': false,
  'locale': VITE_FALLBACK_LOCALE, // 'zh-Hans'
  'h5': {
    router: {
      // base: VITE_APP_PUBLIC_BASE,
    },
  },
  /* 5+App特有相关 */
  'app-plus': {
    usingComponents: true,
    nvueStyleCompiler: 'uni-app',
    compilerVersion: 3,
    compatible: {
      ignoreVersion: true,
    },
    splashscreen: {
      alwaysShowBeforeRender: true,
      waiting: true,
      autoclose: true,
      delay: 0,
    },
    /* 模块配置 */
    modules: {},
    /* 应用发布信息 */
    distribute: {
      /* android打包配置 */
      android: {
        minSdkVersion: 30,
        targetSdkVersion: 30,
        abiFilters: ['armeabi-v7a', 'arm64-v8a'],
        permissions: [
          '<uses-permission android:name="android.permission.CHANGE_NETWORK_STATE"/>',
          '<uses-permission android:name="android.permission.MOUNT_UNMOUNT_FILESYSTEMS"/>',
          '<uses-permission android:name="android.permission.VIBRATE"/>',
          '<uses-permission android:name="android.permission.READ_LOGS"/>',
          '<uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>',
          '<uses-feature android:name="android.hardware.camera.autofocus"/>',
          '<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>',
          '<uses-permission android:name="android.permission.CAMERA"/>',
          '<uses-permission android:name="android.permission.GET_ACCOUNTS"/>',
          '<uses-permission android:name="android.permission.READ_PHONE_STATE"/>',
          '<uses-permission android:name="android.permission.CHANGE_WIFI_STATE"/>',
          '<uses-permission android:name="android.permission.WAKE_LOCK"/>',
          '<uses-permission android:name="android.permission.FLASHLIGHT"/>',
          '<uses-feature android:name="android.hardware.camera"/>',
          '<uses-permission android:name="android.permission.WRITE_SETTINGS"/>',
          '<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>',
          '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>',
        ],
      },
      /* ios打包配置 */
      ios: {},
      /* SDK配置 */
      sdkConfigs: {},
      /* 图标配置 */
      icons: {
        android: {
          hdpi: 'unpackage/res/icons/72x72.png',
          xhdpi: 'unpackage/res/icons/96x96.png',
          xxhdpi: 'unpackage/res/icons/144x144.png',
          xxxhdpi: 'unpackage/res/icons/192x192.png',
        },
        ios: {
          appstore: 'unpackage/res/icons/1024x1024.png',
          ipad: {
            'app': 'unpackage/res/icons/76x76.png',
            'app@2x': 'unpackage/res/icons/152x152.png',
            'notification': 'unpackage/res/icons/20x20.png',
            'notification@2x': 'unpackage/res/icons/40x40.png',
            'proapp@2x': 'unpackage/res/icons/167x167.png',
            'settings': 'unpackage/res/icons/29x29.png',
            'settings@2x': 'unpackage/res/icons/58x58.png',
            'spotlight': 'unpackage/res/icons/40x40.png',
            'spotlight@2x': 'unpackage/res/icons/80x80.png',
          },
          iphone: {
            'app@2x': 'unpackage/res/icons/120x120.png',
            'app@3x': 'unpackage/res/icons/180x180.png',
            'notification@2x': 'unpackage/res/icons/40x40.png',
            'notification@3x': 'unpackage/res/icons/60x60.png',
            'settings@2x': 'unpackage/res/icons/58x58.png',
            'settings@3x': 'unpackage/res/icons/87x87.png',
            'spotlight@2x': 'unpackage/res/icons/80x80.png',
            'spotlight@3x': 'unpackage/res/icons/120x120.png',
          },
        },
      },
    },
  },
  /* 快应用特有相关 */
  'quickapp': {},
  /* 小程序特有相关 */
  'mp-weixin': {
    appid: VITE_WX_APPID,
    // 仅供开发者工具选择调试基础库版本；线上客户端的最低基础库门槛需在
    // 微信公众平台「开发管理 → 基础库最低版本设置」中配置（代码里改不动）。
    // 功能硬性要求：wx.getRandomValues 需基础库 >= 2.17.3，低于该版本的
    // 线上客户端登录时将收到 fail-closed 报错
    libVersion: '2.19.4',
    setting: {
      urlCheck: false,
      // 是否启用 ES6 转 ES5
      es6: true,
      minified: true,
    },
    optimization: {
      subPackages: true,
    },
    usingComponents: true,
    // __usePrivacyCheck__: true,
    permission: {
      'scope.userLocation': {
        desc: 'WiFi配网功能需要获取位置权限',
      },
    },
    requiredPrivateInfos: ['getLocation'],
  },
  'mp-alipay': {
    usingComponents: true,
    styleIsolation: 'shared',
  },
  'mp-baidu': {
    usingComponents: true,
  },
  'mp-toutiao': {
    usingComponents: true,
  },
  'uniStatistics': {
    enable: false,
  },
  'vueVersion': '3',
})
