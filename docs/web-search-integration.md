# 联网搜索插件使用指南

## 功能简介

联网搜索插件 `web_search` 支持在对话过程中实时联网搜索信息并返回结果。插件支持两个搜索源：秘塔（Metaso）和Tavily，用户可根据需要选择其中一个。

## API Key申请指南

目前我们适配了`秘塔搜索`和`Tavily搜索`。
- Tavily搜索：每个月1000次免费额度。
- 秘塔搜索：拥有较为优质的国内数据源。

## API Key申请指南

### 方式一：使用秘塔搜索

- 访问 [秘塔搜索API](https://metaso.cn/search-api/api-keys)，注册并登录账号
- 在API密钥管理页面，点击"创建新的Key"
- 复制生成的API Key（以 `mk-` 为前缀），这是配置所需的关键信息

### 方式二：使用Tavily搜索

- 访问 [Tavily控制台](https://app.tavily.com/home)，注册并登录账号
- 在控制台中创建API Key
- 复制生成的API Key（以 `tvly-` 为前缀），这是配置所需的关键信息

## 配置方式

### 方式1. 使用智控台部署（推荐）

- 登录智控台
- 进入"配置角色"页面，选择要配置的智能体
- 点击"编辑功能"按钮，在右侧参数配置区域找到"联网搜索"插件
- 勾选"联网搜索"
- 填入搜索源（`metaso`或`tavily`），并将对应的`API Key`填入配置项
- 保存配置，再保存智能体配置

### 方式2. 单模块xiaozhi-server部署

在 `data/.config.yaml` 中配置：

- 将搜索源填入 `provider`，可选值为 `metaso` 或 `tavily`
- 将申请到的API Key填入 `api_key`

```yaml
plugins:
  web_search:
    provider: "metaso"
    api_key: "你的API Key"
```

如需自定义返回结果数量和工具描述，可额外配置 `max_results` 和 `description`：

```yaml
plugins:
  web_search:
    provider: "metaso"
    description: "联网搜索工具。当用户明确需要联网搜索问题时使用此工具。"
    max_results: 5
    api_key: "你的API Key"
```

同时在 `functions` 列表中确保已启用 `web_search`：

```yaml
plugins:
  functions:
    - web_search
```

配置完成后重启服务即可生效。
