# 按设备覆盖配置（单模块部署）

## 概述

智控台（manager-api）能给每台设备配不同的模型和提示词；只跑 xiaozhi-server 一个模块时，配置是全局的，所有设备一样。
`data/devices.yaml` 补上这一块：连接初始化时按 `device-id` 读这台设备的覆盖项，合并进这条连接的配置。

## 工作原理

`core/utils/device_overrides.py` 在 `ConnectionHandler._initialize_components` 最开头被调用（每条连接的 config 都是深拷贝，互不影响）。
每次连接都重读文件（几 KB），改完表让设备重连即生效，不用重启服务器。文件不存在、格式错、设备没登记、`enabled: false`、
名字在对应配置块里不存在，都只记日志、不改配置、不抛异常。

## 配置

`data/.config.yaml`：

```yaml
device_overrides_file: data/devices.yaml   # 默认值，可不写
```

`data/devices.yaml`（schema v1）：

```yaml
version: 1
devices:
  "aa:bb:cc:dd:ee:ff":          # device-id（设备 MAC，小写；大小写不敏感）
    name: 书房
    enabled: true
    brain: cascade              # cascade = 原版 VAD→ASR→LLM→TTS；填 S2S 配置块里的名字 = 这台设备用语音进语音出模型
    prompt: 你是书房的语音助手。   # 非空则替换全局 prompt
    llm: null                   # 非空且在 LLM 配置块里存在 → 这台设备用它
    tts: null                   # 同上
```

同一份文件也可以给前置的准入网关当白名单（`client_id` 字段给网关用，服务器不读）。

## 测试

```bash
cd main/xiaozhi-server
pytest tests/core/utils/test_device_overrides.py -q
```
