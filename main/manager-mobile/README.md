## Smart Control Panel Mobile (manager-mobile)
Cross-platform mobile management application based on uni-app v3 + Vue 3 + Vite, supporting App (Android & iOS) and WeChat Mini Program.

### Platform Compatibility

| H5 | iOS | Android | WeChat Mini Program |
| -- | --- | ------- | ------------------- | 
| √  | √   | √       | √                   | 

Note: Different UI components may have slight compatibility differences across platforms. Please refer to the respective component library documentation.

### Development Environment Requirements
- Node >= 18
- pnpm >= 7.30 (recommended to use `pnpm@10.x` as declared in the project)
- Optional: HBuilderX (for App debugging/packaging), WeChat Developer Tools (for WeChat Mini Program)

### Quick Start
1) Configure environment variables
   - Copy `env/.env.example` to `env/.env.development`
   - Modify configuration items according to your needs (especially `VITE_SERVER_BASEURL`, `VITE_UNI_APPID`, `VITE_WX_APPID`)

2) Install dependencies

```bash
pnpm i
```

3) Local development (hot reload)
- H5: `pnpm dev:h5`, then check the IP and port displayed in the startup logs
- WeChat Mini Program: `pnpm dev:mp` or `pnpm dev:mp-weixin`, then import `dist/dev/mp-weixin` in WeChat Developer Tools
- App: Import `manager-mobile` in HBuilderX, then follow the tutorial below to run

### Environment Variables and Configuration
The project uses a custom `env` directory for environment files, named according to Vite conventions: `.env.development`, `.env.production`, etc.

Key variables (partial):
- VITE_APP_TITLE: Application name (written to `manifest.config.ts`)
- VITE_UNI_APPID: uni-app application appid (App)
- VITE_WX_APPID: WeChat Mini Program appid (mp-weixin)
- VITE_FALLBACK_LOCALE: Default language, e.g., `zh-Hans`
- VITE_SERVER_BASEURL: Server base URL (HTTP request baseURL)
- VITE_DELETE_CONSOLE: Whether to remove console during build (`true`/`false`)
- VITE_SHOW_SOURCEMAP: Whether to generate sourcemap (disabled by default)
- VITE_LOGIN_URL: Login page path for redirect when not logged in (used by route interceptor)

Example (`env/.env.development`):
```env
VITE_APP_TITLE=XiaoZhi
VITE_FALLBACK_LOCALE=zh-Hans
VITE_UNI_APPID=
VITE_WX_APPID=

VITE_SERVER_BASEURL=http://localhost:8080

VITE_DELETE_CONSOLE=false
VITE_SHOW_SOURCEMAP=false
VITE_LOGIN_URL=/pages/login/index
```

Note:
- `manifest.config.ts` reads title, appid, language and other configurations from `env`.

### Important Notes
⚠️ **Configuration items that must be modified before deployment:**

1. **Application ID Configuration**
   - `VITE_UNI_APPID`: Need to create an application in [DCloud Developer Center](https://dev.dcloud.net.cn/) and obtain AppID
   - `VITE_WX_APPID`: Need to register a Mini Program in [WeChat Public Platform](https://mp.weixin.qq.com/) and obtain AppID

2. **Server Address**
   - `VITE_SERVER_BASEURL`: Modify to your actual server address

3. **Application Information**
   - `VITE_APP_TITLE`: Modify to your application name
   - Update icon resources like `src/static/logo.png`

4. **Other Configurations**
   - Check application configuration in `manifest.config.ts`
   - Modify tabbar configuration in `src/layouts/fg-tabbar/tabbarList.ts` as needed

### Detailed Operation Guide

#### 1. Get uni-app AppID
![Generate AppID](../../docs/images/manager-mobile/生成appid.png)
- Copy the generated AppID to environment variable `VITE_UNI_APPID`

#### 2. Local Run Steps
![Local Run](../../docs/images/manager-mobile/本地运行.png)

**App Local Debugging:**
1. Import `manager-mobile` directory in HBuilderX
2. Re-identify the project
3. Connect phone or use emulator for real device debugging

**Project Recognition Issue Resolution:**
![Re-identify Project](../../docs/images/manager-mobile/重新识别项目.png)

If HBuilderX cannot correctly identify the project type:
- Right-click in project root directory and select "Re-identify Project Type"
- Ensure the project is recognized as a "uni-app" project

### Routing and Authentication
- Route interceptor plugin `routeInterceptor` is registered in `src/main.ts`.
- Blacklist interception: Only validates pages configured as requiring login (from `getNeedLoginPages` in `@/utils`).
- Login check: Based on user information (`useUserStore` from `pinia`), redirects to `VITE_LOGIN_URL` when not logged in, with redirect parameter to return to original page.

### Network Requests
- Based on `alova` + `@alova/adapter-uniapp`, instance created uniformly in `src/http/request/alova.ts`.
- `baseURL` reads environment configuration (`getEnvBaseUrl`), can dynamically switch domains via `method.config.meta.domain`.
- Authentication: Defaults to injecting `Authorization` header from local `token` (`uni.getStorageSync('token')`), redirects to login if missing.
- Response: Unified handling of HTTP errors with `statusCode !== 200` and business errors with `code !== 0`; `401` clears token and redirects to login.

### Build and Release

**WeChat Mini Program:**
1. Ensure correct `VITE_WX_APPID` is configured
2. Run `pnpm build:mp`, output in `dist/build/mp-weixin`
3. Import project directory in WeChat Developer Tools and upload code
4. Submit for review in WeChat Public Platform

**Android & iOS App:**

#### 3. App Packaging and Release Steps

**Step 1: Prepare for Packaging**
![Packaging Release Step 1](../../docs/images/manager-mobile/打包发行步骤1.png)

1. Ensure correct `VITE_UNI_APPID` is configured
2. Run `pnpm build:app`, output in `dist/build/app`
3. Import project directory in HBuilderX
4. Click "Release" → "Native App-Cloud Packaging" in HBuilderX

**Step 2: Configure Packaging Parameters**
![Packaging Release Step 2](../../docs/images/manager-mobile/打包发行步骤2.png)

1. **App Icon and Launch Screen**: Upload app icon and launch screen images
2. **App Version Number**: Set version number and version name
3. **Signing Certificate**:
   - Android: Upload keystore certificate file
   - iOS: Configure developer certificate and provisioning profile
4. **Package Name Configuration**: Set app package name (Bundle ID)
5. **Package Type**: Choose test package or release package
6. Click "Package" to start cloud packaging process

**Publish to App Stores:**
- **Android**: Upload generated APK file to various Android app markets
- **iOS**: Upload generated IPA file to App Store via App Store Connect (requires Apple Developer account)

### Conventions and Engineering
- Pages and subpackages: Generated uniformly by `@uni-helper/vite-plugin-uni-pages` and `pages.config.ts`; tabbar configuration in `src/layouts/fg-tabbar/tabbarList.ts`.
- Auto-import of components and hooks: See `unplugin-auto-import` and `@uni-helper/vite-plugin-uni-components` in `vite.config.ts`.
- Styling: Uses UnoCSS and `src/style/index.scss`.
- State management: `pinia` + `pinia-plugin-persistedstate`.
- Code standards: Built-in `eslint`, `husky`, `lint-staged`, auto-format before commit (`lint-staged`).

### Common Scripts
```bash
# Development
pnpm dev:mp        # Equivalent to dev:mp-weixin

# Build
pnpm build:mp      # Equivalent to build:mp-weixin

# Others
pnpm type-check
pnpm lint && pnpm lint:fix
```

### License
MIT