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
                "name": "hass_toggle_device",
                "description": "用homeassistant帮助用户打开或关闭设备",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "enum": ["on", "off"],
                                "description": "指定开还是关,开是on,关是off"
                            },
                            "entity_id": {
                            "type": "string",
                            "description": "需要操作的设备id,homeassistant里的entity_id"
                            }
                        },
                        "required": ["state", "entity_id"]
                    }
                }
            },
            {
            "type": "function",
            "function": {
                "name": "hass_play_music",
                "description": "用户想听音乐、有声书的时候使用，在房间的媒体播放器（media_player）里播放对应音频",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "media_content_id": {
                                "type": "string",
                                "description": "可以是音乐或有声书的专辑名称、歌曲名、演唱者,如果未指定就填random"
                            },
                            "entity_id": {
                            "type": "string",
                            "description": "需要操作的音箱的设备id,homeassistant里的entity_id,media_player开头"
                            }
                        },
                        "required": ["media_content_id", "entity_id"]
                    }
                }
            }

        ]
