import requests
import json
import re
from typing import Dict, List, Optional, Union, Any

# 假设这些导入存在于项目中
try:
    from config.logger import setup_logging
    from plugins_func.register import register_function, ToolType, ActionResponse, Action
    from core.utils.util import get_ip_info
except ImportError:
    # 导入失败时的兼容处理
    print("警告: 部分模块导入失败，可能需要调整导入路径")

TAG = __name__

# 尝试设置日志
try:
    logger = setup_logging()
except:
    # 简单的日志后备方案
    import logging
    logger = logging.getLogger(TAG)
    logger.setLevel(logging.INFO)
    
    # 添加bind方法模拟structured logger
    def _bind(self, **kwargs):
        return self
    logger.bind = _bind.__get__(logger)
    
    # 添加debug/info/error方法的后备
    if not hasattr(logger, "error"):
        logger.error = logger.warning


# 简化函数描述定义，避免多行字符串语法错误
GET_PLACE_INFO_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_place_info",
        "description": "获取附近的商铺信息。基于用户位置(自动获取IP或用户指定)搜索附近商铺、餐厅、景点。例如用户说'附近有什么好吃的'或'杭州西湖附近有什么景点'。",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "地点名，例如杭州。可选参数，如果不提供则通过IP定位，如果没有指定特定的地点，例如街道，城市，乡村等；那就直接返回附近"
                },
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，例如餐厅、咖啡厅、景点等"
                },
                "radius": {
                    "type": "integer",
                    "description": "搜索半径，默认1000米"
                },
                "lang": {
                    "type": "string",
                    "description": "返回用户使用的语言code，例如zh_CN/zh_HK/en_US/ja_JP等，默认zh_CN"
                }
            },
            "required": ["keyword", "lang"]
        }
    }
}


