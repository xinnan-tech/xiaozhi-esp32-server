# 导入所需的模块
from config.logger import setup_logging  # 导入日志设置模块
import time  # 导入时间模块，用于处理时间相关的操作
from core.utils.util import remove_punctuation_and_length  # 导入工具函数，用于去除标点符号并计算文本长度
from core.handle.sendAudioHandle import send_stt_message  # 导入发送音频消息的模块

# 定义当前模块的标签，通常用于日志记录
TAG = __name__

# 设置日志记录器
logger = setup_logging()

async def handleAudioMessage(conn, audio):
    """处理音频消息"""
    if not conn.asr_server_receive:  # 如果ASR服务器未准备好接收数据
        logger.bind(tag=TAG).debug(f"前期数据处理中，暂停接收")  # 记录调试信息
        return

    # 根据客户端的监听模式判断是否有声音
    if conn.client_listen_mode == "auto":  # 如果监听模式为自动
        have_voice = conn.vad.is_vad(conn, audio)  # 使用VAD（语音活动检测）判断是否有声音
    else:
        have_voice = conn.client_have_voice  # 否则使用客户端的声音状态

    # 如果本次没有声音且本段也没有声音，丢弃音频数据并关闭连接
    if have_voice == False and conn.client_have_voice == False:
        await no_voice_close_connect(conn)  # 调用无声音关闭连接函数
        conn.asr_audio.clear()  # 清空ASR音频缓存
        return

    conn.client_no_voice_last_time = 0.0  # 重置无声音计时器
    conn.asr_audio.append(audio)  # 将当前音频数据添加到ASR音频缓存中

    # 如果本段有声音且已经停止
    if conn.client_voice_stop:
        conn.client_abort = False  # 重置客户端中止标志
        conn.asr_server_receive = False  # 设置ASR服务器接收状态为False

        # 如果音频数据太短，无法识别
        if len(conn.asr_audio) < 3:
            conn.asr_server_receive = True  # 设置ASR服务器接收状态为True
        else:
            # 调用ASR服务将音频转换为文本
            text, file_path = await conn.asr.speech_to_text(conn.asr_audio, conn.session_id)
            logger.bind(tag=TAG).info(f"识别文本: {text}")  # 记录识别到的文本

            # 去除标点符号并计算文本长度
            text_len, text_without_punctuation = remove_punctuation_and_length(text)

            # 处理音乐命令
            if await conn.music_handler.handle_music_command(conn, text_without_punctuation):
                conn.asr_server_receive = True  # 设置ASR服务器接收状态为True
                conn.asr_audio.clear()  # 清空ASR音频缓存
                return

            # 处理命令消息
            if text_len <= conn.max_cmd_length and await handleCMDMessage(conn, text_without_punctuation):
                return

            # 如果文本长度大于0，启动聊天
            if text_len > 0:
                await startToChat(conn, text)
            else:
                conn.asr_server_receive = True  # 设置ASR服务器接收状态为True

        conn.asr_audio.clear()  # 清空ASR音频缓存
        conn.reset_vad_states()  # 重置VAD状态

async def handleCMDMessage(conn, text):
    """处理命令消息"""
    cmd_exit = conn.cmd_exit  # 获取退出命令列表
    for cmd in cmd_exit:  # 遍历退出命令列表
        if text == cmd:  # 如果识别到的文本与退出命令匹配
            logger.bind(tag=TAG).info("识别到明确的退出命令".format(text))  # 记录识别到的退出命令
            await conn.close()  # 关闭连接
            return True
    return False  # 如果没有匹配的退出命令，返回False

async def startToChat(conn, text):
    """启动聊天"""
    # 异步发送STT信息
    await send_stt_message(conn, text)
    # 提交聊天任务到线程池
    conn.executor.submit(conn.chat, text)

async def no_voice_close_connect(conn):
    """无声音时关闭连接"""
    if conn.client_no_voice_last_time == 0.0:  # 如果无声音计时器未启动
        conn.client_no_voice_last_time = time.time() * 1000  # 启动无声音计时器
    else:
        # 计算无声音时间
        no_voice_time = time.time() * 1000 - conn.client_no_voice_last_time
        # 获取配置中的无声音关闭连接时间，默认为120秒
        close_connection_no_voice_time = conn.config.get("close_connection_no_voice_time", 120)
        # 如果无声音时间超过配置的时间
        if no_voice_time > 1000 * close_connection_no_voice_time:
            conn.client_abort = False  # 重置客户端中止标志
            conn.asr_server_receive = False  # 设置ASR服务器接收状态为False
            # 设置提示信息
            prompt = "时间过得真快，我都好久没说话了。请你用十个字左右话跟我告别，以“再见”或“拜拜”为结尾"
            # 启动聊天
            await startToChat(conn, prompt)