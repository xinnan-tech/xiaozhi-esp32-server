# AI 语音数字人 H5 组件抽取方案

## 目标

将当前 `feedback-h5` 中的 AI 语音对话能力抽成独立组件，后续可被多个业务复用：

- 客户反馈 H5
- 后台 AI 数字人助手
- CRM 建档助手
- 产品/套餐咨询助手
- 其他门店经营助手

组件只负责“对话体验”，不关心 CRM、反馈、员工 KPI 等业务细节。

## 当前耦合点

当前 `feedback-h5` 同时承担：

1. 门店服务码查询。
2. 员工选择。
3. 设备初始化/OTA。
4. WebSocket 语音连接。
5. 音频采集/Opus 编码。
6. 音频播放/Opus 解码。
7. Live2D 数字人展示。
8. 反馈业务流程。
9. 点评生成和发布跳转。

其中真正应该抽成通用组件的是：

```text
音频采集
音频播放
WebSocket 对话协议
Live2D 展示
消息状态管理
数字人说话/停顿/表情
```

业务方只注入：

```text
会话配置
用户上下文
系统提示词/业务指令
onMessage 回调
onResult 回调
```

## 建议目录结构

```text
main/ai-voice-widget/
├── README.md
├── index.html                    # 独立演示页
├── src/
│   ├── voice-widget.js            # 对外主入口
│   ├── voice-session.js           # WebSocket 会话管理
│   ├── audio-recorder.js          # 录音/Opus 编码
│   ├── audio-player.js            # 播放/Opus 解码
│   ├── live2d-avatar.js           # Live2D 适配层
│   ├── protocol.js                # 消息协议封装
│   └── styles.css                 # 组件样式
├── adapters/
│   ├── feedback-adapter.js        # 客户反馈业务适配
│   ├── admin-agent-adapter.js     # 后台 AI 助手适配
│   └── crm-profile-adapter.js     # CRM 建档助手适配
└── resources/                     # 可选：Live2D 模型资源，或由业务方传入
```

## 对外 API 设计

```js
import { createVoiceWidget } from './src/voice-widget.js';

const widget = createVoiceWidget({
  container: '#voiceWidget',
  wsUrl: 'wss://example.com/ws',
  model: {
    type: 'live2d',
    name: 'hiyori_pro_zh',
    basePath: '/resources/hiyori_pro_zh/'
  },
  session: {
    storeId: 'store001',
    employeeId: 'emp001',
    memberId: 'member001',
    mode: 'crm-profile'
  },
  prompts: {
    system: '你是门店CRM建档助手',
    opening: '您好，我来帮您完善客户档案。'
  },
  onMessage(message) {
    console.log('message', message);
  },
  onFinal(result) {
    console.log('structured result', result);
  },
  onError(error) {
    console.error(error);
  }
});

await widget.start();
```

## 与业务解耦后的事件

组件只抛事件：

```text
ready
connected
disconnected
user_speech_start
user_speech_end
assistant_speech_start
assistant_speech_end
message
structured_result
error
```

业务方自己决定如何处理：

```text
保存反馈
创建客户
更新客户档案
创建建议
创建问题
消费套餐
```

## 后台 AI 数字人的落地方式

后台当前已经有文本对话版 AI 助手。后续可以把输入层替换为：

```text
VoiceWidget
  ↓ structured_result / message
/agent/chat
  ↓ Agent Graph
Skill / CLI / CRM API
```

即：

```text
数字人只是交互壳
Agent Graph 负责思考和编排
CLI/API 负责执行系统操作
```

## CRM 建档助手示例

用户说：

```text
她叫张女士，38岁，手机号尾号1234，主要是肩颈酸痛，睡眠不好，买了养生减肥10次套餐。
```

语音组件产出文本，Agent Graph 解析为计划：

```json
[
  {"skill": "crm.member-list", "args": {"keyword": "1234"}},
  {"skill": "crm.member-create-or-update", "args": {"name": "张女士", "age": 38, "healthIssues": ["肩颈酸痛", "睡眠不好"]}},
  {"skill": "crm.product-list", "args": {"keyword": "养生减肥"}},
  {"skill": "crm.product-purchase", "args": {"totalCount": 10}}
]
```

高风险或资产变动步骤进入确认：

```text
我将为张女士关联“养生减肥10次套餐”，是否确认？
```

## 当前建议的产品方向

门店核心不应以“到店记录/账户流水”为中心，而应以：

```text
客户档案
身体状态变化
已购产品/套餐
套餐剩余次数/金额
累计消费金额
建议/问题闭环
```

到店记录和账户流水仍保留，但降级为支撑数据，不作为店长主视角。

## 下一步拆分计划

1. 从 `feedback-h5/js/audio-recorder.js` 抽出 `ai-voice-widget/src/audio-recorder.js`。
2. 从 `feedback-h5/js/audio-player.js` 抽出 `ai-voice-widget/src/audio-player.js`。
3. 从 `feedback-h5/js/live2d-manager.js` 抽出 `ai-voice-widget/src/live2d-avatar.js`。
4. 新增 `voice-session.js` 管理 WebSocket 协议。
5. 新增 `voice-widget.js` 作为统一入口。
6. 用 adapter 方式接入反馈、CRM、后台 Agent。
7. 后台 AI 助手可选择文本输入或语音数字人输入。
