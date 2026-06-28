"""SQLAlchemy ORM 模型 - 映射到 MySQL 表

注意：这些是基础设施层的持久化模型，与领域层的 Entity 分离。
Repository 实现负责在 ORM Model 和 Domain Entity 之间转换。
"""

from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Text, JSON, SmallInteger, DateTime, Index, ForeignKey,
    Date, Numeric
)
from sqlalchemy.orm import relationship

from .database import Base


class StoreModel(Base):
    """门店表"""
    __tablename__ = "feedback_store"

    id = Column(String(64), primary_key=True)
    store_code = Column(String(6), unique=True, nullable=False, comment="6位门店编码")
    store_name = Column(String(128), nullable=False, comment="门店名称")
    manager = Column(String(64), nullable=True, comment="店长")
    shareholders = Column(String(256), nullable=True, comment="股东(逗号分隔)")
    agent_id = Column(String(32), nullable=True, comment="绑定的智能体ID")
    status = Column(SmallInteger, default=1, comment="0=禁用 1=启用")
    creator = Column(Integer, nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(Integer, nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    employees = relationship("EmployeeModel", back_populates="store", lazy="selectin",
                             primaryjoin="StoreModel.id==EmployeeModel.store_id",
                             foreign_keys="EmployeeModel.store_id")

    def __repr__(self):
        return f"<StoreModel(id={self.id}, code={self.store_code}, name={self.store_name})>"


class EmployeeModel(Base):
    """员工表"""
    __tablename__ = "feedback_employee"

    id = Column(String(64), primary_key=True)
    name = Column(String(64), nullable=False, comment="员工姓名")
    number = Column(Integer, nullable=False, comment="工号(门店内)")
    store_id = Column(String(64), ForeignKey("feedback_store.id"), nullable=False, index=True, comment="门店ID")
    employee_type = Column(String(32), default="normal", comment="manager/excellent/intern/normal")
    status = Column(SmallInteger, default=1, comment="0=禁用 1=启用")
    creator = Column(Integer, nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(Integer, nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    store = relationship("StoreModel", back_populates="employees",
                         primaryjoin="EmployeeModel.store_id==StoreModel.id",
                         foreign_keys="EmployeeModel.store_id")

    __table_args__ = (
        Index("idx_store_number", "store_id", "number"),
    )

    def __repr__(self):
        return f"<EmployeeModel(id={self.id}, name={self.name}, store={self.store_id})>"


class FeedbackRecordModel(Base):
    """反馈记录表"""
    __tablename__ = "feedback_record"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(128), nullable=True, index=True, comment="WebSocket会话ID")
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    employee_id = Column(String(64), nullable=True, comment="员工ID")
    device_mac = Column(String(32), nullable=True, comment="设备MAC地址")
    raw_asr_text = Column(Text, nullable=True, comment="原始ASR文本")
    cleaned_text = Column(Text, nullable=True, comment="清洗后文本")
    qa_json = Column(JSON, nullable=True, comment="结构化Q&A")
    review_long = Column(Text, nullable=True, comment="标准点评(80-150字)")
    review_short = Column(Text, nullable=True, comment="精简短评(30-60字)")
    satisfaction = Column(String(32), nullable=True, comment="满意度: very_satisfied/satisfied/unsatisfied/very_bad")
    member_id = Column(String(64), nullable=True, index=True, comment="关联客户ID")
    visit_id = Column(String(64), nullable=True, index=True, comment="关联到店记录ID")
    card_close_id = Column(String(64), nullable=True, index=True, comment="关联销卡记录ID")
    customer_name = Column(String(64), nullable=True, comment="客户称呼/自报姓名")
    phone_tail = Column(String(4), nullable=True, index=True, comment="客户手机号后四位")
    member_match_status = Column(String(32), nullable=True, comment="客户匹配状态: matched/conflict/not_found")
    member_match_candidates = Column(JSON, nullable=True, comment="手机号后四位匹配候选客户")
    status = Column(SmallInteger, default=1, comment="0=无效 1=有效")
    creator = Column(Integer, nullable=True)
    create_date = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    updater = Column(Integer, nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_store_create", "store_id", "create_date"),
    )

    def __repr__(self):
        return f"<FeedbackRecordModel(id={self.id}, store={self.store_id})>"


class AgentConfigModel(Base):
    """智能体配置表"""
    __tablename__ = "agent_config"

    id = Column(String(64), primary_key=True)
    agent_name = Column(String(128), nullable=False, comment="智能体名称")
    agent_id = Column(String(32), nullable=True, comment="对应xiaozhi-server智能体ID")
    dialogue_rounds = Column(Integer, default=7, comment="对话轮次")
    questions = Column(JSON, nullable=True, comment="问题列表")
    prompts_config = Column(JSON, nullable=True, comment="提示词配置")
    llm_config = Column(JSON, nullable=True, comment="LLM配置")
    review_config = Column(JSON, nullable=True, comment="点评生成规则")
    status = Column(SmallInteger, default=1, comment="0=禁用 1=启用")
    creator = Column(Integer, nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(Integer, nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<AgentConfigModel(id={self.id}, name={self.agent_name})>"


class CrmMemberModel(Base):
    """CRM 客户档案表"""
    __tablename__ = "crm_member"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="所属门店ID")
    name = Column(String(64), nullable=True, comment="姓名")
    phone = Column(String(20), nullable=True, comment="手机号")
    gender = Column(SmallInteger, nullable=True, comment="0未知 1男 2女")
    birthday = Column(Date, nullable=True, comment="生日")
    wechat = Column(String(128), nullable=True, comment="微信号")
    source = Column(String(32), default="manual", comment="来源 manual/feedback/import")
    level = Column(String(32), nullable=True, comment="客户等级")
    tags = Column(JSON, nullable=True, comment="普通客户标签")
    mekai_tags = Column(JSON, nullable=True, comment="麦凯66信息")
    beauty_concerns = Column(JSON, nullable=True, comment="美容关注点")
    health_issues = Column(JSON, nullable=True, comment="身体不适/疾病/禁忌")
    allergies = Column(Text, nullable=True, comment="过敏信息")
    service_preferences = Column(JSON, nullable=True, comment="服务偏好")
    notes = Column(Text, nullable=True, comment="备注")
    last_visit_at = Column(DateTime, nullable=True, comment="最近到店时间")
    total_visits = Column(Integer, default=0, comment="累计到店次数")
    total_spent = Column(Numeric(12, 2), default=0, comment="累计消费金额")
    status = Column(SmallInteger, default=1, comment="0=禁用 1=启用 2=流失")
    creator = Column(String(64), nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(String(64), nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_member_store_phone", "store_id", "phone"),
        Index("idx_crm_member_store_name", "store_id", "name"),
    )


class CrmVisitModel(Base):
    """CRM 到店记录表"""
    __tablename__ = "crm_visit"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    member_id = Column(String(64), nullable=True, index=True, comment="客户ID")
    employee_id = Column(String(64), nullable=True, index=True, comment="服务员工ID")
    feedback_record_id = Column(String(64), nullable=True, index=True, comment="关联反馈记录ID")
    session_id = Column(String(128), nullable=True, comment="WebSocket会话ID")
    device_mac = Column(String(32), nullable=True, comment="设备MAC")
    visit_type = Column(String(32), default="walk_in", comment="walk_in/appointment")
    service_items = Column(JSON, nullable=True, comment="服务项目")
    arrive_at = Column(DateTime, nullable=True, comment="到店时间")
    leave_at = Column(DateTime, nullable=True, comment="离店时间")
    duration_minutes = Column(Integer, nullable=True, comment="耗时分钟")
    satisfaction = Column(String(32), nullable=True, comment="满意度")
    consumption_amount = Column(Numeric(12, 2), default=0, comment="消费金额")
    notes = Column(Text, nullable=True, comment="备注")
    status = Column(SmallInteger, default=1, comment="0=无效 1=有效")
    creator = Column(String(64), nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(String(64), nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_visit_store_arrive", "store_id", "arrive_at"),
    )


class CrmAccountModel(Base):
    """CRM 账户/会员卡表"""
    __tablename__ = "crm_account"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    member_id = Column(String(64), nullable=False, index=True, comment="客户ID")
    account_type = Column(String(32), default="balance", comment="balance/count/course/time/coupon")
    card_name = Column(String(128), nullable=True, comment="卡名称")
    total_amount = Column(Numeric(12, 2), default=0, comment="总金额")
    balance_amount = Column(Numeric(12, 2), default=0, comment="余额")
    total_count = Column(Integer, default=0, comment="总次数")
    balance_count = Column(Integer, default=0, comment="剩余次数")
    valid_start = Column(Date, nullable=True, comment="有效期开始")
    valid_end = Column(Date, nullable=True, comment="有效期结束")
    status = Column(SmallInteger, default=1, comment="0=已销卡 1=使用中 2=已过期")
    closed_reason = Column(String(256), nullable=True, comment="销卡原因")
    closed_at = Column(DateTime, nullable=True, comment="销卡时间")
    notes = Column(Text, nullable=True, comment="备注")
    creator = Column(String(64), nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(String(64), nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_account_store_status", "store_id", "status"),
    )


class CrmAccountTransactionModel(Base):
    """CRM 账户流水表"""
    __tablename__ = "crm_account_transaction"

    id = Column(String(64), primary_key=True)
    account_id = Column(String(64), nullable=False, index=True, comment="账户ID")
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    member_id = Column(String(64), nullable=False, index=True, comment="客户ID")
    transaction_type = Column(String(32), nullable=False, comment="recharge/consume/refund/close/adjust")
    amount = Column(Numeric(12, 2), default=0, comment="金额变动")
    count_change = Column(Integer, default=0, comment="次数变动")
    balance_before = Column(Numeric(12, 2), default=0, comment="变动前余额")
    balance_after = Column(Numeric(12, 2), default=0, comment="变动后余额")
    related_visit_id = Column(String(64), nullable=True, comment="关联到店记录ID")
    notes = Column(String(256), nullable=True, comment="备注")
    operator = Column(String(64), nullable=True, comment="操作人")
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_crm_tx_store_date", "store_id", "create_date"),
    )


class CrmCardCloseModel(Base):
    """CRM 销卡记录表"""
    __tablename__ = "crm_card_close"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    member_id = Column(String(64), nullable=False, index=True, comment="客户ID")
    account_id = Column(String(64), nullable=False, index=True, comment="账户ID")
    feedback_record_id = Column(String(64), nullable=True, index=True, comment="关联反馈记录ID")
    close_type = Column(String(32), default="refund", comment="refund/transfer/close_only")
    reason = Column(String(256), nullable=True, comment="销卡原因")
    refund_amount = Column(Numeric(12, 2), default=0, comment="退款金额")
    remaining_count = Column(Integer, default=0, comment="剩余次数")
    status = Column(String(32), default="pending", comment="pending/processing/done/rejected")
    handled_by = Column(String(64), nullable=True, comment="处理人")
    approved_by = Column(String(64), nullable=True, comment="审批人")
    handle_notes = Column(Text, nullable=True, comment="处理说明")
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class CrmSuggestionModel(Base):
    """CRM 客户建议表"""
    __tablename__ = "crm_suggestion"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    feedback_record_id = Column(String(64), nullable=True, index=True, comment="关联反馈记录ID")
    member_id = Column(String(64), nullable=True, index=True, comment="客户ID")
    content = Column(Text, nullable=False, comment="建议内容")
    content_hash = Column(String(64), nullable=False, index=True, comment="内容哈希")
    category = Column(String(32), nullable=True, comment="分类")
    tags = Column(JSON, nullable=True, comment="标签")
    priority = Column(String(16), default="medium", comment="low/medium/high/urgent")
    source = Column(String(32), default="manual", comment="feedback/manual/card_close/agent")
    submitter_name = Column(String(64), nullable=True, comment="提出人")
    duplicate_group_id = Column(String(64), nullable=True, index=True, comment="去重组ID")
    frequency = Column(Integer, default=1, comment="出现次数")
    status = Column(String(32), default="pending", comment="pending/adopting/adopted/ignored/duplicate")
    adopted_at = Column(DateTime, nullable=True, comment="采纳时间")
    rejected_reason = Column(String(256), nullable=True, comment="拒绝原因")
    handled_by = Column(String(64), nullable=True, comment="处理人")
    handle_notes = Column(Text, nullable=True, comment="处理备注")
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_suggestion_store_status", "store_id", "status"),
    )


class CrmIssueModel(Base):
    """CRM 问题修复表"""
    __tablename__ = "crm_issue"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    feedback_record_id = Column(String(64), nullable=True, index=True, comment="关联反馈记录ID")
    member_id = Column(String(64), nullable=True, index=True, comment="客户ID")
    card_close_id = Column(String(64), nullable=True, index=True, comment="关联销卡记录ID")
    title = Column(String(256), nullable=False, comment="问题标题")
    description = Column(Text, nullable=True, comment="问题描述")
    severity = Column(String(16), default="medium", comment="low/medium/high/critical")
    category = Column(String(32), nullable=True, comment="分类")
    status = Column(String(32), default="identified", comment="identified/fixing/fixed/closed")
    identified_at = Column(DateTime, default=datetime.now, comment="识别时间")
    fix_plan = Column(Text, nullable=True, comment="修复方案")
    fix_deadline = Column(DateTime, nullable=True, comment="修复截止时间")
    fixed_at = Column(DateTime, nullable=True, comment="修复完成时间")
    fix_result = Column(Text, nullable=True, comment="修复结果")
    assigned_to = Column(String(64), nullable=True, comment="负责人")
    closed_at = Column(DateTime, nullable=True, comment="关闭时间")
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_issue_store_status", "store_id", "status"),
    )


class CrmBodyStatusModel(Base):
    """客户身体变化状态记录"""
    __tablename__ = "crm_body_status"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    member_id = Column(String(64), nullable=False, index=True, comment="客户ID")
    visit_id = Column(String(64), nullable=True, index=True, comment="关联到店记录ID")
    member_product_id = Column(String(64), nullable=True, index=True, comment="关联客户套餐ID")
    record_date = Column(DateTime, default=datetime.now, comment="记录时间")
    weight = Column(Numeric(8, 2), nullable=True, comment="体重kg")
    waistline = Column(Numeric(8, 2), nullable=True, comment="腰围cm")
    pain_level = Column(Integer, nullable=True, comment="疼痛/不适程度 0-10")
    sleep_quality = Column(Integer, nullable=True, comment="睡眠质量 0-10")
    skin_status = Column(String(128), nullable=True, comment="皮肤状态")
    body_parts = Column(JSON, nullable=True, comment="身体部位状态")
    metrics = Column(JSON, nullable=True, comment="其他指标")
    notes = Column(Text, nullable=True, comment="备注")
    creator = Column(String(64), nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(String(64), nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_body_status_member_date", "member_id", "record_date"),
        Index("idx_crm_body_status_store_date", "store_id", "record_date"),
    )


class CrmProductModel(Base):
    """CRM 产品/项目表"""
    __tablename__ = "crm_product"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    product_name = Column(String(128), nullable=False, comment="产品/项目名称")
    product_type = Column(String(32), default="service", comment="service/package/product")
    category = Column(String(64), nullable=True, comment="分类，如养生/减肥/美容")
    price = Column(Numeric(12, 2), default=0, comment="单价")
    default_count = Column(Integer, default=1, comment="默认次数")
    duration_minutes = Column(Integer, default=60, comment="默认服务时长")
    description = Column(Text, nullable=True, comment="说明")
    status = Column(SmallInteger, default=1, comment="0=下架 1=启用")
    creator = Column(String(64), nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(String(64), nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_product_store_category", "store_id", "category"),
    )


class CrmMemberProductModel(Base):
    """客户已购买产品/套餐表"""
    __tablename__ = "crm_member_product"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    member_id = Column(String(64), nullable=False, index=True, comment="客户ID")
    product_id = Column(String(64), nullable=True, index=True, comment="产品ID")
    account_id = Column(String(64), nullable=True, index=True, comment="关联账户ID")
    product_name = Column(String(128), nullable=False, comment="购买产品/套餐名称")
    package_items = Column(JSON, nullable=True, comment="套餐明细")
    unit_price = Column(Numeric(12, 2), default=0, comment="购买时单价")
    purchase_count = Column(Integer, default=0, comment="购买数量/次数")
    discount = Column(Numeric(5, 2), default=1, comment="折扣系数，1=10折")
    total_count = Column(Integer, default=0, comment="总次数")
    balance_count = Column(Integer, default=0, comment="剩余次数")
    total_amount = Column(Numeric(12, 2), default=0, comment="购买金额")
    balance_amount = Column(Numeric(12, 2), default=0, comment="剩余金额")
    valid_start = Column(Date, nullable=True, comment="有效期开始")
    valid_end = Column(Date, nullable=True, comment="有效期结束")
    status = Column(SmallInteger, default=1, comment="0=已用完/关闭 1=使用中 2=已过期")
    notes = Column(Text, nullable=True, comment="备注")
    creator = Column(String(64), nullable=True)
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    updater = Column(String(64), nullable=True)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_crm_member_product_store_status", "store_id", "status"),
        Index("idx_crm_member_product_member_status", "member_id", "status"),
    )


class CrmProductConsumeModel(Base):
    """客户产品/套餐消费记录"""
    __tablename__ = "crm_product_consume"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    member_id = Column(String(64), nullable=False, index=True, comment="客户ID")
    member_product_id = Column(String(64), nullable=False, index=True, comment="客户已购产品ID")
    product_id = Column(String(64), nullable=True, index=True, comment="产品ID")
    visit_id = Column(String(64), nullable=True, index=True, comment="到店记录ID")
    consume_count = Column(Integer, default=0, comment="消费次数")
    consume_amount = Column(Numeric(12, 2), default=0, comment="消费金额")
    balance_count_after = Column(Integer, default=0, comment="消费后剩余次数")
    balance_amount_after = Column(Numeric(12, 2), default=0, comment="消费后剩余金额")
    notes = Column(String(256), nullable=True, comment="备注")
    operator = Column(String(64), nullable=True, comment="操作人")
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_crm_product_consume_store_date", "store_id", "create_date"),
    )


class CrmEmployeeScheduleModel(Base):
    """员工每周排班"""
    __tablename__ = "crm_employee_schedule"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True, comment="门店ID")
    employee_id = Column(String(64), nullable=False, index=True, comment="员工ID")
    weekday = Column(SmallInteger, nullable=False, comment="1-7 周一到周日")
    start_time = Column(String(8), nullable=False, comment="HH:mm")
    end_time = Column(String(8), nullable=False, comment="HH:mm")
    is_working = Column(SmallInteger, default=1, comment="0=休息 1=上班")
    status = Column(SmallInteger, default=1)
    create_date = Column(DateTime, default=datetime.now)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_crm_schedule_employee_weekday", "employee_id", "weekday"),
    )


class CrmEmployeeTimeoffModel(Base):
    """员工特殊不可用时间"""
    __tablename__ = "crm_employee_timeoff"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True)
    employee_id = Column(String(64), nullable=False, index=True)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    reason = Column(String(256), nullable=True)
    status = Column(SmallInteger, default=1)
    create_date = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_crm_timeoff_employee_time", "employee_id", "start_at", "end_at"),
    )


