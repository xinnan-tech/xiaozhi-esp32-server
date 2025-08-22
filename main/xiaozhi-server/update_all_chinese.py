#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
import sys

# Set UTF-8 encoding for output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Database connection
connection = pymysql.connect(
    host='nozomi.proxy.rlwy.net',
    port=25037,
    user='root',
    password='OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
    database='railway',
    charset='utf8mb4'
)

try:
    with connection.cursor() as cursor:
        print("=" * 60)
        print("Updating all Chinese model names to English...")
        print("=" * 60)
        
        # Comprehensive list of updates
        updates = [
            # TTS Models
            ("302AI语音合成", "302AI TTS"),
            ("ACGN语音合成", "ACGN TTS"),
            ("Coze中文语音合成", "Coze Chinese TTS"),
            ("FishSpeech语音合成", "FishSpeech TTS"),
            ("机智云语音合成", "Gizwits TTS"),
            ("火山双流式语音合成", "Volcano Dual-Stream TTS"),
            ("火山引擎边缘大模型网关", "Volcano Edge Gateway"),
            ("硅基流动语音合成", "SiliconFlow TTS"),
            ("自定义语音合成", "Custom TTS"),
            ("豆包语音合成", "Doubao TTS"),
            ("阿里云语音合成", "Aliyun TTS"),
            ("阿里云语音合成(流式)", "Aliyun TTS (Streaming)"),
            ("Linkerai语音合成", "Linkerai TTS"),
            ("MiniMax语音合成", "MiniMax TTS"),
            ("OpenAI语音合成", "OpenAI TTS"),
            ("Index-TTS-vLLM流式语音合成", "Index-TTS-vLLM Streaming"),
            
            # ASR Models
            ("FunASR服务语音识别", "FunASR Server Recognition"),
            ("FunASR语音识别", "FunASR Recognition"),
            ("Groq语音识别", "Groq Speech Recognition"),
            ("OpenAI语音识别", "OpenAI Speech Recognition"),
            ("Sherpa语音识别", "Sherpa Speech Recognition"),
            ("百度语音识别", "Baidu Speech Recognition"),
            ("腾讯语音识别", "Tencent Speech Recognition"),
            ("豆包语音识别", "Doubao Speech Recognition"),
            ("豆包语音识别(流式)", "Doubao Speech Recognition (Streaming)"),
            ("阿里云语音识别", "Aliyun Speech Recognition"),
            ("阿里云语音识别(流式)", "Aliyun Speech Recognition (Streaming)"),
            
            # LLM Models
            ("豆包大模型", "Doubao LLM"),
            ("Ollama本地模型", "Ollama Local Model"),
            ("Xinference大模型", "Xinference LLM"),
            ("Xinference小模型", "Xinference Small Model"),
            ("智谱AI", "Zhipu AI"),
            ("谷歌Gemini", "Google Gemini"),
            ("通义千问", "Tongyi Qianwen"),
            ("通义百炼", "Tongyi Bailian"),
            
            # Intent Models
            ("LLM意图识别", "LLM Intent Recognition"),
            ("函数调用意图识别", "Function Call Intent"),
            ("无意图识别", "No Intent Recognition"),
            
            # Memory Models
            ("Mem0AI记忆", "Mem0AI Memory"),
            ("无记忆", "No Memory"),
            ("本地短期记忆", "Local Short-term Memory"),
            
            # Vision Models
            ("千问视觉模型", "Qianwen Vision Model"),
            ("智谱视觉AI", "Zhipu Vision AI"),
        ]
        
        total_updated = 0
        for old_name, new_name in updates:
            sql = "UPDATE ai_model_config SET model_name = %s WHERE model_name = %s"
            cursor.execute(sql, (new_name, old_name))
            if cursor.rowcount > 0:
                print(f"✓ Updated: '{old_name}' → '{new_name}'")
                total_updated += 1
        
        connection.commit()
        
        if total_updated > 0:
            print(f"\n✅ Successfully updated {total_updated} model names!")
        else:
            print("\n⚠️ No models needed updating.")
        
        # Show final results
        print("\n" + "=" * 60)
        print("Final Model Names:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT model_type, model_name, id 
        FROM ai_model_config 
        ORDER BY model_type, model_name
        """)
        
        current_type = None
        for row in cursor.fetchall():
            if row[0] != current_type:
                current_type = row[0]
                print(f"\n{current_type.upper()} Models:")
            print(f"  - {row[1]} (ID: {row[2]})")
            
finally:
    connection.close()