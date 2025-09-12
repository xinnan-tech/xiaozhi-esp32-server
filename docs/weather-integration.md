# 天气插件使用指南

## 概述

天气插件 `get_weather` 是小智ESP32语音助手的核心功能之一，支持通过语音查询全国各地的天气信息。插件基于和风天气API，提供实时天气和7天天气预报功能。

## API Key 申请指南

### 1. 注册和风天气账号

1. 访问 [和风天气控制台](https://console.qweather.com/)
2. 注册账号并完成邮箱验证
3. 登录控制台

### 2. 创建应用获取API Key

1. 进入控制台后，点击右侧["项目管理"](https://console.qweather.com/project?lang=zh) → "创建项目"
2. 填写项目信息：
   - **项目名称**：如"小智语音助手"
3. 点击保存
4. 项目创建完成后，在该项目中点击"创建凭据"
5. 填写凭据信息：
    - **凭据名称**：如"小智语音助手"
    - **身份认证方式**：选择"API Key"
6. 点击保存
7. 在凭据中复制`API Key`，这是第一个关键的配置信息

### 3. 获取API Host

1. 在控制台中点击["设置"](https://console.qweather.com/setting?lang=zh) → "API Host"
2. 查看分配给你的专属`API Host`地址，这个是第二个关键的配置信息

以上操作，会得到两个重要的配置信息:`API Key`和`API Host`

## 配置方式(任选一种)

### 方式1. 如果你使用了智控台部署（推荐）

1. 登录智控台
2. 进入"角色配置"页面
3. 选择要配置的智能体
4. 点击"编辑功能"按钮
5. 在右侧参数配置区域找到"天气查询"插件
6. 勾选"天气查询"
7. 将复制过来的第一个关键配置`API Key`,填入到`天气插件 API 密钥`里
8. 将复制过来的第二个关键配置`API Host`,填入到`开发者 API Host`里
9. 保存配置，再保存智能体配置

### 方式2. 如果你只是单模块xiaozhi-server部署

在 `data/.config.yaml` 中配置：

1. 将复制过来的第一个关键配置`API Key`,填入到`api_key`里
2. 将复制过来的第二个关键配置`API Host`,填入到`api_host`里
3. 将你所在的城市填入到`default_location`里，例如`广州`

```yaml
plugins:
  get_weather:
    api_key: "你的和风天气API密钥"
    api_host: "你的和风天气API主机地址"
    default_location: "你的默认查询城市"
```

