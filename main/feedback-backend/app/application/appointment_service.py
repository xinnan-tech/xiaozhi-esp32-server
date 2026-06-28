"""预约日历服务"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    CrmAppointmentLogModel,
    CrmAppointmentModel,
    CrmEmployeeScheduleModel,
    CrmEmployeeTimeoffModel,
    CrmMemberModel,
    CrmMemberProductModel,
    CrmProductModel,
    EmployeeModel,
)
from app.shared.utils import generate_id

ACTIVE_STATUS = ["pending", "confirmed", "arrived"]


class AppointmentService:
    def __init__(self, session: Session):
        self.session = session

    async def calendar(self, store_id: str, start_date: str, end_date: str,
                       employee_id: Optional[str] = None) -> dict:
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        emp_query = self.session.query(EmployeeModel).filter(EmployeeModel.store_id == store_id, EmployeeModel.status == 1)
        if employee_id:
            emp_query = emp_query.filter(EmployeeModel.id == employee_id)
        employees = emp_query.order_by(EmployeeModel.number).all()
        query = self.session.query(CrmAppointmentModel).filter(
            CrmAppointmentModel.store_id == store_id,
            CrmAppointmentModel.appointment_date >= start,
            CrmAppointmentModel.appointment_date <= end,
        )
        if employee_id:
            query = query.filter(CrmAppointmentModel.employee_id == employee_id)
        appointments = query.order_by(CrmAppointmentModel.start_at).all()
        return {
            "resources": [{"id": e.id, "title": e.name, "number": e.number, "type": e.employee_type} for e in employees],
            "events": [self._appointment_to_event(a) for a in appointments],
        }

    async def availability(self, store_id: str, appointment_date: str,
                           employee_id: Optional[str] = None,
                           duration_minutes: int = 60) -> dict:
        day = self._parse_date(appointment_date)
        weekday = day.isoweekday()
        employees_query = self.session.query(EmployeeModel).filter(EmployeeModel.store_id == store_id, EmployeeModel.status == 1)
        if employee_id:
            employees_query = employees_query.filter(EmployeeModel.id == employee_id)
        employees = employees_query.order_by(EmployeeModel.number).all()
        slots = []
        for emp in employees:
            schedules = self.session.query(CrmEmployeeScheduleModel).filter(
                CrmEmployeeScheduleModel.employee_id == emp.id,
                CrmEmployeeScheduleModel.weekday == weekday,
                CrmEmployeeScheduleModel.status == 1,
                CrmEmployeeScheduleModel.is_working == 1,
            ).all()
            if not schedules:
                schedules = [self._default_schedule(emp, weekday)]
            for schedule in schedules:
                slots.extend(self._slots_for_schedule(store_id, emp, day, schedule, duration_minutes))
        return {"date": str(day), "slots": slots}

    async def create_appointment(self, data: dict, operator: str = "") -> dict:
        start_at = self._parse_datetime(data.get("start_at") or data.get("startAt"))
        duration = int(data.get("duration_minutes") or data.get("durationMinutes") or 60)
        end_at = self._parse_datetime(data.get("end_at") or data.get("endAt")) or (start_at + timedelta(minutes=duration))
        store_id = data.get("store_id") or data.get("storeId")
        employee_id = data.get("employee_id") or data.get("employeeId")
        if start_at <= datetime.now():
            raise ValueError("不能预约已经过去的时间")
        if self._has_conflict(employee_id, start_at, end_at):
            raise ValueError("该员工该时间段已有预约")
        member_product = self._member_product(data.get("member_product_id") or data.get("memberProductId"))
        product = self._product(data.get("product_id") or data.get("productId") or (member_product.product_id if member_product else None))
        appointment = CrmAppointmentModel(
            id=generate_id(), store_id=store_id,
            member_id=data.get("member_id") or data.get("memberId"),
            employee_id=employee_id,
            member_product_id=data.get("member_product_id") or data.get("memberProductId"),
            product_id=data.get("product_id") or data.get("productId") or (member_product.product_id if member_product else None),
            product_name=data.get("product_name") or data.get("productName") or (member_product.product_name if member_product else (product.product_name if product else None)),
            appointment_date=start_at.date(), start_at=start_at, end_at=end_at,
            duration_minutes=duration,
            source=data.get("source") or "admin",
            status=data.get("status") or "pending",
            customer_notes=data.get("customer_notes") or data.get("customerNotes"),
            store_notes=data.get("store_notes") or data.get("storeNotes"),
            created_by=operator,
        )
        self.session.add(appointment)
        self._log(appointment.id, "create", None, self._appointment_to_dict(appointment), operator)
        self.session.commit()
        self.session.refresh(appointment)
        return self._appointment_to_dict(appointment)

    async def update_status(self, appointment_id: str, status: str, data: dict, operator: str = "") -> Optional[dict]:
        appointment = self.session.query(CrmAppointmentModel).filter(CrmAppointmentModel.id == appointment_id).first()
        if not appointment:
            return None
        before = self._appointment_to_dict(appointment)
        appointment.status = status
        if status == "confirmed":
            appointment.confirmed_by = operator
        if status == "cancelled":
            appointment.cancelled_by = operator
            appointment.cancel_reason = data.get("reason") or data.get("cancelReason")
        appointment.update_date = datetime.now()
        self._log(appointment.id, status, before, self._appointment_to_dict(appointment), operator, data.get("notes"))
        if status == "completed" and data.get("consume"):
            from app.application.crm_service import CrmService
            if appointment.member_product_id:
                CrmService(self.session).consume_member_product_sync(appointment.member_product_id, {
                    "consumeCount": data.get("consumeCount") or 1,
                    "consumeAmount": data.get("consumeAmount") or 0,
                    "visitId": data.get("visitId"),
                    "notes": f"预约完成自动消耗：{appointment.product_name or ''}",
                }, appointment.store_id, operator)
        self.session.commit()
        self.session.refresh(appointment)
        return self._appointment_to_dict(appointment)

    def _slots_for_schedule(self, store_id, emp, day, schedule, duration_minutes):
        start_t = self._parse_time(schedule.start_time)
        end_t = self._parse_time(schedule.end_time)
        cursor = datetime.combine(day, start_t)
        end_day = datetime.combine(day, end_t)
        slots = []
        while cursor + timedelta(minutes=duration_minutes) <= end_day:
            slot_end = cursor + timedelta(minutes=duration_minutes)
            available = cursor > datetime.now() and not self._has_conflict(emp.id, cursor, slot_end) and not self._has_timeoff(emp.id, cursor, slot_end)
            slots.append({"employeeId": emp.id, "employeeName": emp.name, "start": cursor.strftime("%H:%M"), "end": slot_end.strftime("%H:%M"), "available": available})
            cursor += timedelta(minutes=30)
        return slots

    def _has_conflict(self, employee_id: str, start_at: datetime, end_at: datetime) -> bool:
        return self.session.query(CrmAppointmentModel).filter(
            CrmAppointmentModel.employee_id == employee_id,
            CrmAppointmentModel.status.in_(ACTIVE_STATUS),
            CrmAppointmentModel.start_at < end_at,
            CrmAppointmentModel.end_at > start_at,
        ).first() is not None

    def _has_timeoff(self, employee_id: str, start_at: datetime, end_at: datetime) -> bool:
        return self.session.query(CrmEmployeeTimeoffModel).filter(
            CrmEmployeeTimeoffModel.employee_id == employee_id,
            CrmEmployeeTimeoffModel.status == 1,
            CrmEmployeeTimeoffModel.start_at < end_at,
            CrmEmployeeTimeoffModel.end_at > start_at,
        ).first() is not None

    def _default_schedule(self, emp, weekday):
        return CrmEmployeeScheduleModel(id="default", store_id=emp.store_id, employee_id=emp.id, weekday=weekday, start_time="10:00", end_time="20:00", is_working=1)

    def _member_product(self, member_product_id):
        if not member_product_id:
            return None
        return self.session.query(CrmMemberProductModel).filter(CrmMemberProductModel.id == member_product_id).first()

    def _product(self, product_id):
        if not product_id:
            return None
        return self.session.query(CrmProductModel).filter(CrmProductModel.id == product_id).first()

    def _log(self, appointment_id, action, before, after, operator, notes=None):
        self.session.add(CrmAppointmentLogModel(id=generate_id(), appointment_id=appointment_id, action=action, before_json=before, after_json=after, operator=operator, notes=notes))

    def _appointment_to_event(self, a):
        member = self.session.query(CrmMemberModel).filter(CrmMemberModel.id == a.member_id).first()
        return {
            "id": a.id, "resourceId": a.employee_id,
            "title": f"{member.name if member else '客户'} - {a.product_name or '预约'}",
            "start": a.start_at.isoformat(sep=" "), "end": a.end_at.isoformat(sep=" "),
            "status": a.status, "memberId": a.member_id, "memberName": member.name if member else None,
            "employeeId": a.employee_id, "productName": a.product_name,
        }

    def _appointment_to_dict(self, a):
        return {
            "id": a.id, "storeId": a.store_id, "memberId": a.member_id, "employeeId": a.employee_id,
            "memberProductId": a.member_product_id, "productId": a.product_id, "productName": a.product_name,
            "appointmentDate": str(a.appointment_date), "startAt": str(a.start_at), "endAt": str(a.end_at),
            "durationMinutes": a.duration_minutes, "source": a.source, "status": a.status,
            "customerNotes": a.customer_notes, "storeNotes": a.store_notes, "cancelReason": a.cancel_reason,
        }

    @staticmethod
    def _parse_date(value):
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value)[:10]).date()

    @staticmethod
    def _parse_time(value):
        h, m = str(value).split(":")[:2]
        return time(int(h), int(m))

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