class CrmAppointmentModel(Base):
    """门店预约"""
    __tablename__ = "crm_appointment"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=False, index=True)
    member_id = Column(String(64), nullable=False, index=True)
    employee_id = Column(String(64), nullable=False, index=True)
    member_product_id = Column(String(64), nullable=True, index=True)
    product_id = Column(String(64), nullable=True, index=True)
    product_name = Column(String(128), nullable=True)
    appointment_date = Column(Date, nullable=False, index=True)
    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=60)
    source = Column(String(32), default="admin", comment="admin/h5/voice/agent")
    status = Column(String(32), default="pending", comment="pending/confirmed/arrived/completed/cancelled/no_show")
    customer_notes = Column(Text, nullable=True)
    store_notes = Column(Text, nullable=True)
    cancel_reason = Column(String(256), nullable=True)
    created_by = Column(String(64), nullable=True)
    confirmed_by = Column(String(64), nullable=True)
    cancelled_by = Column(String(64), nullable=True)
    create_date = Column(DateTime, default=datetime.now)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_crm_appointment_store_date", "store_id", "appointment_date"),
        Index("idx_crm_appointment_employee_time", "employee_id", "start_at", "end_at"),
    )


class CrmAppointmentLogModel(Base):
    """预约变更日志"""
    __tablename__ = "crm_appointment_log"

    id = Column(String(64), primary_key=True)
    appointment_id = Column(String(64), nullable=False, index=True)
    action = Column(String(32), nullable=False)
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    operator = Column(String(64), nullable=True)
    notes = Column(String(256), nullable=True)
    create_date = Column(DateTime, default=datetime.now)


