"""后台 AI 助手服务 - 将自然语言路由到 CRM/统计能力。

当前是安全 MVP：用规则识别常见意图并调用现有应用服务。
后续可替换为 LLM + skill/CLI 工具调用。
"""

import re
from typing import Optional

from sqlalchemy.orm import Session

from app.application.crm_service import CrmService
from app.application.stats_service import StatsService


class AgentChatService:
    """后台 AI 助手服务"""

    def __init__(self, session: Session):
        self.session = session
        self.crm = CrmService(session)
        self.stats = StatsService(session)

    async def chat(self, message: str, history: Optional[list[dict]] = None, store_id: Optional[str] = None, operator: str = "") -> dict:
        from app.agent.graph import AgentGraph, AgentState

        graph = AgentGraph(self._plan, self._execute_step, self._summarize)
        contextual_message = self._with_context(message, history or [])
        state = await graph.run(AgentState(message=contextual_message, store_id=store_id, operator=operator))
        return {"reply": state.final_answer, "data": state.data, "route": state.route, "intent": state.intent, "trace": state.trace, "action": getattr(state, "action", None)}

    def _plan(self, state):
        from app.agent.graph import AgentStep

        original_text = state.message
        text = self._current_user_text(original_text)
        if not text:
            state.intent = "help"
            state.steps = [AgentStep("help")]
        elif self._has(text, ["帮助", "怎么用", "help", "菜单"]):
            state.intent = "help"
            state.steps = [AgentStep("help")]
        elif self._has(text, ["kpi", "KPI", "员工统计", "员工评价", "好评", "差评排行"]):
            state.intent = "employee_kpi"
            state.steps = [AgentStep("stats.employee-kpi")]
        elif self._has(text, ["概览", "看板", "总览", "crm概况", "CRM概况"]):
            state.intent = "crm_overview"
            state.steps = [AgentStep("crm.overview")]
        elif self._is_appointment_request(text):
            state.intent = "appointment_request"
            state.steps = [AgentStep("appointment.plan", self._extract_appointment_payload(text), risk="write")]
        elif self._has(text, ["创建产品", "新增产品", "新建产品"]):
            state.intent = "product_create"
            state.steps = [AgentStep("form.open", {"form": "crm.product.create", "payload": self._extract_product_payload(text)}, risk="write")]
        elif self._has(text, ["身体变化", "身体状态", "体重", "腰围", "睡眠", "疼痛"]):
            tail = self._extract_phone_tail(text)
            if tail:
                state.intent = "member_body_status"
                state.steps = [
                    AgentStep("crm.member-list", {"keyword": tail}),
                    AgentStep("crm.body-status-list", {"from_previous_member": True}),
                ]
            else:
                state.intent = "body_status"
                state.steps = [AgentStep("crm.body-status-list")]
        elif self._has(text, ["产品", "套餐", "养生", "减肥", "product", "package"]):
            tail = self._extract_phone_tail(text)
            if tail and self._has(text, ["剩", "还有", "几次", "多少次"]):
                state.intent = "member_package_balance"
                state.steps = [
                    AgentStep("crm.member-list", {"keyword": tail}),
                    AgentStep("crm.member-product-list", {"from_previous_member": True}),
                ]
            elif tail and self._has(text, ["消费", "扣", "用一次", "做一次"]):
                state.intent = "member_package_consume_plan"
                state.steps = [
                    AgentStep("crm.member-list", {"keyword": tail}),
                    AgentStep("crm.member-product-list", {"from_previous_member": True}),
                    AgentStep("confirm.required", {"action": "product_consume"}, risk="danger"),
                ]
            else:
                state.intent = "products"
                state.steps = [AgentStep("crm.product-list", {"keyword": self._extract_keyword(text)})]
        elif self._has(text, ["麦凯66", "麦凯", "66字段"]):
            state.intent = "mekai66"
            state.steps = [AgentStep("crm.mekai66-fields")]
        elif self._has(text, ["建议"]):
            state.intent = "suggestions"
            state.steps = [AgentStep("crm.suggestion-list", {"status": "pending" if self._has(text, ["待处理", "未处理"]) else None})]
        elif self._has(text, ["问题", "修复", "投诉"]):
            state.intent = "issues"
            state.steps = [AgentStep("crm.issue-list", {"status": "identified" if self._has(text, ["待修复", "待处理", "未修复"]) else None})]
        elif self._has(text, ["账户流水", "流水"]):
            state.intent = "transactions"
            state.steps = [AgentStep("crm.transactions", {"member_id": self._extract_id(text, "member")})]
        elif self._has(text, ["账户", "卡", "余额", "剩余次数"]):
            state.intent = "accounts"
            state.steps = [AgentStep("crm.account-list", {"member_id": self._extract_id(text, "member")})]
        elif self._has(text, ["创建客户", "新增客户", "新建客户", "创建用户", "新增用户", "新建用户"]):
            state.intent = "member_create"
            state.steps = [AgentStep("form.open", {"form": "crm.member.create", "payload": self._extract_member_payload(text)}, risk="write")]
        else:
            tail = self._extract_phone_tail(text)
            if tail or self._has(text, ["查客户", "找客户", "客户"]):
                state.intent = "member_search"
                state.steps = [AgentStep("crm.member-list", {"keyword": tail or self._extract_keyword(text)})]
            else:
                state.intent = "unknown"
                state.steps = [AgentStep("unknown")]
        return state

    async def _execute_step(self, state, step):
        skill = step.skill
        args = step.args
        if skill == "help":
            return self._help()["reply"]
        if skill == "unknown":
            return "我暂时没理解。你可以说：查客户尾号1234、员工KPI、CRM概览、产品套餐、待处理建议、待修复问题、账户流水。"
        if skill == "appointment.plan":
            return args
        if skill == "form.open":
            return args
        if skill == "stats.employee-kpi":
            return await self.stats.get_employee_kpi(state.store_id)
        if skill == "crm.overview":
            return await self.crm.get_overview(state.store_id)
        if skill == "crm.body-status-list":
            member_id = args.get("member_id")
            if args.get("from_previous_member") and state.steps and state.steps[0].result:
                members = state.steps[0].result.get("list") if isinstance(state.steps[0].result, dict) else []
                member_id = members[0].get("id") if members else None
            return await self.crm.list_body_statuses(page=1, page_size=10, store_id=state.store_id, member_id=member_id)
        if skill == "crm.product-create":
            if not args.get("productName"):
                return {"error": "创建产品需要产品名称，例如：创建产品 冰蚕乌酒"}
            return await self.crm.create_product({"store_id": state.store_id, **args}, state.operator)
        if skill == "crm.product-list":
            return await self.crm.list_products(page=1, page_size=10, store_id=state.store_id, keyword=args.get("keyword"))
        if skill == "crm.member-product-list":
            member_id = args.get("member_id")
            if args.get("from_previous_member") and state.steps and state.steps[0].result:
                members = state.steps[0].result.get("list") if isinstance(state.steps[0].result, dict) else []
                member_id = members[0].get("id") if members else None
            if not member_id:
                return {"list": [], "total": 0, "message": "未找到客户，无法查询已购套餐"}
            return await self.crm.list_member_products(page=1, page_size=10, store_id=state.store_id, member_id=member_id, status=1)
        if skill == "confirm.required":
            return {"needConfirmation": True, "message": "这是会减少客户套餐次数的操作，当前版本先返回待确认计划，暂不自动执行。请在客户套餐页或CLI确认后执行。"}
        if skill == "crm.mekai66-fields":
            from app.shared.mekai66 import MEKAI66_FIELDS
            return MEKAI66_FIELDS
        if skill == "crm.suggestion-list":
            return await self.crm.list_suggestions(page=1, page_size=10, store_id=state.store_id, status=args.get("status"))
        if skill == "crm.issue-list":
            return await self.crm.list_issues(page=1, page_size=10, store_id=state.store_id, status=args.get("status"))
        if skill == "crm.transactions":
            return await self.crm.list_account_transactions(page=1, page_size=10, store_id=state.store_id, member_id=args.get("member_id"))
        if skill == "crm.account-list":
            return await self.crm.list_accounts(page=1, page_size=10, store_id=state.store_id, member_id=args.get("member_id"))
        if skill == "crm.member-create":
            if not args.get("phone") and not args.get("name"):
                return {"error": "创建客户需要至少提供姓名或手机号，例如：新增客户 张女士 13800001234"}
            payload = {"store_id": state.store_id, "source": "agent", **args}
            return await self.crm.create_member(payload, state.operator)
        if skill == "crm.member-list":
            return await self.crm.list_members(page=1, page_size=10, store_id=state.store_id, keyword=args.get("keyword"))
        return {"error": f"未注册skill: {skill}"}

    def _summarize(self, state):
        if not state.steps:
            state.final_answer = "无执行步骤。"
            return state
        step = state.steps[-1]
        data = step.result
        state.data = data
        if isinstance(data, dict) and data.get("error"):
            state.final_answer = data["error"]
            return state
        if step.skill == "help" or step.skill == "unknown":
            state.final_answer = str(data)
        elif step.skill == "form.open":
            form = data.get("form")
            state.action = {"type": "open_form", "form": form, "route": "crm", "payload": data.get("payload") or {}}
            state.final_answer = "我已识别到要填写表单，会自动打开并预填已识别的信息。请确认后保存；缺少的字段可以继续告诉我。"
            state.route = "crm"
        elif step.skill == "appointment.plan":
            state.final_answer = "我识别到这是预约需求，已帮你打开预约表单。请先选择客户，系统会自动加载客户套餐；员工和时间我会尽量预填。"
            state.action = {"type": "open_form", "form": "crm.appointment.create", "route": "crm", "payload": data}
            state.route = "crm"
        elif step.skill == "stats.employee-kpi":
            state.final_answer = self._format_employee_kpi(data)
            state.route = "dashboard"
        elif step.skill == "crm.overview":
            state.final_answer = self._format_overview(data)
            state.route = "crm"
        elif step.skill == "crm.body-status-list":
            state.final_answer = self._format_body_statuses(data)
            state.route = "crm"
        elif step.skill == "crm.product-create":
            state.final_answer = f"已创建产品：{data.get('productName') or '-'}，分类：{data.get('category') or '-'}，默认次数：{data.get('defaultCount') or 0}"
            state.route = "crm"
        elif step.skill == "crm.product-list":
            state.final_answer = self._format_products(data)
            state.route = "crm"
        elif step.skill == "crm.member-product-list":
            state.final_answer = self._format_member_products(data)
            state.route = "crm"
        elif step.skill == "confirm.required":
            state.final_answer = data.get("message", "需要确认后执行。") if isinstance(data, dict) else "需要确认后执行。"
            state.route = "crm"
        elif step.skill == "crm.mekai66-fields":
            categories = {}
            for field in data:
                categories.setdefault(field["category"], 0)
                categories[field["category"]] += 1
            state.final_answer = "\n".join(["麦凯66字段已配置，共66项："] + [f"- {k}: {v}项" for k, v in categories.items()])
            state.route = "crm"
        elif step.skill == "crm.suggestion-list":
            state.final_answer = self._format_suggestions(data)
            state.route = "crm"
        elif step.skill == "crm.issue-list":
            state.final_answer = self._format_issues(data)
            state.route = "crm"
        elif step.skill == "crm.transactions":
            state.final_answer = self._format_transactions(data)
            state.route = "crm"
        elif step.skill == "crm.account-list":
            state.final_answer = self._format_accounts(data)
            state.route = "crm"
        elif step.skill == "crm.member-list":
            state.final_answer = self._format_members(data)
            state.route = "crm"
        elif step.skill == "crm.member-create":
            state.final_answer = (f"已创建客户：{data.get('name') or '-'}，手机号：{data.get('phone') or '-'}。\n"
                                  "还可以继续补充：生日、微信、客户等级、过敏史、皮肤状态、睡眠、体重/腰围、偏好技师、已购产品/套餐、服务力度偏好、下次跟进重点。")
            state.route = "crm"
        else:
            state.final_answer = "已执行。"
        return state

    @staticmethod
    def _current_user_text(text: str) -> str:
        marker = "当前用户说："
        if marker in (text or ""):
            return text.rsplit(marker, 1)[-1].strip()
        return (text or "").strip()

    @staticmethod
    def _with_context(message: str, history: list[dict]) -> str:
        """把最近几轮短上下文拼到当前输入，辅助长聊时省略主语的表达。"""
        text = (message or "").strip()
        if not history:
            return text
        lines = []
        for item in history[-6:]:
            role = "用户" if item.get("role") == "user" else "助手"
            content = str(item.get("text") or "").strip()
            if content and content != text:
                lines.append(f"{role}: {content[:200]}")
        if not lines:
            return text
        return "最近对话上下文：\n" + "\n".join(lines) + "\n当前用户说：" + text

    @staticmethod
    def _reply(text: str, data=None, route: Optional[str] = None) -> dict:
        return {"reply": text, "data": data, "route": route}

    @staticmethod
    def _has(text: str, keywords: list[str]) -> bool:
        lower = text.lower()
        return any(k.lower() in lower for k in keywords)

    @staticmethod
    def _is_appointment_request(text: str) -> bool:
        appointment_words = ["预约", "预定", "约一下", "约", "预战", "预占", "排个", "安排"]
        time_words = ["今天", "明天", "后天", "上午", "下午", "晚上", "点", "点钟"]
        service_words = ["服务", "做身体", "做一下", "过来", "到店", "员工"]
        return (any(w in text for w in appointment_words) or (any(w in text for w in time_words) and any(w in text for w in service_words)))

    @staticmethod
    def _extract_appointment_payload(text: str) -> dict:
        normalized = AgentChatService._normalize_asr_alias(text)
        employee = ""
        patterns = [
            r"(?:让|找|由|给|约)(?:那个|这个)?([一-龥A-Za-z]{2,8})(?:一号|1号|员工|老师|服务)",
            r"([一-龥A-Za-z]{2,8})(?:一号|1号)员工",
            r"员工[：: ]*([一-龥A-Za-z]{2,8})",
        ]
        for pattern in patterns:
            emp_match = re.search(pattern, normalized)
            if emp_match:
                employee = emp_match.group(1)
                break
        start_hint = ""
        time_match = re.search(r"((?:今天|明天|后天)?\s*(?:上午|下午|晚上|中午)?\s*(?:\d{1,2}|[一二两三四五六七八九十]{1,3})点(?:半|\d{1,2}分)?(?:钟)?(?:到(?:\d{1,2}|[一二两三四五六七八九十]{1,3})点(?:半|\d{1,2}分)?(?:钟)?)?)", normalized)
        if time_match:
            start_hint = time_match.group(1).strip()
        phone = re.search(r"1\d{10}|\d{4}", normalized)
        service = ""
        for kw in ["腰妍", "乌蛇", "冰蚕", "减肥", "养生", "肩颈", "身体"]:
            if kw in normalized:
                service = kw
                break
        return {"employeeName": employee, "startHint": start_hint, "memberKeyword": phone.group(0) if phone else "", "serviceKeyword": service, "raw": text, "normalized": normalized}

    @staticmethod
    def _normalize_asr_alias(text: str) -> str:
        aliases = {
            "预战": "预约", "预占": "预约", "场预战": "想预约", "长预战": "想预约",
            "李艾元": "李爱媛", "李艾媛": "李爱媛", "李爱元": "李爱媛",
            "一号": "1号",
        }
        for k, v in aliases.items():
            text = text.replace(k, v)
        return text

    @staticmethod
    def _extract_phone_tail(text: str) -> str:
        match = re.search(r"(?:尾号|后四位|手机号)[^0-9]{0,8}(\d{4})", text)
        if match:
            return match.group(1)
        match = re.search(r"(?<!\d)(\d{4})(?!\d)", text)
        return match.group(1) if match else ""

    @staticmethod
    def _extract_phone(text: str) -> str:
        match = re.search(r"1\d{10}", text)
        return match.group(0) if match else ""

    def _extract_member_payload(self, text: str) -> dict:
        name = self._extract_name(text)
        phone = self._extract_phone(text)
        gender = 1 if self._has(text, ["男", "先生"]) else (2 if self._has(text, ["女", "女士"]) else None)
        birth_year = self._extract_birth_year(text)
        health = []
        for word in ["膝盖积液", "脚踝扭伤", "肩颈酸痛", "腰背酸痛", "睡眠不好", "皮肤干燥"]:
            if word in text:
                health.append(word)
        mekai = {}
        if birth_year:
            mekai["birthday"] = f"{birth_year}年"
        if "已婚" in text:
            mekai["marital_status"] = "已婚"
        child = re.search(r"(\d+)岁宝宝", text)
        if child:
            mekai["children"] = f"{child.group(1)}岁宝宝"
        job = re.search(r"(?:工作岗位|职业|岗位)[：: ]*([一-龥A-Za-z0-9_+-]{2,20})", text)
        if job:
            mekai["position"] = job.group(1)
        return {
            "name": name,
            "phone": phone,
            "gender": gender,
            "healthIssues": health,
            "mekaiTags": mekai,
        }

    @staticmethod
    def _extract_birth_year(text: str) -> str:
        match = re.search(r"(19\d{2}|20\d{2}|\d{2})年", text)
        if not match:
            return ""
        year = match.group(1)
        if len(year) == 2:
            year = "19" + year if int(year) > 30 else "20" + year
        return year

    @staticmethod
    def _extract_product_payload(text: str) -> dict:
        name = ""
        match = re.search(r"(?:创建产品|新增产品|新建产品)[，,：: ]*([一-龥A-Za-z0-9_+-]{2,30})", text)
        if match:
            name = match.group(1).strip()
        category = ""
        for word in ["减肥", "养生", "美容", "酒", "产品", "套餐"]:
            if word in name or word in text:
                category = word
                break
        product_type = "package" if "套餐" in text or "套餐" in name else "product"
        price = 0
        price_match = re.search(r"(?:价格|售价|卖|金额)[：: ]*(\d+(?:\.\d+)?)", text)
        if not price_match:
            price_match = re.search(r"(\d+(?:\.\d+)?)\s*元", text)
        if price_match:
            price = price_match.group(1)
        count = 1
        count_match = re.search(r"(?:默认|次数|共)?\s*(\d+)\s*次", text)
        if count_match:
            count = count_match.group(1)
        category_match = re.search(r"(?:分类|类别)[：: ]*([一-龥A-Za-z0-9_+-]{1,20})", text)
        if category_match:
            category = category_match.group(1)
        return {"productName": name, "productType": product_type, "category": category, "defaultCount": count, "price": price}

    @staticmethod
    def _extract_name(text: str) -> str:
        patterns = [
            r"(?:姓名|名字|叫)[：: ]*([一-龥A-Za-z]{2,12})",
            r"(?:创建客户|新增客户|新建客户|创建用户|新增用户|新建用户)\s*([一-龥A-Za-z]{2,12})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _extract_keyword(text: str) -> str:
        for word in ["查客户", "找客户", "客户", "尾号", "后四位"]:
            text = text.replace(word, " ")
        return text.strip().split()[0] if text.strip().split() else ""

    @staticmethod
    def _extract_id(text: str, prefix: str) -> Optional[str]:
        match = re.search(rf"({prefix}[A-Za-z0-9_-]+|[a-f0-9]{{32}})", text)
        return match.group(1) if match else None

    def _help(self) -> dict:
        return self._reply("\n".join([
            "我可以帮你管理后台：",
            "1. 查客户尾号1234 / 查客户张女士",
            "2. 新增客户 张女士 13800001234",
            "3. 员工KPI / 差评排行",
            "4. CRM概览 / 账户流水 / 账户余额",
            "5. 待处理建议 / 待修复问题",
            "6. 麦凯66字段",
            "高风险操作（销卡、删除、批量修改）建议仍通过页面或CLI确认执行。",
        ]))

    @staticmethod
    def _format_overview(data: dict) -> str:
        return (f"CRM概览：客户{data.get('members', 0)}人，到店{data.get('visits', 0)}次，"
                f"有效账户{data.get('activeAccounts', 0)}个，账户余额¥{data.get('accountBalance', 0)}，"
                f"待处理建议{data.get('pendingSuggestions', 0)}条，待修复问题{data.get('openIssues', 0)}条。")

    @staticmethod
    def _format_employee_kpi(data: list[dict]) -> str:
        if not data:
            return "暂无员工KPI数据。"
        lines = ["员工KPI："]
        for item in data[:8]:
            lines.append(f"- {item.get('employeeName')}: 总{item.get('total')}，好评{item.get('good')}，中评{item.get('middle')}，差评{item.get('bad')}，好评率{item.get('goodRate')}%")
        return "\n".join(lines)

    @staticmethod
    def _format_members(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return "没有找到客户。"
        lines = [f"找到{data.get('total', len(rows))}个客户："]
        for m in rows:
            lines.append(f"- {m.get('name') or '-'} {m.get('phone') or '-'}，到店{m.get('totalVisits', 0)}次，消费¥{m.get('totalSpent', 0)}，ID={m.get('id')}")
        return "\n".join(lines)

    @staticmethod
    def _format_accounts(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return "暂无账户/卡。"
        return "\n".join(["账户/卡："] + [f"- {a.get('memberName') or '-'} {a.get('cardName') or a.get('accountType')}：余额¥{a.get('balanceAmount')}，剩余{a.get('balanceCount')}次，ID={a.get('id')}" for a in rows])

    @staticmethod
    def _format_transactions(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return "暂无账户流水。"
        return "\n".join(["最近账户流水："] + [f"- {t.get('createDate')} {t.get('memberName') or '-'} {t.get('transactionType')} 金额{t.get('amount')} 次数{t.get('countChange')} 备注:{t.get('notes') or '-'}" for t in rows])

    @staticmethod
    def _format_body_statuses(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return "暂无身体变化记录。"
        return "\n".join(["身体变化记录："] + [f"- {b.get('recordDate')} {b.get('memberName') or '-'}：体重{b.get('weight') or '-'}kg，腰围{b.get('waistline') or '-'}cm，不适{b.get('painLevel') or '-'}/10，睡眠{b.get('sleepQuality') or '-'}/10，{b.get('notes') or ''}" for b in rows])

    @staticmethod
    def _format_products(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return "暂无产品/套餐。"
        return "\n".join(["产品/套餐："] + [f"- {p.get('productName')}（{p.get('category') or '-'}，¥{p.get('price')}，默认{p.get('defaultCount')}次，ID={p.get('id')}）" for p in rows])

    @staticmethod
    def _format_member_products(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return data.get("message") or "该客户暂无已购产品/套餐。"
        return "\n".join(["客户已购产品/套餐："] + [f"- {p.get('productName')}：剩余{p.get('balanceCount')}/{p.get('totalCount')}次，余额¥{p.get('balanceAmount')}/¥{p.get('totalAmount')}，ID={p.get('id')}" for p in rows])

    @staticmethod
    def _format_suggestions(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return "暂无建议。"
        return "\n".join(["建议："] + [f"- {s.get('content')}（{s.get('status')}，出现{s.get('frequency')}次，ID={s.get('id')}）" for s in rows])

    @staticmethod
    def _format_issues(data: dict) -> str:
        rows = data.get("list") or []
        if not rows:
            return "暂无问题。"
        return "\n".join(["问题修复："] + [f"- {i.get('title')}（{i.get('status')}，{i.get('severity')}，负责人:{i.get('assignedTo') or '-'}，ID={i.get('id')}）" for i in rows])
