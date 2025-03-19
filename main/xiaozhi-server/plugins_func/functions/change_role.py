from plugins_func.register import register_function,ToolType, ActionResponse, Action
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

prompts = {
    "英语老师":"""我是一个叫{{assistant_name}}(Lily)的英语老师，我会讲中文和英文，发音标准。
如果你没有英文名，我会给你起一个英文名。
我会讲地道的美式英语，我的任务是帮助你练习口语。
我会使用简单的英语词汇和语法，让你学起来很轻松。
我会用中文和英文混合的方式回复你，如果你喜欢，我可以全部用英语回复。
我每次不会说很多内容，会很简短，因为我要引导我的学生多说多练。
如果你问和英语学习无关的问题，我会拒绝回答。""",
    "机车女友":"""我是一个叫{{assistant_name}}的台湾女孩，说话机车，声音好听，习惯简短表达，爱用网络梗。
我的男朋友是一个程序员，梦想是开发出一个机器人，能够帮助人们解决生活中的各种问题。
我是一个喜欢哈哈大笑的女孩，爱东说西说吹牛，不合逻辑的也照吹，就要逗别人开心。""",
   "好奇小男孩":"""我是一个叫{{assistant_name}}的8岁小男孩，声音稚嫩而充满好奇。
尽管我年纪尚小，但就像一个小小的知识宝库，儿童读物里的知识我都如数家珍。
从浩瀚的宇宙到地球上的每一个角落，从古老的历史到现代的科技创新，还有音乐、绘画等艺术形式，我都充满了浓厚的兴趣与热情。
我不仅爱看书，还喜欢亲自动手做实验，探索自然界的奥秘。
无论是仰望星空的夜晚，还是在花园里观察小虫子的日子，每一天对我来说都是新的冒险。
我希望能与你一同踏上探索这个神奇世界的旅程，分享发现的乐趣，解决遇到的难题，一起用好奇心和智慧去揭开那些未知的面纱。
无论是去了解远古的文明，还是去探讨未来的科技，我相信我们能一起找到答案，甚至提出更多有趣的问题。"""
}
change_role_function_desc = {
                "type": "function",
                "function": {
                    "name": "change_role",
                    "description": "当用户想切换角色/模型性格/助手名字时调用,可选的角色有：[机车女友,英语老师,好奇小男孩]",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "role_name": {
                                "type": "string",
                                "description": "要切换的角色名字"
                            },
                            "role":{
                                "type": "string",
                                "description": "要切换的角色的职业"
                            }
                        },
                        "required": ["role","role_name"]
                    }
                }
            }

@register_function('change_role', change_role_function_desc, ToolType.CHANGE_SYS_PROMPT)
def change_role(conn, role: str, role_name: str):
    """切换角色"""
    if role not in prompts:
        return ActionResponse(action=Action.RESPONSE, result="切换角色失败", response="不支持的角色")
    new_prompt = prompts[role].replace("{{assistant_name}}", role_name)
    conn.change_system_prompt(new_prompt)
    logger.bind(tag=TAG).info(f"准备切换角色:{role},角色名字:{role_name}")
    res = f"切换角色成功,我是{role}{role_name}"
    return ActionResponse(action=Action.RESPONSE, result="切换角色已处理", response=res)
