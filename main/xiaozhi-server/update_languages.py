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
        print("Updating Language Names in TTS Voices:")
        print("=" * 60)
        
        # Update language names
        language_updates = [
            ("普通话", "Mandarin"),
            ("粤语", "Cantonese"),
            ("辽宁", "Liaoning"),
            ("陕西", "Shaanxi"),
            ("四川", "Sichuan"),
            ("台湾", "Taiwan"),
            ("香港", "Hong Kong"),
            ("英语", "English"),
            ("日语", "Japanese"),
            ("韩语", "Korean"),
            ("法语", "French"),
            ("德语", "German"),
            ("西班牙语", "Spanish"),
            ("意大利语", "Italian"),
            ("俄语", "Russian"),
            ("阿拉伯语", "Arabic"),
        ]
        
        total_updated = 0
        for old_lang, new_lang in language_updates:
            cursor.execute("""
            UPDATE ai_tts_voice 
            SET languages = %s 
            WHERE languages = %s
            """, (new_lang, old_lang))
            
            if cursor.rowcount > 0:
                print(f"✓ Updated {cursor.rowcount} voices: '{old_lang}' → '{new_lang}'")
                total_updated += cursor.rowcount
        
        connection.commit()
        
        if total_updated > 0:
            print(f"\n✅ Successfully updated {total_updated} language entries!")
        
        # Show final results for EdgeTTS
        print("\n" + "=" * 60)
        print("Final EdgeTTS Voice Configuration:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT v.name, v.tts_voice, v.languages, v.remark
        FROM ai_tts_voice v
        JOIN ai_model_config m ON v.tts_model_id = m.id
        WHERE m.model_name LIKE '%Edge%'
        ORDER BY v.name
        """)
        
        voices = cursor.fetchall()
        
        print(f"{'Name':<20} {'Voice ID':<30} {'Language':<15} {'Remark':<20}")
        print("-" * 85)
        for voice in voices:
            remark = (voice[3][:17] + '...') if voice[3] and len(voice[3]) > 20 else (voice[3] or '')
            print(f"{voice[0]:<20} {voice[1]:<30} {voice[2] or 'N/A':<15} {remark:<20}")
            
finally:
    connection.close()