import path from 'node:path'
import process from 'node:process'
import Uni from '@dcloudio/vite-plugin-uni'
import Components from '@uni-helper/vite-plugin-uni-components'
// @see https://uni-helper.js.org/vite-plugin-uni-layouts
import UniLayouts from '@uni-helper/vite-plugin-uni-layouts'
// @see https://github.com/uni-helper/vite-plugin-uni-manifest
import UniManifest from '@uni-helper/vite-plugin-uni-manifest'
// @see https://uni-helper.js.org/vite-plugin-uni-pages
import UniPages from '@uni-helper/vite-plugin-uni-pages'
// @see https://github.com/uni-helper/vite-plugin-uni-platform
// Need to use with @uni-helper/vite-plugin-uni-pages plugin
import UniPlatform from '@uni-helper/vite-plugin-uni-platform'
/**
 * Sub-package optimization, module async cross-package calls, component async cross-package references
 * @see https://github.com/uni-ku/bundle-optimizer
 */
import Optimization from '@uni-ku/bundle-optimizer'
import dayjs from 'dayjs'
import { visualizer } from 'rollup-plugin-visualizer'
import AutoImport from 'unplugin-auto-import/vite'
import { defineConfig, loadEnv } from 'vite'
import ViteRestart from 'vite-plugin-restart'

// https://vitejs.dev/config/
export default async ({ command, mode }) => {
  // @see https://unocss.dev/
  const UnoCSS = (await import('unocss/vite')).default
  // console.log(mode === process.env.NODE_ENV) // true

  // mode: Distinguish between production and development environment
  console.log('command, mode -> ', command, mode)
  // pnpm dev:h5 gets => serve development
  // pnpm build:h5 gets => build production
  // pnpm dev:mp-weixin gets => build development (note difference, command is build)
  // pnpm build:mp-weixin gets => build production
  // pnpm dev:app gets => build development (note difference, command is build)
  // pnpm build:app gets => build production
  // dev and build commands can use .env.development and .env.production environment variables respectively

  const { UNI_PLATFORM } = process.env
  console.log('UNI_PLATFORM -> ', UNI_PLATFORM) // Get mp-weixin, h5, app etc.

  const env = loadEnv(mode, path.resolve(process.cwd(), 'env'))
  const {
    VITE_APP_PORT,
    VITE_SERVER_BASEURL,
    VITE_DELETE_CONSOLE,
    VITE_SHOW_SOURCEMAP,
    VITE_APP_PUBLIC_BASE,
    VITE_APP_PROXY,
    VITE_APP_PROXY_PREFIX,
  } = env
  console.log('Environment variables env -> ', env)

  return defineConfig({
    envDir: './env', // Custom env directory
    base: VITE_APP_PUBLIC_BASE,
    plugins: [
      UniPages({
        exclude: ['**/components/**/**.*'],
        // homePage is set through route-block type="home" in vue files
        // pages directory is src/pages, sub-package directories cannot be configured under pages directory
        subPackages: ['src/pages-sub'], // It's an array, can configure multiple, but cannot be directories inside pages
        dts: 'src/types/uni-pages.d.ts',
      }),
      UniLayouts(),
      UniPlatform(),
      UniManifest(),
      // UniXXX needs to be imported before Uni
      {
        // Temporarily fix compilation BUG in dcloudio official @dcloudio/uni-mp-compiler
        // Reference github issue: https://github.com/dcloudio/uni-app/issues/4952
        // Custom plugin disables vite:vue plugin devToolsEnabled, forces inline to true when compiling vue templates
        name: 'fix-vite-plugin-vue',
        configResolved(config) {
          const plugin = config.plugins.find(p => p.name === 'vite:vue')
          if (plugin && plugin.api && plugin.api.options) {
            plugin.api.options.devToolsEnabled = false
          }
        },
      },
      UnoCSS(),
      AutoImport({
        imports: ['vue', 'uni-app'],
        dts: 'src/types/auto-import.d.ts',
        dirs: ['src/hooks'], // Auto import hooks
        vueTemplate: true, // default false
      }),
      // Optimization plugin needs page.json file, so it should execute after UniPages plugin
      Optimization({
        enable: {
          'optimization': true,
          'async-import': true,
          'async-component': true,
        },
        dts: {
          base: 'src/types',
        },
        logger: false,
      }),

      ViteRestart({
        // Through this plugin, modifying vite.config.js file does not need to restart to take effect
        restart: ['vite.config.js'],
      }),
      // Add BUILD_TIME and BUILD_BRANCH in h5 environment
      UNI_PLATFORM === 'h5' && {
        name: 'html-transform',
        transformIndexHtml(html) {
          return html.replace('%BUILD_TIME%', dayjs().format('YYYY-MM-DD HH:mm:ss'))
        },
      },
      // Bundle analysis plugin, only pops up in h5 + production environment
      UNI_PLATFORM === 'h5'
      && mode === 'production'
      && visualizer({
        filename: './node_modules/.cache/visualizer/stats.html',
        open: false,
        gzipSize: true,
        brotliSize: true,
      }),
      // Only enable copyNativeRes plugin on app platform
      // UNI_PLATFORM === 'app' && copyNativeRes(),
      Components({
        extensions: ['vue'],
        deep: true, // Whether to recursively scan subdirectories,
        directoryAsNamespace: false, // Whether to use directory name as namespace prefix, when true component name is directory+component name,
        dts: 'src/types/components.d.ts', // Auto-generated component type declaration file path (for TypeScript support)
      }),
      Uni(),
    ],
    define: {
      __UNI_PLATFORM__: JSON.stringify(UNI_PLATFORM),
      __VITE_APP_PROXY__: JSON.stringify(VITE_APP_PROXY),
    },
    css: {
      postcss: {
        plugins: [
          // autoprefixer({
          //   // Specify target browsers
          //   overrideBrowserslist: ['> 1%', 'last 2 versions'],
          // }),
        ],
      },
    },

    resolve: {
      alias: {
        '@': path.join(process.cwd(), './src'),
        '@img': path.join(process.cwd(), './src/static/images'),
      },
    },
    server: {
      host: '0.0.0.0',
      hmr: true,
      port: Number.parseInt(VITE_APP_PORT, 10),
      // Only effective on H5 end, not effective on other ends (other ends use build, not devServer)
      proxy: JSON.parse(VITE_APP_PROXY)
        ? {
            [VITE_APP_PROXY_PREFIX]: {
              target: VITE_SERVER_BASEURL,
              changeOrigin: true,
              rewrite: path => path.replace(new RegExp(`^${VITE_APP_PROXY_PREFIX}`), ''),
            },
          }
        : undefined,
    },
    esbuild: {
      drop: VITE_DELETE_CONSOLE === 'true' ? ['console', 'debugger'] : ['debugger'],
    },
    build: {
      sourcemap: false,
      // Convenient for non-h5 debugging
      // sourcemap: VITE_SHOW_SOURCEMAP === 'true', // default is false
      target: 'es6',
      // No compression in development environment
      minify: mode === 'development' ? false : 'esbuild',

    },
  })
}
