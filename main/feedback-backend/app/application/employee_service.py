"""员工应用服务 - 员工 CRUD 用例"""

from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.employee.entity import Employee
from app.domain.employee.value_objects import EmployeeType
from app.infrastructure.persistence.employee_repo_impl import EmployeeRepositoryImpl
from app.shared.exceptions import EmployeeNotFoundError, StoreNotFoundError, ValidationError
from app.shared.utils import generate_id


class EmployeeService:
    """员工应用服务"""

    def __init__(self, session: Session):
        self.repo = EmployeeRepositoryImpl(session)
        self.session = session

    async def list_by_store_id(self, store_id: str, status: Optional[int] = None) -> list:
        """获取门店下所有员工（公开接口用）"""
        return await self.repo.list_by_store_id(store_id, status)

    async def get_by_id(self, employee_id: str) -> Employee:
        """根据 ID 获取员工"""
        employee = await self.repo.get_by_id(employee_id)
        if not employee:
            raise EmployeeNotFoundError(employee_id)
        return employee

    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_id: Optional[str] = None,
                        name: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        """分页查询员工"""
        return await self.repo.list_page(page, page_size, store_id, name, status)

    async def create_employee(self, name: str, number: int, store_id: str,
                              employee_type: str = "normal") -> Employee:
        """创建员工"""
        # 验证员工类型
        if employee_type not in Employee.valid_employee_types():
            raise ValidationError(f"无效的员工类型: {employee_type}")

        # 检查工号唯一性
        if await self.repo.exists_by_store_and_number(store_id, number):
            raise ValidationError(f"门店 {store_id} 下工号 {number} 已存在")

        employee = Employee(
            id=generate_id(),
            name=name,
            number=number,
            store_id=store_id,
            employee_type=employee_type,
        )
        result = await self.repo.save(employee)
        logger.info(f"创建员工: name={name}, store={store_id}, number={number}")
        return result

    async def update_employee(self, employee_id: str, **kwargs) -> Employee:
        """更新员工"""
        employee = await self.repo.get_by_id(employee_id)
        if not employee:
            raise EmployeeNotFoundError(employee_id)

        # 如果修改了工号，检查唯一性
        if "number" in kwargs and kwargs["number"] != employee.number:
            store_id = kwargs.get("store_id", employee.store_id)
            if await self.repo.exists_by_store_and_number(store_id, kwargs["number"], exclude_id=employee_id):
                raise ValidationError(f"工号 {kwargs['number']} 已存在")

        if "employee_type" in kwargs:
            if kwargs["employee_type"] not in Employee.valid_employee_types():
                raise ValidationError(f"无效的员工类型: {kwargs['employee_type']}")

        for key, value in kwargs.items():
            if hasattr(employee, key) and value is not None:
                setattr(employee, key, value)

        result = await self.repo.save(employee)
        logger.info(f"更新员工: id={employee_id}")
        return result

    async def delete_employee(self, employee_id: str) -> bool:
        """删除员工"""
        employee = await self.repo.get_by_id(employee_id)
        if not employee:
            raise EmployeeNotFoundError(employee_id)
        result = await self.repo.delete(employee_id)
        logger.info(f"删除员工: id={employee_id}")
        return result
