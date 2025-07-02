"""IoT设备描述符定义"""

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IotDescriptor:
    """IoT设备描述符"""

    def __init__(self, name, description, properties, methods):
        self.name = name
        self.description = description
        self.properties = []
        self.methods = []

        # 根据描述创建属性
        if properties is not None:
            for key, value in properties.items():
                property_item = {}
                property_item["name"] = key
                property_item["description"] = value["description"]
                if value["type"] == "number":
                    property_item["value"] = 0
                elif value["type"] == "boolean":
                    property_item["value"] = False
                else:
                    property_item["value"] = ""
                self.properties.append(property_item)

        # 根据描述创建方法
        if methods is not None:
            for key, value in methods.items():
                method = {}
                method["description"] = value["description"]
                method["name"] = key
                # 检查方法是否有参数
                if "parameters" in value:
                    method["parameters"] = {}
                    for k, v in value["parameters"].items():
                        method["parameters"][k] = {
                            "description": v["description"],
                            "type": v["type"],
                        }
                self.methods.append(method)
