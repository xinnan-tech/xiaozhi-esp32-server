#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试PlaceSearchService类的功能
"""

import os
import sys
import json

# 添加项目根目录到PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 创建一个简化版的PlaceSearchService类，不依赖项目的logger等组件
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
        self.api_key = api_key
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
            # 公共API，获取IP地址的位置信息
            url = f"https://whois.pconline.com.cn/ipJson.jsp?json=true&ip={client_ip}"
            import requests
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return {
                    "city": data.get("city", ""),
                    "province": data.get("pro", ""),
                    "ip": client_ip
                }
        except Exception as e:
            print(f"获取IP信息出错: {e}")
        return {"city": "", "province": "", "ip": client_ip}
    
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
            import requests
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            print(f"地理编码API响应: {json.dumps(data, ensure_ascii=False)}")
            
            if data.get("status") == "1" and data.get("geocodes") and len(data["geocodes"]) > 0:
                return {
                    "location": data["geocodes"][0]["location"],  # 格式："116.481488,39.990464"
                    "formatted_address": data["geocodes"][0]["formatted_address"],
                    "province": data["geocodes"][0]["province"],
                    "city": data["geocodes"][0]["city"],
                    "district": data["geocodes"][0]["district"]
                }
            elif data.get("status") == "0":
                print(f"API返回错误: {data.get('info')}")
        except Exception as e:
            print(f"获取地点经纬度失败: {e}")
        
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
        
        print(f"请求附近场所API: {url}")
        print(f"参数: {params}")
        
        try:
            import requests
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            print(f"附近场所API响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")
            
            if data.get("status") == "1":
                return data.get("pois", [])
            elif data.get("status") == "0":
                print(f"API返回错误: {data.get('info')}")
        except Exception as e:
            print(f"搜索附近场所失败: {e}")
        
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
            import requests
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            if data.get("status") == "1":
                return data.get("pois", [])
        except Exception as e:
            print(f"搜索城市内场所失败: {e}")
        
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

def test_get_location_by_name():
    """测试根据地名获取位置信息"""
    # 从环境变量或配置文件获取API密钥
    api_key = os.environ.get("GD_KEY", "你的高德地图API密钥")  # 替换为实际的API密钥
    
    service = PlaceSearchService(api_key)
    location = "杭州西湖"
    result = service.get_location_by_name(location)
    
    print(f"\n=== 测试根据地名获取位置信息 ===")
    print(f"位置名称: {location}")
    
    if result:
        print(f"获取成功!")
        print(f"格式化地址: {result.get('formatted_address')}")
        print(f"经纬度: {result.get('location')}")
        print(f"省份: {result.get('province')}")
        print(f"城市: {result.get('city')}")
        print(f"区县: {result.get('district')}")
    else:
        print(f"获取位置信息失败")

def test_search_places_by_keyword():
    """测试根据经纬度和关键词搜索场所"""
    api_key = os.environ.get("GD_KEY", "你的高德地图API密钥")  # 替换为实际的API密钥
    
    service = PlaceSearchService(api_key)
    # 杭州西湖的经纬度
    lng, lat = 120.14, 30.24
    keyword = "咖啡厅"
    radius = 1000
    
    print(f"\n=== 测试根据经纬度搜索场所 ===")
    print(f"位置: 经度={lng}, 纬度={lat}")
    print(f"关键词: {keyword}")
    print(f"半径: {radius}米")
    
    places = service.search_places_by_keyword(lng, lat, keyword, radius)
    
    if places:
        print(f"搜索成功! 找到{len(places)}个结果")
        result_text = service.format_search_results(places, "杭州西湖")
        print(result_text)
    else:
        print("搜索场所失败或未找到结果")

def test_search_places_by_city():
    """测试根据城市名和关键词搜索场所"""
    api_key = os.environ.get("GD_KEY", "你的高德地图API密钥")  # 替换为实际的API密钥
    
    service = PlaceSearchService(api_key)
    city = "北京"
    keyword = "火锅"
    
    print(f"\n=== 测试根据城市名搜索场所 ===")
    print(f"城市: {city}")
    print(f"关键词: {keyword}")
    
    places = service.search_places_by_city(city, keyword)
    
    if places:
        print(f"搜索成功! 找到{len(places)}个结果")
        result_text = service.format_search_results(places, city)
        print(result_text)
    else:
        print("搜索场所失败或未找到结果")

def test_get_location_by_ip():
    """测试根据IP地址获取位置信息"""
    api_key = os.environ.get("GD_KEY", "你的高德地图API密钥")  # 替换为实际的API密钥
    
    service = PlaceSearchService(api_key)
    # 随便一个IP地址，这里使用百度的公共DNS
    ip = "180.76.76.76"
    
    print(f"\n=== 测试根据IP地址获取位置信息 ===")
    print(f"IP地址: {ip}")
    
    result = service.get_location_by_ip(ip)
    
    print(f"位置信息: {json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    print("开始测试PlaceSearchService类...")
    
    # 可以选择单独运行某个测试或全部测试
    test_get_location_by_ip()
    os.environ["GD_KEY"] = "1ba9b66a094a5a86b22e6c7425a4f33b"
    # 如果有设置API密钥，再测试需要密钥的功能
    if os.environ.get("GD_KEY"):
        test_get_location_by_name()
        test_search_places_by_keyword()
        test_search_places_by_city()
    else:
        print("\n注意: 未设置GD_KEY环境变量，跳过需要API密钥的测试")
        print("请设置环境变量 GD_KEY=你的高德地图API密钥 再运行完整测试")
    
    print("\n测试完成!") 