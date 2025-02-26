import os
import sys
import asyncio
from typing import List, Dict, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

from config.logger import setup_logging
import importlib
from datetime import datetime
from core.utils.util import is_segment
from core.utils.util import get_string_no_punctuation_or_emoji
from core.utils.util import read_config, get_project_dir

TAG = __name__
logger = setup_logging()


def create_instance(class_name, *args, **kwargs):
    # 创建LLM实例
    if os.path.exists(os.path.join('core', 'providers', 'llm', class_name, f'{class_name}.py')):
        lib_name = f'core.providers.llm.{class_name}.{class_name}'
        logger.bind(tag=TAG).info(f"加载LLM模块: {lib_name}")
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f'{lib_name}')
        return sys.modules[lib_name].LLMProvider(*args, **kwargs)

    raise ValueError(f"不支持的LLM类型: {class_name}，请检查该配置的type是否设置正确")


async def test_single_model(llm_name: str, llm_config: Dict[str, Any], test_prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """异步测试单个模型"""
    try:
        # 获取实际的LLM类型
        llm_type = llm_config["type"] if "type" in llm_config else llm_name
        llm = create_instance(llm_type, llm_config)
        
        # 开始测试
        dialogue = []
        dialogue.append({"role": "system", "content": config.get("prompt")})
        dialogue.append({"role": "user", "content": test_prompt})
        
        start_time = datetime.now()
        llm_responses = llm.response("test", dialogue)
        response_message = []
        first_response_time = None
        total_response_time = None
        start = 0
        full_response = ""

        for content in llm_responses:
            response_message.append(content)
            full_response += content

            if is_segment(response_message):
                segment_text = "".join(response_message[start:])
                segment_text = get_string_no_punctuation_or_emoji(segment_text)
                if len(segment_text) > 0:
                    if first_response_time is None:
                        first_response_time = (datetime.now() - start_time).total_seconds()
                    start = len(response_message)

        total_response_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "name": llm_name,
            "type": llm_type,
            "first_response_time": first_response_time,
            "total_response_time": total_response_time,
            "response_length": len(full_response),
            "status": "成功",
            "response": full_response
        }

    except Exception as e:
        print(f"测试 {llm_name} 时发生错误: {str(e)}")
        return {
            "name": llm_name,
            "type": llm_config.get("type", llm_name),
            "first_response_time": None,
            "total_response_time": None,
            "response_length": 0,
            "status": f"失败 - {str(e)}",
            "response": ""
        }


async def main():
    """
    LLM模型响应速度测试和排行（异步版本）
    """
    config = read_config(get_project_dir() + "config.yaml")
    test_prompt = "你好小智"
    
    print("开始并发测试所有模型...")
    
    # 创建所有模型的测试任务
    tasks = []
    for llm_name, llm_config in config["LLM"].items():
        task = asyncio.create_task(test_single_model(llm_name, llm_config, test_prompt, config))
        tasks.append(task)
    
    # 等待所有测试完成
    test_results = await asyncio.gather(*tasks)
    
    # 打印测试结果排行榜
    print("\n========= LLM模型性能测试排行榜 =========")
    print("测试提示词:", test_prompt)
    
    # 过滤出成功的结果，并确保数值有效
    successful_results = [r for r in test_results if r["status"] == "成功" and r["first_response_time"] is not None]
    
    if successful_results:
        print("\n1. 首次响应时间排行:")
        sorted_by_first = sorted(successful_results, key=lambda x: x["first_response_time"])
        for i, result in enumerate(sorted_by_first, 1):
            print(f"{i}. {result['name']}({result['type']}) - {result['first_response_time']:.2f}秒")
            print(f"   响应内容: {result['response'][:50]}...")  # 只显示前50个字符

        print("\n2. 总响应时间排行:")
        sorted_by_total = sorted(successful_results, key=lambda x: x["total_response_time"] or float('inf'))
        for i, result in enumerate(sorted_by_total, 1):
            if result["total_response_time"] is not None:
                print(f"{i}. {result['name']}({result['type']}) - {result['total_response_time']:.2f}秒")

        print("\n3. 响应长度比较:")
        sorted_by_length = sorted(successful_results, key=lambda x: x["response_length"], reverse=True)
        for i, result in enumerate(sorted_by_length, 1):
            print(f"{i}. {result['name']}({result['type']}) - {result['response_length']}字符")
    else:
        print("\n没有成功完成测试的模型。")

    if len(test_results) != len(successful_results):
        print("\n测试失败的模型:")
        failed_results = [r for r in test_results if r["status"] != "成功" or r["first_response_time"] is None]
        for result in failed_results:
            print(f"- {result['name']}({result['type']}): {result['status']}")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
