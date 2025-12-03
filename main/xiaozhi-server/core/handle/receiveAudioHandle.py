import time
import json
import asyncio
import threading
import concurrent.futures
from core.utils.util import audio_to_data
from core.handle.abortHandle import handleAbortMessage
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.sendAudioHandle import send_stt_message, SentenceType
from config.logger import setup_logging
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO
from typing import List, Dict, Any

TAG = __name__
logger = setup_logging()


def _get_parallel_chat_handler(conn):
    """
    获取或创建 ParallelChatHandler 实例
    
    缓存在 conn 对象上，避免重复创建
    """
    if hasattr(conn, '_parallel_chat_handler') and conn._parallel_chat_handler is not None:
        return conn._parallel_chat_handler
    
    try:
        from core.parallel import ParallelChatHandler, FeatureFlag, get_feature_manager
        
        # 检查是否启用 LLMCompiler
        if not get_feature_manager().is_enabled(FeatureFlag.LLM_COMPILER):
            return None
        
        conn._parallel_chat_handler = ParallelChatHandler(conn)
        conn.logger.bind(tag=TAG).info("ParallelChatHandler 已初始化")
        return conn._parallel_chat_handler
    except ImportError as e:
        conn.logger.bind(tag=TAG).warning(f"并行优化模块未安装: {e}")
        return None
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"ParallelChatHandler 初始化失败: {e}")
        return None


def _is_parallel_enabled() -> bool:
    """检查并行优化是否启用"""
    try:
        from core.parallel.feature_flags import FeatureFlag, get_feature_manager
        return get_feature_manager().is_enabled(FeatureFlag.LLM_COMPILER)
    except ImportError:
        return False

# ============== 打断检测配置 ==============
# 业界最佳实践：持续语音检测 + 分层打断

# 持续语音检测阈值（避免短暂噪音、回声、咳嗽等误触发）
# 需要连续检测到语音的帧数才触发打断
CONTINUOUS_VOICE_THRESHOLD = 3  # 连续 3 帧（约 180ms @ 60ms/帧）

# 智能打断配置（用于 ASR 意图识别）
INTERRUPT_BUFFER_SIZE = 5  # 累积 5 个音频包（约 300ms @ 60ms/包）
INTERRUPT_ASR_TIMEOUT = 0.8  # 快速 ASR 超时时间（秒）
INTERRUPT_DEBOUNCE_MS = 500  # 打断防抖时间（毫秒）

# 打断意图关键词
INTERRUPTION_KEYWORDS = [
    "停", "等等", "打住", "不对", "算了", "别说了",
    "我想问", "我要", "帮我", "听我说", "等一下"
]

# 强制停止关键词（即使 TTS 未播放也会取消当前任务）
FORCE_STOP_KEYWORDS = ["停止", "取消", "算了", "不要了", "停下"]


async def _smart_interrupt_handler(conn, text: str) -> bool:
    """
    智能打断处理

    Args:
        conn: ConnectionHandler
        text: ASR 识别的文本

    Returns:
        bool: True=继续处理, False=跳过（反馈信号）
    """
    try:
        from core.parallel.smart_interruption import (
            SmartInterruptionManager,
            InterruptionDecision,
            InterruptionType,
        )
        from core.parallel.feature_flags import FeatureFlag, get_feature_manager

        # 检查是否启用智能打断
        if not get_feature_manager().is_enabled(FeatureFlag.SMART_INTERRUPTION):
            # 未启用智能打断，使用传统逻辑
            await handleAbortMessage(conn)
            return True

        # 获取或创建管理器
        if not hasattr(conn, '_smart_interruption_manager'):
            conn._smart_interruption_manager = SmartInterruptionManager(
                logger=conn.logger if hasattr(conn, 'logger') else None,
            )

        manager = conn._smart_interruption_manager

        # 检测打断意图
        decision, int_type = await manager.should_interrupt_on_text(
            text=text,
            is_speaking=conn.client_is_speaking,
            listen_mode=conn.client_listen_mode,
        )

        # 反馈信号：不打断，也不处理
        if int_type == InterruptionType.BACKCHANNEL and decision == InterruptionDecision.CONTINUE:
            return False

        # 需要打断
        if decision == InterruptionDecision.INTERRUPT:
            # 通知 ParallelChatHandler 处理打断（如果存在）
            parallel_handler = _get_parallel_chat_handler(conn)
            if parallel_handler is not None:
                await parallel_handler.handle_user_interruption(text)
            
            # 同时执行传统的打断处理
            await handleAbortMessage(conn)

        return True

    except ImportError:
        # 模块未安装，使用传统逻辑
        await handleAbortMessage(conn)
        return True
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"智能打断处理失败: {e}")
        # 出错时使用传统逻辑
        await handleAbortMessage(conn)
        return True


