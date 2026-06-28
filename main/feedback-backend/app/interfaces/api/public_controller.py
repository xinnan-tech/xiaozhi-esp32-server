"""公开接口控制器 - H5 前端调用，无需认证"""

from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.application.appointment_service import AppointmentService
from app.application.employee_service import EmployeeService
from app.application.feedback_service import FeedbackService
from app.application.store_service import StoreService
from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import AdminNotificationModel, CrmAppointmentModel, CrmMemberModel, CrmMemberProductModel, CrmProductModel
from app.shared.config import settings
from app.shared.exceptions import StoreNotFoundError, LLMProcessingError
from app.shared.utils import generate_id

router = APIRouter(prefix="/public", tags=["公开接口"])


# ---- Request Models (兼容 H5 前端 camelCase 字段名) ----

class ProcessFeedbackRequest(BaseModel):
    """AI 处理反馈请求 - 字段名与 H5 前端完全一致"""
    storeName: str = Field(..., description="门店名称")
    employeeNumber: str = Field(..., description="技师工号")
    asrText: str = Field(..., description="原始 ASR 文本")
    sessionId: Optional[str] = Field(None, description="WebSocket 会话 ID")
    deviceMac: Optional[str] = Field(None, description="设备 MAC 地址")
    clientId: Optional[str] = Field(None, description="客户端 ID")
    satisfaction: Optional[str] = Field(None, description="满意度")
    storeId: Optional[str] = Field(None, description="门店 ID")
    employeeId: Optional[str] = Field(None, description="员工 ID")
    customerName: Optional[str] = Field(None, description="客户称呼/自报姓名")
    phoneTail: Optional[str] = Field(None, description="手机号后四位")


class SaveRecordRequest(BaseModel):
    """保存反馈记录请求 - 字段名与 H5 前端完全一致"""
    model_config = ConfigDict(populate_by_name=True)

    storeId: Optional[str] = Field(default=None, description="门店 ID")
    employeeId: Optional[str] = Field(default=None, description="员工 ID")
    sessionId: Optional[str] = Field(default=None, description="会话 ID")
    deviceMac: Optional[str] = Field(default=None, description="设备 MAC")
    rawAsrText: Optional[str] = Field(default=None, description="原始 ASR 文本")
    cleanedText: Optional[str] = Field(default=None, description="清洗后文本")
    qaJson: Optional[str] = Field(default=None, description="QA JSON")
    reviewLong: Optional[str] = Field(default=None, description="标准点评")
    reviewShort: Optional[str] = Field(default=None, description="精简短评")
    satisfaction: Optional[str] = Field(default=None, description="满意度")
    customerName: Optional[str] = Field(default=None, description="客户称呼/自报姓名")
    phoneTail: Optional[str] = Field(default=None, description="手机号后四位")


class PublicAppointmentActionRequest(BaseModel):
    """公开预约取消/改约请求"""
    storeCode: str
    customerPhone: str
    appointmentId: Optional[str] = None
    employeeId: Optional[str] = None
    startAt: Optional[str] = None
    durationMinutes: int = 60
    reason: Optional[str] = None


class PublicAppointmentBookRequest(BaseModel):
    """公开预约提交请求"""
    storeCode: str
    employeeId: str
    startAt: str
    durationMinutes: int = 60
    customerName: Optional[str] = None
    customerPhone: str
    memberProductId: Optional[str] = None
    productId: Optional[str] = None
    serviceName: Optional[str] = None
    notes: Optional[str] = None


def _appointment_notify(session: Session, store_id: str, title: str, content: str, appointment_id: Optional[str] = None):
    session.add(AdminNotificationModel(
        id=generate_id(),
        store_id=store_id,
        title=title,
        content=content,
        notification_type="appointment",
        target_route="crm:appointments",
        target_id=appointment_id,
    ))


class DeviceInitRequest(BaseModel):
    """设备初始化请求 - 兼容 H5 前端两种传参方式"""
    model_config = ConfigDict(populate_by_name=True)

    storeId: Optional[str] = Field(default=None, description="门店 ID (H5 旧版)")
    employeeId: Optional[str] = Field(default=None, description="员工 ID (H5 旧版)")
    storeCode: Optional[str] = Field(default=None, description="门店编码 (新版)")
    deviceMac: Optional[str] = Field(default=None, description="设备 MAC")

    # 兼容 Pydantic V2：至少提供 storeId 或 storeCode 之一
    # 不设 required，在 endpoint 中手动校验


