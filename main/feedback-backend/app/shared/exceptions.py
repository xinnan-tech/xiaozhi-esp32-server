"""自定义异常体系"""


class FeedbackBaseException(Exception):
    """反馈系统基础异常"""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ---- 领域异常 ----

class StoreNotFoundError(FeedbackBaseException):
    """门店不存在"""

    def __init__(self, store_code: str):
        super().__init__(f"门店不存在: {store_code}", "STORE_NOT_FOUND")


class EmployeeNotFoundError(FeedbackBaseException):
    """员工不存在"""

    def __init__(self, employee_id: str):
        super().__init__(f"员工不存在: {employee_id}", "EMPLOYEE_NOT_FOUND")


class AgentConfigNotFoundError(FeedbackBaseException):
    """智能体配置不存在"""

    def __init__(self, agent_id: str):
        super().__init__(f"智能体配置不存在: {agent_id}", "AGENT_CONFIG_NOT_FOUND")


# ---- 应用异常 ----

class LLMProcessingError(FeedbackBaseException):
    """LLM 处理失败"""

    def __init__(self, detail: str):
        super().__init__(f"AI 处理失败: {detail}", "LLM_PROCESSING_ERROR")


class PromptTemplateError(FeedbackBaseException):
    """提示词模板错误"""

    def __init__(self, template_name: str, detail: str):
        super().__init__(f"提示词模板 {template_name} 错误: {detail}", "PROMPT_TEMPLATE_ERROR")


class RecordSaveError(FeedbackBaseException):
    """记录保存失败"""

    def __init__(self, detail: str):
        super().__init__(f"记录保存失败: {detail}", "RECORD_SAVE_ERROR")


# ---- 基础设施异常 ----

class DatabaseConnectionError(FeedbackBaseException):
    """数据库连接失败"""

    def __init__(self, detail: str):
        super().__init__(f"数据库连接失败: {detail}", "DATABASE_CONNECTION_ERROR")


class AuthenticationError(FeedbackBaseException):
    """认证失败"""

    def __init__(self, detail: str = "认证失败"):
        super().__init__(detail, "AUTHENTICATION_ERROR")


class AuthorizationError(FeedbackBaseException):
    """权限不足"""

    def __init__(self, detail: str = "权限不足"):
        super().__init__(detail, "AUTHORIZATION_ERROR")


# ---- 验证异常 ----

class ValidationError(FeedbackBaseException):
    """数据验证失败"""

    def __init__(self, detail: str):
        super().__init__(detail, "VALIDATION_ERROR")