def _is_smart_interruption_enabled() -> bool:
    """检查智能打断是否启用"""
    try:
        from core.parallel.feature_flags import FeatureFlag, get_feature_manager
        return get_feature_manager().is_enabled(FeatureFlag.SMART_INTERRUPTION)
    except ImportError:
        return False


def _is_interruption_intent(text: str) -> bool:
    """检测是否是打断意图"""
    if not text:
        return False
    return any(keyword in text for keyword in INTERRUPTION_KEYWORDS)


def _is_force_stop_intent(text: str) -> bool:
    """检测是否是强制停止意图（即使 TTS 未播放也生效）"""
    if not text:
        return False
    return any(keyword in text for keyword in FORCE_STOP_KEYWORDS)


def _init_interrupt_state(conn):
    """初始化打断检测状态"""
    if not hasattr(conn, '_interrupt_buffer'):
        conn._interrupt_buffer = []
    if not hasattr(conn, '_interrupt_check_running'):
        conn._interrupt_check_running = False
    if not hasattr(conn, '_last_interrupt_time'):
        conn._last_interrupt_time = 0
    # 持续语音检测计数器
    if not hasattr(conn, '_continuous_voice_count'):
        conn._continuous_voice_count = 0



# 伪流式预取配置
PSEUDO_STREAM_BUFFER_THRESHOLD = 8  # 触发预取的音频帧数阈值（约 500ms @ 60ms/帧）
PSEUDO_STREAM_ASR_TIMEOUT = 2.0  # 预取 ASR 超时时间（秒）
PSEUDO_STREAM_MEMORY_TIMEOUT = 1.5  # 预取 Memory 超时时间（秒）


def _init_pseudo_stream_state(conn):
    """初始化伪流式预取状态"""
    if not hasattr(conn, '_pseudo_stream_buffer'):
        conn._pseudo_stream_buffer = []
    if not hasattr(conn, '_pseudo_stream_prefetch_triggered'):
        conn._pseudo_stream_prefetch_triggered = False
    if not hasattr(conn, '_prefetch_asr_text'):
        conn._prefetch_asr_text = None


def _reset_pseudo_stream_state(conn):
    """重置伪流式预取状态（VAD 静默后调用）"""
    conn._pseudo_stream_buffer = []
    conn._pseudo_stream_prefetch_triggered = False
    conn._prefetch_asr_text = None


