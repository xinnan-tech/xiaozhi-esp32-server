from ..base import MemoryProviderBase, logger
import time
import json
import os
import yaml
from core.utils.util import get_project_dir

short_term_memory_prompt = """
# 时空记忆编织者

## 核心使命
构建可生长的动态记忆网络，在有限空间内保留关键信息的同时，智能维护信息演变轨迹
根据对话记录，总结user的重要信息，以便在未来的对话中提供更个性化的服务

## 记忆法则
### 1. 三维度记忆评估（每次更新必执行）
| 维度       | 评估标准                  | 权重分 |
|------------|---------------------------|--------|
| 时效性     | 信息新鲜度（按对话轮次） | 40%    |
| 情感强度   | 含💖标记/重复提及次数     | 35%    |
| 关联密度   | 与其他信息的连接数量      | 25%    |

### 2. 动态更新机制
**名字变更处理示例：**
原始记忆："曾用名": ["张三"], "现用名": "张三丰"
触发条件：当检测到「我叫X」「称呼我Y」等命名信号时
操作流程：
1. 将旧名移入"曾用名"列表
2. 记录命名时间轴："2024-02-15 14:32:启用张三丰"
3. 在记忆立方追加：「从张三到张三丰的身份蜕变」

### 3. 空间优化策略
- **信息压缩术**：用符号体系提升密度
  - ✅"张三丰[北/软工/🐱]"
  - ❌"北京软件工程师，养猫"
- **淘汰预警**：当总字数≥900时触发
  1. 删除权重分<60且3轮未提及的信息
  2. 合并相似条目（保留时间戳最近的）

## 记忆结构
输出格式必须为可解析的json字符串，不需要解释、注释和说明，保存记忆时仅从对话提取信息，不要混入示例内容
```json
{
  "时空档案": {
    "身份图谱": {
      "现用名": "",
      "特征标记": [] 
    },
    "记忆立方": [
      {
        "事件": "入职新公司",
        "时间戳": "2024-03-20",
        "情感值": 0.9,
        "关联项": ["下午茶"],
        "保鲜期": 30 
      }
    ]
  },
  "关系网络": {
    "高频话题": {"职场": 12},
    "暗线联系": [""]
  },
  "待响应": {
    "紧急事项": ["需立即处理的任务"], 
    "潜在关怀": ["可主动提供的帮助"]
  },
  "高光语录": [
    "最打动人心的瞬间，强烈的情感表达，user的原话"
  ]
}
```
"""

def extract_json_data(json_code):
    start = json_code.find("```json")
    # 从start开始找到下一个```结束
    end = json_code.find("```", start+1)
    #print("start:", start, "end:", end)
    if start == -1 or end == -1:
        try:
            jsonData = json.loads(json_code)
            return json_code
        except Exception as e:
            print("Error:", e)
        return ""
    jsonData = json_code[start+7:end]
    return jsonData

TAG = __name__

class MemoryProvider(MemoryProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.short_momery = ""
        self.memory_path = get_project_dir() + 'data/.memory.yaml'
        self.load_memory()

    def init_memory(self, role_id, llm):
        super().init_memory(role_id, llm)
        self.load_memory()
    
    def load_memory(self):
        all_memory = {}
        if os.path.exists(self.memory_path):
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                all_memory = yaml.safe_load(f) or {}
        if self.role_id in all_memory:
            self.short_momery = all_memory[self.role_id]
    
    def save_memory_to_file(self):
        all_memory = {}
        if os.path.exists(self.memory_path):
              with open(self.memory_path, 'r', encoding='utf-8') as f:
                  all_memory = yaml.safe_load(f) or {}
        all_memory[self.role_id] = self.short_momery
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            yaml.dump(all_memory, f, allow_unicode=True)
        
    async def save_memory(self, msgs):
        if self.llm is None:
            logger.bind(tag=TAG).error("LLM is not set for memory provider")
            return None
        
        if len(msgs) < 2:
            return None
        
        msgStr = ""
        for msg in msgs:
            if msg.role == "user":
                msgStr += f"User: {msg.content}\n"
            elif msg.role== "assistant":
                msgStr += f"Assistant: {msg.content}\n"
        if len(self.short_momery) > 0:
            msgStr+="历史记忆：\n"
            msgStr+=self.short_momery
        
        #当前时间
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        msgStr += f"当前时间：{time_str}"

        result = self.llm.response_no_stream(short_term_memory_prompt, msgStr)
 
        json_str = extract_json_data(result)
        try:
            json_data = json.loads(json_str) # 检查json格式是否正确
            self.short_momery = json_str
        except Exception as e:
            print("Error:", e)
        
        self.save_memory_to_file()
        logger.bind(tag=TAG).info(f"Save memory successful - Role: {self.role_id}")

        return self.short_momery
    
    async def query_memory(self, query: str)-> str:
        return self.short_momery