class AdminNotificationModel(Base):
    """后台通知消息"""
    __tablename__ = "admin_notification"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=True, index=True)
    title = Column(String(128), nullable=False)
    content = Column(Text, nullable=True)
    notification_type = Column(String(32), default="appointment", comment="appointment/system")
    target_route = Column(String(128), nullable=True)
    target_id = Column(String(64), nullable=True)
    status = Column(String(16), default="unread", comment="unread/read")
    create_date = Column(DateTime, default=datetime.now)
    read_date = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_admin_notification_store_status", "store_id", "status", "create_date"),
    )


class AgentFeedbackCaseModel(Base):
    """AI 助手反馈/失败案例"""
    __tablename__ = "agent_feedback_case"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), nullable=True, index=True)
    username = Column(String(64), nullable=True)
    message = Column(Text, nullable=False)
    reply = Column(Text, nullable=True)
    intent = Column(String(64), nullable=True)
    rating = Column(String(16), nullable=False, comment="like/dislike")
    trace = Column(JSON, nullable=True)
    status = Column(String(32), default="open", comment="open/reviewed/fixed/ignored")
    notes = Column(Text, nullable=True)
    create_date = Column(DateTime, default=datetime.now)
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_agent_feedback_status", "status", "create_date"),
    )


class AdminUserModel(Base):
    """管理员用户表（后台管理登录用）"""
    __tablename__ = "admin_user"

    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(256), nullable=False, comment="密码哈希")
    display_name = Column(String(64), nullable=True, comment="显示名称")
    role = Column(String(32), default="admin", comment="角色: super_admin/admin")
    status = Column(SmallInteger, default=1, comment="0=禁用 1=启用")
    create_date = Column(DateTime, default=datetime.now, comment="创建时间")
    update_date = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<AdminUserModel(id={self.id}, username={self.username})>"
