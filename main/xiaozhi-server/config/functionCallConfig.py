FunctionCallConfig = [
            {
                "type": "function",
                "function": {
                    "name": "handle_exit_intent",
                    "description": "当用户想结束对话或需要退出系统时调用",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "say_goodbye": {
                                "type": "string",
                                "description": "和用户友好结束对话的告别语"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "play_music",
                    "description": "唱歌、听歌、播放音乐方法。比如用户说播放音乐，参数为：random，比如用户说播放两只老虎，参数为：两只老虎",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "song_name": {
                                "type": "string",
                                "description": "歌曲名称，如果没有指定具体歌名则为'random'"
                            }
                        },
                        "required": ["song_name"]
                    }
                }
            }
        ]