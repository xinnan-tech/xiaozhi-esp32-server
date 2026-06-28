"""反馈记录领域实体"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FeedbackRecord:
    """反馈记录实体 - 核心领域对象"""
    id: str
    store_id: str
    session_id: Optional[str] = None
    employee_id: Optional[str] = None
    device_mac: Optional[str] = None
    raw_asr_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    qa_json: Optional[str] = None        # JSON 格式的 Q&A 结构
    review_long: Optional[str] = None     # 标准点评 (80-150字)
    review_short: Optional[str] = None    # 精简短评 (30-60字)
    satisfaction: Optional[str] = None    # very_satisfied/satisfied/unsatisfied/very_bad
    member_id: Optional[str] = None        # 关联客户ID
    visit_id: Optional[str] = None         # 关联到店记录ID
    card_close_id: Optional[str] = None    # 关联销卡记录ID
    customer_name: Optional[str] = None     # 客户称呼/自报姓名
    phone_tail: Optional[str] = None        # 手机号后四位
    member_match_status: Optional[str] = None  # matched/conflict/not_found
    member_match_candidates: Optional[list] = None  # 匹配候选客户
    status: int = 1                       # 0=无效 1=有效
    create_date: Optional[datetime] = None
    update_date: Optional[datetime] = None

    def is_valid(self) -> bool:
        return self.status == 1

    def invalidate(self):
        """标记为无效记录"""
        self.status = 0
        self.update_date = datetime.now()

    def has_review(self) -> bool:
        """是否已生成点评"""
        return bool(self.review_long or self.review_short)

    def should_generate_review(self) -> bool:
        """是否应生成点评（仅满意时）"""
        return self.satisfaction in ("very_satisfied", "satisfied")
