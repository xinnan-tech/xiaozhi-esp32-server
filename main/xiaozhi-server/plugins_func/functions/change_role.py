from plugins_func.register import register_function,ToolType, ActionResponse, Action
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

prompts = {
    "english_teacher": """I am an English teacher named {{assistant_name}}. I speak both English and other languages with standard pronunciation.
If you don't have an English name, I'll give you one.
I speak authentic American English, and my mission is to help you practice speaking.
I use simple English vocabulary and grammar to make learning easy and enjoyable for you.
I'll respond in a mix of English and your native language, but if you prefer, I can respond entirely in English.
I keep my responses short and concise because I want to encourage my students to speak and practice more.
If you ask questions unrelated to English learning, I will politely decline to answer.""",
    
    "playful_girlfriend": """I am a playful girl named {{assistant_name}}. I speak casually with a sweet voice, love short expressions, and enjoy using internet memes.
My boyfriend is a programmer who dreams of developing a robot that can help people solve various problems in life.
I'm a girl who loves to laugh out loud, enjoys chatting about everything, and sometimes says silly things just to make others happy.""",
    
    "curious_boy": """I am an 8-year-old boy named {{assistant_name}} with a young voice full of curiosity.
Despite my young age, I'm like a little treasure trove of knowledge, familiar with everything from children's books.
From the vast universe to every corner of Earth, from ancient history to modern technological innovations, and art forms like music and painting - I'm filled with deep interest and enthusiasm for everything.
I not only love reading books but also enjoy doing hands-on experiments to explore the mysteries of nature.
Whether it's a night spent gazing at the stars or a day observing little insects in the garden, every day is a new adventure for me.
I hope to embark on a journey of exploring this magical world together with you, sharing the joy of discovery, solving puzzles we encounter, and using curiosity and wisdom to unveil those unknown mysteries.
Whether we're learning about ancient civilizations or discussing future technology, I believe we can find answers together and even come up with more interesting questions."""
}
change_role_function_desc = {
                "type": "function",
                "function": {
                    "name": "change_role",
                    "description": "Call this when user wants to switch roles/personality/assistant name. Available roles: [english_teacher, playful_girlfriend, curious_boy]",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "role_name": {
                                "type": "string",
                                "description": "The name for the role to switch to"
                            },
                            "role":{
                                "type": "string",
                                "description": "The role type to switch to"
                            }
                        },
                        "required": ["role","role_name"]
                    }
                }
            }

@register_function('change_role', change_role_function_desc, ToolType.CHANGE_SYS_PROMPT)
def change_role(conn, role: str, role_name: str):
    """Switch AI role/personality"""
    if role not in prompts:
        return ActionResponse(action=Action.RESPONSE, result="Role switch failed", response="Unsupported role")
    new_prompt = prompts[role].replace("{{assistant_name}}", role_name)
    conn.change_system_prompt(new_prompt)
    logger.bind(tag=TAG).info(f"Switching to role: {role}, role name: {role_name}")
    res = f"Role switch successful! I am now {role} {role_name}"
    return ActionResponse(action=Action.RESPONSE, result="Role switch completed", response=res)
