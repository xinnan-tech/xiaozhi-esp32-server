# 服务端集成凭据

Manager 的普通用户 token 属于网页登录会话，不应作为长期的 server-to-server 凭据。
`server.secret` 是 Xiaozhi Server 内部接口的信任边界，也不应交给外部集成。

Manager 为 Explorer 提供了独立、可撤销、绑定资源 owner 的 integration credential。
数据库只保存 token 的 SHA-256 摘要，原始 token 只在创建成功时返回一次。

## 为什么不复用已有认证

- `SysUserTokenServiceImpl` 的普通 token 是一条按用户保存的可变登录会话记录；登录响应只有
  access token 和相对有效期，没有 refresh token 或 renew endpoint，退出登录和修改密码还会
  立即让该记录过期。登录本身还依赖图形验证码和 SM2 密码解密，因此不适合作为机器身份。
- `server.secret` 只保护 Xiaozhi Server 内部的 `/config/**`、通讯录呼叫和聊天上报/摘要等路由，
  不覆盖 Explorer 所需的 Agent/Device API；扩大它的用途还会混淆内部服务器与 Explorer 两个主体。
- integration credential 使用独立 token namespace、独立数据库记录和独立路由前缀，不继承网页
  会话的过期/刷新行为，也不能访问 `server.secret` 的内部接口。

## 管理员操作

以超级管理员普通登录 token 调用：

- `POST /admin/integration-credentials` 创建 Explorer credential。
- `GET /admin/integration-credentials` 查看不含 secret/hash 的元数据。
- `POST /admin/integration-credentials/{credentialId}/revoke` 立即撤销。

创建请求体：

```json
{
  "name": "Explorer classroom",
  "ownerUserId": 123,
  "expiresAt": null
}
```

`ownerUserId` 决定 Explorer 可读写哪个 Manager 账号所属的 Agent/Device。
该用户被停用时，credential 也会立即失效。

创建响应中的 `token` 必须立即存入调用方的正式 secret store。不得把它写入 Git、日志、URL 或浏览器持久存储。

## Explorer 固定权限

凭据仅在 `Authorization: Bearer <integration-token>` 访问
`/integration/explorer/**` 时有效。当前只存在以下路由：

- Agent 读取、创建。
- Agent 的 `agentName` / `systemPrompt` / `ttsVoiceId` / `ttsLanguage` 更新。
- 指定 Agent 的 Device 列表读取。
- Device bind-by-code、manual-add 和 unbind；manual-add 的 `appVersion` 由 Manager 固定为
  `explorer-enrollment`，调用方不能扩大该字段。

所有 Agent/Device 操作都强制限定在 credential 绑定的 owner。

该 credential 不能访问：

- `/agent/**` 和 `/device/**` 普通用户路由。
- Agent 删除、其他账号的 Agent/Device。
- 用户管理、Provider 配置、系统配置。
- `server.secret` 管理或 `/config/**` 内部路由。

## 轮换

1. 创建新 credential。
2. 把新 token 写入调用方的正式 secret store 并部署。
3. 验证读取与允许的写入操作。
4. 撤销旧 credential。

先上线新凭据、后撤销旧凭据，可避免轮换窗口中断。
