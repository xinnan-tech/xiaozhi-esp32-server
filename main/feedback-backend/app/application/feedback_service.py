"""反馈处理应用服务 - AI 处理管线（3步 LLM Pipeline）"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.feedback.entity import FeedbackRecord
from app.domain.feedback.value_objects import Satisfaction
from app.infrastructure.llm.llm_service import LLMService
from app.infrastructure.persistence.feedback_repo_impl import FeedbackRecordRepositoryImpl
from app.infrastructure.persistence.store_repo_impl import StoreRepositoryImpl
from app.infrastructure.persistence.agent_repo_impl import AgentConfigRepositoryImpl
from app.shared.config import settings
from app.shared.exceptions import StoreNotFoundError, LLMProcessingError, PromptTemplateError
from app.shared.utils import generate_id, should_generate_review, render_prompt
from app.infrastructure.persistence.models import (
    CrmIssueModel,
    CrmMemberModel,
    CrmSuggestionModel,
    CrmVisitModel,
    FeedbackRecordModel,
)


class FeedbackService:
    """反馈处理应用服务 - 核心业务逻辑

    3 步 AI Pipeline:
    1. ASR 清洗 - 去除语音填充词
    2. QA 结构化 - 提取结构化 Q&A
    3. 点评生成 - 仅满意时生成点评
    """

    def __init__(self, session: Session):
        self.record_repo = FeedbackRecordRepositoryImpl(session)
        self.store_repo = StoreRepositoryImpl(session)
        self.agent_repo = AgentConfigRepositoryImpl(session)
        self.session = session

    def _get_prompts_dir(self) -> Path:
        """获取提示词模板目录"""
        base_dir = Path(__file__).resolve().parent.parent.parent  # feedback-backend/
        return base_dir / "prompts"

    def _load_prompt(self, filename: str) -> str:
        """加载提示词模板"""
        path = self._get_prompts_dir() / filename
        if not path.exists():
            raise PromptTemplateError(filename, f"模板文件不存在: {path}")
        return path.read_text(encoding="utf-8")

    def _resolve_llm_service(self, agent_id: Optional[str] = None) -> LLMService:
        """解析 LLM 服务 - 优先使用门店绑定的智能体配置"""
        if agent_id:
            # 尝试从 agent_config 获取自定义 LLM 配置
            # 注意：这里不能用 async，所以在外层处理
            pass
        # 使用默认配置
        return LLMService()

    async def _resolve_llm_service_async(self, agent_id: Optional[str] = None) -> LLMService:
        """异步解析 LLM 服务"""
        if agent_id:
            agent_config = await self.agent_repo.get_by_agent_id(agent_id)
            if agent_config and agent_config.llm_config:
                return LLMService(llm_config=agent_config.llm_config)
        return LLMService()

    async def process_feedback(
        self,
        store_name: str,
        employee_number: str,
        asr_text: str,
        session_id: Optional[str] = None,
        device_mac: Optional[str] = None,
        satisfaction: Optional[str] = None,
        store_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        phone_tail: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        处理客户反馈 - 完整的 3 步 AI Pipeline

        Args:
            store_name: 门店名称
            employee_number: 技师工号
            asr_text: 原始 ASR 文本
            session_id: 会话 ID
            device_mac: 设备 MAC
            satisfaction: 满意度
            store_id: 门店 ID
            employee_id: 员工 ID
            agent_id: 智能体 ID

        Returns:
            处理结果字典
        """
        logger.info(f"开始处理反馈: store={store_name}, employee={employee_number}, satisfaction={satisfaction}")

        # 验证满意度
        satisfaction_text = ""
        should_publish = False
        if satisfaction:
            try:
                sat = Satisfaction(satisfaction)
                satisfaction_text = sat.text
                should_publish = sat.is_positive
            except ValueError:
                logger.warning(f"无效的满意度值: {satisfaction}")

        # 解析 LLM 服务
        llm = await self._resolve_llm_service_async(agent_id)

        # Step 1: ASR 清洗
        cleaned_text = await self._step_asr_cleanup(llm, store_name, employee_number, asr_text)
        logger.info(f"ASR 清洗完成，原文 {len(asr_text)} 字 -> 清洗后 {len(cleaned_text)} 字")

        # Step 2: QA 结构化
        qa_result = await self._step_qa_structured(llm, store_name, employee_number, cleaned_text)
        logger.info(f"QA 结构化完成")

        # Step 3: 点评生成（仅满意时）
        review_long = None
        review_short = None
        if should_publish and should_generate_review(satisfaction):
            review_long, review_short = await self._step_review_generation(
                llm, store_name, employee_number, qa_result, satisfaction
            )
            logger.info(f"点评生成完成: 长评={len(review_long or '')}字, 短评={len(review_short or '')}字")

        # 保存记录（通过 session_id upsert，如果 H5 已先保存了 rawAsrText，这里会更新）
        record = FeedbackRecord(
            id=generate_id(),
            store_id=store_id or "",
            session_id=session_id,
            employee_id=employee_id,
            device_mac=device_mac,
            raw_asr_text=asr_text,
            cleaned_text=cleaned_text,
            qa_json=qa_result,
            review_long=review_long,
            review_short=review_short,
            satisfaction=satisfaction,
            customer_name=(customer_name or "").strip() or None,
            phone_tail=self._normalize_phone_tail(phone_tail) or None,
        )
        try:
            # 如果已有同 session_id 的记录，更新它
            if session_id:
                existing = await self.record_repo.get_by_session_id(session_id)
                if existing:
                    existing.cleaned_text = cleaned_text
                    existing.qa_json = qa_result
                    existing.review_long = review_long
                    existing.review_short = review_short
                    existing.satisfaction = satisfaction
                    existing.customer_name = (customer_name or existing.customer_name or "").strip() or None
                    existing.phone_tail = self._normalize_phone_tail(phone_tail) or existing.phone_tail
                    record = await self.record_repo.save(existing)
                    logger.info(f"反馈记录已更新: session_id={session_id}")
                else:
                    record = await self.record_repo.save(record)
                    logger.info(f"反馈记录已保存: id={record.id}")
            else:
                record = await self.record_repo.save(record)
                logger.info(f"反馈记录已保存: id={record.id}")
        except Exception as e:
            logger.error(f"反馈记录保存失败: {e}")
            # 记录保存失败不影响返回结果

        self._auto_link_feedback_to_crm(record, cleaned_text, qa_result, satisfaction)

        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "qa_result": qa_result,
            "review_long": review_long,
            "review_short": review_short,
            "satisfaction": satisfaction,
            "satisfaction_text": satisfaction_text,
            "should_publish": should_publish,
            "customer_name": record.customer_name,
            "phone_tail": record.phone_tail,
            "member_id": record.member_id,
            "member_match_status": record.member_match_status,
            "member_match_candidates": record.member_match_candidates or [],
        }

    def _auto_link_feedback_to_crm(self, record: FeedbackRecord, cleaned_text: str,
                                   qa_result: str, satisfaction: Optional[str]):
        """根据已有反馈结构化内容自动关联 CRM。"""
        if not record or not record.store_id:
            return
        try:
            phone_tail = record.phone_tail or self._extract_phone_tail(qa_result or cleaned_text or "")
            record.phone_tail = phone_tail or None
            customer_name = record.customer_name or self._extract_customer_name(qa_result or cleaned_text or "")
            record.customer_name = customer_name or None
            match_result = self._match_member_by_identity(record.store_id, phone_tail, customer_name)
            member = match_result.get("member")
            record.member_match_status = match_result.get("status")
            record.member_match_candidates = match_result.get("candidates") or []
            if member:
                record.member_id = member.id
                self._merge_member_profile(member, qa_result)

            visit = self._create_or_update_visit(record, qa_result, satisfaction)
            if visit:
                record.visit_id = visit.id

            self.session.query(FeedbackRecordModel).filter(FeedbackRecordModel.id == record.id).update({
                "member_id": record.member_id,
                "visit_id": record.visit_id,
                "customer_name": record.customer_name,
                "phone_tail": record.phone_tail,
                "member_match_status": record.member_match_status,
                "member_match_candidates": record.member_match_candidates,
            })
            self._auto_create_suggestion(record, qa_result)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.warning(f"自动关联 CRM 失败: {e}")
        # 问题修复模块已从主流程下线：反馈只进入建议/客户档案/到店，不再自动创建问题。

    def _match_member_by_identity(self, store_id: str, phone_tail: str, customer_name: str = "") -> dict:
        phone_tail = self._normalize_phone_tail(phone_tail)
        if not phone_tail:
            return {"status": None, "member": None, "candidates": []}
        candidates = self.session.query(CrmMemberModel).filter(
            CrmMemberModel.store_id == store_id,
            CrmMemberModel.phone.like(f"%{phone_tail}"),
            CrmMemberModel.status == 1,
        ).order_by(CrmMemberModel.update_date.desc()).all()
        candidate_list = [self._member_candidate(m) for m in candidates]
        if not candidates:
            return {"status": "not_found", "member": None, "candidates": []}
        if len(candidates) == 1:
            return {"status": "matched", "member": candidates[0], "candidates": candidate_list}
        name = (customer_name or "").strip()
        if name:
            name_matches = [m for m in candidates if self._name_matches(name, m)]
            if len(name_matches) == 1:
                return {"status": "matched", "member": name_matches[0], "candidates": candidate_list}
        return {"status": "conflict", "member": None, "candidates": candidate_list}

    @staticmethod
    def _member_candidate(member) -> dict:
        return {
            "id": member.id,
            "name": member.name,
            "phone": member.phone,
            "phoneTail": (member.phone or "")[-4:],
            "nickname": (member.mekai_tags or {}).get("nickname") if isinstance(member.mekai_tags, dict) else None,
        }

    @staticmethod
    def _normalize_phone_tail(value: str) -> str:
        import re
        digits = re.sub(r"\D", "", value or "")
        return digits[-4:] if len(digits) >= 4 else ""

    @staticmethod
    def _name_matches(customer_name: str, member) -> bool:
        name = (customer_name or "").strip()
        if not name:
            return False
        candidates = [member.name or ""]
        if isinstance(member.mekai_tags, dict):
            candidates.append(member.mekai_tags.get("nickname") or "")
        normalized = name.replace("女士", "").replace("先生", "").replace("姐", "").replace("哥", "").strip()
        for item in candidates:
            item = (item or "").strip()
            item_norm = item.replace("女士", "").replace("先生", "").replace("姐", "").replace("哥", "").strip()
            if name and (name in item or item in name):
                return True
            if normalized and item_norm and (normalized in item_norm or item_norm in normalized):
                return True
        return False

    @staticmethod
    def _extract_customer_name(text: str) -> str:
        import re
        patterns = [
            r"(?:怎么称呼您|如何称呼您|称呼您|您的称呼|您怎么称呼)[^\n：:，,。]{0,12}[：:]?\s*([一-龥A-Za-z]{1,12})",
            r"(?:我叫|我是|叫我)([一-龥A-Za-z]{1,12})",
            r"Q9[^\n]*\n?A9[：:]\s*([^\n，,。]+)",
            r"Q9[^A]*A9[：:]\s*([^\n，,。]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text or "")
            if match:
                name = match.group(1).strip()
                if name and name not in {"未提及", "用户未作答", "不知道"} and not re.fullmatch(r"\d+", name):
                    return name[:12]
        return ""

    @staticmethod
    def _extract_phone_tail(text: str) -> str:
        import re
        match = re.search(r"(?:手机号后四位|手机尾号|尾号|后四位)[^0-9]{0,8}(\d{4})", text or "")
        if match:
            return match.group(1)
        matches = re.findall(r"(?<!\d)(\d{4})(?!\d)", text or "")
        return matches[-1] if matches else ""

    def _merge_member_profile(self, member, qa_result: str):
        discomfort = self._extract_qa_answer(qa_result, "Q5") or self._extract_qa_answer(qa_result, "不舒服")
        if discomfort:
            existing = member.health_issues if isinstance(member.health_issues, list) else []
            if isinstance(existing, str):
                try:
                    existing = json.loads(existing)
                except Exception:
                    existing = [existing]
            if discomfort not in existing:
                existing.append(discomfort)
                member.health_issues = existing
        member.update_date = datetime.now()

    def _create_or_update_visit(self, record: FeedbackRecord, qa_result: str, satisfaction: Optional[str]):
        visit_time = self._extract_qa_answer(qa_result, "Q4") or self._extract_qa_answer(qa_result, "时间")
        service_item = self._extract_qa_answer(qa_result, "Q3") or self._extract_qa_answer(qa_result, "项目")
        existing = None
        if record.session_id:
            existing = self.session.query(CrmVisitModel).filter(CrmVisitModel.session_id == record.session_id).first()
        visit = existing or CrmVisitModel(id=generate_id(), store_id=record.store_id, session_id=record.session_id)
        visit.member_id = record.member_id
        visit.employee_id = record.employee_id
        visit.feedback_record_id = record.id
        visit.device_mac = record.device_mac
        visit.satisfaction = satisfaction
        if service_item:
            visit.service_items = [service_item]
        if visit_time and not visit.arrive_at:
            visit.arrive_at = self._parse_visit_time(visit_time)
        if not existing:
            self.session.add(visit)
        return visit

    def _auto_create_suggestion(self, record: FeedbackRecord, qa_result: str):
        suggestion_text = self._extract_qa_answer(qa_result, "Q10") or self._extract_qa_answer(qa_result, "Q8") or self._extract_qa_answer(qa_result, "建议")
        if not suggestion_text:
            return
        content_hash = self._content_hash(suggestion_text)
        existing = self.session.query(CrmSuggestionModel).filter(
            CrmSuggestionModel.store_id == record.store_id,
            CrmSuggestionModel.content_hash == content_hash,
        ).first()
        if existing:
            existing.frequency = (existing.frequency or 1) + 1
            existing.member_id = existing.member_id or record.member_id
            existing.feedback_record_id = existing.feedback_record_id or record.id
            existing.update_date = datetime.now()
            return
        self.session.add(CrmSuggestionModel(
            id=generate_id(),
            store_id=record.store_id,
            feedback_record_id=record.id,
            member_id=record.member_id,
            content=suggestion_text,
            content_hash=content_hash,
            category="feedback",
            tags=["反馈建议"],
            priority="medium",
            source="feedback",
            submitter_name=self._member_name(record.member_id),
            duplicate_group_id=generate_id(),
            status="pending",
        ))

    def _member_name(self, member_id: Optional[str]) -> Optional[str]:
        if not member_id:
            return None
        member = self.session.query(CrmMemberModel).filter(CrmMemberModel.id == member_id).first()
        return member.name if member else None

    @staticmethod
    def _content_hash(content: str) -> str:
        import hashlib
        import re
        normalized = re.sub(r"\s+", "", content or "").lower()
        normalized = re.sub(r"[，。！？,.!?；;：:]", "", normalized)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_visit_time(text: str):
        import re
        now = datetime.now()
        match = re.search(r"(\d{1,2})[点:：](\d{1,2})?", text or "")
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return None

    def _auto_create_feedback_issue(self, record: FeedbackRecord, cleaned_text: str,
                                    qa_result: str, satisfaction: Optional[str]):
        """基于已有反馈自动生成待修复问题。"""
        if not record or not record.store_id:
            return
        negative = satisfaction in ("unsatisfied", "very_bad")
        text = f"{cleaned_text or ''}\n{qa_result or ''}"
        keywords = ["退款", "销卡", "投诉", "没效果", "不满意", "很差", "态度", "卫生", "太冷", "太热"]
        if not negative and not any(k in text for k in keywords):
            return
        try:
            from app.infrastructure.persistence.models import CrmIssueModel

            title = "客户反馈待修复问题"
            if "销卡" in text or "退款" in text:
                title = "客户存在销卡/退款风险"
            elif "态度" in text:
                title = "客户反馈服务态度问题"
            elif "太冷" in text or "太热" in text:
                title = "客户反馈环境温度问题"
            elif "没效果" in text:
                title = "客户反馈项目效果问题"
            exists = self.session.query(CrmIssueModel).filter(
                CrmIssueModel.feedback_record_id == record.id,
                CrmIssueModel.title == title,
            ).first()
            if exists:
                return
            issue = CrmIssueModel(
                id=generate_id(),
                store_id=record.store_id,
                feedback_record_id=record.id,
                member_id=record.member_id,
                title=title,
                description=text[:1000] if text else None,
                severity="high" if satisfaction == "very_bad" else "medium",
                category="feedback",
                status="identified",
            )
            self.session.add(issue)
            self.session.commit()
            logger.info(f"已从反馈自动创建问题: feedback_id={record.id}, issue_id={issue.id}")
        except Exception as e:
            self.session.rollback()
            logger.warning(f"自动创建反馈问题失败: {e}")

    async def _step_asr_cleanup(self, llm: LLMService, store_name: str,
                                 employee_number: str, asr_text: str) -> str:
        """Step 1: ASR 清洗 - 去除语音填充词"""
        try:
            template = self._load_prompt("asr-cleanup.txt")
            prompt = render_prompt(
                template,
                门店名称=store_name,
                技师工号=employee_number,
                用户全部语音原话=asr_text,
            )
            result = await llm.chat(
                system_prompt="你是一位专业的语音文本清洗专家。",
                user_message=prompt,
                temperature=0.1,
            )
            return result.strip()
        except PromptTemplateError:
            # 模板不存在时，直接使用简单清洗
            logger.warning("ASR 清洗模板不存在，使用简单清洗")
            return asr_text.strip()
        except Exception as e:
            logger.error(f"ASR 清洗失败: {e}")
            raise LLMProcessingError(f"ASR 清洗失败: {e}")

    async def _step_qa_structured(self, llm: LLMService, store_name: str,
                                   employee_number: str, cleaned_text: str) -> str:
        """Step 2: QA 结构化 - 提取结构化 Q&A"""
        try:
            template = self._load_prompt("qa-structured.txt")
            prompt = render_prompt(
                template,
                门店名称=store_name,
                技师编号=employee_number,
                消费项目="",
                规整后ASR文本=cleaned_text,
            )
            result = await llm.chat(
                system_prompt="你是一位专业的客户反馈分析师。",
                user_message=prompt,
                temperature=0.2,
            )
            return result.strip()
        except PromptTemplateError:
            logger.warning("QA 结构化模板不存在，跳过结构化")
            return cleaned_text
        except Exception as e:
            logger.error(f"QA 结构化失败: {e}")
            raise LLMProcessingError(f"QA 结构化失败: {e}")

    async def _step_review_generation(self, llm: LLMService, store_name: str,
                                       employee_number: str, qa_result: str,
                                       satisfaction: str) -> tuple:
        """Step 3: 点评生成 - 生成标准版和精简版点评"""
        try:
            template = self._load_prompt("review-generation.txt")

            # 从 QA 结果中提取信息（解析 Q1-Q8 格式）
            consumption_item = self._extract_qa_answer(qa_result, "Q3") or self._extract_qa_answer(qa_result, "项目")
            duration = self._extract_qa_answer(qa_result, "Q2") or self._extract_qa_answer(qa_result, "多久")
            visit_time = self._extract_qa_answer(qa_result, "Q4") or self._extract_qa_answer(qa_result, "时间")
            discomfort = self._extract_qa_answer(qa_result, "Q5") or self._extract_qa_answer(qa_result, "不舒服")
            problem_solved = self._extract_qa_answer(qa_result, "Q6") or self._extract_qa_answer(qa_result, "解决")
            satisfaction_level = Satisfaction(satisfaction).text if satisfaction else ""

            prompt = render_prompt(
                template,
                门店名称=store_name,
                技师编号=employee_number,
                消费项目=consumption_item or "未提及",
                到店时长=duration or "未提及",
                到店时间=visit_time or "未提及",
                身体不舒服症状=discomfort or "未提及",
                问题是否解决=problem_solved or "未提及",
                满意程度=satisfaction_level or "满意",
            )

            # 将完整的 QA 结果附加到 prompt 中，作为上下文参考
            full_prompt = prompt + "\n\n以下是客户的完整QA反馈记录，请严格基于这些QA内容生成点评（注意区分【客户】和【技师】的归属，不要张冠李戴）：\n" + qa_result

            result = await llm.chat(
                system_prompt="你是一位专业的点评撰写专家，擅长根据客户反馈撰写真实自然的消费点评。你必须严格基于QA记录中的信息撰写，特别注意区分客户本人和技师的属性（比如来店3年是客户的消费时长，不是技师的工作时长）。",
                user_message=full_prompt,
                temperature=0.7,
                max_tokens=1000,
            )

            # 解析点评结果
            review_long, review_short = self._parse_review_result(result)
            return review_long, review_short

        except PromptTemplateError:
            logger.warning("点评生成模板不存在，跳过点评生成")
            return None, None
        except Exception as e:
            logger.error(f"点评生成失败: {e}")
            return None, None

    @staticmethod
    def _parse_review_result(result: str) -> tuple:
        """解析 LLM 返回的点评结果 - 支持多种格式"""
        import re
        review_long = None
        review_short = None

        # 清理 markdown 格式符号
        cleaned = re.sub(r'^#{1,6}\s*', '', result, flags=re.MULTILINE)
        cleaned = re.sub(r'^---+\s*$', '', cleaned, flags=re.MULTILINE)

        # 策略1: 【标准版点评】...【精简短评】...
        long_match = re.search(r"【标准版点评】[：:\s]*(.*?)(?=【精简短评】|$)", cleaned, re.DOTALL)
        short_match = re.search(r"【精简短评】[：:\s]*(.*?)$", cleaned, re.DOTALL)

        # 策略2: 标准版点评：...精简短评：...
        if not long_match:
            long_match = re.search(r"标准版点评[：:\s]*(.*?)(?=精简短评|$)", cleaned, re.DOTALL)
        if not short_match:
            short_match = re.search(r"精简短评[：:\s]*(.*?)$", cleaned, re.DOTALL)

        # 策略3: 长评：...短评：...
        if not long_match:
            long_match = re.search(r"长评[：:\s]*(.*?)(?=短评|$)", cleaned, re.DOTALL)
        if not short_match:
            short_match = re.search(r"短评[：:\s]*(.*?)$", cleaned, re.DOTALL)

        if long_match:
            review_long = long_match.group(1).strip()
        if short_match:
            review_short = short_match.group(1).strip()

        # 如果没有标准格式，整段作为长评
        if not review_long and not review_short:
            review_long = result.strip()

        return review_long, review_short

    @staticmethod
    def _extract_qa_answer(qa_text: str, question_key: str) -> str:
        """从 QA 结构化文本中提取指定问题的答案

        支持多种格式：
        - Q1: xxx  A1: xxx
        - Q1：xxx  A1：xxx
        - 技师工号是多少？xxx  => 用关键词匹配
        """
        import re

        if not qa_text:
            return ""

        lines = qa_text.strip().split('\n')

        # 尝试按 Q编号 + A编号 格式匹配
        # 先找 question_key 对应的 Q 编号
        if question_key.startswith('Q'):
            q_num = question_key[1:]
            # 匹配 A{n}: 或 A{n}：格式
            pattern = rf'A{q_num}\s*[：:]\s*(.+?)$'
            for line in lines:
                match = re.search(pattern, line.strip())
                if match:
                    answer = match.group(1).strip()
                    if answer and answer != '未提及' and answer != '用户未作答':
                        return answer

        # 关键词匹配模式
        for line in lines:
            if question_key in line:
                # 提取 A: 后面的部分
                match = re.search(r'A\d*\s*[：:]\s*(.+?)$', line.strip())
                if match:
                    answer = match.group(1).strip()
                    if answer and answer != '未提及' and answer != '用户未作答':
                        return answer

        return ""

    async def save_record(self, record_data: Dict[str, Any]) -> FeedbackRecord:
        """保存反馈记录（H5 前端直接调用）

        支持 upsert 逻辑：
        - 如果传了 session_id 且已有该 session 的记录，则更新（补全 AI 处理结果）
        - 否则创建新记录
        """
        # 尝试通过 session_id 查找已有记录
        existing = None
        session_id = record_data.get("session_id")
        if session_id:
            existing = await self.record_repo.get_by_session_id(session_id)

        if existing:
            # 更新已有记录（仅覆盖非空字段）
            if record_data.get("raw_asr_text"):
                existing.raw_asr_text = record_data["raw_asr_text"]
            if record_data.get("cleaned_text"):
                existing.cleaned_text = record_data["cleaned_text"]
            if record_data.get("qa_json"):
                existing.qa_json = record_data["qa_json"]
            if record_data.get("review_long"):
                existing.review_long = record_data["review_long"]
            if record_data.get("review_short"):
                existing.review_short = record_data["review_short"]
            if record_data.get("satisfaction"):
                existing.satisfaction = record_data["satisfaction"]
            if record_data.get("customer_name"):
                existing.customer_name = record_data["customer_name"].strip()
            if record_data.get("phone_tail"):
                existing.phone_tail = self._normalize_phone_tail(record_data["phone_tail"])
            return await self.record_repo.save(existing)
        else:
            # 创建新记录
            record = FeedbackRecord(
                id=generate_id(),
                store_id=record_data.get("store_id", ""),
                session_id=session_id,
                employee_id=record_data.get("employee_id"),
                device_mac=record_data.get("device_mac"),
                raw_asr_text=record_data.get("raw_asr_text"),
                cleaned_text=record_data.get("cleaned_text"),
                qa_json=record_data.get("qa_json"),
                review_long=record_data.get("review_long"),
                review_short=record_data.get("review_short"),
                satisfaction=record_data.get("satisfaction"),
                customer_name=(record_data.get("customer_name") or "").strip() or None,
                phone_tail=self._normalize_phone_tail(record_data.get("phone_tail")),
            )
            return await self.record_repo.save(record)

    async def list_records(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        """查询反馈记录"""
        return await self.record_repo.list_page(page, page_size, **filters)