class PlaceSearchService:
    """
    场所搜索服务类，封装根据IP获取经纬度和搜索附近店铺的功能
    """
    
    def __init__(self, api_key):
        """
        初始化场所搜索服务
        
        Args:
            api_key: 高德地图API密钥
        """
        self.api_key = "1ba9b66a094a5a86b22e6c7425a4f33b"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
            ),
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    
    def get_location_by_ip(self, client_ip):
        """
        根据IP地址获取城市信息
        
        Args:
            client_ip: 客户端IP地址
            
        Returns:
            dict: 包含城市等信息的字典
        """
        try:
            ip_info = get_ip_info(client_ip, logger)
            return ip_info
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取IP信息失败: {e}")
            return {}
    
    def get_location_by_name(self, location_name):
        """
        根据地点名称获取该地点的地理编码(经纬度等信息)
        
        Args:
            location_name: 地点名称
            
        Returns:
            dict: 地点信息字典，包含经纬度等
        """
        url = f"https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": self.api_key,
            "address": location_name,
            "output": "json",
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            if data.get("status") == "1" and data.get("geocodes") and len(data["geocodes"]) > 0:
                return {
                    "location": data["geocodes"][0]["location"],  # 格式："116.481488,39.990464"
                    "formatted_address": data["geocodes"][0]["formatted_address"],
                    "province": data["geocodes"][0]["province"],
                    "city": data["geocodes"][0]["city"],
                    "district": data["geocodes"][0]["district"]
                }
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取地点经纬度失败: {e}")
        
        return None
    
    def search_places_by_keyword(self, lng, lat, keyword, radius=1000, page=1, page_size=20):
        """
        根据经纬度和关键词搜索附近场所
        
        Args:
            lng: 经度
            lat: 纬度
            keyword: 搜索关键词
            radius: 搜索半径，单位米
            page: 页码，从1开始
            page_size: 每页结果数
            
        Returns:
            list: 场所信息列表
        """
        url = "https://restapi.amap.com/v3/place/around"
        params = {
            "key": self.api_key,
            "location": f"{lng},{lat}",
            "keywords": keyword,
            "radius": str(radius),
            "offset": str(page_size),
            "page": str(page),
            "extensions": "all",
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            if data.get("status") == "1":
                return data.get("pois", [])
        except Exception as e:
            logger.bind(tag=TAG).error(f"搜索附近场所失败: {e}")
        
        return []
    
    def search_places_by_city(self, city_name, keyword, page=1, page_size=20):
        """
        根据城市名和关键词搜索场所
        
        Args:
            city_name: 城市名称
            keyword: 搜索关键词
            page: 页码
            page_size: 每页结果数
            
        Returns:
            list: 场所信息列表
        """
        url = "http://restapi.amap.com/v3/place/text"
        params = {
            "key": self.api_key,
            "keywords": keyword,
            "city": city_name,
            "citylimit": "true",
            "offset": str(page_size),
            "page": str(page),
            "extensions": "all",
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            if data.get("status") == "1":
                return data.get("pois", [])
        except Exception as e:
            logger.bind(tag=TAG).error(f"搜索城市内场所失败: {e}")
        
        return []
    
    def format_search_results(self, pois, location_desc=""):
        """
        格式化搜索结果为可读的文本
        
        Args:
            pois: POI数据列表
            location_desc: 位置描述
            
        Returns:
            str: 格式化后的结果文本
        """
        if not pois:
            return f"抱歉，在{location_desc}附近没有找到符合条件的场所。"
        
        result = f"在{location_desc}附近找到以下场所：\n\n"
        
        for index, poi in enumerate(pois[:10], 1):  # 最多显示10个结果
            name = poi.get("name", "未知场所")
            address = poi.get("address", "地址未知")
            distance = poi.get("distance", "")
            distance_text = f"距离约{distance}米" if distance else ""
            rating = poi.get("biz_ext", {}).get("rating", "") if "biz_ext" in poi else ""
            rating_text = f"，评分{rating}" if rating else ""
            tel = poi.get("tel", "")
            tel_text = f"，电话：{tel}" if tel else ""
            
            result += f"{index}. {name}\n   {address}\n   {distance_text}{rating_text}{tel_text}\n\n"
        
        if len(pois) > 10:
            result += f"共找到{len(pois)}个结果，仅显示前10个。\n"
        
        result += "如需了解更多信息，请告诉我具体的场所名称。"
        return result


def is_nearby_query(query: str) -> bool:
    """
    判断用户查询是否是关于"附近"的查询
    
    Args:
        query: 用户查询文本
        
    Returns:
        bool: 是否是附近查询
    """
    nearby_patterns = [
        r'附近',
        r'我附近',
        r'周边',
        r'我周边',
        r'周围',
        r'我周围',
        r'就近',
        r'身边',
        r'我身边'
    ]
    
    # 检查查询中是否包含"附近"相关的词语
    for pattern in nearby_patterns:
        if re.search(pattern, query):
            return True
    
    return False


def is_vague_location(location: str) -> bool:
    """
    判断location是否是模糊位置词
    
    Args:
        location: 位置字符串
        
    Returns:
        bool: 是否是模糊位置词
    """
    if not location:
        return False
        
    vague_locations = [
        '附近', '周边', '周围', '身边', '就近', 
        '这里', '这儿', '这边', '我这里', '我这儿', '我这边',
        '当前位置', '我当前位置', '我的位置', '当前地点'
    ]
    
    # 精确匹配这些模糊词
    if location.strip() in vague_locations:
        return True
    
    return False


def parse_location_from_query(query: str) -> Optional[str]:
    """
    从查询中解析出具体的位置名称
    
    Args:
        query: 用户查询文本
        
    Returns:
        Optional[str]: 解析出的位置名称，如果没有则为None
    """
    # 如果是纯粹的"附近"查询，不包含具体位置名称
    if is_nearby_query(query) and not re.search(r'[在于]([\u4e00-\u9fa5a-zA-Z0-9]+)(附近|周边|周围)', query):
        return None
    
    # 尝试匹配"XX附近"模式
    location_match = re.search(r'([在于]?)([^在于]{2,}?)(附近|周边|周围)', query)
    if location_match and location_match.group(2):
        return location_match.group(2).strip()
    
    return None


try:
    @register_function("get_place_info", GET_PLACE_INFO_FUNCTION_DESC, ToolType.SYSTEM_CTL)
    def get_place_info(conn, location: str = None, keyword: str = "餐厅", radius: int = 1000, lang: str = "zh_CN"):
        """
        获取附近场所信息的函数
        
        Args:
            conn: 连接对象
            location: 地点名称，可选
            keyword: 搜索关键词，默认为"餐厅"
            radius: 搜索半径，默认1000米
            lang: 语言代码，默认zh_CN
            
        Returns:
            ActionResponse: 动作响应对象
        """
        # 获取配置中的高德地图API密钥
        api_key = "1ba9b66a094a5a86b22e6c7425a4f33b"#conn.config["plugins"].get("get_place_info", {}).get("api_key", "")
        default_city = "上海"
        
        # 检查API密钥是否存在
        if not api_key:
            return ActionResponse(
                Action.REQLLM, "抱歉，未配置高德地图API密钥，无法获取位置信息。", None
            )
        
        # 获取用户原始查询，用于判断是否是"附近"查询
        user_query = conn.get_last_user_message() if hasattr(conn, "get_last_user_message") else ""
        
        # 判断是否是纯粹的"附近"查询
        if user_query and is_nearby_query(user_query) and not parse_location_from_query(user_query):
            # 对于纯粹的"附近"查询，强制将location设为None
            location = None
        
        # 检查location是否为模糊位置词（"附近"等），如果是则设为None
        if location and is_vague_location(location):
            location = None
        
        # 初始化场所搜索服务
        place_service = PlaceSearchService(api_key)
        client_ip = conn.client_ip
        
        # 1. 优先使用用户提供的location参数
        if location:
            # 获取位置的地理编码信息
            geo_info = place_service.get_location_by_name(location)
            if not geo_info:
                return ActionResponse(
                    Action.REQLLM, f"抱歉，无法找到位置：{location}，请提供更准确的位置信息。", None
                )
            
            # 解析经纬度
            lng, lat = geo_info["location"].split(",")
            location_desc = geo_info["formatted_address"]
            
            # 搜索附近场所
            places = place_service.search_places_by_keyword(lng, lat, keyword, radius)
            
        # 2. 如果没有提供location，尝试通过IP地址定位
        elif client_ip:
            # 获取IP对应的城市信息
            ip_info = place_service.get_location_by_ip(client_ip)
            city_name = ip_info.get("city") if ip_info and "city" in ip_info else default_city
            
            if not city_name:
                city_name = default_city
            
            # 根据城市名搜索场所
            places = place_service.search_places_by_city(city_name, keyword)
            location_desc = city_name
            
        # 3. 兜底：使用默认城市
        else:
            places = place_service.search_places_by_city(default_city, keyword)
            location_desc = default_city
        
        # 格式化搜索结果
        result_text = place_service.format_search_results(places, location_desc)
        
        return ActionResponse(Action.REQLLM, result_text, None)
except Exception as e:
    # 捕获注册函数可能的异常
    print(f"注册get_place_info函数失败: {e}") 