# ---- Endpoints ----

@router.get("/store/{store_code}")
async def get_store_by_code(
    store_code: str,
    session: Session = Depends(get_session),
):
    """根据门店编码获取门店信息（扫码入口）"""
    service = StoreService(session)
    try:
        store = await service.get_by_store_code(store_code)
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "id": store.id,
                "storeCode": store.store_code,
                "storeName": store.store_name,
                "manager": store.manager,
                "shareholders": store.shareholders,
                "agentId": store.agent_id,
            },
        }
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}


@router.get("/employees/{store_id}")
async def get_employees_by_store(
    store_id: str,
    session: Session = Depends(get_session),
):
    """获取门店下所有员工"""
    service = EmployeeService(session)
    employees = await service.list_by_store_id(store_id, status=1)
    return {
        "code": 0,
        "msg": "success",
        "data": [
            {
                "id": e.id,
                "name": e.name,
                "number": e.number,
                "employeeType": e.employee_type,
            }
            for e in employees
        ],
    }


@router.get("/appointment/bootstrap")
async def public_appointment_bootstrap(
    storeCode: str,
    date: Optional[str] = None,
    durationMinutes: int = 60,
    session: Session = Depends(get_session),
):
    """公开预约页初始化：门店、技师、当天空闲档期一次返回。"""
    store_service = StoreService(session)
    try:
        store = await store_service.get_by_store_code(storeCode)
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}

    day = date or datetime.now().date().isoformat()
    appointment_service = AppointmentService(session)
    availability = await appointment_service.availability(store.id, day, None, durationMinutes)
    employees = await EmployeeService(session).list_by_store_id(store.id, status=1)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "serverTime": datetime.now().isoformat(sep=" ", timespec="seconds"),
            "date": day,
            "durationMinutes": durationMinutes,
            "store": {
                "id": store.id,
                "storeCode": store.store_code,
                "storeName": store.store_name,
                "manager": store.manager,
            },
            "employees": [
                {"id": e.id, "name": e.name, "number": e.number, "employeeType": e.employee_type}
                for e in employees
            ],
            "availability": availability,
        },
    }


@router.get("/appointment/availability")
async def public_appointment_availability(
    storeCode: str,
    date: str,
    employeeId: Optional[str] = None,
    durationMinutes: int = 60,
    session: Session = Depends(get_session),
):
    """公开查询预约空档。"""
    try:
        store = await StoreService(session).get_by_store_code(storeCode)
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}
    data = await AppointmentService(session).availability(store.id, date, employeeId, durationMinutes)
    return {"code": 0, "msg": "success", "data": data}


@router.get("/appointment/member-products")
async def public_appointment_member_products(
    storeCode: str,
    phone: str,
    session: Session = Depends(get_session),
):
    """根据手机号查询客户已购项目/套餐，用于预约选择项目。"""
    try:
        store = await StoreService(session).get_by_store_code(storeCode)
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}
    phone = (phone or "").strip()
    if len(phone) < 7:
        return {"code": 400, "msg": "请填写有效手机号", "data": None}
    member = session.query(CrmMemberModel).filter(
        CrmMemberModel.store_id == store.id,
        CrmMemberModel.phone == phone,
        CrmMemberModel.status == 1,
    ).first()
    if not member:
        return {"code": 404, "msg": "未查询到该手机号的客户档案，请联系门店添加后再预约", "data": {"member": None, "products": []}}

    rows = session.query(CrmMemberProductModel).filter(
        CrmMemberProductModel.store_id == store.id,
        CrmMemberProductModel.member_id == member.id,
        CrmMemberProductModel.status == 1,
    ).order_by(CrmMemberProductModel.create_date.desc()).all()
    products = []
    for p in rows:
        product = session.query(CrmProductModel).filter(CrmProductModel.id == p.product_id).first() if p.product_id else None
        products.append({
            "id": p.id,
            "memberProductId": p.id,
            "productId": p.product_id,
            "productName": p.product_name,
            "durationMinutes": product.duration_minutes if product else 60,
            "balanceCount": p.balance_count or 0,
            "balanceAmount": float(p.balance_amount or 0),
            "validEnd": str(p.valid_end) if p.valid_end else None,
        })
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "member": {"id": member.id, "name": member.name, "phone": member.phone},
            "products": products,
        },
    }


