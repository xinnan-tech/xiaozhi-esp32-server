# QWeather 天气插件配置

天气插件使用 QWeather GeoAPI v2 和天气 API v7，支持 API Key 与 Ed25519 JWT 两种认证方式。

## API Key

```yaml
plugins:
  get_weather:
    api_host: "你的API Host"
    auth_type: "api_key"
    api_key: "你的API Key"
    default_location: "广州"
```

API Key 通过 `X-QW-Api-Key` 请求头发送。请使用 QWeather 控制台分配的 API Host。

## JWT

先在 QWeather 控制台创建 JWT 凭据并登记 Ed25519 公钥，然后配置对应的 Project ID、Credential ID 和 PKCS#8 私钥：

```yaml
plugins:
  get_weather:
    api_host: "你的API Host"
    auth_type: "jwt"
    project_id: "你的Project ID"
    credential_id: "你的Credential ID"
    private_key_path: "/安全目录/ed25519-private.pem"
    default_location: "广州"
```

使用 manager-api 时，在智能体的天气插件配置中上传私钥。manager-api 需要配置项目主密钥：

```yaml
xiaozhi:
  secret:
    # `openssl rand -base64 32` 生成，解码后必须为 32 字节。
    master-key: "Base64编码的项目主密钥"
```

也可通过环境变量 `XIAOZHI_SECRET_MASTER_KEY` 提供。主密钥只应配置在 manager-api；请勿提交主密钥、API Key 或私钥到代码仓库。
