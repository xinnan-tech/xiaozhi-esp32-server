# 请求库

当前项目使用 Alova 作为唯一的 HTTP 请求库：

## 使用方式

- **Alova HTTP**：路径（src/http/request/alova.ts）
- **示例代码**：src/api/foo-alova.ts 和 src/api/foo.ts
- **API文档**：https://alova.js.org/

## 配置说明

Alova 实例已配置：
- 自动 Token 认证和刷新
- 统一错误处理和提示
- 支持动态域名切换
- 内置请求/响应拦截器

## 使用示例

```typescript
import { http } from '@/http/request/alova'

// GET 请求
http.Get<ResponseType>('/api/path', {
  params: { id: 1 },
  headers: { 'Custom-Header': 'value' },
  meta: { toast: false } // 关闭错误提示
})

// POST 请求  
http.Post<ResponseType>('/api/path', data, {
  params: { query: 'param' },
  headers: { 'Content-Type': 'application/json' }
})
```