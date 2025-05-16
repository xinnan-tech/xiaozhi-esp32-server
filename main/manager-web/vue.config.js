const { defineConfig } = require('@vue/cli-service');
const dotenv = require('dotenv');
// TerserPlugin 用于压缩 JavaScript
const TerserPlugin = require('terser-webpack-plugin');
// CompressionPlugin 开启 Gzip 压缩
const CompressionPlugin = require('compression-webpack-plugin')
// BundleAnalyzerPlugin 用于分析打包后的文件
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
// WorkboxPlugin 用于生成Service Worker
const { InjectManifest } = require('workbox-webpack-plugin');
// 引入 path 模块

const path = require('path')
 
function resolve(dir) {
  return path.join(__dirname, dir)
}

// 确保加载 .env 文件
dotenv.config();

// 定义CDN资源列表，确保Service Worker也能访问
const cdnResources = {
  css: [
    'https://unpkg.com/element-ui@2.15.14/lib/theme-chalk/index.css',
    'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css'
  ],
  js: [
    'https://unpkg.com/vue@2.6.14/dist/vue.min.js',
    'https://unpkg.com/vue-router@3.6.5/dist/vue-router.min.js',
    'https://unpkg.com/vuex@3.6.2/dist/vuex.min.js',
    'https://unpkg.com/element-ui@2.15.14/lib/index.js',
    'https://unpkg.com/axios@0.27.2/dist/axios.min.js',
    'https://unpkg.com/opus-decoder@0.7.7/dist/opus-decoder.min.js'
  ]
};

// 判断是否使用CDN
const useCDN = process.env.VUE_APP_USE_CDN === 'true';

module.exports = defineConfig({
  productionSourceMap: process.env.NODE_ENV !=='production', // 生产环境不生成 source map
  devServer: {
    port: 8001, // 指定端口为 8001
    proxy: {
      '/xiaozhi': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true
      }
    },
    client: {
      overlay: false, // 不显示 webpack 错误覆盖层
    },
  },
  publicPath: process.env.VUE_APP_PUBLIC_PATH || "/",
  chainWebpack: config => {

    // 修改 HTML 插件配置，动态插入 CDN 链接
    config.plugin('html')
      .tap(args => {
        // 根据配置决定是否使用CDN
        if (process.env.NODE_ENV === 'production' && useCDN) {
          args[0].cdn = cdnResources;
        }
        return args;
      });

    // 代码分割优化
    config.optimization.splitChunks({
      chunks: 'all',
      minSize: 20000,
      maxSize: 250000,
      cacheGroups: {
        vendors: {
          name: 'chunk-vendors',
          test: /[\\/]node_modules[\\/]/,
          priority: -10,
          chunks: 'initial',
        },
        common: {
          name: 'chunk-common',
          minChunks: 2,
          priority: -20,
          chunks: 'initial',
          reuseExistingChunk: true,
        },
      }
    });

    // 启用优化设置
    config.optimization.usedExports(true);
    config.optimization.concatenateModules(true);
    config.optimization.minimize(true);
  },
  configureWebpack: config => {
    if (process.env.NODE_ENV === 'production') {
      // 开启多线程编译
      config.optimization = {
        minimize: true,
        minimizer: [
          new TerserPlugin({
            parallel: true,
            terserOptions: {
              compress: {
                drop_console: true,
                drop_debugger: true,
                pure_funcs: ['console.log']
              }
            }
          })
        ]
      };
      config.plugins.push(
        new CompressionPlugin({
          algorithm: 'gzip',
          test: /\.(js|css|html|svg)$/,
          threshold: 20480,
          minRatio: 0.8
        })
      );

      // 根据是否使用CDN来决定是否添加Service Worker
      config.plugins.push(
        new InjectManifest({
          swSrc: path.resolve(__dirname, 'src/service-worker.js'),
          swDest: 'service-worker.js',
          exclude: [/\.map$/, /asset-manifest\.json$/],
          maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
          // 自定义Service Worker注入点
          injectionPoint: 'self.__WB_MANIFEST',
          // 添加额外信息传递给Service Worker
          additionalManifestEntries: useCDN ?
            [{ url: 'cdn-mode', revision: 'enabled' }] :
            [{ url: 'cdn-mode', revision: 'disabled' }]
        })
      );

      // 如果使用CDN，则配置externals排除依赖包
      if (useCDN) {
        config.externals = {
          'vue': 'Vue',
          'vue-router': 'VueRouter',
          'vuex': 'Vuex',
          'element-ui': 'ELEMENT',
          'axios': 'axios',
          'opus-decoder': 'OpusDecoder'
        };
      } else {
        // 确保不使用CDN时不设置externals，让webpack打包所有依赖
        config.externals = {};
      }

      if (process.env.ANALYZE === 'true') {  // 通过环境变量控制
        config.plugins.push(
          new BundleAnalyzerPlugin({
            analyzerMode: 'server',    // 开启本地服务器模式
            openAnalyzer: true,        // 自动打开浏览器
            analyzerPort: 8888         // 指定端口号
          })
        );
      }
      config.cache = {
        type: 'filesystem',  // 使用文件系统缓存
        cacheDirectory: path.resolve(__dirname, '.webpack_cache'),  // 自定义缓存目录
        allowCollectingMemory: true,  // 启用内存收集
        compression: 'gzip',  // 启用gzip压缩缓存
        maxAge: 5184000000, // 缓存有效期为 1个月
        buildDependencies: {
          config: [__filename]  // 每次配置文件修改时缓存失效
        }
      };
    }
  },
  // 将CDN资源信息暴露给service-worker.js
  pwa: {
    workboxOptions: {
      skipWaiting: true,
      clientsClaim: true
    }
  }
});
