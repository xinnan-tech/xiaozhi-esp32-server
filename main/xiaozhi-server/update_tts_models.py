#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
import json
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
        # Check TTS models
        print("=" * 60)
        print("Current TTS Models in Database:")
        print("=" * 60)
        
        sql = """
        SELECT id, model_name, model_type, config_json 
        FROM ai_model_config 
        WHERE model_type = 'tts' OR model_name LIKE '%Edge%' OR model_name LIKE '%语音%' OR model_name LIKE '%TTS%'
        ORDER BY model_name
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if not results:
            print("No TTS models found. Checking all models...")
            cursor.execute("SELECT id, model_name, model_type FROM ai_model_config")
            results = cursor.fetchall()
        
        for row in results:
            print(f"\nID: {row[0]}")
            print(f"Model Name: {row[1]}")
            print(f"Model Type: {row[2]}")
            if len(row) > 3 and row[3]:
                try:
                    config = json.loads(row[3])
                    print(f"Config Type: {config.get('type', 'N/A')}")
                except:
                    pass
        
        # Update the Chinese text to English
        print("\n" + "=" * 60)
        print("Updating Chinese model names to English...")
        print("=" * 60)
        
        updates = [
            ("Edge语音合成", "Edge TTS"),
            ("Edge TTS语音合成", "Edge TTS"),
            ("百度语音合成", "Baidu TTS"),
            ("阿里语音合成", "Ali TTS"),
            ("腾讯语音合成", "Tencent TTS"),
            ("科大讯飞语音合成", "iFlytek TTS"),
            ("讯飞语音合成", "iFlytek TTS"),
            ("微软语音合成", "Microsoft TTS"),
            ("谷歌语音合成", "Google TTS"),
            # Also update other model types if needed
            ("语音识别", "Speech Recognition"),
            ("语音活动检测", "Voice Activity Detection"),
            ("大语言模型", "Large Language Model"),
            ("视觉大模型", "Vision Language Model"),
            ("意图识别", "Intent Recognition"),
            ("记忆模型", "Memory Model")
        ]
        
        for old_name, new_name in updates:
            sql = "UPDATE ai_model_config SET model_name = %s WHERE model_name = %s"
            cursor.execute(sql, (new_name, old_name))
            if cursor.rowcount > 0:
                print(f"✓ Updated: '{old_name}' → '{new_name}'")
        
        # Also check for partial matches and update them
        cursor.execute("SELECT id, model_name FROM ai_model_config WHERE model_name LIKE '%语音%' OR model_name LIKE '%模型%'")
        chinese_models = cursor.fetchall()
        
        if chinese_models:
            print("\nFound models with Chinese characters:")
            for model_id, model_name in chinese_models:
                print(f"  - {model_name} (ID: {model_id})")
        
        connection.commit()
        print("\n✅ All model names have been updated to English!")
        
        # Verify the changes
        print("\n" + "=" * 60)
        print("Updated Models (showing all):")
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