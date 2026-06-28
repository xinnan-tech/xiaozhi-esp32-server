"""员工仓储实现"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.employee.entity import Employee
from app.domain.employee.repository import IEmployeeRepository
from app.infrastructure.persistence.models import EmployeeModel
from app.shared.utils import generate_id


class EmployeeRepositoryImpl(IEmployeeRepository):
    """员工仓储实现"""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_entity(model: EmployeeModel) -> Employee:
        return Employee(
            id=model.id,
            name=model.name,
            number=model.number,
            store_id=model.store_id,
            employee_type=model.employee_type,
            status=model.status,
            create_date=model.create_date,
            update_date=model.update_date,
        )

    @staticmethod
    def _to_model(entity: Employee) -> EmployeeModel:
        return EmployeeModel(
            id=entity.id,
            name=entity.name,
            number=entity.number,
            store_id=entity.store_id,
            employee_type=entity.employee_type,
            status=entity.status,
            create_date=entity.create_date or datetime.now(),
            update_date=entity.update_date or datetime.now(),
        )

    async def get_by_id(self, employee_id: str) -> Optional[Employee]:
        model = self.session.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
        return self._to_entity(model) if model else None

    async def list_by_store_id(self, store_id: str, status: Optional[int] = None) -> List[Employee]:
        query = self.session.query(EmployeeModel).filter(EmployeeModel.store_id == store_id)
        if status is not None:
            query = query.filter(EmployeeModel.status == status)
        models = query.order_by(EmployeeModel.number.asc()).all()
        return [self._to_entity(m) for m in models]

    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_id: Optional[str] = None,
                        name: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        query = self.session.query(EmployeeModel)
        if store_id:
            query = query.filter(EmployeeModel.store_id == store_id)
        if name:
            query = query.filter(EmployeeModel.name.like(f"%{name}%"))
        if status is not None:
            query = query.filter(EmployeeModel.status == status)

        total = query.count()
        models = query.order_by(EmployeeModel.create_date.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return {
            "list": [self._to_entity(m) for m in models],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def save(self, employee: Employee) -> Employee:
        existing = self.session.query(EmployeeModel).filter(EmployeeModel.id == employee.id).first()
        if existing:
            existing.name = employee.name
            existing.number = employee.number
            existing.store_id = employee.store_id
            existing.employee_type = employee.employee_type
            existing.status = employee.status
            existing.update_date = datetime.now()
            self.session.commit()
            self.session.refresh(existing)
            return self._to_entity(existing)
        else:
            if not employee.id:
                employee.id = generate_id()
            model = self._to_model(employee)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)

    async def delete(self, employee_id: str) -> bool:
        count = self.session.query(EmployeeModel).filter(EmployeeModel.id == employee_id).delete()
        self.session.commit()
        return count > 0

    async def exists_by_store_and_number(self, store_id: str, number: int,
                                          exclude_id: Optional[str] = None) -> bool:
        query = self.session.query(EmployeeModel).filter(
            EmployeeModel.store_id == store_id,
            EmployeeModel.number == number,
        )
        if exclude_id:
            query = query.filter(EmployeeModel.id != exclude_id)
        return query.first() is not None
