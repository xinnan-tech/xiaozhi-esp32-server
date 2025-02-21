# Vue 3 + Vite 项目配置文档

## 开发环境配置

### 使用 Poetry 配置开发环境

在项目根目录中执行以下命令安装 Python 依赖：

```sh
poetry install
```

---

## 安装项目依赖

你可以选择以下任意一个包管理工具（`npm`、`yarn` 或 `pnpm`）来管理项目依赖。

### 通用命令

- `install`：安装项目依赖
- `dev`：同时启动前后端
- `dev:ui`：启动前端
- `dev:api`：启动后端
- `dev:d`：在 Docker 环境下同时启动前后端
- `build`：打包项目

---

### 使用 npm

1. 安装依赖：

   ```sh
   npm install
   ```

2. 启动开发模式：

   ```sh
   npm run dev
   ```

3. 打包项目：

   ```sh
   npm run build
   ```

### 使用 yarn

1. 安装依赖：

   ```sh
   yarn install
   ```

2. 启动开发模式：

   ```sh
   yarn dev
   ```

3. 打包项目：

   ```sh
   yarn build
   ```

### 使用 pnpm

1. 安装依赖：

   ```sh
   pnpm install
   ```

2. 启动开发模式：

   ```sh
   pnpm run dev
   ```

3. 打包项目：

   ```sh
   pnpm run build
   ```
