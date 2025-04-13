const { defineConfig } = require('@vue/cli-service');
const dotenv = require('dotenv');
// TerserPlugin 用于压缩 JavaScript
const TerserPlugin = require('terser-webpack-plugin');
// CompressionPlugin 开启 Gzip 压缩
const CompressionPlugin = require('compression-webpack-plugin')
// BundleAnalyzerPlugin 用于分析打包后的文件
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
// 引入 path 模块
const path = require('path');
// 确保加载 .env 文件
dotenv.config();
module.exports = defineConfig({
  productionSourceMap: process.env.NODE_ENV === 'production' ? false : true, // 生产环境不生成 source map
  devServer: {
    port: 8001, // 指定端口为 8001
    proxy: {
    },
    client: {
      overlay: false, // 不显示 webpack 错误覆盖层
    },
  },
  chainWebpack: config => {

    // 修改 HTML 插件配置，动态插入 CDN 链接
    config.plugin('html')
      .tap(args => {
        if (process.env.NODE_ENV === 'production') {
          args[0].cdn = {
            css: [
              'https://cdn.jsdelivr.net/npm/element-ui@2.15.14/lib/theme-chalk/index.css',
              'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css'
            ],
            js: [
              'https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.min.js',
              'https://cdn.jsdelivr.net/npm/vue-router@3.6.5/dist/vue-router.min.js',
              'https://cdn.jsdelivr.net/npm/vuex@3.6.2/dist/vuex.min.js',
              'https://cdn.jsdelivr.net/npm/element-ui@2.15.14/lib/index.js',
              'https://cdn.jsdelivr.net/npm/axios@0.27.2/dist/axios.min.js',
              'https://cdn.jsdelivr.net/npm/opus-decoder@0.7.7/dist/opus-decoder.min.js'
            ]
          };
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
      config.externals = {
        'vue': 'Vue',
        'vue-router': 'VueRouter',
        'vuex': 'Vuex',
        'element-ui': 'ELEMENT',
        'axios': 'axios',
        'opus-decoder': 'OpusDecoder'
      };
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
      config.resolve.alias = {
        '@': path.resolve(__dirname, 'src'),  // 让 '@' 代表 'src' 目录
        '@assets': path.resolve(__dirname, 'src/assets'), // 设置 '@assets' 为 'src/assets' 目录
        '@components': path.resolve(__dirname, 'src/components'), // 设置 '@components' 为 'src/components' 目录
        '@views': path.resolve(__dirname, 'src/views'), // 设置 '@views' 为 'src/views' 目录
      }
    }
  },

});