async def _trigger_pseudo_streaming_prefetch(conn, audio: bytes, have_voice: bool):
    """
    伪流式 ASR Memory 预取
    
    策略：
    - 检测语音开始时，开始累积音频 buffer
    - buffer 累积到 ~500ms（约 8 帧）时，发送预取 ASR
    - 用 ASR 部分结果预取 Memory
    - 预取 query 来自用户当前说的话，天然与最终 query 相关
    

    """
    # 检查是否有 Memory 组件
    if not hasattr(conn, 'memory') or conn.memory is None:
        return
    
    _init_pseudo_stream_state(conn)
    
    # 获取上一帧的语音状态
    prev_have_voice = getattr(conn, '_prev_have_voice_for_prefetch', False)
    conn._prev_have_voice_for_prefetch = have_voice
    
    # 检测边缘：从无声到有声 → 重置状态，开始新一轮预取
    if have_voice and not prev_have_voice:
        _reset_pseudo_stream_state(conn)
        logger.bind(tag=TAG).debug("检测到语音开始，开始累积音频 buffer")
    
    # 检测边缘：从有声到无声 → 重置状态（静默后清理）
    if not have_voice and prev_have_voice:
        # 不立即重置，让 parallel_chat_handler 有机会使用预取结果
        pass
    
    # 累积音频到 buffer（仅在有声时）
    if have_voice:
        conn._pseudo_stream_buffer.append(audio)
        
        # 检查是否达到预取阈值
        if (len(conn._pseudo_stream_buffer) >= PSEUDO_STREAM_BUFFER_THRESHOLD 
            and not conn._pseudo_stream_prefetch_triggered):
            
            conn._pseudo_stream_prefetch_triggered = True
            
            # 复制当前 buffer 用于预取（不影响后续累积）
            prefetch_buffer = conn._pseudo_stream_buffer.copy()
            
            logger.bind(tag=TAG).info(
                f"触发伪流式预取: buffer={len(prefetch_buffer)} 帧 "
                f"(~{len(prefetch_buffer) * 60}ms)"
            )
            
            # 异步启动预取任务
            conn._prefetched_memory_task = asyncio.create_task(
                _pseudo_stream_prefetch_memory(conn, prefetch_buffer)
            )


async def _pseudo_stream_prefetch_memory(conn, audio_buffer: List[bytes]) -> None:
    """
    伪流式预取 Memory
    

    """
    try:
        start_time = time.time()
        
        # Step 1: 预取 ASR（用部分音频获取部分文本）
        partial_text = await _quick_asr_for_prefetch(conn, audio_buffer)
        
        if not partial_text or len(partial_text.strip()) < 2:
            logger.bind(tag=TAG).debug("预取 ASR 结果太短，跳过 Memory 预取")
            conn._prefetched_memory_result = None
            conn._prefetch_asr_text = None
            return
        
        # 保存预取的 ASR 文本（用于日志和调试）
        conn._prefetch_asr_text = partial_text
        
        asr_elapsed_ms = (time.time() - start_time) * 1000
        logger.bind(tag=TAG).info(
            f"预取 ASR 完成: {asr_elapsed_ms:.0f}ms, 部分文本: '{partial_text}'"
        )
        
        # Step 2: 用部分文本预取 Memory
        memory_start = time.time()
        try:
            result = await asyncio.wait_for(
                conn.memory.query_memory(partial_text),
                timeout=PSEUDO_STREAM_MEMORY_TIMEOUT
            )
            conn._prefetched_memory_result = result
            
            memory_elapsed_ms = (time.time() - memory_start) * 1000
            total_elapsed_ms = (time.time() - start_time) * 1000
            
            logger.bind(tag=TAG).info(
                f"Memory 预取完成: ASR={asr_elapsed_ms:.0f}ms, "
                f"Memory={memory_elapsed_ms:.0f}ms, 总计={total_elapsed_ms:.0f}ms, "
                f"结果长度: {len(result) if result else 0}"
            )
            
        except asyncio.TimeoutError:
            logger.bind(tag=TAG).debug("Memory 预取超时")
            conn._prefetched_memory_result = None
            
    except Exception as e:
        logger.bind(tag=TAG).warning(f"伪流式预取异常: {e}")
        conn._prefetched_memory_result = None
        conn._prefetch_asr_text = None


