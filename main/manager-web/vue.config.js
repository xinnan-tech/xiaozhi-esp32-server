const { defineConfig } = require('@vue/cli-service');
const dotenv = require('dotenv');
// TerserPlugin is used to compress JavaScript
const TerserPlugin = require('terser-webpack-plugin');
// CompressionPlugin enables Gzip compression
const CompressionPlugin = require('compression-webpack-plugin')
// BundleAnalyzerPlugin is used to analyze bundled files
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
// WorkboxPlugin generates the Service Worker
const { InjectManifest } = require('workbox-webpack-plugin');
// Import path module

const path = require('path')

function resolve(dir) {
  return path.join(__dirname, dir)
}

// Ensure the .env file is loaded
dotenv.config();

// Define the CDN resource list to ensure Service Worker accessibility
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

// Check if CDN is used
const useCDN = process.env.VUE_APP_USE_CDN === 'true';

module.exports = defineConfig({
  productionSourceMap: process.env.NODE_ENV !== 'production', // Do not generate source maps in production
  devServer: {
    port: 8001, // Set port to 8001
    proxy: {
      '/xiaozhi': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true
      }
    },
    client: {
      overlay: false, // Do not display webpack error overlay
    },
  },
  publicPath: process.env.VUE_APP_PUBLIC_PATH || "/",
  chainWebpack: config => {

    // Modify HTML plugin config to dynamically insert CDN links
    config.plugin('html')
      .tap(args => {
        // Determine whether to use CDN based on config
        if (process.env.NODE_ENV === 'production' && useCDN) {
          args[0].cdn = cdnResources;
        }
        return args;
      });

    // Code splitting optimization
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

    // Enable optimization settings
    config.optimization.usedExports(true);
    config.optimization.concatenateModules(true);
    config.optimization.minimize(true);
  },
  configureWebpack: config => {
    if (process.env.NODE_ENV === 'production') {
      // Enable multi-threaded compilation
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

      // Conditionally add Service Worker based on CDN usage
      config.plugins.push(
        new InjectManifest({
          swSrc: path.resolve(__dirname, 'src/service-worker.js'),
          swDest: 'service-worker.js',
          exclude: [/\.map$/, /asset-manifest\.json$/],
          maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
          // Custom Service Worker injection point
          injectionPoint: 'self.__WB_MANIFEST',
          // Pass additional info to Service Worker
          additionalManifestEntries: useCDN ?
            [{ url: 'cdn-mode', revision: 'enabled' }] :
            [{ url: 'cdn-mode', revision: 'disabled' }]
        })
      );

      // If using a CDN, configure externals to exclude dependencies
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
        // Ensure externals are not set when CDN is disabled, allowing webpack to bundle all dependencies
        config.externals = {};
      }

      if (process.env.ANALYZE === 'true') {  // Control via environment variables
        config.plugins.push(
          new BundleAnalyzerPlugin({
            analyzerMode: 'server',    // Enable local server mode
            openAnalyzer: true,        // Automatically open browser
            analyzerPort: 8888         // Specify port number
          })
        );
      }
      config.cache = {
        type: 'filesystem',  // Use filesystem cache
        cacheDirectory: path.resolve(__dirname, '.webpack_cache'),  // Custom cache directory
        allowCollectingMemory: true,  // Enable memory collection
        compression: 'gzip',  // Enable gzip compression cache
        maxAge: 5184000000, // Cache validity period is 1 month
        buildDependencies: {
          config: [__filename]  // Invalidate cache on every config file modification
        }
      };
    }
  },
  // Expose CDN resource info to service-worker.js
  pwa: {
    workboxOptions: {
      skipWaiting: true,
      clientsClaim: true
    }
  }
});
