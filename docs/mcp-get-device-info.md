# MCP 方法如何获取设备信息

本教程将指导你如何使用MCP方法获取设备信息。

第一步：自定义你的`agent-base-prompt.txt`文件

把xiaozhi-server目录的`agent-base-prompt.txt`文件内容复制到你的`data`目录下，并重命名为`.agent-base-prompt.txt`。

第二步：修改`data/.agent-base-prompt.txt`文件，找到`<context>`标签，在标签内容中添加以下代码内容：
```
- **设备ID：** {{device_id}}
```

添加完成后，你的`data/.agent-base-prompt.txt`文件的`<context>`标签内容大致如下：
```
<context>
【重要！以下信息已实时提供，无需调用工具查询，请直接使用：】
- **设备ID：** {{device_id}}
- **当前时间：** {{current_time}}
- **今天日期：** {{today_date}} ({{today_weekday}})
- **今天农历：** {{lunar_date}}
- **用户所在城市：** {{local_address}}
- **当地未来7天天气：** {{weather_info}}
</context>
```

第三步：修改`data/.config.yaml`文件，找到`agent-base-prompt`配置，修改前内容如下：
```
prompt_template: agent-base-prompt.txt
```
修改成
```
prompt_template: data/.agent-base-prompt.txt
```

第四步：重启你的xiaozhi-server服务。

第五步：在你的mcp方法增加名称为`device_id`,类型为`string`,描述为`设备ID`的参数。

第六步：重新唤醒小智，让他调用mcp方法，查看你的mcp方法是否可以获取`设备ID`。