@router.post("/appointment/book")
async def public_appointment_book(
    req: PublicAppointmentBookRequest,
    session: Session = Depends(get_session),
):
    """公开预约提交。提交前实时二次校验冲突，防止档期被抢占。"""
    try:
        store = await StoreService(session).get_by_store_code(req.storeCode)
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}

    phone = (req.customerPhone or "").strip()
    if not phone or len(phone) < 7:
        return {"code": 400, "msg": "请填写有效手机号", "data": None}

    member = session.query(CrmMemberModel).filter(
        CrmMemberModel.store_id == store.id,
        CrmMemberModel.phone == phone,
        CrmMemberModel.status == 1,
    ).first()
    if not member:
        return {"code": 404, "msg": "未查询到该手机号的客户档案，请联系门店添加后再预约", "data": None}

    member_product = None
    if req.memberProductId:
        member_product = session.query(CrmMemberProductModel).filter(
            CrmMemberProductModel.id == req.memberProductId,
            CrmMemberProductModel.store_id == store.id,
            CrmMemberProductModel.member_id == member.id,
            CrmMemberProductModel.status == 1,
        ).first()
        if not member_product:
            return {"code": 400, "msg": "所选项目不可用，请重新选择", "data": None}

    payload = {
        "storeId": store.id,
        "memberId": member.id,
        "employeeId": req.employeeId,
        "startAt": req.startAt,
        "durationMinutes": req.durationMinutes,
        "memberProductId": member_product.id if member_product else None,
        "productId": req.productId or (member_product.product_id if member_product else None),
        "productName": req.serviceName or (member_product.product_name if member_product else "预约服务"),
        "source": "h5",
        "status": "pending",
        "customerNotes": req.notes,
    }
    try:
        result = await AppointmentService(session).create_appointment(payload, "appointment_h5")
        _appointment_notify(
            session,
            store.id,
            "新的客户预约",
            f"{member.name or member.phone} 预约了 {payload['productName']}，时间 {result.get('startAt')}",
            result.get("id"),
        )
        session.commit()
        return {"code": 0, "msg": "预约成功", "data": result}
    except ValueError as e:
        session.rollback()
        return {"code": 409, "msg": str(e), "data": None}
    except Exception as e:
        session.rollback()
        logger.error(f"公开预约失败: {e}")
        return {"code": 500, "msg": f"预约失败: {e}", "data": None}


@router.get("/appointment/my")
async def public_my_appointments(
    storeCode: str,
    phone: str,
    session: Session = Depends(get_session),
):
    """按手机号查询客户未完成预约，用于取消/改约。"""
    try:
        store = await StoreService(session).get_by_store_code(storeCode)
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}
    member = session.query(CrmMemberModel).filter(
        CrmMemberModel.store_id == store.id,
        CrmMemberModel.phone == (phone or "").strip(),
        CrmMemberModel.status == 1,
    ).first()
    if not member:
        return {"code": 404, "msg": "未查询到该手机号的客户档案", "data": {"member": None, "appointments": []}}
    rows = session.query(CrmAppointmentModel).filter(
        CrmAppointmentModel.store_id == store.id,
        CrmAppointmentModel.member_id == member.id,
        CrmAppointmentModel.status.in_(["pending", "confirmed", "arrived"]),
        CrmAppointmentModel.start_at >= datetime.now(),
    ).order_by(CrmAppointmentModel.start_at.asc()).all()
    service = AppointmentService(session)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "member": {"id": member.id, "name": member.name, "phone": member.phone},
            "appointments": [service._appointment_to_dict(a) for a in rows],
        },
    }


