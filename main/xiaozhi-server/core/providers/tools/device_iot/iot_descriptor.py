"""IoT device descriptor definition"""

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class IotDescriptor:
    """IoT device descriptor"""
    
    def __init__(self, name, description, properties, methods):
        self.name = name
        self.description = description
        self.properties = []
        self.methods = []
        
        # Create properties based on description
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
        
        # Create methods based on description
        if methods is not None:
            for key, value in methods.items():
                method = {}
                method["description"] = value["description"]
                method["name"] = key
                # Check if method has parameters
                if "parameters" in value:
                    method["parameters"] = {}
                    for k, v in value["parameters"].items():
                        method["parameters"][k] = {
                            "description": v["description"],
                            "type": v["type"],
                        }
                self.methods.append(method)
