# 自定义主题对接说明（前端/设备端/MQTT 网关）

本文总结近期合入主分支的“自定义主题”相关改动，便于其他人同步：

## 前端/业务侧改动
- 主题生成对设备在线状态做强绑定：设备不在线时，入口按钮禁用且无法进入配置。
- 支持自定义唤醒词，打包时写入 `CONFIG_CUSTOM_WAKE_WORD` 与 `CONFIG_CUSTOM_WAKE_WORD_DISPLAY`，设备端解析生效。
- 解决浅色/深色模式选择后仅生效浅色的问题：生成的 `index.json` 中带 `skin.default_mode`，设备按该值加载默认主题。

## 设备端改动（xiaozhi-esp32）
- 文件：`main/assets.cc`
- 解析 `skin.default_mode` 字段（`light`/`dark`），加载完资源后选择对应的主题并调用 `display->SetTheme`，从而让前端选择的默认模式在设备端生效。

关键代码：
```200:247:xiaozhi-esp32/main/assets.cc
    cJSON* skin = cJSON_GetObjectItem(root, "skin");
    const char* default_skin = nullptr;
    if (cJSON_IsObject(skin)) {
        cJSON* default_mode = cJSON_GetObjectItem(skin, "default_mode");
        if (cJSON_IsString(default_mode)) {
            default_skin = default_mode->valuestring;
        }
        ...
    }
    auto display = Board::GetInstance().GetDisplay();
    LvglTheme* target_theme = nullptr;
    if (default_skin && std::string(default_skin) == "dark") {
        target_theme = dark_theme;
    } else {
        target_theme = light_theme;
    }
    if (target_theme != nullptr) {
        display->SetTheme(target_theme);
    }
```


关键代码：
```39:118:xiaozhi-esp32/main/audio/wake_words/custom_wake_word.cc
void CustomWakeWord::ParseWakenetModelConfig() {
    language_ = "cn";
    duration_ = 3000;
    threshold_ = 0.2f;
    commands_.clear();
    ...
    cJSON* multinet_model = cJSON_GetObjectItem(root, "multinet_model_info");
    if (!cJSON_IsObject(multinet_model)) {
        multinet_model = cJSON_GetObjectItem(root, "multinet_model");
    }
    if (cJSON_IsObject(multinet_model)) {
        ...
        if (cJSON_IsNumber(threshold)) {
            double th = threshold->valuedouble;
            threshold_ = (th > 1.0) ? (th / 100.0f) : th;
        }
        parse_commands(commands);
    }
    if (commands_.empty()) { // CONFIG_* 回退
        cJSON* cfg_cmd = cJSON_GetObjectItem(root, "CONFIG_CUSTOM_WAKE_WORD");
        cJSON* cfg_disp = cJSON_GetObjectItem(root, "CONFIG_CUSTOM_WAKE_WORD_DISPLAY");
        if (cJSON_IsString(cfg_cmd) && cJSON_IsString(cfg_disp)) {
            commands_.push_back({cfg_cmd->valuestring, cfg_disp->valuestring, "wake"});
        }
    }
#ifdef CONFIG_CUSTOM_WAKE_WORD
    if (commands_.empty()) {
        commands_.push_back({CONFIG_CUSTOM_WAKE_WORD, CONFIG_CUSTOM_WAKE_WORD_DISPLAY, "wake"});
    }
#endif
}
```

## MQTT 网关改动（xiaozhi-mqtt-gateway）
- 文件：`app.js`
- CORS 允许 `Content-Type, Authorization, token`，避免前端预检因自定义头失败。
- 新增接口 `GET /api/token`，返回 `{ date, token }`，其中 `token = sha256(YYYY-MM-DD + MQTT_SIGNATURE_KEY)`，方便前端动态获取当日 token，避免手工填写或写死。

关键代码：
```803:813:xiaozhi-mqtt-gateway/app.js
    res.header('Access-Control-Allow-Origin', allowOrigin);
    res.header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, token');
```

```1000:1016:xiaozhi-mqtt-gateway/app.js
// 对外暴露今日 token（仅 token，不暴露密钥），便于前端动态获取
app.get('/api/token', (req, res) => {
    try {
        const token = calculateDailyToken();
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const dateStr = `${year}-${month}-${day}`;
        res.json({ date: dateStr, token });
    } catch (error) {
        console.error('获取 token 失败:', error);
        res.status(500).json({ error: 'failed to calculate token' });
    }
});
```