@router.post("/appointment/cancel")
async def public_cancel_appointment(
    req: PublicAppointmentActionRequest,
    session: Session = Depends(get_session),
):
    """公开取消预约。"""
    try:
        store = await StoreService(session).get_by_store_code(req.storeCode)
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}
    member = session.query(CrmMemberModel).filter(CrmMemberModel.store_id == store.id, CrmMemberModel.phone == req.customerPhone).first()
    if not member:
        return {"code": 404, "msg": "未查询到该手机号的客户档案", "data": None}
    query = session.query(CrmAppointmentModel).filter(
        CrmAppointmentModel.store_id == store.id,
        CrmAppointmentModel.member_id == member.id,
        CrmAppointmentModel.status.in_(["pending", "confirmed", "arrived"]),
    )
    if req.appointmentId:
        query = query.filter(CrmAppointmentModel.id == req.appointmentId)
    appointment = query.order_by(CrmAppointmentModel.start_at.asc()).first()
    if not appointment:
        return {"code": 404, "msg": "未找到可取消的预约", "data": None}
    result = await AppointmentService(session).update_status(appointment.id, "cancelled", {"reason": req.reason or "客户H5取消"}, "appointment_h5")
    _appointment_notify(session, store.id, "客户取消预约", f"{member.name or member.phone} 取消了 {appointment.start_at}", appointment.id)
    session.commit()
    return {"code": 0, "msg": "预约已取消", "data": result}


@router.post("/appointment/reschedule")
async def public_reschedule_appointment(
    req: PublicAppointmentActionRequest,
    session: Session = Depends(get_session),
):
    """公开改约。提交前实时二次校验新时间。"""
    if not req.startAt:
        return {"code": 400, "msg": "请选择新的预约时间", "data": None}
    try:
        store = await StoreService(session).get_by_store_code(req.storeCode)
    except StoreNotFoundError as e:
        return {"code": 404, "msg": e.message, "data": None}
    member = session.query(CrmMemberModel).filter(CrmMemberModel.store_id == store.id, CrmMemberModel.phone == req.customerPhone).first()
    if not member:
        return {"code": 404, "msg": "未查询到该手机号的客户档案", "data": None}
    query = session.query(CrmAppointmentModel).filter(
        CrmAppointmentModel.store_id == store.id,
        CrmAppointmentModel.member_id == member.id,
        CrmAppointmentModel.status.in_(["pending", "confirmed", "arrived"]),
    )
    if req.appointmentId:
        query = query.filter(CrmAppointmentModel.id == req.appointmentId)
    appointment = query.order_by(CrmAppointmentModel.start_at.asc()).first()
    if not appointment:
        return {"code": 404, "msg": "未找到可改约的预约", "data": None}

    start_at = datetime.fromisoformat(req.startAt)
    duration = req.durationMinutes or appointment.duration_minutes or 60
    end_at = start_at + timedelta(minutes=duration)
    employee_id = req.employeeId or appointment.employee_id
    checker = AppointmentService(session)
    if start_at <= datetime.now():
        return {"code": 409, "msg": "不能改约到已经过去的时间", "data": None}
    if checker._has_conflict(employee_id, start_at, end_at):
        return {"code": 409, "msg": "该员工该时间段已有预约", "data": None}

    appointment.employee_id = employee_id
    appointment.start_at = start_at
    appointment.end_at = end_at
    appointment.appointment_date = start_at.date()
    appointment.duration_minutes = duration
    appointment.update_date = datetime.now()
    checker._log(appointment.id, "reschedule", None, checker._appointment_to_dict(appointment), "appointment_h5", req.reason or "客户H5改约")
    _appointment_notify(session, store.id, "客户改约", f"{member.name or member.phone} 改约到 {start_at}", appointment.id)
    session.commit()
    session.refresh(appointment)
    return {"code": 0, "msg": "改约成功", "data": checker._appointment_to_dict(appointment)}


