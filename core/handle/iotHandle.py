import json
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IotDescriptor:
    """
    A class to represent an IoT descriptor.
    Attributes:
    ----------
    name : str
        The name of the IoT descriptor.
    description : str
        A brief description of the IoT descriptor.
    properties : dict
        A dictionary containing properties of the IoT descriptor.
    methods : dict
        A dictionary containing methods of the IoT descriptor.
    -------
    """

    def __init__(self, name, description, properties, methods):
        self.name = name
        self.description = description
        self.properties = []
        self.methods = []

        # 根据描述创建属性
        for key, value in properties.items():
            # "volume":{"description":"当前音量 值","type":"number"}
            """
            等价于
            {
                'name': 名字,
                'description': 描述,
                'value': 0
            }
            """
            # setattr(self, key, {}) # 创建一个空字典, 名字是属性名
            property_item = globals()[key] = {}  # 创建一个空字典, 名字是属性名
            property_item['name'] = key
            property_item["description"] = value["description"]
            if value["type"] == "number":
                property_item["value"] = 0
            elif value["type"] == "bool":
                property_item["value"] = False
            elif value["type"] == "string":
                property_item["value"] = ""
            else:
                raise ValueError("Invalid type")
            self.properties.append(property_item)

        # 根据描述创建方法
        for key, value in methods.items():
            # "SetVolume": {"description":"设置音量","parameters":{"volume":{"description":"0到100之间的整数","type":"number"}}}
            """
            等价于
            SetVolume = {
                `description`: 描述,
                `volume`: {
                    `description`: 描述,
                    `value`: 0
                }
            }
            """
            # setattr(self, key, {}) # 创建一个空字典, 名字是方法名
            method = globals()[key] = {}  # 创建一个空字典, 名字是方法名
            method["description"] = value["description"]
            method['name'] = key
            for k, v in value["parameters"].items():
                # 不同的参数解析
                method[k] = {}
                method[k]["description"] = v["description"]
                if v["type"] == "number":
                    method[k]["value"] = 0
                elif v["type"] == "bool":
                    method[k]["value"] = False
                elif v["type"] == "string":
                    method[k]["value"] = ""
                else:
                    raise ValueError("Invalid type")

            self.methods.append(method)


async def handleIotDescriptors(conn, descriptors):
    """
    处理物联网描述
    示例: [{
        "name":"Speaker",
        "description":"当前 AI 机器人的扬声器",
        "properties":{
            "volume":{"description":"当前音量 值","type":"number"}  可以有bool, int, string三种类型
        },
        "methods":{
            "SetVolume":{
                "description":"设置音量","parameters":{"volume":{"description":"0到100之间的整数","type":"number"}}
            }
        }
    }]
    descriptors: 描述列表
    """
    for descriptor in descriptors:
        iot_descriptor = IotDescriptor(descriptor["name"], descriptor["description"], descriptor["properties"],
                                       descriptor["methods"])
        conn.iot_descriptors[descriptor["name"]] = iot_descriptor

    # 暂时从配置文件中设置音量，后期通过意图识别控制音量
    default_iot_volume = 100
    if "iot" in conn.config:
        default_iot_volume = conn.config["iot"]["Speaker"]["volume"]
    logger.bind(tag=TAG).info(f"服务端设置音量为{default_iot_volume}")
    await send_iot_conn(conn, "Speaker", "SetVolume", {"volume": default_iot_volume})


async def send_iot_conn(conn, name, method_name, parameters):
    """
    发送物联网指令
    name: 设备名称 "Speaker"
    method: 方法 "SetVolume"
    parameters: 参数, 是一个字典 {"volume": 100}
    发送示例:
    {
        "type": "iot",
        "commands": [
            {
                "name" :  "Speaker",
                "method": "SetVolume",
                "parameters": {
                    "volume": 100
                    }
            }
        ]
    }
    """

    for key, value in conn.iot_descriptors.items():
        if key == name:
            # 找到了设备
            for method in value.methods:
                # 找到了方法
                if method["name"] == method_name:
                    await conn.websocket.send(json.dumps({
                        "type": "iot",
                        "commands": [
                            {
                                "name": name,
                                "method": method_name,
                                "parameters": parameters
                            }
                        ]
                    }))
                    return
    logger.bind(tag=TAG).error(f"未找到方法{method_name}")