async def _quick_asr_for_prefetch(conn, audio_buffer: List[bytes]) -> str:
    """
    快速 ASR（用于伪流式预取）
    
    复用现有 ASR 服务，对部分音频进行识别。
    在线程池中执行，避免阻塞事件循环。
    """
    try:
        loop = asyncio.get_event_loop()
        
        def run_asr():
            """在线程中执行 ASR"""
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(
                        conn.asr.speech_to_text(
                            audio_buffer,
                            conn.session_id + "_prefetch",
                            conn.audio_format
                        )
                    )
                    return result[0] if result else ""
                finally:
                    new_loop.close()
            except Exception as e:
                logger.bind(tag=TAG).debug(f"预取 ASR 失败: {e}")
                return ""
        
        # 在线程池中执行，设置超时
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(run_asr)
                return future.result(timeout=PSEUDO_STREAM_ASR_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.bind(tag=TAG).debug("预取 ASR 超时")
                return ""
                
    except Exception as e:
        logger.bind(tag=TAG).warning(f"快速 ASR 异常: {e}")
        return ""


async def _parallel_interruption_check(conn, audio_chunk):
    """
    并行打断检测（目标 <400ms）
    
    流程：
    1. 累积音频到打断检测缓冲区
    2. 累积足够音频后触发快速 ASR
    3. 检测打断意图
    4. 如果是打断，立即停止 TTS
    """
    _init_interrupt_state(conn)
    
    # 防抖检查
    current_time = time.time() * 1000
    if (current_time - conn._last_interrupt_time) < INTERRUPT_DEBOUNCE_MS:
        return
    
    # 累积音频到缓冲区
    conn._interrupt_buffer.append(audio_chunk)
    
    # 检查是否已经有正在运行的检测任务
    if conn._interrupt_check_running:
        return
    
    # 累积足够音频后触发快速识别
    if len(conn._interrupt_buffer) >= INTERRUPT_BUFFER_SIZE:
        conn._interrupt_check_running = True
        audio_to_check = conn._interrupt_buffer.copy()
        conn._interrupt_buffer.clear()
        
        # 启动异步检测任务
        asyncio.create_task(_quick_asr_and_check(conn, audio_to_check))


async def _quick_asr_and_check(conn, audio_chunks):
    """
    快速 ASR + 打断意图检测
    
    在独立线程中执行 ASR，不阻塞主流程
    目标：<400ms 完成打断响应
    """
    try:
        start_time = time.time()
        
        # 使用线程池执行 ASR（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        
        def run_quick_asr():
            """在线程中执行快速 ASR"""
            try:
                # 创建新的事件循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    # 调用现有 ASR 接口
                    result = new_loop.run_until_complete(
                        conn.asr.speech_to_text(
                            audio_chunks, 
                            conn.session_id + "_interrupt", 
                            conn.audio_format
                        )
                    )
                    return result[0] if result else ""
                finally:
                    new_loop.close()
            except Exception as e:
                logger.bind(tag=TAG).debug(f"快速 ASR 失败: {e}")
                return ""
        
        # 在线程池中执行，设置超时
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(run_quick_asr)
                text = future.result(timeout=INTERRUPT_ASR_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.bind(tag=TAG).debug("快速 ASR 超时，跳过本次检测")
                return
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # 检测打断意图
        if text and _is_interruption_intent(text):
            # 再次检查是否还在说话（可能在 ASR 期间已经停止了）
            if conn.client_is_speaking:
                logger.bind(tag=TAG).info(
                    f"智能打断触发: '{text}' (耗时 {elapsed_ms:.0f}ms)"
                )
                conn._last_interrupt_time = time.time() * 1000
                
                # 通知 ParallelChatHandler 处理打断
                parallel_handler = _get_parallel_chat_handler(conn)
                if parallel_handler is not None:
                    await parallel_handler.handle_user_interruption(text)
                
                # 执行传统的打断处理
                await handleAbortMessage(conn)
                
                # 记录打断响应时间
                total_elapsed_ms = (time.time() - start_time) * 1000
                if total_elapsed_ms > 400:
                    logger.bind(tag=TAG).warning(
                        f"打断响应超时: {total_elapsed_ms:.0f}ms > 400ms"
                    )
                else:
                    logger.bind(tag=TAG).info(
                        f"打断响应完成: {total_elapsed_ms:.0f}ms (目标 <400ms)"
                    )
        elif text:
            logger.bind(tag=TAG).debug(
                f"快速 ASR 识别: '{text}'，非打断意图 (耗时 {elapsed_ms:.0f}ms)"
            )
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"快速打断检测失败: {e}")
    finally:
        conn._interrupt_check_running = False


async def handleAudioMessage(conn, audio):
    # 当前片段是否有人说话
    have_voice = conn.vad.is_vad(conn, audio)
    # 如果设备刚刚被唤醒，短暂忽略VAD检测
    if hasattr(conn, "just_woken_up") and conn.just_woken_up:
        have_voice = False
        # 设置一个短暂延迟后恢复VAD检测
        conn.asr_audio.clear()
        if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
            conn.vad_resume_task = asyncio.create_task(resume_vad_detection(conn))
        return

    # 当音频 buffer 累积到 ~500ms 时，用部分 ASR 结果预取 Memory
    await _trigger_pseudo_streaming_prefetch(conn, audio, have_voice)

    # 只有 TTS 正在播放且非手动监听模式时才检测打断
    # if conn.client_is_speaking and conn.client_listen_mode != "manual":
    #     # 初始化打断检测状态
    #     _init_interrupt_state(conn)
        
    #     if have_voice:
    #         # 检测到语音，增加连续语音帧计数
    #         conn._continuous_voice_count += 1
            
    #         # 当连续语音帧达到阈值时，触发打断
    #         # 这样可以过滤短暂噪音、回声、咳嗽等误触发
    #         if conn._continuous_voice_count >= CONTINUOUS_VOICE_THRESHOLD:
    #             logger.bind(tag=TAG).info(
    #                 f"持续语音检测触发打断: 连续 {conn._continuous_voice_count} 帧 "
    #                 f"(阈值 {CONTINUOUS_VOICE_THRESHOLD} 帧, 约 {CONTINUOUS_VOICE_THRESHOLD * 60}ms)"
    #             )
    #             # 重置计数器
    #             conn._continuous_voice_count = 0
    #             # 触发打断
    #             await handleAbortMessage(conn)
    #     else:
    #         # 没有检测到语音，重置连续语音帧计数
    #         conn._continuous_voice_count = 0
    if have_voice:
        if conn.client_is_speaking and conn.client_listen_mode != "manual":
            logger.bind(tag=TAG).info("检测到语音，触发打断")
            await handleAbortMessage(conn)

    # 设备长时间空闲检测，用于say goodbye
    await no_voice_close_connect(conn, have_voice)
    # 接收音频
    await conn.asr.receive_audio(conn, audio, have_voice)


async def resume_vad_detection(conn):
    # 等待2秒后恢复VAD检测
    await asyncio.sleep(2)
    conn.just_woken_up = False


async def startToChat(conn, text: str, multimodal_content: List[Dict[str, Any]] | None = None):
    """
    start to chat
    
    Args:
        conn: Session Connection 
        text: Text content
        multimodal_content: Optional multimodal content
    """
    # check if input is JSON format (contains speaker information)
    speaker_name = None
    actual_text = text

    try:
        # 尝试解析JSON格式的输入
        if text.strip().startswith("{") and text.strip().endswith("}"):
            data = json.loads(text)
            if "speaker" in data and "content" in data:
                speaker_name = data["speaker"]
                actual_text = data["content"]
                conn.logger.bind(tag=TAG).info(f"解析到说话人信息: {speaker_name}")

                # 直接使用JSON格式的文本，不解析
                actual_text = text
    except (json.JSONDecodeError, KeyError):
        # 如果解析失败，继续使用原始文本
        pass

    # 保存说话人信息到连接对象
    if speaker_name:
        conn.current_speaker = speaker_name
    else:
        conn.current_speaker = None

    if conn.need_bind:
        await check_bind_device(conn)
        return

    # 如果当日的输出字数大于限定的字数
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return

    # 提取用于检测的纯文本（去除JSON包装）
    check_text = actual_text
    try:
        if actual_text.strip().startswith("{"):
            parsed = json.loads(actual_text)
            if "content" in parsed:
                check_text = parsed["content"]
    except (json.JSONDecodeError, KeyError):
        pass

    # 强制停止检测：即使 TTS 未播放，如果有正在进行的 LLM 任务也要停止
    if _is_force_stop_intent(check_text):
        # 检查是否有正在进行的 LLM 任务
        if not conn.llm_finish_task:
            conn.logger.bind(tag=TAG).info(f"强制停止意图检测到: '{check_text}'，取消当前任务")
            await handleAbortMessage(conn)
            # 不继续处理，直接返回
            return
        # 如果 TTS 正在播放也要停止
        if conn.client_is_speaking:
            conn.logger.bind(tag=TAG).info(f"强制停止 TTS 播放: '{check_text}'")
            await handleAbortMessage(conn)
            return

    # 智能打断处理（TTS 正在播放时）
    if conn.client_is_speaking and conn.client_listen_mode != "manual":
        should_continue = await _smart_interrupt_handler(conn, actual_text)
        if not should_continue:
            # 反馈信号（嗯、好的等），不打断也不处理
            conn.logger.bind(tag=TAG).debug(f"跳过反馈信号: {actual_text}")
            return

    # 首先进行意图分析，使用实际文本内容
    intent_handled = await handle_user_intent(conn, actual_text)

    if intent_handled:
        # 如果意图已被处理，不再进行聊天
        return

    # 意图未被处理，继续常规聊天流程
    await send_stt_message(conn, actual_text)
    
    # 确定聊天内容：multimodal 优先
    chat_content = multimodal_content if multimodal_content else actual_text
    
    # 尝试使用并行优化的聊天处理器
    parallel_handler = _get_parallel_chat_handler(conn)
    if parallel_handler is not None:
        # 使用并行优化的异步 chat 方法
        conn.logger.bind(tag=TAG).debug("使用 ParallelChatHandler 处理消息")
        asyncio.create_task(_run_parallel_chat(conn, parallel_handler, chat_content))
    else:
        # 降级到原始的同步 chat 方法
        conn.executor.submit(conn.chat, chat_content)


async def _run_parallel_chat(conn, handler, content):
    """
    运行并行聊天处理
    
    包装 ParallelChatHandler.chat() 的异步调用，处理异常并降级
    
    Args:
        conn: 连接对象
        handler: ParallelChatHandler 实例
        content: 文本或 multimodal 内容
    """
    try:
        await handler.chat(content)
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"并行聊天处理失败: {e}，降级到原始方法")
        # 降级到原始方法
        conn.executor.submit(conn.chat, content)