@router.post("/process")
async def process_feedback(
    req: ProcessFeedbackRequest,
    session: Session = Depends(get_session),
):
    """AI 处理反馈 - 3 步 LLM Pipeline"""
    service = FeedbackService(session)
    try:
        result = await service.process_feedback(
            store_name=req.storeName,
            employee_number=req.employeeNumber,
            asr_text=req.asrText,
            session_id=req.sessionId,
            device_mac=req.deviceMac,
            satisfaction=req.satisfaction,
            store_id=req.storeId,
            employee_id=req.employeeId,
            customer_name=req.customerName,
            phone_tail=req.phoneTail,
        )
        return {"code": 0, "msg": "success", "data": result}
    except LLMProcessingError as e:
        logger.error(f"AI 处理失败: {e}")
        return {"code": 500, "msg": e.message, "data": None}
    except Exception as e:
        logger.error(f"处理反馈异常: {e}")
        return {"code": 500, "msg": f"处理失败: {str(e)}", "data": None}


@router.post("/record")
async def save_record(
    req: SaveRecordRequest,
    session: Session = Depends(get_session),
):
    """保存反馈记录 - H5 前端调用，字段名兼容"""
    service = FeedbackService(session)
    try:
        # 将 camelCase 映射到 domain 层的 snake_case
        record_data = {
            "store_id": req.storeId or "",
            "session_id": req.sessionId,
            "employee_id": req.employeeId,
            "device_mac": req.deviceMac,
            "raw_asr_text": req.rawAsrText,
            "cleaned_text": req.cleanedText,
            "qa_json": req.qaJson,
            "review_long": req.reviewLong,
            "review_short": req.reviewShort,
            "satisfaction": req.satisfaction,
            "customer_name": req.customerName,
            "phone_tail": req.phoneTail,
        }
        record = await service.save_record(record_data)
        return {
            "code": 0,
            "msg": "success",
            "data": {"id": record.id},
        }
    except Exception as e:
        logger.error(f"保存记录失败: {e}")
        return {"code": 500, "msg": f"保存失败: {str(e)}", "data": None}


@router.post("/device-init")
async def device_init(
    req: DeviceInitRequest,
    session: Session = Depends(get_session),
):
    """设备初始化 - 返回设备 MAC、OTA 信息、agentId、激活码

    流程:
    1. 查询门店信息，生成设备 MAC
    2. 服务端调用 Java OTA 获取激活码（设备未绑定时）或 WebSocket URL（已绑定时）
    3. 将 OTA 结果一并返回给 H5

    兼容两种调用方式:
    1. H5 旧版: {storeId, employeeId}
    2. 新版: {storeCode, deviceMac}
    """
    service = StoreService(session)

    # 确定门店信息
    store = None
    if req.storeCode:
        try:
            store = await service.get_by_store_code(req.storeCode)
        except StoreNotFoundError:
            return {"code": 404, "msg": f"门店不存在: {req.storeCode}", "data": None}
    elif req.storeId:
        try:
            store = await service.get_by_id(req.storeId)
        except StoreNotFoundError:
            return {"code": 404, "msg": f"门店不存在: {req.storeId}", "data": None}
    else:
        return {"code": 400, "msg": "请提供 storeCode 或 storeId", "data": None}

    # 生成/使用 MAC 地址（必须符合标准 MAC 格式 XX:XX:XX:XX:XX:XX，Java OTA 会校验）
    mac = req.deviceMac
    if not mac:
        code_part = store.store_code[-4:]
        emp_part = (req.employeeId or "0001").replace("emp", "").zfill(2)
        mac = f"FB:{code_part[:2]}:{code_part[2:4]}:{emp_part[:2]}:{code_part[:2]}:{emp_part[-2:]}"

    ws_port = settings.get("xiaozhi.ws_port", 18000)

    # 服务端调用 Java OTA，获取激活码或 WebSocket URL
    ota_result = await _call_java_ota(mac)

    return {
        "code": 0,
        "msg": "success",
        "data": {
            "deviceMac": mac,
            "agentId": store.agent_id,
            "storeId": store.id,
            "storeName": store.store_name,
            "wsPort": ws_port,
            "wsPath": "/xiaozhi/v1/voice",
            # OTA 结果：包含 activation.code 或 websocket.url
            "otaResult": ota_result,
        },
    }


