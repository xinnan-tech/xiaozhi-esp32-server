import requests
import sys
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

# Define the base function description template
SEARCH_FROM_RAGFLOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_from_ragflow",
        "description": "Query information from the knowledge base",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The question to query"}},
            "required": ["question"],
        },
    },
}


@register_function(
    "search_from_ragflow", SEARCH_FROM_RAGFLOW_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def search_from_ragflow(conn, question=None):
    # Ensure string parameters handle encoding correctly
    if question and isinstance(question, str):
        # Ensure question parameter is a UTF-8 encoded string
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
        # Use ensure_ascii=False to ensure correct handling of non-ASCII characters during JSON serialization
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=5,
            verify=False,
        )

        # Explicitly set response encoding to utf-8
        response.encoding = "utf-8"

        response.raise_for_status()

        # Get content first, then manually handle JSON decoding
        response_text = response.text
        import json

        result = json.loads(response_text)

        if result.get("code") != 0:
            error_detail = result.get("error", {}).get("detail", "Unknown error")
            error_message = result.get("error", {}).get("message", "")
            error_code = result.get("code", "")

            # Log error details safely
            logger.bind(tag=TAG).error(
                f"RAGFlow API call failed, code: {error_code}, detail: {error_detail}, response: {result}"
            )

            # Build detailed error response
            error_response = f"RAG interface returned exception (Error code: {error_code})"

            if error_message:
                error_response += f": {error_message}"
            if error_detail:
                error_response += f"\nDetail: {error_detail}"

            return ActionResponse(Action.RESPONSE, None, error_response)

        chunks = result.get("data", {}).get("chunks", [])
        contents = []
        for chunk in chunks:
            content = chunk.get("content", "")
            if content:
                # Handle content string safely
                if isinstance(content, str):
                    contents.append(content)
                elif isinstance(content, bytes):
                    contents.append(content.decode("utf-8", errors="replace"))
                else:
                    contents.append(str(content))

        if contents:
            # Organize knowledge base content into citation mode
            context_text = f"# Knowledge base results for [{question}]\n"
            context_text += "```\n\n\n".join(contents[:5])
            context_text += "\n```"
        else:
            context_text = "No relevant information found in the knowledge base."
        return ActionResponse(Action.REQLLM, context_text, None)

    except requests.exceptions.RequestException as e:
        # Network request exception
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGFlow network request failed, type: {error_type}, detail: {str(e)}"
        )

        # Provide more detailed error info based on exception type
        if isinstance(e, requests.exceptions.ConnectTimeout):
            error_response = "RAG interface connection timeout (5 seconds)"
            error_response += "\nPossible cause: RAGFlow service not started or network issues"
            error_response += "\nSolution: Please check RAGFlow service status and network connection"

        elif isinstance(e, requests.exceptions.ConnectionError):
            error_response = "Unable to connect to RAG interface"
            error_response += "\nPossible cause: RAGFlow service address error or service not running"
            error_response += "\nSolution: Please check RAGFlow service address configuration and service status"

        elif isinstance(e, requests.exceptions.Timeout):
            error_response = "RAG interface request timeout"
            error_response += "\nPossible cause: RAGFlow service responding slowly or network latency"
            error_response += "\nSolution: Please try again later or check RAGFlow service performance"

        elif isinstance(e, requests.exceptions.HTTPError):
            # Handle HTTP error status codes
            if hasattr(e.response, "status_code"):
                status_code = e.response.status_code
                error_response = f"RAG interface HTTP error (Status code: {status_code})"

                # Attempt to get error info from response content
                try:
                    error_detail = e.response.json().get("error", {}).get("message", "")
                    if error_detail:
                        error_response += f"\nError detail: {error_detail}"
                except:
                    pass
            else:
                error_response = f"RAG interface HTTP exception: {str(e)}"

        else:
            error_response = f"RAG interface network exception ({error_type}): {str(e)}"

        return ActionResponse(Action.RESPONSE, None, error_response)

    except Exception as e:
        # Other exceptions
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGFlow processing exception, type: {error_type}, detail: {str(e)}"
        )

        # Provide detailed error info
        error_response = f"RAG interface processing exception ({error_type}): {str(e)}"
        return ActionResponse(Action.RESPONSE, None, error_response)