async def no_voice_close_connect(conn, have_voice):
    if have_voice:
        conn.last_activity_time = time.time() * 1000
        return
    # 只有在已经初始化过时间戳的情况下才进行超时检查
    if conn.last_activity_time > 0.0:
        no_voice_time = time.time() * 1000 - conn.last_activity_time
        close_connection_no_voice_time = int(
            conn.config.get("close_connection_no_voice_time", 120)
        )
        if (
            not conn.close_after_chat
            and no_voice_time > 1000 * close_connection_no_voice_time
        ):
            conn.close_after_chat = True
            conn.client_abort = False
            end_prompt = conn.config.get("end_prompt", {})
            if end_prompt and end_prompt.get("enable", True) is False:
                conn.logger.bind(tag=TAG).info("结束对话，无需发送结束提示语")
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = "请你以```时间过得真快```未来头，用富有感情、依依不舍的话来结束这场对话吧。！"
            await startToChat(conn, prompt)


async def max_out_size(conn):
    # 播放超出最大输出字数的提示
    conn.client_abort = False
    text = "不好意思，我现在有点事情要忙，明天这个时候我们再聊，约好了哦！明天不见不散，拜拜！"
    await send_stt_message(conn, text)
    file_path = "config/assets/max_output_size.wav"
    opus_packets = audio_to_data(file_path)
    conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
    conn.close_after_chat = True


async def check_bind_device(conn):
    if conn.bind_code:
        # 确保bind_code是6位数字
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(f"无效的绑定码格式: {conn.bind_code}")
            text = "绑定码格式错误，请检查配置。"
            await send_stt_message(conn, text)
            return

        text = f"请登录控制面板，输入{conn.bind_code}，绑定设备。"
        await send_stt_message(conn, text)

        # 播放提示音
        music_path = "config/assets/bind_code.wav"
        opus_packets = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

        # 逐个播放数字
        for i in range(6):  # 确保只播放6位数字
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets = audio_to_data(num_path)
                conn.tts.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"播放数字音频失败: {e}")
                continue
        conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
    else:
        # 播放未绑定提示
        conn.client_abort = False
        text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
        await send_stt_message(conn, text)
        music_path = "config/assets/bind_not_found.wav"
        opus_packets = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