async def _call_java_ota(device_mac: str) -> Optional[dict]:
    """服务端调用 Java OTA 端点，获取激活码或 WebSocket URL

    这是关键：通过服务端调用避免浏览器 CORS 问题，
    并且由 Java 管理后台生成激活码（存储在 Redis 中），
    这样管理员在智控台输入激活码才能完成绑定。
    """
    manager_api_url = settings.get("xiaozhi.manager_api_url", "http://127.0.0.1:8002")
    ota_url = f"{manager_api_url}/xiaozhi/ota/"

    ota_request_body = {
        "version": 0,
        "uuid": "",
        "application": {
            "name": "xiaozhi-feedback-h5",
            "version": "1.0.0",
            "compile_time": "2026-06-10 10:00:00",
            "idf_version": "4.4.3",
            "elf_sha256": "1234567890abcdef1234567890abcdef1234567890abcdef",
        },
        "ota": {"label": "xiaozhi-feedback-h5"},
        "board": {
            "type": "反馈H5",
            "ssid": "xiaozhi-feedback-h5",
            "rssi": 0,
            "channel": 0,
            "ip": "192.168.1.1",
            "mac": device_mac,
        },
        "flash_size": 0,
        "minimum_free_heap_size": 0,
        "mac_address": device_mac,
        "chip_model_name": "",
        "chip_info": {"model": 0, "cores": 0, "revision": 0, "features": 0},
        "partition_table": [{"label": "", "type": 0, "subtype": 0, "address": 0, "size": 0}],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                ota_url,
                headers={
                    "Device-Id": device_mac,
                    "Client-Id": "feedback_client",
                    "Content-Type": "application/json",
                },
                json=ota_request_body,
            )
            if resp.status_code == 200:
                result = resp.json()
                logger.info(f"Java OTA 响应: mac={device_mac}, "
                           f"has_activation={bool(result.get('activation'))}, "
                           f"has_websocket={bool(result.get('websocket', {}).get('url'))}")
                return result
            else:
                logger.warning(f"Java OTA 返回非200: status={resp.status_code}, body={resp.text[:200]}")
    except httpx.ConnectError:
        logger.error(f"Java OTA 连接失败: {ota_url}，请确认管理后台 (port 8002) 是否运行")
    except Exception as e:
        logger.error(f"Java OTA 调用异常: {e}")
    return None


# ---- OTA 代理 - 解决 H5 跨域问题 ----

async def _do_ota_proxy(path: str, request: Request):
    """OTA 代理核心逻辑 - 转发到 Java 管理后台

    H5 前端调用 /api/v1/public/ota/ → feedback-backend → Java 管理后台
    解决浏览器跨域问题，同时确保激活码在 Java Redis 中正确生成。
    """
    # 优先使用 Java 管理后台 URL（激活码在此生成）
    # 回退到 xiaozhi-server HTTP（仅独立模式可用）
    manager_api_url = settings.get("xiaozhi.manager_api_url", "")
    if manager_api_url:
        target_url = f"{manager_api_url}/xiaozhi/ota/{path}"
    else:
        xiaozhi_http = settings.get("xiaozhi.http_url", "http://127.0.0.1:18003")
        target_url = f"{xiaozhi_http}/xiaozhi/ota/{path}"

    # OPTIONS 预检直接放行
    if request.method == "OPTIONS":
        return JSONResponse(content={}, status_code=200)

    # 转发请求
    try:
        headers = dict(request.headers)
        # 移除 hop-by-hop 头
        for h in ["host", "content-length", "transfer-encoding", "connection"]:
            headers.pop(h, None)

        body = await request.body()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                params=dict(request.query_params),
            )

        # 透传响应
        content_type = resp.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        else:
            from fastapi.responses import Response
            return Response(content=resp.content, status_code=resp.status_code,
                            media_type=content_type)
    except Exception as e:
        logger.error(f"OTA 代理失败: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=502)


# 两个路由：/ota/ 和 /ota/{sub_path}，覆盖所有情况
@router.api_route("/ota/", methods=["GET", "POST", "OPTIONS"])
async def ota_proxy_root(request: Request):
    """代理 /xiaozhi/ota/ 根路径"""
    return await _do_ota_proxy("", request)


@router.api_route("/ota/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def ota_proxy_path(path: str, request: Request):
    """代理 /xiaozhi/ota/{sub_path}"""
    return await _do_ota_proxy(path, request)
