import json
import os
import copy
from aiohttp import web
from config.logger import setup_logging
from core.api.base_handler import BaseHandler
from core.utils.llm import create_instance as create_llm_instance
from config.config_loader import get_private_config_from_api

TAG = __name__

# 提示词文件目录
PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "feedback-prompts")


class FeedbackHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        self._load_prompts()

    def _load_prompts(self):
        """加载三套提示词模板"""
        self.prompt_asr_cleanup = self._read_prompt("asr-cleanup.txt")
        self.prompt_qa_structured = self._read_prompt("qa-structured.txt")
        self.prompt_review_generation = self._read_prompt("review-generation.txt")

    def _read_prompt(self, filename):
        """读取提示词文件"""
        filepath = os.path.join(PROMPT_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            self.logger.bind(tag=TAG).error(f"提示词文件不存在: {filepath}")
            return ""

    def _fill_prompt(self, template, variables):
        """填充提示词模板变量"""
        result = template
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", str(value) if value else "未提供")
        return result

    def _get_llm(self, config=None):
        """获取LLM实例"""
        current_config = config or self.config
        selected_module = current_config.get("selected_module", {})
        llm_name = selected_module.get("LLM")
        if not llm_name:
            # 使用默认LLM
            llm_configs = current_config.get("LLM", {})
            if llm_configs:
                llm_name = list(llm_configs.keys())[0]
        if not llm_name:
            raise ValueError("未找到可用的LLM配置")

        llm_config = current_config.get("LLM", {}).get(llm_name, {})
        llm_type = llm_config.get("type", "openai")
        return create_llm_instance(llm_type, llm_config)

    async def _get_llm_for_device(self, device_id, client_id):
        """根据设备ID从智控台获取私有配置中的LLM"""
        current_config = copy.deepcopy(self.config)
        read_config_from_api = current_config.get("read_config_from_api", False)
        if read_config_from_api and device_id:
            try:
                current_config = await get_private_config_from_api(
                    current_config, device_id, client_id or "feedback_client"
                )
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"获取设备配置失败: {e}，使用本地配置")
        return self._get_llm(current_config)

    async def handle_post(self, request):
        """处理反馈AI处理请求"""
        response = None
        try:
            # 解析请求体
            body = await request.json()
            store_name = body.get("storeName", "")
            employee_number = body.get("employeeNumber", "")
            asr_text = body.get("asrText", "")
            session_id = body.get("sessionId", "")
            device_mac = body.get("deviceMac", "")
            client_id = body.get("clientId", "feedback_client")
            # 用户主动选择的满意度: very_satisfied / satisfied / unsatisfied / very_bad
            satisfaction = body.get("satisfaction", "")

            if not asr_text:
                return web.Response(
                    text=json.dumps({"success": False, "message": "ASR文本不能为空"}),
                    content_type="application/json",
                    status=400,
                )

            # 满意度映射到中文
            satisfaction_map = {
                "very_satisfied": "非常满意",
                "satisfied": "满意",
                "unsatisfied": "不满意",
                "very_bad": "非常糟糕",
            }
            satisfaction_text = satisfaction_map.get(satisfaction, "")

            # 准备变量
            variables = {
                "门店名称": store_name,
                "技师工号": employee_number,
                "用户全部语音原话": asr_text,
                "消费项目": "",
                "到店时长": "",
                "到店时间": "",
                "身体不舒服症状": "",
                "问题是否解决": "",
                "满意程度": satisfaction_text,
                "客户建议内容": "",  # 注意：建议内容仅做后台沉淀，不传给好评生成
            }

            self.logger.bind(tag=TAG).info(f"开始处理反馈: store={store_name}, employee={employee_number}, satisfaction={satisfaction}")

            # 获取LLM实例（优先使用设备绑定的智能体LLM）
            if device_mac:
                llm = await self._get_llm_for_device(device_mac, client_id)
            else:
                llm = self._get_llm()

            # 第1步：ASR规整
            self.logger.bind(tag=TAG).info("第1步：ASR规整处理")
            asr_cleanup_prompt = self._fill_prompt(self.prompt_asr_cleanup, variables)
            cleaned_text = llm.response_no_stream(asr_cleanup_prompt, asr_text)
            variables["规整后ASR文本"] = cleaned_text

            # 第2步：QA结构化
            self.logger.bind(tag=TAG).info("第2步：QA结构化处理")
            qa_prompt = self._fill_prompt(self.prompt_qa_structured, variables)
            qa_result = llm.response_no_stream(qa_prompt, asr_text)

            # 从QA结果中提取更多变量用于好评生成
            self._extract_qa_variables(qa_result, variables)

            # 第3步：好评生成 — 仅在用户满意/非常满意时生成
            review_long = ""
            review_short = ""
            if satisfaction in ("very_satisfied", "satisfied"):
                self.logger.bind(tag=TAG).info(f"第3步：好评生成（满意度={satisfaction_text}）")
                review_prompt = self._fill_prompt(self.prompt_review_generation, variables)
                review_result = llm.response_no_stream(review_prompt, asr_text)
                review_long, review_short = self._parse_review(review_result)
            else:
                self.logger.bind(tag=TAG).info(f"跳过好评生成（满意度={satisfaction_text or '未选择'}）")

            result = {
                "success": True,
                "cleaned_text": cleaned_text,
                "qa_result": qa_result,
                "review_long": review_long,
                "review_short": review_short,
                "satisfaction": satisfaction,
                "satisfaction_text": satisfaction_text,
                "should_publish": satisfaction in ("very_satisfied", "satisfied"),
            }

            response = web.Response(
                text=json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                content_type="application/json",
            )

        except ValueError as e:
            self.logger.bind(tag=TAG).error(f"反馈处理参数错误: {e}")
            response = web.Response(
                text=json.dumps({"success": False, "message": str(e)}),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"反馈处理异常: {e}")
            import traceback
            self.logger.bind(tag=TAG).error(traceback.format_exc())
            response = web.Response(
                text=json.dumps({"success": False, "message": "处理请求时发生错误"}),
                content_type="application/json",
                status=500,
            )
        finally:
            if response:
                self._add_cors_headers(response)
            return response

    def _extract_qa_variables(self, qa_result, variables):
        """从QA结果中提取变量用于好评生成。
        注意：满意程度由用户主动选择（已在variables中），不从QA覆盖；
        客户建议内容仅落盘到后台，不传给好评提示词，避免污染评论文案。
        """
        try:
            lines = qa_result.split("\n")
            for line in lines:
                if line.startswith("A3：") or line.startswith("A3:"):
                    variables["消费项目"] = line[3:].strip()
                elif line.startswith("A2：") or line.startswith("A2:"):
                    variables["到店时长"] = line[3:].strip()
                elif line.startswith("A4：") or line.startswith("A4:"):
                    variables["到店时间"] = line[3:].strip()
                elif line.startswith("A5：") or line.startswith("A5:"):
                    variables["身体不舒服症状"] = line[3:].strip()
                elif line.startswith("A6：") or line.startswith("A6:"):
                    variables["问题是否解决"] = line[3:].strip()
                # A7（满意程度）以用户选的为准，跳过
                # A8（客户建议）仅留在 qa_result 落盘，不进 variables
        except Exception:
            pass

    def _parse_review(self, review_result):
        """解析好评生成结果，分离标准版和精简版"""
        review_long = ""
        review_short = ""

        try:
            if "【标准版点评】" in review_result:
                parts = review_result.split("【精简短评】")
                if len(parts) >= 2:
                    long_part = parts[0]
                    short_part = parts[1]
                    # 提取标准版内容
                    if "：" in long_part:
                        review_long = long_part.split("：", 1)[1].strip()
                    else:
                        review_long = long_part.replace("【标准版点评】", "").strip()
                    # 提取精简版内容
                    if "：" in short_part:
                        review_short = short_part.split("：", 1)[1].strip()
                    else:
                        review_short = short_part.strip()
                else:
                    review_long = review_result.replace("【标准版点评】", "").strip()
            else:
                review_long = review_result
        except Exception:
            review_long = review_result

        return review_long, review_short
