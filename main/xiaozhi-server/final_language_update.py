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
        print("Final Language Updates:")
        print("=" * 60)
        
        # More comprehensive language updates
        language_updates = [
            ("美式英语", "US English"),
            ("英式英语", "UK English"),
            ("澳洲英语", "AU English"),
            ("中文", "Chinese"),
            ("中文-北京口音", "Chinese-Beijing"),
            ("中文-四川口音", "Chinese-Sichuan"),
            ("中文-长沙口音", "Chinese-Changsha"),
            ("中文-广东口音", "Chinese-Guangdong"),
            ("中文-广西口音", "Chinese-Guangxi"),
            ("中文-青岛口音", "Chinese-Qingdao"),
            ("中文-台湾口音", "Chinese-Taiwan"),
            ("中文-河南口音", "Chinese-Henan"),
            ("中文、美式英语", "Chinese, US English"),
            ("中文-北京口音、英文", "Chinese-Beijing, EN"),
            ("日语、西语", "Japanese, Spanish"),
        ]
        
        total_updated = 0
        for old_lang, new_lang in language_updates:
            # Check column length limit (50 chars for languages column)
            if len(new_lang) <= 50:
                cursor.execute("""
                UPDATE ai_tts_voice 
                SET languages = %s 
                WHERE languages = %s
                """, (new_lang, old_lang))
                
                if cursor.rowcount > 0:
                    print(f"✓ Updated {cursor.rowcount} voices: '{old_lang}' → '{new_lang}'")
                    total_updated += cursor.rowcount
        
        connection.commit()
        
        print(f"\n✅ Total updates: {total_updated} language entries!")
        
        # Show EdgeTTS voices specifically
        print("\n" + "=" * 60)
        print("EdgeTTS Voices (Final):")
        print("=" * 60)
        
        cursor.execute("""
        SELECT v.name, v.tts_voice, v.languages
        FROM ai_tts_voice v
        JOIN ai_model_config m ON v.tts_model_id = m.id
        WHERE m.model_name = 'EdgeTTS'
        ORDER BY v.name
        """)
        
        voices = cursor.fetchall()
        
        print(f"{'Name':<20} {'Voice ID':<35} {'Language':<20}")
        print("-" * 75)
        for voice in voices:
            print(f"{voice[0]:<20} {voice[1]:<35} {voice[2] or 'N/A':<20}")
        
        print(f"\n✅ EdgeTTS voices are ready! The voice IDs (like zh-CN-XiaoxiaoNeural) remain unchanged.")
        print("✅ EdgeTTS will continue to work properly with these English display names.")
            
finally:
    connection.close()