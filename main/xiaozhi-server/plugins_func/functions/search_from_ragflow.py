import requests
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

SEARCH_FROM_RAGFLOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_from_ragflow",
        "description": "Search information from the knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The question to query."}},
            "required": ["question"],
        },
    },
}


@register_function(
    "search_from_ragflow", SEARCH_FROM_RAGFLOW_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def search_from_ragflow(conn: "ConnectionHandler", question=None):
    if question and isinstance(question, str):
        pass
    else:
        question = str(question) if question is not None else ""

    ragflow_config = conn.config.get("plugins", {}).get("search_from_ragflow", {})
    base_url = ragflow_config.get("base_url", "")
    api_key = ragflow_config.get("api_key", "")
    dataset_ids = ragflow_config.get("dataset_ids", [])

    url = base_url + "/api/v1/retrieval"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {"question": question, "dataset_ids": dataset_ids}

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=5,
            verify=False,
        )

        response.encoding = "utf-8"

        response.raise_for_status()

        response_text = response.text

        result = json.loads(response_text)

        if result.get("code") != 0:
            error_detail = result.get("error", {}).get("detail", "Unknown error")
            error_message = result.get("error", {}).get("message", "")
            error_code = result.get("code", "")

            logger.bind(tag=TAG).error(
                f"RAGFlow API call failed. Code: {error_code}, detail: {error_detail}, response: {result}"
            )

            error_response = f"RAG endpoint returned an error (code: {error_code})"

            if error_message:
                error_response += f": {error_message}"
            if error_detail:
                error_response += f"\nDetails: {error_detail}"

            return ActionResponse(Action.RESPONSE, None, error_response)

        chunks = result.get("data", {}).get("chunks", [])
        contents = []
        for chunk in chunks:
            content = chunk.get("content", "")
            if content:
                if isinstance(content, str):
                    contents.append(content)
                elif isinstance(content, bytes):
                    contents.append(content.decode("utf-8", errors="replace"))
                else:
                    contents.append(str(content))

        if contents:
            context_text = f"# Knowledge base results for [{question}]\n"
            context_text += "```\n\n\n".join(contents[:5])
            context_text += "\n```"
        else:
            context_text = "No relevant information was found in the knowledge base."
        return ActionResponse(Action.REQLLM, context_text, None)

    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGFlow network request failed. Type: {error_type}, detail: {str(e)}"
        )

        if isinstance(e, requests.exceptions.ConnectTimeout):
            error_response = "RAG endpoint connection timed out (5 seconds)"
            error_response += "\nPossible cause: the RAGFlow service is not running or the network is unstable"
            error_response += "\nSuggested action: check the RAGFlow service status and network connection"

        elif isinstance(e, requests.exceptions.ConnectionError):
            error_response = "Unable to connect to the RAG endpoint"
            error_response += "\nPossible cause: the RAGFlow service address is incorrect or the service is not running"
            error_response += "\nSuggested action: check the RAGFlow service address configuration and status"

        elif isinstance(e, requests.exceptions.Timeout):
            error_response = "RAG endpoint request timed out"
            error_response += "\nPossible cause: the RAGFlow service is slow or the network has high latency"
            error_response += "\nSuggested action: try again later or check the RAGFlow service performance"

        elif isinstance(e, requests.exceptions.HTTPError):
            if hasattr(e.response, "status_code"):
                status_code = e.response.status_code
                error_response = f"RAG endpoint HTTP error (status code: {status_code})"

                try:
                    error_detail = e.response.json().get("error", {}).get("message", "")
                    if error_detail:
                        error_response += f"\nError details: {error_detail}"
                except:
                    pass
            else:
                error_response = f"RAG endpoint HTTP exception: {str(e)}"

    except httpx.HTTPStatusError as e:
        if hasattr(e.response, "status_code"):
            status_code = e.response.status_code
            error_response = f"RAG interface HTTP error (status code: {status_code})"
            try:
                error_detail = e.response.json().get("error", {}).get("message", "")
                if error_detail:
                    error_response += f"\n Error details: {error_detail}"
            except:
                pass
        else:
            error_response = f"RAG endpoint network exception ({error_type}): {str(e)}"

    except httpx.HTTPError as e:
        error_response = "Unable to connect to RAG interface"
        error_response += "\nPossible causes: Incorrect RAGflow service address or service not running"
        error_response += "\n Solution: Check RAGflow service address config and service status"
        return ActionResponse(Action.RESPONSE, None, error_response)

    except Exception as e:
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGFlow processing exception. Type: {error_type}, detail: {str(e)}"
        )

        error_response = f"RAG endpoint processing exception ({error_type}): {str(e)}"
        return ActionResponse(Action.RESPONSE, None, error_response)
