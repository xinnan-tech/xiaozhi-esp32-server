import requests
import sys
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

# 定义基础的函数描述模板
SEARCH_FROM_RAGFLOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_from_ragflow",
        "description": "从知识库中查询信息",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "查询的问题"}},
            "required": ["question"],
        },
    },
}


@register_function(
    "search_from_ragflow", SEARCH_FROM_RAGFLOW_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def search_from_ragflow(conn: "ConnectionHandler", question=None):
    # 确保字符串参数正确处理编码
    if question and isinstance(question, str):
        # 确保问题参数是UTF-8编码的字符串
        pass
    else:
        question = str(question) if question is not None else ""

    ragflow_config = conn.config.get("plugins", {}).get("search_from_ragflow", {})
    base_url = ragflow_config.get("base_url", "")
    api_key = ragflow_config.get("api_key", "")
    dataset_ids = ragflow_config.get("dataset_ids", [])

    url = base_url + "/api/v1/retrieval"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # 确保payload中的字符串都是UTF-8编码
    payload = {"question": question, "dataset_ids": dataset_ids}

    try:
        # 使用ensure_ascii=False确保JSON序列化时正确处理中文
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=5,
            verify=False,
        )

        # 显式设置响应的编码为utf-8
        response.encoding = "utf-8"

        response.raise_for_status()

        # 先获取文本内容，然后手动处理JSON解码
        response_text = response.text
        import json

        result = json.loads(response_text)

        if result.get("code") != 0:
            error_detail = result.get("error", {}).get("detail", "未知错误")
            error_message = result.get("error", {}).get("message", "")
            error_code = result.get("code", "")

            # 安全地记录错误信息
            logger.bind(tag=TAG).error(
                f"RAGFlow API调用失败，响应码：{error_code}，错误详情：{error_detail}，完整响应：{result}"
            )

            # 构建详细的错误响应
            error_response = f"RAG接口返回异常（错误码：{error_code}）"

            if error_message:
                error_response += f"：{error_message}"
            if error_detail:
                error_response += f"\n详情：{error_detail}"

            return ActionResponse(Action.RESPONSE, None, error_response)

        chunks = result.get("data", {}).get("chunks", [])
        contents = []
        for chunk in chunks:
            content = chunk.get("content", "")
            if content:
                # 安全地处理内容字符串
                if isinstance(content, str):
                    contents.append(content)
                elif isinstance(content, bytes):
                    contents.append(content.decode("utf-8", errors="replace"))
                else:
                    contents.append(str(content))

        if contents:
            # 组织知识库内容为引用模式
            context_text = f"# 关于问题【{question}】查到知识库如下\n"
            context_text += "```\n\n\n".join(contents[:5])
            context_text += "\n```"
        else:
            context_text = "根据知识库查询结果，没有相关信息。"
        return ActionResponse(Action.REQLLM, context_text, None)

    except requests.exceptions.RequestException as e:
        # 网络请求异常
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGflow网络请求失败，异常类型：{error_type}，详情：{str(e)}"
        )

        # 根据异常类型提供更详细的错误信息和解决方案
        if isinstance(e, requests.exceptions.ConnectTimeout):
            error_response = "RAG接口连接超时（5秒）"
            error_response += "\n可能原因：RAGflow服务未启动或网络连接问题"
            error_response += "\n解决方案：请检查RAGflow服务状态和网络连接"

        elif isinstance(e, requests.exceptions.ConnectionError):
            error_response = "无法连接到RAG接口"
            error_response += "\n可能原因：RAGflow服务地址错误或服务未运行"
            error_response += "\n解决方案：请检查RAGflow服务地址配置和服务状态"

        elif isinstance(e, requests.exceptions.Timeout):
            error_response = "RAG接口请求超时"
            error_response += "\n可能原因：RAGflow服务响应缓慢或网络延迟"
            error_response += "\n解决方案：请稍后重试或检查RAGflow服务性能"

        elif isinstance(e, requests.exceptions.HTTPError):
            # 处理HTTP错误状态码
            if hasattr(e.response, "status_code"):
                status_code = e.response.status_code
                error_response = f"RAG接口HTTP错误（状态码：{status_code}）"

                # 尝试获取响应内容中的错误信息
                try:
                    error_detail = e.response.json().get("error", {}).get("message", "")
                    if error_detail:
                        error_response += f"\n错误详情：{error_detail}"
                except:
                    pass
            else:
                error_response = f"RAG接口HTTP异常：{str(e)}"

        else:
            error_response = f"RAG接口网络异常（{error_type}）：{str(e)}"

        return ActionResponse(Action.RESPONSE, None, error_response)

    except Exception as e:
        # 其他异常
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGflow处理异常，异常类型：{error_type}，详情：{str(e)}"
        )

        # 提供详细的错误信息
        error_response = f"RAG接口处理异常（{error_type}）：{str(e)}"
        return ActionResponse(Action.RESPONSE, None, error_response)
