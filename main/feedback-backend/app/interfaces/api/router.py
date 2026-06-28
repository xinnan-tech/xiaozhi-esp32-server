"""API 路由汇总"""

from fastapi import APIRouter

from .public_controller import router as public_router
from .store_controller import router as store_router
from .employee_controller import router as employee_router
from .feedback_controller import router as feedback_router
from .stats_controller import router as stats_router
from .agent_config_controller import router as agent_config_router
from .auth_controller import router as auth_router
from .crm_controller import router as crm_router
from .agent_chat_controller import router as agent_chat_router
from .appointment_controller import router as appointment_router
from .notification_controller import router as notification_router

api_router = APIRouter(prefix="/api/v1")

# 公开接口（无需认证）
api_router.include_router(public_router)

# 认证接口
api_router.include_router(auth_router)

# 后台管理接口（需要认证）
api_router.include_router(store_router)
api_router.include_router(employee_router)
api_router.include_router(feedback_router)
api_router.include_router(stats_router)
api_router.include_router(agent_config_router)
api_router.include_router(crm_router)
api_router.include_router(agent_chat_router)
api_router.include_router(appointment_router)
api_router.include_router(notification_router)
